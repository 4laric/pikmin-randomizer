#!/usr/bin/env python3
"""Run-log verifier for lane impact-fixture-gating-fix-native (#739).

Maps a headed fixture log to honest verdicts for the #698 gating fix. It never
claims what the log does not show. Two acceptable terminal states:
  * attributed stall: a P2_CHALLENGE_GATE_DIAG line names the holding gate
    (the #698 deliverable - the freeze is no longer silent);
  * squad spawn: P2_CHALLENGE_SQUAD / BOOT / PASS markers observed.
A silent freeze (neither) is a failure. Any CAPTAIN_DOWN is a failure.
Stdlib only.
"""
import argparse
import json
import re
import sys

GATE_DIAG_RE = re.compile(r"P2_CHALLENGE_GATE_DIAG gate=(\w+)")
PARK_ALIVE_RE = re.compile(r"P2_CHALLENGE_PARK_ALIVE pikis=(\d+)")
SQUAD_RE = re.compile(r"P2_CHALLENGE_SQUAD pikis=(\d+)")
BOOT_MARKERS = ("P2_CHALLENGE_BOOT", "PASS P2_CHALLENGE_GUARDED_BOOT")
FAILURE_MARKERS = ("P2_FIXTURE_CAPTAIN_DOWN",)


def verify_run_log(log_text):
    """Map the headed run log to fix verdicts. Never invents a PASS."""
    gates = sorted(set(GATE_DIAG_RE.findall(log_text)))
    park = [int(v) for v in PARK_ALIVE_RE.findall(log_text)]
    squad = [int(v) for v in SQUAD_RE.findall(log_text)]
    boot = any(m in log_text for m in BOOT_MARKERS)
    failures = [m for m in FAILURE_MARKERS if m in log_text]
    attributed = bool(gates)
    spawned = bool(squad and max(squad) > 0)
    overall_pass = (spawned or attributed) and not failures and bool(
        park or squad or gates)
    return {
        "gate_diagnostics": gates,
        "park_alive": park[-1] if park else None,
        "squad_counts": squad[-3:] if squad else [],
        "boot_markers": boot,
        "failure_markers": failures,
        "attributed_stall": attributed and not spawned,
        "squad_spawned": spawned,
        "overall_pass": overall_pass,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Impact gating-fix run-log verifier")
    parser.add_argument("--log", required=True)
    args = parser.parse_args(argv)
    with open(args.log, encoding="utf-8", errors="replace") as f:
        result = verify_run_log(f.read())
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0 if result["overall_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
