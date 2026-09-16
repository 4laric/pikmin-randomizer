"""P0 import-contract adapter for P2 cave tutorial_3 (issue #153).

Isolated metadata/decode boundary for the tutorial_3 cave definition
(`user/Mukki/mapunits/caveinfo/tutorial_3.txt`, 8 floors). It reuses the
shared retail parsers (`experimental.pikmin2_cave_catalog.parse`) without
modifying them and never emits runtime placements: every roster row the
packet produces carries `runtime_status='unsupported'`, and weights stay
definition inputs, never spawn instances.

Baseline floor metadata below is transcribed from the read-only lane entry
`docs/PIKMIN_CONTENT_IMPORT_LANES.json` (lane `p2-cave-tutorial_3`,
`details.floors`) which agrees with `docs/PIKMIN2_CONTENT_INVENTORY.json`
`story_caves` tutorial_3; `baseline_matches_lane_entry()` guards drift.
Raw `source_token` multisets (not tokenized ids) are compared so no
TekiInfo split/case assumption is baked in here.
"""
import hashlib
from pathlib import Path

from experimental.pikmin2_cave_catalog import parse as parse_cave

CAVE_ID = 'tutorial_3'
SOURCE_PATH = 'user/Mukki/mapunits/caveinfo/tutorial_3.txt'
EXPECTED_FLOORS = 8
SCHEMA = 'p2-cave-import-p0-1'

# (floor, unit_pool, enemy source tokens, treasure ids). Transcribed from the
# lane entry; agreement is checked, never auto-corrected.
BASELINE_FLOORS = (
    (1, '3_MAT_nor4_hit2_blk1_snow.txt',
     ('YellowChappy', 'YellowKochappy', 'YellowKochappy', 'Fart', 'Fart',
      'KareOoinu_s', 'KareOoinu_l', 'KareOoinu_l', 'KareOoinu_s',
      'KareOoinu_l', 'KareOoinu_s', 'KareOoinu_l', 'Wakame_l'),
     ('Xmas_item', 'teala_dia_a')),
    (2, '3_MAT_ike3_mid2_sak1_snow.txt',
     ('RKabuto', 'YellowChappy', 'YellowKochappy', 'YellowKochappy',
      'KareOoinu_s', 'KareOoinu_s', 'KareOoinu_l'),
     ('chess_king_black', 'toy_ring_c_blue')),
    (3, '3_MAT_d_g_m_renga.txt',
     ('LeafChappy', 'KumaChappy_bell_red', 'KumaKochappy', 'KumaKochappy',
      'KumaKochappy', 'GasHiba', 'Hiba', 'ElecHiba', 'KareOoinu_s',
      'KareOoinu_s'),
     ('toy_ring_a_green', 'toy_ring_c_red')),
    (4, '3_MAT_a_h_m_renga.txt',
     ('Sarai', 'Sarai', 'Demon', 'Demon', 'ElecBug', 'ElecBug', 'ElecBug',
      'ElecHiba', 'KareOoinu_s', 'KareOoinu_s', 'KareOoinu_l'),
     ('toy_ring_c_green', 'be_dama_red')),
    (5, '1_MAT_cent2_tsuchi.txt',
     ('Miulin_fue_a', 'ShijimiChou', 'Miulin', 'WaterOtakara', 'WaterOtakara',
      'Clover', 'Wakame_s', 'Wakame_l', 'Ooinu_l', 'Magaret', 'Ooinu_s'),
     ()),
    (6, '3_MAT_nor4_ike1_ike2_tsuchi.txt',
     ('RKabuto', 'LeafChappy', 'Catfish', 'Catfish', 'Catfish', 'Hiba',
      'HikariKinoko', 'HikariKinoko'),
     ('chess_king_white', 'chess_queen_black')),
    (7, '3_MAT_cent_mid1_mid2_tsuchi.txt',
     ('BlueChappy', 'Rock', 'Rock', 'Rock', 'BlueKochappy', 'BlueKochappy',
      'BlueKochappy', 'HikariKinoko', 'HikariKinoko'),
     ('yoyo_red', 'bell_yellow')),
    (8, '1_units_queen_b_tsuchi.txt',
     ('Queen_dashboots', 'Baby', 'Baby'),
     ()),
)


def sha256_bytes(data):
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError('Source bytes required for hashing')
    return hashlib.sha256(bytes(data)).hexdigest()


def decode_source(text, enemy_ids, treasure_ids):
    """Decode actual cave definition bytes (shift_jis-decoded text).

    Thin fail-closed wrapper over the shared retail parser; ValueError
    propagates unchanged for malformed input. `enemy_ids`/`treasure_ids`
    are the caller's authoritative reference sets (decomp enemyInfo +
    pellet configs when available).
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Missing cave definition text')
    if enemy_ids is None or treasure_ids is None:
        raise ValueError('Authoritative enemy/treasure reference sets required')
    return parse_cave(text, enemy_ids, treasure_ids)


def occupied_floors(parsed):
    """Sorted 1-based floor numbers covered by parsed definitions."""
    try:
        floors = parsed['floors']
    except (TypeError, KeyError):
        raise ValueError('Parsed cave has no floor list')
    if not isinstance(floors, list):
        raise ValueError('Parsed cave has no floor list')
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
    """Require exactly `expected` contiguous floors starting at 1."""
    occupied = occupied_floors(parsed)
    if len(occupied) != expected or occupied != list(range(1, expected + 1)):
        raise ValueError(
            'Incomplete floor coverage: got %s, need 1..%d' % (occupied, expected))
    return [{'floor': number, 'covered': True} for number in occupied]


def baseline_agreement(parsed, baseline=BASELINE_FLOORS):
    """Compare decoded definitions against the catalogued baseline.

    Per floor: unit pool (`f008`) exact match, enemy `source_token`
    multiset match, treasure id multiset match. Returns the agreement
    report; mismatches are reported, never corrected or fabricated.
    """
    by_floor = {}
    for floor in parsed['floors']:
        for number in range(floor['first_floor'], floor['last_floor'] + 1):
            if number in by_floor:
                raise ValueError('Overlapping floor definitions')
            by_floor[number] = floor
    report = []
    for number, pool, enemies, treasures in baseline:
        floor = by_floor.get(number)
        if floor is None:
            report.append(dict(floor=number, agrees=False,
                               reason='Floor missing from decoded definitions'))
            continue
        try:
            actual_pool = floor['parameters']['f008']
        except (TypeError, KeyError):
            raise ValueError('Floor lacks unit pool parameter')
        actual_enemies = sorted(r['source_token'] for r in floor['enemies'])
        actual_treasures = sorted(r['treasure_id'] for r in floor['treasures'])
        mismatches = []
        if actual_pool != pool:
            mismatches.append('unit_pool %r != baseline %r' % (actual_pool, pool))
        if actual_enemies != sorted(enemies):
            mismatches.append('enemy roster differs (%d decoded vs %d baseline)'
                              % (len(actual_enemies), len(enemies)))
        if actual_treasures != sorted(treasures):
            mismatches.append('treasure roster differs (%d decoded vs %d baseline)'
                              % (len(actual_treasures), len(treasures)))
        report.append(dict(floor=number, agrees=not mismatches,
                           mismatches=mismatches))
    return report


def baseline_matches_lane_entry(lanes_path):
    """Guard embedded baseline against the read-only lane entry drift."""
    import json
    try:
        document = json.loads(Path(lanes_path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise ValueError('Lane plan unreadable')
    entries = [lane for lane in document.get('lanes', [])
               if lane.get('lane') == 'p2-cave-tutorial_3']
    if len(entries) != 1:
        raise ValueError('Lane entry missing or ambiguous')
    expected = [(floor['first'], floor['unit_pool'],
                 tuple(floor['enemy_ids']), tuple(floor['treasure_ids']))
                for floor in entries[0]['details']['floors']]
    actual = [(number, pool, enemies, treasures)
              for number, pool, enemies, treasures in BASELINE_FLOORS]
    if actual != expected:
        raise ValueError('Embedded baseline drifted from lane entry')
    return True


def unsupported_references(parsed, enemy_ids, treasure_ids):
    """Enemy/treasure tokens with no authoritative reference: explicit blockers."""
    if enemy_ids is None or treasure_ids is None:
        raise ValueError('Authoritative enemy/treasure reference sets required')
    missing_enemies = sorted({row['source_token'] for floor in parsed['floors']
                              for row in floor['enemies']
                              if row['enemy_id'] not in enemy_ids})
    missing_treasures = sorted({row['treasure_id'] for floor in parsed['floors']
                                for row in floor['treasures']
                                if row['treasure_id'] not in treasure_ids})
    return dict(enemies=missing_enemies, treasures=missing_treasures)


def resource_closure_manifest(parsed):
    """Unit pools referenced per floor plus roster totals (definitions only)."""
    manifest = []
    for floor in parsed['floors']:
        try:
            pool = floor['parameters']['f008']
        except (TypeError, KeyError):
            raise ValueError('Floor lacks unit pool parameter')
        manifest.append(dict(first_floor=floor['first_floor'],
                             last_floor=floor['last_floor'], unit_pool=pool,
                             enemies=len(floor['enemies']),
                             treasures=len(floor['treasures'])))
    return manifest


def read_source_file(path):
    """Read local cave definition bytes; exact error when unavailable."""
    try:
        data = Path(path).read_bytes()
    except OSError:
        raise ValueError('Source unavailable: ' + str(path))
    if not data:
        raise ValueError('Source empty: ' + str(path))
    return data


def read_iso_entry(iso_path, member=SOURCE_PATH):
    """Read the cave definition from a local retail ISO; exact prerequisite.

    Requires a US GPVE01 revision 0 disc image exposing the caveinfo
    member. The standard runtime ISO in this workspace is a source-test
    image, not a retail disc: callers must supply a real one.
    """
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
    """Exact native/framework owners required before P1/P2 activation."""
    return [
        '#129 cave generation/seams/navigation (active #468, lanes 34-51): '
        'accepted generator pin required; no replacement forked here',
        '#128/#130/#131/#140-#146 actor/assets/species/hazards: roster '
        'admission (e.g. Sarai, Demon, WaterOtakara, Queen_dashboots, Baby) '
        'blocks promotion, not P0 preparation',
        '#132 surface days/saves/progression: stable course/floor identity '
        'and schedules preserved from source, not redefined here',
        'Unit pool arc/texts closure per floor (BASE/units/<pool> + arc '
        'members): unverified until retail ISO bytes are available',
    ]


def summarize(parsed, source_sha256, enemy_ids, treasure_ids):
    """Reviewed P0 implementation packet: metadata only, nothing playable."""
    validate_floor_coverage(parsed)
    agreement = baseline_agreement(parsed)
    unsupported = unsupported_references(parsed, enemy_ids, treasure_ids)
    floors = []
    for floor in parsed['floors']:
        rows = [dict(definition_id='%s:definition%d:enemy:%d'
                     % (CAVE_ID, floor['definition_index'], i),
                     source=row, runtime_status='unsupported',
                     reason='P0 metadata only; no native species/distribution '
                            'acceptance in this stage',
                     placement=None)
                for i, row in enumerate(floor['enemies'])]
        floors.append(dict(first_floor=floor['first_floor'],
                           last_floor=floor['last_floor'],
                           parameters=floor['parameters'], enemies=rows,
                           treasures=floor['treasures'], gates=floor['gates'],
                           caps=floor['caps']))
    return dict(schema=SCHEMA, cave=CAVE_ID, source=SOURCE_PATH,
                source_sha256=source_sha256, floor_coverage=len(occupied_floors(parsed)),
                baseline_agrees=all(row['agrees'] for row in agreement),
                baseline_report=agreement, unsupported=unsupported,
                resource_closure=resource_closure_manifest(parsed),
                blockers=native_framework_blockers(), floors=floors,
                retail_generation=False, playable=False,
                limitations=['Weights/counts are definition inputs, not final spawn '
                             'instances or placements.',
                             'No seeded topology, hole selection, radial distribution '
                             'or restart identity is generated.',
                             'P0 packet is metadata for integrator review; full '
                             'content issue #153 stays OPEN.'])
