"""Reconciliation tests for experimental.pikmin2_cave_lane41_reconcile.

Proves the committed lane-36 leaf table and lane-40 spike table both map onto
lane 34's canonical ``pikmin2_cave_schema`` shape (verified with
``validate_floor_table``), that a canonical table round-trips unchanged, and
that an unrecognised shape fails closed.  Fixtures are the committed repo
examples, never a lane-local worktree path.
"""
import json
from pathlib import Path

import pytest

from experimental.pikmin2_cave_lane41_reconcile import (SHAPE_CANONICAL, SHAPE_LEAF,
                                                        SHAPE_SPIKE, ReconcileError,
                                                        reconcile_report, to_canonical)
from experimental.pikmin2_cave_schema import slot_id, validate_floor_table, worked_example

REPO = Path(__file__).resolve().parents[1]
LEAF_EXAMPLE = REPO / 'docs' / 'PIKMIN2_CAVE_LEAF_TABLE_EXAMPLE.json'
SPIKE_TABLE = REPO / 'tests' / 'fixtures' / 'pikmin2_cave_spike' / 'spike_table.json'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def test_lane36_example_maps_to_canonical_and_validates():
    example = load(LEAF_EXAMPLE)
    canonical = to_canonical(example)

    assert validate_floor_table(canonical) is canonical
    assert canonical['cave_id'] == 'forest_1'
    assert canonical['floor'] == 2
    assert [segment['index'] for segment in canonical['segments']] == [0, 1]
    assert [leaf['hazard'] for leaf in canonical['leaves']] == ['water', 'elec']
    assert all(leaf['item_slots'] == 1 for leaf in canonical['leaves'])
    assert (canonical['chokes'], canonical['buds'], canonical['treasures']) == ([], [], [])
    assert canonical['hole'] == {'slot_id': slot_id('forest_1', 2, 'segment', 1), 'segment': 1}
    assert canonical['seed']


def test_lane40_spike_maps_to_canonical_and_validates():
    spike = load(SPIKE_TABLE)
    canonical = to_canonical(spike)

    assert validate_floor_table(canonical) is canonical
    assert canonical['cave_id'] == 'forest_1'
    assert canonical['floor'] == 1
    assert canonical['seed'] == 468001
    choke = canonical['chokes'][0]
    assert (choke['hazard'], choke['after_segment'], choke['before_segment']) == ('water', 0, 1)
    assert (choke['kind'], choke['hardness']) == ('hard', 'hard')
    assert choke['unit']
    assert [leaf['hazard'] for leaf in canonical['leaves']] == ['elec', 'water']
    assert [treasure['treasure_id'] for treasure in canonical['treasures']] == \
        ['treasure_elec', 'treasure_water']
    assert canonical['treasures'][0]['slot_id'] == canonical['leaves'][0]['slot_id']
    assert canonical['hole']['segment'] == 1


def test_lane40_untagged_treasure_is_dropped_not_invented():
    canonical = to_canonical(load(SPIKE_TABLE))
    assert 'juji_key_fc' not in {t['treasure_id'] for t in canonical['treasures']}


def test_canonical_input_round_trips_unchanged():
    table = worked_example()
    result = to_canonical(table)

    assert result == table
    assert result is not table
    result['leaves'][0]['hazard'] = 'fire'
    assert table['leaves'][0]['hazard'] == 'water'


def test_unrecognised_schema_raises_value_error():
    with pytest.raises(ReconcileError):
        to_canonical({'schema': 'totally-unknown/9'})
    with pytest.raises(ValueError):
        to_canonical({'schema': 'totally-unknown/9'})


def test_lane40_choke_with_unknown_kind_raises():
    spike = load(SPIKE_TABLE)
    spike['chokes'][0]['kind'] = 'lava'
    with pytest.raises(ValueError):
        to_canonical(spike)


def test_report_summarises_shapes_and_unmapped_fields():
    report = reconcile_report([load(LEAF_EXAMPLE), load(SPIKE_TABLE), worked_example()])

    assert report['total'] == 3
    assert report['shapes'] == {SHAPE_LEAF: 1, SHAPE_SPIKE: 1, SHAPE_CANONICAL: 1}
    assert all(row['ok'] for row in report['tables'])
    assert 'segments[0].doors' in report['unmapped_fields']
    assert 'chokes[0].unit' in report['unmapped_fields']


def test_report_records_unmappable_table_as_error():
    report = reconcile_report([{'schema': 'nope'}])

    assert report['shapes'] == {'unrecognized': 1}
    assert report['tables'][0]['ok'] is False
    assert report['tables'][0]['error']
