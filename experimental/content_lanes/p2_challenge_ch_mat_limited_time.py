"""P0 import-contract adapter for P2 Challenge 12: ch_MAT_limited_time (#544).

Isolated metadata/decode boundary for the single-floor timed challenge
stage (user/Mukki/mapunits/caveinfo/ch_MAT_limited_time.txt). It reuses
the shared retail parsers (experimental.pikmin2_cave_catalog.parse)
without modifying them and never emits runtime placements: the packet
carries stage timing/roster metadata only, with playable False.

Two catalog records agree on this stage metadata: the lane entry
(docs/PIKMIN_CONTENT_IMPORT_LANES.json lane
p2-challenge-ch_mat_limited_time, details) and the inventory
(docs/PIKMIN2_CONTENT_INVENTORY.json challenge.stages); both pin
source_sha256 82b53ab1... for the definition file. hash_pin_consistency
guards drift across the embedded pin and both records. Observed-bytes
hashing (verify_source_hash) is implemented and tested, but no local
bytes exist (no retail ISO in workspace), so P0 reports the exact
prerequisite instead of a hash claim. Native color/maturity indices in the
starting-roster matrix are preserved as indices, never mapped to gameplay
names the source does not state.
"""
import hashlib
from pathlib import Path

from experimental.pikmin2_cave_catalog import parse as parse_cave

STAGE_ID = 'ch_MAT_limited_time'
SOURCE_PATH = 'user/Mukki/mapunits/caveinfo/ch_MAT_limited_time.txt'
SOURCE_SHA256 = '82b53ab1a24a1360a5761c61e3403af6f4e3efbfe0418c51913ca959e3542b1f'
EXPECTED_FLOORS = 1
UI_INDEX = 11
SCHEMA = 'p2-challenge-import-p0-1'

BASELINE_METADATA = dict(
    floors=1,
    pikmin_by_native_color_and_maturity=(
        (0, 0, 0),
        (0, 0, 40),
        (0, 0, 0),
        (0, 0, 0),
        (0, 0, 0),
        (0, 0, 0),
        (0, 0, 0),
    ),
    legacy_time=160.0,
    bitter_sprays=3,
    spicy_sprays=4,
    treasure_count_field=0,
    ui_index=11,
    floor_seconds=(130.0,),
)


def sha256_bytes(data):
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError('Source bytes required for hashing')
    return hashlib.sha256(bytes(data)).hexdigest()


def verify_source_hash(data):
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise ValueError('Observed definition bytes required for ' + STAGE_ID)
    digest = sha256_bytes(data)
    if digest != SOURCE_SHA256:
        raise ValueError('Source hash mismatch for %s: observed %s, pin %s'
                         % (STAGE_ID, digest, SOURCE_SHA256))
    return digest


def hash_pin_consistency(lanes_path, inventory_path):
    import json
    try:
        lanes = json.loads(Path(lanes_path).read_text(encoding='utf-8'))
        inventory = json.loads(Path(inventory_path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise ValueError('Catalog records unreadable')
    entries = [lane for lane in lanes.get('lanes', [])
               if lane.get('lane') == 'p2-challenge-ch_mat_limited_time']
    if len(entries) != 1:
        raise ValueError('Lane entry missing or ambiguous')
    stages = [stage for stage in inventory.get('challenge', {}).get('stages', [])
              if stage.get('cave_id') == STAGE_ID]
    if len(stages) != 1:
        raise ValueError('Inventory stage entry missing or ambiguous')
    pins = {SOURCE_SHA256, entries[0].get('source_sha256'),
            inventory.get('source_sha256', {}).get(SOURCE_PATH)}
    if len(pins) != 1 or None in pins:
        raise ValueError('Source hash pin drift across catalog records')
    return True


def _is_finite_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    import math
    return math.isfinite(number)


def validate_stage_metadata(details):
    if not isinstance(details, dict):
        raise ValueError('Stage metadata must be a mapping')
    try:
        floors = details['floors']
        matrix = details['pikmin_by_native_color_and_maturity']
        legacy = details['legacy_time']
        bitter = details['bitter_sprays']
        spicy = details['spicy_sprays']
        treasures = details['treasure_count_field']
        ui_index = details['ui_index']
        seconds = details['floor_seconds']
    except KeyError:
        raise ValueError('Stage metadata lacks required fields')
    if floors != EXPECTED_FLOORS or not isinstance(floors, int):
        raise ValueError('Challenge stage must declare exactly 1 floor')
    if (not isinstance(matrix, (list, tuple)) or len(matrix) != 7
            or any(not isinstance(row, (list, tuple)) or len(row) != 3
                   or any(not isinstance(v, int) or v < 0 or v > 999 for v in row)
                   for row in matrix)):
        raise ValueError('Starting roster must be a 7x3 nonnegative int matrix')
    if sum(sum(row) for row in matrix) <= 0:
        raise ValueError('Starting roster is empty')
    if not _is_finite_number(legacy) or float(legacy) <= 0:
        raise ValueError('Invalid legacy_time')
    for name, value in (('bitter_sprays', bitter), ('spicy_sprays', spicy),
                        ('treasure_count_field', treasures)):
        if not isinstance(value, int) or value < 0 or value > 99:
            raise ValueError('Invalid %s' % name)
    if not isinstance(ui_index, int) or ui_index < 0 or ui_index > 29:
        raise ValueError('UI index out of 30-stage range')
    if (not isinstance(seconds, (list, tuple)) or len(seconds) != floors
            or any(not _is_finite_number(v) or float(v) <= 0 for v in seconds)):
        raise ValueError('Per-floor seconds must cover every floor')
    return dict(floors=floors,
                starting_pikmin=sum(sum(row) for row in matrix),
                legacy_time=float(legacy), bitter_sprays=bitter,
                spicy_sprays=spicy, treasure_count_field=treasures,
                ui_index=ui_index,
                floor_seconds=[float(v) for v in seconds])


def metadata_agreement(details):
    validated = validate_stage_metadata(details)

    def norm(matrix):
        return [list(row) for row in matrix]

    baseline = dict(BASELINE_METADATA)
    mismatches = []
    if norm(details['pikmin_by_native_color_and_maturity']) != norm(baseline['pikmin_by_native_color_and_maturity']):
        mismatches.append('starting roster differs')
    for field in ('legacy_time', 'bitter_sprays', 'spicy_sprays',
                  'treasure_count_field', 'ui_index'):
        if details[field] != baseline[field]:
            mismatches.append('%s %r != baseline %r'
                              % (field, details[field], baseline[field]))
    if [float(v) for v in details['floor_seconds']] != [float(v) for v in baseline['floor_seconds']]:
        mismatches.append('floor_seconds differ')
    return dict(agrees=not mismatches, mismatches=mismatches,
                validated=validated)


def decode_source(text, enemy_ids, treasure_ids):
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Missing stage definition text')
    if enemy_ids is None or treasure_ids is None:
        raise ValueError('Authoritative enemy/treasure reference sets required')
    return parse_cave(text, enemy_ids, treasure_ids)


def occupied_floors(parsed):
    try:
        floors = parsed['floors']
    except (TypeError, KeyError, AttributeError):
        raise ValueError('Parsed stage has no floor list')
    if not isinstance(floors, list):
        raise ValueError('Parsed stage has no floor list')
    occupied = set()
    for floor in floors:
        try:
            first, last = floor['first_floor'], floor['last_floor']
        except (TypeError, KeyError):
            raise ValueError('Floor definition lacks range')
        if (not isinstance(first, int) or not isinstance(last, int)
                or first < 1 or last < first):
            raise ValueError('Invalid floor range')
        occupied.update(range(first, last + 1))
    return sorted(occupied)


def validate_floor_coverage(parsed, expected=EXPECTED_FLOORS):
    occupied = occupied_floors(parsed)
    if len(occupied) != expected or occupied != list(range(1, expected + 1)):
        raise ValueError(
            'Incomplete floor coverage: got %s, need 1..%d' % (occupied, expected))
    return [{'floor': number, 'covered': True} for number in occupied]


def read_source_file(path):
    try:
        data = Path(path).read_bytes()
    except OSError:
        raise ValueError('Source unavailable: ' + str(path))
    if not data:
        raise ValueError('Source empty: ' + str(path))
    return data


def read_iso_entry(iso_path, member=SOURCE_PATH):
    from experimental.pikmin2_assets import disc_files
    iso = Path(iso_path)
    if not iso.is_file():
        raise ValueError('Missing prerequisite: retail ISO not present: ' + str(iso))
    try:
        index = disc_files(iso)
    except ValueError:
        raise ValueError('Missing prerequisite: ISO is not US GPVE01 revision 0: '
                         + str(iso))
    if member not in index:
        raise ValueError('Missing prerequisite: %s absent from ISO' % member)
    with iso.open('rb') as disc:
        offset, size = index[member]
        disc.seek(offset)
        data = disc.read(size)
    if len(data) != size:
        raise ValueError('Truncated ISO member: ' + member)
    return data


def native_framework_blockers():
    return [
        '#136 P2 Challenge runtime framework: starting color/maturity '
        'populations, sprays, per-floor timing, keys/exits, scores, retry '
        'and ordinary/deathless result semantics; nothing staged here',
        '#137 P2 Challenge content: thirty per-stage children, all 59 '
        'floors audited and tested on framework/generator pins',
        '#129 cave generation/seams/navigation (active #468): accepted '
        'generator pin required; no replacement forked here',
        '#130/#131 actor/assets/species: stage roster admission blocks '
        'promotion, not P0 preparation',
    ]


def summarize(metadata, source_sha256):
    agreement = metadata_agreement(metadata)
    validated = agreement['validated']
    return dict(
        schema=SCHEMA, stage=STAGE_ID, source=SOURCE_PATH,
        source_sha256=source_sha256,
        source_status=('hash-verified against catalogued pin'
                       if source_sha256 == SOURCE_SHA256
                       else 'bytes unavailable; pin recorded, hash claim withheld'),
        floor_coverage=EXPECTED_FLOORS,
        baseline_agrees=agreement['agrees'],
        baseline_mismatches=agreement['mismatches'],
        stage_metadata=dict(
            floors=EXPECTED_FLOORS,
            starting_pikmin=validated['starting_pikmin'],
            legacy_time=validated['legacy_time'],
            bitter_sprays=validated['bitter_sprays'],
            spicy_sprays=validated['spicy_sprays'],
            treasure_count_field=validated['treasure_count_field'],
            ui_index=validated['ui_index'],
            floor_seconds=validated['floor_seconds']),
        unsupported=dict(
            roster='Stage enemy roster unresolved until definition bytes decode; '
                   'no native species admission claimed',
            placements='No placements emitted: weights are definition inputs, '
                       'never spawn instances'),
        blockers=native_framework_blockers(),
        retail_generation=False, playable=False,
        limitations=['Stage timing/roster/spray metadata is catalogued, not observed gameplay.',
                     'No seeded topology, spawn selection, score/retry semantics or restart identity is generated.',
                     'P0 packet is metadata for integrator review; full content issue #544 stays OPEN.'])
