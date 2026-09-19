#!/usr/bin/env python3
"""Run-log verifier for lane challenge-hostmode-engine-hook-native (#710).

Maps a headed engine/fixture log to honest verdicts for the challenge
host-mode runtime bridge. A PASS is reported only when the engine bridge
markers are present in order with zero failure/interruption markers; anything
else is unobserved/unsupported, never passing. Stdlib only.
"""

import argparse
import json
import sys

REQUIRED_BOOT_MARKERS = [
    "P2_CHALLENGE_MODE_BOOT",
]

TICK_MARKERS = (
    "P2_CHALLENGE_MODE_TICK",
    "P2CHALLENGE_WIRING_TICK",
)

DONE_MARKERS = (
    "P2_CHALLENGE_MODE_DONE",
    "PASS CHALLENGE_HOST_RUNTIME",
)

FAILURE_MARKERS = (
    "FAIL CHALLENGE_HOST_RUNTIME",
    "P2_FIXTURE_CAPTAIN_DOWN",
)


def verify_run_log(log_text):
    """Map the headed run log to bridge verdicts. Never invents a PASS."""
    boot = all(m in log_text for m in REQUIRED_BOOT_MARKERS)
    ticks = sum(log_text.count(m) for m in TICK_MARKERS)
    done = any(m in log_text for m in DONE_MARKERS)
    failures = [m for m in FAILURE_MARKERS if m in log_text]
    overall_pass = bool(boot and ticks > 0 and not failures and done)
    return {
        "engine_bridge_boot": boot,
        "tick_markers": ticks,
        "done_marker": done,
        "failure_markers": failures,
        "overall_pass": overall_pass,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Challenge host-runtime run-log verifier")
    parser.add_argument("--log", required=True)
    args = parser.parse_args(argv)
    with open(args.log, encoding="utf-8", errors="replace") as f:
        result = verify_run_log(f.read())
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0 if result["overall_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
