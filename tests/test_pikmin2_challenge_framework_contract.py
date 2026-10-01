"""Tests for the P2 Challenge framework contract (#136).

Pure unit tests plus repo-file checks: synthetic stage-table decode,
malformed-input rejection, scoring formula, provider split shape, and
agreement between the decoded retail table and the canonical inventory.
The live-disc test skips cleanly when no local GPVE01 image exists.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    'pikmin2_challenge_framework_contract',
    ROOT / 'experimental/pikmin2_challenge_framework_contract.py')
_contract = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_contract)

parse_stage_table = _contract.parse_stage_table
cross_check_inventory = _contract.cross_check_inventory
compute_score = _contract.compute_score
framework_providers = _contract.framework_providers
first_slice_spec = _contract.first_slice_spec
STAGE_TABLE_PATH = _contract.STAGE_TABLE_PATH
ContractError = _contract.ContractError

SYNTHETIC = """2 # num stages
# stage
{
4 # version
ch_TEST_demo.txt
# PikiCounter
0 # col0 happa0
0 # col0 happa1
10 # col0 happa2
0 # col1 happa0
0 # col1 happa1
0 # col1 happa2
0 # col2 happa0
0 # col2 happa1
0 # col2 happa2
0 # col3 happa0
0 # col3 happa1
0 # col3 happa2
0 # col4 happa0
0 # col4 happa1
0 # col4 happa2
0 # col5 happa0
0 # col5 happa1
0 # col5 happa2
0 # col6 happa0
0 # col6 happa1
0 # col6 happa2
350.000000 # time
1 # dope black
2 # dope red
1 # floor num
0 # otakara num
3 # 2d index
180.000000 # floor seconds
}
# stage
{
4 # version
ch_TEST_demo2.txt
# PikiCounter
""" + '\n'.join('0 # col%d happa%d' % (c, h) for c in range(7) for h in range(3)) + """
0.000000 # time
0 # dope black
1 # dope red
2 # floor num
0 # otakara num
7 # 2d index
100.000000 # floor one
150.000000 # floor two
}
"""


def test_decode_synthetic_table():
    stages = parse_stage_table(SYNTHETIC)
    assert len(stages) == 2
    first = stages[0]
    assert first['cave_id'] == 'ch_TEST_demo' and first['floors'] == 1
    assert first['roster'][0] == [0, 0, 10]
    assert first['legacy_time'] == 350.0 and first['ui_index'] == 3
    assert first['floor_seconds'] == [180.0]
    assert stages[1]['floors'] == 2 and stages[1]['floor_seconds'] == [100.0, 150.0]


def test_rejects_malformed_tables():
    bad = ['', '0 # num stages', '1 # num stages',
           SYNTHETIC.replace('4 # version', '3 # version', 1),
           SYNTHETIC.replace('180.000000 # floor seconds', '', 1),
           SYNTHETIC.replace('ch_TEST_demo.txt', 'not a path!!', 1),
           SYNTHETIC + 'trailing garbage line']
    for text in bad:
        try:
            parse_stage_table(text)
        except ContractError:
            continue
        raise AssertionError('expected ContractError for %r' % text[:50])


def test_scoring_formula():
    assert compute_score(0, 0, 0) == 0
    assert compute_score(5, 120, 30) == 5 * 10 + 120 + 30 * 10
    for bad in (-1, 1.5, 'x'):
        try:
            compute_score(bad, 0, 0)
        except ContractError:
            continue
        raise AssertionError('expected ContractError')


def test_provider_split_shape():
    providers = framework_providers()
    assert set(providers) == {'existing', 'missing'}
    assert 'challenge_host_mode' in providers['missing']
    assert 'cave_generation_129' in providers['existing']


def test_first_slice_spec_shape():
    spec = first_slice_spec()
    assert spec['steps'] and spec['owners']['host_mode'] and spec['acceptance']


def test_inventory_agreement():
    inventory = json.loads((ROOT / 'docs/PIKMIN2_CONTENT_INVENTORY.json').read_text(encoding='utf-8'))
    plan = json.loads((ROOT / 'docs/PIKMIN_CONTENT_IMPORT_LANES.json').read_text(encoding='utf-8-sig'))
    assert len(inventory['challenge']['stages']) == 30
    assert len([e for e in plan['lanes'] if e['category'] == 'p2-challenge']) == 30
    assert inventory['source_sha256'][STAGE_TABLE_PATH]


ISO = Path('C:/Users/alari/pikmin-randomizer/assets/disc/PIKMIN2 for GAMECUBE.iso')


@pytest.mark.skipif(not ISO.is_file(), reason='no local GPVE01 disc image')
def test_live_table_matches_inventory():
    from experimental.pikmin2_assets import disc_files
    catalog = disc_files(ISO)
    at, size = catalog[STAGE_TABLE_PATH]
    with ISO.open('rb') as disc:
        disc.seek(at)
        stages = parse_stage_table(disc.read(size).decode('shift_jis'))
    assert len(stages) == 30
    inventory = json.loads((ROOT / 'docs/PIKMIN2_CONTENT_INVENTORY.json').read_text(encoding='utf-8'))
    assert cross_check_inventory(stages, inventory) == []
    assert {s['cave_id'] for s in stages} == {e['cave_id'] for e in inventory['challenge']['stages']}