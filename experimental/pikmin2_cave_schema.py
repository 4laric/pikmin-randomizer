"""Lane 34 (#473) host-side cave slot schema and per-floor seeded table.

Implements the frozen #468 model: four slot classes (segment, choke, leaf, bud),
hazard tags with their hardness and alternate key, a per-floor seeded structural
table, a fail-closed validator, the logic requirement projection and a worked
`forest_1` example. It generates no geometry and edits no native code; lanes
35-38 realize the table in the engine and lane 39 consumes ``requirements``.
"""
import argparse
import hashlib
import json
import random
from pathlib import Path

SCHEMA_VERSION = 1
SLOT_CLASSES = ('segment', 'choke', 'leaf', 'bud')

HAZARDS = {
    'water': {'kind': 'hard', 'form': 'pool', 'captain_can_wade': True,
              'captain_can_carry': False, 'alternate_key': 'blue'},
    'elec': {'kind': 'hard', 'form': 'gate', 'captain_can_wade': False,
             'captain_can_carry': False, 'alternate_key': 'yellow'},
    'fire': {'kind': 'soft', 'form': 'geyser', 'captain_can_wade': True,
             'captain_can_carry': True, 'alternate_key': 'red'},
    'poison': {'kind': 'soft', 'form': 'geyser', 'captain_can_wade': True,
               'captain_can_carry': True, 'alternate_key': 'white'},
}
HAZARD_SPECIES = {'water': 'blue', 'elec': 'yellow', 'fire': 'red', 'poison': 'white'}
SPECIES_HAZARD = {species: hazard for hazard, species in HAZARD_SPECIES.items()}
SPECIES_PURPLE = 'purple'
HARDNESS = ('hard', 'soft')
SEED_NAMESPACE = b'P2_CAVE_SEED_1'
MAX_SLOTS = 1000


class SchemaError(ValueError):
    """Raised when a cave table violates the frozen slug/hazard schema."""


def slot_id(cave_id, floor, slot_class, index):
    if slot_class not in SLOT_CLASSES:
        raise SchemaError('Unknown slot class: ' + repr(slot_class))
    if not isinstance(cave_id, str) or not cave_id or ':' in cave_id:
        raise SchemaError('Invalid cave id')
    if not isinstance(floor, int) or isinstance(floor, bool) or floor < 1:
        raise SchemaError('Invalid floor')
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < MAX_SLOTS:
        raise SchemaError('Invalid slot index')
    return f'{cave_id}:f{floor}:{slot_class}:{index}'


def _parse_slot(value, cave_id, floor):
    if not isinstance(value, str):
        return None
    parts = value.split(':')
    if len(parts) != 4 or parts[0] != cave_id or parts[1] != f'f{floor}':
        return None
    if parts[2] not in SLOT_CLASSES or not parts[3].isdigit():
        return None
    return parts[2], int(parts[3])


def _require(condition, message):
    if not condition:
        raise SchemaError(message)


def _integer(value, message, minimum=0):
    _require(isinstance(value, int) and not isinstance(value, bool) and value >= minimum, message)
    return value


def valid_hazard(hazard):
    return hazard in HAZARDS


def _collect_slot_ids(table, cave_id, floor):
    seen = {}
    for collection, slot_class in (('segments', 'segment'), ('chokes', 'choke'),
                                   ('leaves', 'leaf'), ('buds', 'bud')):
        entries = table.get(collection)
        _require(isinstance(entries, list), 'Missing slot collection: ' + collection)
        for position, entry in enumerate(entries):
            _require(isinstance(entry, dict), 'Malformed slot entry: ' + collection)
            parsed = _parse_slot(entry.get('slot_id'), cave_id, floor)
            _require(parsed is not None and parsed[0] == slot_class,
                     'Non-canonical slot id in ' + collection)
            _require(parsed[1] == position, 'Slot index is not the list position in ' + collection)
            _require(entry['slot_id'] not in seen,
                     'Duplicate slot id: ' + entry['slot_id'])
            seen[entry['slot_id']] = slot_class
    return seen


def _validate_segments(table, cave_id, floor):
    segments = table['segments']
    _require(len(segments) >= 2, 'At least two segments are required')
    for index, segment in enumerate(segments):
        _integer(segment.get('index'), 'Invalid segment index', 0)
        _require(segment['index'] == index, 'Non-contiguous segment indices')
    return [segment['index'] for segment in segments]


def _validate_chokes(table, segments):
    chokes = table['chokes']
    for index, choke in enumerate(chokes):
        _require(choke.get('index') == index, 'Non-contiguous choke ordering')
        after = _integer(choke.get('after_segment'), 'Invalid choke after_segment', 0)
        before = _integer(choke.get('before_segment'), 'Invalid choke before_segment', 0)
        _require(before == after + 1, 'Choke does not join adjacent segments')
        _require(after in segments and before in segments, 'Choke references unknown segment')
        _require(valid_hazard(choke.get('hazard')), 'Unknown choke hazard')
        _require(choke.get('kind') in HARDNESS, 'Invalid choke kind')
        _require(choke.get('hardness') in HARDNESS, 'Invalid choke hardness')
        _require(isinstance(choke.get('unit'), str) and choke['unit'], 'Missing choke unit')
    return chokes


def _validate_leaves(table, segments):
    leaves = table['leaves']
    by_slot = {}
    for index, leaf in enumerate(leaves):
        _require(leaf.get('index') == index, 'Non-contiguous leaf ordering')
        _integer(leaf.get('segment'), 'Invalid leaf segment', 0)
        _require(leaf['segment'] in segments, 'Leaf references unknown segment')
        _require(valid_hazard(leaf.get('hazard')), 'Unknown leaf hazard')
        _require('item_slots' in leaf and leaf['item_slots'] == 1,
                 'A leaf carries exactly one item slot')
        by_slot[leaf['slot_id']] = leaf
    return by_slot


def _validate_buds(table, segments, chokes):
    for index, bud in enumerate(table['buds']):
        _require(bud.get('index') == index, 'Non-contiguous bud ordering')
        segment = _integer(bud.get('segment'), 'Invalid bud segment', 0)
        _require(segment in segments, 'Bud references unknown segment')
        species = bud.get('species')
        _require(species in HAZARD_SPECIES.values() or species == SPECIES_PURPLE,
                 'Unknown bud species')
        _integer(bud.get('count'), 'Invalid bud conversion count', 1)
        hazard = SPECIES_HAZARD.get(species)
        if hazard is not None:
            nearest = {choke['hazard'] for choke in chokes if choke['after_segment'] < segment}
            _require(hazard not in nearest, 'Bud species gated by its own hazard')


def _validate_treasures(table, leaves_by_slot, hole_segment, known_treasures):
    seen = set()
    for treasure in table['treasures']:
        treasure_id = treasure.get('treasure_id')
        _require(isinstance(treasure_id, str) and treasure_id, 'Invalid treasure id')
        _require(treasure_id not in seen, 'Duplicate treasure id: ' + treasure_id)
        seen.add(treasure_id)
        if known_treasures is not None:
            _require(treasure_id in known_treasures, 'Unknown treasure: ' + treasure_id)
        leaf = leaves_by_slot.get(treasure.get('slot_id'))
        _require(leaf is not None, 'Treasure references unknown leaf slot')
        _require(treasure.get('leaf_hazard') == leaf['hazard'],
                 'Treasure tag disagrees with its leaf hazard')
        _require(treasure.get('segment') == leaf['segment'],
                 'Treasure segment disagrees with its leaf segment')
        _require(leaf['segment'] <= hole_segment, 'Treasure is placed beyond the hole')
    return seen


def _validate_hole(table, segments):
    hole = table.get('hole')
    _require(isinstance(hole, dict), 'Missing hole')
    segment = _integer(hole.get('segment'), 'Invalid hole segment', 0)
    _require(segment == segments[-1], 'Hole must be the last segment')
    parsed = _parse_slot(hole.get('slot_id'), table['cave_id'], table['floor'])
    _require(parsed is not None and parsed[0] == 'segment' and parsed[1] == segment,
             'Hole slot id must name its segment')
    return segment


def validate_floor_table(table, known_treasures=None):
    _require(isinstance(table, dict), 'Table must be a mapping')
    _require(table.get('schema') == SCHEMA_VERSION, 'Unsupported cave schema version')
    cave_id = table.get('cave_id')
    _require(isinstance(cave_id, str) and cave_id and ':' not in cave_id, 'Invalid cave id')
    _integer(table.get('floor'), 'Invalid floor', 1)
    seed = table.get('seed')
    _require(isinstance(seed, (str, int)) and not isinstance(seed, bool) and str(seed) != '',
             'Missing seed')
    segments = _validate_segments(table, cave_id, table['floor'])
    _collect_slot_ids(table, cave_id, table['floor'])
    chokes = _validate_chokes(table, segments)
    leaves = _validate_leaves(table, segments)
    _validate_buds(table, segments, chokes)
    hole_segment = _validate_hole(table, segments)
    _validate_treasures(table, leaves, hole_segment, known_treasures)
    return table


def _path_chokes(chokes, segment):
    return [choke['slot_id'] for choke in chokes if choke['after_segment'] < segment]


def requirements(table):
    validate_floor_table(table)
    chokes = table['chokes']
    report = {'treasures': {}, 'hole': {'segment': table['hole']['segment'],
                                        'chokes': _path_chokes(chokes, table['hole']['segment'])}}
    for treasure in table['treasures']:
        report['treasures'][treasure['treasure_id']] = {
            'segment': treasure['segment'],
            'leaf_hazard': treasure['leaf_hazard'],
            'chokes': _path_chokes(chokes, treasure['segment']),
        }
    return report


def _rng(seed, cave_id, floor):
    material = SEED_NAMESPACE + b'\0' + str(seed).encode('utf-8') + b'\0' + \
        cave_id.encode('utf-8') + b'\0' + str(floor).encode('utf-8')
    return random.Random(int.from_bytes(hashlib.sha256(material).digest(), 'big'))


def _bud_allowed(species, segment, chokes):
    hazard = SPECIES_HAZARD.get(species)
    if hazard is None:
        return True
    return all(choke['hazard'] != hazard for choke in chokes if choke['after_segment'] < segment)


def derive_floor_table(seed, cave_id, floor, *, unit_pool, unit_candidates,
                       tagged_treasures, gates=()):
    _require(seed is not None and str(seed) != '', 'Missing seed')
    _require(isinstance(cave_id, str) and cave_id, 'Invalid cave id')
    _integer(floor, 'Invalid floor', 1)
    _require(isinstance(unit_pool, str) and unit_pool, 'Missing unit pool')
    _require(isinstance(unit_candidates, (list, tuple)) and unit_candidates,
             'Missing unit candidates')
    _require(isinstance(tagged_treasures, (list, tuple)), 'Invalid tagged treasures')
    _require(isinstance(gates, (list, tuple)), 'Invalid gates')
    for tagged in tagged_treasures:
        _require(isinstance(tagged, dict) and isinstance(tagged.get('treasure_id'), str)
                 and tagged.get('hazard') in HAZARDS, 'Invalid tagged treasure')

    rng = _rng(seed, cave_id, floor)
    segment_count = 2 + rng.randrange(0, 3)
    segments = [{'slot_id': slot_id(cave_id, floor, 'segment', i), 'index': i}
                for i in range(segment_count)]

    choke_count = rng.randrange(0, segment_count)
    choke_pool = sorted(HAZARDS)
    chokes = []
    for i in range(choke_count):
        hazard = rng.choice(choke_pool)
        spec = HAZARDS[hazard]
        chokes.append({
            'slot_id': slot_id(cave_id, floor, 'choke', i), 'index': i,
            'after_segment': i, 'before_segment': i + 1, 'hazard': hazard,
            'kind': spec['kind'], 'hardness': spec['kind'],
            'unit': rng.choice(list(unit_candidates)),
        })

    leaves = []
    treasures = []
    for i, tagged in enumerate(tagged_treasures):
        leaves.append({
            'slot_id': slot_id(cave_id, floor, 'leaf', i), 'index': i,
            'segment': rng.randrange(0, segment_count), 'hazard': tagged['hazard'],
            'item_slots': 1,
        })
        treasures.append({
            'treasure_id': tagged['treasure_id'], 'slot_id': leaves[-1]['slot_id'],
            'segment': leaves[-1]['segment'], 'leaf_hazard': tagged['hazard'],
        })

    buds = []
    for i in range(rng.randrange(0, 2)):
        species = rng.choice(sorted(SPECIES_HAZARD) + [SPECIES_PURPLE])
        candidates = [s for s in range(segment_count) if _bud_allowed(species, s, chokes)]
        if not candidates:
            continue
        buds.append({'slot_id': slot_id(cave_id, floor, 'bud', len(buds)), 'index': len(buds),
                     'segment': rng.choice(candidates), 'species': species, 'count': 5})

    table = {
        'schema': SCHEMA_VERSION, 'seed': str(seed), 'cave_id': cave_id, 'floor': floor,
        'unit_pool': unit_pool,
        'segments': segments, 'chokes': chokes, 'leaves': leaves, 'buds': buds,
        'treasures': treasures,
        'hole': {'slot_id': segments[-1]['slot_id'], 'segment': segments[-1]['index']},
        'generated': True, 'geometry_rerolls': True,
    }
    validate_floor_table(table)
    return table


def table_digest(table):
    payload = {key: table[key] for key in
               ('schema', 'seed', 'cave_id', 'floor', 'unit_pool', 'segments', 'chokes',
                'leaves', 'buds', 'treasures', 'hole') if key in table}
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def worked_example():
    cave_id, floor = 'forest_1', 1
    segments = [{'slot_id': slot_id(cave_id, floor, 'segment', i), 'index': i}
                for i in range(3)]
    chokes = [{
        'slot_id': slot_id(cave_id, floor, 'choke', 0), 'index': 0,
        'after_segment': 0, 'before_segment': 1, 'hazard': 'water', 'kind': 'hard',
        'hardness': 'hard', 'unit': 'way2_tsuchi',
    }]
    leaves = [
        {'slot_id': slot_id(cave_id, floor, 'leaf', 0), 'index': 0, 'segment': 0,
         'hazard': 'water', 'item_slots': 1},
        {'slot_id': slot_id(cave_id, floor, 'leaf', 1), 'index': 1, 'segment': 1,
         'hazard': 'elec', 'item_slots': 1},
    ]
    treasures = [
        {'treasure_id': 'juji_key_fc', 'slot_id': leaves[0]['slot_id'], 'segment': 0,
         'leaf_hazard': 'water'},
        {'treasure_id': 'example_elec_treasure', 'slot_id': leaves[1]['slot_id'],
         'segment': 1, 'leaf_hazard': 'elec'},
    ]
    table = {
        'schema': SCHEMA_VERSION, 'seed': 'worked-example', 'cave_id': cave_id, 'floor': floor,
        'unit_pool': '1_units_cent3_tsuchi.txt',
        'segments': segments, 'chokes': chokes, 'leaves': leaves, 'buds': [],
        'treasures': treasures,
        'hole': {'slot_id': segments[-1]['slot_id'], 'segment': segments[-1]['index']},
        'generated': False, 'geometry_rerolls': True,
    }
    validate_floor_table(table)
    return table


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed')
    parser.add_argument('--cave')
    parser.add_argument('--floor', type=int)
    parser.add_argument('--pool')
    parser.add_argument('--unit', action='append', default=[])
    parser.add_argument('--tag', action='append', default=[],
                        help='treasure_id=hazard, repeatable')
    parser.add_argument('--worked', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.worked:
        table = worked_example()
    else:
        _require(args.seed and args.cave and args.floor and args.pool and args.unit,
                 '--seed, --cave, --floor, --pool and --unit are required without --worked')
        tagged = []
        for item in args.tag:
            _require('=' in item, 'Malformed --tag')
            treasure_id, hazard = item.split('=', 1)
            _require(hazard in HAZARDS, 'Unknown --tag hazard')
            tagged.append({'treasure_id': treasure_id, 'hazard': hazard})
        table = derive_floor_table(args.seed, args.cave, args.floor,
                                   unit_pool=args.pool, unit_candidates=args.unit,
                                   tagged_treasures=tagged)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(table, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(output=str(args.output), digest=table_digest(table),
                          slots=len(table['segments']) + len(table['chokes'])
                          + len(table['leaves']) + len(table['buds']))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
