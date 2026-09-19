"""P0 import-contract adapter for P2 Challenge 25: ch_NARI_08tobasare (#557).

Isolated per-source metadata and boundary checks for exactly one retail
challenge definition. Reuses the shared caveinfo framing parser
(:mod:`experimental.pikmin2_cave`) and the shared semantic decoder
(:mod:`experimental.pikmin2_cave_catalog`); it never forks them.

What this module does NOT do: emit placements, spawn counts, seeded topology,
or any playability claim. Weighted roster rows stay definitions. The actual
retail bytes for this source are only readable from a local legal US GPVE01
(Pikmin 2) revision 0 disc image; when they are absent every decode entry
point fails closed with an exact missing-prerequisite record instead of
invented values.
"""
import hashlib

from experimental.pikmin2_cave import BASE, parameters, safe_name, tree

SOURCE_ID = 'ch_NARI_08tobasare'
SOURCE_PATH = 'user/Mukki/mapunits/caveinfo/ch_NARI_08tobasare.txt'
SOURCE_SHA256 = '1ba97d8165e7d29257620b08565e7273dd2529328e565cc09ba5fc4d220832db'
SCHEMA = 1

EXPECTED_DETAILS = {
    'table_order': 18,
    'cave_id': SOURCE_ID,
    'cave_path': SOURCE_PATH,
    'floors': 2,
    'legacy_time': 0.0,
    'bitter_sprays': 2,
    'spicy_sprays': 0,
    'treasure_count_field': 0,
    'ui_index': 24,
    'floor_seconds': [150.0, 100.0],
    'issue': 137,
}
EXPECTED_PIKMIN_ROSTER = [[0, 0, 25], [0, 0, 20], [0, 0, 0], [0, 0, 5],
                          [0, 0, 0], [0, 0, 0], [0, 0, 0]]
EXPECTED_FLOORS = 2

UNIT_BASE = BASE + '/units'
ARC_BASE = BASE + '/arc'
ENEMY_INFO_SOURCE = 'src/plugProjectYamashitaU/enemyInfo.cpp'
PELLET_ARCHIVE = 'user/Abe/Pellet/us/pelletlist_us.szs'
STAGES_TABLE = 'user/Matoba/challenge/stages.txt'
DISC_IDENTITY = 'US GPVE01 revision 0 (Pikmin 2)'

UNSUPPORTED_REFERENCES = [
    {'item': 'TheKey/hole/geyser placement and floor exits',
     'owner': '#136', 'status': 'unresolved', 'needs': 'accepted Challenge framework pin'},
    {'item': 'scoring and ordinary vs deathless completion',
     'owner': '#136', 'status': 'unresolved', 'needs': 'accepted Challenge framework pin'},
    {'item': 'retry reset semantics',
     'owner': '#136', 'status': 'unresolved', 'needs': 'accepted Challenge framework pin'},
    {'item': 'generator assembly, seams and navigation',
     'owner': '#129', 'status': 'unresolved', 'needs': 'accepted generator pin'},
    {'item': 'actor/species admission for referenced roster entries',
     'owner': '#130/#131', 'status': 'unresolved', 'needs': 'decoded roster plus admission ledger'},
    {'item': 'localized English display title',
     'owner': '#137', 'status': 'unresolved', 'needs': 'message-table extraction, never guessed'},
]


class ImportContractError(ValueError):
    """Malformed definition or contract violation; never a placement."""


class MissingPrerequisite(ImportContractError):
    """Actual retail source bytes are unavailable; exact needs attached."""

    def __init__(self, message, prerequisites):
        super().__init__(message)
        self.prerequisites = list(prerequisites)


def _integer(value, label, maximum=10000):
    if not isinstance(value, str) or not value.isdigit():
        raise ImportContractError('Expected nonnegative integer for ' + label)
    number = int(value)
    if number > maximum:
        raise ImportContractError(label + ' exceeds catalog limit')
    return number


def source_prerequisites():
    """Exact inputs required before any byte-level decode of this source."""
    return [
        {'kind': 'disc_image', 'identity': DISC_IDENTITY,
         'path_hint': 'local legal ISO exposing the GPVE01 revision 0 filesystem',
         'provides': [SOURCE_PATH, PELLET_ARCHIVE, STAGES_TABLE]},
        {'kind': 'disc_path', 'path': SOURCE_PATH,
         'expected_sha256': SOURCE_SHA256, 'encoding': 'shift_jis'},
        {'kind': 'enemy_catalog', 'path': ENEMY_INFO_SOURCE,
         'provides': 'native enemy ID set for semantic roster decode'},
        {'kind': 'treasure_catalog', 'path': PELLET_ARCHIVE,
         'provides': 'pellet/treasure ID set for semantic roster decode'},
    ]


def verify_source(data, expected_sha256=SOURCE_SHA256):
    """Hash-gate raw source bytes; raises on mismatch instead of decoding."""
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise ImportContractError('Source bytes required for ' + SOURCE_ID)
    digest = hashlib.sha256(bytes(data)).hexdigest()
    if digest != expected_sha256:
        raise ImportContractError(
            'Source hash mismatch for %s: got %s' % (SOURCE_PATH, digest))
    return dict(schema=SCHEMA, source_id=SOURCE_ID, source_path=SOURCE_PATH,
                sha256=digest, verified=True, size=len(data))


def decode_structure(text):
    """Decode caveinfo framing and floor ranges without enemy catalogs."""
    if not isinstance(text, str) or not text.strip():
        raise ImportContractError('Caveinfo text required for ' + SOURCE_ID)
    try:
        nodes = tree(text)
    except ValueError as exc:
        raise ImportContractError('Unparseable caveinfo framing: %s' % exc) from None
    if len(nodes) < 2 or not isinstance(nodes[0], list):
        raise ImportContractError('Missing cave header')
    try:
        header = parameters(nodes[0])
    except ValueError as exc:
        raise ImportContractError('Malformed cave header: %s' % exc) from None
    if set(header) != {'c000'}:
        raise ImportContractError('Unsupported cave header')
    if not isinstance(nodes[1], str):
        raise ImportContractError('Missing cave definition count')
    count = _integer(nodes[1], 'definition count', 128)
    if count < 1 or _integer(header['c000'], 'header count', 128) != count:
        raise ImportContractError('Cave definition count mismatch')
    floors = []
    cursor = 2
    occupied = set()
    for index in range(count):
        if cursor >= len(nodes) or not isinstance(nodes[cursor], list):
            raise ImportContractError('Missing floor parameter block %d' % index)
        try:
            params = parameters(nodes[cursor])
        except ValueError as exc:
            raise ImportContractError('Malformed floor parameters %d: %s' % (index, exc)) from None
        if not {'f000', 'f001'} <= set(params):
            raise ImportContractError('Incomplete floor range in block %d' % index)
        first = _integer(params['f000'], 'floor first', 127)
        last = _integer(params['f001'], 'floor last', 127)
        if first > last:
            raise ImportContractError('Inverted floor range in block %d' % index)
        if occupied.intersection(range(first, last + 1)):
            raise ImportContractError('Overlapping floor range in block %d' % index)
        occupied.update(range(first, last + 1))
        version = _integer(params.get('f015', '0'), 'floor version')
        pool = params.get('f008')
        if pool is not None:
            try:
                pool = safe_name(pool)
            except ValueError as exc:
                raise ImportContractError('Unsafe unit pool name in block %d' % index) from None
        floors.append(dict(definition_index=index, first_floor=first + 1,
                           last_floor=last + 1, version=version, unit_pool=pool,
                           unit_pool_path=(UNIT_BASE + '/' + pool) if pool else None))
        cursor += 1 + (4 if version >= 1 else 3)
    if cursor != len(nodes):
        raise ImportContractError('Trailing or missing cave roster data')
    return dict(schema=SCHEMA, source_id=SOURCE_ID, source_path=SOURCE_PATH,
                definition_count=count, floors=floors, generated=False)


def check_floor_coverage(floors, expected=EXPECTED_FLOORS):
    """Require gapless 1-based coverage of exactly the catalogued floors."""
    occupied = set()
    for floor in floors:
        first, last = floor.get('first_floor'), floor.get('last_floor')
        if type(first) is not int or type(last) is not int or first < 1 or last < first:
            raise ImportContractError('Invalid floor range record')
        if occupied.intersection(range(first, last + 1)):
            raise ImportContractError('Overlapping floor ranges')
        occupied.update(range(first, last + 1))
    if occupied != set(range(1, expected + 1)):
        raise ImportContractError(
            'Floor coverage %s differs from catalogued %d floors' % (sorted(occupied), expected))
    return dict(source_id=SOURCE_ID, expected_floors=expected,
                covered_floors=sorted(occupied), complete=True)


def decode_full(text, enemy_ids, treasure_ids):
    """Semantic decode via the shared catalog parser (catalogs required)."""
    if not enemy_ids or not treasure_ids:
        raise MissingPrerequisite(
            'Semantic decode of %s needs enemy and treasure catalogs' % SOURCE_ID,
            [p for p in source_prerequisites() if p['kind'] in ('enemy_catalog', 'treasure_catalog')])
    from experimental.pikmin2_cave_catalog import parse
    try:
        result = parse(text, set(enemy_ids), set(treasure_ids))
    except ValueError as exc:
        raise ImportContractError('Semantic decode rejected: %s' % exc) from None
    check_floor_coverage(
        [dict(first_floor=f['first_floor'], last_floor=f['last_floor']) for f in result['floors']],
        expected=EXPECTED_FLOORS)
    if result['floor_count'] != EXPECTED_FLOORS:
        raise ImportContractError('Decoded floor total differs from catalogued stage')
    return result


def starting_population(roster):
    """Validate the native color/maturity roster and total its starting Pikmin."""
    if not isinstance(roster, list) or len(roster) != 7:
        raise ImportContractError('Starting roster must have 7 native color rows')
    rows = []
    for index, row in enumerate(roster):
        if not isinstance(row, list) or len(row) != 3:
            raise ImportContractError('Roster row %d must have 3 maturity columns' % index)
        if any(type(v) is not int or v < 0 for v in row):
            raise ImportContractError('Roster row %d has invalid counts' % index)
        rows.append(dict(color_index=index, leaf=row[0], bud=row[1], flower=row[2], total=sum(row)))
    return dict(source_id=SOURCE_ID, rows=rows, total=sum(r['total'] for r in rows))


def cross_check_catalog(details, roster=None):
    """Compare candidate stage metadata against the catalogued baseline pins."""
    if not isinstance(details, dict):
        raise ImportContractError('Stage details mapping required')
    mismatches = [k for k in EXPECTED_DETAILS if details.get(k) != EXPECTED_DETAILS[k]]
    if roster is not None and roster != EXPECTED_PIKMIN_ROSTER:
        mismatches.append('pikmin_by_native_color_and_maturity')
    if mismatches:
        raise ImportContractError('Catalogue mismatch: ' + ', '.join(sorted(mismatches)))
    return dict(source_id=SOURCE_ID, checked_fields=sorted(EXPECTED_DETAILS) + ['pikmin_roster'],
                mismatches=[], match=True)


def stage_contract(details, roster):
    """Metadata-only contract: spray, timer and starting-roster pins."""
    cross_check_catalog(details, roster)
    population = starting_population(roster)
    return dict(source_id=SOURCE_ID, schema=SCHEMA, metadata_only=True,
                floors=EXPECTED_FLOORS, floor_seconds=list(EXPECTED_DETAILS['floor_seconds']),
                bitter_sprays=EXPECTED_DETAILS['bitter_sprays'],
                spicy_sprays=EXPECTED_DETAILS['spicy_sprays'],
                ui_index=EXPECTED_DETAILS['ui_index'], table_order=EXPECTED_DETAILS['table_order'],
                starting_population=population,
                unsupported_references=list(UNSUPPORTED_REFERENCES),
                limitations=['Roster and sprays are definitions, not runtime actor counts.',
                             'No playability or Challenge-mode completion claim in P0.'])


def resource_closure_requirements(structure):
    """Exact retail inputs still needed for full resource closure."""
    floors = structure.get('floors') if isinstance(structure, dict) else None
    if not floors:
        raise ImportContractError('Decoded structure with floors required')
    pools = []
    for floor in floors:
        pool = floor.get('unit_pool_path')
        if pool and pool not in pools:
            pools.append(pool)
    if not pools:
        raise ImportContractError('No unit pools referenced; nothing to close')
    pending = [{'unit_pool': p,
                'needs': [p, ARC_BASE + '/<unit>/arc.szs', ARC_BASE + '/<unit>/texts.szs'],
                'note': 'unit names resolve only after pool text is read from disc'} for p in pools]
    return dict(source_id=SOURCE_ID, unit_pools=pools, pending_unit_payloads=pending,
                closed=False, missing=source_prerequisites(),
                unsupported_references=list(UNSUPPORTED_REFERENCES),
                limitations=['Weights/counts are definition inputs, not spawn instances or placements.',
                             'No seeded topology, hole selection, radial distribution or restart identity is generated.'])


def audit_packet(details, roster=None, source_bytes=None, expected_sha256=SOURCE_SHA256):
    """Assemble the P0 audit packet; byte decode only when source is present."""
    record = dict(schema=SCHEMA, source_id=SOURCE_ID, source_path=SOURCE_PATH,
                  expected_sha256=SOURCE_SHA256, catalog=cross_check_catalog(details, roster),
                  unsupported_references=list(UNSUPPORTED_REFERENCES),
                  limitations=['Metadata is not runtime acceptance.',
                               'No native build, gameplay, or playability claim in P0.'])
    if source_bytes is None:
        record.update(decoded=False, missing_prerequisites=source_prerequisites(), coverage=None)
        return record
    record.update(source=verify_source(source_bytes, expected_sha256))
    decoded = decode_structure(source_bytes.decode('shift_jis'))
    record.update(decoded=True, structure=decoded,
                  coverage=check_floor_coverage(decoded['floors']),
                  resource_closure=resource_closure_requirements(decoded))
    return record
