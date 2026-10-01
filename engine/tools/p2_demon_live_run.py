"""Execute the private Demon live-capture fixture with provenance records."""
import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
from pathlib import Path

MODES = ("capture", "ownerlost", "replacement", "reset", "stageexit", "forced", "refusal")

def digest(path):
    path = path.resolve()
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "size": path.stat().st_size}

def main():
    p = argparse.ArgumentParser()
    for name in ("root", "assets", "room", "fixture", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    args = p.parse_args()
    exe = args.fixture / "fixture.exe"
    provenance = args.fixture / "provenance.json"
    manifest = json.loads(provenance.read_text(encoding="utf-8"))
    actual = digest(exe)
    expected = next(v for k, v in manifest["artifacts"].items() if Path(k).name == "fixture.exe")
    if manifest.get("status") != "built" or actual["sha256"] != expected["sha256"]:
        raise ValueError("fixture executable fails its built provenance")
    helper = args.root / "scripts" / "preview_pikmin2_room.py"
    spec = importlib.util.spec_from_file_location("preview", helper)
    preview = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(preview)
    passed = True
    for mode in MODES:
        session = preview.prepare(args.assets.resolve(), args.room.resolve(), args.output.resolve())
        env = dict(os.environ, DEMON_FIXTURE_MODE=mode)
        record = {"mode": mode, "fixture": actual, "provenance": digest(provenance),
                  "runner": digest(Path(__file__)), "helper": digest(helper), "status": "failed"}
        try:
            run = subprocess.run([str(exe.resolve()), "--experimental-pikmin2-room"], cwd=session,
                env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=75)
            stdout, stderr = session / "stdout.log", session / "stderr.log"
            stdout.write_text(run.stdout, encoding="utf-8")
            stderr.write_text(run.stderr, encoding="utf-8")
            record.update(returncode=run.returncode, stdout=digest(stdout), stderr=digest(stderr))
            if run.returncode == 0 and "PASS DEMON_LIVE" in run.stdout:
                record["status"] = "passed_scoped_runtime"
            else:
                passed = False
        except Exception as exc:
            record["error"] = str(exc)
            passed = False
        (session / "verification.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(mode, record["status"], session, flush=True)
    return 0 if passed else 1

if __name__ == "__main__":
    raise SystemExit(main())