"""Challenge 03toy stage-table row contract (issue #752).

Lane toy-stage-table-row-native. Records the exact pinned ch_NARI_03toy row
facts, the serialized-integration follow-on, and the fixture contract. Stdlib
only; no runtime, no build here.

The row lives in native/pc_port/pc_p2_challenge_toy_stage.{h,cpp} (new
disjoint files, engine-free). The pc_bbft.cpp table integration + CMakeLists
membership are a specified follow-on blocked on the #710/#736 line; they are
NOT implemented here and this module never claims otherwise.
"""

import re

SCHEMA = "p2-challenge-toy-stage-table-row-v1"
ISSUE = 752
CONSUMER = {"lane": "p2-challenge-ch-nari-03toy-p1", "issue": 746}

ROW = {
    "cave_id": "ch_NARI_03toy",
    "cave_path": "user/Mukki/mapunits/caveinfo/ch_NARI_03toy.txt",
    "source_sha256": "d74b49ac3d9a2388288b9cb868dd8717ff893fd522453b309740519be841f03c",
    "ui_index": 5,
    "table_order": 2,
    "floors": 2,
    "floor_seconds": [100.0, 150.0],
    "roster": [[0, 0, 0], [0, 0, 0], [0, 0, 100], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
    "bitter_sprays": 2,
    "spicy_sprays": 2,
    "legacy_time": 0.0,
    "treasure_count_field": 0,
}

MARKERS = (
    "P2_TOY_STAGE_TABLE stage=ch_NARI_03toy ui_index=5 floors=2",
    "P2_TOY_STAGE_RESOLVED stage=ch_NARI_03toy ui_index=5 floors=2 roster_total=100",
)
PASS_MARKER = "PASS P2_TOY_STAGE_TABLE_RUN markers=3"
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"
OWNED_NATIVE = (
    "native/pc_port/pc_p2_challenge_toy_stage.h",
    "native/pc_port/pc_p2_challenge_toy_stage.cpp",
    "native/tools/p2_toy_stage_table_fixture.cpp",
)

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def roster_total(roster=None):
    rows = roster if roster is not None else ROW["roster"]
    if not isinstance(rows, list) or len(rows) != 7:
        raise ValueError("roster must have 7 rows")
    return sum(int(v) for row in rows for v in row)


def row_valid(row=None):
    """True when a row dict carries every pinned field exactly."""
    rec = row if row is not None else ROW
    if not isinstance(rec, dict):
        return False
    for key in ("cave_id", "cave_path", "source_sha256", "ui_index", "table_order",
                "floors", "floor_seconds", "bitter_sprays", "spicy_sprays",
                "legacy_time", "treasure_count_field"):
        if rec.get(key) != ROW[key]:
            return False
    if not _HEX64.match(rec.get("source_sha256", "")):
        return False
    try:
        if roster_total(rec.get("roster")) != 100:
            return False
    except (TypeError, ValueError):
        return False
    cells = [(c, h) for c, row in enumerate(rec.get("roster", []))
             for h, v in enumerate(row) if v]
    return cells == [(2, 2)]


def check_marker_log(text):
    """Return (ok, detail) for a toy-stage fixture run log; fail-closed."""
    if not isinstance(text, str):
        raise TypeError("marker log must be text")
    if CAPTAIN_DOWN in text:
        return False, "captain-down interruption present"
    if PASS_MARKER not in text:
        return False, "run PASS marker absent"
    missing = [m for m in MARKERS if m not in text]
    if missing:
        return False, "missing markers: %s" % "; ".join(missing)
    if "P2_TOY_STAGE_REFUSED" in text:
        return False, "refusal present"
    return True, "run PASS with exact markers"


def integration_followon():
    """Exact serialized pc_bbft.cpp/CMakeLists integration for the owner line."""
    return {
        "owner": "#710/#736 line (owns native/pc_port/pc_bbft.cpp and native/CMakeLists.txt)",
        "blocked_on": "#736 release of pc_bbft.cpp/CMakeLists.txt + #186 review",
        "edits": [
            "native/pc_port/pc_bbft.cpp: add the ch_NARI_03toy row to kP2ChallengeStages (or route lookup to p2_toy_stage_table) and call it from the challenge boot path",
            "native/CMakeLists.txt: add pc_port/pc_p2_challenge_toy_stage.cpp to the pikmin_pc target",
        ],
        "row": dict(ROW),
        "note": "Until then the row TU compiles only into the guarded fixture; the engine cannot resolve 03toy.",
    }
