"""P0 import-contract adapter for retail story cave yakushima_2 (issue #159).

Lane p2-cave-yakushima_2, phase P0 (source audit and additive import
contract). This module consumes three already-catalogued JSON inputs and
produces one validated import-contract packet for THIS cave only:

- the lane-plan entry (docs/PIKMIN_CONTENT_IMPORT_LANES.json, lane
  p2-cave-yakushima_2): 6 floors with exact unit pools, enemy source tokens
  and treasure IDs;
- the inventory cave entry (docs/PIKMIN2_CONTENT_INVENTORY.json, id
  yakushima_2): the factual roster baseline;
- the decoded catalog cave entry plus its source-hash map and unit-pool
  closure (retail GPVE01 rev 0 evidence, e.g. the l35 catalog.json):
  full floor parameters, weighted enemy/treasure/gate rows and cap blocks.

It decodes nothing itself: existing importers
(experimental.pikmin2_cave_catalog) own parsing. It re-derives no placements:
source weights stay definition inputs (minimum_count/selection_weight are
reported, never emitted as spawn instances). The actual disc source
(user/Mukki/mapunits/caveinfo/yakushima_2.txt) was unavailable to this turn,
so recorded catalog hashes are validated as well-formed evidence pins, not
re-extracted bytes; the packet says so explicitly.

Fail-closed: any identity/floor/pool/roster/hash/closure mismatch raises
ValueError. Stdlib only.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path

LANE = "p2-cave-yakushima_2"
SOURCE_ID = "yakushima_2"
SOURCE_PATH = "user/Mukki/mapunits/caveinfo/yakushima_2.txt"
UNIT_PREFIX = "user/Mukki/mapunits/units/"
ISSUE = 159
FLOOR_COUNT = 6

# Exact P0 contract pinned from the lane plan and issue #159 acceptance:
# (floor, unit pool, enemy source tokens in order, treasure IDs in order).
PLAN_FLOORS = (
    (1, "1_units_hit6x6_yakushima_toy.txt",
     ("KumaKochappy", "KumaKochappy", "KumaKochappy"), ("bane_red",)),
    (2, "1_units_large_toy.txt",
     ("BlackPom", "UjiA", "UjiA", "UjiB", "PanModoki", "PanModoki",
      "Armor", "Chiyogami"), ("g_futa_kyusyu", "cookie_m_l")),
    (3, "3_units_small2_small_mid_toy.txt",
     ("Mar", "PanModoki", "ElecBug", "ElecBug", "ElecBug", "ElecHiba"),
     ("tatebue", "castanets")),
    (4, "2_units_hit47_hit67_toy.txt",
     ("KumaChappy_g_futa_sikoku", "KumaKochappy", "KumaKochappy",
      "PanModoki"), ("chocowhite_l", "sensya")),
    (5, "2_units_sara_sara2_toy.txt",
     ("Fkabuto", "KumaKochappy", "KumaKochappy", "KumaKochappy",
      "KumaKochappy"), ("compact", "bell_blue")),
    (6, "1_units_opan_toy.txt",
     ("OoPanModoki_fue_b", "PanModoki", "Egg", "ElecBug", "ElecBug",
      "ElecHiba"), ("dia_b_green", "medama_yaki", "donutsichigo")),
)

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


def _tokens(entry):
    return [row["source_token"] for row in entry.get("enemies", [])]


def _treasures(entry):
    return [row["treasure_id"] for row in entry.get("treasures", [])]


def verify_identity(plan_entry, inventory_cave, catalog_cave):
    """All three sources must name the same cave, source path and issue."""
    _require(plan_entry.get("lane") == LANE, "Plan entry is not %s" % LANE)
    _require(plan_entry.get("source") == SOURCE_PATH, "Plan source drift")
    _require(plan_entry.get("issue") == ISSUE, "Plan issue drift")
    _require(inventory_cave.get("id") == SOURCE_ID, "Inventory cave mismatch")
    _require(inventory_cave.get("source") == SOURCE_PATH, "Inventory source drift")
    _require(catalog_cave.get("cave_id") == SOURCE_ID, "Catalog cave mismatch")
    _require(catalog_cave.get("source") == SOURCE_PATH, "Catalog source drift")
    return {"lane": LANE, "source_id": SOURCE_ID, "source": SOURCE_PATH,
            "issue": ISSUE}


def verify_floors(plan_entry, inventory_cave, catalog_cave):
    """6 contiguous floors with exact pools, enemy tokens and treasures.

    Compares catalog source_tokens (not re-derived IDs) against the pinned
    contract; inventory must agree floor by floor. Cap/ambush blocks are
    collected separately as explicit extra rosters, never merged silently.
    """
    plan_floors = plan_entry.get("details", {}).get("floors", [])
    inv_floors = inventory_cave.get("floors", [])
    cat_floors = catalog_cave.get("floors", [])
    _require(len(plan_floors) == FLOOR_COUNT, "Plan floor count drift")
    _require(len(inv_floors) == FLOOR_COUNT, "Inventory floor count drift")
    _require(len(cat_floors) == FLOOR_COUNT, "Catalog floor count drift")
    floors = []
    for number, pool, enemies, treasures in PLAN_FLOORS:
        plan = next((f for f in plan_floors
                     if f.get("first") == number and f.get("last") == number), None)
        inv = next((f for f in inv_floors
                    if f.get("first") == number and f.get("last") == number), None)
        cat = next((f for f in cat_floors
                    if f.get("first_floor") == number and f.get("last_floor") == number),
                   None)
        _require(plan is not None, "Plan missing floor %d" % number)
        _require(inv is not None, "Inventory missing floor %d" % number)
        _require(cat is not None, "Catalog missing floor %d" % number)
        _require(plan.get("unit_pool") == pool, "Plan pool drift floor %d" % number)
        _require(inv.get("unit_pool") == pool, "Inventory pool drift floor %d" % number)
        _require(cat["parameters"].get("f008") == pool,
                 "Catalog pool parameter drift floor %d" % number)
        _require(tuple(plan.get("enemy_ids", [])) == enemies,
                 "Plan roster drift floor %d" % number)
        _require(tuple(inv.get("enemy_ids", [])) == enemies,
                 "Inventory roster drift floor %d" % number)
        _require(tuple(_tokens(cat)) == enemies,
                 "Catalog roster drift floor %d" % number)
        _require(tuple(plan.get("treasure_ids", [])) == treasures,
                 "Plan treasure drift floor %d" % number)
        _require(tuple(inv.get("treasure_ids", [])) == treasures,
                 "Inventory treasure drift floor %d" % number)
        _require(tuple(_treasures(cat)) == treasures,
                 "Catalog treasure drift floor %d" % number)
        caps = [dict(empty=c["empty"],
                     source_token=None if c["empty"] else c["enemy"]["source_token"],
                     enemy_id=None if c["empty"] else c["enemy"]["enemy_id"],
                     drop_mode=None if c["empty"] else c["enemy"]["drop_mode"])
                for c in cat.get("caps", [])]
        floors.append({"floor": number, "unit_pool": pool,
                       "enemy_tokens": list(enemies), "treasure_ids": list(treasures),
                       "parameters": dict(cat["parameters"]),
                       "gates": [dict(g) for g in cat.get("gates", [])],
                       "caps": caps,
                       "weight_rows": {"enemies": len(cat.get("enemies", [])),
                                       "treasures": len(cat.get("treasures", []))}})
    covered = sorted(f["floor"] for f in floors)
    _require(covered == [1, 2, 3, 4, 5, 6], "Floor coverage gap")
    return floors


def verify_closure(catalog_hashes, unit_pools):
    """Recorded hash pins for the cave definition and all 6 pools must exist
    and be well-formed; every pool must carry at least one decoded unit with
    resource references. Units themselves stay catalog-owned data."""
    needed = [SOURCE_PATH] + [UNIT_PREFIX + pool for _, pool, _, _ in PLAN_FLOORS]
    pins = {}
    for path in needed:
        _require(path in catalog_hashes, "Missing recorded hash: %s" % path)
        pins[path] = check_hash(catalog_hashes[path], path)
    closure = {}
    for _, pool, _, _ in PLAN_FLOORS:
        entry = unit_pools.get(pool)
        _require(isinstance(entry, dict), "Missing unit pool closure: %s" % pool)
        _require(entry.get("source") == UNIT_PREFIX + pool,
                 "Pool source drift: %s" % pool)
        units = entry.get("units", [])
        _require(isinstance(units, list) and len(units) >= 1,
                 "Empty unit pool closure: %s" % pool)
        for unit in units:
            _require(isinstance(unit.get("name"), str) and unit["name"],
                     "Nameless unit in %s" % pool)
        closure[pool] = {"source": entry["source"],
                         "units": [u["name"] for u in units]}
    return {"pins": pins, "pools": closure}


def ledger(floors):
    """Per-ID occurrence ledger split into main-roster, cap/ambush and cargo
    entries. Cap-only IDs and drop-mode/cargo tokens are explicit open roster
    questions for the floor audit, not silent inclusions."""
    enemies = {}
    for floor in floors:
        for token in floor["enemy_tokens"]:
            record = enemies.setdefault(token, {"floors": [], "cap_floors": [],
                                                "cargo": None, "drop_modes": set()})
            record["floors"].append(floor["floor"])
        for cap in floor["caps"]:
            if cap["empty"] or cap["source_token"] is None:
                continue
            record = enemies.setdefault(cap["source_token"],
                                        {"floors": [], "cap_floors": [],
                                         "cargo": None, "drop_modes": set()})
            record["cap_floors"].append(floor["floor"])
            record["drop_modes"].add(cap["drop_mode"] if cap["drop_mode"] is not None else 0)
    treasures = {}
    for floor in floors:
        for treasure in floor["treasure_ids"]:
            treasures.setdefault(treasure, []).append(floor["floor"])
    main_only = sorted(t for t, r in enemies.items() if r["floors"] and not r["cap_floors"])
    cap_only = sorted(t for t, r in enemies.items() if r["cap_floors"] and not r["floors"])
    both = sorted(t for t, r in enemies.items() if r["floors"] and r["cap_floors"])
    cargo = sorted(t for t in enemies if "_" in t)
    drop = sorted((t, sorted(r["drop_modes"])) for t, r in enemies.items() if r["drop_modes"])
    return {"enemies": {t: {"floors": r["floors"], "cap_floors": r["cap_floors"],
                            "drop_modes": sorted(r["drop_modes"])} for t, r in enemies.items()},
            "treasures": treasures,
            "main_roster_tokens": main_only,
            "cap_only_tokens": cap_only,
            "main_and_cap_tokens": both,
            "cargo_tokens": cargo,
            "drop_tokens": drop}


def packet(plan_entry, inventory_cave, catalog_cave, catalog_hashes, unit_pools,
           enemy_catalog_sha256):
    """Build the validated P0 import-contract packet. No placements emitted."""
    identity = verify_identity(plan_entry, inventory_cave, catalog_cave)
    floors = verify_floors(plan_entry, inventory_cave, catalog_cave)
    closure = verify_closure(catalog_hashes, unit_pools)
    check_hash(enemy_catalog_sha256, "enemy catalog")
    result = {"schema": 1, "lane": LANE, "phase": "P0",
              "identity": identity,
              "floor_count": FLOOR_COUNT,
              "floors": floors,
              "ledger": ledger(floors),
              "hashes": {"cave_definition": closure["pins"][SOURCE_PATH],
                         "unit_pools": {pool: closure["pins"][UNIT_PREFIX + pool]
                                        for _, pool, _, _ in PLAN_FLOORS},
                         "enemy_catalog": enemy_catalog_sha256},
              "resource_closure": closure["pools"],
              "generated": False,
              "placements": [],
              "blockers": [
                  "Runtime phase P1 waits on validated generator/actor/mode "
                  "contracts (#129 actors/assets/species lanes, #468 active "
                  "cave work, lanes 34-51); no native build or runtime in P0.",
                  "Cap/ambush-only tokens %s plus drop/cargo tokens %s need "
                  "floor-audit resolution with family owners before promotion."
                  % (ledger(floors)["cap_only_tokens"],
                     [t for t, _ in ledger(floors)["drop_tokens"]]
                     + ledger(floors)["cargo_tokens"]),
                  "Localized display-name mapping stays open; stable source "
                  "IDs above are authoritative, never guessed translations.",
              ],
              "limitations": [
                  "Weights/counts are definition inputs, not final spawn "
                  "instances or placements; no seeded topology generated.",
                  "Recorded hashes are catalog evidence pins; the disc source "
                  "was unavailable to this turn, so no bytes were re-extracted.",
                  "Metadata is not runtime acceptance; full content stays OPEN.",
              ]}
    result["packet_sha256"] = hashlib.sha256(
        json.dumps(result, sort_keys=True).encode("utf-8")).hexdigest()
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-entry", required=True,
                        help="JSON file holding the lane plan entry")
    parser.add_argument("--inventory-cave", required=True,
                        help="JSON file holding the inventory cave entry")
    parser.add_argument("--catalog-cave", required=True,
                        help="JSON file holding the decoded catalog cave entry")
    parser.add_argument("--catalog", required=True,
                        help="JSON catalog file (hash map, unit pools, enemy hash)")
    parser.add_argument("--output", required=True,
                        help="Packet output JSON path (parent must exist)")
    args = parser.parse_args(argv)
    plan_entry = load_json(args.plan_entry)
    inventory_cave = load_json(args.inventory_cave)
    catalog_cave = load_json(args.catalog_cave)
    catalog = load_json(args.catalog)
    result = packet(plan_entry, inventory_cave, catalog_cave,
                    catalog.get("source_sha256", {}),
                    catalog.get("unit_pools", {}),
                    catalog.get("enemy_catalog_sha256"))
    out = Path(args.output)
    _require(out.parent.is_dir(), "Missing output directory: %s" % out.parent)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"lane": LANE, "floors": result["floor_count"],
                      "main_tokens": len(result["ledger"]["main_roster_tokens"]),
                      "cap_only": result["ledger"]["cap_only_tokens"],
                      "packet_sha256": result["packet_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
