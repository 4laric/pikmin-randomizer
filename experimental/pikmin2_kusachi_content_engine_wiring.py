#!/usr/bin/env python3
"""Wiring-log verifier for lane kusachi-content-engine-wiring-native (#728).

Maps a headed fixture log to honest verdicts for the kusachi content wiring.
A PASS is reported only when a P2_CHALLENGE_CONTENT_WIRED line shows a
positive bound count with no failure/interruption marker; anything else is
not a pass. Stdlib only.
"""
import argparse
import json
import re
import sys

WIRED_RE = re.compile(r"P2_CHALLENGE_CONTENT_WIRED wired=(\d+) total=(\d+)")
PASS_LINE = "PASS KUSACHI_CONTENT_WIRING"
FAILURE_MARKERS = (
    "FAIL KUSACHI_CONTENT_WIRING",
    "P2_FIXTURE_CAPTAIN_DOWN",
)


def verify_run_log(log_text):
    """Map the headed run log to wiring verdicts. Never invents a PASS."""
    best = 0
    total = 0
    for match in WIRED_RE.finditer(log_text):
        wired = int(match.group(1))
        if wired > best:
            best = wired
            total = int(match.group(2))
    failures = [m for m in FAILURE_MARKERS if m in log_text]
    overall_pass = (best > 0 and not failures
                    and PASS_LINE in log_text)
    return {
        "content_wired": best,
        "squad_total": total,
        "failure_markers": failures,
        "overall_pass": overall_pass,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Kusachi content wiring-log verifier")
    parser.add_argument("--log", required=True)
    args = parser.parse_args(argv)
    with open(args.log, encoding="utf-8", errors="replace") as f:
        result = verify_run_log(f.read())
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0 if result["overall_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
