"""Damagumo stage-table row pins + run-log observer (#742).

Pinned ch_MUKI_damagumo contract values (from #740 source via the lane plan):
1 floor, 150 s, 50 leaf roster row, bitter 0 / spicy 1, legacy 0.0, treasure
field 0, ui 6, table order 9, source sha256
c6f2dede22acb37cb0d939b1ee9670b103dc9408d3c9fe100000482891fefa9e.
No placements are emitted; no gameplay is claimed. Fail-closed throughout.
"""
import re

CAVE_ID = "ch_MUKI_damagumo"
CAVE_PATH = "user/Mukki/mapunits/caveinfo/ch_MUKI_damagumo.txt"
SOURCE_SHA256 = "c6f2dede22acb37cb0d939b1ee9670b103dc9408d3c9fe100000482891fefa9e"
UI_INDEX = 6
TABLE_ORDER = 9
FLOORS = 1
FLOOR_SECONDS = [150.0]
ROSTER = [[0, 0, 0], [0, 0, 0], [0, 0, 50], [0, 0, 0], [0, 0, 0],
          [0, 0, 0], [0, 0, 0]]
BITTER_SPRAYS = 0
SPICY_SPRAYS = 1
LEGACY_TIME = 0.0
TREASURE_COUNT_FIELD = 0

CAPTAIN_GUARD_HEADER = "scripts/p2_fixture_captain_guard.h"
CAPTAIN_GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"


def expected_row():
    """The pinned row as plain data (mirrors the native header constants)."""
    return {"cave_id": CAVE_ID, "cave_path": CAVE_PATH,
            "source_sha256": SOURCE_SHA256, "ui_index": UI_INDEX,
            "table_order": TABLE_ORDER, "floors": FLOORS,
            "floor_seconds": list(FLOOR_SECONDS),
            "roster": [list(row) for row in ROSTER],
            "bitter_sprays": BITTER_SPRAYS, "spicy_sprays": SPICY_SPRAYS,
            "legacy_time": LEGACY_TIME,
            "treasure_count_field": TREASURE_COUNT_FIELD}


def check_row(row):
    """Fail closed on any drift from the pinned contract."""
    want = expected_row()
    if not isinstance(row, dict):
        raise ValueError("Stage row must be a mapping")
    for key, expected in want.items():
        if row.get(key) != expected:
            raise ValueError("Stage row %s drift: %r" % (key, row.get(key)))
    return True


def roster_total(roster=None):
    rows = ROSTER if roster is None else roster
    return sum(value for row in rows for value in row)


def validate_log(text):
    """Validate receipt-parseable markers from a fixture run log.

    Returns findings; raises on captain-down. Unknown stages must be
    refused, never resolved. Unobserved legs stay False.
    """
    if "P2_FIXTURE_CAPTAIN_DOWN" in text:
        raise ValueError("Captain-down BLOCKED observation")
    resolved = re.search(
        r"P2_DAMAGUMO_STAGE_RESOLVED cave=(\S+) ui_index=(\d+) floors=(\d+) "
        r"roster_total=(\d+) bitter=(\d+) spicy=(\d+) legacy=([\d.]+) "
        r"treasure=(\d+) source=(\S+)", text)
    refused = "P2_DAMAGUMO_STAGE_REFUSED" in text
    gates = "P2_DAMAGUMO_STAGE_GATES all=UNTESTED" in text
    findings = {"resolved": False, "refused": refused,
                "gates_unclaimed": gates, "cave_id": CAVE_ID}
    if resolved:
        (cave, ui, floors, total, bitter, spicy, legacy, treasure,
         source) = resolved.groups()
        findings.update(cave=cave, ui_index=int(ui), floors=int(floors),
                        roster_total=int(total), bitter=int(bitter),
                        spicy=int(spicy), legacy=float(legacy),
                        treasure=int(treasure))
        findings["resolved"] = (
            cave == CAVE_ID and int(ui) == UI_INDEX and int(floors) == FLOORS
            and int(total) == roster_total() and int(bitter) == BITTER_SPRAYS
            and int(spicy) == SPICY_SPRAYS and float(legacy) == LEGACY_TIME
            and int(treasure) == TREASURE_COUNT_FIELD
            and source == SOURCE_SHA256[:8])
    return findings
