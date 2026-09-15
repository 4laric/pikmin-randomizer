"""Lane 37 tests: tagged treasure and gate placement over a frozen floor table.

Covers the frozen ``forest_1`` floor 1 fixtures (seeds 20771 and 42209), the
tag/leaf binding rejection, segment/elec/required gate violations, the untagged
normal-pool path and marker round-tripping. Standard library plus pytest only.
"""
import copy
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from experimental.pikmin2_cave_item_gate_placement import (DOOR_CLASSES, GATES, HAZARDS, SCHEMA,
                                                            PlacementError, describe_seed,
                                                            format_gate, format_item,
                                                            load_floor_table,
                                                            parse_native_trace,
                                                            plan_placements,
                                                            validate_floor_table,
                                                            validate_placement)


def floor_table(seed=20771, choke_hazard='water'):
    return {
        'schema': SCHEMA,
        'seed': seed,
        'cave': 'forest_1',
        'floor': 1,
        'chokes': [{'id': 'choke_0', 'hazard': choke_hazard, 'segment': 0}],
        'leaves': [
            {'id': 'leaf_0', 'hazard': 'water', 'segment': 1},
            {'id': 'leaf_1', 'hazard': 'elec', 'segment': 1},
        ],
        'buds': [],
        'treasures': [
            {'id': 'treasure_water', 'tag': 'water', 'leaf': 'leaf_0'},
            {'id': 'treasure_elec', 'tag': 'elec', 'leaf': 'leaf_1'},
        ],
    }


def item_by_id(result, item_id):
    return next(item for item in result['items'] if item['id'] == item_id)


def gate_by_door(result, door):
    return next(gate for gate in result['gates'] if gate['door'] == door)


def test_constants_are_frozen():
    assert SCHEMA == 'p2-cave-floor-table-v1'
    assert HAZARDS == ('water', 'elec', 'fire', 'poison')
    assert DOOR_CLASSES == ('segment', 'choke', 'leaf')
    assert GATES == ('none', 'elec')


def test_two_seed_fixtures_plan_cleanly():
    for seed, choke_hazard in ((20771, 'water'), (42209, 'elec')):
        result = plan_placements(load_floor_table(floor_table(seed, choke_hazard)))
        assert validate_placement(result) == []
        assert len(result['items']) == 2
        assert len(result['gates']) == 3

        water = item_by_id(result, 'treasure_water')
        elec = item_by_id(result, 'treasure_elec')
        assert (water['placement'], water['leaf'], water['hazard']) == ('leaf', 'leaf_0', 'water')
        assert (elec['placement'], elec['leaf'], elec['hazard']) == ('leaf', 'leaf_1', 'elec')

        assert gate_by_door(result, 'leaf_1')['gate'] == 'elec'
        assert gate_by_door(result, 'leaf_0')['gate'] == 'none'
        assert gate_by_door(result, 'choke_0')['gate'] == ('elec' if choke_hazard == 'elec' else 'none')
        assert all(gate['door_class'] != 'segment' for gate in result['gates'])


def test_seed_tables_differ_and_each_validates():
    first = plan_placements(load_floor_table(floor_table(20771, 'water')))
    second = plan_placements(load_floor_table(floor_table(42209, 'elec')))
    assert first != second
    assert first['items'] != second['items']
    assert first['gates'] != second['gates']
    assert validate_placement(first) == []
    assert validate_placement(second) == []

    differing = {key for key in first['items'][0] if first['items'][0][key] != second['items'][0][key]}
    assert 'seed' in differing
    assert gate_by_door(first, 'choke_0')['gate'] != gate_by_door(second, 'choke_0')['gate']


def test_wrong_hazard_binding_is_rejected():
    bad = copy.deepcopy(floor_table())
    bad['treasures'][0]['leaf'] = 'leaf_1'
    with pytest.raises(PlacementError):
        load_floor_table(bad)
    with pytest.raises(PlacementError):
        validate_floor_table(bad)

    result = plan_placements(load_floor_table(floor_table()))
    item_by_id(result, 'treasure_water')['hazard'] = 'fire'
    violations = validate_placement(result)
    assert any('treasure_water' in message for message in violations)


def test_untagged_treasures_use_the_normal_pool():
    table = load_floor_table(floor_table())
    result = plan_placements(table, untagged=['gem_b', 'gem_a'])
    gems = [item for item in result['items'] if item['id'].startswith('gem_')]
    assert [item['id'] for item in gems] == ['gem_a', 'gem_b']
    for item in gems:
        assert (item['tag'], item['placement'], item['leaf'], item['hazard']) == (
            'none', 'normal', 'none', 'none')

    with pytest.raises(PlacementError):
        plan_placements(table, untagged=['gem_a', 'gem_b'], normal_capacity=1)

    result['items'].append(dict(floor=1, seed=20771, id='gem_c', tag='none',
                                placement='leaf', leaf='leaf_0', hazard='none'))
    assert any('gem_c' in message for message in validate_placement(result))


def test_gate_violations_are_flagged():
    result = plan_placements(load_floor_table(floor_table()))
    result['gates'].append(dict(floor=1, seed=20771, door='segment_0', door_class='segment',
                                gate='none', required=1))
    result['gates'].append(dict(floor=1, seed=20771, door='leaf_1', door_class='leaf',
                                gate='none', required=1))
    result['gates'].append(dict(floor=1, seed=20771, door='leaf_0', door_class='leaf',
                                gate='elec', required=0))
    violations = validate_placement(result)
    assert any('segment_0' in message and 'segment' in message for message in violations)
    assert any('leaf_1' in message for message in violations)
    assert any('leaf_0' in message and 'required=0' in message for message in violations)


def test_marker_lines_round_trip():
    result = plan_placements(load_floor_table(floor_table()), untagged=['gem_a'])
    text = '\n'.join([format_item(item) for item in result['items']]
                     + [format_gate(gate) for gate in result['gates']])
    text += '\nrandom unrelated line\nP2_CAVE_ITEM floor=one seed=two\n'
    parsed = parse_native_trace(text)
    assert parsed['items'] == result['items']
    assert parsed['gates'] == result['gates']
    assert parsed['unparsed'] == ['P2_CAVE_ITEM floor=one seed=two']


def test_load_floor_table_accepts_json_and_path(tmp_path):
    table = floor_table()
    from_json = load_floor_table(json.dumps(table))
    assert from_json == validate_floor_table(table)
    path = tmp_path / 'floor.json'
    path.write_text(json.dumps(table), encoding='utf-8')
    assert load_floor_table(path) == validate_floor_table(table)
    assert load_floor_table(str(path)) == validate_floor_table(table)


def test_malformed_tables_fail_closed():
    with pytest.raises(PlacementError):
        load_floor_table('{"schema": "wrong"}')
    bad = floor_table()
    bad['extra'] = 1
    with pytest.raises(PlacementError):
        validate_floor_table(bad)
    bad = floor_table()
    del bad['seed']
    with pytest.raises(PlacementError):
        validate_floor_table(bad)
    bad = floor_table()
    bad['chokes'][0]['hazard'] = 'wind'
    with pytest.raises(PlacementError):
        validate_floor_table(bad)


def test_describe_seed_summarizes_spread():
    spread = {20771: floor_table(20771, 'water'), 42209: floor_table(42209, 'elec')}
    lines = describe_seed(spread).splitlines()
    assert lines == ['seed=20771 items=2 gates=3 violations=0',
                     'seed=42209 items=2 gates=3 violations=0']


def _native_trace_path():
    override = os.environ.get('PIKMIN_CAVE_L37_TRACE')
    candidates = [Path(override)] if override else []
    candidates.append(Path(__file__).resolve().parents[2] / 'l37-out' / 'l37-native-placement.log')
    for path in candidates:
        if path.is_file():
            return path
    return None


def _read_text(path):
    raw = path.read_bytes()
    if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return raw.decode('utf-16')
    return raw.decode('utf-8', errors='replace')


def test_native_trace_reconciles_across_seeds():
    path = _native_trace_path()
    if path is None:
        pytest.skip('lane 37 native placement trace not present')
    parsed = parse_native_trace(_read_text(path))
    assert parsed['unparsed'] == []
    result = {'items': parsed['items'], 'gates': parsed['gates']}
    assert validate_placement(result) == []
    for item in result['items']:
        if item['tag'] == 'none':
            assert (item['placement'], item['leaf'], item['hazard']) == ('normal', 'none', 'none')
        else:
            assert item['placement'] == 'leaf' and item['hazard'] == item['tag']
    elec_doors = [gate for gate in result['gates']
                  if gate['door_class'] == 'leaf' and gate['gate'] == 'elec']
    assert [gate['door'] for gate in elec_doors] == ['leaf_1', 'leaf_1']
