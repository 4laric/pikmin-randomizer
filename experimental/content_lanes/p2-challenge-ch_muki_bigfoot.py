"""P0 import contract for P2 Challenge 08 ch_MUKI_bigfoot (issue #539).

Isolated metadata/import-contract adapter for this source entry only. It
reuses the shared caveinfo brace grammar from experimental.pikmin2_cave
without modifying it, and carries the pinned catalogued baseline from
docs/PIKMIN2_CONTENT_INVENTORY.json and docs/PIKMIN_CONTENT_IMPORT_LANES.json.

The actual disc bytes (user/Mukki/mapunits/caveinfo/ch_MUKI_bigfoot.txt) are
not present locally ("metadata inventory only; no source assets copied"), so
every entry point that needs them fails closed with the exact missing
prerequisite instead of inventing values. Weighted enemy/treasure rows decode
as definitions (id plus packed weight); they are never emitted as runtime
placements, positions or actor counts.
"""
import hashlib
from pathlib import Path

from experimental.pikmin2_cave import parameters, tree, weighted

CAVE_ID = 'ch_MUKI_bigfoot'
SOURCE_PATH = 'user/Mukki/mapunits/caveinfo/ch_MUKI_bigfoot.txt'
SOURCE_SHA256 = '9d3efaf030587a94366bf2db7ed26aecfd93f37b806708061bd218440a2a782f'
FLOORS = 1
FLOOR_SECONDS = [200.0]
UI_INDEX = 7
SPICY_SPRAYS = 2
BITTER_SPRAYS = 0
TREASURE_COUNT_FIELD = 0
LEGACY_TIME = 0.0
# Pinned catalogued starting roster by native color and maturity; baseline, not a claim.
ROSTER = [[0, 0, 0], [25, 0, 0], [0, 0, 0], [0, 0, 0], [25, 0, 0], [0, 0, 0], [0, 0, 0]]
# P1/P2 runtime work waits on these published contracts; P0 proceeds without them.
RUNTIME_DEPENDENCIES = (136, 137, 129, 130, 131)


class MissingSource(FileNotFoundError):
    """Raised when the disc source is unavailable; message is the prerequisite."""


class MalformedStage(ValueError):
    """Raised when stage bytes do not follow the shared caveinfo grammar."""


def missing_prerequisite():
    """Exact missing prerequisite for decoding actual stage definitions."""
    return dict(cave_id=CAVE_ID, disc_path=SOURCE_PATH, expected_sha256=SOURCE_SHA256,
                instruction='Supply a legal US GPVE01 rev 0 disc copy containing ' + SOURCE_PATH +
                            '; verify its SHA-256 against expected_sha256 before decoding.')


def validate_source_bytes(data):
    """Return the SHA-256 hex of source bytes, failing closed on mismatch."""
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise MalformedStage('Source bytes must be nonempty')
    observed = hashlib.sha256(bytes(data)).hexdigest()
    if observed != SOURCE_SHA256:
        raise MalformedStage('Source hash differs: observed ' + observed +
                             ' expected ' + SOURCE_SHA256)
    return observed


def load_source(path):
    """Read stage bytes from a local path, or raise the exact prerequisite."""
    candidate = Path(path)
    if not candidate.is_file():
        raise MissingSource('Missing disc source ' + SOURCE_PATH +
                            ' (expected SHA-256 ' + SOURCE_SHA256 + '); ' +
                            missing_prerequisite()['instruction'])
    return validate_source_bytes(candidate.read_bytes())


def decode_stage(text):
    """Decode stage text with the shared grammar; definitions only, no placements."""
    try:
        nodes = tree(text)
    except ValueError as error:
        raise MalformedStage('Unparseable stage grammar: ' + str(error)) from error
    if len(nodes) < 2:
        raise MalformedStage('Missing stage header')
    try:
        header = parameters(nodes[0])
        count = int(nodes[1])
    except (ValueError, IndexError, TypeError) as error:
        raise MalformedStage('Invalid stage header: ' + str(error)) from error
    if count != FLOORS or len(nodes) != 2 + 5 * count:
        raise MalformedStage('Floor coverage differs: header declares %d floor(s), want %d' % (count, FLOORS))
    floors = []
    for i in range(count):
        params, enemies, items, gates, caps = nodes[2 + 5 * i:7 + 5 * i]
        try:
            params = parameters(params)
        except ValueError as error:
            raise MalformedStage('Invalid floor parameters: ' + str(error)) from error
        if int(params.get('f000', -1)) != i or int(params.get('f001', -1)) != i:
            raise MalformedStage('Only individual authored floor definitions supported')
        if gates != ['0'] or caps != ['0']:
            raise MalformedStage('Gate/cap rosters not yet supported')
        try:
            enemy_defs = [dict(id=a, packed_weight=int(b), placement_type=int(c))
                          for a, b, c in weighted(enemies, 3)]
            treasure_defs = [dict(id=a, packed_weight=int(b)) for a, b in weighted(items, 2)]
        except (ValueError, IndexError) as error:
            raise MalformedStage('Invalid weighted roster: ' + str(error)) from error
        floors.append(dict(number=i + 1, parameters=params,
                           enemy_definitions=enemy_defs, treasure_definitions=treasure_defs))
    return dict(cave_id=CAVE_ID, source_path=SOURCE_PATH, source_sha256=SOURCE_SHA256,
                floors=floors, floor_seconds=list(FLOOR_SECONDS), ui_index=UI_INDEX)


def roster_totals(roster=None):
    """Sum the pinned starting roster; counts only, never placements."""
    rows = roster if roster is not None else ROSTER
    if (not isinstance(rows, list) or len(rows) != len(ROSTER) or
            any(not isinstance(r, list) or len(r) != 3 or
                any(type(v) is not int or v < 0 for v in r) for r in rows)):
        raise MalformedStage('Roster must be %d rows of 3 nonnegative ints' % len(ROSTER))
    return dict(rows=[sum(r) for r in rows], total=sum(sum(r) for r in rows))


def resource_closure(record=None):
    """Preserved roster/spray/timer closure plus explicit unsupported references."""
    roster = roster_totals()
    return dict(cave_id=CAVE_ID, source_path=SOURCE_PATH, source_sha256=SOURCE_SHA256,
                floors=FLOORS, floor_seconds=list(FLOOR_SECONDS), ui_index=UI_INDEX,
                starting_roster_total=roster['total'], starting_roster_rows=roster['rows'],
                spicy_sprays=SPICY_SPRAYS, bitter_sprays=BITTER_SPRAYS,
                treasure_count_field=TREASURE_COUNT_FIELD, legacy_time=LEGACY_TIME,
                unsupported=[
                    'Actual floor unit/arc/mapunit files: disc source unavailable (see missing_prerequisite).',
                    'Enemy cargo/receiver resolution: P2 Challenge runtime framework #136 and content #137.',
                    'Generator/seam/navigation pin: #129 with lanes 34-51 and #468; actor/assets/species: #128, #130, #131.',
                    'Starting color/maturity populations, per-floor timing, keys/exits, scores, retry and ordinary/deathless semantics: framework #136.',
                ])


def stage_contract():
    """Reviewed implementation packet content for this source entry."""
    return dict(schema=1, lane='p2-challenge-ch_muki_bigfoot', issue=539, cave_id=CAVE_ID,
                source_path=SOURCE_PATH, source_sha256=SOURCE_SHA256,
                floor_coverage=dict(floors=FLOORS, floor_seconds=list(FLOOR_SECONDS), ui_index=UI_INDEX),
                resource_closure=resource_closure(), missing_prerequisite=missing_prerequisite(),
                runtime_dependencies=list(RUNTIME_DEPENDENCIES),
                limitations=['Metadata and import contract only; no claim of playability.',
                             'Weighted definitions are not runtime placements, positions or actor counts.',
                             'Actual stage bytes undecodable until the missing prerequisite is supplied.'])
