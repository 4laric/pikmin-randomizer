"""Lane 37 tagged-item and gate placement over a frozen cave floor table.

Pure planning: this module reads a ``p2-cave-floor-table-v1`` mapping (a dict,
JSON text or a path) and decides, deterministically, where each tagged treasure
and each gate record goes. It emits ``P2_CAVE_ITEM`` / ``P2_CAVE_GATE`` marker
lines and can parse them back for reconciliation against a native trace.

Rules enforced by ``validate_placement``:

* a tagged treasure lives in the leaf whose hazard equals its tag;
* an untagged treasure uses the normal random pool, never a forced leaf;
* gates exist only on ``choke`` or ``leaf`` doors, never ``segment`` doors;
* an ``elec`` leaf door is electrified (the "come back with yellow" loop);
* no gate is present on a door that the frozen table marks ``required=0``.
"""
import json
import os
import re
from pathlib import Path

SCHEMA = "p2-cave-floor-table-v1"
HAZARDS = ("water", "elec", "fire", "poison")
DOOR_CLASSES = ("segment", "choke", "leaf")
GATES = ("none", "elec")

_TOP_FIELDS = ("schema", "seed", "cave", "floor", "chokes", "leaves", "buds", "treasures")
_CHOKE_FIELDS = ("id", "hazard", "segment")
_LEAF_FIELDS = ("id", "hazard", "segment")
_TREASURE_FIELDS = ("id", "tag", "leaf")
_REQUIRED_TOP = ("schema", "seed", "cave", "floor", "chokes", "leaves", "treasures")


class PlacementError(ValueError):
    """Raised when a floor table or placement request is malformed."""


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _records(table, field):
    value = table.get(field, [])
    if not isinstance(value, list):
        raise PlacementError('Field %s must be a list' % field)
    for record in value:
        if not isinstance(record, dict):
            raise PlacementError('Field %s must contain mappings' % field)
    return value


def _check_keys(record, allowed, field, required):
    missing = [key for key in required if key not in record]
    if missing:
        raise PlacementError('Field %s record is missing %s' % (field, ', '.join(missing)))
    extra = [key for key in record if key not in allowed]
    if extra:
        raise PlacementError('Field %s record has extra fields %s' % (field, ', '.join(extra)))


def validate_floor_table(table):
    """Return a normalized copy of ``table`` or raise ``PlacementError``."""
    if not isinstance(table, dict):
        raise PlacementError('Floor table must be a mapping')
    extra = [key for key in table if key not in _TOP_FIELDS]
    if extra:
        raise PlacementError('Floor table has extra fields %s' % ', '.join(sorted(extra)))
    missing = [key for key in _REQUIRED_TOP if key not in table]
    if missing:
        raise PlacementError('Floor table is missing %s' % ', '.join(missing))
    if table['schema'] != SCHEMA:
        raise PlacementError('Unknown schema %r (expected %r)' % (table['schema'], SCHEMA))
    if not _is_int(table['seed']):
        raise PlacementError('seed must be an integer')
    if not isinstance(table['cave'], str) or not table['cave']:
        raise PlacementError('cave must be a non-empty string')
    if not _is_int(table['floor']):
        raise PlacementError('floor must be an integer')

    chokes = _records(table, 'chokes')
    leaves = _records(table, 'leaves')
    buds = _records(table, 'buds') if 'buds' in table else []
    treasures = _records(table, 'treasures')

    seen_leaves = set()
    for leaf in leaves:
        _check_keys(leaf, _LEAF_FIELDS, 'leaves', _LEAF_FIELDS)
        if leaf['hazard'] not in HAZARDS:
            raise PlacementError('leaf %s has unknown hazard %r' % (leaf['id'], leaf['hazard']))
        if leaf['id'] in seen_leaves:
            raise PlacementError('Duplicate leaf id %s' % (leaf['id'],))
        if not _is_int(leaf['segment']):
            raise PlacementError('leaf %s segment must be an integer' % (leaf['id'],))
        seen_leaves.add(leaf['id'])

    for choke in chokes:
        _check_keys(choke, _CHOKE_FIELDS, 'chokes', _CHOKE_FIELDS)
        if choke['hazard'] not in HAZARDS:
            raise PlacementError('choke %s has unknown hazard %r' % (choke['id'], choke['hazard']))
        if not _is_int(choke['segment']):
            raise PlacementError('choke %s segment must be an integer' % (choke['id'],))

    hazards = {leaf['id']: leaf['hazard'] for leaf in leaves}
    bound = {}
    for treasure in treasures:
        _check_keys(treasure, _TREASURE_FIELDS, 'treasures', _TREASURE_FIELDS)
        if treasure['tag'] not in HAZARDS:
            raise PlacementError('treasure %s has unknown tag %r' % (treasure['id'], treasure['tag']))
        if treasure['leaf'] not in hazards:
            raise PlacementError('treasure %s bound to nonexistent leaf %s'
                                 % (treasure['id'], treasure['leaf']))
        if hazards[treasure['leaf']] != treasure['tag']:
            raise PlacementError('treasure %s tag=%s does not match leaf %s hazard=%s'
                                 % (treasure['id'], treasure['tag'], treasure['leaf'],
                                    hazards[treasure['leaf']]))
        if treasure['leaf'] in bound:
            raise PlacementError('leaf %s carries more than one treasure (%s and %s)'
                                 % (treasure['leaf'], bound[treasure['leaf']], treasure['id']))
        bound[treasure['leaf']] = treasure['id']

    return dict(schema=SCHEMA, seed=table['seed'], cave=table['cave'], floor=table['floor'],
                chokes=[dict(c) for c in chokes], leaves=[dict(l) for l in leaves],
                buds=[dict(b) for b in buds], treasures=[dict(t) for t in treasures])


def load_floor_table(value):
    """Normalize a dict, JSON string or path to a validated floor table."""
    if isinstance(value, dict):
        return validate_floor_table(value)
    if isinstance(value, (str, os.PathLike)):
        text = None
        if isinstance(value, str) and value.lstrip()[:1] == '{':
            text = value
        else:
            path = Path(value)
            if path.is_file():
                text = path.read_text(encoding='utf-8')
            elif isinstance(value, str):
                text = value
            else:
                raise PlacementError('Floor table path does not exist: %s' % value)
        try:
            data = json.loads(text)
        except ValueError:
            raise PlacementError('Floor table is not valid JSON') from None
        if not isinstance(data, dict):
            raise PlacementError('Floor table JSON must be an object')
        return validate_floor_table(data)
    raise PlacementError('Unsupported floor table source %r' % (value,))


def plan_placements(table, untagged=(), normal_capacity=None):
    """Deterministically place tagged treasures, untagged ids and gate records."""
    table = validate_floor_table(table)
    if isinstance(untagged, str):
        raise PlacementError('untagged must be a sequence of ids, not a string')
    ids = list(untagged)
    for item_id in ids:
        if not isinstance(item_id, str) or not item_id:
            raise PlacementError('untagged ids must be non-empty strings')
    if normal_capacity is not None:
        if not _is_int(normal_capacity) or normal_capacity < 0:
            raise PlacementError('normal_capacity must be a nonnegative integer')
        if len(ids) > normal_capacity:
            raise PlacementError('normal pool capacity %d exceeded by %d untagged treasures'
                                 % (normal_capacity, len(ids)))

    floor, seed = table['floor'], table['seed']
    items = []
    for treasure in sorted(table['treasures'], key=lambda t: t['id']):
        items.append(dict(floor=floor, seed=seed, id=treasure['id'], tag=treasure['tag'],
                          placement='leaf', leaf=treasure['leaf'], hazard=treasure['tag']))
    for item_id in sorted(ids):
        items.append(dict(floor=floor, seed=seed, id=item_id, tag='none',
                          placement='normal', leaf='none', hazard='none'))

    required_leaves = {t['leaf'] for t in table['treasures']}
    gates = []
    for choke in sorted(table['chokes'], key=lambda c: c['id']):
        gates.append(dict(floor=floor, seed=seed, door=choke['id'], door_class='choke',
                          gate='elec' if choke['hazard'] == 'elec' else 'none', required=1))
    for leaf in sorted(table['leaves'], key=lambda l: l['id']):
        gates.append(dict(floor=floor, seed=seed, door=leaf['id'], door_class='leaf',
                          gate='elec' if leaf['hazard'] == 'elec' else 'none',
                          required=1 if leaf['id'] in required_leaves else 0))
    return dict(items=items, gates=gates)


def format_item(record):
    """Render one item record as a ``P2_CAVE_ITEM`` marker line."""
    return ('P2_CAVE_ITEM floor=%s seed=%s id=%s tag=%s placement=%s leaf=%s hazard=%s'
            % (record['floor'], record['seed'], record['id'], record['tag'],
               record['placement'], record['leaf'], record['hazard']))


def format_gate(record):
    """Render one gate record as a ``P2_CAVE_GATE`` marker line."""
    return ('P2_CAVE_GATE floor=%s seed=%s door=%s door_class=%s gate=%s required=%s'
            % (record['floor'], record['seed'], record['door'], record['door_class'],
               record['gate'], record['required']))


def _fields(line):
    return dict(re.findall(r'(\w+)=(\S+)', line))


def parse_native_trace(text):
    """Parse marker lines, ignoring unrelated text and collecting malformed markers."""
    if not isinstance(text, str):
        raise PlacementError('Native trace must be a string')
    items, gates, unparsed = [], [], []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith('P2_CAVE_ITEM'):
            fields = _fields(line)
            try:
                items.append(dict(floor=int(fields['floor']), seed=int(fields['seed']),
                                  id=fields['id'], tag=fields['tag'],
                                  placement=fields['placement'], leaf=fields['leaf'],
                                  hazard=fields['hazard']))
            except (KeyError, ValueError):
                unparsed.append(raw)
        elif line.startswith('P2_CAVE_GATE'):
            fields = _fields(line)
            try:
                gates.append(dict(floor=int(fields['floor']), seed=int(fields['seed']),
                                  door=fields['door'], door_class=fields['door_class'],
                                  gate=fields['gate'], required=int(fields['required'])))
            except (KeyError, ValueError):
                unparsed.append(raw)
        elif line.startswith('P2_CAVE_'):
            unparsed.append(raw)
    return dict(items=items, gates=gates, unparsed=unparsed)


def validate_placement(result):
    """Return human-readable violations for a ``{"items", "gates"}`` result."""
    if not isinstance(result, dict):
        raise PlacementError('Placement result must be a mapping')
    if not isinstance(result.get('items'), list) or not isinstance(result.get('gates'), list):
        raise PlacementError('Placement result requires item and gate lists')
    violations = []
    leaf_hazards = {}
    for item in result['items']:
        if not isinstance(item, dict):
            raise PlacementError('Item record must be a mapping')
        item_id = item.get('id', '<unknown>')
        tag = item.get('tag')
        placement = item.get('placement')
        leaf = item.get('leaf')
        hazard = item.get('hazard')
        if tag == 'none':
            if placement != 'normal' or leaf != 'none' or hazard != 'none':
                violations.append('untagged item %s must use the normal pool, not leaf %s'
                                  % (item_id, leaf))
        elif tag in HAZARDS:
            if placement != 'leaf' or leaf in (None, 'none'):
                violations.append('tagged item %s (tag=%s) must be placed in a leaf, not %s'
                                  % (item_id, tag, placement))
            elif hazard != tag:
                violations.append('tagged item %s tag=%s does not match hazard=%s in leaf %s'
                                  % (item_id, tag, hazard, leaf))
            else:
                leaf_hazards[leaf] = hazard
        else:
            violations.append('item %s has unknown tag %r' % (item_id, tag))

    for gate in result['gates']:
        if not isinstance(gate, dict):
            raise PlacementError('Gate record must be a mapping')
        door = gate.get('door', '<unknown>')
        door_class = gate.get('door_class')
        value = gate.get('gate')
        required = gate.get('required')
        if door_class not in DOOR_CLASSES:
            violations.append('gate door %s has unknown class %r' % (door, door_class))
        elif door_class == 'segment':
            violations.append('gate record on segment door %s is not allowed' % door)
        if value not in GATES:
            violations.append('gate door %s has unknown gate %r' % (door, value))
        if required == 0 and value != 'none':
            violations.append('gate %s is present on unrequired door %s (required=0)'
                              % (value, door))
        if door_class == 'leaf' and leaf_hazards.get(door) == 'elec' and value != 'elec':
            violations.append('elec leaf %s must have an elec gate, got %r' % (door, value))
    return violations


def describe_seed(spread):
    """Summarize a ``{seed: floor table}`` mapping as one line per seed."""
    if not isinstance(spread, dict):
        raise PlacementError('Expected a seed -> floor table mapping')
    lines = []
    for seed in sorted(spread):
        value = spread[seed]
        if isinstance(value, dict) and 'items' in value and 'gates' in value:
            result = value
        else:
            result = plan_placements(load_floor_table(value))
        violations = validate_placement(result)
        lines.append('seed=%s items=%d gates=%d violations=%d'
                     % (seed, len(result['items']), len(result['gates']), len(violations)))
    return '\n'.join(lines)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('table', type=Path)
    arguments = parser.parse_args()
    plan = plan_placements(load_floor_table(arguments.table))
    for record in plan['items']:
        print(format_item(record))
    for record in plan['gates']:
        print(format_gate(record))
