"""P0 import-contract adapter for P2 Challenge 23 ch_MUKI_bombing (#556).

Isolated per-lane metadata boundary: pins the canonical source identity from
docs/PIKMIN2_CONTENT_INVENTORY.json and docs/PIKMIN_CONTENT_IMPORT_LANES.json,
locates and hash-verifies the retail caveinfo bytes against the local legal
disc image, and decodes the stage through the EXISTING shared parser
(experimental.pikmin2_cave_catalog.parse) without forking it. No placements,
no gameplay, no shared-file edits.

Actual source bytes were verified against assets/disc/PIKMIN2 for GAMECUBE.iso:
1852 bytes, sha256 matches the pinned canonical hash, 1 definition / 1 floor
decoded with complete resource closure (pool
2_units_5x5a_big_tekiF_kusachi.txt, 8 units, no missing unit assets). See
docs/content_lanes/p2-challenge-ch_muki_bombing.md. When bytes are absent the
functions below still report the exact prerequisite instead of inventing
values. Catalogued metadata is baseline, not a reimplementation: values are
asserted against the canonical JSON files.
"""
import hashlib
import json
from pathlib import Path

from experimental.pikmin2_assets import disc_files
from experimental.pikmin2_cave_catalog import parse as parse_caveinfo

CAVE_ID = 'ch_MUKI_bombing'
SOURCE_PATH = 'user/Mukki/mapunits/caveinfo/ch_MUKI_bombing.txt'
SOURCE_SHA256 = '558fa438ba56377f5242020e3389354d9be4db01243cc6423fd299d66a3442b0'
EXPECTED_FLOORS = 1
# Catalogued stage contract (docs/PIKMIN2_CONTENT_INVENTORY.json challenge entry):
# single floor, 30 + 20 leaf Pikmin at native roster rows 2 and 3 (native color
# mapping unresolved; indices reported verbatim), 255 s floor timer, 1 bitter +
# 1 spicy sprays, ui_index 22. English title unresolved; source ID and UI index
# authoritative.
EXPECTED_ROSTER = [[0, 0, 0], [0, 0, 0], [0, 0, 30], [0, 0, 20], [0, 0, 0], [0, 0, 0], [0, 0, 0]]
EXPECTED_FLOOR_SECONDS = [255.0]
EXPECTED_LEGACY_TIME = 0.0
EXPECTED_BITTER_SPRAYS = 1
EXPECTED_SPICY_SPRAYS = 1
EXPECTED_UI_INDEX = 22
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
    return dict(schema=1, lane='p2-challenge-ch_muki_bombing', issue=556,
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