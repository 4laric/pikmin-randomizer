"""P0 import-contract adapter for retail story cave tutorial_2 (issue #152).

Lane p2-cave-tutorial_2, generation 2. Concrete source-import preparation
only: no native build, no runtime, no ADMIT, no playability claim. The full
content issue #152 stays open for P1/P2.

What this module does (stdlib only, dependency-free pure functions):

- Validates the catalogued tutorial_2 baseline (docs/PIKMIN2_CONTENT_INVENTORY.json
  story_caves entry): nine floors with contiguous 1..9 coverage, one unit
  pool per floor, flat enemy/treasure id rosters per floor.
- Classifies every enemy token with the TekiInfo::read splitting rule used by
  experimental.pikmin2_cave_catalog.enemy_token (``$`` drop prefix, then the
  FIRST underscore whose prefix is a known enemy separates carried cargo),
  but non-raising: unknown enemies, unknown cargo and malformed tokens are
  collected as findings instead of aborting the audit.
- Cross-checks exact enemy tokens against the inventory enemy universe and
  treasure tokens against the pellet catalog universe supplied by the caller.
- Reports resource closure (ordered/distinct/duplicate unit pools, distinct
  enemy and treasure tokens) and the exact missing prerequisite for decoding
  the actual retail definition (user/Mukki/mapunits/caveinfo/tutorial_2.txt),
  which is not available in this worktree. When a source root IS supplied,
  the definition is decoded with experimental.pikmin2_cave_catalog.parse
  (imported, never edited); nothing is invented.

The catalogued flat rosters are roster summaries, not weighted definitions:
this module never emits placements, weights, counts-as-spawns or topology.
"""

import hashlib
import re
from pathlib import Path

LANE = "p2-cave-tutorial_2"
ISSUE = 152
SOURCE_ID = "tutorial_2"
SOURCE_PATH = "user/Mukki/mapunits/caveinfo/tutorial_2.txt"
SCHEMA = "p2-cave-tutorial_2-p0/1"
EXPECTED_FLOOR_COUNT = 9

_TOKEN_RE = re.compile(r"\$?[1-9]?[A-Za-z][A-Za-z0-9_]*")


def find_lane_entry(lanes_doc):
    """Return the tutorial_2 lane entry from a PIKMIN_CONTENT_IMPORT_LANES doc."""
    if not isinstance(lanes_doc, dict):
        raise TypeError("lanes document must be a mapping")
    lanes = lanes_doc.get("lanes")
    if not isinstance(lanes, list):
        raise ValueError("lanes document has no lanes list")
    for entry in lanes:
        if isinstance(entry, dict) and entry.get("lane") == LANE:
            return entry
    raise ValueError("lane entry missing: " + LANE)


def find_cave_entry(inventory_doc):
    """Return the tutorial_2 story_caves entry from a content inventory doc."""
    if not isinstance(inventory_doc, dict):
        raise TypeError("inventory document must be a mapping")
    caves = inventory_doc.get("story_caves")
    if not isinstance(caves, list):
        raise ValueError("inventory document has no story_caves list")
    for entry in caves:
        if isinstance(entry, dict) and entry.get("id") == SOURCE_ID:
            return entry
    raise ValueError("story cave entry missing: " + SOURCE_ID)


def floor_coverage(entry):
    """Validate contiguous floor coverage; return the ordered floor records."""
    if not isinstance(entry, dict):
        raise TypeError("cave entry must be a mapping")
    floors = entry.get("floors")
    if not isinstance(floors, list) or not floors:
        raise ValueError("cave entry has no floors list")
    records = []
    occupied = set()
    for index, floor in enumerate(floors):
        if not isinstance(floor, dict):
            raise ValueError("floor %d is not a mapping" % index)
        for key in ("first", "last", "unit_pool", "enemy_ids", "treasure_ids"):
            if key not in floor:
                raise ValueError("floor %d missing %r" % (index, key))
        first, last = floor["first"], floor["last"]
        if (not isinstance(first, int) or isinstance(first, bool)
                or not isinstance(last, int) or isinstance(last, bool)):
            raise ValueError("floor %d has non-integer range" % index)
        if first > last:
            raise ValueError("floor %d has inverted range" % index)
        if not isinstance(floor["unit_pool"], str) or not floor["unit_pool"]:
            raise ValueError("floor %d has empty unit pool" % index)
        for key in ("enemy_ids", "treasure_ids"):
            if not isinstance(floor[key], list):
                raise ValueError("floor %d %s is not a list" % (index, key))
        span = set(range(first, last + 1))
        if occupied.intersection(span):
            raise ValueError("overlapping floor range at index %d" % index)
        occupied.update(span)
        records.append(floor)
    if occupied != set(range(1, EXPECTED_FLOOR_COUNT + 1)):
        raise ValueError("floor coverage is not contiguous 1..%d: %s"
                         % (EXPECTED_FLOOR_COUNT, sorted(occupied)))
    return records


def classify_token(token, enemy_ids, treasure_ids):
    """Classify one roster token without raising on unknowns.

    Mirrors the TekiInfo::read rule in
    experimental.pikmin2_cave_catalog.enemy_token: an optional ``$`` drop
    prefix (with optional digit mode), then the split at the FIRST
    underscore whose prefix names a known enemy. Returns a dict with
    ``kind`` in (exact, generator_variant, carrier, unknown_enemy,
    unknown_cargo, malformed), the resolved ``base``, optional ``carried``
    cargo and the ``drop`` mode (0 for plain tokens).
    """
    if not isinstance(token, str) or not _TOKEN_RE.fullmatch(token):
        return {"source_token": token, "kind": "malformed", "base": None,
                "carried": None, "drop": 0}
    name = token
    drop = 0
    variant = False
    if name.startswith("$"):
        variant = True
        name = name[1:]
        drop = 1
        if name[:1] in "123456789":
            drop = int(name[0])
            name = name[1:]
    carried = None
    for pos, char in enumerate(name):
        if char == "_" and name[:pos] in enemy_ids:
            carried = name[pos + 1:]
            name = name[:pos]
            break
    lookup = {value.lower(): value for value in enemy_ids}
    if name.lower() not in lookup:
        return {"source_token": token, "kind": "unknown_enemy", "base": None,
                "carried": carried, "drop": drop}
    base = lookup[name.lower()]
    if carried is not None:
        if carried not in treasure_ids:
            return {"source_token": token, "kind": "unknown_cargo",
                    "base": base, "carried": carried, "drop": drop}
        return {"source_token": token, "kind": "carrier", "base": base,
                "carried": carried, "drop": drop}
    if variant:
        return {"source_token": token, "kind": "generator_variant",
                "base": base, "carried": None, "drop": drop}
    return {"source_token": token, "kind": "exact", "base": base,
            "carried": None, "drop": 0}


def audit_entry(entry, enemy_universe, treasure_universe):
    """Audit the catalogued entry; return the findings packet (generated=False).

    Raises on structural defects (coverage, shapes); collects token-level
    unknowns as findings. Flat rosters are reported as-is: no weights, no
    placements, no topology are derived here.
    """
    floors = floor_coverage(entry)
    enemy_ids = set(enemy_universe)
    treasure_ids = set(treasure_universe)
    floor_reports = []
    unresolved = []
    kinds = {}
    for floor in floors:
        tokens = []
        for token in floor["enemy_ids"]:
            classified = classify_token(token, enemy_ids, treasure_ids)
            tokens.append(classified)
            kinds[classified["kind"]] = kinds.get(classified["kind"], 0) + 1
            if classified["kind"] in ("unknown_enemy", "unknown_cargo", "malformed"):
                unresolved.append({"floor": floor["first"], "token": token,
                                   "kind": classified["kind"]})
        missing_treasure = [name for name in floor["treasure_ids"]
                            if name not in treasure_ids]
        for name in missing_treasure:
            unresolved.append({"floor": floor["first"], "token": name,
                               "kind": "unknown_treasure"})
        floor_reports.append({
            "floor": floor["first"],
            "unit_pool": floor["unit_pool"],
            "enemy_tokens": len(floor["enemy_ids"]),
            "treasure_tokens": len(floor["treasure_ids"]),
            "tokens": tokens,
            "missing_treasure": missing_treasure,
        })
    pools = [floor["unit_pool"] for floor in floors]
    seen = set()
    duplicates = sorted({pool for pool in pools if pool in seen or seen.add(pool)})
    return {
        "schema": SCHEMA,
        "lane": LANE,
        "issue": ISSUE,
        "source_id": SOURCE_ID,
        "source_path": SOURCE_PATH,
        "floor_count": len(floors),
        "floors": floor_reports,
        "unit_pools_ordered": pools,
        "unit_pools_distinct": sorted(set(pools)),
        "unit_pools_duplicated": duplicates,
        "distinct_enemy_tokens": sorted({t for f in floors for t in f["enemy_ids"]}),
        "distinct_treasure_tokens": sorted({t for f in floors for t in f["treasure_ids"]}),
        "token_kinds": kinds,
        "unresolved": unresolved,
        "generated": False,
        "limitations": [
            "Catalogued flat rosters are roster summaries, not weighted definitions.",
            "No spawn instances, weights, placements, topology or schedules are derived.",
            "Carrier cargo and $-variant drop modes need the actual retail definition to confirm.",
        ],
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
        raise ValueError("inventory document has no us/runtime/otakara catalog")
    if not isinstance(entries, list):
        raise ValueError("otakara catalog entries are not a list")
    universe = {e["name"] for e in entries
                if isinstance(e, dict) and isinstance(e.get("name"), str)}
    if not universe:
        raise ValueError("otakara treasure universe is empty")
    return universe


def inventory_hashes(inventory_path, lanes_doc):
    """Report the observed inventory hash against the lane-plan pin."""
    data = Path(inventory_path).read_bytes()
    observed = hashlib.sha256(data).hexdigest()
    pinned = lanes_doc.get("inventory_sha256") if isinstance(lanes_doc, dict) else None
    return {"path": str(inventory_path), "pinned": pinned,
            "observed": observed, "match": pinned == observed}


def source_prerequisite(source_root=None):
    """Return the exact missing prerequisite, or the available source hash.

    The retail definition user/Mukki/mapunits/caveinfo/tutorial_2.txt is not
    present in this worktree. When source_root holds it, report its sha256
    for decode; otherwise report the exact prerequisite with no invented values.
    """
    if source_root is not None:
        candidate = Path(source_root) / SOURCE_PATH
        if candidate.is_file():
            digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
            return {"available": True, "path": str(candidate), "sha256": digest,
                    "prerequisite": None}
    return {"available": False, "path": None, "sha256": None,
            "prerequisite": "Retail US GPVE01 revision 0 definition " + SOURCE_PATH
                            + " (shift_jis caveinfo text); decode with "
                            + "experimental.pikmin2_cave_catalog.inventory(iso, source, output). "
                            + "No retail ISO is staged in this worktree."}


def decode_source_text(text, enemy_ids, treasure_ids):
    """Decode actual retail definition text with the shared cave parser."""
    from experimental.pikmin2_cave_catalog import parse
    return parse(text, enemy_ids, treasure_ids)
