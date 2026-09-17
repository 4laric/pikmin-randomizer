"""NARI stage-row checker: pins vs live decode + fixture-log observer (#769).

EXPECTED rows mirror the native module pins, themselves decoded live from
#705 (02tile) and #743 (03toy) and cross-checked against the P0 catalogue:
- 02tile: ui 4, order 19, 2 floors 200+150 s, bitter 0 / spicy 5, row0 50.
- 03toy: ui 5, order 2, 2 floors 100+150 s, bitter 2 / spicy 2, row2 100.
Boot pops equal the roster sums (50 / 100). Pure checker: launches nothing.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

EXPECTED = {
    "ch_NARI_02tile": {
        "cave_id": "ch_NARI_02tile", "ui_index": 4, "table_order": 19,
        "floors": 2, "floor_seconds": [200.0, 150.0],
        "roster": [[0, 0, 50], [0, 0, 0], [0, 0, 0], [0, 0, 0],
                   [0, 0, 0], [0, 0, 0], [0, 0, 0]],
        "bitter_sprays": 0, "spicy_sprays": 5, "boot_pops": 50,
        "source": "#705 landing adapter",
    },
    "ch_NARI_03toy": {
        "cave_id": "ch_NARI_03toy", "ui_index": 5, "table_order": 2,
        "floors": 2, "floor_seconds": [100.0, 150.0],
        "roster": [[0, 0, 0], [0, 0, 0], [0, 0, 100], [0, 0, 0],
                   [0, 0, 0], [0, 0, 0], [0, 0, 0]],
        "bitter_sprays": 2, "spicy_sprays": 2, "boot_pops": 100,
        "source": "#743 gap record",
    },
}

RESOLVED_RE = re.compile(r"P2_NARI_STAGE_RESOLVED cave=(\S+) ui_index=(\d+) floors=(\d+)")
POP_RE = re.compile(r"P2_NARI_STAGE_BOOT_POP cave=(\S+) pops=(\d+)")
ERROR_RE = re.compile(r"P2_NARI_STAGE_ERROR missing_stage ui=(\d+)")
DONE_RE = re.compile(r"P2_NARI_STAGE_TABLE_DONE stages=(\d+)")
SELFTEST_RE = re.compile(r"P2_NARI_STAGE_GUARD_SELFTEST_PASS rows=(\d+)")
REFUSED_RE = re.compile(r"P2_NARI_STAGE_REFUSED reason=(\S+)")
CAPTAIN_DOWN_RE = re.compile(r"P2_FIXTURE_CAPTAIN_DOWN")


def check_pins(rows: dict) -> list:
    """Compare decoded rows against EXPECTED; returns problem strings."""
    problems = []
    for key, want in EXPECTED.items():
        got = rows.get(key)
        if got is None:
            problems.append("missing row " + key)
            continue
        for field in ("cave_id", "ui_index", "table_order", "floors",
                      "floor_seconds", "roster", "bitter_sprays", "spicy_sprays"):
            if got.get(field) != want[field]:
                problems.append("drift %s.%s" % (key, field))
    for key in rows:
        if key not in EXPECTED:
            problems.append("unexpected row " + key)
    return problems


def validate_log(text: str) -> dict:
    """Classify a fixture log; both rows must resolve with exact pops."""
    verdict: dict = {"resolved": {}, "pops": {}, "errors": [], "refused": "",
                     "selftest": False, "captain_down": False, "done": 0,
                     "passed": False, "failures": []}
    if CAPTAIN_DOWN_RE.search(text):
        verdict["captain_down"] = True
    for m in RESOLVED_RE.finditer(text):
        verdict["resolved"][m.group(1)] = (int(m.group(2)), int(m.group(3)))
    for m in POP_RE.finditer(text):
        verdict["pops"][m.group(1)] = int(m.group(2))
    for m in ERROR_RE.finditer(text):
        verdict["errors"].append(int(m.group(1)))
    m = REFUSED_RE.search(text)
    if m:
        verdict["refused"] = m.group(1)
    if SELFTEST_RE.search(text):
        verdict["selftest"] = True
    m = DONE_RE.search(text)
    if m:
        verdict["done"] = int(m.group(1))
    for key, want in EXPECTED.items():
        got = verdict["resolved"].get(key)
        if got != (want["ui_index"], want["floors"]):
            verdict["failures"].append("unresolved-or-drift " + key)
        elif verdict["pops"].get(key) != want["boot_pops"]:
            verdict["failures"].append("pop-mismatch " + key)
    if verdict["captain_down"]:
        verdict["failures"].append("captain-down")
    if verdict["errors"]:
        verdict["failures"].append("row-errors")
    verdict["passed"] = not verdict["failures"] and verdict["done"] == 2
    return verdict


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(description="Check NARI pins / validate fixture log")
    parser.add_argument("--log", type=Path, default=None)
    parser.add_argument("--json", default="")
    args = parser.parse_args(argv)
    if args.log is None:
        parser.error("--log required")
    verdict = validate_log(args.log.read_text(encoding="utf-8", errors="replace"))
    print("resolved=%s pops=%s done=%d captain_down=%s passed=%s" % (
        sorted(verdict["resolved"]), verdict["pops"], verdict["done"],
        verdict["captain_down"], verdict["passed"]))
    for failure in verdict["failures"]:
        print("FAIL " + failure)
    if args.json:
        Path(args.json).write_text(json.dumps(verdict, indent=1), encoding="utf-8")
    print("VERDICT " + ("PASS both rows resolve" if verdict["passed"] else "NOT-READY"))
    return 0 if verdict["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
