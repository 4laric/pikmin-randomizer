"""P0 import-contract adapter for P2 Challenge 28: ch_MAT_route_rover (#561).

Lane p2-challenge-ch_mat_route_rover, phase P0 (source audit and additive
import contract). This module consumes two already-catalogued JSON inputs and
produces one validated import-contract packet for THIS stage only:

- the lane-plan entry (docs/PIKMIN_CONTENT_IMPORT_LANES.json): source path
  with hash pin, table order, UI index, floor count and timers, starting
  Pikmin populations by native color/maturity, sprays and legacy time;
- the inventory challenge collection (docs/PIKMIN2_CONTENT_INVENTORY.json):
  the 30-stage table with the same row, the stages.txt hash pin and the
  per-stage caveinfo hash pins.

It decodes no caveinfo itself: the disc source
(user/Mukki/mapunits/caveinfo/ch_MAT_route_rover.txt) was unavailable to this
turn, so per-floor enemy rosters stay an explicit open decode and the packet
records recorded hashes as evidence pins, never re-extracted bytes. No
placements, timers-as-gameplay, scores or completion claims are emitted:
floor_seconds are preserved definition inputs for the P1 framework (#136).

Additionally this adapter reports an explicit floor-coverage block and a
resource closure mapping each required Challenge resource to the owning
system/issue, so P1 has a named hand-off surface rather than a bare metadata
dump.

Fail-closed: any identity/detail/collection/hash mismatch raises ValueError.
Stdlib only.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path

LANE = "p2-challenge-ch_mat_route_rover"
SOURCE_ID = "ch_MAT_route_rover"
LABEL = "P2 Challenge 28: ch_MAT_route_rover"
SOURCE_PATH = "user/Mukki/mapunits/caveinfo/ch_MAT_route_rover.txt"
STAGES_TXT = "user/Matoba/challenge/stages.txt"
ISSUE = 561
PARENT_ISSUE = 137

# Exact P0 contract pinned from the lane plan and issue #561.
TABLE_ORDER = 21
UI_INDEX = 27
FLOORS = 1
PIKMIN_MATRIX = ((0, 0, 20), (0, 0, 20), (0, 0, 20), (0, 0, 0),
                 (0, 0, 0), (0, 0, 0), (0, 0, 0))
LEGACY_TIME = 300.0
BITTER_SPRAYS = 2
SPICY_SPRAYS = 2
TREASURE_COUNT_FIELD = 0
FLOOR_SECONDS = (90.0,)
STAGE_COUNT = 30
CHALLENGE_FLOOR_TOTAL = 59

# Label ordinal is the 1-based display number; the catalog convention is
# ordinal == ui_index + 1 (verified across all 30 stages), while table_order
# is the separate stages.txt row index. Kept as a cross-check, not a retail
# claim.
DISPLAY_ORDINAL = 28
NATIVE_COLOR_COUNT = 7
MATURITY_SLOTS = 3

_HEX64 = re.compile(r"[0-9a-f]{64}")


def _require(condition, message):
    if not condition:
        raise ValueError(message)
    return condition


def load_json(path):
    """Read a JSON document, failing closed on missing/corrupt input."""
    path = Path(path)
    _require(path.is_file(), "Missing input: %s" % path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError("Corrupt JSON input %s: %s" % (path, error))


def check_hash(value, what):
    """A recorded source hash must be a 64-hex digest, never empty/placeholder."""
    _require(isinstance(value, str) and _HEX64.fullmatch(value),
             "Missing or malformed source hash for %s" % what)
    _require(value != "0" * 64, "Placeholder source hash for %s" % what)
    return value


def _number(value, what):
    _require(isinstance(value, (int, float)) and not isinstance(value, bool),
             "Non-numeric %s" % what)
    _require(value >= 0, "Negative %s" % what)
    return float(value)


def verify_identity(plan_entry, inventory_stage):
    """Plan and inventory must name the same stage, source path and issues."""
    _require(plan_entry.get("lane") == LANE, "Plan entry is not %s" % LANE)
    _require(plan_entry.get("source") == SOURCE_PATH, "Plan source drift")
    _require(plan_entry.get("issue") == ISSUE, "Plan issue drift")
    _require(plan_entry.get("label") == LABEL, "Plan label drift")
    _require(DISPLAY_ORDINAL == UI_INDEX + 1, "Display ordinal must be ui_index + 1")
    _require(inventory_stage.get("cave_id") == SOURCE_ID, "Inventory stage mismatch")
    _require(inventory_stage.get("cave_path") == SOURCE_PATH, "Inventory path drift")
    _require(inventory_stage.get("issue") == PARENT_ISSUE, "Inventory issue drift")
    return {"lane": LANE, "source_id": SOURCE_ID, "label": LABEL,
            "source": SOURCE_PATH, "issue": ISSUE, "parent_issue": PARENT_ISSUE}


def verify_population_matrix(matrix, name):
    """7 native-color rows x 3 maturity slots, non-negative int counts."""
    _require(isinstance(matrix, list) and len(matrix) == NATIVE_COLOR_COUNT,
             "%s population matrix shape drift" % name)
    for row in matrix:
        _require(isinstance(row, list) and len(row) == MATURITY_SLOTS
                 and all(isinstance(v, int) and not isinstance(v, bool) and v >= 0
                         for v in row),
                 "%s population row drift" % name)
    _require(tuple(tuple(row) for row in matrix) == PIKMIN_MATRIX,
             "%s population drift" % name)
    return tuple(tuple(row) for row in matrix)


def verify_details(plan_entry, inventory_stage):
    """Every stage metadata field must match the pinned contract exactly in
    both sources: identity, order/UI indices, floor count and per-floor
    timers, starting populations, sprays, legacy time and treasure field."""
    details = plan_entry.get("details", {})
    for source, name in ((details, "plan"), (inventory_stage, "inventory")):
        _require(source.get("table_order") == TABLE_ORDER,
                 "%s table_order drift" % name)
        _require(source.get("cave_id") == SOURCE_ID, "%s cave_id drift" % name)
        _require(source.get("ui_index") == UI_INDEX, "%s ui_index drift" % name)
        _require(source.get("floors") == FLOORS, "%s floor count drift" % name)
        verify_population_matrix(source.get("pikmin_by_native_color_and_maturity"), name)
        _require(_number(source.get("legacy_time"), "%s legacy_time" % name)
                 == LEGACY_TIME, "%s legacy_time drift" % name)
        _require(source.get("bitter_sprays") == BITTER_SPRAYS,
                 "%s bitter spray drift" % name)
        _require(source.get("spicy_sprays") == SPICY_SPRAYS,
                 "%s spicy spray drift" % name)
        _require(source.get("treasure_count_field") == TREASURE_COUNT_FIELD,
                 "%s treasure-count drift" % name)
        seconds = source.get("floor_seconds")
        _require(isinstance(seconds, list)
                 and tuple(_number(v, "floor timer") for v in seconds) == FLOOR_SECONDS,
                 "%s floor timer drift" % name)
        _require(len(seconds) == FLOORS, "%s timer/floor count mismatch" % name)
    return {"table_order": TABLE_ORDER, "ui_index": UI_INDEX, "floors": FLOORS,
            "floor_seconds": list(FLOOR_SECONDS),
            "pikmin_by_native_color_and_maturity": [list(r) for r in PIKMIN_MATRIX],
            "legacy_time": LEGACY_TIME, "bitter_sprays": BITTER_SPRAYS,
            "spicy_sprays": SPICY_SPRAYS,
            "treasure_count_field": TREASURE_COUNT_FIELD}


def floor_coverage(details):
    """Explicit floor coverage: one floor with exactly one timer, and the
    per-floor timer set is complete (no gap between floors and timers)."""
    floors = details["floors"]
    seconds = details["floor_seconds"]
    return {
        "floors": floors,
        "timer_count": len(seconds),
        "complete": floors == FLOORS and len(seconds) == floors,
        "floor_seconds": list(seconds),
        "timer_total": sum(seconds),
        "coverage": "floor %d..%d" % (1, floors) if floors else "none",
    }


def verify_collection(inventory_challenge, inventory_hashes, plan_source_sha256):
    """The 30-stage table must carry this row exactly once with unique order
    and UI indices; the stages.txt pin and this stage's caveinfo pin must be
    present, well-formed, and the caveinfo pin must equal the plan pin."""
    stages = inventory_challenge.get("stages", [])
    _require(len(stages) == STAGE_COUNT, "Challenge stage count drift")
    rows = [s for s in stages if s.get("cave_id") == SOURCE_ID]
    _require(len(rows) == 1, "Stage row missing or duplicated")
    orders = sorted(s.get("table_order") for s in stages)
    _require(orders == list(range(STAGE_COUNT)), "Table order collision/gap")
    uis = sorted(s.get("ui_index") for s in stages)
    _require(uis == list(range(STAGE_COUNT)), "UI index collision/gap")
    for s in stages:
        _require(isinstance(s.get("floors"), int) and s["floors"] >= 1,
                 "Stage floor count invalid")
    _require(sum(s["floors"] for s in stages) == CHALLENGE_FLOOR_TOTAL,
             "Challenge floor total drift")
    _require(STAGES_TXT in inventory_hashes, "Missing stages.txt hash")
    stages_hash = check_hash(inventory_hashes[STAGES_TXT], STAGES_TXT)
    _require(SOURCE_PATH in inventory_hashes, "Missing stage caveinfo hash")
    stage_hash = check_hash(inventory_hashes[SOURCE_PATH], SOURCE_PATH)
    _require(stage_hash == check_hash(plan_source_sha256, "plan source pin"),
             "Caveinfo pin differs between plan and inventory")
    return {"stages": STAGE_COUNT, "challenge_floor_total": CHALLENGE_FLOOR_TOTAL,
            "stages_txt": STAGES_TXT, "stages_txt_sha256": stages_hash,
            "stage_sha256": stage_hash}


def ledger():
    """Conserved quantities carried verbatim for the P1 framework: starting
    populations, sprays, per-floor and total timers. Native color/maturity
    indices are reported as indices, never guessed into species names."""
    populations = [{"native_color": color, "maturity": maturity, "count": count}
                   for color, row in enumerate(PIKMIN_MATRIX)
                   for maturity, count in enumerate(row) if count]
    return {"starting_populations": populations,
            "starting_pikmin_total": sum(p["count"] for p in populations),
            "bitter_sprays": BITTER_SPRAYS, "spicy_sprays": SPICY_SPRAYS,
            "floor_seconds": list(FLOOR_SECONDS),
            "floor_timer_total": sum(FLOOR_SECONDS),
            "legacy_time": LEGACY_TIME,
            "treasure_count_field": TREASURE_COUNT_FIELD}


def resource_closure(hashes):
    """Map each required Challenge resource to status/owner. Nothing is
    claimed present: the stage bytes are unavailable to this turn, and every
    runtime resource is owned by another lane/issue."""
    def hash_status(path):
        pinned = hashes.get(path)
        if isinstance(pinned, str) and _HEX64.fullmatch(pinned):
            return ("pinned-not-read",
                    "recorded sha256 %s; bytes not re-extracted (disc unavailable)" % pinned)
        return ("missing-source", "no recorded hash")

    stage_status, stage_detail = hash_status(SOURCE_PATH)
    stages_status, stages_detail = hash_status(STAGES_TXT)
    return {
        "stage definition bytes": {
            "status": stage_status, "path": SOURCE_PATH, "detail": stage_detail,
            "owner": "content lane #561 (decode is OPEN; no roster values invented)",
        },
        "stage table ordering": {
            "status": stages_status, "path": STAGES_TXT, "detail": stages_detail,
            "owner": "Challenge content #137",
        },
        "floor layout and generator seams": {
            "status": "unsupported-reference",
            "detail": "unit/generator/collision layout is not carried in the stage "
                      "metadata; consumed from the accepted generator pin",
            "owner": "#129 (cave generation) and #137 (Challenge content)",
        },
        "starting roster, sprays and timers": {
            "status": "pinned-not-read",
            "detail": "carried as definition inputs only; native color/maturity "
                      "indices are not resolved to species by this lane",
            "owner": "#136 (Challenge runtime framework)",
        },
        "floor actors and hazards": {
            "status": "unsupported-reference",
            "detail": "per-floor enemy/hazard roster needs the caveinfo bytes; "
                      "unresolved admission blocks promotion, not this P0",
            "owner": "#130/#131 and family lanes",
        },
        "TheKey/hole/geyser, scoring, retry, result semantics": {
            "status": "unsupported-reference",
            "detail": "no stage-metadata field encodes these; the host chal0 "
                      "fixture is not Challenge mode and proves nothing here",
            "owner": "#136 (framework) and #137 (content)",
        },
    }


def packet(plan_entry, inventory_stage, inventory_challenge, inventory_hashes):
    """Build the validated P0 import-contract packet. No gameplay emitted."""
    identity = verify_identity(plan_entry, inventory_stage)
    details = verify_details(plan_entry, inventory_stage)
    coverage = floor_coverage(details)
    _require(coverage["complete"], "Floor coverage incomplete")
    collection = verify_collection(inventory_challenge, inventory_hashes,
                                   plan_entry.get("source_sha256"))
    result = {"schema": 1, "lane": LANE, "phase": "P0",
              "identity": identity,
              "details": details,
              "floor_coverage": coverage,
              "collection": collection,
              "ledger": ledger(),
              "resource_closure": resource_closure(inventory_hashes),
              "generated": False,
              "placements": [],
              "floor_roster_decode": "OPEN: per-floor enemy rosters need the "
                                     "caveinfo bytes (disc unavailable); no "
                                     "roster values invented.",
              "blockers": [
                  "P1 runtime waits on the Challenge framework (#136: native "
                  "color/maturity populations, sprays, per-floor timing, "
                  "keys/exits, scores, retry and ordinary/deathless result "
                  "semantics) and content/generator/actor contracts "
                  "(#137, #129, #130, #131); no native build or runtime in P0.",
                  "Per-floor enemy roster decode needs local legal caveinfo "
                  "bytes; the exact missing prerequisite is the disc source, "
                  "not a re-derivation of weights.",
                  "TheKey/hole/geyser, scoring, ordinary vs deathless "
                  "completion and retry reset are unvalidated; the host "
                  "chal0 fixture is not Challenge mode and proves nothing here.",
                  "English title unresolved; source ID ch_MAT_route_rover "
                  "and UI index 27 are authoritative, never guessed. The "
                  "backlog label ordinal 28 is not the UI index (ordinal = "
                  "ui_index + 1 across the 30-stage catalog).",
              ],
              "limitations": [
                  "Timers/sprays/populations are definition inputs, not "
                  "observed gameplay; no seeded play, score or completion "
                  "generated.",
                  "Recorded hashes are inventory evidence pins; no bytes "
                  "were re-extracted by this turn.",
                  "Metadata is not runtime acceptance; full content stays OPEN.",
              ]}
    result["packet_sha256"] = hashlib.sha256(
        json.dumps(result, sort_keys=True).encode("utf-8")).hexdigest()
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-entry", required=True,
                        help="JSON file holding the lane plan entry")
    parser.add_argument("--inventory-stage", required=True,
                        help="JSON file holding the inventory stage row")
    parser.add_argument("--inventory-collection", required=True,
                        help="JSON file holding the inventory challenge collection "
                             "(stages, hash map)")
    parser.add_argument("--output", required=True,
                        help="Packet output JSON path (parent must exist)")
    args = parser.parse_args(argv)
    plan_entry = load_json(args.plan_entry)
    inventory_stage = load_json(args.inventory_stage)
    collection = load_json(args.inventory_collection)
    result = packet(plan_entry, inventory_stage, collection,
                    collection.get("source_sha256", {}))
    out = Path(args.output)
    _require(out.parent.is_dir(), "Missing output directory: %s" % out.parent)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"lane": LANE, "floors": result["details"]["floors"],
                      "timer_total": result["ledger"]["floor_timer_total"],
                      "starting_pikmin": result["ledger"]["starting_pikmin_total"],
                      "packet_sha256": result["packet_sha256"]}, indent=2))


if __name__ == "__main__":
    main()