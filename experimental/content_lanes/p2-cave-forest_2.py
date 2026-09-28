"""P0 import-contract adapter for forest_2 (lane p2-cave-forest_2, #155).

Isolated per-source contract: reads the actual forest_2 caveinfo
definition plus its five referenced unit pools from a local disc image,
decodes them with the EXISTING shared parsers
(``experimental.pikmin2_cave_catalog.parse`` and
``experimental.pikmin2_cave.unit_definition`` — reused, never forked),
and validates the decoded result against this lane's catalogued contract
(floor coverage, unit pools, enemy/treasure rosters per floor). Emits a
metadata packet and an explicit blocker list.

No placements are emitted (weighted rows stay definitions), no gameplay
is claimed, and no shared file is edited. Fail-closed: malformed
definitions raise ``ValueError``; absent inputs raise
``FileNotFoundError``; contract drift is reported as mismatches, never
silently corrected.
"""
from pathlib import Path

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_cave import BASE, unit_definition
from experimental.pikmin2_cave_catalog import parse as parse_cave

LANE = "p2-cave-forest_2"
CAVE_ID = "forest_2"
SOURCE = BASE + "/caveinfo/forest_2.txt"
ENEMY_INFO = "src/plugProjectYamashitaU/enemyInfo.cpp"
PELLET_ARCHIVE = "user/Abe/Pellet/us/pelletlist_us.szs"
PELLET_CONFIGS = ("otakara_config.txt", "item_config.txt")

# Catalogued contract (docs/PIKMIN_CONTENT_IMPORT_LANES.json lane entry):
# per-floor unit pool plus enemy/treasure source tokens in listed order.
# "SnakeCrow_radar_b" is a cargo-suffixed source token: base enemy
# SnakeCrow carrying treasure radar_b (native first-underscore split).
EXPECTED_FLOORS = (
    {"first": 1, "last": 1, "unit_pool": "2_ABE_nor1_cen2_metal.txt",
     "enemies": ["UjiB", "UjiA", "UjiA", "UjiA"],
     "treasures": ["fire_helmet"]},
    {"first": 2, "last": 2, "unit_pool": "1_ABE_ari_metal.txt",
     "enemies": ["Tank"],
     "treasures": ["chocoichigo_l", "diamond_red"]},
    {"first": 3, "last": 3, "unit_pool": "1_units_white_metal.txt",
     "enemies": ["WhitePom", "Qurione", "DaiodoGreen", "KareOoinu_s",
                 "KareOoinu_l", "Clover"],
     "treasures": ["gum_tape"]},
    {"first": 4, "last": 4, "unit_pool": "3_ABE_sak1_sak2_hit1_tsuchi.txt",
     "enemies": ["GasHiba"],
     "treasures": ["g_futa_kajiwara", "kinoko_doku"]},
    {"first": 5, "last": 5, "unit_pool": "1_units_snake_tsuchi.txt",
     "enemies": ["SnakeCrow_radar_b", "Egg", "KareOoinu_l", "KareOoinu_s",
                 "Zenmai"],
     "treasures": []},
)

UNIT_SUFFIXES = ("arc.szs", "texts.szs")


def split_cargo_token(token, treasure_ids):
    """Split a catalogued source token into (enemy_id, carried|None).

    Mirrors the native first-underscore rule used by the shared parser: a
    token keeps its full form unless the segment before its FIRST
    underscore is itself followed by a known treasure suffix. Only the
    exact ``<base>_<treasure>`` shape splits; anything else stays whole
    so "KareOoinu_s" never degrades.
    """
    head, sep, tail = token.partition("_")
    if sep and tail in treasure_ids:
        return head, tail
    return token, None


def expected_roster(entry, treasure_ids):
    """Multisets the decoded floor must carry: base enemies + cargo."""
    enemies, carried = [], []
    for token in entry["enemies"]:
        base, cargo = split_cargo_token(token, treasure_ids)
        enemies.append(base)
        if cargo is not None:
            carried.append(cargo)
    return sorted(enemies), sorted(carried), sorted(entry["treasures"])


def read_blob(catalog, iso, path):
    """Read one disc file; missing catalog entries fail closed."""
    if path not in catalog:
        raise FileNotFoundError("Missing disc source: " + path)
    at, size = catalog[path]
    with iso.open("rb") as disc:
        disc.seek(at)
        data = disc.read(size)
    if len(data) != size:
        raise ValueError("Truncated disc source: " + path)
    return data


def collect(iso, decomp_root):
    """Catalog the disc plus the enemy/treasure ID sets (read-only refs)."""
    import hashlib
    import re
    from experimental.pikmin2_pod import pellet_catalog
    catalog = disc_files(iso)
    enemy_raw = (Path(decomp_root) / ENEMY_INFO).read_bytes()
    enemy_ids = set(re.findall(r'\{"([A-Za-z0-9_]+)"', enemy_raw.decode("utf-8")))
    archive = archive_files(read_blob(catalog, iso, PELLET_ARCHIVE))
    treasure_ids = set()
    for name in PELLET_CONFIGS:
        treasure_ids.update(pellet_catalog(archive[name].decode("shift_jis")))
    return {"catalog": catalog,
            "enemy_ids": enemy_ids,
            "treasure_ids": treasure_ids,
            "enemy_catalog_sha256": hashlib.sha256(enemy_raw).hexdigest()}


def decode(blobs, enemy_ids, treasure_ids):
    """Decode the cave plus every referenced unit pool (shared parsers)."""
    import hashlib
    cave_blob = blobs[SOURCE]
    cave = parse_cave(cave_blob.decode("shift_jis"), enemy_ids, treasure_ids)
    pools = {}
    for floor in cave["floors"]:
        pool = floor["parameters"]["f008"]
        if pool not in pools:
            path = BASE + "/units/" + pool
            if path not in blobs:
                raise FileNotFoundError("Missing unit pool: " + path)
            pools[pool] = unit_definition(blobs[path].decode("shift_jis"))
    hashes = {path: hashlib.sha256(blobs[path]).hexdigest() for path in blobs}
    return {"cave": cave, "pools": pools, "sha256": hashes}


def check_contract(cave, treasure_ids):
    """Compare decoded floors against EXPECTED_FLOORS; return mismatches."""
    mismatches = []
    occupied = set()
    for floor in cave["floors"]:
        occupied.update(range(floor["first_floor"], floor["last_floor"] + 1))
    if occupied != {1, 2, 3, 4, 5}:
        mismatches.append("floor coverage is %s, expected 1-5" % sorted(occupied))
    by_first = {floor["first_floor"]: floor for floor in cave["floors"]}
    for entry in EXPECTED_FLOORS:
        floor = by_first.get(entry["first"])
        if floor is None or floor["last_floor"] != entry["last"]:
            mismatches.append("floor %d range drift" % entry["first"])
            continue
        if floor["parameters"]["f008"] != entry["unit_pool"]:
            mismatches.append("floor %d pool %s, expected %s"
                              % (entry["first"], floor["parameters"]["f008"],
                                 entry["unit_pool"]))
        want_enemies, want_carried, want_treasures = expected_roster(entry, treasure_ids)
        got_enemies = sorted(e["enemy_id"] for e in floor["enemies"])
        got_carried = sorted(e["carried_treasure"] for e in floor["enemies"]
                             if e["carried_treasure"] is not None)
        got_treasures = sorted(t["treasure_id"] for t in floor["treasures"])
        if got_enemies != want_enemies:
            mismatches.append("floor %d enemies %s, expected %s"
                              % (entry["first"], got_enemies, want_enemies))
        if got_carried != want_carried:
            mismatches.append("floor %d cargo %s, expected %s"
                              % (entry["first"], got_carried, want_carried))
        if got_treasures != want_treasures:
            mismatches.append("floor %d treasures %s, expected %s"
                              % (entry["first"], got_treasures, want_treasures))
    return mismatches


def check_closure(pools, catalog_names):
    """Every decoded unit needs its arc.szs + texts.szs on disc."""
    missing = []
    for pool, units in sorted(pools.items()):
        for unit in units:
            for suffix in UNIT_SUFFIXES:
                asset = "%s/arc/%s/%s" % (BASE, unit["name"], suffix)
                if asset not in catalog_names:
                    missing.append(asset + " (via pool " + pool + ")")
    return sorted(missing)


def build_packet(cave, pools, hashes, mismatches, missing_assets,
                 enemy_catalog_sha256):
    """Assemble the P0 metadata packet (definitions only, never spawns)."""
    floors = []
    for floor in cave["floors"]:
        pool = floor["parameters"]["f008"]
        floors.append({
            "first": floor["first_floor"], "last": floor["last_floor"],
            "unit_pool": pool,
            "unit_names": [u["name"] for u in pools[pool]],
            "enemies": [{"enemy_id": e["enemy_id"],
                         "carried_treasure": e["carried_treasure"],
                         "minimum_count": e.get("minimum_count"),
                         "selection_weight": e.get("selection_weight"),
                         "target_count": e.get("target_count")}
                        for e in floor["enemies"]],
            "treasures": [t["treasure_id"] for t in floor["treasures"]],
            "gates": [g["gate_id"] for g in floor["gates"]],
            "cap_count": len(floor["caps"]),
        })
    return {
        "schema": 1, "lane": LANE, "cave_id": CAVE_ID, "source": SOURCE,
        "source_sha256": hashes[SOURCE],
        "unit_pool_sha256": {pool: hashes[BASE + "/units/" + pool]
                             for pool in pools},
        "enemy_catalog_sha256": enemy_catalog_sha256,
        "floor_count": cave["floor_count"], "floors": floors,
        "contract_mismatches": mismatches,
        "missing_unit_assets": missing_assets,
        "blockers": [
            "P1/P2 runtime import needs generator/collision/actor contracts "
            "from existing owners #129 (caves), #128 (assets), #131 "
            "(species), #132 (saves), #140/#144/#145/#146.",
            "Promotion needs species admission per the roster ledger; "
            "unadmitted floor roster members block promotion, not this "
            "preparatory packet.",
        ],
        "generated": False,
        "limitations": [
            "Weights/counts are definition inputs, not final spawn "
            "instances or placements.",
            "No seeded topology, hole selection, radial distribution or "
            "restart identity is generated.",
        ],
    }


def run(iso, decomp_root, output_dir):
    """End-to-end P0 slice: read, decode, validate, write packet.json."""
    import json
    iso, output_dir = Path(iso), Path(output_dir)
    collected = collect(iso, decomp_root)
    catalog = collected["catalog"]
    paths = [SOURCE] + [BASE + "/units/" + e["unit_pool"] for e in EXPECTED_FLOORS]
    blobs = {path: read_blob(catalog, iso, path) for path in paths}
    decoded = decode(blobs, collected["enemy_ids"], collected["treasure_ids"])
    mismatches = check_contract(decoded["cave"], collected["treasure_ids"])
    missing = check_closure(decoded["pools"], set(catalog))
    packet = build_packet(decoded["cave"], decoded["pools"], decoded["sha256"],
                          mismatches, missing,
                          collected["enemy_catalog_sha256"])
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "packet.json").write_text(json.dumps(packet, indent=2) + "\n",
                                            encoding="utf-8")
    return packet
