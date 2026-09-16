"""Prepare and run the private BigTreasure slice-3 ordinary-loop fixture.

Buckets (#246): a parameterized reproduction runner that stages a fresh room
overlay, installs the host profile + event table, and runs the slice-3 fixture
at --experimental-pikmin2-room. Mirrors tools/p2_bigtreasure_runtime_run.py's
CLI shape: all absolute inputs are caller-supplied, no lane worktree paths.

    py -3.12 tools/p2_bigtreasure_slice3_run.py \
        --root-worktree <repo> --assets <P1-assets> --room <converted-room> \
        --host-stage <dir-with-p2-bigtreasure-host.txt> \
        --visual-stage <stage-dir-with-p2_bigtreasure_events.txt> \
        --fixture <built-fixture-dir> --output <out-parent>
"""
import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-worktree", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--room", type=Path, required=True)
    parser.add_argument("--host-stage", type=Path, required=True)
    parser.add_argument("--visual-stage", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()

    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ["PIKMIN_P2_ROOM_WINDOW"] = "960x540"

    preview = args.root_worktree / "scripts" / "preview_pikmin2_room.py"
    spec = importlib.util.spec_from_file_location("p2_preview", str(preview))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    run = module.prepare(args.assets, args.room, args.output)
    print("RUN", run, flush=True)

    host = run / "p2-bigtreasure-host.txt"
    if not host.exists():
        host.write_bytes((args.host_stage / "p2-bigtreasure-host.txt").read_bytes())
    events = run / "p2_bigtreasure_events.txt"
    if not events.exists():
        events.write_bytes((args.visual_stage / "p2_bigtreasure_events.txt").read_bytes())

    executable = args.fixture / "fixture.exe"
    result = subprocess.run([str(executable), "--experimental-pikmin2-room"],
                            cwd=run, env=dict(os.environ), timeout=args.timeout,
                            text=True, encoding="utf-8", errors="replace",
                            capture_output=True)
    (run / "stdout.log").write_text(result.stdout, encoding="utf-8")
    (run / "stderr.log").write_text(result.stderr, encoding="utf-8")
    print("RETURNCODE", result.returncode, flush=True)
    print(result.stdout[-8000:])
    print(result.stderr[-1500:])
    return 0 if result.returncode == 0 else result.returncode


if __name__ == "__main__":
    sys.exit(main())
