"""P0 source-audit adapter for P2 Challenge 21 ch_NARI_07whitepurple (#553).

Isolated metadata/import contract for one caveinfo definition. It reuses the
shared brace-stream and roster decoders (experimental.pikmin2_cave and
experimental.pikmin2_cave_catalog) and emits no placements: weighted rows
stay definition inputs, exactly as the shared catalog limitations state.

Timer/roster/spray figures are the recorded inventory baseline
(docs/PIKMIN_CONTENT_IMPORT_LANES.json and
docs/PIKMIN2_CONTENT_INVENTORY.json), not values re-derived from the
caveinfo bytes: floor timers, starting Pikmin and sprays live in the
Challenge stage parameter table, not in this file.
"""
import hashlib
import re
from pathlib import Path

from experimental.pikmin2_cave import parameters, safe_name, tree
from experimental.pikmin2_cave_catalog import integer, parse, rows

CAVE_ID = "ch_NARI_07whitepurple"
CAVE_PATH = "user/Mukki/mapunits/caveinfo/ch_NARI_07whitepurple.txt"
SOURCE_SHA256 = "478fee6f70236ed8d51ad47cf8a08809309dc25bc763a54e484ff12693e0ad92"
EXPECTED_FLOORS = 2
UI_INDEX = 20
TABLE_ORDER = 1

BASELINE = {
    "floors": 2,
    "floor_seconds": [170.0, 170.0],
    "pikmin_by_native_color_and_maturity": [[0, 0, 0], [0, 0, 0], [0, 0, 0],
                                             [0, 0, 0], [30, 0, 0], [0, 0, 0],
                                             [0, 0, 0]],
    "legacy_time": 0.0,
    "bitter_sprays": 0,
    "spicy_sprays": 3,
    "treasure_count_field": 0,
    "ui_index": 20,
}

RESEARCH_ENEMYINFO = (
    "C:/Users/alari/pikmin-randomizer/native/pikmin2-research"
    "/src/plugProjectYamashitaU/enemyInfo.cpp"
)

KNOWN_FLOOR_KEYS = (
    {"f%03X" % index for index in range(0x18)}
    - {"f00B", "f00C", "f00D", "f00E", "f00F"}
)
STRING_FLOOR_KEYS = {"f008", "f009", "f00A"}
# Disc-observed asset directories (read-only enumeration of the local GPVE01
# image): unit pools live under mapunits/units, Challenge lights under Abe/cave.
UNIT_POOL_DIR = "user/Mukki/mapunits/units/"
LIGHT_DIR = "user/Abe/cave/"

LIMITATIONS = [
    "Weighted rows are definition inputs, not final spawn instances or "
    "placements; no coordinates are emitted.",
    "Floor timers, starting Pikmin and sprays are inventory baseline from "
    "the lane plan, not values decoded from these bytes.",
    "Enemy/treasure/cap tokens are observed source strings pending catalog "
    "resolution by the owning lanes; placement_type 5 is carried verbatim "
    "and not rewritten to a plant/target interpretation.",
]

BLOCKERS = [
    "P2 Challenge runtime framework (#136): starting color/maturity intake, "
    "per-floor timing, keys/exits, scoring, retry and ordinary/deathless "
    "result semantics are not established for this stage.",
    "Challenge content owner (#137): stage completion, timer/roster stage-"
    "table verification and the Challenge 21 English title stay with the "
    "content owner.",
    "Cave generation seams (#129, lanes 34-51): unit-pool instantiation for "
    "2_units_cent_north_tsuchi.txt and 2_units_mid2_north_tsuchi.txt is "
    "unproven; authored floor maxima (enemies 13/10, items 6/5, caps 100) "
    "are definition limits, not observed counts.",
    "Actor/asset owners (#128, #130, #131): definition-level resolution "
    "succeeds (8 plain enemies plus 4 Enemy_treasure carries, all treasures "
    "resolved in contract-p0.json), but real actor admission and behavior "
    "for these tokens plus the TamagoMushi cap payload remain unresolved.",
    "Treasure pellet catalog: key/apple/leaf/dia/ichigo/momiji/donut/bane "
    "pellet resolution needs the disc pellet table verified by #137.",
    "Disc asset presence: both unit pools and the Challenge light were "
    "verified present in contract-p0.json resource_closure; a static audit "
    "still does not authorize runtime promotion.",
]


class SourceMissing(ValueError):
    pass


class HashMismatch(ValueError):
    pass


class UnsupportedDefinition(ValueError):
    pass


def source_bytes(path):
    """Read raw definition bytes; fail closed when the prerequisite is absent."""
    candidate = Path(path)
    if not candidate.is_file():
        raise SourceMissing("Missing source prerequisite: " + str(path))
    return candidate.read_bytes()


def verify_source(data):
    """Pin raw bytes to the recorded source identity."""
    digest = hashlib.sha256(bytes(data)).hexdigest()
    if digest != SOURCE_SHA256:
        raise HashMismatch("Source hash mismatch: " + digest)
    return digest


def decode_text(data):
    """Decode shift_jis source bytes; undecodable input fails closed."""
    return bytes(data).decode("shift_jis")


def _floor_params(raw):
    """Floor parameters with shared type-tag and key discipline enforced."""
    try:
        params = parameters(raw)
    except ValueError as error:
        raise UnsupportedDefinition("Bad floor params: " + str(error)) from None
    for at in range(0, len(raw) - 1, 3):
        key, size, value = raw[at:at + 3]
        if not isinstance(key, list) or len(key) != 1:
            raise UnsupportedDefinition("Malformed parameter framing")
        expected = "-1" if key[0] in STRING_FLOOR_KEYS else "4"
        if size != expected or not isinstance(value, str):
            raise UnsupportedDefinition("Parameter type mismatch: " + key[0])
        if key[0] not in KNOWN_FLOOR_KEYS:
            raise UnsupportedDefinition("Unsupported floor parameter: " + key[0])
    return params


def _caps(node):
    """Structural cap records: empty slots or opaque (token, weight, kind)."""
    if not isinstance(node, list) or not node:
        raise UnsupportedDefinition("Missing cap block")
    count = integer(node[0], 255)
    result = []
    cursor = 1
    for _ in range(count):
        if cursor >= len(node):
            raise UnsupportedDefinition("Truncated cap record")
        empty = integer(node[cursor], 255)
        cursor += 1
        if empty:
            result.append({"empty": True})
            continue
        if cursor + 2 >= len(node):
            raise UnsupportedDefinition("Truncated cap payload")
        token, weight, kind = node[cursor:cursor + 3]
        cursor += 3
        if not all(isinstance(v, str) for v in (token, weight, kind)):
            raise UnsupportedDefinition("Malformed cap payload")
        result.append({"empty": False, "token": token,
                       "source_weight": integer(weight),
                       "placement_type": integer(kind, 8)})
    if cursor != len(node):
        raise UnsupportedDefinition("Trailing cap data")
    return result


def structural_scan(text):
    """Decode floor coverage, pools and opaque roster rows without ID sets.

    Enemy/treasure/cap tokens stay observed source strings; semantic
    resolution against enemy/pellet catalogs is an explicit P1 item.
    """
    try:
        nodes = tree(text)
    except ValueError as error:
        raise UnsupportedDefinition("Unparseable stream: " + str(error)) from None
    if len(nodes) < 2 or not isinstance(nodes[0], list):
        raise UnsupportedDefinition("Missing cave header")
    try:
        header = parameters(nodes[0])
        count = integer(nodes[1], 128)
    except ValueError as error:
        raise UnsupportedDefinition("Malformed header: " + str(error)) from None
    if set(header) != {"c000"} or count < 1 or integer(header["c000"], 128) != count:
        raise UnsupportedDefinition("Cave definition count mismatch")
    floors = []
    occupied = set()
    cursor = 2
    for index in range(count):
        if cursor + 4 >= len(nodes):
            raise UnsupportedDefinition("Truncated floor %d" % (index + 1))
        block = nodes[cursor:cursor + 5]
        cursor += 5
        if any(not isinstance(part, list) for part in block):
            raise UnsupportedDefinition("Malformed floor framing")
        params = _floor_params(block[0])
        for key in ("f000", "f001", "f008"):
            if key not in params:
                raise UnsupportedDefinition("Incomplete floor parameters")
        try:
            first = integer(params["f000"], 127)
            last = integer(params["f001"], 127)
            pool = safe_name(params["f008"])
            light = safe_name(params.get("f009", "none"))
            vrbox = safe_name(params.get("f00A", "none"))
        except ValueError as error:
            raise UnsupportedDefinition("Invalid parameter: " + str(error)) from None
        if first > last or occupied.intersection(range(first, last + 1)):
            raise UnsupportedDefinition("Overlapping/inverted floor range")
        occupied.update(range(first, last + 1))
        try:
            enemies = [{"token": token, "source_weight": integer(weight),
                        "placement_type": integer(kind, 8)}
                       for token, weight, kind in rows(block[1], 3)]
            treasures = [{"token": token, "source_weight": integer(weight)}
                         for token, weight in rows(block[2], 2)]
            gates = [{"gate_id": name, "life": life, "selection_weight": weight}
                     for name, life, weight in rows(block[3], 3)]
            caps = _caps(block[4])
        except ValueError as error:
            raise UnsupportedDefinition("Malformed roster: " + str(error)) from None
        for gate in gates:
            if not gate["gate_id"].startswith("gate"):
                raise UnsupportedDefinition("Unknown cave gate type")
        floors.append({"definition_index": index, "first_floor": first + 1,
                       "last_floor": last + 1, "unit_pool": pool, "light": light,
                       "vrbox": vrbox, "parameters": params, "enemies": enemies,
                       "treasures": treasures, "gates": gates, "caps": caps})
    if cursor != len(nodes):
        raise UnsupportedDefinition("Trailing cave data")
    covered = sorted(occupied)
    if [f + 1 for f in covered] != list(range(1, len(covered) + 1)):
        raise UnsupportedDefinition("Discontiguous floor coverage")
    return {"cave_id": CAVE_ID, "source": CAVE_PATH, "floor_count": len(covered),
            "floors": floors, "generated": False}


def decode_full(text, enemy_ids, treasure_ids):
    """Shared-parser decode; caller supplies authoritative ID sets."""
    try:
        return parse(text, enemy_ids, treasure_ids)
    except ValueError as error:
        raise UnsupportedDefinition("Shared decode rejected input: " + str(error)) from None


def load_enemy_ids(path=RESEARCH_ENEMYINFO):
    """Read-only enemy-ID set for shared-parser resolution (local runs only)."""
    raw = source_bytes(path).decode("utf-8")
    return set(re.findall(r'\{"([A-Za-z0-9_]+)"', raw))


def asset_closure(scan, catalog):
    """Check referenced pool/light assets against an explicit catalog mapping.

    ``catalog`` maps disc-relative asset paths to True; nothing is read from
    disc here. A ``None`` catalog leaves every asset explicitly unverified.
    """
    assets = []
    for floor in scan["floors"]:
        refs = {"unit_pool": UNIT_POOL_DIR + floor["unit_pool"]}
        if floor["light"] != "none":
            refs["light"] = LIGHT_DIR + floor["light"]
        for name, path in refs.items():
            if catalog is None:
                status = "unverified"
            else:
                status = "present" if catalog.get(path) else "missing"
            assets.append({"floor": floor["first_floor"], "kind": name,
                           "path": path, "status": status})
    return assets


def import_contract(scan, assets):
    """Reviewed P0 packet: identity, coverage, observed refs, open items."""
    observed_enemies = sorted({e["token"] for f in scan["floors"] for e in f["enemies"]})
    observed_treasures = sorted({t["token"] for f in scan["floors"] for t in f["treasures"]})
    observed_caps = sorted({c["token"] for f in scan["floors"]
                            for c in f["caps"] if not c["empty"]})
    open_refs = observed_enemies + observed_treasures + observed_caps
    return {
        "schema": 1,
        "cave_id": CAVE_ID,
        "source": CAVE_PATH,
        "source_sha256": SOURCE_SHA256,
        "ui_index": UI_INDEX,
        "table_order": TABLE_ORDER,
        "floor_coverage": [f["first_floor"] for f in scan["floors"]],
        "floor_manifest": [
            {"floor": f["first_floor"], "unit_pool": f["unit_pool"],
             "light": f["light"], "enemy_rows": len(f["enemies"]),
             "treasure_rows": len(f["treasures"]),
             "gate_rows": len(f["gates"]), "cap_rows": len(f["caps"])}
            for f in scan["floors"]
        ],
        "observed_enemy_tokens": observed_enemies,
        "observed_treasure_tokens": observed_treasures,
        "observed_cap_tokens": observed_caps,
        "timer_roster_spray_baseline": dict(BASELINE),
        "asset_closure": assets,
        "semantic_resolution": "open",
        "open_references": open_refs,
        "blockers": list(BLOCKERS),
        "limitations": list(LIMITATIONS),
        "generated": False,
    }
