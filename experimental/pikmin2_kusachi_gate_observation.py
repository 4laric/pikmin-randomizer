"""Kusachi six-gate + P2 persistence observation adapter (lane kusachi-gate-persistence-observation, #818).

Read-only log adjudicator for the EXISTING verified wiring fixture
(native/tools/p2_kusachi_content_wiring_fixture.cpp at pinned native 704bad6c;
callsites pc_port/pc_p2_challenge_content.cpp anonymous update() line 90 and the
fixture main() line 203, read-only). It parses one headed fixture run log for the
wiring/stage markers, the six arena-gate evidence markers and the
save/reload/retry/re-entry markers where the port emits them, then adjudicates
each gate as observed or honest UNTESTED with the exact blocker. It never edits
engine/source, builds, launches or claims gameplay acceptance; fail-closed on
missing or malformed logs. No ADMIT.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

GATES = ("identity_spawn", "movement_animation", "attacks_receivers",
         "death_corpse", "transport_reward", "cleanup_reentry")

WIRED = "P2_CHALLENGE_CONTENT_WIRED"
STAGE = "P2_KUSACHI_CONTENT_WIRING_STAGE"
PASS = "PASS KUSACHI_CONTENT_WIRING"
FAIL = "FAIL KUSACHI_CONTENT_WIRING"
TIMEOUT = "FAIL KUSACHI_CONTENT_WIRING timeout"
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"
SELFTEST = "P2_KUSACHI_CONTENT_WIRING_SELFTEST_PASS"

SAVE_MARKS = ("P2_KUSACHI_SAVE", "P2_KUSACHI_RELOAD", "P2_KUSACHI_RETRY", "P2_KUSACHI_REENTRY")


class ObservationError(ValueError):
    """Fail-closed refusal."""


def parse_log(text):
    if not isinstance(text, str) or not text.strip():
        raise ObservationError("empty run log")
    lines = text.splitlines()
    found = {
        "wired": any(WIRED in l for l in lines),
        "stage": any(STAGE in l for l in lines),
        "passed": any((PASS in l) and ("timeout" not in l) for l in lines),
        "failed": any(FAIL in l for l in lines),
        "timeout": any(TIMEOUT in l for l in lines),
        "captain_down": any(CAPTAIN_DOWN in l for l in lines),
        "selftest": any(SELFTEST in l for l in lines),
        "save_marks": sorted({m for m in SAVE_MARKS for l in lines if m in l}),
    }
    return found


def adjudicate(found):
    """Map parsed markers onto per-gate verdicts. Observed only on evidence."""
    gates = {}
    if found["captain_down"]:
        for g in GATES:
            gates[g] = {"status": "BLOCKED", "detail": "CAPTAIN_DOWN trip; observation interrupted"}
        return gates
    if found["timeout"] or (found["failed"] and not found["passed"]):
        for g in GATES:
            gates[g] = {"status": "BLOCKED", "detail": "fixture did not pass; no gate observed"}
        return gates
    if not (found["wired"] and found["stage"] and found["passed"]):
        for g in GATES:
            gates[g] = {"status": "UNTESTED",
                        "detail": "wiring/stage/pass markers incomplete; exact blocker: engine wiring not observed"}
        return gates
    gates["identity_spawn"] = {"status": "observed",
        "detail": "P2_CHALLENGE_CONTENT_WIRED + stage marker + PASS with live run"}
    for g in ("movement_animation", "attacks_receivers", "death_corpse",
              "transport_reward", "cleanup_reentry"):
        gates[g] = {"status": "UNTESTED",
                    "detail": "wiring observed; gate-specific combat/death/corpse/re-entry evidence not in this log"}
    return gates


def persistence(found):
    marks = found["save_marks"]
    if len(marks) == 4:
        return {"status": "observed",
                "detail": "save/reload/retry/re-entry markers all present: " + ",".join(marks)}
    missing = [m for m in SAVE_MARKS if m not in marks]
    return {"status": "UNTESTED",
            "detail": "persistence markers incomplete; missing: " + ",".join(missing)}


def verdict(log_path):
    text = Path(log_path).read_text(encoding="utf-8", errors="replace")
    found = parse_log(text)
    gates = adjudicate(found)
    return {"schema": 1, "log": str(log_path), "markers": found,
            "gates": gates, "persistence": persistence(found), "admit": False}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--log", required=True)
    ap.add_argument("--out", required=False)
    args = ap.parse_args(argv)
    result = verdict(args.log)
    text = json.dumps(result, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
