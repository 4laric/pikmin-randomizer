"""P0 import-contract adapter for P2 Challenge 17: ch_NARI_06start3hard (#549).

Lane p2-challenge-ch_nari_06start3hard, phase P0 (source audit and additive
import contract). This module consumes two already-catalogued JSON inputs and
produces one validated import-contract packet for THIS stage only:

- the lane-plan entry (docs/PIKMIN_CONTENT_IMPORT_LANES.json): source path
  with hash pin, table order, UI index, floor count and timers, starting
  Pikmin populations by native color/maturity, sprays and legacy time;
- the inventory challenge collection (docs/PIKMIN2_CONTENT_INVENTORY.json):
  the 30-stage table with the same row, the stages.txt hash pin and the
  per-stage caveinfo hash pins.

It decodes no caveinfo itself: the disc source
(user/Mukki/mapunits/caveinfo/ch_NARI_06start3hard.txt) was unavailable to
this turn, so per-floor enemy rosters stay an explicit open decode and the
packet records recorded hashes as evidence pins, never re-extracted bytes.
No placements, timers-as-gameplay, scores or completion claims are emitted:
floor_seconds are preserved definition inputs for the P1 framework (#136).

Fail-closed: any identity/detail/collection/hash mismatch raises ValueError.
Stdlib only.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_cave import unit_definition
from experimental.pikmin2_cave_catalog import parse as parse_cave
from experimental.pikmin2_pod import pellet_catalog

LANE = "p2-challenge-ch_nari_06start3hard"
SOURCE_ID = "ch_NARI_06start3hard"
LABEL = "P2 Challenge 17: ch_NARI_06start3hard"
SOURCE_PATH = "user/Mukki/mapunits/caveinfo/ch_NARI_06start3hard.txt"
STAGES_TXT = "user/Matoba/challenge/stages.txt"
ISSUE = 549
PARENT_ISSUE = 137

# Exact P0 contract pinned from the lane plan and issue #549.
TABLE_ORDER = 25
UI_INDEX = 16
FLOORS = 3
PIKMIN_MATRIX = ((0, 0, 0), (0, 0, 4), (0, 0, 0), (0, 0, 0),
                 (0, 0, 0), (0, 0, 0), (0, 0, 0))
LEGACY_TIME = 450.0
BITTER_SPRAYS = 2
SPICY_SPRAYS = 3
TREASURE_COUNT_FIELD = 0
FLOOR_SECONDS = (100.0, 150.0, 180.0)
STAGE_COUNT = 30

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
    _require(inventory_stage.get("cave_id") == SOURCE_ID, "Inventory stage mismatch")
    _require(inventory_stage.get("cave_path") == SOURCE_PATH, "Inventory path drift")
    _require(inventory_stage.get("issue") == PARENT_ISSUE, "Inventory issue drift")
    return {"lane": LANE, "source_id": SOURCE_ID, "label": LABEL,
            "source": SOURCE_PATH, "issue": ISSUE}


def verify_details(plan_entry, inventory_stage):
    """Every stage metadata field must match the pinned contract exactly in
    both sources: order/UI indices, floor count and per-floor timers,
    starting populations, sprays, legacy time and treasure-count field."""
    details = plan_entry.get("details", {})
    for source, name in ((details, "plan"), (inventory_stage, "inventory")):
        _require(source.get("table_order") == TABLE_ORDER,
                 "%s table_order drift" % name)
        _require(source.get("cave_id") == SOURCE_ID, "%s cave_id drift" % name)
        _require(source.get("ui_index") == UI_INDEX, "%s ui_index drift" % name)
        _require(source.get("floors") == FLOORS, "%s floor count drift" % name)
        matrix = source.get("pikmin_by_native_color_and_maturity")
        _require(isinstance(matrix, list) and len(matrix) == 7,
                 "%s population matrix shape drift" % name)
        for row in matrix:
            _require(isinstance(row, list) and len(row) == 3
                     and all(isinstance(v, int) and not isinstance(v, bool) and v >= 0
                             for v in row),
                     "%s population row drift" % name)
        _require(tuple(tuple(row) for row in matrix) == PIKMIN_MATRIX,
                 "%s population drift" % name)
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
    _require(STAGES_TXT in inventory_hashes, "Missing stages.txt hash")
    stages_hash = check_hash(inventory_hashes[STAGES_TXT], STAGES_TXT)
    _require(SOURCE_PATH in inventory_hashes, "Missing stage caveinfo hash")
    stage_hash = check_hash(inventory_hashes[SOURCE_PATH], SOURCE_PATH)
    _require(stage_hash == check_hash(plan_source_sha256, "plan source pin"),
             "Caveinfo pin differs between plan and inventory")
    return {"stages": STAGE_COUNT, "stages_txt": STAGES_TXT,
            "stages_txt_sha256": stages_hash, "stage_sha256": stage_hash}


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


def packet(plan_entry, inventory_stage, inventory_challenge, inventory_hashes):
    """Build the validated P0 import-contract packet. No gameplay emitted."""
    identity = verify_identity(plan_entry, inventory_stage)
    details = verify_details(plan_entry, inventory_stage)
    collection = verify_collection(inventory_challenge, inventory_hashes,
                                   plan_entry.get("source_sha256"))
    result = {"schema": 1, "lane": LANE, "phase": "P0",
              "identity": identity,
              "details": details,
              "collection": collection,
              "ledger": ledger(),
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
                  "English title unresolved; source ID ch_NARI_06start3hard "
                  "and UI index 16 are authoritative, never guessed.",
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


# ---------------------------------------------------------------------------
# P1 private runtime import path (lane p2-challenge-ch_nari_06start3hard-p1,
# issue #549). Extends the P0 contract above: reuses the pinned P0 constants
# and ledger() helpers, decodes the two live sources through the shared
# retail parser (no forked parser), and stages the decoded stage manifest
# into a private run layout consumed by the integrated Challenge
# content-loading boot path (#701 binder) plus the host-mode module contract
# (native/pc_port/pc_p2_challenge_mode.h StageEntry shape).
# ---------------------------------------------------------------------------

CAVEINFO_PATH = SOURCE_PATH
PELLET_ARCHIVE = "user/Abe/Pellet/us/pelletlist_us.szs"
ENEMYINFO = "src/plugProjectYamashitaU/enemyInfo.cpp"
DEFAULT_ISO = Path("C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso")
DEFAULT_RESEARCH = Path("C:/Users/alari/pikmin-randomizer/native/pikmin2-research")
COLORS = 7
MATURITY = 3

P1_WINDOW = "960x540"
RUN_LAYOUT_FILES = ("p2-challenge-content.txt", "p2-cave-generate.txt",
                    "stage-manifest.json", "preview.json")
ANCHOR_BY_RETURN = {"0": "hole", "1": "geyser"}

# Receipt-parseable runtime markers (content-loading boot path + room preview).
CONTENT_SELECTED = "P2_CHALLENGE_CONTENT_SELECTED"
CONTENT_SPAWN_COVERED = "P2_CHALLENGE_CONTENT_SPAWN_COVERED"
CONTENT_READY = "P2_CHALLENGE_CONTENT_READY"
CONTENT_LIVE = "P2_CHALLENGE_CONTENT_LIVE"
CONTENT_PASS = "PASS P2_CHALLENGE_CONTENT_RUN"
COLLISION_MARKER = "P2_ROOM_GROUND"
ACTOR_MARKER = "P2_PLACEMENT_PROBE"
CAPTAIN_DOWN_MARKER = "P2_FIXTURE_CAPTAIN_DOWN"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"


def p1_contract():
    """Lane stage contract rebuilt from the pinned P0 constants (single source)."""
    return dict(lane=LANE, source_id=SOURCE_ID, cave_path=CAVEINFO_PATH,
                table_order=TABLE_ORDER, cave_id=SOURCE_ID, floors=FLOORS,
                pikmin=[list(row) for row in PIKMIN_MATRIX],
                legacy_time=LEGACY_TIME, bitter_sprays=BITTER_SPRAYS,
                spicy_sprays=SPICY_SPRAYS, treasure_count=TREASURE_COUNT_FIELD,
                ui_index=UI_INDEX, floor_seconds=list(FLOOR_SECONDS))


def check_lane_entry(lanes_path):
    """The lanes document must carry this lane with details equal to the P0 pins."""
    try:
        lanes = json.loads(Path(lanes_path).read_text(encoding="utf-8"))["lanes"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError("Unreadable lanes document: %s" % error)
    entries = [entry for entry in lanes if entry.get("lane") == LANE]
    if len(entries) != 1:
        raise ValueError("Lane %r must appear exactly once" % LANE)
    details = entries[0].get("details") or {}
    expected = p1_contract()
    for key in ("cave_path", "cave_id", "table_order", "floors", "legacy_time",
                "bitter_sprays", "spicy_sprays",
                "ui_index", "floor_seconds"):
        _require(details.get(key) == expected[key],
                 "Lane entry %r drift" % key)
    _require(details.get("treasure_count_field") == expected["treasure_count"],
             "Lane entry 'treasure_count' drift")
    _require(details.get("pikmin_by_native_color_and_maturity") == expected["pikmin"],
             "Lane entry pikmin matrix drift")
    return True


def read_iso_file(iso_path, disc_path):
    """Read one file from the local disc image and return (bytes, sha256)."""
    iso = Path(iso_path)
    try:
        catalog = disc_files(iso)
    except (OSError, ValueError) as error:
        raise ValueError("Unreadable disc image: %s" % error)
    if disc_path not in catalog:
        raise ValueError("Disc entry missing: " + disc_path)
    at, size = catalog[disc_path]
    try:
        with iso.open("rb") as disc:
            disc.seek(at)
            data = disc.read(size)
    except OSError as error:
        raise ValueError("Disc read failed: %s" % error)
    if len(data) != size:
        raise ValueError("Truncated disc source: " + disc_path)
    return data, hashlib.sha256(data).hexdigest()


def reference_ids(iso_path, research_root):
    """Enemy IDs from the research source plus treasure IDs from the disc pellet
    archive. These are the exact decoder inputs the shared parser requires."""
    enemy_source = Path(research_root) / ENEMYINFO
    try:
        raw = enemy_source.read_bytes().decode("utf-8")
    except OSError as error:
        raise ValueError("Missing research enemy catalog: %s" % error)
    enemy_ids = set(re.findall(r"\{\"([A-Za-z0-9_]+)\"", raw))
    if not enemy_ids:
        raise ValueError("No enemy IDs decoded from research source")
    archive_data, _ = read_iso_file(iso_path, PELLET_ARCHIVE)
    try:
        archive = archive_files(archive_data)
        treasure_ids = set()
        for name in ("otakara_config.txt", "item_config.txt"):
            treasure_ids.update(pellet_catalog(archive[name].decode("shift_jis")))
    except (ValueError, KeyError) as error:
        raise ValueError("Unreadable pellet archive: %s" % error)
    if not treasure_ids:
        raise ValueError("No treasure IDs decoded from pellet archive")
    return enemy_ids, treasure_ids


def decode_cave(iso_path, research_root, source=CAVEINFO_PATH):
    """Decode the actual cave definition from local sources.

    Returns (cave, file_sha256). Weights are definition inputs, never spawn
    instances.
    """
    data, digest = read_iso_file(iso_path, source)
    try:
        text = data.decode("shift_jis")
    except UnicodeDecodeError as error:
        raise ValueError("Caveinfo is not shift_jis: %s" % error)
    enemy_ids, treasure_ids = reference_ids(iso_path, research_root)
    try:
        cave = parse_cave(text, enemy_ids, treasure_ids)
    except ValueError as error:
        raise ValueError("Retail definition failed shared parse: %s" % error)
    cave.update(cave_id=SOURCE_ID, source=source)
    return cave, digest


def split_stage_blocks(text):
    """Split stages.txt into raw stage-block strings (header discarded)."""
    chunks = re.split(r"^# stage[ \t]*$", text, flags=re.MULTILINE)
    if len(chunks) < 2:
        raise ValueError("No stage blocks in challenge stage table")
    head = chunks[0].strip().splitlines()
    if not head or not re.fullmatch(r"\d+", head[0].split("#")[0].strip()):
        raise ValueError("Stage table missing leading stage count")
    return chunks[1:]


def parse_stage_block(block):
    """Strictly parse one stage block into stage metadata.

    Layout (comment-labeled, fail closed on any deviation): `{`, version line,
    cave filename line, `# PikiCounter`, 21 `col/maturity` counter lines,
    legacy time, bitter dopes, spicy dopes, floor count, otakara count,
    2d index, then exactly floor-count per-floor second lines, `}`.
    """
    lines = [line for line in block.splitlines() if line.strip()]
    if len(lines) < 2 or lines[0].strip() != "{":
        raise ValueError("Stage block must open with brace")
    cursor = 1

    def take(pattern, label):
        nonlocal cursor
        if cursor >= len(lines):
            raise ValueError("Truncated stage block at " + label)
        match = re.fullmatch(pattern, lines[cursor].strip())
        if not match:
            raise ValueError("Stage block field %r mismatch: %r" % (label, lines[cursor].strip()))
        cursor += 1
        return match

    take(r"\d+\s+#\s*version", "version")
    cave = take(r"(ch_[A-Za-z0-9_]+\.txt)\s*", "cave reference").group(1)
    take(r"#\s*PikiCounter", "PikiCounter header")
    pikmin = []
    for color in range(COLORS):
        row = []
        for maturity in range(MATURITY):
            value = take(r"(\d+)\s+#\s*col%d\s+happa%d" % (color, maturity),
                         "col%d happa%d" % (color, maturity)).group(1)
            row.append(int(value))
        pikmin.append(row)
    legacy_time = float(take(r"(\d+(?:\.\d+)?)\s+#\s*time", "time").group(1))
    bitter = int(take(r"(\d+)\s+#\s*dope black", "dope black").group(1))
    spicy = int(take(r"(\d+)\s+#\s*dope red", "dope red").group(1))
    floors = int(take(r"(\d+)\s+#\s*floor num", "floor num").group(1))
    treasures = int(take(r"(\d+)\s+#\s*otakara num", "otakara num").group(1))
    ui_index = int(take(r"(\d+)\s+#\s*2d index", "2d index").group(1))
    seconds = []
    for index in range(floors):
        mark = str(index + 1) + "\u968e\u306e\u79d2\u6570"
        value = take(r"(\d+(?:\.\d+)?)\s+#\s*" + mark, "floor seconds %d" % (index + 1)).group(1)
        seconds.append(float(value))
    if cursor >= len(lines) or lines[cursor].strip() != "}":
        raise ValueError("Stage block must close with brace")
    cursor += 1
    if cursor != len(lines):
        raise ValueError("Trailing data in stage block")
    return dict(cave_file=cave, pikmin=pikmin, legacy_time=legacy_time,
                bitter_sprays=bitter, spicy_sprays=spicy, floors=floors,
                treasure_count=treasures, ui_index=ui_index, floor_seconds=seconds)


def decode_stage(iso_path, cave_file=SOURCE_ID + ".txt"):
    """Decode this lane's stage row from the live challenge stage table.

    Returns (stage, table_sha256). Exactly one block may reference the file.
    """
    data, digest = read_iso_file(iso_path, STAGES_TXT)
    try:
        text = data.decode("shift_jis").replace(chr(13) + chr(10), chr(10))
    except UnicodeDecodeError as error:
        raise ValueError("Stage table is not shift_jis: %s" % error)
    matches = []
    for block in split_stage_blocks(text):
        try:
            stage = parse_stage_block(block)
        except ValueError:
            continue
        if stage["cave_file"] == cave_file:
            matches.append(stage)
    if len(matches) != 1:
        raise ValueError("Stage table must reference %r exactly once" % cave_file)
    return matches[0], digest


def verify_stage(stage, contract):
    """Cross-check a decoded stage row against the lane stage contract."""
    for key in (("pikmin", "pikmin"), ("legacy_time", "legacy_time"),
                ("bitter_sprays", "bitter_sprays"), ("spicy_sprays", "spicy_sprays"),
                ("treasure_count", "treasure_count"), ("ui_index", "ui_index"),
                ("floor_seconds", "floor_seconds"), ("floors", "floors")):
        if stage[key[0]] != contract[key[1]]:
            raise ValueError("Stage field %r diverges from contract" % key[0])
    return dict(cave_file=stage["cave_file"], floors=stage["floors"],
                starting_pikmin=sum(sum(row) for row in stage["pikmin"]),
                floor_seconds=stage["floor_seconds"], ui_index=stage["ui_index"])


def verify_cave_contract(cave, contract):
    """Cross-check the decoded cave definition: identity, full floor cover,
    per-floor unit pools and complete enemy/item/gate/cap rosters (recorded,
    not placed)."""
    if cave.get("cave_id") != contract["source_id"]:
        raise ValueError("Decoded identity does not match lane contract source")
    if cave.get("floor_count") != contract["floors"] or len(cave.get("floors", ())) != contract["floors"]:
        raise ValueError("Decoded floor records do not cover the contract")
    coverage = []
    for floor in cave["floors"]:
        coverage.append(dict(floor=floor["first_floor"], last=floor["last_floor"],
                             unit_pool=floor["parameters"].get("f008"),
                             enemies=[dict(source_token=e["source_token"], enemy_id=e["enemy_id"],
                                           carried_treasure=e["carried_treasure"],
                                           source_weight=e["source_weight"],
                                           placement_type=e["placement_type"]) for e in floor["enemies"]],
                             treasures=[dict(treasure_id=t["treasure_id"], source_weight=t["source_weight"])
                                        for t in floor["treasures"]],
                             gates=floor["gates"], caps=floor["caps"]))
    ranges = [(row["floor"], row["last"]) for row in coverage]
    if ranges != [(index, index) for index in range(1, contract["floors"] + 1)]:
        raise ValueError("Challenge floor ranges must tile 1..floors exactly once")
    return coverage


def decode_pool_live(iso_path, pool):
    """Decode a unit pool definition live from the disc (fallback when the
    story-cave baseline catalog does not cover it). Verifies every referenced
    unit asset (arc.szs/texts.szs) exists in the disc table of contents, exactly
    like the shared inventory audit. Returns (entry, pool_sha256)."""
    poolpath = "user/Mukki/mapunits/units/" + pool
    data, digest = read_iso_file(iso_path, poolpath)
    try:
        text = data.decode("shift_jis")
    except UnicodeDecodeError as error:
        raise ValueError("Unit pool is not shift_jis: %s" % error)
    try:
        definitions = unit_definition(text)
    except ValueError as error:
        raise ValueError("Unit pool failed shared parse: %s" % error)
    iso = Path(iso_path)
    try:
        toc = disc_files(iso)
    except (OSError, ValueError) as error:
        raise ValueError("Unreadable disc table: %s" % error)
    for unit in definitions:
        for suffix in ("arc.szs", "texts.szs"):
            if "user/Mukki/mapunits/arc/" + unit["name"] + "/" + suffix not in toc:
                raise ValueError("Missing unit asset for " + unit["name"])
    return dict(source=poolpath, units=definitions), digest


def verify_closure(cave, catalog, iso_path=None):
    """Verify unit-pool resource closure.

    Pools present in the existing catalog baseline resolve there (provenance
    `baseline`); a pool the baseline does not cover is decoded live from the
    disc with asset-reference checks (provenance `live`) instead of failing the
    whole audit on a baseline gap. Without `iso_path`, a missing pool still
    fails closed. Returns (closure, pool_hashes).
    """
    pools = catalog.get("unit_pools") or {}
    closure = []
    pool_hashes = {}
    for floor in cave["floors"]:
        pool = floor["parameters"].get("f008")
        entry = pools.get(pool)
        provenance = "baseline"
        if not entry or not entry.get("units"):
            if iso_path is None:
                raise ValueError("Unit pool without decoded closure: %r" % pool)
            entry, digest = decode_pool_live(iso_path, pool)
            pool_hashes[pool] = digest
            provenance = "live"
        closure.append(dict(floor=floor["first_floor"], unit_pool=pool,
                            source=entry.get("source"), provenance=provenance,
                            units=[unit["name"] for unit in entry["units"]]))
    return closure, pool_hashes


def p1_blockers(coverage, closure):
    """Exact native/framework prerequisites for the P1 runtime import."""
    pools = sorted({row["unit_pool"] for row in closure})
    return [
        "Native cave/generator import hook for caveinfo definitions plus Challenge-mode "
        "stage bootstrap (PikiCounter roster, dopes, floor timers, 2d index) "
        "(integration owner); the staged manifest decodes definitions only and wires no native path.",
        "Unit-pool asset staging for %s via the existing unit pipeline; the manifest records "
        "pool sources, not staged assets." % ", ".join(pools),
        "Seeded topology/hole selection and generator pins are unproven for these %d floors; "
        "weights in the manifest are definition inputs, not placements." % len(coverage),
        "Enemy admission resolved per enemy roster at P1; unresolved admission blocks "
        "promotion, not this preparatory manifest; no host chal0 fixture treated as Challenge mode.",
    ]


def floor_manifest(cave, index):
    """Per-floor staging manifest: unit pool, anchor and spawn intents.

    Spawn intents aggregate the decoded roster by token (deterministic sorted
    order); they are definition inputs, never placements.
    """
    floors = cave.get("floors") or []
    if index < 0 or index >= len(floors):
        raise ValueError("Floor index out of range: %r" % (index,))
    floor = floors[index]
    pool = (floor.get("parameters") or {}).get("f008")
    if not pool or not re.fullmatch(r"[A-Za-z0-9_.\-]+\.txt", pool):
        raise ValueError("Floor %d has no usable unit pool" % (index + 1))
    counts = {}
    for entry in floor.get("enemies", []):
        token = entry.get("source_token") or entry.get("enemy_id")
        if not token:
            raise ValueError("Enemy entry without a source token")
        counts[token] = counts.get(token, 0) + 1
    for entry in floor.get("treasures", []):
        token = entry.get("treasure_id")
        if not token:
            raise ValueError("Treasure entry without an id")
        counts[token] = counts.get(token, 0) + 1
    if not counts:
        raise ValueError("Floor %d has an empty roster" % (index + 1))
    anchor = ANCHOR_BY_RETURN.get(str((floor.get("parameters") or {}).get("f007")), "hole")
    return dict(floor=floor.get("first_floor"), unit_pool=pool, anchor=anchor,
                spawns=[dict(id=key, count=counts[key]) for key in sorted(counts)],
                gates=list(floor.get("gates", [])))


def content_sidecar(manifest):
    """Exact `p2-challenge-content.txt` text the #701 binder consumes."""
    lines = ["P2_CHALLENGE_CONTENT_1",
             "stage %s %d" % (SOURCE_ID, manifest["floor"]),
             "pool %s" % manifest["unit_pool"]]
    lines.extend("spawn %s %d" % (s["id"], s["count"]) for s in manifest["spawns"])
    lines.append("anchor %s" % manifest["anchor"])
    return "\n".join(lines) + "\n"


def generate_sidecar(manifest):
    """Exact `p2-cave-generate.txt` coverage text the #701 binder scans."""
    return "".join("spawn %s %d\n" % (s["id"], s["count"]) for s in manifest["spawns"])


def preview_record(units):
    """`preview.json` for the private room preview; room chosen deterministically."""
    names = [u for u in (units or []) if u]
    if not names:
        raise ValueError("No unit available for the preview room")
    room = next((u for u in names if u.startswith("room")), names[0])
    return {"room": room, "experimental": True, "ap": False, "save_resume": False}


def stage_manifest_record(cave, stage, cave_sha, table_sha):
    """Machine-readable staged stage manifest (source pins + per-floor intents)."""
    record_floors = []
    for index in range(len(cave.get("floors") or [])):
        manifest = floor_manifest(cave, index)
        record_floors.append(dict(floor=manifest["floor"],
                                  unit_pool=manifest["unit_pool"],
                                  anchor=manifest["anchor"],
                                  spawns=manifest["spawns"],
                                  enemy_rows=len(cave["floors"][index].get("enemies", [])),
                                  treasure_rows=len(cave["floors"][index].get("treasures", [])),
                                  gate_rows=len(cave["floors"][index].get("gates", []))))
    return dict(schema=1, lane=LANE, source_id=SOURCE_ID, source_sha256=cave_sha,
                stage_table_sha256=table_sha, floor_count=cave["floor_count"],
                floor_seconds=list(stage["floor_seconds"]), legacy_time=stage["legacy_time"],
                bitter_sprays=stage["bitter_sprays"], spicy_sprays=stage["spicy_sprays"],
                ui_index=stage["ui_index"],
                starting_pikmin=sum(sum(row) for row in stage["pikmin"]),
                preview_window=P1_WINDOW, floors=record_floors, generated=False)


def stage_run_layout(cave, stage, cave_sha, table_sha, closure, output, write=True):
    """Stage the decoded stage into a private run layout (boot floor = floor 1).

    Fail closed on any missing/undecodable input. With write=False the layout is
    computed and hashed but no file is written (used by focused tests).
    """
    if not (cave.get("floors") or []):
        raise ValueError("No decoded floors to stage")
    boot = floor_manifest(cave, 0)
    units = []
    for row in closure or []:
        if row.get("floor") == boot["floor"]:
            units = list(row.get("units") or [])
    record = stage_manifest_record(cave, stage, cave_sha, table_sha)
    files = {
        "p2-challenge-content.txt": content_sidecar(boot),
        "p2-cave-generate.txt": generate_sidecar(boot),
        "stage-manifest.json": json.dumps(record, indent=1, sort_keys=True) + "\n",
        "preview.json": json.dumps(preview_record(units), indent=1, sort_keys=True) + "\n",
    }
    digests = {name: hashlib.sha256(text.encode("utf-8")).hexdigest()
               for name, text in files.items()}
    if write:
        out = Path(output)
        out.mkdir(parents=True, exist_ok=True)
        for name, text in files.items():
            (out / name).write_text(text, encoding="utf-8")
    return dict(run_layout=str(Path(output)), files=sorted(files), sha256=digests,
                manifest=record, boot_floor=boot, window=P1_WINDOW)


def parse_run_markers(log_text):
    """Parse receipt-parseable runtime markers from a boot log."""
    text = log_text or ""
    lines = text.splitlines()

    def has(token):
        return any(token in line for line in lines)

    stage = None
    for line in lines:
        if CONTENT_SELECTED in line and "cave=" in line:
            stage = line.split("cave=")[-1].split()[0] if "cave=" in line else None
            break
    return dict(content_selected=has(CONTENT_SELECTED),
                spawn_covered=[line for line in lines if CONTENT_SPAWN_COVERED in line],
                ready=has(CONTENT_READY), live=has(CONTENT_LIVE),
                pass_run=has(CONTENT_PASS),
                collision=[line for line in lines if COLLISION_MARKER in line],
                actors=[line for line in lines if ACTOR_MARKER in line],
                captain_down=has(CAPTAIN_DOWN_MARKER),
                window_960x540=(P1_WINDOW in text), stage=stage)


def verify_receipt(markers, require_collision=True, require_actors=True):
    """Fail closed unless the runtime receipt carries the observed evidence."""
    if markers.get("captain_down"):
        raise ValueError("Captain-down run cannot substantiate a receipt")
    missing = []
    for key in ("content_selected", "ready", "live", "pass_run", "window_960x540"):
        if not markers.get(key):
            missing.append(key)
    if not markers.get("spawn_covered"):
        missing.append("spawn_covered")
    if require_collision and not markers.get("collision"):
        missing.append("collision")
    if require_actors and not markers.get("actors"):
        missing.append("actors")
    if missing:
        raise ValueError("Incomplete runtime receipt: missing " + ", ".join(missing))
    return dict(ok=True, stage=markers.get("stage"),
                collision_probes=len(markers["collision"]),
                actor_probes=len(markers["actors"]))


def build_p1(iso_path, research_root, lanes_path, catalog, output):
    """Run the live decode and stage the P1 run layout from real sources."""
    check_lane_entry(lanes_path)
    contract = p1_contract()
    if contract["cave_path"] != CAVEINFO_PATH:
        raise ValueError("Lane contract cave path diverges from assigned source")
    cave, cave_digest = decode_cave(iso_path, research_root)
    stage, stages_digest = decode_stage(iso_path)
    verify_stage(stage, contract)
    coverage = verify_cave_contract(cave, contract)
    closure, _ = verify_closure(cave, catalog, iso_path)
    layout = stage_run_layout(cave, stage, cave_digest, stages_digest, closure, output)
    return layout, coverage


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-entry",
                        help="JSON file holding the lane plan entry")
    parser.add_argument("--inventory-stage",
                        help="JSON file holding the inventory stage row")
    parser.add_argument("--inventory-collection",
                        help="JSON file holding the inventory challenge collection "
                             "(stages, hash map)")
    parser.add_argument("--output", required=True,
                        help="Packet output JSON path (parent must exist), or run "
                             "layout directory with --p1")
    parser.add_argument("--p1", action="store_true",
                        help="stage the P1 private run layout from live sources")
    parser.add_argument("--iso", type=Path, default=DEFAULT_ISO)
    parser.add_argument("--research", type=Path, default=DEFAULT_RESEARCH)
    parser.add_argument("--lanes", type=Path,
                        help="lanes document path (required with --p1)")
    parser.add_argument("--catalog", type=Path,
                        help="catalog JSON path with unit_pools baseline (required "
                             "with --p1; missing pools decode live)")
    args = parser.parse_args(argv)
    if args.p1:
        _require(args.lanes, "--lanes is required with --p1")
        _require(args.catalog, "--catalog is required with --p1")
        catalog = load_json(args.catalog)
        layout, coverage = build_p1(args.iso, args.research, args.lanes,
                                    catalog, args.output)
        print(json.dumps(dict(run_layout=layout["run_layout"], files=layout["files"],
                              sha256=layout["sha256"], window=layout["window"],
                              floors=len(coverage)), indent=2))
        return
    _require(args.plan_entry, "--plan-entry is required without --p1")
    _require(args.inventory_stage, "--inventory-stage is required without --p1")
    _require(args.inventory_collection, "--inventory-collection is required without --p1")
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
