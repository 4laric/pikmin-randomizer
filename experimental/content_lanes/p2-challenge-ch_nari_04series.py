"""P0 import-contract adapter for ch_NARI_04series (lane p2-challenge, #545).

Isolated per-source contract: reads the actual series caveinfo
definition, its referenced unit pools, and its Challenge stage record
from a local disc image; decodes the cave with the EXISTING shared
parsers (experimental.pikmin2_cave_catalog.parse and
experimental.pikmin2_cave.unit_definition, reused and never forked);
parses the previously-unparsed user/Matoba/challenge/stages.txt stage
block with a small local reader; and validates everything against the
catalogued contract (expected source hash, 7-floor coverage, stage
timers and sprays and starting roster). Emits a metadata packet and an
explicit blocker list.

No placements are emitted (weighted rows stay definitions), no gameplay
is claimed, and no shared file is edited. Fail-closed: malformed
definitions raise ValueError; absent inputs raise FileNotFoundError;
contract drift is reported as mismatches and never silently corrected.
"""
from pathlib import Path

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_cave import BASE, unit_definition
from experimental.pikmin2_cave_catalog import parse as parse_cave

LANE = "p2-challenge-ch_nari_04series"
CAVE_ID = "ch_NARI_04series"
SOURCE = BASE + "/caveinfo/ch_NARI_04series.txt"
EXPECTED_SOURCE_SHA256 = "83cda0aa4e8fc96a68060ed1dba8e1e9ff53151a29856d813e23328618b70e18"
STAGES_TABLE = "user/Matoba/challenge/stages.txt"
ENEMY_INFO = "src/plugProjectYamashitaU/enemyInfo.cpp"
PELLET_ARCHIVE = "user/Abe/Pellet/us/pelletlist_us.szs"
PELLET_CONFIGS = ("otakara_config.txt", "item_config.txt")

# Catalogued stage contract (lane JSON entry): starting roster by native
# color and maturity, legacy time, sprays, treasure-count field, UI index
# and per-floor seconds. Values are asserted verbatim against stages.txt.
EXPECTED_STAGE = {
    "cave_file": "ch_NARI_04series.txt",
    "pikmin": [[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0],
               [0, 0, 50], [0, 0, 0], [0, 0, 0]],
    "time": 450.0,
    "bitter_sprays": 2,
    "spicy_sprays": 3,
    "floor_count": 7,
    "treasure_count": 0,
    "ui_index": 12,
    "floor_seconds": [40.0, 30.0, 40.0, 40.0, 40.0, 45.0, 60.0],
}

EXPECTED_FLOOR_COUNT = 7
UNIT_SUFFIXES = ("arc.szs", "texts.szs")


def _number(token, what):
    try:
        value = float(token)
    except (TypeError, ValueError):
        raise ValueError("Malformed stage field: " + what)
    if value != value or value < 0:
        raise ValueError("Invalid stage field: " + what)
    return value


def parse_stage_record(block):
    """Decode one stages.txt brace block into stage metadata.

    Layout: version, cave filename, 21 PikiCounter ints (7 native colors
    times 3 maturities), legacy time, bitter (dope black) and spicy (dope
    red) spray counts, floor count, treasure-count field, 2D UI index,
    then exactly floor_count per-floor second values.
    """
    if not block or block[0] != "{" or block[-1] != "}":
        raise ValueError("Malformed stage block framing")
    inner = block[1:-1]
    if len(inner) < 2 + 21 + 6:
        raise ValueError("Truncated stage block")
    version = inner[0]
    if version != "4":
        raise ValueError("Unsupported stage version: " + version)
    cave_file = inner[1]
    counters = [int(_number(t, "pikmin counter")) for t in inner[2:23]]
    pikmin = [counters[c * 3:(c + 1) * 3] for c in range(7)]
    time = _number(inner[23], "time")
    bitter = int(_number(inner[24], "bitter sprays"))
    spicy = int(_number(inner[25], "spicy sprays"))
    floors = int(_number(inner[26], "floor count"))
    treasures = int(_number(inner[27], "treasure count"))
    ui_index = int(_number(inner[28], "ui index"))
    seconds = [_number(t, "floor seconds") for t in inner[29:]]
    if len(seconds) != floors:
        raise ValueError("Stage floor-seconds count mismatch")
    if len(inner) != 29 + floors:
        raise ValueError("Trailing stage data")
    return {"version": version, "cave_file": cave_file, "pikmin": pikmin,
            "time": time, "bitter_sprays": bitter, "spicy_sprays": spicy,
            "floor_count": floors, "treasure_count": treasures,
            "ui_index": ui_index, "floor_seconds": seconds}


def find_stage_record(text, cave_id):
    """Locate the stage block naming <cave_id>.txt in stages.txt."""
    tokens = []
    for line in text.splitlines():
        stripped = line.split("#")[0].strip()
        if stripped:
            tokens.extend(stripped.split())
    depth, block, found = 0, [], None
    for token in tokens:
        if token == "{":
            if depth == 0:
                block = ["{"]
            else:
                block.append(token)
            depth += 1
        elif token == "}":
            depth -= 1
            if depth < 0:
                raise ValueError("Unbalanced stage table")
            block.append(token)
            if depth == 0:
                if len(block) > 2 and block[2] == cave_id + ".txt":
                    if found is not None:
                        raise ValueError("Duplicate stage record: " + cave_id)
                    found = list(block)
                block = []
        elif depth > 0:
            block.append(token)
    if depth != 0:
        raise ValueError("Unclosed stage table")
    if found is None:
        raise FileNotFoundError("No stage record: " + cave_id)
    return parse_stage_record(found)


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
    """Catalog the disc plus the enemy and treasure ID sets (read-only)."""
    import hashlib
    import re
    from experimental.pikmin2_pod import pellet_catalog
    catalog = disc_files(iso)
    enemy_raw = (Path(decomp_root) / ENEMY_INFO).read_bytes()
    pat = chr(123) + chr(34) + "([A-Za-z0-9_]+)" + chr(34)
    enemy_ids = set(re.findall(pat, enemy_raw.decode("utf-8")))
    archive = archive_files(read_blob(catalog, iso, PELLET_ARCHIVE))
    treasure_ids = set()
    for name in PELLET_CONFIGS:
        treasure_ids.update(pellet_catalog(archive[name].decode("shift_jis")))
    return {"catalog": catalog,
            "enemy_ids": enemy_ids,
            "treasure_ids": treasure_ids,
            "enemy_catalog_sha256": hashlib.sha256(enemy_raw).hexdigest()}


def decode(blobs, enemy_ids, treasure_ids):
    """Decode the cave, stage record and every referenced unit pool."""
    import hashlib
    cave_blob = blobs[SOURCE]
    cave = parse_cave(cave_blob.decode("shift_jis"), enemy_ids, treasure_ids)
    stage = find_stage_record(blobs[STAGES_TABLE].decode("shift_jis"), CAVE_ID)
    pools = {}
    for floor in cave["floors"]:
        pool = floor["parameters"]["f008"]
        if pool not in pools:
            path = BASE + "/units/" + pool
            if path not in blobs:
                raise FileNotFoundError("Missing unit pool: " + path)
            pools[pool] = unit_definition(blobs[path].decode("shift_jis"))
    hashes = {path: hashlib.sha256(blobs[path]).hexdigest() for path in blobs}
    return {"cave": cave, "stage": stage, "pools": pools, "sha256": hashes}


def check_contract(cave, stage):
    """Validate coverage, stage record and roster preservation."""
    mismatches = []
    occupied = set()
    for floor in cave["floors"]:
        occupied.update(range(floor["first_floor"], floor["last_floor"] + 1))
    want_floors = set(range(1, EXPECTED_FLOOR_COUNT + 1))
    if occupied != want_floors:
        mismatches.append("floor coverage is %s, expected 1-7" % sorted(occupied))
    if cave["floor_count"] != EXPECTED_FLOOR_COUNT:
        mismatches.append("decoded floor count %d, expected 7" % cave["floor_count"])
    want = EXPECTED_STAGE
    got_stage = {"cave_file": stage["cave_file"].replace(".txt", ""),
                 "pikmin": stage["pikmin"], "time": stage["time"],
                 "bitter_sprays": stage["bitter_sprays"],
                 "spicy_sprays": stage["spicy_sprays"],
                 "floor_count": stage["floor_count"],
                 "treasure_count": stage["treasure_count"],
                 "ui_index": stage["ui_index"],
                 "floor_seconds": stage["floor_seconds"]}
    want_stage = {"cave_file": CAVE_ID, "pikmin": want["pikmin"],
                  "time": want["time"], "bitter_sprays": want["bitter_sprays"],
                  "spicy_sprays": want["spicy_sprays"],
                  "floor_count": want["floor_count"],
                  "treasure_count": want["treasure_count"],
                  "ui_index": want["ui_index"],
                  "floor_seconds": want["floor_seconds"]}
    for key in ("cave_file", "pikmin", "time", "bitter_sprays", "spicy_sprays",
                "floor_count", "treasure_count", "ui_index", "floor_seconds"):
        if got_stage[key] != want_stage[key]:
            mismatches.append("stage %s is %r, expected %r"
                              % (key, got_stage[key], want_stage[key]))
    if stage["floor_count"] != cave["floor_count"]:
        mismatches.append("stage/cave floor count disagreement")
    if len(stage["floor_seconds"]) != cave["floor_count"]:
        mismatches.append("floor-seconds/floor disagreement")
    return mismatches


def check_closure(pools, catalog_names):
    """Every decoded unit needs its arc.szs plus texts.szs on disc."""
    missing = []
    for pool, units in sorted(pools.items()):
        for unit in units:
            for suffix in UNIT_SUFFIXES:
                asset = "%s/arc/%s/%s" % (BASE, unit["name"], suffix)
                if asset not in catalog_names:
                    missing.append(asset + " (via pool " + pool + ")")
    return sorted(missing)


def build_packet(cave, stage, pools, hashes, mismatches, missing_assets,
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
        "source_sha256_expected": EXPECTED_SOURCE_SHA256,
        "source_sha256_match": hashes[SOURCE] == EXPECTED_SOURCE_SHA256,
        "stages_table": STAGES_TABLE,
        "stages_table_sha256": hashes[STAGES_TABLE],
        "stage": stage,
        "unit_pool_sha256": {pool: hashes[BASE + "/units/" + pool]
                             for pool in pools},
        "enemy_catalog_sha256": enemy_catalog_sha256,
        "floor_count": cave["floor_count"], "floors": floors,
        "contract_mismatches": mismatches,
        "missing_unit_assets": missing_assets,
        "blockers": [
            "P1/P2 runtime import needs generator and framework contracts "
            "from existing owners #136 (Challenge framework), #137 "
            "(Challenge content), #129 (caves), #130 (species and assets), "
            "#131 (species).",
            "Promotion needs species admission per the roster ledger; "
            "unadmitted floor roster members block promotion, not this "
            "preparatory packet. English stage title stays unresolved; "
            "source ID and UI index are authoritative.",
        ],
        "generated": False,
        "limitations": [
            "Weights and counts are definition inputs, not final spawn "
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
    paths = [SOURCE, STAGES_TABLE]
    cave_probe = parse_cave(
        read_blob(catalog, iso, SOURCE).decode("shift_jis"),
        collected["enemy_ids"], collected["treasure_ids"])
    for floor in cave_probe["floors"]:
        paths.append(BASE + "/units/" + floor["parameters"]["f008"])
    blobs = {path: read_blob(catalog, iso, path) for path in paths}
    decoded = decode(blobs, collected["enemy_ids"], collected["treasure_ids"])
    mismatches = check_contract(decoded["cave"], decoded["stage"])
    if decoded["sha256"][SOURCE] != EXPECTED_SOURCE_SHA256:
        mismatches.append("source hash drift")
    missing = check_closure(decoded["pools"], set(catalog))
    packet = build_packet(decoded["cave"], decoded["stage"], decoded["pools"],
                          decoded["sha256"], mismatches, missing,
                          collected["enemy_catalog_sha256"])
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "packet.json").write_text(json.dumps(packet, indent=2) + "\n",
                                            encoding="utf-8")
    return packet
