"""Host-driver tests for the lane-41 native cave-generator glue.

These do not run the native executable (that needs a native build); they pin the
``P2_CAVE_FLOOR_V1`` serialisation contract, the source-id preservation lane 40's
checker needs, and the canonical -> lane-40 projection.
"""
import json
from pathlib import Path

import pytest

from experimental.pikmin2_cave_lane41_generator import (
    Lane41Error,
    _annotate_source_ids,
    _seed_uint64,
    canonical_to_spike,
    write_native_table,
)
from experimental.pikmin2_cave_lane41_reconcile import to_canonical
from experimental.pikmin2_cave_spike import validate_table as validate_spike_table

REPO = Path(__file__).resolve().parents[1]
SPIKE_TABLE = REPO / 'tests' / 'fixtures' / 'pikmin2_cave_spike' / 'spike_table.json'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def parse_native(text):
    tokens = text.split()
    assert tokens[0] == 'P2_CAVE_FLOOR_V1'
    out = {'chokes': [], 'leaves': [], 'buds': [], 'treasures': [], 'loose': []}
    position = 1

    def next_token():
        nonlocal position
        value = tokens[position]
        position += 1
        return value

    assert next_token() == 'seed'
    out['seed'] = int(next_token())
    assert next_token() == 'cave'
    out['cave'] = next_token()
    assert next_token() == 'floor'
    out['floor'] = int(next_token())
    assert next_token() == 'unit_pool'
    out['unit_pool'] = next_token()
    for section in ('segments', 'chokes', 'leaves', 'buds', 'treasures', 'loose'):
        assert next_token() == section
        count = int(next_token())
        for _ in range(count):
            if section == 'segments':
                next_token(), next_token()
            elif section == 'chokes':
                out['chokes'].append([next_token() for _ in range(8)])
            elif section == 'leaves':
                out['leaves'].append([next_token() for _ in range(5)])
            elif section == 'buds':
                out['buds'].append([next_token() for _ in range(5)])
            elif section == 'treasures':
                out['treasures'].append([next_token() for _ in range(4)])
            else:
                out['loose'].append(next_token())
    assert next_token() == 'hole'
    out['hole'] = int(next_token())
    assert position == len(tokens)
    return out


def test_native_serialisation_preserves_source_ids():
    spike = load(SPIKE_TABLE)
    canonical = _annotate_source_ids(to_canonical(spike), spike)
    canonical['loose_treasures'] = ['juji_key_fc']
    path = REPO / 'output' / 'dsw' / 'l41-out' / 'test-floor-table.txt'
    write_native_table(canonical, path)
    try:
        parsed = parse_native(path.read_text(encoding='ascii'))
    finally:
        path.unlink(missing_ok=True)

    assert parsed['seed'] == 468001
    assert parsed['cave'] == 'forest_1'
    assert parsed['floor'] == 1
    assert parsed['chokes'][0][0] == 'choke_water_0'
    assert [leaf[0] for leaf in parsed['leaves']] == ['leaf_elec_0', 'leaf_water_0']
    assert [leaf[3] for leaf in parsed['leaves']] == ['elec', 'water']
    assert [treasure[0] for treasure in parsed['treasures']] == ['treasure_elec', 'treasure_water']
    assert all(treasure[1].startswith('leaf_') for treasure in parsed['treasures'])
    assert parsed['loose'] == ['juji_key_fc']
    assert parsed['hole'] == 1


def test_canonical_to_spike_reproduces_lane40_ids():
    spike = load(SPIKE_TABLE)
    canonical = _annotate_source_ids(to_canonical(spike), spike)
    projected = canonical_to_spike(canonical, ['juji_key_fc'])

    validate_spike_table(projected)
    assert [choke['id'] for choke in projected['chokes']] == ['choke_water_0']
    assert [leaf['id'] for leaf in projected['leaves']] == ['leaf_elec_0', 'leaf_water_0']
    assert [treasure['id'] for treasure in projected['treasures']] == \
        ['treasure_elec', 'treasure_water', 'juji_key_fc']
    assert projected['treasures'][0]['leaf'] == 'leaf_elec_0'
    assert projected['hole'] == {'segment_index': 1}


def test_seed_uint64_passthrough_and_hashing():
    assert _seed_uint64(468001) == 468001
    assert _seed_uint64('worked-example') == _seed_uint64('worked-example')
    assert _seed_uint64('worked-example') != _seed_uint64('worked-example-2')


def test_purple_bud_has_no_lane40_vocabulary():
    canonical = to_canonical(load(SPIKE_TABLE))
    canonical['buds'] = [{'slot_id': canonical['segments'][0]['slot_id'].replace('segment', 'bud'),
                          'index': 0, 'segment': 0, 'species': 'purple', 'count': 5}]
    with pytest.raises(Lane41Error):
        canonical_to_spike(canonical)
