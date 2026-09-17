"""Pinned MUKI houdai + redblue stage rows for the P1 boots (#748).

Coordinator shared producer for blocked p2-challenge-ch-muki-houdai-p1 (#735)
and p2-challenge-ch-muki-redblue-p1 (#744). Rows are decoded live from the
retail stage table (user/Matoba/challenge/stages.txt, sha256
59890efa80fe5a77d52b9a87301b97c91cd10c94ff9a3fb85c49b78dfae03cf1) through the
#136 framework contract parser and cross-checked against the P0 catalogue pins
(#541 houdai, #551 redblue). Nothing is invented. Fail-closed on any
divergence. Native table + lookup + guarded fixture live in
native/pc_port/pc_p2_challenge_muki_stages.{h,cpp} and
native/tools/p2_muki_stage_table_fixture.cpp (same values, asserted by tests).
"""

COLORS = ("Blue", "Red", "Yellow", "Purple", "White", "Bulbmin", "Carrot")
HAPPA = ("Leaf", "Bud", "Flower")

SOURCE_TABLE_SHA256 = "59890efa80fe5a77d52b9a87301b97c91cd10c94ff9a3fb85c49b78dfae03cf1"

# Pinned rows: (cave_id, ui_index, floors, floor_seconds, roster 7x3,
# bitter, spicy). Roster uses stage-table native color x happa ordering.
PINNED = {
    "ch_MUKI_houdai": {
        "cave_id": "ch_MUKI_houdai",
        "cave_path": "user/Mukki/mapunits/caveinfo/ch_MUKI_houdai.txt",
        "ui_index": 8,
        "floors": 2,
        "floor_seconds": [100.0, 150.0],
        "roster": [[0, 0, 10], [0, 0, 10], [0, 0, 10], [0, 0, 10],
                   [0, 0, 10], [0, 0, 0], [0, 0, 0]],
        "bitter_sprays": 1,
        "spicy_sprays": 1,
        "treasure_count_field": 0,
        "population": 50,
    },
    "ch_MUKI_redblue": {
        "cave_id": "ch_MUKI_redblue",
        "cave_path": "user/Mukki/mapunits/caveinfo/ch_MUKI_redblue.txt",
        "ui_index": 18,
        "floors": 2,
        "floor_seconds": [200.0, 200.0],
        "roster": [[0, 0, 25], [0, 0, 25], [0, 0, 0], [0, 0, 0],
                   [0, 0, 0], [0, 0, 0], [0, 0, 0]],
        "bitter_sprays": 1,
        "spicy_sprays": 1,
        "treasure_count_field": 0,
        "population": 50,
    },
}

# Receipt-parseable marker contract (native fixture emits these).
MARKERS = ("P2_MUKI_STAGE_RESOLVED", "P2_MUKI_STAGE_ERROR",
           "P2_MUKI_STAGE_TABLE_DONE", "P2_CHALLENGE_MODE_BOOT",
           "P2_CHALLENGE_MODE_TICK", "P2_CHALLENGE_MODE_FLOOR_ADVANCE",
           "P2_CHALLENGE_MODE_RETRY_STATE", "P2_CHALLENGE_MODE_DONE")


class PinMismatch(ValueError):
    pass


def population(roster):
    """Sum a 7x3 roster matrix. Fail-closed on shape/values."""
    if not isinstance(roster, list) or len(roster) != 7:
        raise PinMismatch("roster must have 7 color rows")
    total = 0
    for row in roster:
        if not isinstance(row, list) or len(row) != 3:
            raise PinMismatch("roster rows must have 3 happa bins")
        for value in row:
            if not isinstance(value, int) or value < 0:
                raise PinMismatch("roster bins must be non-negative ints")
            total += value
    return total


def verify_row(cave_id, decoded):
    """Fail-closed: decoded stage dict must equal the pinned row exactly."""
    if cave_id not in PINNED:
        raise PinMismatch("unknown stage: %r" % (cave_id,))
    want = PINNED[cave_id]
    if not isinstance(decoded, dict):
        raise PinMismatch("decoded stage must be a dict")
    for key in ("ui_index", "floors", "floor_seconds", "roster",
                "bitter_sprays", "spicy_sprays", "treasure_count_field"):
        got = decoded.get(key)
        if got != want[key]:
            raise PinMismatch("%s.%s mismatch: %r != pinned %r"
                              % (cave_id, key, got, want[key]))
    if population(decoded["roster"]) != want["population"]:
        raise PinMismatch("%s population mismatch" % cave_id)
    return True


def lookup_ui(ui_index):
    """Return the pinned cave_id for a ui_index, or None."""
    for cave_id, row in PINNED.items():
        if row["ui_index"] == ui_index:
            return cave_id
    return None