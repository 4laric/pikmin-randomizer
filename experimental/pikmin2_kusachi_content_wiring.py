"""Content-wiring bridge: staged kusachi layout to boot parameters (#688).

Connects the staged kusachi run layout (commit `380610a3`, issue #533) to a
booted stage: arena geometry binding, actor placement rows, starting-squad
wiring and observation markers. Consumes the #533 staging adapter, the #656
harness and the #675/#651 selection interfaces READ-ONLY (by contract, never
by import: none of them exist at this base). Reuses only the shared
brace-stream decoders (`experimental.pikmin2_cave_catalog`,
`experimental.pikmin2_assets`). Emits definitions and boot parameters, never
placements or gameplay. No shared/native/family edits, no runtime, no ADMIT.
"""
import hashlib
from pathlib import Path

from experimental.pikmin2_cave_catalog import parse as parse_caveinfo

CAVE_ID = "ch_NARI_01kusachi"
SOURCE_PATH = "user/Mukki/mapunits/caveinfo/ch_NARI_01kusachi.txt"
SOURCE_SHA256 = "b8d232f417ce3fd4b2903571a1c53234e63dec49e127d5ef5b8ef3cc34bb8d85"
EXPECTED_FLOORS = 1
EXPECTED_ROSTER = [[0, 0, 50], [0, 0, 0], [0, 0, 0], [0, 0, 0],
                   [0, 0, 0], [0, 0, 0], [0, 0, 0]]
EXPECTED_FLOOR_SECONDS = [180.0]
EXPECTED_LEGACY_TIME = 350.0
EXPECTED_BITTER_SPRAYS = 1
EXPECTED_SPICY_SPRAYS = 2
EXPECTED_UI_INDEX = 3
STAGED_COMMIT = "380610a3cd4e014a63005dfb17ed462b70485faf"

# Boot-selection contract (verified read-only, not implemented here):
# P2 challenge stages boot through the #651 host-mode fixture stage table
# keyed by ui_index (`selectByUiIndex(stages, count, uiIndex)` in
# `pc_port/pc_p2_challenge_mode.h`); kusachi resolves at ui_index 3. The
# native entry is the #675 stage-boot hook. The P1
# `--experimental-challenge-level <id 0-4>` namespace is for P1 layouts and
# is NOT the kusachi boot path.
BOOT_SELECTION = {
    "mechanism": "host-mode StageEntry table keyed by ui_index",
    "ui_index": EXPECTED_UI_INDEX,
    "cave_id": CAVE_ID,
    "native_entry": "#675 stage-boot hook",
    "not_this_path": "--experimental-challenge-level (P1 layouts only)",
}

# Harness contract (verified read-only): the #656 build/run harness consumes a
# staged run layout plus the #632 guard header and emits boot/run evidence.
# This bridge supplies the layout side; it does not reimplement the harness.
HARNESS_CONTRACT = {
    "harness": "#656 build/run harness",
    "needs": ["staged run layout (this bridge)", "#632 guard header"],
    "emits": ["boot/run evidence logs"],
}

# Observation markers this bridge defines for a booted kusachi run. Staged
# markers (from #533) describe the layout; these boot markers describe the
# observation points a runtime must emit. No marker is fabricated evidence.
BOOT_MARKERS = ("P2_KUSACHI_BOOT", "P2_KUSACHI_ARENA_BOUND",
                "P2_KUSACHI_SQUAD", "P2_KUSACHI_PLACEMENT_ROWS",
                "P2_KUSACHI_SELECT")


class MissingInput(ValueError):
    pass


class HashMismatch(ValueError):
    pass


class LayoutDecodeError(ValueError):
    pass


def staged_identity():
    """Pinned staged-layout facts (from #533 commit 380610a3 + lane plan)."""
    return dict(cave_id=CAVE_ID, source_path=SOURCE_PATH,
                source_sha256=SOURCE_SHA256, floors=EXPECTED_FLOORS,
                roster=[list(row) for row in EXPECTED_ROSTER],
                floor_seconds=list(EXPECTED_FLOOR_SECONDS),
                legacy_time=EXPECTED_LEGACY_TIME,
                bitter_sprays=EXPECTED_BITTER_SPRAYS,
                spicy_sprays=EXPECTED_SPICY_SPRAYS,
                ui_index=EXPECTED_UI_INDEX,
                staged_commit=STAGED_COMMIT)


def verify_source_bytes(data):
    """Fail closed unless bytes match the pinned canonical hash."""
    actual = hashlib.sha256(bytes(data)).hexdigest()
    if actual != SOURCE_SHA256:
        raise HashMismatch("Source hash %s does not match pinned %s"
                           % (actual, SOURCE_SHA256))
    return dict(source_path=SOURCE_PATH, sha256=actual, size=len(bytes(data)))


def decode_layout(text, enemy_ids, treasure_ids):
    """Decode the stage through the shared parser (never forked)."""
    try:
        return parse_caveinfo(text, enemy_ids, treasure_ids)
    except ValueError as error:
        raise LayoutDecodeError("Shared decode rejected input: %s" % error) from None


def arena_binding(decoded):
    """Arena geometry binding from a decoded stage: pools and units only."""
    floors = decoded.get("floors", [])
    if len(floors) != EXPECTED_FLOORS:
        raise LayoutDecodeError("Floor coverage mismatch")
    floor = floors[0]
    params = floor.get("parameters")
    if not isinstance(params, dict) or not params.get("f008"):
        raise LayoutDecodeError("Unit pool unresolved")
    pool = params["f008"]
    return dict(cave_id=CAVE_ID, floor=1, unit_pool=pool,
                light=floor["parameters"].get("f009", "none"))


def actor_rows(decoded):
    """Actor placement ROWS as definitions (weights/types), never placements."""
    rows = []
    for floor in decoded.get("floors", []):
        for kind, entries in (("enemy", floor.get("enemies", [])),
                              ("treasure", floor.get("treasures", [])),
                              ("gate", floor.get("gates", [])),
                              ("cap", floor.get("caps", []))):
            for entry in entries:
                rows.append({"floor": floor.get("first_floor"), "kind": kind,
                             "record": dict(entry)})
    return rows


def starting_squad():
    """Starting-squad wiring from the pinned roster (50 blue leaf)."""
    return dict(cave_id=CAVE_ID, ui_index=EXPECTED_UI_INDEX,
                roster=[list(row) for row in EXPECTED_ROSTER],
                floor_seconds=list(EXPECTED_FLOOR_SECONDS),
                legacy_time=EXPECTED_LEGACY_TIME,
                bitter_sprays=EXPECTED_BITTER_SPRAYS,
                spicy_sprays=EXPECTED_SPICY_SPRAYS)


def boot_params(decoded):
    """Assemble boot parameters: arena + actors + squad + markers + selection."""
    return dict(cave_id=CAVE_ID, ui_index=EXPECTED_UI_INDEX,
                arena=arena_binding(decoded),
                actor_rows=actor_rows(decoded),
                squad=starting_squad(),
                selection=dict(BOOT_SELECTION),
                harness=dict(HARNESS_CONTRACT),
                markers=list(BOOT_MARKERS))


def wiring_packet(params):
    """Reviewed packet: identity, boot params, contracts, open items."""
    return {
        "schema": 1,
        "cave_id": CAVE_ID,
        "source_sha256": SOURCE_SHA256,
        "staged_commit": STAGED_COMMIT,
        "boot": params,
        "semantic_resolution": "open",
        "blockers": [
            "P1 runtime observation needs the #656 harness plus #675/#651 selection wiring against these boot params (owner lanes).",
            "Enemy/treasure token resolution and unit-asset presence stay with #137 and the #533 adapter record.",
            "Any native fixture change is a private scoped candidate for owner review, never a shared edit.",
        ],
        "limitations": [
            "Actor rows are definition inputs, not spawn instances or placements; no coordinates are emitted.",
            "Timers, roster and sprays are staged baseline carried into boot params, not observed gameplay.",
            "Markers name observation points; emitting them without a runtime would fabricate evidence.",
        ],
        "generated": False,
    }
