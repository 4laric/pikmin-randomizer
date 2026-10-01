"""P0 import-contract adapter for P2 Challenge 11 ch_MAT_t_hunter_enemy (issue #543).

Lane p2-challenge-ch_mat_t_hunter_enemy, generation 2. Concrete
source-import preparation only: no native build, no runtime, no ADMIT, no
playability claim. The full-content issue #543 stays open for P1/P2.

What this module does (stdlib only, dependency-free pure functions):

- Validates the catalogued challenge stage-metadata baseline
  (docs/PIKMIN2_CONTENT_INVENTORY.json challenge entry plus the lane-plan
  entry in docs/PIKMIN_CONTENT_IMPORT_LANES.json): identity fields
  (cave_id, cave_path, table_order, ui_index), floor count, the 7x3 native
  color/maturity pikmin roster (preserved exactly, never reinterpreted),
  per-floor timers, spray counts and the treasure-count field.
- Reports the legacy_time vs floor_seconds-sum relationship as an observed
  finding (both values preserved as-is; P1 reconciles against the source).
- Carries the lane-plan source_sha256 pin as the P1 acceptance hash: when a
  source root supplies user/Mukki/mapunits/caveinfo/ch_MAT_t_hunter_enemy.txt,
  its bytes are hashed and compared to the pin; when absent, the exact
  missing prerequisite is returned with no invented values.
- Decodes actual retail definition text through the shared
  experimental.pikmin2_cave_catalog.parse entry point (imported, never
  edited) once the source lands.

Unlike story caves, the catalogued challenge baseline carries stage-level
metadata only (no per-floor enemy/treasure rosters): this module never
emits placements, weights, topology or schedules.
"""
import hashlib
import re
from pathlib import Path

LANE = "p2-challenge-ch_mat_t_hunter_enemy"
ISSUE = 543
SOURCE_ID = "ch_MAT_t_hunter_enemy"
SOURCE_PATH = "user/Mukki/mapunits/caveinfo/ch_MAT_t_hunter_enemy.txt"
SCHEMA = "p2-challenge-ch_mat_t_hunter_enemy-p0/1"
EXPECTED_FLOORS = 5
EXPECTED_TABLE_ORDER = 10
EXPECTED_UI_INDEX = 10
EXPECTED_SOURCE_SHA256 = "dc3734362430697c2a4dbce67b447efe876c60934cb282bc10051a3cdb2f5a82"

_SHA_RE = re.compile(r"[0-9a-f]{64}")


def find_lane_entry(lanes_doc):
    """Return the challenge lane entry from a PIKMIN_CONTENT_IMPORT_LANES doc."""
    if not isinstance(lanes_doc, dict):
        raise TypeError("lanes document must be a mapping")
    lanes = lanes_doc.get("lanes")
    if not isinstance(lanes, list):
        raise ValueError("lanes document has no lanes list")
    for entry in lanes:
        if isinstance(entry, dict) and entry.get("lane") == LANE:
            return entry
    raise ValueError("lane entry missing: " + LANE)


def find_stage_entry(inventory_doc):
    """Return the ch_MAT_t_hunter_enemy entry from the challenge stages list."""
    if not isinstance(inventory_doc, dict):
        raise TypeError("inventory document must be a mapping")
    challenge = inventory_doc.get("challenge")
    if not isinstance(challenge, dict):
        raise ValueError("inventory document has no challenge mapping")
    stages = challenge.get("stages")
    if not isinstance(stages, list):
        raise ValueError("challenge inventory has no stages list")
    for entry in stages:
        if isinstance(entry, dict) and entry.get("cave_id") == SOURCE_ID:
            return entry
    raise ValueError("challenge stage entry missing: " + SOURCE_ID)


def _require_int(name, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer" % name)
    if value < minimum:
        raise ValueError("%s is negative" % name)
    return value


def _require_number(name, value, minimum=0.0):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric" % name)
    if value < minimum:
        raise ValueError("%s is negative" % name)
    return float(value)


def validate_stage_metadata(entry):
    """Validate the catalogued stage-metadata contract; return the findings."""
    if not isinstance(entry, dict):
        raise TypeError("stage entry must be a mapping")
    if entry.get("cave_id") != SOURCE_ID:
        raise ValueError("stage entry is not %s" % SOURCE_ID)
    if entry.get("cave_path") != SOURCE_PATH:
        raise ValueError("stage entry path mismatch")
    if entry.get("table_order") != EXPECTED_TABLE_ORDER:
        raise ValueError("stage entry table_order mismatch")
    if entry.get("ui_index") != EXPECTED_UI_INDEX:
        raise ValueError("stage entry ui_index mismatch")
    floors = _require_int("floors", entry.get("floors"), 1)
    roster = entry.get("pikmin_by_native_color_and_maturity")
    if not isinstance(roster, list) or len(roster) != 7:
        raise ValueError("pikmin roster must be a 7-row matrix")
    for index, row in enumerate(roster):
        if not isinstance(row, list) or len(row) != 3:
            raise ValueError("pikmin roster row %d must hold 3 maturity counts" % index)
        for value in row:
            _require_int("pikmin roster count", value)
    nonzero = [{"row": index, "counts": list(row)}
               for index, row in enumerate(roster) if any(row)]
    seconds = entry.get("floor_seconds")
    if not isinstance(seconds, list) or len(seconds) != floors:
        raise ValueError("floor_seconds must list one timer per floor")
    timers = [_require_number("floor timer", value) for value in seconds]
    legacy = _require_number("legacy_time", entry.get("legacy_time"))
    bitter = _require_int("bitter_sprays", entry.get("bitter_sprays"))
    spicy = _require_int("spicy_sprays", entry.get("spicy_sprays"))
    treasure_count = _require_int("treasure_count_field", entry.get("treasure_count_field"))
    total = sum(timers)
    return {
        "cave_id": SOURCE_ID,
        "cave_path": SOURCE_PATH,
        "table_order": EXPECTED_TABLE_ORDER,
        "ui_index": EXPECTED_UI_INDEX,
        "floors": floors,
        "pikmin_roster": [list(row) for row in roster],
        "pikmin_nonzero_rows": nonzero,
        "pikmin_total": sum(sum(row) for row in roster),
        "legacy_time": legacy,
        "floor_seconds": timers,
        "floor_seconds_total": total,
        "timer_finding": {
            "legacy_time": legacy,
            "floor_total": total,
            "legacy_minus_floor_total": legacy - total,
            "note": "Both values preserved as catalogued; P1 reconciles against the source.",
        },
        "bitter_sprays": bitter,
        "spicy_sprays": spicy,
        "treasure_count_field": treasure_count,
    }


def source_pin(lane_entry):
    """Return the lane-plan source_sha256 pin, format-checked."""
    if not isinstance(lane_entry, dict):
        raise TypeError("lane entry must be a mapping")
    pin = lane_entry.get("source_sha256")
    if not isinstance(pin, str) or not _SHA_RE.fullmatch(pin):
        raise ValueError("lane entry has no well-formed source_sha256 pin")
    if pin != EXPECTED_SOURCE_SHA256:
        raise ValueError("lane entry source pin does not match the P0 record")
    return pin


def source_prerequisite(lane_entry, source_root=None):
    """Return the exact missing prerequisite, or hash-verify a supplied source.

    When source_root holds user/Mukki/mapunits/caveinfo/ch_MAT_t_hunter_enemy.txt,
    its bytes are hashed and compared against the lane-plan pin. Otherwise the
    exact prerequisite is returned with the pin quoted as the P1 acceptance
    hash; nothing is invented.
    """
    pin = source_pin(lane_entry)
    if source_root is not None:
        candidate = Path(source_root) / SOURCE_PATH
        if candidate.is_file():
            digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
            return {"available": True, "path": str(candidate), "sha256": digest,
                    "expected_sha256": pin, "match": digest == pin,
                    "prerequisite": None}
    return {"available": False, "path": None, "sha256": None,
            "expected_sha256": pin, "match": False,
            "prerequisite": "Retail US GPVE01 revision 0 definition " + SOURCE_PATH
                            + " (shift_jis caveinfo text, sha256 must equal " + pin + "); "
                            + "decode with experimental.pikmin2_cave_catalog.parse against the "
                            + "inventory enemy universe and pellet-catalog treasure universe. "
                            + "No retail ISO is staged in this worktree."}


def decode_source_text(text, enemy_ids, treasure_ids):
    """Decode actual retail definition text with the shared cave parser."""
    from experimental.pikmin2_cave_catalog import parse
    return parse(text, enemy_ids, treasure_ids)


def enemy_universe_from_inventory(inventory_doc):
    """Return the set of exact enemy internal names from the inventory."""
    enemies = inventory_doc.get("enemies")
    if not isinstance(enemies, list):
        raise ValueError("inventory document has no enemies list")
    universe = {r["internal"] for r in enemies
                if isinstance(r, dict) and isinstance(r.get("internal"), str)}
    if not universe:
        raise ValueError("inventory enemy universe is empty")
    return universe


def treasure_universe_from_inventory(inventory_doc):
    """Return the set of pellet-catalog treasure names from the inventory."""
    try:
        entries = inventory_doc["catalogs"]["us/runtime/otakara"]["entries"]
    except (KeyError, TypeError):
        raise ValueError("inventory document has no us/runtime/otakara catalog")
    if not isinstance(entries, list):
        raise ValueError("otakara catalog entries are not a list")
    universe = {e["name"] for e in entries
                if isinstance(e, dict) and isinstance(e.get("name"), str)}
    if not universe:
        raise ValueError("otakara treasure universe is empty")
    return universe


def audit_stage(entry, lane_entry):
    """Audit the catalogued stage entry; return the findings packet."""
    metadata = validate_stage_metadata(entry)
    packet = {
        "schema": SCHEMA,
        "lane": LANE,
        "issue": ISSUE,
        "source_id": SOURCE_ID,
        "source_path": SOURCE_PATH,
        "source_sha256_pin": source_pin(lane_entry),
        "generated": False,
    }
    packet.update(metadata)
    packet["limitations"] = [
        "Catalogued challenge baseline is stage-level metadata only; no per-floor enemy/treasure rosters are catalogued.",
        "No spawn instances, weights, placements, topology or schedules are derived.",
        "Floor timers, roster counts and spray counts are preserved as catalogued, never renormalized.",
    ]
    return packet
