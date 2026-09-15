"""Run and verify the private Waterwraith ENCOUNTER runtime fixture (#443 / #175).

Mirrors tools/p2_waterwraith_register_runtime_run.py: verifies fixture
provenance, stages a fresh room overlay via scripts/preview_pikmin2_room.py,
copies the opt-in actor profile and the two-species visual stage in, runs the
fixture with --experimental-pikmin2-room, and checks the encounter markers. The
combat itself is driven by the real engine tick (pc_p2_waterwraith_register ->
pc_p2_waterwraith_encounter) over the live Piki squad; the fixture only arranges
Pikmin near the actor.
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

MARKERS = (
    "P2_WATERWRAITH_ENCOUNTER_WINDOW",
    "P2_WATERWRAITH_ENCOUNTER_READY",
    "P2_WATERWRAITH_ENCOUNTER_STAGE_A",
    "P2_WATERWRAITH_ENCOUNTER_PURPLE_SETUP",
    "P2_WATERWRAITH_BODY_ZERO",
    "P2_WATERWRAITH_CORPSE",
    "P2_WATERWRAITH_FINISHED",
    "P2_WATERWRAITH_CARRY_SETUP",
    "P2_WATERWRAITH_POD_RECEIPT",
    "P2_WATERWRAITH_ENCOUNTER_DELIVERED",
    "P2_WATERWRAITH_ENCOUNTER_PASS",
    "PASS WATERWRAITH_ENCOUNTER_RUNTIME",
)


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
    if not re.search(r"^P2_WATERWRAITH_ENCOUNTER_WINDOW\s+size=960x540\s*$", text,
                     flags=re.MULTILINE):
        errors.append("missing 960x540 window marker")
    if not re.search(r"^P2_WATERWRAITH_ENCOUNTER_READY\s*$", text, flags=re.MULTILINE):
        errors.append("missing encounter READY marker")
    stage_a = re.search(r"^P2_WATERWRAITH_ENCOUNTER_STAGE_A\s+crushes=(\d+)\s+damage=([\d.]+)\s*$",
                        text, flags=re.MULTILINE)
    if not stage_a:
        errors.append("missing Stage A marker")
    elif int(stage_a.group(1)) < 1 or float(stage_a.group(2)) != 0.0:
        errors.append(f"Stage A non-Purple damage/crush gate failed: {stage_a.groups()}")
    if not re.search(r"^P2_WATERWRAITH_ENCOUNTER_PURPLE_SETUP\s*$", text, flags=re.MULTILINE):
        errors.append("missing Purple setup marker")
    if not re.search(r"^P2_WATERWRAITH_BODY_ZERO\s+tick=\d+\s+bodyHealth=0\.0\s*$", text,
                     flags=re.MULTILINE):
        errors.append("missing body-zero marker")
    if not re.search(r"^P2_WATERWRAITH_CORPSE\s+.*standin=number_pellet\s*$", text,
                     flags=re.MULTILINE):
        errors.append("missing corpse stand-in marker")
    if not re.search(r"^P2_WATERWRAITH_FINISHED\s+tick=\d+\s+bodyHealth=0\.0\s*$", text,
                     flags=re.MULTILINE):
        errors.append("missing teardown marker")
    if not re.search(r"^P2_WATERWRAITH_CARRY_SETUP\s*$", text, flags=re.MULTILINE):
        errors.append("missing carry-setup marker")
    delivered = bool(re.search(r"^P2_WATERWRAITH_POD_RECEIPT\s+generator=\d+\s+deliveries=\d+\s*$",
                               text, flags=re.MULTILINE))
    blocked = bool(re.search(r"^P2_WATERWRAITH_CARRY_UNRESOLVED\s+frame=\d+\s+max_carriers=\d+\s+"
                             r"deliveries=0\s*$", text, flags=re.MULTILINE))
    if delivered:
        if not re.search(r"^P2_WATERWRAITH_ENCOUNTER_DELIVERED\s+deliveries=\d+\s*$", text,
                         flags=re.MULTILINE):
            errors.append("missing encounter delivered marker")
    elif blocked:
        pass  # natural carry did not complete; carrier evidence is logged
    else:
        errors.append("missing carry outcome (delivered or unresolved)")
    if not re.search(r"^P2_WATERWRAITH_ENCOUNTER_DEATH_REENTRY\s+ready=1\s+attached=1\s*$", text,
                     flags=re.MULTILINE):
        errors.append("missing death cleanup/re-entry marker")
    passed = re.search(r"^P2_WATERWRAITH_ENCOUNTER_PASS\s+stuns=(\d+)\s+hits=(\d+)\s+crushes=(\d+)\s+"
                       r"damage=([\d.]+)\s+zeroed=1\s+child_removed=1\s+body_zeroed=1\s+"
                       r"treasure=1\s+kill=1\s+delivered=(\d+)\s*$", text, flags=re.MULTILINE)
    if not passed:
        errors.append("missing encounter PASS marker")
    else:
        stuns, hits, crushes, damage, delivered_flag = (int(passed.group(1)), int(passed.group(2)),
                                                        int(passed.group(3)), float(passed.group(4)),
                                                        int(passed.group(5)))
        if stuns < 1:
            errors.append("no Purple landing stun observed")
        if hits < 1:
            errors.append("no accepted Purple hit observed")
        if crushes < 1:
            errors.append("no roller crush observed")
        if damage <= 0.0:
            errors.append("no damage dealt")
        if delivered_flag != (1 if delivered else 0):
            errors.append("delivered flag mismatch with carry outcome")
    if delivered and "PASS WATERWRAITH_ENCOUNTER_RUNTIME" not in text:
        errors.append("missing runtime PASS marker")
    elif blocked and "BLOCKED WATERWRAITH_ENCOUNTER_RUNTIME" not in text:
        errors.append("missing runtime BLOCKED marker")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-worktree", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--room", type=Path, required=True)
    parser.add_argument("--stage", type=Path, required=True,
                        help="Directory containing p2-waterwraith-actor.txt")
    parser.add_argument("--visual-stage", type=Path, required=True)
    parser.add_argument("--purple-stage", type=Path, default=None,
                        help="Directory containing p2-purple.txt and courses/purple_*.mod")
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

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
        copy_new(stage / "p2-waterwraith-actor.txt", run / "p2-waterwraith-actor.txt")
        profile = visual_stage / "p2-waterwraith-visual.txt"
        copy_new(profile, run / "p2-waterwraith-visual.txt")
        # The Purple converter (pc_p2_make_purple) and several opt-in family
        # setups gate on a live Pod anchor (pc_p2_preview_goal); stage one when
        # the provider directory carries it (same borrow the cave/purple lanes use).
        for extra in ("p2-pod.txt", "p2-economy.txt"):
            if (stage / extra).is_file():
                copy_new(stage / extra, run / extra)
        staged = {}
        mods = sorted((visual_stage / "assets" / "dataDir" / "courses" / "pikmin2room").glob("*.mod"))
        if not mods:
            raise ValueError("visual stage has no .mod files")
        total = 0
        for source in mods:
            total += source.stat().st_size
            if total > 96 * 1024 * 1024:
                raise ValueError("visual stage byte budget exceeded")
            target = run / "assets" / "dataDir" / "courses" / "pikmin2room" / source.name
            copy_new(source, target)
            staged[source.name] = sha256(target)
        record["visual_stage_files"] = len(staged)
        if args.purple_stage is not None:
            purple_stage = args.purple_stage.resolve()
            purple_profiles = sorted(p for p in purple_stage.iterdir()
                                     if p.is_file() and p.name.startswith("p2-"))
            if not any(p.name == "p2-purple.txt" for p in purple_profiles):
                raise ValueError("purple stage has no p2-purple.txt")
            copied = {}
            for source in purple_profiles:
                copy_new(source, run / source.name)
                copied[source.name] = file_record(run / source.name)
            record["purple_profiles"] = copied
            purple_courses = purple_stage / "courses"
            purple_mods = sorted(purple_courses.glob("*.mod")) if purple_courses.is_dir() else []
            purple_total = 0
            for source in purple_mods:
                purple_total += source.stat().st_size
                if purple_total > 8 * 1024 * 1024:
                    raise ValueError("purple stage byte budget exceeded")
                target = run / "assets" / "dataDir" / "courses" / "pikmin2room" / source.name
                if not target.exists():
                    copy_new(source, target)
            record["purple_stage_files"] = len(purple_mods)
        record["fixture"] = {"provenance": file_record(provenance_path),
                             "provenance_status": provenance.get("status"),
                             "executable": {"path": str(executable), "sha256": executable_hash}}
        record["inputs"] = {"actor_profile": file_record(run / "p2-waterwraith-actor.txt"),
                            "profile": file_record(run / "p2-waterwraith-visual.txt")}
        for name in ("room.mod", "room.ini", "treasure.mod"):
            record["inputs"][name] = file_record(room / name)
        record["inputs"]["preview_helper"] = file_record(root / "scripts" / "preview_pikmin2_room.py")
        command = [str(executable), "--experimental-pikmin2-room"]
        record["command"] = command
        result = subprocess.run(command, cwd=run, env=dict(os.environ), timeout=150,
                                text=True, encoding="utf-8", errors="replace", capture_output=True)
        (run / "stdout.log").write_text(result.stdout, encoding="utf-8")
        (run / "stderr.log").write_text(result.stderr, encoding="utf-8")
        record["subprocess"] = {"returncode": result.returncode, "timeout_seconds": 150,
                                "stdout": file_record(run / "stdout.log"),
                                "stderr": file_record(run / "stderr.log")}
        combined = result.stdout + "\n" + result.stderr
        errors = verify_log(combined)
        record["verification"] = {"errors": errors}
        capture = run / "waterwraith-encounter.ppm"
        if not capture.is_file():
            errors.append("missing capture: waterwraith-encounter.ppm")
        elif capture.stat().st_size < 100000:
            errors.append("trivial capture: waterwraith-encounter.ppm")
        else:
            record["captures"] = {"waterwraith-encounter.ppm": file_record(capture)}
        if result.returncode != 0:
            errors.append(f"fixture exit code {result.returncode}")
        record["errors"].extend(errors)
        if not errors:
            record["status"] = (
                "blocked" if "BLOCKED WATERWRAITH_ENCOUNTER_RUNTIME" in combined else "passed")
            record["outcome"] = (
                "blocked" if "BLOCKED WATERWRAITH_ENCOUNTER_RUNTIME" in combined else "delivered")
    except subprocess.TimeoutExpired as error:
        record["errors"].append("fixture timed out after 150 seconds")
        if run is not None:
            for name, value in (("stdout.log", error.stdout), ("stderr.log", error.stderr)):
                if isinstance(value, bytes):
                    value = value.decode("utf-8", errors="replace")
                (run / name).write_text(value or "", encoding="utf-8")
    except Exception as error:  # noqa: BLE001 - report any staging failure in the record
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
