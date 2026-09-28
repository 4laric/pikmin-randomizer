"""Reconcile divergent cave per-floor table shapes into lane 34's canonical form.

The cave wave published three per-floor table shapes:

* lane 34 -- ``experimental.pikmin2_cave_schema``, validated by
  ``validate_floor_table``.  This is the canonical shape the wave's docs call
  ``p2-cave-floor-table-v1`` even though its ``schema`` field is the integer
  ``SCHEMA_VERSION``: canonical ``{cave_id}:f{floor}:{class}:{index}`` slot ids,
  ordered ``segments``/``chokes``/``leaves``/``buds``/``treasures`` plus ``hole``.
* lane 36 -- ``experimental.pikmin2_cave_leaf`` ``p2-cave-leaf-table-v1``: only
  ``segments`` (with free ``doors``) and ``leaves``; no seed, chokes, treasures,
  buds or hole.
* lane 40 -- ``experimental.pikmin2_cave_spike`` ``p2-cave-seeded-table/1``: QA's
  ``chokes``/``leaves``/``buds``/``treasures``/``hole`` vocabulary keyed by
  ``segment_index``, with no unit names and untagged treasures.

``to_canonical`` maps the lane-36 and lane-40 shapes onto lane 34's canonical
shape by importing the lane-34/36/40 modules instead of re-declaring a schema.
``reconcile_report`` records, per input table, which shape it was and which
fields could not be carried across.  A table that cannot be mapped without
inventing data raises ``ReconcileError`` (a ``ValueError``) with a clear message.
"""
import copy
import re

from experimental.pikmin2_cave_leaf import LEAF_TABLE_SCHEMA
from experimental.pikmin2_cave_schema import (
    HAZARD_SPECIES,
    HAZARDS,
    SCHEMA_VERSION,
    slot_id,
    validate_floor_table,
)
from experimental.pikmin2_cave_spike import SCHEMA_TABLE

SHAPE_CANONICAL = 'lane34-canonical'
SHAPE_LEAF = 'lane36-leaf-table'
SHAPE_SPIKE = 'lane40-spike-table'
SHAPE_UNKNOWN = 'unrecognized'

# lane 36 names its floor as one provenance string, e.g. "forest_1:floor2".
_FLOOR = re.compile(r'^(?P<cave>[^:]+):(?:floor)?(?P<floor>\d+)$')


class ReconcileError(ValueError):
    """Raised when an input table cannot be mapped onto the canonical shape."""


def _note(field, disposition, detail):
    return {'field': field, 'disposition': disposition, 'detail': detail}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _shape_of(table):
    if not isinstance(table, dict):
        return SHAPE_UNKNOWN
    if table.get('schema') == SCHEMA_VERSION and 'cave_id' in table:
        return SHAPE_CANONICAL
    if table.get('schema') == LEAF_TABLE_SCHEMA:
        return SHAPE_LEAF
    if table.get('schema') == SCHEMA_TABLE:
        return SHAPE_SPIKE
    return SHAPE_UNKNOWN


def _from_leaf(table):
    """Map the lane-36 leaf table onto the canonical shape."""
    notes = []
    identity = table.get('floor')
    if not isinstance(identity, str):
        raise ReconcileError('lane-36 table.floor must be a "<cave>:floor<N>" string')
    match = _FLOOR.match(identity)
    if match is None:
        raise ReconcileError('cannot read cave/floor from lane-36 table.floor %r' % (identity,))
    cave_id, floor = match.group('cave'), int(match.group('floor'))

    raw_segments = table.get('segments')
    if not isinstance(raw_segments, list) or len(raw_segments) < 2:
        raise ReconcileError('lane-36 table needs at least two segments')
    segments = []
    for position, segment in enumerate(raw_segments):
        if not isinstance(segment, dict) or segment.get('segment') != position:
            raise ReconcileError('lane-36 segment index must equal its list position')
        segments.append({'slot_id': slot_id(cave_id, floor, 'segment', position),
                         'index': position})
        if 'doors' in segment:
            notes.append(_note('segments[%d].doors' % position, 'dropped',
                               'free doors are a lane-35/36 product, absent from the canonical table'))

    raw_leaves = table.get('leaves', [])
    if not isinstance(raw_leaves, list):
        raise ReconcileError('lane-36 table.leaves must be a list')
    leaves = []
    for position, leaf in enumerate(raw_leaves):
        if not isinstance(leaf, dict) or leaf.get('hazard') not in HAZARDS:
            raise ReconcileError('lane-36 leaf has an unknown hazard')
        segment = leaf.get('segment')
        if not _is_int(segment) or not 0 <= segment < len(segments):
            raise ReconcileError('lane-36 leaf references a missing segment')
        leaves.append({'slot_id': slot_id(cave_id, floor, 'leaf', position),
                       'index': position, 'segment': segment,
                       'hazard': leaf['hazard'], 'item_slots': 1})
        notes.append(_note('leaves[%d].slot' % position, 'dropped',
                           'the leaf label is not part of the canonical slot id'))

    notes.append(_note('seed', 'derived',
                       'lane-36 has no seed; the floor id %r is used' % identity))
    notes.append(_note('hole', 'derived',
                       'lane-36 has no hole marker; the last segment is used'))
    notes.append(_note('chokes', 'defaulted', 'lane-36 carries no chokes; mapped empty'))
    notes.append(_note('buds', 'defaulted', 'lane-36 carries no buds; mapped empty'))
    notes.append(_note('treasures', 'defaulted', 'lane-36 carries no treasures; mapped empty'))

    hole_segment = len(segments) - 1
    canonical = {
        'schema': SCHEMA_VERSION, 'seed': identity, 'cave_id': cave_id, 'floor': floor,
        'segments': segments, 'chokes': [], 'leaves': leaves, 'buds': [], 'treasures': [],
        'hole': {'slot_id': segments[hole_segment]['slot_id'], 'segment': hole_segment},
        'generated': False, 'geometry_rerolls': True,
    }
    return canonical, notes


def _from_spike(table):
    """Map the lane-40 spike table onto the canonical shape."""
    notes = []
    cave_id, floor, seed = table.get('cave'), table.get('floor'), table.get('seed')
    if not isinstance(cave_id, str) or not cave_id:
        raise ReconcileError('lane-40 table.cave must be a non-empty string')
    if not _is_int(floor) or floor < 1:
        raise ReconcileError('lane-40 table.floor must be a positive integer')

    raw_segments = table.get('segments')
    if not isinstance(raw_segments, list) or len(raw_segments) < 2:
        raise ReconcileError('lane-40 table needs at least two segments')
    segments = []
    for position, segment in enumerate(raw_segments):
        if not isinstance(segment, dict) or segment.get('index') != position:
            raise ReconcileError('lane-40 segment index must equal its list position')
        segments.append({'slot_id': slot_id(cave_id, floor, 'segment', position),
                         'index': position})
        if 'name' in segment:
            notes.append(_note('segments[%d].name' % position, 'dropped',
                               'segment name is not part of the canonical table'))

    leaves, leaf_by_id = [], {}
    for position, leaf in enumerate(table.get('leaves', [])):
        if not isinstance(leaf, dict) or leaf.get('hazard') not in HAZARDS:
            raise ReconcileError('lane-40 leaf has an unknown hazard')
        segment = leaf.get('segment_index')
        if not _is_int(segment) or not 0 <= segment < len(segments):
            raise ReconcileError('lane-40 leaf references a missing segment')
        record = {'slot_id': slot_id(cave_id, floor, 'leaf', position), 'index': position,
                  'segment': segment, 'hazard': leaf['hazard'], 'item_slots': 1}
        leaves.append(record)
        leaf_by_id[leaf.get('id')] = record
        if 'item_slot' in leaf:
            notes.append(_note('leaves[%d].item_slot' % position, 'dropped',
                               'the single item_slot label becomes canonical item_slots=1'))

    chokes = []
    for position, choke in enumerate(table.get('chokes', [])):
        hazard = choke.get('kind') if isinstance(choke, dict) else None
        segment = choke.get('segment_index') if isinstance(choke, dict) else None
        if hazard not in HAZARDS:
            raise ReconcileError('lane-40 choke %r kind %r is not a canonical hazard'
                                 % (choke.get('id') if isinstance(choke, dict) else choke, hazard))
        if not _is_int(segment) or not 1 <= segment < len(segments):
            raise ReconcileError('lane-40 choke %r segment_index must gate an existing segment'
                                 % (choke.get('id'),))
        spec = HAZARDS[hazard]
        unit = choke.get('unit')
        if not (isinstance(unit, str) and unit):
            unit = choke.get('id')
            if not (isinstance(unit, str) and unit):
                raise ReconcileError('lane-40 choke has neither a unit nor an id to substitute')
            notes.append(_note('chokes[%d].unit' % position, 'substituted',
                               'lane-40 has no unit name; the choke id %r is used' % unit))
        chokes.append({'slot_id': slot_id(cave_id, floor, 'choke', position), 'index': position,
                       'after_segment': segment - 1, 'before_segment': segment,
                       'hazard': hazard, 'kind': spec['kind'], 'hardness': spec['kind'],
                       'unit': unit})
        notes.append(_note('chokes[%d].kind' % position, 'renamed',
                           'lane-40 kind holds the hazard; canonical kind/hardness come from HAZARDS'))

    buds = []
    for position, bud in enumerate(table.get('buds', [])):
        hazard, segment, count = bud.get('hazard'), bud.get('segment_index'), bud.get('count')
        species = HAZARD_SPECIES.get(hazard)
        if species is None:
            raise ReconcileError('lane-40 bud hazard %r has no canonical species' % (hazard,))
        if not _is_int(segment) or not 0 <= segment < len(segments):
            raise ReconcileError('lane-40 bud references a missing segment')
        if not _is_int(count) or count < 1:
            raise ReconcileError('lane-40 bud count must be >= 1')
        buds.append({'slot_id': slot_id(cave_id, floor, 'bud', position), 'index': position,
                     'segment': segment, 'species': species, 'count': count})
        notes.append(_note('buds[%d].hazard' % position, 'renamed',
                           'lane-40 bud hazard maps to canonical species via HAZARD_SPECIES'))

    treasures = []
    for treasure in table.get('treasures', []):
        if not treasure.get('tagged'):
            notes.append(_note('treasures[%r]' % treasure.get('id'), 'dropped',
                               'untagged treasures use the normal pool and have no canonical leaf binding'))
            continue
        record = leaf_by_id.get(treasure.get('leaf'))
        if record is None:
            raise ReconcileError('lane-40 tagged treasure %r references an unknown leaf'
                                 % (treasure.get('id'),))
        if treasure.get('hazard') != record['hazard']:
            raise ReconcileError('lane-40 tagged treasure %r hazard disagrees with its leaf'
                                 % (treasure.get('id'),))
        treasures.append({'treasure_id': treasure.get('id'), 'slot_id': record['slot_id'],
                          'segment': record['segment'], 'leaf_hazard': record['hazard']})

    raw_hole = table.get('hole')
    if not isinstance(raw_hole, dict) or not _is_int(raw_hole.get('segment_index')):
        raise ReconcileError('lane-40 table.hole is malformed')
    hole_segment = raw_hole['segment_index']
    if hole_segment != len(segments) - 1:
        raise ReconcileError('lane-40 hole must be the last segment to map onto the canonical shape')

    canonical = {
        'schema': SCHEMA_VERSION, 'seed': seed, 'cave_id': cave_id, 'floor': floor,
        'segments': segments, 'chokes': chokes, 'leaves': leaves, 'buds': buds,
        'treasures': treasures,
        'hole': {'slot_id': segments[hole_segment]['slot_id'], 'segment': hole_segment},
        'generated': False, 'geometry_rerolls': True,
    }
    return canonical, notes


def _convert(table):
    shape = _shape_of(table)
    if shape == SHAPE_CANONICAL:
        return copy.deepcopy(table), shape, []
    if shape == SHAPE_LEAF:
        canonical, notes = _from_leaf(table)
    elif shape == SHAPE_SPIKE:
        canonical, notes = _from_spike(table)
    else:
        schema = table.get('schema') if isinstance(table, dict) else table
        raise ReconcileError('unrecognized floor table schema: %r' % (schema,))
    validate_floor_table(canonical)
    return canonical, shape, notes


def to_canonical(floor_table):
    """Return ``floor_table`` as a lane-34 canonical ``p2-cave-floor-table-v1``.

    Accepts the lane-36 leaf-table shape, the lane-40 spike shape, or an already
    canonical table (returned as an independent copy).  Raises ``ReconcileError``
    when a shape cannot be mapped without inventing fields.
    """
    return _convert(floor_table)[0]


def reconcile_report(tables):
    """Summarise the shape of each table and every field that could not be mapped."""
    if not isinstance(tables, list):
        raise ReconcileError('reconcile_report expects a list of floor tables')
    rows = []
    shapes = {}
    for index, table in enumerate(tables):
        shape = _shape_of(table)
        try:
            _canonical, shape, notes = _convert(table)
            row = {'index': index, 'shape': shape, 'ok': True,
                   'unmapped': notes, 'error': None}
        except ValueError as error:
            row = {'index': index, 'shape': shape, 'ok': False,
                   'unmapped': [], 'error': str(error)}
        shapes[row['shape']] = shapes.get(row['shape'], 0) + 1
        rows.append(row)
    fields = sorted({note['field'] for row in rows for note in row['unmapped']})
    return {'total': len(tables), 'shapes': shapes, 'tables': rows, 'unmapped_fields': fields}
