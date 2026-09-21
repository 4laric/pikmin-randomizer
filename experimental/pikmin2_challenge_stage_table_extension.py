"""Challenge stage extension table pins + log validator (#730).

Lane challenge-stage-table-extension-native. Pins for ch_ABEM_LeafChappy
(#550) and ch_NARI_02tile (#537) mirrored from
docs/PIKMIN_CONTENT_IMPORT_LANES.json; validates fixture native.log marker
chains. Stages nothing, launches nothing, emits no markers.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROWS = {
    "ch_ABEM_LeafChappy": {
        "cave_path": "user/Mukki/mapunits/caveinfo/ch_ABEM_LeafChappy.txt",
        "sha256": "49cc9076cede949786025b3bcd08ce60362096d8fe8f8b5330c725de4acd2baf",
        "ui_index": 17, "table_order": 4, "floors": 2,
        "floor_seconds": [85.0, 100.0],
        "roster": [[10, 0, 0], [10, 0, 0], [10, 0, 0],
                   [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
        "bitter": 1, "spicy": 1, "legacy": 400.0, "treasure": 11,
    },
    "ch_NARI_02tile": {
        "cave_path": "user/Mukki/mapunits/caveinfo/ch_NARI_02tile.txt",
        "sha256": "d047060c7965e501d23b23e2850b5f58e327d40b452d70710149ea4b41479ea6",
        "ui_index": 4, "table_order": 19, "floors": 2,
        "floor_seconds": [200.0, 150.0],
        "roster": [[0, 0, 50], [0, 0, 0], [0, 0, 0], [0, 0, 0],
                   [0, 0, 0], [0, 0, 0], [0, 0, 0]],
        "bitter": 0, "spicy": 5, "legacy": 0.0, "treasure": 0,
    },
}

RESOLVED_RE = re.compile(
    r"P2_CHALLENGE_STAGE_EXT_RESOLVED cave=(\S+) ui_index=(\d+) table_order=(\d+) "
    r"floors=(\d+) roster_total=(\d+) timers=([\d.]+),([\d.]+) sprays=(\d+),(\d+) "
    r"legacy=([\d.]+) treasure=(\d+) sha=(\S+)")
ENGINE_UNTOUCHED_RE = re.compile(
    r"P2_CHALLENGE_STAGE_EXT_ENGINE_UNTOUCHED cave=ch_NARI_01kusachi ui_index=3")
FALLTHROUGH_RE = re.compile(
    r"P2_CHALLENGE_STAGE_EXT_FALLTHROUGH cave=(\S+) ui_index=(\d+)")
WINDOW_RE = re.compile(
    r"P2_CHALLENGE_STAGE_EXT_WINDOW size=960x540 .* centered=1")
READY_RE = re.compile(r"P2_CHALLENGE_STAGE_EXT_READY observed=(\d+)")
GATES_RE = re.compile(
    r"P2_CHALLENGE_STAGE_EXT_GATES all=UNTESTED content_wired=0")
PASS_RE = re.compile(r"^PASS CHALLENGE_STAGE_TABLE_EXT$", re.MULTILINE)
REFUSED_RE = re.compile(r"P2_CHALLENGE_STAGE_EXT_REFUSED reason=(\S+)")
CAPTAIN_DOWN_RE = re.compile(r"P2_FIXTURE_CAPTAIN_DOWN")


def validate(text: str, cave: str) -> dict:
    """Validate a fixture log for one stage key. JSON-serializable verdict."""
    verdict: dict = {"cave": cave, "resolved": False, "engine_untouched": False,
                     "fallthrough_wired": False, "window": False, "ready": False,
                     "gates_untested": False, "passed": False, "captain_down": False,
                     "refusals": [], "failures": []}
    lines = text.splitlines()
    for line in lines:
        if CAPTAIN_DOWN_RE.search(line):
            verdict["captain_down"] = True
        m = REFUSED_RE.search(line)
        if m:
            verdict["refusals"].append(m.group(1))
    if verdict["captain_down"]:
        verdict["failures"].append("captain-down")
        return verdict
    if verdict["refusals"]:
        verdict["failures"].append("refused:" + ",".join(verdict["refusals"]))
        return verdict
    pin = ROWS.get(cave)
    if pin is None:
        verdict["failures"].append("unknown-cave")
        return verdict
    m = RESOLVED_RE.search(text)
    if not m or m.group(1) != cave:
        verdict["failures"].append("no-resolved-marker")
        return verdict
    got = {"ui_index": int(m.group(2)), "table_order": int(m.group(3)),
           "floors": int(m.group(4)), "roster_total": int(m.group(5)),
           "timers": [float(m.group(6)), float(m.group(7))],
           "sprays": [int(m.group(8)), int(m.group(9))],
           "legacy": float(m.group(10)), "treasure": int(m.group(11)),
           "sha8": m.group(12)}
    roster_total = sum(sum(row) for row in pin["roster"])
    checks = [
        ("ui_index", got["ui_index"] == pin["ui_index"]),
        ("table_order", got["table_order"] == pin["table_order"]),
        ("floors", got["floors"] == pin["floors"]),
        ("roster_total", got["roster_total"] == roster_total),
        ("timers", got["timers"] == pin["floor_seconds"]),
        ("sprays", got["sprays"] == [pin["bitter"], pin["spicy"]]),
        ("legacy", got["legacy"] == pin["legacy"]),
        ("treasure", got["treasure"] == pin["treasure"]),
        ("sha8", pin["sha256"].startswith(got["sha8"]) and len(got["sha8"]) == 8),
    ]
    bad = [name for name, ok in checks if not ok]
    if bad:
        verdict["failures"].append("pin-mismatch:" + ",".join(bad))
        return verdict
    verdict["resolved"] = True
    verdict["engine_untouched"] = ENGINE_UNTOUCHED_RE.search(text) is not None
    wired = {m.group(1): int(m.group(2)) for m in FALLTHROUGH_RE.finditer(text)}
    verdict["fallthrough_wired"] = wired == {name: pin["ui_index"] for name, pin in ROWS.items()}
    verdict["window"] = WINDOW_RE.search(text) is not None
    verdict["ready"] = READY_RE.search(text) is not None
    verdict["gates_untested"] = GATES_RE.search(text) is not None
    verdict["passed"] = (PASS_RE.search("\n".join(
        line.strip() for line in lines)) is not None
        and verdict["engine_untouched"] and verdict["fallthrough_wired"]
        and verdict["window"] and verdict["ready"] and verdict["gates_untested"])
    if not verdict["passed"]:
        verdict["failures"].append("incomplete-chain")
    return verdict


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(description="Validate a stage-table-ext fixture log")
    parser.add_argument("--log", required=True)
    parser.add_argument("--cave", required=True)
    parser.add_argument("--json", default="")
    args = parser.parse_args(argv)
    verdict = validate(Path(args.log).read_text(encoding="utf-8", errors="replace"), args.cave)
    print("resolved=%s engine_untouched=%s fallthrough_wired=%s window=%s ready=%s passed=%s" % (
        verdict["resolved"], verdict["engine_untouched"], verdict["fallthrough_wired"],
        verdict["window"], verdict["ready"], verdict["passed"]))
    for failure in verdict["failures"]:
        print("FAIL " + failure)
    if args.json:
        Path(args.json).write_text(json.dumps(verdict, indent=1), encoding="utf-8")
    if verdict["captain_down"]:
        print("VERDICT BLOCKED captain-down")
        return 86
    if verdict["passed"]:
        print("VERDICT PASS %s resolves with pins intact" % args.cave)
        return 0
    print("VERDICT FAIL %s" % args.cave)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

