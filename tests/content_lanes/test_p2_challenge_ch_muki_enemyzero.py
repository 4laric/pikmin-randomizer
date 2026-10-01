"""Focused P0 tests for the ch_MUKI_enemyzero import adapter (issue #546).

Synthetic inputs only (no disc image): malformed stage blocks, contract
divergences, missing pools and unreadable sources must fail closed with
ContractMismatch, never with invented values.
"""
import importlib.util as _importlib_util
import unittest
from pathlib import Path

# Reserved filename contains dashes; load the exact reserved path under alias.
_ADAPTER_PATH = (Path(__file__).resolve().parents[2] / "experimental" / "content_lanes"
                 / "p2-challenge-ch_muki_enemyzero.py")
_SPEC = _importlib_util.spec_from_file_location("p2_challenge_ch_muki_enemyzero", _ADAPTER_PATH)
_adapter = _importlib_util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_adapter)

ContractMismatch = _adapter.ContractMismatch
decode_stage = _adapter.decode_stage
lane_contract = _adapter.lane_contract
parse_stage_block = _adapter.parse_stage_block
read_iso_file = _adapter.read_iso_file
split_stage_blocks = _adapter.split_stage_blocks
verify_cave_contract = _adapter.verify_cave_contract
verify_closure = _adapter.verify_closure
verify_stage = _adapter.verify_stage

LANES = "C:/Users/alari/pikmin-randomizer/docs/PIKMIN_CONTENT_IMPORT_LANES.json"

BLOCK = """{
\t4 \t# version
\tch_MUKI_enemyzero.txt 
\t# PikiCounter
\t0 \t# col0 happa0
\t0 \t# col0 happa1
\t0 \t# col0 happa2
\t0 \t# col1 happa0
\t0 \t# col1 happa1
\t0 \t# col1 happa2
\t0 \t# col2 happa0
\t0 \t# col2 happa1
\t0 \t# col2 happa2
\t0 \t# col3 happa0
\t0 \t# col3 happa1
\t0 \t# col3 happa2
\t0 \t# col4 happa0
\t0 \t# col4 happa1
\t0 \t# col4 happa2
\t0 \t# col5 happa0
\t0 \t# col5 happa1
\t2 \t# col5 happa2
\t0 \t# col6 happa0
\t0 \t# col6 happa1
\t0 \t# col6 happa2
\t0.000000 \t# time
\t0 \t# dope black
\t0 \t# dope red
\t1 \t# floor num
\t0 \t# otakara num
\t13 \t# 2d index
\t200.000000 \t# 1""" + "\u968e\u306e\u79d2\u6570" + """
}"""


def stage():
    return dict(cave_file="ch_MUKI_enemyzero.txt",
                pikmin=[[0, 0, 0]] * 5 + [[0, 0, 2]] + [[0, 0, 0]],
                legacy_time=0.0, bitter_sprays=0, spicy_sprays=0, floors=1,
                treasure_count=0, ui_index=13, floor_seconds=[200.0])


def contract():
    return dict(lane="p2-challenge-ch_muki_enemyzero", source_id="ch_MUKI_enemyzero",
                cave_path="user/Mukki/mapunits/caveinfo/ch_MUKI_enemyzero.txt",
                floors=1, pikmin=[[0, 0, 0]] * 5 + [[0, 0, 2]] + [[0, 0, 0]],
                legacy_time=0.0, bitter_sprays=0, spicy_sprays=0,
                treasure_count=0, ui_index=13, floor_seconds=[200.0])


def cave():
    return dict(
        cave_id="ch_MUKI_enemyzero",
        source="user/Mukki/mapunits/caveinfo/ch_MUKI_enemyzero.txt",
        floor_count=1, definition_count=1, floors=[
            dict(first_floor=1, last_floor=1,
                 parameters={"f008": "1_unit_16x17r_conc.txt"},
                 enemies=[dict(source_token="Sokkuri_key", enemy_id="Sokkuri",
                               carried_treasure="key", source_weight=1, placement_type=6)],
                 treasures=[dict(treasure_id="be_dama_blue_l", source_weight=10)],
                 gates=[], caps=[])])


def catalog():
    return {"unit_pools": {
        "1_unit_16x17r_conc.txt": {"source": "user/Mukki/mapunits/units/1_unit_16x17r_conc.txt",
                                   "units": [{"name": "room_16x17r_conc"}]}}}


class EnemyzeroContractTests(unittest.TestCase):
    def test_stage_block_parses(self):
        parsed = parse_stage_block(BLOCK)
        self.assertEqual(parsed["cave_file"], "ch_MUKI_enemyzero.txt")
        self.assertEqual(parsed["pikmin"][5], [0, 0, 2])
        self.assertEqual(parsed["floor_seconds"], [200.0])
        self.assertEqual(parsed["ui_index"], 13)
        report = verify_stage(parsed, contract())
        self.assertEqual(report["starting_pikmin"], 2)

    def test_matching_cave_verifies(self):
        coverage = verify_cave_contract(cave(), contract())
        self.assertEqual(coverage["unit_pool"], "1_unit_16x17r_conc.txt")
        self.assertEqual(coverage["enemies"][0]["enemy_id"], "Sokkuri")
        closure = verify_closure(cave(), catalog())
        self.assertEqual(closure[0]["units"], ["room_16x17r_conc"])

    def test_real_lanes_document_loads(self):
        loaded = lane_contract(LANES)
        self.assertEqual(loaded["floors"], 1)
        self.assertEqual(loaded["pikmin"][5], [0, 0, 2])
        self.assertEqual(loaded["floor_seconds"], [200.0])
        self.assertEqual(loaded["ui_index"], 13)

    def test_stage_block_problems_fail_closed(self):
        with self.assertRaises(ContractMismatch):
            split_stage_blocks("no blocks here")
        with self.assertRaises(ContractMismatch):
            parse_stage_block(BLOCK.replace("13 \t# 2d index", "14 \t# 2d index") + "trailing")
        with self.assertRaises(ContractMismatch):
            parse_stage_block(BLOCK.replace("{", "", 1))
        with self.assertRaises(ContractMismatch):
            verify_stage(stage() | {"ui_index": 14}, contract())
        with self.assertRaises(ContractMismatch):
            verify_stage(stage() | {"floor_seconds": [100.0]}, contract())

    def test_cave_contract_problems_fail_closed(self):
        mutated = cave()
        mutated["floors"][0]["first_floor"] = 2
        with self.assertRaises(ContractMismatch):
            verify_cave_contract(mutated, contract())
        mutated = cave()
        mutated["cave_id"] = "ch_MUKI_king"
        with self.assertRaises(ContractMismatch):
            verify_cave_contract(mutated, contract())
        with self.assertRaises(ContractMismatch):
            verify_closure(cave(), {"unit_pools": {}})

    def test_contract_document_problems_fail_closed(self):
        with self.assertRaises(ContractMismatch):
            lane_contract("C:/nonexistent-lanes.json")
        with self.assertRaises(ContractMismatch):
            lane_contract(LANES, lane="p2-challenge-no-such-lane")

    def test_unreadable_sources_fail_closed(self):
        with self.assertRaises(ContractMismatch):
            read_iso_file("C:/nonexistent.iso", "user/Mukki/mapunits/caveinfo/ch_MUKI_enemyzero.txt")
        with self.assertRaises(ContractMismatch):
            decode_stage("C:/nonexistent.iso")


if __name__ == "__main__":
    unittest.main()
