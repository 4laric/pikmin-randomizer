"""Focused P0 tests for the yakushima_1 import adapter (issue #158).

Synthetic inputs only (no disc image): malformed contracts, token/floor
divergences, missing pools and unreadable sources must fail closed with
ContractMismatch, never with invented values.
"""
import json
import unittest
from pathlib import Path

# The reserved adapter filename contains dashes (p2-cave-yakushima_1.py), so it
# is not importable by statement; load it from its exact reserved path under a
# valid module alias. The adapter's own shared imports stay absolute.
import importlib.util as _importlib_util

_ADAPTER_PATH = (Path(__file__).resolve().parents[2] / 'experimental' / 'content_lanes'
                 / 'p2-cave-yakushima_1.py')
_SPEC = _importlib_util.spec_from_file_location('p2_cave_yakushima_1', _ADAPTER_PATH)
_adapter = _importlib_util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_adapter)

ContractMismatch = _adapter.ContractMismatch
decode_live = _adapter.decode_live
lane_contract = _adapter.lane_contract
read_iso_file = _adapter.read_iso_file
verify_closure = _adapter.verify_closure
verify_contract = _adapter.verify_contract

LANES = 'C:/Users/alari/pikmin-randomizer/docs/PIKMIN_CONTENT_IMPORT_LANES.json'


def contract_floors():
    return [
        dict(index=0, first=1, last=1, unit_pool='pool_a.txt',
             enemy_ids=['Tobi', 'Frog_g_futa_titiyas'], treasure_ids=['leaf_normal']),
        dict(index=1, first=2, last=2, unit_pool='pool_b.txt',
             enemy_ids=['Sarai'], treasure_ids=['sinjyu', 'kan_nichiro']),
    ]


def contract():
    return dict(lane='p2-cave-yakushima_1', source_id='yakushima_1',
                source='user/Mukki/mapunits/caveinfo/yakushima_1.txt',
                floor_count=2, floors=contract_floors())


def cave():
    return dict(
        cave_id='yakushima_1', source='user/Mukki/mapunits/caveinfo/yakushima_1.txt',
        floor_count=2, definition_count=2, floors=[
            dict(first_floor=1, last_floor=1,
                 parameters={'f008': 'pool_a.txt'},
                 enemies=[dict(source_token='Tobi'), dict(source_token='Frog_g_futa_titiyas')],
                 treasures=[dict(treasure_id='leaf_normal')], gates=[], caps=[]),
            dict(first_floor=2, last_floor=2,
                 parameters={'f008': 'pool_b.txt'},
                 enemies=[dict(source_token='Sarai')],
                 treasures=[dict(treasure_id='sinjyu'), dict(treasure_id='kan_nichiro')],
                 gates=[], caps=[]),
        ])


def catalog():
    return {'unit_pools': {
        'pool_a.txt': {'source': 'user/Mukki/mapunits/units/pool_a.txt',
                       'units': [{'name': 'unit_a'}, {'name': 'unit_b'}]},
        'pool_b.txt': {'source': 'user/Mukki/mapunits/units/pool_b.txt',
                       'units': [{'name': 'unit_c'}]},
    }}


class YakushimaContractTests(unittest.TestCase):
    def test_matching_contract_verifies(self):
        coverage = verify_contract(cave(), contract())
        self.assertEqual([(row['floor'], row['unit_pool']) for row in coverage],
                         [(1, 'pool_a.txt'), (2, 'pool_b.txt')])
        closure = verify_closure(cave(), catalog())
        self.assertEqual([row['units'] for row in closure],
                         [['unit_a', 'unit_b'], ['unit_c']])

    def test_real_lanes_document_loads(self):
        loaded = lane_contract(LANES)
        self.assertEqual(loaded['floor_count'], 5)
        self.assertEqual([floor['first'] for floor in loaded['floors']], [1, 2, 3, 4, 5])
        self.assertEqual(loaded['floors'][1]['enemy_ids'][0], 'Frog_g_futa_titiyas')
        self.assertEqual(loaded['floors'][4]['unit_pool'], '1_units_DKumo_conc.txt')

    def test_contract_document_problems_fail_closed(self):
        with self.assertRaises(ContractMismatch):
            lane_contract('C:/nonexistent-lanes.json')
        with self.assertRaises(ContractMismatch):
            lane_contract(LANES, lane='p2-cave-no-such-lane')

    def test_token_floor_pool_divergences_fail_closed(self):
        mutated = cave()
        mutated['floors'][0]['enemies'][1]['source_token'] = 'Frog'
        with self.assertRaises(ContractMismatch):
            verify_contract(mutated, contract())
        mutated = cave()
        mutated['floors'][1]['treasures'] = [dict(treasure_id='wrong')]
        with self.assertRaises(ContractMismatch):
            verify_contract(mutated, contract())
        mutated = cave()
        mutated['floors'][0]['parameters'] = {'f008': 'other.txt'}
        with self.assertRaises(ContractMismatch):
            verify_contract(mutated, contract())
        mutated = cave()
        mutated['floor_count'] = 3
        with self.assertRaises(ContractMismatch):
            verify_contract(mutated, contract())
        mutated = cave()
        mutated['cave_id'] = 'yakushima_2'
        with self.assertRaises(ContractMismatch):
            verify_contract(mutated, contract())

    def test_missing_pool_breaks_closure(self):
        broken = catalog()
        del broken['unit_pools']['pool_b.txt']
        with self.assertRaises(ContractMismatch):
            verify_closure(cave(), broken)
        with self.assertRaises(ContractMismatch):
            verify_closure(cave(), {'unit_pools': {}})

    def test_unreadable_sources_fail_closed(self):
        with self.assertRaises(ContractMismatch):
            read_iso_file('C:/nonexistent.iso', 'user/Mukki/mapunits/caveinfo/yakushima_1.txt')
        with self.assertRaises(ContractMismatch):
            decode_live('C:/nonexistent.iso', 'C:/nonexistent-research')


if __name__ == '__main__':
    unittest.main()
