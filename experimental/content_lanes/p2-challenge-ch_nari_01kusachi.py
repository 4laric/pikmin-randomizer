"""P0 import-contract adapter for P2 Challenge 04 ch_NARI_01kusachi (#533).

Isolated per-lane metadata boundary: pins the canonical source identity from
docs/PIKMIN2_CONTENT_INVENTORY.json and docs/PIKMIN_CONTENT_IMPORT_LANES.json,
locates and hash-verifies the retail caveinfo bytes when a local legal disc
copy is available, and decodes the stage through the EXISTING shared parser
(experimental.pikmin2_cave_catalog.parse) without forking it. No placements,
no gameplay, no shared-file edits.

Actual source bytes were verified against the local legal disc image
(assets/disc/PIKMIN2 for GAMECUBE.iso): 1267 bytes, sha256 matches the pinned
canonical hash, 1 definition / 1 floor decoded through the shared parser with
complete resource closure (pool 1_MAT_ike_kusachi.txt, 8 units, no missing
unit assets). See docs/content_lanes/p2-challenge-ch_nari_01kusachi.md. When
bytes are absent the functions below still report the exact prerequisite
instead of inventing values. Catalogued metadata is baseline, not a
reimplementation: values are asserted against the canonical JSON files.
"""
import hashlib
import json
from pathlib import Path

from experimental.pikmin2_assets import disc_files
from experimental.pikmin2_cave_catalog import parse as parse_caveinfo

CAVE_ID = 'ch_NARI_01kusachi'
SOURCE_PATH = 'user/Mukki/mapunits/caveinfo/ch_NARI_01kusachi.txt'
SOURCE_SHA256 = 'b8d232f417ce3fd4b2903571a1c53234e63dec49e127d5ef5b8ef3cc34bb8d85'
EXPECTED_FLOORS = 1
# Catalogued stage contract (docs/PIKMIN2_CONTENT_INVENTORY.json challenge entry):
# single floor, 50 blue leaf Pikmin (native color index 2, maturity index 0),
# 180 s floor timer within a 350 s legacy budget, 1 bitter + 2 spicy sprays,
# ui_index 3. English title unresolved; source ID and UI index authoritative.
EXPECTED_ROSTER = [[0, 0, 50], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]]
EXPECTED_FLOOR_SECONDS = [180.0]
EXPECTED_LEGACY_TIME = 350.0
EXPECTED_BITTER_SPRAYS = 1
EXPECTED_SPICY_SPRAYS = 2
EXPECTED_UI_INDEX = 3
RUNTIME_DEPENDENCIES = [136, 137, 129, 130, 131]

MISSING_SOURCE_PREREQUISITE = (
    'Missing local legal source: owned US Pikmin 2 GPVE01 revision 0 disc image '
    '(PATH/PIKMIN2.iso) exposing %s with sha256 %s. Provide --iso to a lane '
    'runner or stage the extracted file read-only; no values are synthesized.' % (SOURCE_PATH, SOURCE_SHA256))


class MissingSourcePrerequisite(ValueError):
    pass


class SourceHashMismatch(ValueError):
    pass


class StageDecodeError(ValueError):
    pass


def source_identity():
    """Canonical pinned identity for this lane's source entry."""
    return dict(cave_id=CAVE_ID, source_path=SOURCE_PATH, source_sha256=SOURCE_SHA256,
                floors=EXPECTED_FLOORS, roster=EXPECTED_ROSTER, floor_seconds=EXPECTED_FLOOR_SECONDS,
                legacy_time=EXPECTED_LEGACY_TIME, bitter_sprays=EXPECTED_BITTER_SPRAYS,
                spicy_sprays=EXPECTED_SPICY_SPRAYS, ui_index=EXPECTED_UI_INDEX,
                runtime_dependencies=list(RUNTIME_DEPENDENCIES))


def locate_source(search_roots):
    """Find the retail caveinfo file under local disc roots.

    Raises MissingSourcePrerequisite naming the exact prerequisite when absent.
    """
    for root in search_roots:
        candidate = Path(root) / Path(*SOURCE_PATH.split('/'))
        if candidate.is_file():
            return candidate
    raise MissingSourcePrerequisite(MISSING_SOURCE_PREREQUISITE)


def read_disc_source(iso_path):
    """Read the pinned caveinfo bytes from a local GPVE01 disc image.

    Reuses experimental.pikmin2_assets.disc_files (not modified). Raises
    MissingSourcePrerequisite when the image or entry is absent.
    """
    try:
        catalog = disc_files(Path(iso_path))
        at, size = catalog[SOURCE_PATH]
    except (OSError, ValueError, KeyError) as exc:
        raise MissingSourcePrerequisite(
            MISSING_SOURCE_PREREQUISITE + ' (lookup failed: %s)' % exc) from exc
    with open(iso_path, 'rb') as disc:
        disc.seek(at)
        data = disc.read(size)
    if len(data) != size:
        raise StageDecodeError('Truncated disc source for %s' % CAVE_ID)
    return data


def verify_source_bytes(data):
    """Fail closed unless bytes match the pinned canonical hash."""
    actual = hashlib.sha256(bytes(data)).hexdigest()
    if actual != SOURCE_SHA256:
        raise SourceHashMismatch('Source hash %s does not match pinned %s' % (actual, SOURCE_SHA256))
    return dict(source_path=SOURCE_PATH, sha256=actual, verified=True)


def decode_stage(text, enemy_ids, treasure_ids):
    """Decode one challenge stage through the shared caveinfo parser.

    Returns the shared parse result plus this lane's 1-floor coverage check.
    Raises StageDecodeError (never partial data) on any malformed input.
    """
    try:
        cave = parse_caveinfo(text, set(enemy_ids), set(treasure_ids))
    except ValueError as exc:
        raise StageDecodeError('Caveinfo decode failed for %s: %s' % (CAVE_ID, exc)) from exc
    floors = cave.get('floors', [])
    if cave.get('floor_count') != EXPECTED_FLOORS or len(floors) != EXPECTED_FLOORS:
        raise StageDecodeError('Floor coverage mismatch for %s: expected %d floor, decoded %r'
                               % (CAVE_ID, EXPECTED_FLOORS, cave.get('floor_count')))
    return cave


def resource_closure(cave):
    """List f008 unit-pool references whose availability is unknown without source.

    No pool bytes are available in P0, so every pool is reported unresolved;
    resolving them is P1 work against the pinned disc image.
    """
    pools = []
    for floor in cave.get('floors', []):
        pool = floor.get('parameters', {}).get('f008')
        if pool and pool not in pools:
            pools.append(pool)
    return dict(unit_pools=pools, resolved=False,
                prerequisite=MISSING_SOURCE_PREREQUISITE if pools else None)


def build_import_packet(cave, verification):
    """Assemble the reviewed P0 implementation packet (JSON-serializable)."""
    closure = resource_closure(cave)
    return dict(schema=1, lane='p2-challenge-ch_nari_01kusachi', issue=533,
                identity=source_identity(), verification=verification,
                floor_coverage=dict(expected_floors=EXPECTED_FLOORS,
                                    decoded_floor_count=cave.get('floor_count'),
                                    definition_count=cave.get('definition_count')),
                resource_closure=closure,
                blockers=dict(runtime_dependencies=list(RUNTIME_DEPENDENCIES),
                              missing_local_disc=SOURCE_PATH),
                limitations=['Weights/counts are definition inputs, not final spawn instances or placements.',
                             'No seeded topology, hole selection, radial distribution or restart identity is generated.',
                             'Catalogued roster/timer/spray metadata is baseline, not observed runtime.',
                             'No claim of playability; P1/P2 remain OPEN.'])


def write_packet(packet, output_dir):
    """Write the packet under ignored output; return path and sha256."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    path = output / ('import-packet-%s.json' % CAVE_ID)
    text = json.dumps(packet, indent=2, sort_keys=True) + '\n'
    # newline='' keeps \n bytes stable across platforms so the recorded sha256
    # always matches the file on disk.
    path.write_text(text, encoding='utf-8', newline='')
    return dict(path=str(path), sha256=hashlib.sha256(text.encode('utf-8')).hexdigest())


# ---------------------------------------------------------------------------
# P1 runtime import path (lane p2-challenge-ch_nari_01kusachi-p1, issue #533).
#
# Extends the P0 decode above (reuses its helpers; no forked parser) with a
# staging step that writes a private run layout for a runtime boot attempt.
# Unsupported challenge semantics are RECORDED, never claimed.
# ---------------------------------------------------------------------------

# Challenge semantics this host cannot execute; mirrored from the contract
# consumer unsupported list (docs/PIKMIN2_CHALLENGE2_CONTRACT_CONSUMER.md).
UNSUPPORTED_CHALLENGE_SEMANTICS = (
    "challenge_host_mode",
    "coop_2p",
    "key_completion",
    "result_screen",
)

# Receipt-parseable markers a runtime MUST emit for observations to count.
# P2_KUSACHI_WINDOW size=960x540        - observed centred window
# P2_KUSACHI_SQUAD count=N             - live starting squad
# P2_KUSACHI_FLOOR_READY floor=N       - floor collision/routes staged
# P2_KUSACHI_ACTOR id=<id> x=<x> z=<z> - live actor observed
# P2_KUSACHI_PASS floors=N actors=N    - run summary
MARKER_PREFIX = "P2_KUSACHI_"
COLORS = 7
MATURITY = 3


def squad_list(matrix):
    """Flatten the 7x3 native color/maturity matrix to staged squad rows."""
    if (not isinstance(matrix, list) or len(matrix) != COLORS
            or any(not isinstance(row, list) or len(row) != MATURITY
                   or any(type(v) is not int or v < 0 for v in row) for row in matrix)):
        raise StageDecodeError("Squad matrix must be 7x3 nonnegative ints")
    return [dict(color=color, maturity=maturity, count=count)
            for color, row in enumerate(matrix)
            for maturity, count in enumerate(row) if count]


def _staged_floors(packet, cave):
    """Build staged floor rows, preferring the real decoded cave when given."""
    floors = []
    if cave is not None:
        for floor in cave.get("floors", ()):
            floors.append(dict(
                floor=floor.get("first_floor"),
                last=floor.get("last_floor"),
                unit_pool=(floor.get("parameters") or {}).get("f008"),
                enemies=[row.get("enemy_id") for row in floor.get("enemies", ())],
                treasures=[row.get("treasure_id") for row in floor.get("treasures", ())]))
        return floors
    pools = (packet.get("resource_closure") or {}).get("unit_pools") or []
    for index in range(packet["floor_coverage"]["decoded_floor_count"]):
        floors.append(dict(floor=index + 1, last=index + 1,
                           unit_pool=pools[index] if index < len(pools) else None,
                           enemies=[], treasures=[]))
    return floors


def stage_run_layout(packet, output, cave=None):
    """Stage a decoded P0 packet into a private run layout. Returns paths dict.

    Writes stage-manifest.json (floors, pools, squad, timers, unsupported),
    squad.json (starting squad rows), run-config.json (window, squad source,
    unsupported list) and markers.txt (required marker contract). Fails closed
    on any packet divergence: identity, floor coverage, squad total, timers and
    pool/floor counts must all agree.
    """
    if not isinstance(packet, dict) or packet.get("schema") != 1:
        raise StageDecodeError("Packet must be a schema-1 import packet")
    if packet.get("issue") != 533:
        raise StageDecodeError("Packet identity does not match issue #533")
    identity = packet.get("identity") or {}
    if identity.get("cave_id") != CAVE_ID:
        raise StageDecodeError("Packet identity does not match this lane")
    coverage = packet.get("floor_coverage") or {}
    expected = coverage.get("expected_floors")
    decoded = coverage.get("decoded_floor_count")
    if expected != EXPECTED_FLOORS or decoded != EXPECTED_FLOORS:
        raise StageDecodeError("Packet/contract floor count diverge")
    squad = squad_list(identity.get("roster"))
    staged_total = sum(row["count"] for row in squad)
    if staged_total <= 0:
        raise StageDecodeError("Staged squad must be non-empty")
    timers = list(identity.get("floor_seconds") or ())
    if len(timers) != EXPECTED_FLOORS or any(
            type(v) not in (int, float) or v <= 0 for v in timers):
        raise StageDecodeError("Staged timers must cover each floor positively")
    floors = _staged_floors(packet, cave)
    if len(floors) != decoded:
        raise StageDecodeError("Staged floors do not cover the decoded count")
    pools = (packet.get("resource_closure") or {}).get("unit_pools") or []
    if len(pools) > decoded:
        raise StageDecodeError("Packet pool count exceeds floor count")
    manifest = dict(schema=1, lane="p2-challenge-ch_nari_01kusachi", cave_id=CAVE_ID,
                    floor_count=expected, floors=floors, squad=squad, squad_total=staged_total,
                    floor_seconds=timers, legacy_time=identity.get("legacy_time"),
                    bitter_sprays=identity.get("bitter_sprays"),
                    spicy_sprays=identity.get("spicy_sprays"),
                    ui_index=identity.get("ui_index"),
                    unsupported_semantics=list(UNSUPPORTED_CHALLENGE_SEMANTICS),
                    source_sha256=(packet.get("verification") or {}).get("sha256"),
                    generated=False)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    paths = {}
    for name, payload in (("stage-manifest.json", manifest),
                          ("squad.json", dict(squad=squad, total=staged_total)),
                          ("run-config.json", dict(window="960x540",
                                                   squad_source="identity roster matrix",
                                                   unsupported_semantics=list(UNSUPPORTED_CHALLENGE_SEMANTICS)))):
        target = output / name
        target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8", newline="")
        paths[name] = target
    markers = output / "markers.txt"
    markers.write_text(
        "P2_KUSACHI_WINDOW size=960x540\n"
        "P2_KUSACHI_SQUAD count=%d\n"
        "P2_KUSACHI_FLOOR_READY floor=\n"
        "P2_KUSACHI_ACTOR id= x= z=\n"
        "P2_KUSACHI_PASS floors=%d actors=\n"
        % (staged_total, expected), encoding="utf-8", newline="")
    paths["markers.txt"] = markers
    return paths


def verify_run_layout(output):
    """Re-read a staged run layout and fail closed on any inconsistency."""
    output = Path(output)
    try:
        manifest = json.loads((output / "stage-manifest.json").read_text(encoding="utf-8"))
        squad_doc = json.loads((output / "squad.json").read_text(encoding="utf-8"))
        text = (output / "markers.txt").read_text(encoding="utf-8")
    except (OSError, ValueError) as error:
        raise StageDecodeError("Unreadable staged run layout: " + str(error)) from None
    if manifest.get("cave_id") != CAVE_ID:
        raise StageDecodeError("Staged manifest identity drift")
    if manifest.get("squad_total") != squad_doc.get("total"):
        raise StageDecodeError("Staged manifest/squad totals diverge")
    if sum(row["count"] for row in manifest.get("squad", ())) != manifest.get("squad_total"):
        raise StageDecodeError("Staged squad rows do not sum to total")
    if len(manifest.get("floors", ())) != manifest.get("floor_count"):
        raise StageDecodeError("Staged floors do not cover the count")
    if len(manifest.get("floor_seconds", ())) != manifest.get("floor_count"):
        raise StageDecodeError("Staged timers do not cover the count")
    for marker in ("P2_KUSACHI_WINDOW size=960x540", "P2_KUSACHI_SQUAD count=",
                   "P2_KUSACHI_FLOOR_READY floor=", "P2_KUSACHI_ACTOR id=",
                   "P2_KUSACHI_PASS floors="):
        if marker not in text:
            raise StageDecodeError("Staged marker contract missing %r" % marker)
    return manifest


def parse_marker_log(text):
    """Parse a runtime marker log into observations. Fails closed on absence.

    Returns dict with window/centre size, squad count, ready floors, actors and
    pass summary. Only markers actually present are reported; nothing is
    inferred, and a missing required marker raises StageDecodeError.
    """
    if not isinstance(text, str) or not text.strip():
        raise StageDecodeError("Empty marker log")
    observed = dict(window=None, squad=None, floors=[], actors=[], pass_summary=None)
    import re
    for line in text.splitlines():
        line = line.strip()
        match = re.fullmatch(r"P2_KUSACHI_WINDOW size=(\d+)x(\d+)", line)
        if match:
            observed["window"] = (int(match.group(1)), int(match.group(2)))
            continue
        match = re.fullmatch(r"P2_KUSACHI_SQUAD count=(\d+)", line)
        if match:
            observed["squad"] = int(match.group(1))
            continue
        match = re.fullmatch(r"P2_KUSACHI_FLOOR_READY floor=(\d+)", line)
        if match:
            observed["floors"].append(int(match.group(1)))
            continue
        match = re.fullmatch(r"P2_KUSACHI_ACTOR id=(\S+) x=(\S+) z=(\S+)", line)
        if match:
            observed["actors"].append(dict(id=match.group(1), x=match.group(2), z=match.group(3)))
            continue
        match = re.fullmatch(r"P2_KUSACHI_PASS floors=(\d+) actors=(\d+)", line)
        if match:
            observed["pass_summary"] = dict(floors=int(match.group(1)), actors=int(match.group(2)))
    missing = [name for name in ("window", "squad", "pass_summary")
               if observed[name] is None]
    if missing or not observed["floors"]:
        raise StageDecodeError("Marker log missing required entries: %s"
                               % ", ".join(missing + ([] if observed["floors"] else ["floors"])))
    if observed["window"] != (960, 540):
        raise StageDecodeError("Marker log window is not centred 960x540: %r" % (observed["window"],))
    return observed


def guard_hashes(root):
    """Hash the canonical #632 guard + the P0 source identity read-only.

    Never imports or re-implements the guard; records the exact hashes a
    runtime adoption must cite. Fails closed if the guard header is absent.
    """
    guard = Path(root) / "scripts/p2_fixture_captain_guard.h"
    if not guard.is_file():
        raise StageDecodeError("missing canonical guard header: %s" % guard)
    return dict(guard_path="scripts/p2_fixture_captain_guard.h",
                guard_sha256=hashlib.sha256(guard.read_bytes()).hexdigest(),
                source_path=SOURCE_PATH, source_sha256=SOURCE_SHA256,
                policy_required=True)
