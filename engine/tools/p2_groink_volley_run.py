"""Run and verify the private six-shell Groink fixture in a fresh room overlay."""

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
import uuid


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


def verify_log(text, expected_contact):
    receipts = re.findall(
        r"^P2_GROINK_VOLLEY_IMPACT\s+tick=\d+\s+slot=(\d+)\s+primary=(\d+)\s+"
        r"reason=(\d+)\s+xyz=", text, flags=re.MULTILINE)
    errors = []
    if "PASS GROINK_VOLLEY_RUNTIME" not in text:
        errors.append("missing runtime PASS marker")
    if len(receipts) != 6:
        errors.append(f"expected 6 terminal receipts, got {len(receipts)}")
    slots = [int(slot) for slot, _, _ in receipts]
    primary = [int(value) for _, value, _ in receipts]
    reasons = [int(reason) for _, _, reason in receipts]
    if set(slots) != set(range(6)) or len(set(slots)) != 6:
        errors.append(f"terminal slots were not distinct 0..5: {slots}")
    if sum(primary) != 2:
        errors.append(f"expected two primary receipts, got {sum(primary)}")
    if any(value not in (0, 1) for value in primary) or any(reason not in (1, 2) for reason in reasons):
        errors.append("invalid primary flag or non-terrain terminal")
    # P2GroinkTerminalReason is None=0, Floor=1, Wall=2, OutOfRange=3, Invalid=4.
    expected_reason = {"floor": 1, "wall": 2}[expected_contact]
    if expected_reason not in reasons:
        errors.append(f"expected at least one {expected_contact} terminal, got reasons {reasons}")
    pass_match = re.search(r"^P2_GROINK_VOLLEY_PASS\s+emitted=(\d+)\s+impacts=(\d+)\s+"
                           r"primary=(\d+)\s+reset=(\d+)\s*$", text, flags=re.MULTILINE)
    if not pass_match:
        errors.append("missing volley accounting/reset marker")
    elif tuple(map(int, pass_match.groups())) != (6, 6, 2, 1):
        errors.append(f"unexpected volley accounting: {pass_match.groups()}")
    return {"receipts": [{"slot": slot, "primary": value, "reason": reason}
                          for slot, value, reason in receipts],
            "errors": errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-worktree", type=Path, required=True,
                        help="Python repository containing scripts/preview_pikmin2_room.py")
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--room", type=Path, required=True,
                        help="Converted room directory accepted by preview.prepare")
    parser.add_argument("--stage", type=Path, required=True,
                        help="Groink stage containing p2-groink-arena.txt and assets")
    parser.add_argument("--fixture", type=Path, required=True,
                        help="Built fixture directory containing fixture.exe and provenance.json")
    parser.add_argument("--output", type=Path, required=True,
                        help="Parent directory for the fresh run overlay")
    parser.add_argument("--expected-contact", choices=("floor", "wall"), required=True)
    args = parser.parse_args()

    record = {"schema": 1, "arguments": {key: str(value) if isinstance(value, Path) else value
              for key, value in vars(args).items()}, "status": "failed", "errors": []}
    run = None
    try:
        root = args.root_worktree.resolve()
        assets, room, stage, fixture, output = (args.assets.resolve(), args.room.resolve(),
                                                 args.stage.resolve(), args.fixture.resolve(),
                                                 args.output.resolve())
        provenance_path, provenance, executable, executable_hash = fixture_provenance(fixture)
        prepare = load_preview_prepare(root)
        run = prepare(assets, room, output)
        record["run"] = str(run)
        profile_source = stage / "p2-groink-arena.txt"
        model_source = stage / "assets" / "dataDir" / "courses" / "pikmin2room" / "groink_attack.mod"
        profile_target = run / "p2-groink-arena.txt"
        model_target = run / "assets" / "dataDir" / "courses" / "pikmin2room" / "groink_attack.mod"
        copy_new(model_source, model_target)
        copy_new(profile_source, profile_target)
        record["fixture"] = {"provenance": file_record(provenance_path),
                             "provenance_status": provenance.get("status"),
                             "executable": {"path": str(executable), "sha256": executable_hash}}
        record["inputs"] = {"profile": file_record(profile_target), "model": file_record(model_target)}
        for name in ("room.mod", "room.ini", "treasure.mod"):
            record["inputs"][name] = file_record(room / name)
        record["inputs"]["preview_helper"] = file_record(root / "scripts/preview_pikmin2_room.py")
        command = [str(executable), "--experimental-pikmin2-room"]
        record["command"] = command
        # Inherit the caller's PATH and all other environment values unchanged.
        result = subprocess.run(command, cwd=run, env=dict(os.environ), timeout=75,
                                text=True, encoding="utf-8", errors="replace",
                                capture_output=True)
        (run / "stdout.log").write_text(result.stdout, encoding="utf-8")
        (run / "stderr.log").write_text(result.stderr, encoding="utf-8")
        record["subprocess"] = {"returncode": result.returncode, "timeout_seconds": 75,
                                "stdout": file_record(run / "stdout.log"),
                                "stderr": file_record(run / "stderr.log")}
        verification = verify_log(result.stdout + "\n" + result.stderr, args.expected_contact)
        record["verification"] = verification
        captures = {}
        for name in ("groink-volley-flight.ppm", "groink-volley-terminal.ppm"):
            path = run / name
            if not path.is_file():
                verification["errors"].append(f"missing capture: {name}")
            else:
                captures[name] = file_record(path)
        record["captures"] = captures
        spread = run / "groink-volley-spread.ppm"
        if spread.is_file():
            captures[spread.name] = file_record(spread)
        if result.returncode != 0:
            verification["errors"].append(f"fixture exit code {result.returncode}")
        record["errors"].extend(verification["errors"])
        if not verification["errors"]:
            record["status"] = "passed"
    except subprocess.TimeoutExpired as error:
        record["errors"].append("fixture timed out after 75 seconds")
        if run is not None:
            for name, value in (("stdout.log", error.stdout), ("stderr.log", error.stderr)):
                if isinstance(value, bytes):
                    value = value.decode("utf-8", errors="replace")
                (run / name).write_text(value or "", encoding="utf-8")
    except Exception as error:
        record["errors"].append(str(error))
        record["traceback"] = traceback.format_exc()
    finally:
        destination = (run if run is not None else args.output.resolve() / ("failed-" + uuid.uuid4().hex)) / "verification.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
        print(destination)
    if record["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
