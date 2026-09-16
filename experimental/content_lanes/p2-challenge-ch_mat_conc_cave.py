"""P0 import-contract adapter for P2 Challenge stage ch_MAT_conc_cave (issue #536).

Lane p2-challenge-ch_mat_conc_cave, generation 2. Concrete source-import
preparation only: no native build, no runtime, no ADMIT, no playability
claim. The full content issue #536 stays open for P1/P2.

What this module does (stdlib only, dependency-free pure functions):

- Loads this lane's entry from docs/PIKMIN_CONTENT_IMPORT_LANES.json and
  the ch_MAT_conc_cave stage entry from docs/PIKMIN2_CONTENT_INVENTORY.json
  challenge stages (fail closed when either is missing or mismatched).
- Audits the catalogued challenge-stage metadata: exactly 3 floors, one
  positive finite timer per floor ([70.0, 100.0, 50.0]), a 7x3 native
  color/maturity starting-population matrix of nonnegative integers
  (only [4][2] == 2, total 2), sprays, treasure field, legacy time,
  ui_index and table order. Catalogued values are the baseline; nothing
  is re-derived or invented.
- Verifies raw source bytes against the pinned sha256
  (b3ae2c41...f35b1d5fe) and reports the exact missing prerequisite while
  the retail definition is unstaged (no ISO in this worktree).
- Decodes actual retail definition text with the shared parser
  (experimental.pikmin2_cave_catalog.parse, imported and never edited),
  then checks decoded 3-floor coverage and summarizes per-floor unit
  pools and token counts. Counts and pools are definition inputs, never
  spawn instances, weights-as-counts or placements.
- Checks resource closure of decoded unit pools against a
  caller-supplied disc file set (units/<pool> plus per-unit arc/texts
  archives once unit tables are decoded), reporting every missing file.
- Assembles the machine-readable P0 audit packet (generated False).

Challenge stages carry no per-floor enemy/treasure rosters in the
catalogue (unlike story caves); rosters arrive only with the decoded
retail definition, so unknown-actor reporting lives on the decode path.
"""

import hashlib
import math
from pathlib import Path

LANE = "p2-challenge-ch_mat_conc_cave"
ISSUE = 536
SOURCE_ID = "ch_MAT_conc_cave"
SOURCE_PATH = "user/Mukki/mapunits/caveinfo/ch_MAT_conc_cave.txt"
EXPECTED_SHA256 = "b3ae2c41e4719e1c34a86e887847650d9da293b992b7899c5559f60f35b1d5fe"
SCHEMA = "p2-challenge-ch_mat_conc_cave-p0/1"
EXPECTED_FLOORS = 3
EXPECTED_FLOOR_SECONDS = [70.0, 100.0, 50.0]
EXPECTED_TOTAL_PIKMIN = 2
BASE = "user/Mukki/mapunits"


def find_lane_entry(lanes_doc):
    """Return this lane's entry from a PIKMIN_CONTENT_IMPORT_LANES doc."""
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
    """Return the ch_MAT_conc_cave entry from a content inventory doc."""
    if not isinstance(inventory_doc, dict):
        raise TypeError("inventory document must be a mapping")
    try:
        stages = inventory_doc["challenge"]["stages"]
    except (KeyError, TypeError):
        raise ValueError("inventory document has no challenge stages") from None
    if not isinstance(stages, list):
        raise ValueError("inventory challenge stages are not a list")
    for entry in stages:
        if isinstance(entry, dict) and entry.get("cave_id") == SOURCE_ID:
            return entry
    raise ValueError("challenge stage entry missing: " + SOURCE_ID)


def _nonnegative_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(label + " must be a number")
    if not math.isfinite(value) or value < 0:
        raise ValueError(label + " must be finite and nonnegative")
    return value


def audit_metadata(stage):
    """Validate catalogued challenge-stage metadata; return the audit record.

    Raises on structural defects (floor count, timer list, population
    matrix shape/content, negative values). Catalogued values are reported
    as-is; no gameplay quantities are derived.
    """
    if not isinstance(stage, dict):
        raise TypeError("stage entry must be a mapping")
    if stage.get("floors") != EXPECTED_FLOORS:
        raise ValueError("stage floors != %d: %r" % (EXPECTED_FLOORS, stage.get("floors")))
    seconds = stage.get("floor_seconds")
    if not isinstance(seconds, list) or len(seconds) != EXPECTED_FLOORS:
        raise ValueError("floor_seconds must list exactly %d timers" % EXPECTED_FLOORS)
    timers = [_nonnegative_number(v, "floor_seconds[%d]" % i) for i, v in enumerate(seconds)]
    if any(t <= 0 for t in timers):
        raise ValueError("floor timers must be positive")
    matrix = stage.get("pikmin_by_native_color_and_maturity")
    if not isinstance(matrix, list) or len(matrix) != 7:
        raise ValueError("starting-population matrix must have 7 color rows")
    total = 0
    for color, row in enumerate(matrix):
        if not isinstance(row, list) or len(row) != 3:
            raise ValueError("starting-population row %d must have 3 maturities" % color)
        for maturity, count in enumerate(row):
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError("starting population [%d][%d] must be a nonnegative integer"
                                 % (color, maturity))
            total += count
    for key in ("bitter_sprays", "spicy_sprays", "treasure_count_field", "legacy_time"):
        _nonnegative_number(stage.get(key), key)
    for key in ("ui_index", "table_order"):
        value = stage.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(key + " must be a nonnegative integer")
    return {
        "cave_id": SOURCE_ID,
        "floors": EXPECTED_FLOORS,
        "floor_seconds": list(timers),
        "total_starting_pikmin": total,
        "nonzero_population_cells": sorted(
            (c, m) for c, row in enumerate(matrix) for m, v in enumerate(row) if v),
        "bitter_sprays": stage["bitter_sprays"],
        "spicy_sprays": stage["spicy_sprays"],
        "treasure_count_field": stage["treasure_count_field"],
        "legacy_time": stage["legacy_time"],
        "ui_index": stage["ui_index"],
        "table_order": stage["table_order"],
    }


def enemy_universe_from_inventory(inventory_doc):
    """Return the set of exact enemy internal names from the inventory."""
    enemies = inventory_doc.get("enemies")
    if not isinstance(enemies, list):
        raise ValueError("inventory document has no enemies list")
    universe = set()
    for record in enemies:
        if isinstance(record, dict) and isinstance(record.get("internal"), str):
            universe.add(record["internal"])
    if not universe:
        raise ValueError("inventory enemy universe is empty")
    return universe


def treasure_universe_from_inventory(inventory_doc):
    """Return the set of pellet-catalog treasure names from the inventory."""
    try:
        entries = inventory_doc["catalogs"]["us/runtime/otakara"]["entries"]
    except (KeyError, TypeError):
        raise ValueError("inventory document has no us/runtime/otakara catalog") from None
    if not isinstance(entries, list):
        raise ValueError("otakara catalog entries are not a list")
    universe = {e["name"] for e in entries
                if isinstance(e, dict) and isinstance(e.get("name"), str)}
    if not universe:
        raise ValueError("otakara treasure universe is empty")
    return universe


def verify_source_bytes(data, expected_sha256=EXPECTED_SHA256):
    """Hash raw source bytes against the pinned hash; drift fails loudly."""
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("source data must be bytes")
    observed = hashlib.sha256(bytes(data)).hexdigest()
    return {"sha256": observed, "expected": expected_sha256,
            "match": observed == expected_sha256}


def source_prerequisite(source_root=None):
    """Return the exact missing prerequisite, or the available source hash.

    The retail definition user/Mukki/mapunits/caveinfo/ch_MAT_conc_cave.txt
    is not staged in this worktree. When source_root holds it, report its
    sha256 and whether it matches the lane pin; otherwise report the exact
    prerequisite with no invented values.
    """
    if source_root is not None:
        candidate = Path(source_root) / SOURCE_PATH
        if candidate.is_file():
            report = verify_source_bytes(candidate.read_bytes())
            report.update(available=True, path=str(candidate), prerequisite=None)
            return report
    return {"available": False, "path": None, "sha256": None, "expected": EXPECTED_SHA256,
            "match": False,
            "prerequisite": "Retail US GPVE01 revision 0 definition " + SOURCE_PATH
                            + " (shift_jis caveinfo text); decode with "
                            + "experimental.pikmin2_cave_catalog.parse via "
                            + "decode_source_text, then summarize_decoded. "
                            + "No retail ISO is staged in this worktree."}


def decode_source_text(text, enemy_ids, treasure_ids):
    """Decode actual retail definition text with the shared cave parser."""
    from experimental.pikmin2_cave_catalog import parse
    return parse(text, enemy_ids, treasure_ids)


def summarize_decoded(parsed):
    """Check decoded 3-floor coverage; summarize pools and token counts.

    Returns definition inputs only: per-floor unit pool, enemy/treasure/
    gate/cap counts and distinct enemy base ids. Never emits placements,
    weights-as-counts or topology. Raises on coverage mismatch.
    """
    if not isinstance(parsed, dict):
        raise TypeError("decoded definition must be a mapping")
    floors = parsed.get("floors")
    if not isinstance(floors, list):
        raise ValueError("decoded definition has no floors list")
    occupied = set()
    reports = []
    for floor in floors:
        first, last = floor.get("first_floor"), floor.get("last_floor")
        if not isinstance(first, int) or not isinstance(last, int) or first > last:
            raise ValueError("decoded floor has an invalid range")
        occupied.update(range(first, last + 1))
        enemies = floor.get("enemies", [])
        reports.append({
            "definition_index": floor.get("definition_index"),
            "first_floor": first,
            "last_floor": last,
            "unit_pool": floor.get("parameters", {}).get("f008"),
            "enemy_tokens": len(enemies),
            "distinct_enemy_ids": sorted({e.get("enemy_id") for e in enemies}),
            "treasure_tokens": len(floor.get("treasures", [])),
            "gate_tokens": len(floor.get("gates", [])),
            "cap_tokens": len(floor.get("caps", [])),
        })
    if occupied != set(range(1, EXPECTED_FLOORS + 1)):
        raise ValueError("decoded floor coverage is not contiguous 1..%d: %s"
                         % (EXPECTED_FLOORS, sorted(occupied)))
    pools = [r["unit_pool"] for r in reports]
    return {"floor_count": len(reports), "floors": reports,
            "unit_pools_ordered": pools,
            "unit_pools_distinct": sorted(set(pools)),
            "generated": False}


def resource_closure_contract(pools, available_files, unit_tables=None):
    """Check decoded unit-pool resource closure against a disc file set.

    Required files: units/<pool> for every decoded pool, plus
    arc/<unit>/arc.szs and arc/<unit>/texts.szs for every unit once the
    pool's unit table is decoded (unit_tables maps pool -> [unit names]).
    Returns per-file presence and the missing list; raises on bad inputs.
    """
    if not isinstance(pools, list) or not pools or not all(isinstance(p, str) and p for p in pools):
        raise ValueError("pools must be a nonempty list of names")
    if available_files is None:
        raise ValueError("a disc file set is required (no silent pass)")
    available = set(available_files)
    unit_tables = unit_tables or {}
    if not isinstance(unit_tables, dict):
        raise ValueError("unit tables must map pool names to unit lists")
    required = [BASE + "/units/" + pool for pool in pools]
    for pool in pools:
        units = unit_tables.get(pool, [])
        if not isinstance(units, list):
            raise ValueError("unit table for %r is not a list" % pool)
        for unit in units:
            if not isinstance(unit, str) or not unit:
                raise ValueError("unit name in %r is not a string" % pool)
            required.append(BASE + "/arc/" + unit + "/arc.szs")
            required.append(BASE + "/arc/" + unit + "/texts.szs")
    missing = sorted({path for path in required if path not in available})
    return {"required": required, "present": sorted(set(required) - set(missing)),
            "missing": missing, "closed": not missing}


def audit_packet(metadata, prerequisite, lane_entry=None):
    """Assemble the machine-readable P0 audit packet (generated False)."""
    if not isinstance(metadata, dict) or metadata.get("floors") != EXPECTED_FLOORS:
        raise ValueError("metadata audit must cover exactly %d floors" % EXPECTED_FLOORS)
    if not isinstance(prerequisite, dict) or "available" not in prerequisite:
        raise ValueError("prerequisite report required")
    return {
        "schema": SCHEMA,
        "lane": LANE,
        "issue": ISSUE,
        "source_id": SOURCE_ID,
        "source_path": SOURCE_PATH,
        "source_sha256_pin": EXPECTED_SHA256,
        "metadata": metadata,
        "source": prerequisite,
        "lane_entry_issue": lane_entry.get("issue") if isinstance(lane_entry, dict) else None,
        "generated": False,
        "limitations": [
            "Catalogued metadata is the baseline; per-floor enemy/treasure rosters need the retail definition.",
            "Counts and pools are definition inputs, not spawn instances, placements or topology.",
            "Starting populations, timers and sprays are preserved verbatim; no playability is claimed.",
        ],
    }
