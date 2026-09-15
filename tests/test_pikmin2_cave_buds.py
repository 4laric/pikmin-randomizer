"""Focused contracts for the Candypop bud slot model (lane 38)."""
import copy

import pytest

from experimental.pikmin2_cave_buds import (
    DEFAULT_CONVERSION_COUNT,
    VIOLATION_RULES,
    bud_key_available,
    bud_slot,
    from_floor_table,
    segment_requirements,
    validate_buds,
)


def lane34_table(buds, chokes=()):
    """A minimal literal of the lane-34 (#473) seeded floor-table shape."""
    return {
        'schema': 1, 'seed': 'lane38-seed', 'cave_id': 'forest_1', 'floor': 1,
        'segments': [{'slot_id': f'forest_1:f1:segment:{i}', 'index': i}
                     for i in range(3)],
        'chokes': [{'slot_id': f'forest_1:f1:choke:{i}', 'index': i,
                    'after_segment': after, 'before_segment': after + 1,
                    'hazard': hazard, 'kind': 'hard', 'hardness': 'hard',
                    'unit': 'way2_tsuchi'}
                   for i, (after, hazard) in enumerate(chokes)],
        'leaves': [],
        'buds': [{'slot_id': f'forest_1:f1:bud:{i}', 'index': i,
                  'segment': segment, 'species': species, 'count': count}
                 for i, (segment, species, count) in enumerate(buds)],
        'treasures': [],
        'hole': {'slot_id': 'forest_1:f1:segment:2', 'segment': 2},
    }


def rules(violations):
    return sorted(row['rule'] for row in violations)


def test_bud_slot_record_and_field_validation():
    assert bud_slot(2, 'purple') == dict(segment_index=2, provides='purple',
                                         conversion_count=DEFAULT_CONVERSION_COUNT)
    assert bud_slot(0, 'white', 3)['conversion_count'] == 3
    for args in ((-1, 'purple'), (True, 'purple'), (0, ''), (0, 'purple', 0),
                 (0, 'purple', -2), (0, 'purple', True)):
        with pytest.raises(ValueError):
            bud_slot(*args)


def test_duplicate_bud_in_same_segment_is_reported():
    duplicate = dict(segment_count=3, gates={},
                     buds=[bud_slot(1, 'purple'), bud_slot(1, 'white')])
    violations = validate_buds(duplicate)
    assert rules(violations) == ['duplicate_bud']
    row = violations[0]
    assert (row['segment_index'], row['provides'], row['first_provides']) == (1, 'white', 'purple')

    distinct = dict(segment_count=3, gates={},
                    buds=[bud_slot(0, 'purple'), bud_slot(1, 'white')])
    assert validate_buds(distinct) == []


def test_non_positive_conversion_count_is_reported():
    floor = dict(segment_count=2, gates={},
                 buds=[dict(segment_index=0, provides='purple', conversion_count=0),
                       dict(segment_index=1, provides='white', conversion_count=-4)])
    violations = validate_buds(floor)
    assert rules(violations) == ['invalid_conversion_count', 'invalid_conversion_count']
    assert sorted(row['conversion_count'] for row in violations) == [-4, 0]

    valid = dict(segment_count=2, gates={}, buds=[dict(segment_index=0, provides='purple',
                                                       conversion_count=5)])
    assert validate_buds(valid) == []


def test_bud_behind_its_own_type_is_reported_directly_and_transitively():
    direct = dict(segment_count=3, gates={0: set(), 1: {'purple'}, 2: set()},
                  buds=[bud_slot(1, 'purple')])
    assert rules(validate_buds(direct)) == ['bud_behind_own_type']

    transitive = dict(segment_count=3, gates={0: set(), 1: {'purple'}, 2: set()},
                      buds=[bud_slot(2, 'purple')])
    assert rules(validate_buds(transitive)) == ['bud_behind_own_type']

    unrelated = dict(segment_count=3, gates={0: set(), 1: {'purple'}, 2: set()},
                     buds=[bud_slot(2, 'white')])
    assert validate_buds(unrelated) == []


def test_bud_before_the_gate_is_accepted():
    floor = dict(segment_count=3, gates=[set(), set(), {'purple'}],
                 buds=[bud_slot(1, 'purple')])
    assert validate_buds(floor) == []


def test_out_of_range_segment_is_reported():
    floor = dict(segment_count=2, gates={},
                 buds=[bud_slot(0, 'purple'), dict(segment_index=5, provides='white'),
                       dict(segment_index=-1, provides='elec')])
    violations = validate_buds(floor)
    assert rules(violations) == ['segment_out_of_range', 'segment_out_of_range']
    assert sorted(row['segment_index'] for row in violations) == [-1, 5]


def test_validate_buds_does_not_mutate_floor_and_reports_every_class():
    floor = dict(segment_count=2, gates={0: set(), 1: {'purple'}},
                 buds=[bud_slot(1, 'purple'), bud_slot(1, 'white'), bud_slot(9, 'elec'),
                       dict(segment_index=0, provides='red', conversion_count=0)])
    before = copy.deepcopy(floor)
    violations = validate_buds(floor)
    assert floor == before
    assert set(rules(violations)) == set(VIOLATION_RULES)


def test_segment_requirements_accumulate_along_the_chain():
    gates = {0: set(), 1: {'water'}, 2: {'elec'}, 3: set()}
    assert segment_requirements(gates) == {0: set(), 1: {'water'},
                                           2: {'water', 'elec'}, 3: {'water', 'elec'}}
    assert segment_requirements([set(), {'white'}], segment_count=3) == {
        0: set(), 1: {'white'}, 2: {'white'}}
    for excluded in ('', 'water'):
        with pytest.raises(ValueError):
            segment_requirements({0: excluded})


def test_bud_key_available_type_satisfied():
    assert bud_key_available(2, None, [], 0) is True
    assert bud_key_available(2, 'water', [], 0, available_types={'water'}) is True
    assert bud_key_available(2, 'water', [], 0, available_types={'elec'}) is False


def test_bud_key_available_bud_satisfied_with_enough_pikmin():
    buds = [bud_slot(0, 'purple', 5), bud_slot(3, 'white', 3)]
    assert bud_key_available(2, 'purple', buds, 5) is True
    assert bud_key_available(4, 'white', buds, 3) is True
    assert bud_key_available(4, 'white', [dict(segment_index=1, provides='white')], 5) is True


def test_bud_key_available_bud_present_but_too_few_pikmin():
    buds = [bud_slot(0, 'purple', 5)]
    assert bud_key_available(2, 'purple', buds, 4) is False
    assert bud_key_available(2, 'purple', [bud_slot(0, 'purple', 3)], 2) is False


def test_bud_key_available_no_matching_bud():
    assert bud_key_available(2, 'purple', [], 10) is False
    assert bud_key_available(2, 'purple', [bud_slot(0, 'white', 5)], 10) is False


def test_bud_key_available_requires_strictly_before_the_gate():
    at_gate = [bud_slot(2, 'purple', 5)]
    after_gate = [bud_slot(3, 'purple', 5)]
    assert bud_key_available(2, 'purple', at_gate, 5) is False
    assert bud_key_available(2, 'purple', after_gate, 5) is False
    assert bud_key_available(2, 'purple', [bud_slot(1, 'purple', 5)], 5) is True


def test_bud_key_available_rejects_malformed_inputs():
    for args in ((-1, 'purple', [], 5), (2, 'purple', [], -1)):
        with pytest.raises(ValueError):
            bud_key_available(*args)
    with pytest.raises(ValueError):
        bud_key_available(2, 'purple', [], 5, available_types='purple')


def test_from_lane34_table_translates_choke_hazards_to_species():
    # water choke gates segment 1; white bud at segment 2 is not behind white.
    table = lane34_table(buds=[(2, 'white', 5)], chokes=[(0, 'water')])
    model = from_floor_table(table)
    assert model['segment_count'] == 3
    assert model['gates'] == {1: {'blue'}}
    assert model['buds'] == [bud_slot(2, 'white', 5)]
    assert validate_buds(model) == []


def test_from_lane34_table_rejects_bud_behind_its_own_hazard():
    # Blue bud at segment 1 sits behind the water choke that needs blue.
    table = lane34_table(buds=[(1, 'blue', 5), (0, 'purple', 5)],
                         chokes=[(0, 'water')])
    assert rules(validate_buds(from_floor_table(table))) == ['bud_behind_own_type']
    # A purple bud has no hazard, so it is legal anywhere on the path.
    purple_only = lane34_table(buds=[(2, 'purple', 5)], chokes=[(0, 'water'), (1, 'elec')])
    assert validate_buds(from_floor_table(purple_only)) == []


def test_from_lane34_table_exposes_conversion_count_to_logic():
    table = lane34_table(buds=[(0, 'white', 5)], chokes=[(0, 'water')])
    model = from_floor_table(table)
    buds = model['buds']
    # White keys the poison requirement deeper in, but only at count >= N.
    assert bud_key_available(2, 'white', buds, 5) is True
    assert bud_key_available(2, 'white', buds, 4) is False
    assert bud_key_available(2, 'blue', buds, 5) is False


def test_from_lane34_table_rejects_malformed_tables():
    for bad in (None, [], {'segments': 'x'},
                {'segments': [{'index': 0}], 'chokes': None},
                {'segments': [{'index': 0}], 'buds': [None]}):
        with pytest.raises(ValueError):
            from_floor_table(bad)
