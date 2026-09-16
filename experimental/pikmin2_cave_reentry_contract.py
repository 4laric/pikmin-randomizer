'''Contract checker for the cave cleanup_reentry provider (#488 review).

Review-only tool (lane cave-reentry-provider-contract-review). Two checks,
both pure presence/sequence assertions on supplied inputs:

- check_provider(native_root): the lane-11 checkpoint provider artifacts
  exist with their contract markers (P2_CAVE_RESTORE in
  engine/pc_port/pc_p2_cave.cpp; P2_LANE11_WRITE / P2_CAVE_TRANSFER_3 /
  PASS P2_LANE11_RESTORE in experimental/pikmin2_cave_restart_runtime.py;
  restart runtime tests present; P2_CAVE_TRANSFER_3 schema assert in
  engine/tools/test_p2_cave_transfer.cpp).
- check_runlog(text, staged): a candidate re-entry run log shows the
  write/read marker sequence IN ORDER (WRITE ok=1, TRANSFER_3 header,
  >=1 RESTORE line, PASS P2_LANE11_RESTORE). The staged flag is recorded
  verbatim from the caller and never inferred; it cannot prove natural
  gameplay.

No invented values, no gameplay claims, no gate flips. Stdlib only.
'''
import argparse
import json
import re
from pathlib import Path

CAVE_CPP = "engine/pc_port/pc_p2_cave.cpp"
RESTART_RUNTIME = "experimental/pikmin2_cave_restart_runtime.py"
RESTART_TESTS = "tests/test_pikmin2_cave_restart_runtime.py"
TRANSFER_TEST = "engine/tools/test_p2_cave_transfer.cpp"

RESTORE_MARKER = "P2_CAVE_RESTORE"
WRITE_MARKER = "P2_LANE11_WRITE"
TRANSFER_MARKER = "P2_CAVE_TRANSFER_3"
PASS_MARKER = "PASS P2_LANE11_RESTORE"


def check_provider(native_root):
    """Return {checks, passed} for a native source tree path."""
    root = Path(native_root)
    checks = {}

    def read(rel):
        p = root / rel
        return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""

    checks["restore_emitter"] = RESTORE_MARKER in read(CAVE_CPP)
    runtime = read(RESTART_RUNTIME)
    checks["restart_validator"] = all(m in runtime for m in
                                      (WRITE_MARKER, TRANSFER_MARKER, PASS_MARKER))
    checks["restart_tests"] = bool(read(RESTART_TESTS).strip())
    checks["transfer_schema"] = TRANSFER_MARKER in read(TRANSFER_TEST)
    return {"checks": checks, "passed": all(checks.values())}


def check_runlog(text, staged):
    """Validate a candidate re-entry run log marker sequence.

    staged is True/False/None (unknown): recorded verbatim, never inferred.
    A staged True result proves the plumbing ran, never natural gameplay.
    """
    lines = text.splitlines()
    def first(pattern):
        for i, line in enumerate(lines):
            if re.search(pattern, line):
                return i
        return None
    w = first(r"P2_LANE11_WRITE ok=1")
    t = first(r"^P2_CAVE_TRANSFER_3$")
    restores = [i for i, line in enumerate(lines)
                if "P2_CAVE_RESTORE" in line]
    p = first(r"^PASS P2_LANE11_RESTORE$")
    ordered = (w is not None and t is not None and restores and p is not None
               and w < t < restores[0] and restores[-1] < p)
    checks = {
        "write_confirmed": w is not None,
        "transfer_schema": t is not None,
        "restore_observed": bool(restores),
        "restore_pass": p is not None,
        "sequence_ordered": bool(ordered),
    }
    return {"checks": checks, "passed": all(checks.values()),
            "restore_count": len(restores), "staged": staged}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", help="native source tree to inspect")
    parser.add_argument("--log", help="candidate re-entry run log to validate")
    parser.add_argument("--staged", choices=("yes", "no", "unknown"), default="unknown",
                        help="whether the run inputs were staged (recorded verbatim)")
    args = parser.parse_args(argv)
    if not args.native and not args.log:
        parser.error("supply --native and/or --log")
    report = {}
    if args.native:
        report["provider"] = check_provider(args.native)
    if args.log:
        staged = {"yes": True, "no": False, "unknown": None}[args.staged]
        report["runlog"] = check_runlog(
            Path(args.log).read_text(encoding="utf-8", errors="replace"), staged)
    print(json.dumps(report, indent=1))
    parts = [v["passed"] for v in report.values()]
    raise SystemExit(0 if all(parts) else 1)


if __name__ == "__main__":
    main()