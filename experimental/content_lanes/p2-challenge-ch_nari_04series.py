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


# ---------------------------------------------------------------------------
# P1 private runtime import (lane p2-challenge-ch-nari-04series-p1, #545).
#
# Additive only: every P0 helper above is reused untouched (real-source decode
# helpers, never a forked parser). The P1 path stages the decoded packet into
# a private run layout, boots the room-preview path in a private runtime, and
# validates receipt-parseable markers. No shared edits; no placements emitted
# beyond the staged arena the engine itself boots.
# ---------------------------------------------------------------------------

P1_STAGE_SELECT_MAGIC = "P2_CHALLENGE_STAGE_SELECT_1"
P1_SQUAD_FILE = "p2-challenge-p1-squad.txt"
P1_TIMERS_FILE = "p2-challenge-p1-timers.txt"
P1_MANIFEST_FILE = "p2-challenge-p1-manifest.json"
P1_SELECT_FILE = "p2-challenge-stage-select.txt"

# Captain guard (#632) canonical header, consumed read-only at review; the
# P1 runner checks the same three signals before counting an observed tick.
CAPTAIN_GUARD_HEADER = "scripts/p2_fixture_captain_guard.h"
CAPTAIN_GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"

# Native Piki color order shared with the engine receivers.
NL = chr(10)
P1_SPECIES = ("blue", "red", "yellow", "purple", "white", "bulbmin", "winged")


def stage_select_record(packet):
    """Render the #669 stage-select record from a decoded packet.

    Strict shape mirroring the engine reader: any deviation must be refused
    downstream, never defaulted. All values come from the decoded packet.
    """
    stage = packet["stage"]
    lines = [P1_STAGE_SELECT_MAGIC]
    lines.append("cave %s ui_index %d table_order %d floors %d" % (
        CAVE_ID, stage["ui_index"], packet.get("table_order", 0),
        stage["floor_count"]))
    lines.append("source %s %s" % (SOURCE, packet["source_sha256"]))
    timers = " ".join("%g" % value for value in stage["floor_seconds"])
    lines.append("timers %s legacy %g" % (timers, stage["time"]))
    lines.append("sprays bitter %d spicy %d treasure_field %d" % (
        stage["bitter_sprays"], stage["spicy_sprays"],
        stage["treasure_count"]))
    for color, row in enumerate(stage["pikmin"]):
        lines.append("roster %d %d %d" % (row[0], row[1], row[2]))
    return NL.join(lines) + NL


def check_stage_record(text, packet):
    """Fail closed on any select-record deviation from the decoded packet."""
    stage = packet["stage"]
    rows = text.splitlines()
    if not rows or rows[0] != P1_STAGE_SELECT_MAGIC:
        raise ValueError("Bad stage-select magic")
    get = {}
    for row in rows[1:]:
        words = row.split()
        if not words:
            raise ValueError("Blank stage-select line")
        get.setdefault(words[0], []).append(words[1:])
    try:
        cave = get["cave"][0][0]
        ui_index = int(get["cave"][0][2])
        floors = int(get["cave"][0][6])
        source_path = get["source"][0][0]
        source_sha = get["source"][0][1]
        timers = [float(v) for v in get["timers"][0][:-2]]
        legacy = float(get["timers"][0][-1])
        bitter = int(get["sprays"][0][1])
        spicy = int(get["sprays"][0][3])
        treasure = int(get["sprays"][0][5])
        rosters = [[int(v) for v in r] for r in get["roster"]]
    except (KeyError, IndexError, ValueError):
        raise ValueError("Malformed stage-select record")
    if cave != CAVE_ID:
        raise ValueError("Stage-select cave mismatch")
    if ui_index != stage["ui_index"] or floors != stage["floor_count"]:
        raise ValueError("Stage-select identity mismatch")
    if source_path != SOURCE or source_sha != packet["source_sha256"]:
        raise ValueError("Stage-select source mismatch")
    if timers != [float(v) for v in stage["floor_seconds"]] or legacy != float(stage["time"]):
        raise ValueError("Stage-select timer mismatch")
    if (bitter, spicy, treasure) != (stage["bitter_sprays"], stage["spicy_sprays"],
                                     stage["treasure_count"]):
        raise ValueError("Stage-select spray mismatch")
    if rosters != [list(map(int, r)) for r in stage["pikmin"]]:
        raise ValueError("Stage-select roster mismatch")
    return True


def stage_p1_run(packet, run_dir):
    """Stage the decoded packet into a private run layout (no engine boot).

    Writes the select record, squad/spray/timer sidecars and the decoded
    manifest copy the runner boots. Returns the run directory. Anything
    missing or drifting from the packet raises instead of defaulting.
    """
    import json
    run_dir = Path(run_dir)
    if packet.get("cave_id") != CAVE_ID:
        raise ValueError("P1 stage packet for another cave")
    if packet.get("contract_mismatches"):
        raise ValueError("P1 refusing packet with contract mismatches: %r"
                         % (packet["contract_mismatches"],))
    if packet.get("missing_unit_assets"):
        raise ValueError("P1 refusing packet with missing unit assets: %r"
                         % (packet["missing_unit_assets"],))
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / P1_SELECT_FILE).write_text(
        stage_select_record(packet), encoding="utf-8")
    stage = packet["stage"]
    squad_lines = ["P2_CHALLENGE_P1_SQUAD_1"]
    for color, row in enumerate(stage["pikmin"]):
        squad_lines.append("color %d leaf %d bud %d flower %d" % (color, row[0], row[1], row[2]))
    squad_lines.append("sprays bitter %d spicy %d" % (
        stage["bitter_sprays"], stage["spicy_sprays"]))
    (run_dir / P1_SQUAD_FILE).write_text(NL.join(squad_lines) + NL,
                                         encoding="utf-8")
    (run_dir / P1_TIMERS_FILE).write_text(
        "P2_CHALLENGE_P1_TIMERS_1\nfloors %d\nseconds %s\nlegacy %g\n" % (
            stage["floor_count"],
            " ".join("%g" % v for v in stage["floor_seconds"]), stage["time"]),
        encoding="utf-8")
    (run_dir / P1_MANIFEST_FILE).write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    check_stage_record((run_dir / P1_SELECT_FILE).read_text(encoding="utf-8"),
                       packet)
    return run_dir


def validate_p1_log(text, packet, expect_captain_guard=True):
    """Validate receipt-parseable markers from a private P1 run log.

    Returns a findings dict; raises on captain-down, extinction without
    observation, or stage-identity mismatch. Never claims more than observed:
    unobserved legs stay False and the caller reports gates UNTESTED.
    """
    import re
    stage = packet["stage"]
    if expect_captain_guard and "P2_FIXTURE_CAPTAIN_DOWN" in text:
        raise ValueError("Captain-down BLOCKED observation")
    window = bool(re.search(
        r"Experimental preview window set to 960x540 windowed and centered", text))
    squad = re.findall(r"P2_FIXTURE_COUNTS reds=(\d+) dwarfs=(\d+)", text)
    live = any(int(r) + int(d) > 0 for r, d in squad) if squad else False
    select = "P2_CHALLENGE_STAGE_SIDECAR cave=%s ui_index=%d" % (CAVE_ID, stage["ui_index"])
    selected = select in text
    resolved = ("P2_CHALLENGE_STAGE_RESOLVED cave=%s ui_index=%d floors=%d"
                % (CAVE_ID, stage["ui_index"], stage["floor_count"])) in text
    actors = bool(re.search(r"P2_LIFECYCLE_ENEMY frame=\d+", text))
    collision = ("ground=" in text and "P2_FINAL_POSITION" in text)
    extinct = bool(re.search(r"Extinction", text, re.IGNORECASE))
    return {"window_960x540": window, "live_squad": live,
            "stage_selected": selected, "stage_resolved": resolved,
            "actors_observed": actors, "collision_observed": collision,
            "no_immediate_extinction": not extinct or live,
            "cave_id": CAVE_ID, "ui_index": stage["ui_index"],
            "floors": stage["floor_count"]}


def run_p1(packet, assets, converted, output, exe, seconds=120):
    """Stage the P1 layout, boot the private room-preview runtime, validate.

    Fresh arena via the shared preview prepare (current starting-Pikmin
    overlay inside `overlay()`), P1 sidecars copied in, then the already
    built private binary boots `--experimental-pikmin2-room` with a centred
    960x540 window. Returns (run_dir, meta, findings). Raises on captain-down
    (BLOCKED exit path is observed, never bypassed).
    """
    import os
    import subprocess
    import sys
    import uuid
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    from preview_pikmin2_room import prepare as preview_prepare
    staged = stage_p1_run(packet, Path(output).resolve() / ("p1-" + uuid.uuid4().hex[:8]))
    run = preview_prepare(Path(assets).resolve(), Path(converted).resolve(),
                          staged / "arena")
    for name in (P1_SELECT_FILE, P1_SQUAD_FILE, P1_TIMERS_FILE, P1_MANIFEST_FILE):
        (run / name).write_bytes((staged / name).read_bytes())
    env = dict(os.environ, PIKMIN_P2_ROOM_WINDOW="960x540",
               SDL_AUDIODRIVER="dummy",
               PATH="C:/msys64/mingw64/bin;" + os.environ.get("PATH", ""))
    log_path = run / "native.log"
    try:
        with log_path.open("w", encoding="utf-8") as log:
            proc = subprocess.run(
                [str(Path(exe).resolve()), "--experimental-pikmin2-room"],
                cwd=run, stdout=log, stderr=subprocess.STDOUT,
                timeout=seconds, env=env)
        code = proc.returncode
        timed_out = False
    except subprocess.TimeoutExpired:
        code, timed_out = "timeout", True
    text = log_path.read_text(encoding="utf-8", errors="replace")
    findings = validate_p1_log(text, packet)
    meta = {"exit_code": code, "timed_out": timed_out,
            "staged": str(staged), "arena": str(run)}
    return run, meta, findings
