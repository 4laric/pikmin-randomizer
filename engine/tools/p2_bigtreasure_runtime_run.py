"""Run and verify the private BigTreasure host-seam runtime fixture in a fresh room overlay.

Issue #246. Mirrors the Groink volley runner pattern: verifies fixture
provenance, stages a private overlay via scripts/preview_pikmin2_room.py,
copies the lane profile in, runs the fixture with --experimental-pikmin2-room
and checks the probe markers (flat floor, free space, vertical wall, elec
bounce, water arc, host-seam lifetime).
"""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import traceback


# Harness watchdog only; the fixture's own 3600-frame idle cap (~120 s at
# 30 Hz) remains the real limiter. The full 29-clip motion phase runs source
# clips 1:1 with the fixture in exclusive control, so the whole session needs
# ~83 s of wall clock.
FIXTURE_TIMEOUT_SECONDS = 240


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path):
    return {"path": str(path), "sha256": sha256(path), "size": path.stat().st_size}


def load_preview_prepare(root):
    source = root / "scripts" / "preview_pikmin2_room.py"
    if not source.is_file():
        raise ValueError(f"missing preview helper: {source}")
    spec = importlib.util.spec_from_file_location("p2_preview_overlay", source)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.prepare


def fixture_provenance(fixture):
    provenance_path = fixture / "provenance.json"
    executable = fixture / "fixture.exe"
    if not provenance_path.is_file() or not executable.is_file():
        raise ValueError("fixture must contain provenance.json and fixture.exe")
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    if provenance.get("status") != "built":
        raise ValueError("fixture provenance is not built")
    artifacts = provenance.get("artifacts", {})
    record = next((value for name, value in artifacts.items()
                   if Path(name).name.lower() == "fixture.exe"), None)
    if not isinstance(record, dict) or not isinstance(record.get("sha256"), str):
        raise ValueError("fixture provenance has no fixture.exe hash")
    actual = sha256(executable)
    if actual != record["sha256"]:
        raise ValueError("fixture.exe hash differs from built provenance")
    return provenance_path, provenance, executable, actual


def copy_new(source, target):
    if not source.is_file():
        raise ValueError(f"missing staged input: {source}")
    if target.exists():
        raise ValueError(f"refusing to replace existing target: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def verify_log(text):
    errors = []
    floor = re.search(r"^P2_BIGTREASURE_FLOOR_PROBE\s+ground=(-?[\d.]+)\s+center=(-?[\d.]+)\s+"
                      r"floor=1\s*$", text, flags=re.MULTILINE)
    if not floor:
        errors.append("missing floor probe marker")
    elif abs(float(floor.group(2)) - (float(floor.group(1)) + 20.0)) > 0.25:
        errors.append(f"floor probe center does not rest at ground+20: {floor.groups()}")
    if not re.search(r"^P2_BIGTREASURE_WALL_PROBE\s+wall=1\s+groundY=-?[\d.]+\s*$", text,
                     flags=re.MULTILINE):
        errors.append("missing wall probe marker")
    for marker in ("P2_BIGTREASURE_MAP_PROBES_PASS", "P2_BIGTREASURE_ELEC_PROBE_PASS",
                   "P2_BIGTREASURE_WATER_PROBE_PASS", "P2_BIGTREASURE_HOST_SEAM_PASS",
                   "P2_BIGTREASURE_HOST_READY"):
        if marker not in text:
            errors.append(f"missing marker: {marker}")
    elec = re.search(r"^P2_BIGTREASURE_ELEC_PROBE_PASS\s+bounces=(\d+)\s+traces=(\d+)\s+"
                     r"floors=(\d+)\s*$", text, flags=re.MULTILINE)
    if elec and (int(elec.group(1)) < 1 or int(elec.group(3)) < 1):
        errors.append(f"elec probe recorded no bounce/floor contact: {elec.groups()}")
    seam = re.search(r"^P2_BIGTREASURE_HOST_SEAM_PASS\s+ticks=(\d+)\s+attacks=(\d+)\s+"
                     r"events=(\d+)\s*$", text, flags=re.MULTILINE)
    if seam and int(seam.group(3)) != 5:
        errors.append(f"seam defeat did not release 5 captures: {seam.groups()}")
    if not re.search(r"^P2_BIGTREASURE_WINDOW\s+size=960x540\s+pos=-?\d+,-?\d+\s*$", text,
                     flags=re.MULTILINE):
        errors.append("missing 960x540 window marker")
    fsmhost = re.search(r"^P2_BIGTREASURE_FSMHOST_FULL_PASS\s+knockoffs=(\d+)\s+weapons=(\d+)\s+"
                        r"phase=(\w+)\s+transitions=(\d+)\s*$", text, flags=re.MULTILINE)
    if not fsmhost:
        errors.append("missing fsmhost FULL PASS marker")
    elif (int(fsmhost.group(1)) != 4 or int(fsmhost.group(2)) != 0
          or fsmhost.group(3) != "DropItem" or int(fsmhost.group(4)) != 4):
        errors.append(f"fsmhost four-weapon phase progression not observed: {fsmhost.groups()}")
    encounter = re.search(r"^P2_BIGTREASURE_ENCOUNTER_PASS\s+knockoffs=(\d+)\s+hits=(\d+)\s+"
                          r"phase=(\w+)\s+events=(\d+)\s*$", text, flags=re.MULTILINE)
    if not encounter:
        errors.append("missing encounter PASS marker")
    elif (int(encounter.group(1)) != 4 or int(encounter.group(2)) < 4
          or encounter.group(3) != "Dead" or int(encounter.group(4)) < 4):
        errors.append(f"encounter did not complete the full boss fight: {encounter.groups()}")
    visual = re.search(r"^P2_BIGTREASURE_VISUAL_READY\s+clips=(\d+)\s+pellets=(\d+)\s+"
                       r"pellet_debug=(\d+)\s*$", text, flags=re.MULTILINE)
    if not visual:
        errors.append("missing visual READY marker")
    elif tuple(map(int, visual.groups()[1:])) != (4, 1):
        errors.append(f"unexpected visual bank accounting: {visual.groups()}")
    draw = re.search(r"^P2_BIGTREASURE_VISUAL_DRAW\s+clip=(\w+)\s+pose=(\d+)\s+pellets=(\d+)\s+"
                     r"pellet_debug=(\d+)\s*$", text, flags=re.MULTILINE)
    if not draw:
        errors.append("missing visual DRAW marker")
    wait1 = re.search(r"^P2_BIGTREASURE_VISUAL_WAIT1_PASS\s+frames=(\d+)\s+events=(\d+)\s+"
                      r"loops=(\d+)\s+pose=(\d+)\s*$", text, flags=re.MULTILINE)
    if not wait1:
        errors.append("missing wait1 playback marker")
    elif int(wait1.group(3)) < 2:
        errors.append(f"wait1 did not loop: {wait1.groups()}")
    dead = re.search(r"^P2_BIGTREASURE_VISUAL_DEAD_PASS\s+frames=(\d+)\s+events=(\d+)\s+"
                     r"keyevent100=(\d+)\s*$", text, flags=re.MULTILINE)
    if not dead:
        errors.append("missing dead playback marker")
    elif int(dead.group(2)) != 12 or int(dead.group(3)) != 320:
        errors.append(f"dead playback did not fire all authored events: {dead.groups()}")
    motion = re.search(r"^P2_BIGTREASURE_MOTION_PASS\s+clips=(\d+)\s+events=(\d+)\s*$", text,
                       flags=re.MULTILINE)
    if not motion:
        errors.append("missing extra-clip motion playback marker")
    elif int(motion.group(1)) < 3:
        errors.append(f"motion playback advanced fewer than 3 staged clips: {motion.groups()}")
    motion_full = re.search(r"^P2_BIGTREASURE_MOTION_FULL_PASS\s+clips=(\d+)\s+events=(\d+)\s+"
                            r"advanced=(\d+)\s*$", text, flags=re.MULTILINE)
    if not motion_full:
        errors.append("missing full motion staging marker")
    else:
        clips, events, advanced = map(int, motion_full.groups())
        if clips < 16:
            errors.append(f"full motion staging covered fewer than 16 clips: {motion_full.groups()}")
        if advanced != clips:
            errors.append(f"full motion staging did not advance every staged clip: "
                          f"{motion_full.groups()}")
        if events < clips:
            errors.append(f"full motion staging dispatched fewer events than clips: "
                          f"{motion_full.groups()}")
    if "PASS BIGTREASURE_RUNTIME" not in text:
        errors.append("missing runtime PASS marker")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-worktree", type=Path, required=True,
                        help="Python repository containing scripts/preview_pikmin2_room.py")
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--room", type=Path, required=True,
                        help="Converted room directory accepted by preview.prepare")
    parser.add_argument("--stage", type=Path, required=True,
                        help="BigTreasure stage containing p2-bigtreasure-host.txt")
    parser.add_argument("--visual-stage", type=Path, required=True,
                        help="Visual stage from pikmin2_bigtreasure_stage (profile, events, mods)")
    parser.add_argument("--fixture", type=Path, required=True,
                        help="Built fixture directory containing fixture.exe and provenance.json")
    parser.add_argument("--output", type=Path, required=True,
                        help="Parent directory for the fresh run overlay")
    args = parser.parse_args()

    record = {"schema": 1, "arguments": {key: str(value) if isinstance(value, Path) else value
              for key, value in vars(args).items()}, "status": "failed", "errors": []}
    run = None
    try:
        root = args.root_worktree.resolve()
        assets, room, stage, fixture, output = (args.assets.resolve(), args.room.resolve(),
                                                 args.stage.resolve(), args.fixture.resolve(),
                                                 args.output.resolve())
        visual_stage = args.visual_stage.resolve()
        provenance_path, provenance, executable, executable_hash = fixture_provenance(fixture)
        prepare = load_preview_prepare(root)
        run = prepare(assets, room, output)
        record["run"] = str(run)
        profile_source = stage / "p2-bigtreasure-host.txt"
        profile_target = run / "p2-bigtreasure-host.txt"
        copy_new(profile_source, profile_target)
        # Visual stage: profile + event table at the run root, converted mods
        # under the overlay's courses/pikmin2room/ (bounded, hash-recorded).
        staged = {}
        manifest = json.loads((visual_stage / "stage.json").read_text(encoding="utf-8"))
        expected_mods = int(manifest["poses"]) + int(manifest["pellets_converted"])
        stage_files = [visual_stage / "p2-bigtreasure-visual.txt",
                       visual_stage / "p2_bigtreasure_events.txt"]
        stage_files += sorted((visual_stage / "assets" / "dataDir" / "courses" / "pikmin2room").glob("*.mod"))
        if len(stage_files) != 2 + expected_mods:
            raise ValueError(f"unexpected visual stage file count: {len(stage_files)}")
        total = 0
        for source in stage_files:
            total += source.stat().st_size
            if total > 96 * 1024 * 1024:
                raise ValueError("visual stage byte budget exceeded")
            if source.suffix == ".mod":
                target = run / "assets" / "dataDir" / "courses" / "pikmin2room" / source.name
            else:
                target = run / source.name
            copy_new(source, target)
            staged[source.name] = sha256(target)
        record["visual_stage_files"] = len(staged)
        record["fixture"] = {"provenance": file_record(provenance_path),
                             "provenance_status": provenance.get("status"),
                             "executable": {"path": str(executable), "sha256": executable_hash}}
        record["inputs"] = {"profile": file_record(profile_target)}
        for name in ("room.mod", "room.ini", "treasure.mod"):
            record["inputs"][name] = file_record(room / name)
        record["inputs"]["preview_helper"] = file_record(root / "scripts" / "preview_pikmin2_room.py")
        command = [str(executable), "--experimental-pikmin2-room"]
        record["command"] = command
        # Inherit the caller's PATH and all other environment values unchanged.
        result = subprocess.run(command, cwd=run, env=dict(os.environ),
                                timeout=FIXTURE_TIMEOUT_SECONDS,
                                text=True, encoding="utf-8", errors="replace",
                                capture_output=True)
        (run / "stdout.log").write_text(result.stdout, encoding="utf-8")
        (run / "stderr.log").write_text(result.stderr, encoding="utf-8")
        record["subprocess"] = {"returncode": result.returncode,
                                "timeout_seconds": FIXTURE_TIMEOUT_SECONDS,
                                "stdout": file_record(run / "stdout.log"),
                                "stderr": file_record(run / "stderr.log")}
        errors = verify_log(result.stdout + "\n" + result.stderr)
        record["verification"] = {"errors": errors}
        captures = {}
        for name in ("bigtreasure-wait1.ppm", "bigtreasure-dead.ppm"):
            path = run / name
            if not path.is_file():
                errors.append(f"missing capture: {name}")
            elif path.stat().st_size < 100000:
                errors.append(f"trivial capture: {name}")
            else:
                captures[name] = file_record(path)
        record["captures"] = captures
        if result.returncode != 0:
            errors.append(f"fixture exit code {result.returncode}")
        record["errors"].extend(errors)
        if not errors:
            record["status"] = "passed"
    except subprocess.TimeoutExpired as error:
        record["errors"].append(
            f"fixture timed out after {FIXTURE_TIMEOUT_SECONDS} seconds")
        if run is not None:
            for name, value in (("stdout.log", error.stdout), ("stderr.log", error.stderr)):
                if isinstance(value, bytes):
                    value = value.decode("utf-8", errors="replace")
                (run / name).write_text(value or "", encoding="utf-8")
    except Exception as error:
        record["errors"].append(str(error))
        record["traceback"] = traceback.format_exc()
    output.mkdir(parents=True, exist_ok=True)
    if run is not None:
        (run / "verification.json").write_text(json.dumps(record, indent=2) + "\n",
                                               encoding="utf-8")
    print(json.dumps({"status": record["status"], "run": str(run) if run else None,
                      "errors": record["errors"]}, indent=2))
    return 0 if record["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
