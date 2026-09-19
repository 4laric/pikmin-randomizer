"""Multi-floor AP logic over lane 34's seeded cave tables (lane 39, #478).

Lane 34 (`experimental.pikmin2_cave_schema`) emits one `p2-cave-floor-table-v1`
per floor: canonical slot ids, segments, chokes, leaves, buds, tagged treasures
and the hole, all derived from the AP seed.  It also projects the per-floor logic
graph via ``requirements(table)`` and owns single-floor validation.  This module
is the AP side it names as the consumer: it composes whole-cave requirements,
adds the bud alternative keys and Pikmin-count tracking, inherits every floor's
chokes into every deeper floor, applies ambient worst-case hazards and turns all
of that into stable hints and a serialisable slot_data row.

Nothing here generates geometry or edits native code, and nothing reads an
observed layout.  Every function is a pure function of the frozen tables, so a
requirement or hint cannot change when the engine rerolls the room on re-entry.

Consumed table fields (see `docs/PIKMIN2_CAVE_SCHEMA.md`):

* ``segments[]``  — ``{slot_id, index}``, index 0-based.
* ``chokes[]``    — ``{slot_id, index, after_segment, before_segment, hazard,
  kind, hardness, unit}``; a choke joins ``after_segment`` to ``before_segment``.
* ``leaves[]``    — ``{slot_id, index, segment, hazard, item_slots}``.
* ``buds[]``      — ``{slot_id, index, segment, species, count}``.
* ``treasures[]`` — ``{treasure_id, slot_id, segment, leaf_hazard}``.
* ``hole``        — ``{slot_id, segment}``, the last segment.

An optional AP-side ``ambient_hazards`` list per table is honoured as worst-case
(non-alcove) hazards; lane 34's validator ignores the extra key.
"""
import hashlib
import json

from .catalog import field_capacity

SCHEMA = 1
HAZARDS = ('water', 'elec', 'fire', 'poison')

# Mirrors lane 34's HAZARDS table: per hazard the default hardness and the Pikmin
# species (candypop colour) that provides the alternate key.  Hardness is a
# per-choke field in the table; this default is only used for leaves and ambient
# hazards, where the table does not carry one.
DEFAULT_HAZARDS = {
    'water': {'hardness': 'hard', 'species': 'blue'},
    'elec': {'hardness': 'hard', 'species': 'yellow'},
    'fire': {'hardness': 'soft', 'species': 'red'},
    'poison': {'hardness': 'soft', 'species': 'white'},
}

_ABILITY_ITEMS = {'blue': 'Blue Onion', 'yellow': 'Yellow Onion',
                  'red': 'Red Onion', 'white': 'White Onion'}
try:  # pragma: no cover - exercised whenever catalog is importable
    from .catalog import BLUE, YELLOW, RED
    _ABILITY_ITEMS.update({'blue': BLUE, 'yellow': YELLOW, 'red': RED})
except Exception:  # pragma: no cover - defensive for isolated imports
    pass


class CaveLogicError(ValueError):
    """Malformed cave table, hazard tag or serialised requirement."""


def default_config():
    return {'abilities': dict(_ABILITY_ITEMS),
            'hazards': {name: dict(spec) for name, spec in DEFAULT_HAZARDS.items()}}


def _config(config):
    merged = default_config()
    if config:
        merged.update(config)
    return merged


def _positive_int(value, where):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise CaveLogicError('Expected positive integer for %s' % where)
    return value


def _hazard(value, where):
    if value not in HAZARDS:
        raise CaveLogicError('Unknown hazard %r in %s' % (value, where))
    return value


def _ability_item(species, config):
    try:
        return config['abilities'][species]
    except KeyError:
        raise CaveLogicError('No ability item configured for species %r' % (species,))


def load_cave(tables, ambient=None):
    """Index lane 34 floor tables into a whole-cave logic graph.

    ``tables`` is a sequence of ``p2-cave-floor-table-v1`` mappings (one per
    floor) or a single mapping.  ``ambient`` optionally maps a floor number to an
    iterable of worst-case hazards, merged with any ``ambient_hazards`` already on
    the table.  Structural validation stays with lane 34; this only indexes what
    the logic reads and fails closed on anything inconsistent.
    """
    if isinstance(tables, dict):
        tables = [tables]
    if not isinstance(tables, (list, tuple)) or not tables:
        raise CaveLogicError('load_cave needs at least one floor table')
    floors = []
    cave_id = None
    seen_treasures = set()
    for table in tables:
        if not isinstance(table, dict):
            raise CaveLogicError('Floor table must be an object')
        if table.get('schema') != SCHEMA:
            raise CaveLogicError('Unsupported cave schema: %r' % (table.get('schema'),))
        current = table.get('cave_id')
        if not isinstance(current, str) or not current:
            raise CaveLogicError('Floor table needs a cave_id')
        if cave_id is None:
            cave_id = current
        elif current != cave_id:
            raise CaveLogicError('Mixed cave ids: %r and %r' % (cave_id, current))
        number = _positive_int(table.get('floor'), 'floor')
        segments = table.get('segments')
        if not isinstance(segments, list) or not segments:
            raise CaveLogicError('Floor %d has no segments' % number)
        if [segment.get('index') for segment in segments] != list(range(len(segments))):
            raise CaveLogicError('Floor %d segment indices are not 0..n-1' % number)
        chokes = []
        for choke in table.get('chokes', []):
            after = choke.get('after_segment')
            if isinstance(after, bool) or not isinstance(after, int):
                raise CaveLogicError('Floor %d choke has no after_segment' % number)
            if choke.get('hardness') not in ('hard', 'soft'):
                raise CaveLogicError('Floor %d choke has invalid hardness' % number)
            chokes.append({'after_segment': after, 'hazard': _hazard(choke.get('hazard'), 'choke'),
                           'hardness': choke['hardness']})
        buds = []
        for bud in table.get('buds', []):
            segment = bud.get('segment')
            if isinstance(segment, bool) or not isinstance(segment, int) or segment < 0:
                raise CaveLogicError('Floor %d bud has invalid segment' % number)
            buds.append({'segment': segment, 'species': bud.get('species'),
                         'count': _positive_int(bud.get('count'), 'bud count')})
        treasures = []
        for treasure in table.get('treasures', []):
            ident = treasure.get('treasure_id')
            if not isinstance(ident, str) or not ident or ident in seen_treasures:
                raise CaveLogicError('Bad or duplicate treasure id on floor %d' % number)
            seen_treasures.add(ident)
            segment = treasure.get('segment')
            if isinstance(segment, bool) or not isinstance(segment, int) or not 0 <= segment < len(segments):
                raise CaveLogicError('Treasure %r has an out-of-range segment' % (ident,))
            treasures.append({'id': ident, 'segment': segment,
                              'hazard': _hazard(treasure.get('leaf_hazard'), 'treasure')})
        extra = list(table.get('ambient_hazards', []))
        extra += list((ambient or {}).get(number, []))
        floors.append({'floor': number, 'chokes': chokes, 'buds': buds,
                       'treasures': treasures,
                       'ambient_hazards': [_hazard(h, 'ambient hazard') for h in extra]})
    floors.sort(key=lambda floor: floor['floor'])
    if [floor['floor'] for floor in floors] != list(range(1, len(floors) + 1)):
        raise CaveLogicError('Floor numbers must be contiguous 1..n')
    return {'schema': SCHEMA, 'cave_id': cave_id, 'floors': floors}


def _floor(graph, number):
    for floor in graph['floors']:
        if floor['floor'] == number:
            return floor
    raise CaveLogicError('Unknown floor %r' % (number,))


def _locate(graph, treasure_id):
    for floor in graph['floors']:
        for treasure in floor['treasures']:
            if treasure['id'] == treasure_id:
                return floor, treasure
    raise CaveLogicError('Unknown treasure %r' % (treasure_id,))


def _bud_alternatives(floor, segment, hazard, config):
    species = config['hazards'][hazard]['species']
    alternatives = set()
    for bud in floor['buds']:
        if bud['species'] == species and bud['segment'] < segment:
            alternatives.add(('capacity', bud['count'], species))
    return alternatives


def _hazard_key(floor, segment, hazard, hardness, config):
    species = config['hazards'][hazard]['species']
    key = {('item', _ability_item(species, config))}
    if hardness == 'hard':
        key |= _bud_alternatives(floor, segment, hazard, config)
    else:
        key.add(('captain',))
    return frozenset(key)


def _choke_key(floor, choke, config):
    # A bud at or before the choke's source segment is available before it.
    segment = choke['after_segment'] + 1
    return _hazard_key(floor, segment, choke['hazard'], choke['hardness'], config)


def _ambient_key(hazard, config):
    # Worst-case: the hazard may be unavoidable and away from a matching bud.
    species = config['hazards'][hazard]['species']
    return frozenset({('item', _ability_item(species, config))})


def _dedupe(keys):
    result = []
    for key in keys:
        if key and key not in result:
            result.append(key)
    return tuple(result)


def _inherited_keys(graph, floor_number, config):
    keys = []
    for floor in graph['floors']:
        if floor['floor'] >= floor_number:
            continue
        for choke in floor['chokes']:
            keys.append(_choke_key(floor, choke, config))
        for hazard in floor['ambient_hazards']:
            keys.append(_ambient_key(hazard, config))
    return keys


def segment_requirement(graph, floor_number, segment, config=None):
    """Requirement to stand in a floor's segment (union of chokes before it)."""
    config = _config(config)
    floor = _floor(graph, floor_number)
    if not 0 <= segment:
        raise CaveLogicError('Segment out of range: %r' % (segment,))
    keys = _inherited_keys(graph, floor_number, config)
    for choke in floor['chokes']:
        if choke['after_segment'] < segment:
            keys.append(_choke_key(floor, choke, config))
    return _dedupe(keys)


def treasure_requirement(graph, treasure_id, config=None):
    """Full requirement: upper floors + this floor's chokes + leaf + ambient."""
    config = _config(config)
    floor, treasure = _locate(graph, treasure_id)
    keys = list(segment_requirement(graph, floor['floor'], treasure['segment'], config))
    hardness = config['hazards'][treasure['hazard']]['hardness']
    keys.append(_hazard_key(floor, treasure['segment'], treasure['hazard'], hardness, config))
    for hazard in floor['ambient_hazards']:
        keys.append(_ambient_key(hazard, config))
    return _dedupe(keys)


def hole_requirement(graph, floor_number, config=None):
    """Requirement to reach the hole: every choke on this floor and above."""
    config = _config(config)
    floor = _floor(graph, floor_number)
    keys = list(_inherited_keys(graph, floor_number, config))
    for choke in floor['chokes']:
        keys.append(_choke_key(floor, choke, config))
    for hazard in floor['ambient_hazards']:
        keys.append(_ambient_key(hazard, config))
    return _dedupe(keys)


def _literal_ok(literal, inventory, capacity):
    kind = literal[0]
    if kind == 'item':
        return inventory.get(literal[1], 0) > 0
    if kind == 'capacity':
        return capacity >= literal[1]
    if kind == 'captain':
        return True
    raise CaveLogicError('Unknown literal %r' % (literal,))


def satisfied(requirement, inventory, starting_flarlic=2):
    """AND over keys, OR within a key.  Count tracking uses field capacity."""
    capacity = field_capacity(inventory, True, starting_flarlic)
    for key in requirement:
        if not key:
            continue
        if not any(_literal_ok(literal, inventory, capacity) for literal in key):
            return False
    return True


def _key_text(key):
    items = sorted(literal[1] for literal in key if literal[0] == 'item')
    capacities = sorted((literal[2], literal[1]) for literal in key if literal[0] == 'capacity')
    parts = []
    if items:
        parts.append(' or '.join(items))
    for species, count in capacities:
        parts.append('%s candypop (%d)' % (species, count))
    if any(literal[0] == 'captain' for literal in key):
        parts.append('timing')
    return ' or '.join(parts) if parts else 'open'


def hint(graph, treasure_id, config=None):
    """Stable human hint: a pure function of the frozen tables."""
    config = _config(config)
    floor, treasure = _locate(graph, treasure_id)
    requirement = treasure_requirement(graph, treasure_id, config)
    text = ' AND '.join(_key_text(key) for key in requirement) or 'open'
    return 'Floor %d %s: %s' % (floor['floor'], treasure['id'], text)


def validate_tags(graph, tags):
    """Fail closed if an AP hazard-tag config disagrees with the seeded tables."""
    known = {treasure['id']: treasure for floor in graph['floors']
             for treasure in floor['treasures']}
    if not isinstance(tags, dict):
        raise CaveLogicError('Hazard tags must be a mapping')
    for ident, hazard in tags.items():
        if ident not in known:
            raise CaveLogicError('Hazard tag for unknown treasure %r' % (ident,))
        if hazard != known[ident]['hazard']:
            raise CaveLogicError('Hazard tag for %r disagrees with the seeded table' % (ident,))
    missing = sorted(set(known) - set(tags))
    if missing:
        raise CaveLogicError('Untagged treasures: %s' % ', '.join(missing))
    return tags


def _literal_json(literal):
    if literal[0] == 'item':
        return {'item': literal[1]}
    if literal[0] == 'capacity':
        return {'capacity': literal[1], 'color': literal[2]}
    return {'captain': True}


def _requirement_json(requirement):
    return [sorted((_literal_json(literal) for literal in key),
                   key=lambda row: json.dumps(row, sort_keys=True))
            for key in requirement]


def requirements_map(graph, config=None):
    """JSON-serialisable requirements for every tagged treasure, for slot_data."""
    config = _config(config)
    return {treasure['id']: _requirement_json(treasure_requirement(graph, treasure['id'], config))
            for floor in graph['floors'] for treasure in floor['treasures']}


def requirements_manifest(graph, config=None):
    config = _config(config)
    return {'schema': SCHEMA, 'cave_id': graph['cave_id'],
            'requirements': requirements_map(graph, config)}


def requirement_fingerprint(graph, config=None):
    """Deterministic digest of the requirement map (re-roll stability check)."""
    payload = json.dumps(requirements_map(graph, config), sort_keys=True).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def _deserialise_requirement(requirement):
    deserialised = []
    for key in requirement:
        alternatives = set()
        for literal in key:
            if not isinstance(literal, dict):
                raise CaveLogicError('Serialised literal must be an object')
            present = [field for field in ('item', 'capacity', 'captain') if field in literal]
            if len(present) != 1:
                raise CaveLogicError('Unknown serialised literal %r' % (literal,))
            if present[0] == 'item':
                if not isinstance(literal['item'], str) or not literal['item']:
                    raise CaveLogicError('Serialised item literal needs a name')
                alternatives.add(('item', literal['item']))
            elif present[0] == 'capacity':
                alternatives.add(('capacity', _positive_int(literal['capacity'], 'capacity'),
                                  literal['color']))
            elif literal['captain'] is True:
                alternatives.add(('captain',))
            else:
                raise CaveLogicError('Serialised captain literal must be true')
        deserialised.append(frozenset(alternatives))
    return tuple(deserialised)


def requirement_satisfied(requirement, inventory, manifest):
    """Consumer entry point for a serialised ``manifest['cave_requirements']`` row."""
    return satisfied(_deserialise_requirement(requirement), inventory,
                     manifest.get('starting_flarlic', 2))
