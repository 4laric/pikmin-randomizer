"""Run and verify the private Waterwraith/Tyre visual runtime fixture (#175/#443).

Mirrors tools/p2_bigtreasure_runtime_run.py: verifies fixture provenance,
stages a fresh room overlay via scripts/preview_pikmin2_room.py, copies the
two-species visual profile and pose .mod files in, runs the fixture with
--experimental-pikmin2-room, and checks the window/visual/PASS markers.
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

MARKERS = ("P2_WATERWRAITH_VISUAL_READY", "P2_WATERWRAITH_VISUAL_DRAW",
           "P2_WATERWRAITH_VISUAL_PLAY", "P2_WATERWRAITH_WINDOW",
           "P2_WATERWRAITH_HOST_PASS", "PASS WATERWRAITH_RUNTIME")


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
    for marker in MARKERS:
        if marker not in text:
            errors.append(f"missing marker: {marker}")
    if not re.search(r"^P2_WATERWRAITH_WINDOW\s+size=960x540\s+pos=-?\d+,-?\d+\s*$", text,
                     flags=re.MULTILINE):
        errors.append("missing 960x540 window marker")
    ready = re.search(r"^P2_WATERWRAITH_VISUAL_READY\s+species=(\d+)\s+clips=(\d+)\s*$", text,
                      flags=re.MULTILINE)
    if not ready:
        errors.append("missing visual READY marker")
    elif int(ready.group(1)) != 2:
        errors.append(f"expected 2 species: {ready.groups()}")
    draw = re.search(r"^P2_WATERWRAITH_VISUAL_DRAW\s+species=(\d+)\s*$", text, flags=re.MULTILINE)
    if not draw:
        errors.append("missing visual DRAW marker")
    elif int(draw.group(1)) != 1:
        errors.append(f"expected per-species draw marker: {draw.groups()}")
    host = re.search(r"^P2_WATERWRAITH_HOST_PASS\s+ticks=(\d+)\s+distance=([\d.]+)\s+"
                     r"roll=([\d.]+)\s+phase=(\w+)\s*$", text, flags=re.MULTILINE)
    if not host:
        errors.append("missing host PASS marker")
    elif float(host.group(2)) <= 0.0 or float(host.group(3)) <= 0.0:
        errors.append(f"roller did not travel/roll: {host.groups()}")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-worktree", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--room", type=Path, required=True)
    parser.add_argument("--visual-stage", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    record = {"schema": 1, "arguments": {key: str(value) if isinstance(value, Path) else value
              for key, value in vars(args).items()}, "status": "failed", "errors": []}
    run = None
    try:
        root = args.root_worktree.resolve()
        assets, room, fixture, output = (args.assets.resolve(), args.room.resolve(),
                                         args.fixture.resolve(), args.output.resolve())
        visual_stage = args.visual_stage.resolve()
        provenance_path, provenance, executable, executable_hash = fixture_provenance(fixture)
        prepare = load_preview_prepare(root)
        run = prepare(assets, room, output)
        record["run"] = str(run)
        profile = visual_stage / "p2-waterwraith-visual.txt"
        copy_new(profile, run / "p2-waterwraith-visual.txt")
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
        record["fixture"] = {"provenance": file_record(provenance_path),
                             "provenance_status": provenance.get("status"),
                             "executable": {"path": str(executable), "sha256": executable_hash}}
        record["inputs"] = {"profile": file_record(run / "p2-waterwraith-visual.txt")}
        for name in ("room.mod", "room.ini", "treasure.mod"):
            record["inputs"][name] = file_record(room / name)
        record["inputs"]["preview_helper"] = file_record(root / "scripts" / "preview_pikmin2_room.py")
        command = [str(executable), "--experimental-pikmin2-room"]
        record["command"] = command
        result = subprocess.run(command, cwd=run, env=dict(os.environ), timeout=75,
                                text=True, encoding="utf-8", errors="replace", capture_output=True)
        (run / "stdout.log").write_text(result.stdout, encoding="utf-8")
        (run / "stderr.log").write_text(result.stderr, encoding="utf-8")
        record["subprocess"] = {"returncode": result.returncode, "timeout_seconds": 75,
                                "stdout": file_record(run / "stdout.log"),
                                "stderr": file_record(run / "stderr.log")}
        errors = verify_log(result.stdout + "\n" + result.stderr)
        record["verification"] = {"errors": errors}
        capture = run / "waterwraith-visual.ppm"
        if not capture.is_file():
            errors.append("missing capture: waterwraith-visual.ppm")
        elif capture.stat().st_size < 100000:
            errors.append("trivial capture: waterwraith-visual.ppm")
        else:
            record["captures"] = {"waterwraith-visual.ppm": file_record(capture)}
        if result.returncode != 0:
            errors.append(f"fixture exit code {result.returncode}")
        record["errors"].extend(errors)
        if not errors:
            record["status"] = "passed"
    except subprocess.TimeoutExpired as error:
        record["errors"].append("fixture timed out after 75 seconds")
        if run is not None:
            for name in ("stdout.log", "stderr.log"):
                value = getattr(error, name.split(".")[0], None)
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
