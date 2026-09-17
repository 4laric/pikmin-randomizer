"""P0 source audit and import contract for ch_NARI_05start3easy (issue #548).

Lane `p2-challenge-ch_nari_05start3easy`, category `p2-challenge`. A Challenge
stage is TWO live sources: the cave definition
(`user/Mukki/mapunits/caveinfo/ch_NARI_05start3easy.txt`, same block family as
story caves; here 2 floors) and the stage row in
`user/Matoba/challenge/stages.txt` (version, cave reference, 7x3 PikiCounter
roster/maturity, legacy time, bitter/spicy dopes, floor count, otakara count,
2d UI index, per-floor seconds). This module decodes both, cross-checks them
against the lane contract in `docs/PIKMIN_CONTENT_IMPORT_LANES.json` and an
existing catalog baseline, verifies unit-pool resource closure, and emits an
import packet. The cave half reuses the shared retail parser
(`experimental.pikmin2_cave_catalog.parse`); the stage-block half is a small
strict parser owned here (no shared challenge decoder exists). No placements,
spawns, topology, or gameplay claims are emitted.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_cave import unit_definition
from experimental.pikmin2_cave_catalog import parse

LANE = "p2-challenge-ch_nari_05start3easy"
SOURCE_ID = "ch_NARI_05start3easy"
CAVEINFO_PATH = "user/Mukki/mapunits/caveinfo/ch_NARI_05start3easy.txt"
STAGES_PATH = "user/Matoba/challenge/stages.txt"
PELLET_ARCHIVE = "user/Abe/Pellet/us/pelletlist_us.szs"
ENEMYINFO = "src/plugProjectYamashitaU/enemyInfo.cpp"
COLORS = 7
MATURITY = 3


class ContractMismatch(ValueError):
    pass


def lane_contract(lanes_path, lane=LANE):
    """Load this lane's stage contract from the lanes document (single source)."""
    try:
        lanes = json.loads(Path(lanes_path).read_text(encoding="utf-8"))["lanes"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ContractMismatch("Unreadable lanes document: " + str(error)) from None
    entries = [entry for entry in lanes if entry.get("lane") == lane]
    if len(entries) != 1:
        raise ContractMismatch("Lane %r must appear exactly once" % lane)
    details = entries[0].get("details") or {}
    for key in ("cave_path", "floors", "pikmin_by_native_color_and_maturity",
                "legacy_time", "bitter_sprays", "spicy_sprays",
                "treasure_count_field", "ui_index", "floor_seconds"):
        if key not in details:
            raise ContractMismatch("Lane %r details missing %r" % (lane, key))
    matrix = details["pikmin_by_native_color_and_maturity"]
    if (not isinstance(matrix, list) or len(matrix) != COLORS
            or any(not isinstance(row, list) or len(row) != MATURITY
                   or any(type(v) is not int or v < 0 for v in row) for row in matrix)):
        raise ContractMismatch("Lane %r pikmin matrix must be 7x3 nonneg ints" % lane)
    if (not isinstance(details["floor_seconds"], list) or not details["floor_seconds"]
            or any(not isinstance(v, (int, float)) for v in details["floor_seconds"])):
        raise ContractMismatch("Lane %r floor_seconds malformed" % lane)
    return dict(lane=lane, source_id=SOURCE_ID, cave_path=details["cave_path"],
                floors=details["floors"], pikmin=matrix, legacy_time=details["legacy_time"],
                bitter_sprays=details["bitter_sprays"], spicy_sprays=details["spicy_sprays"],
                treasure_count=details["treasure_count_field"], ui_index=details["ui_index"],
                floor_seconds=list(details["floor_seconds"]))


def read_iso_file(iso_path, disc_path):
    """Read one file from the local disc image and return (bytes, sha256)."""
    iso = Path(iso_path)
    try:
        catalog = disc_files(iso)
    except (OSError, ValueError) as error:
        raise ContractMismatch("Unreadable disc image: " + str(error)) from None
    if disc_path not in catalog:
        raise ContractMismatch("Disc entry missing: " + disc_path)
    at, size = catalog[disc_path]
    try:
        with iso.open("rb") as disc:
            disc.seek(at)
            data = disc.read(size)
    except OSError as error:
        raise ContractMismatch("Disc read failed: " + str(error)) from None
    if len(data) != size:
        raise ContractMismatch("Truncated disc source: " + disc_path)
    return data, hashlib.sha256(data).hexdigest()


def reference_ids(iso_path, research_root):
    """Enemy IDs from the research source plus treasure IDs from the disc pellet
    archive. These are the exact decoder inputs the shared parser requires."""
    enemy_source = Path(research_root) / ENEMYINFO
    try:
        raw = enemy_source.read_bytes().decode("utf-8")
    except OSError as error:
        raise ContractMismatch("Missing research enemy catalog: " + str(error)) from None
    enemy_ids = set(re.findall(r"\{\"([A-Za-z0-9_]+)\"", raw))
    if not enemy_ids:
        raise ContractMismatch("No enemy IDs decoded from research source")
    archive_data, _ = read_iso_file(iso_path, PELLET_ARCHIVE)
    try:
        from experimental.pikmin2_pod import pellet_catalog
        archive = archive_files(archive_data)
        treasure_ids = set()
        for name in ("otakara_config.txt", "item_config.txt"):
            treasure_ids.update(pellet_catalog(archive[name].decode("shift_jis")))
    except (ValueError, KeyError) as error:
        raise ContractMismatch("Unreadable pellet archive: " + str(error)) from None
    if not treasure_ids:
        raise ContractMismatch("No treasure IDs decoded from pellet archive")
    return enemy_ids, treasure_ids


def decode_cave(iso_path, research_root, source=CAVEINFO_PATH):
    """Decode the actual cave definition from local sources.

    Returns (cave, file_sha256). Weights are definition inputs, never spawn
    instances (see module packet limitations).
    """
    data, digest = read_iso_file(iso_path, source)
    try:
        text = data.decode("shift_jis")
    except UnicodeDecodeError as error:
        raise ContractMismatch("Caveinfo is not shift_jis: " + str(error)) from None
    enemy_ids, treasure_ids = reference_ids(iso_path, research_root)
    try:
        cave = parse(text, enemy_ids, treasure_ids)
    except ValueError as error:
        raise ContractMismatch("Retail definition failed shared parse: " + str(error)) from None
    cave.update(cave_id=SOURCE_ID, source=source)
    return cave, digest


def split_stage_blocks(text):
    """Split stages.txt into raw stage-block strings (header discarded)."""
    chunks = re.split(r"^# stage[ \t]*$", text, flags=re.MULTILINE)
    if len(chunks) < 2:
        raise ContractMismatch("No stage blocks in challenge stage table")
    head = chunks[0].strip().splitlines()
    if not head or not re.fullmatch(r"\d+", head[0].split("#")[0].strip()):
        raise ContractMismatch("Stage table missing leading stage count")
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
        raise ContractMismatch("Stage block must open with brace")
    cursor = 1

    def take(pattern, label):
        nonlocal cursor
        if cursor >= len(lines):
            raise ContractMismatch("Truncated stage block at " + label)
        match = re.fullmatch(pattern, lines[cursor].strip())
        if not match:
            raise ContractMismatch("Stage block field %r mismatch: %r" % (label, lines[cursor].strip()))
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
        raise ContractMismatch("Stage block must close with brace")
    cursor += 1
    if cursor != len(lines):
        raise ContractMismatch("Trailing data in stage block")
    return dict(cave_file=cave, pikmin=pikmin, legacy_time=legacy_time,
                bitter_sprays=bitter, spicy_sprays=spicy, floors=floors,
                treasure_count=treasures, ui_index=ui_index, floor_seconds=seconds)


def decode_stage(iso_path, cave_file=SOURCE_ID + ".txt"):
    """Decode this lane's stage row from the live challenge stage table.

    Returns (stage, table_sha256). Exactly one block may reference the file.
    """
    data, digest = read_iso_file(iso_path, STAGES_PATH)
    try:
        text = data.decode("shift_jis").replace(chr(13) + chr(10), chr(10))
    except UnicodeDecodeError as error:
        raise ContractMismatch("Stage table is not shift_jis: " + str(error)) from None
    matches = []
    for block in split_stage_blocks(text):
        try:
            stage = parse_stage_block(block)
        except ContractMismatch:
            continue
        if stage["cave_file"] == cave_file:
            matches.append(stage)
    if len(matches) != 1:
        raise ContractMismatch("Stage table must reference %r exactly once" % cave_file)
    return matches[0], digest


def verify_stage(stage, contract):
    """Cross-check a decoded stage row against the lane stage contract."""
    for key in (("pikmin", "pikmin"), ("legacy_time", "legacy_time"),
                ("bitter_sprays", "bitter_sprays"), ("spicy_sprays", "spicy_sprays"),
                ("treasure_count", "treasure_count"), ("ui_index", "ui_index"),
                ("floor_seconds", "floor_seconds"), ("floors", "floors")):
        if stage[key[0]] != contract[key[1]]:
            raise ContractMismatch("Stage field %r diverges from contract" % key[0])
    return dict(cave_file=stage["cave_file"], floors=stage["floors"],
                starting_pikmin=sum(sum(row) for row in stage["pikmin"]),
                floor_seconds=stage["floor_seconds"], ui_index=stage["ui_index"])


def verify_cave_contract(cave, contract):
    """Cross-check the decoded cave definition: identity, full floor cover,
    per-floor unit pools and complete enemy/item/gate/cap rosters (recorded,
    not placed)."""
    if cave.get("cave_id") != contract["source_id"]:
        raise ContractMismatch("Decoded identity does not match lane contract source")
    if cave.get("floor_count") != contract["floors"] or len(cave.get("floors", ())) != contract["floors"]:
        raise ContractMismatch("Decoded floor records do not cover the contract")
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
        raise ContractMismatch("Challenge floor ranges must tile 1..floors exactly once")
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
        raise ContractMismatch("Unit pool is not shift_jis: " + str(error)) from None
    try:
        definitions = unit_definition(text)
    except ValueError as error:
        raise ContractMismatch("Unit pool failed shared parse: " + str(error)) from None
    iso = Path(iso_path)
    try:
        from experimental.pikmin2_assets import disc_files as _disc_files
        toc = _disc_files(iso)
    except (OSError, ValueError) as error:
        raise ContractMismatch("Unreadable disc table: " + str(error)) from None
    for unit in definitions:
        for suffix in ("arc.szs", "texts.szs"):
            if "user/Mukki/mapunits/arc/" + unit["name"] + "/" + suffix not in toc:
                raise ContractMismatch("Missing unit asset for " + unit["name"])
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
                raise ContractMismatch("Unit pool without decoded closure: %r" % pool)
            entry, digest = decode_pool_live(iso_path, pool)
            pool_hashes[pool] = digest
            provenance = "live"
        closure.append(dict(floor=floor["first_floor"], unit_pool=pool,
                            source=entry.get("source"), provenance=provenance,
                            units=[unit["name"] for unit in entry["units"]]))
    return closure, pool_hashes


def p1_blockers(coverage, closure):
    """Exact native/framework prerequisites for a future P1 runtime import."""
    pools = sorted({row["unit_pool"] for row in closure})
    return [
        "Native cave/generator import hook for caveinfo definitions plus Challenge-mode "
        "stage bootstrap (PikiCounter roster, dopes, floor timers, 2d index) "
        "(integration owner); this packet decodes definitions only and wires no native path.",
        "Unit-pool asset staging for %s via the existing unit pipeline; packet records "
        "pool sources, not staged assets." % ", ".join(pools),
        "Seeded topology/hole selection and generator pins are unproven for these %d floors; "
        "weights in the packet are definition inputs, not placements." % len(coverage),
        "Enemy admission resolved per enemy roster at P1; unresolved admission blocks "
        "promotion, not this preparatory packet; no host chal0 fixture treated as Challenge mode.",
    ]


def build_packet(iso_path, research_root, lanes_path, catalog, output):
    """Run the full P0 audit and write the import packet JSON. Returns (packet, path)."""
    contract = lane_contract(lanes_path)
    if contract["cave_path"] != CAVEINFO_PATH:
        raise ContractMismatch("Lane contract cave path diverges from assigned source")
    cave, cave_digest = decode_cave(iso_path, research_root)
    stage, stages_digest = decode_stage(iso_path)
    stage_report = verify_stage(stage, contract)
    coverage = verify_cave_contract(cave, contract)
    closure, pool_hashes = verify_closure(cave, catalog, iso_path)
    packet = dict(
        schema=1, lane=LANE, source_id=SOURCE_ID, source=CAVEINFO_PATH,
        source_sha256=cave_digest, stage_table=dict(source=STAGES_PATH, sha256=stages_digest),
        floor_count=contract["floors"], stage=stage_report, coverage=coverage, pool_hashes=pool_hashes,
        closure=closure, blockers=p1_blockers(coverage, closure), generated=False,
        limitations=[
            "Weights/counts are definition inputs, not final spawn instances or placements.",
            "No seeded topology, hole selection, radial distribution or restart identity is generated.",
            "Metadata only; no claim of imported or playable content.",
        ])
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    path = output / "content-ch-nari-05start3easy-p0.json"
    path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return packet, path


# ---------------------------------------------------------------------------
# P1 private runtime import path (issue #548). Extends the P0 decode above;
# reuses its real-source helpers and does NOT fork any parser. Stages the
# decoded stage manifest into a private run layout consumed by the integrated
# Challenge content-loading boot path (#701 binder) plus the host-mode module
# contract (native/pc_port/pc_p2_challenge_mode.h StageEntry shape).
# ---------------------------------------------------------------------------

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


def floor_manifest(cave, index):
    """Per-floor staging manifest: unit pool, anchor and spawn intents.

    Spawn intents aggregate the decoded roster by token (deterministic sorted
    order); they are definition inputs, never placements.
    """
    floors = cave.get("floors") or []
    if index < 0 or index >= len(floors):
        raise ContractMismatch("Floor index out of range: %r" % (index,))
    floor = floors[index]
    pool = (floor.get("parameters") or {}).get("f008")
    if not pool or not re.fullmatch(r"[A-Za-z0-9_.\-]+\.txt", pool):
        raise ContractMismatch("Floor %d has no usable unit pool" % (index + 1))
    counts = {}
    for entry in floor.get("enemies", []):
        token = entry.get("source_token") or entry.get("enemy_id")
        if not token:
            raise ContractMismatch("Enemy entry without a source token")
        counts[token] = counts.get(token, 0) + 1
    for entry in floor.get("treasures", []):
        token = entry.get("treasure_id")
        if not token:
            raise ContractMismatch("Treasure entry without an id")
        counts[token] = counts.get(token, 0) + 1
    if not counts:
        raise ContractMismatch("Floor %d has an empty roster" % (index + 1))
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
        raise ContractMismatch("No unit available for the preview room")
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
        raise ContractMismatch("No decoded floors to stage")
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
        raise ContractMismatch("Captain-down run cannot substantiate a receipt")
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
        raise ContractMismatch("Incomplete runtime receipt: missing " + ", ".join(missing))
    return dict(ok=True, stage=markers.get("stage"),
                collision_probes=len(markers["collision"]),
                actor_probes=len(markers["actors"]))


def build_p1(iso_path, research_root, lanes_path, catalog, output):
    """Run the P0 audit live and stage the P1 run layout from real sources."""
    contract = lane_contract(lanes_path)
    if contract["cave_path"] != CAVEINFO_PATH:
        raise ContractMismatch("Lane contract cave path diverges from assigned source")
    cave, cave_digest = decode_cave(iso_path, research_root)
    stage, stages_digest = decode_stage(iso_path)
    verify_stage(stage, contract)
    coverage = verify_cave_contract(cave, contract)
    closure, _ = verify_closure(cave, catalog, iso_path)
    layout = stage_run_layout(cave, stage, cave_digest, stages_digest, closure, output)
    return layout, coverage

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--research", type=Path, required=True)
    parser.add_argument("--lanes", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--p1", action="store_true", help="stage the P1 private run layout")
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8")) if args.catalog.is_file() else {}
    if args.p1:
        layout, coverage = build_p1(args.iso, args.research, args.lanes, catalog, args.output)
        print(json.dumps(dict(run_layout=layout["run_layout"], files=layout["files"],
                              sha256=layout["sha256"], window=layout["window"],
                              floors=len(coverage))))
    else:
        packet, path = build_packet(args.iso, args.research, args.lanes, catalog, args.output)
        print(json.dumps(dict(packet=str(path), floors=packet["floor_count"],
                              source_sha256=packet["source_sha256"],
                              stages_sha256=packet["stage_table"]["sha256"])))