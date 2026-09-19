"""Focused tests for experimental.pikmin2_cave_leaf (lane 36).

Exercises the pure build-time contract only: classification, hazard authoring,
deterministic selection, table validation, door attachment and catalog
validation. The disc-reading entry points (build_leaf_catalog, main) are not
called.
"""
import copy
import json
import os
from pathlib import Path

import pytest

from experimental import pikmin2_cave_leaf as leaf

REPO = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def dry_unit(name='dry_room'):
    return dict(name=name, kind=leaf.UNITKIND_ROOM, kind_name='room', door=5,
                treasure_slots=[0], water=False,
                supports=['elec', 'poison', 'fire'], authored_hazards=[],
                spawn_types={2: 1})


def water_unit(name='water_room'):
    return dict(name=name, kind=leaf.UNITKIND_ROOM, kind_name='room', door=6,
                treasure_slots=[0], water=True, supports=list(leaf.LEAF_HAZARDS),
                authored_hazards=[], spawn_types={2: 1})


def valid_catalog():
    return dict(schema=1, capacity={h: 1 for h in leaf.LEAF_HAZARDS},
                units=[dry_unit()])


def simple_table():
    return dict(schema=leaf.LEAF_TABLE_SCHEMA,
                segments=[dict(segment=0, doors=[10, 11]),
                          dict(segment=1, doors=[20, 21])],
                leaves=[dict(slot=0, segment=0, hazard='fire'),
                        dict(slot=1, segment=0, hazard='elec'),
                        dict(slot=2, segment=1, hazard='poison')])


# ---------------------------------------------------------------------------
# 1. classify success
# ---------------------------------------------------------------------------

def test_classify_dry_room_success():
    definition = dict(name='room_dry', cells=[1, 2, 3],
                      kind=leaf.UNITKIND_ROOM, doors=[{'id': 7}])
    spawns = [{'type': leaf.TREASURE_SPAWN}]
    result = leaf.classify_leaf_unit(definition, spawns, True)

    assert result['name'] == 'room_dry'
    assert result['kind'] == leaf.UNITKIND_ROOM
    assert result['kind_name'] == 'room'
    assert result['door'] == 7
    assert result['cells'] == [1, 2, 3]
    assert result['treasure_slots'] == [0]
    assert result['water'] is False
    assert result['authored_hazards'] == []
    assert result['supports'] == ['elec', 'poison', 'fire']
    assert result['spawn_types'] == {leaf.TREASURE_SPAWN: 1}


def test_classify_water_cap_success():
    definition = dict(name='cap_water', cells=[9],
                      kind=leaf.UNITKIND_CAP, doors=[{'id': 3}])
    spawns = [{'type': 0}, {'type': leaf.TREASURE_SPAWN}, {'type': 0}]
    result = leaf.classify_leaf_unit(definition, spawns, False)

    assert result['kind'] == leaf.UNITKIND_CAP
    assert result['kind_name'] == 'cap'
    assert result['door'] == 3
    assert result['treasure_slots'] == [1]
    assert result['water'] is True
    assert result['supports'] == list(leaf.LEAF_HAZARDS)
    assert result['spawn_types'] == {0: 2, leaf.TREASURE_SPAWN: 1}


# ---------------------------------------------------------------------------
# 2. classify rejection
# ---------------------------------------------------------------------------

def test_classify_rejects_two_doors():
    definition = dict(name='room_two_doors', cells=[], kind=leaf.UNITKIND_ROOM,
                      doors=[{'id': 1}, {'id': 2}])
    with pytest.raises(ValueError):
        leaf.classify_leaf_unit(definition, [{'type': 2}], True)


def test_classify_rejects_corridor_kind():
    definition = dict(name='corridor_leaf', cells=[], kind=leaf.UNITKIND_CORRIDOR,
                      doors=[{'id': 1}])
    with pytest.raises(ValueError):
        leaf.classify_leaf_unit(definition, [{'type': 2}], True)


def test_classify_rejects_zero_treasure_spawns():
    definition = dict(name='room_no_treasure', cells=[], kind=leaf.UNITKIND_ROOM,
                      doors=[{'id': 1}])
    with pytest.raises(ValueError):
        leaf.classify_leaf_unit(definition, [{'type': 0}], True)


def test_classify_rejects_two_treasure_spawns():
    definition = dict(name='room_two_treasure', cells=[], kind=leaf.UNITKIND_ROOM,
                      doors=[{'id': 1}])
    with pytest.raises(ValueError):
        leaf.classify_leaf_unit(definition, [{'type': 2}, {'type': 2}], True)


def test_classify_rejects_non_bool_water_empty():
    definition = dict(name='room_bad_water', cells=[], kind=leaf.UNITKIND_ROOM,
                      doors=[{'id': 1}])
    with pytest.raises(ValueError):
        leaf.classify_leaf_unit(definition, [{'type': 2}], None)


# ---------------------------------------------------------------------------
# 3. authored_hazards
# ---------------------------------------------------------------------------

def test_authored_hazards_detects_hiba_token():
    assert leaf.authored_hazards('room_north_1_hiba_tsuchi') == ['fire']
    assert leaf.authored_hazards('room_north_1_HIBA_tsuchi') == ['fire']


def test_authored_hazards_ignores_non_hiba_tokens():
    assert leaf.authored_hazards('room_north_1_tsuchi') == []
    assert leaf.authored_hazards('room_hibachi') == []


# ---------------------------------------------------------------------------
# 4. pick_leaf determinism
# ---------------------------------------------------------------------------

def test_pick_leaf_water_is_alphabetical_and_order_independent():
    a = water_unit('a_water')
    b = water_unit('b_water')
    first = leaf.pick_leaf([b, a], 'water')
    second = leaf.pick_leaf([a, b], 'water')
    assert first['name'] == 'a_water'
    assert second['name'] == 'a_water'


def test_pick_leaf_fire_prefers_authored_unit():
    plain = dry_unit('aaa_plain')
    authored = dry_unit('zzz_fire')
    authored['authored_hazards'] = ['fire']
    assert leaf.pick_leaf([plain, authored], 'fire')['name'] == 'zzz_fire'
    assert leaf.pick_leaf([authored, plain], 'fire')['name'] == 'zzz_fire'


def test_pick_leaf_rejects_unknown_hazard():
    with pytest.raises(ValueError):
        leaf.pick_leaf([dry_unit()], 'lava')


def test_pick_leaf_rejects_no_supporting_unit():
    with pytest.raises(ValueError):
        leaf.pick_leaf([dry_unit()], 'water')


def test_leaf_capacity_counts_units_per_hazard():
    units = [dry_unit('dry_a'), dry_unit('dry_b'), water_unit('wet')]
    assert leaf.leaf_capacity(units) == {'water': 1, 'elec': 3, 'poison': 3, 'fire': 3}


# ---------------------------------------------------------------------------
# 5. attach_leaves
# ---------------------------------------------------------------------------

def test_attach_leaves_first_free_door_and_determinism():
    units = [dry_unit('dry_a'), water_unit('water_a')]
    table = simple_table()
    plan = leaf.attach_leaves(copy.deepcopy(units), copy.deepcopy(table))
    again = leaf.attach_leaves(copy.deepcopy(units), copy.deepcopy(table))

    assert plan == again
    assert plan['schema'] == 'p2-cave-leaf-plan-v1'
    assert plan['table_schema'] == leaf.LEAF_TABLE_SCHEMA
    assert [a['door'] for a in plan['assignments']] == [10, 11, 20]
    assert [a['segment'] for a in plan['assignments']] == [0, 0, 1]
    assert [a['hazard'] for a in plan['assignments']] == ['fire', 'elec', 'poison']
    assert [a['hardness'] for a in plan['assignments']] == ['soft', 'hard', 'soft']
    assert [a['slot'] for a in plan['assignments']] == [0, 1, 2]


def test_attach_leaves_never_reuses_a_door():
    units = [dry_unit('dry_a')]
    table = dict(schema=leaf.LEAF_TABLE_SCHEMA,
                 segments=[dict(segment=0, doors=[10, 11])],
                 leaves=[dict(slot=0, segment=0, hazard='fire'),
                         dict(slot=1, segment=0, hazard='elec')])
    plan = leaf.attach_leaves(units, table)
    doors = [a['door'] for a in plan['assignments']]
    assert doors == [10, 11]
    assert len(set(doors)) == len(doors)


def test_attach_leaves_unused_doors_accounting():
    units = [dry_unit('dry_a'), water_unit('water_a')]
    table = simple_table()
    plan = leaf.attach_leaves(units, table)
    assert plan['unused_doors'] == {'1': [21]}


def test_attach_leaves_raises_when_segment_runs_out_of_doors():
    units = [dry_unit('dry_a')]
    table = dict(schema=leaf.LEAF_TABLE_SCHEMA,
                 segments=[dict(segment=0, doors=[10])],
                 leaves=[dict(slot=0, segment=0, hazard='fire'),
                         dict(slot=1, segment=0, hazard='elec')])
    with pytest.raises(ValueError):
        leaf.attach_leaves(units, table)


# ---------------------------------------------------------------------------
# 6. validate_leaf_table
# ---------------------------------------------------------------------------

def test_validate_leaf_table_accepts_valid_table():
    table = simple_table()
    assert leaf.validate_leaf_table(table) is table


def test_validate_leaf_table_rejects_wrong_schema():
    table = simple_table()
    table['schema'] = 'p2-cave-leaf-table-v0'
    with pytest.raises(ValueError):
        leaf.validate_leaf_table(table)


def test_validate_leaf_table_rejects_unknown_segment():
    table = simple_table()
    table['leaves'].append(dict(slot=3, segment=9, hazard='fire'))
    with pytest.raises(ValueError):
        leaf.validate_leaf_table(table)


def test_validate_leaf_table_rejects_unknown_hazard():
    table = simple_table()
    table['leaves'].append(dict(slot=3, segment=1, hazard='lava'))
    with pytest.raises(ValueError):
        leaf.validate_leaf_table(table)


# ---------------------------------------------------------------------------
# 7. validate_leaf_catalog
# ---------------------------------------------------------------------------

def test_validate_leaf_catalog_accepts_valid_catalog():
    catalog = valid_catalog()
    assert leaf.validate_leaf_catalog(catalog) is catalog


def test_validate_leaf_catalog_rejects_wrong_schema():
    catalog = valid_catalog()
    catalog['schema'] = 2
    with pytest.raises(ValueError):
        leaf.validate_leaf_catalog(catalog)


def test_validate_leaf_catalog_rejects_empty_units():
    catalog = valid_catalog()
    catalog['units'] = []
    with pytest.raises(ValueError):
        leaf.validate_leaf_catalog(catalog)


def test_validate_leaf_catalog_rejects_duplicate_units():
    catalog = valid_catalog()
    catalog['units'].append(copy.deepcopy(catalog['units'][0]))
    with pytest.raises(ValueError):
        leaf.validate_leaf_catalog(catalog)


def test_validate_leaf_catalog_rejects_water_unit_without_water_support():
    catalog = valid_catalog()
    catalog['units'][0]['water'] = True
    catalog['units'][0]['supports'] = ['elec', 'poison', 'fire']
    with pytest.raises(ValueError):
        leaf.validate_leaf_catalog(catalog)


def test_validate_leaf_catalog_rejects_dry_unit_claiming_water():
    catalog = valid_catalog()
    catalog['units'][0]['water'] = False
    catalog['units'][0]['supports'] = list(leaf.LEAF_HAZARDS)
    with pytest.raises(ValueError):
        leaf.validate_leaf_catalog(catalog)


def test_validate_leaf_catalog_rejects_unknown_support():
    catalog = valid_catalog()
    catalog['units'][0]['supports'] = ['elec', 'poison', 'weird']
    with pytest.raises(ValueError):
        leaf.validate_leaf_catalog(catalog)


def test_validate_leaf_catalog_rejects_wrong_treasure_slot_count():
    catalog = valid_catalog()
    catalog['units'][0]['treasure_slots'] = [0, 1]
    with pytest.raises(ValueError):
        leaf.validate_leaf_catalog(catalog)


def test_validate_leaf_catalog_rejects_missing_capacity_key():
    catalog = valid_catalog()
    del catalog['capacity']['fire']
    with pytest.raises(ValueError):
        leaf.validate_leaf_catalog(catalog)


# ---------------------------------------------------------------------------
# 8. committed example fixture + opt-in real catalog
# ---------------------------------------------------------------------------

def test_committed_example_leaf_table_is_valid():
    table = json.loads((REPO / 'docs' / 'PIKMIN2_CAVE_LEAF_TABLE_EXAMPLE.json').read_text())
    assert leaf.validate_leaf_table(table) is table
    assert table['schema'] == leaf.LEAF_TABLE_SCHEMA


def test_real_leaf_catalog_if_provided():
    path = os.environ.get('PIKMIN2_CAVE_LEAF_CATALOG')
    if not path or not Path(path).exists():
        pytest.skip('Set PIKMIN2_CAVE_LEAF_CATALOG to a generated leaf_catalog.json')
    catalog = json.loads(Path(path).read_text())
    assert leaf.validate_leaf_catalog(catalog) is catalog
    for hazard in leaf.LEAF_HAZARDS:
        assert catalog['capacity'][hazard] >= 1
