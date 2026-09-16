"""Focused P0 tests for the ch_NARI_05start3easy import adapter (issue #548).

Synthetic inputs only (no disc image): malformed stage blocks, contract
divergences, missing pools and unreadable sources must fail closed with
ContractMismatch, never with invented values.
"""
import importlib.util as _importlib_util
import unittest
from pathlib import Path

# Reserved filename contains dashes; load the exact reserved path under alias.
_ADAPTER_PATH = (Path(__file__).resolve().parents[2] / "experimental" / "content_lanes"
                 / "p2-challenge-ch_nari_05start3easy.py")
_SPEC = _importlib_util.spec_from_file_location("p2_challenge_ch_nari_05start3easy", _ADAPTER_PATH)
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
\tch_NARI_05start3easy.txt
\t# PikiCounter
\t1 \t# col0 happa0
\t0 \t# col0 happa1
\t0 \t# col0 happa2
\t1 \t# col1 happa0
\t0 \t# col1 happa1
\t0 \t# col1 happa2
\t1 \t# col2 happa0
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
\t0 \t# col5 happa2
\t0 \t# col6 happa0
\t0 \t# col6 happa1
\t0 \t# col6 happa2
\t400.000000 \t# time
\t1 \t# dope black
\t2 \t# dope red
\t2 \t# floor num
\t0 \t# otakara num
\t15 \t# 2d index
\t120.000000 \t# 1""" + "\u968e\u306e\u79d2\u6570" + """
\t80.000000 \t# 2""" + "\u968e\u306e\u79d2\u6570" + """
}"""


def stage():
    return dict(cave_file="ch_NARI_05start3easy.txt",
                pikmin=[[1, 0, 0], [1, 0, 0], [1, 0, 0],
                        [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
                legacy_time=400.0, bitter_sprays=1, spicy_sprays=2, floors=2,
                treasure_count=0, ui_index=15, floor_seconds=[120.0, 80.0])


def contract():
    return dict(lane="p2-challenge-ch_nari_05start3easy", source_id="ch_NARI_05start3easy",
                cave_path="user/Mukki/mapunits/caveinfo/ch_NARI_05start3easy.txt",
                floors=2, pikmin=[[1, 0, 0], [1, 0, 0], [1, 0, 0],
                                  [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
                legacy_time=400.0, bitter_sprays=1, spicy_sprays=2,
                treasure_count=0, ui_index=15, floor_seconds=[120.0, 80.0])


def cave():
    return dict(
        cave_id="ch_NARI_05start3easy",
        source="user/Mukki/mapunits/caveinfo/ch_NARI_05start3easy.txt",
        floor_count=2, definition_count=2, floors=[
            dict(first_floor=1, last_floor=1,
                 parameters={"f008": "2_MAT_cent_north_tsuchi.txt"},
                 enemies=[dict(source_token="RandPom", enemy_id="RandPom",
                               carried_treasure=None, source_weight=20, placement_type=1)],
                 treasures=[dict(treasure_id="key", source_weight=10)],
                 gates=[], caps=[dict(empty=True)]),
            dict(first_floor=2, last_floor=2,
                 parameters={"f008": "2_MAT_cent_north_tsuchi.txt"},
                 enemies=[dict(source_token="Wtank_key", enemy_id="Wtank",
                               carried_treasure="key", source_weight=10, placement_type=1)],
                 treasures=[dict(treasure_id="dia_a_green", source_weight=10)],
                 gates=[], caps=[])])


def catalog():
    return {"unit_pools": {
        "2_MAT_cent_north_tsuchi.txt": {"source": "user/Mukki/mapunits/units/2_MAT_cent_north_tsuchi.txt",
                                       "units": [{"name": "room_cent"}, {"name": "way3_tsuchi"}]}}}


class Start3EasyContractTests(unittest.TestCase):
    def test_stage_block_parses(self):
        parsed = parse_stage_block(BLOCK)
        self.assertEqual(parsed["cave_file"], "ch_NARI_05start3easy.txt")
        self.assertEqual(parsed["pikmin"][:3], [[1, 0, 0]] * 3)
        self.assertEqual(parsed["floor_seconds"], [120.0, 80.0])
        self.assertEqual(parsed["bitter_sprays"], 1)
        self.assertEqual(parsed["spicy_sprays"], 2)
        report = verify_stage(parsed, contract())
        self.assertEqual(report["starting_pikmin"], 3)

    def test_matching_cave_verifies(self):
        coverage = verify_cave_contract(cave(), contract())
        self.assertEqual([row["unit_pool"] for row in coverage],
                         ["2_MAT_cent_north_tsuchi.txt"] * 2)
        closure, pool_hashes = verify_closure(cave(), catalog())
        self.assertEqual(closure[1]["units"], ["room_cent", "way3_tsuchi"])
        self.assertEqual(pool_hashes, {})
        self.assertTrue(all(row.get("provenance") == "baseline" for row in closure))

    def test_real_lanes_document_loads(self):
        loaded = lane_contract(LANES)
        self.assertEqual(loaded["floors"], 2)
        self.assertEqual(loaded["floor_seconds"], [120.0, 80.0])
        self.assertEqual(loaded["ui_index"], 15)
        self.assertEqual(loaded["legacy_time"], 400.0)

    def test_stage_block_problems_fail_closed(self):
        with self.assertRaises(ContractMismatch):
            split_stage_blocks("no blocks here")
        with self.assertRaises(ContractMismatch):
            parse_stage_block(BLOCK + "trailing")
        with self.assertRaises(ContractMismatch):
            parse_stage_block(BLOCK.replace("{", "", 1))
        with self.assertRaises(ContractMismatch):
            verify_stage(stage() | {"ui_index": 16}, contract())
        with self.assertRaises(ContractMismatch):
            verify_stage(stage() | {"floor_seconds": [120.0, 90.0]}, contract())
        with self.assertRaises(ContractMismatch):
            verify_stage(stage() | {"spicy_sprays": 0}, contract())

    def test_cave_contract_problems_fail_closed(self):
        mutated = cave()
        mutated["floors"][1]["last_floor"] = 3
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
            read_iso_file("C:/nonexistent.iso", "user/Mukki/mapunits/caveinfo/ch_NARI_05start3easy.txt")
        with self.assertRaises(ContractMismatch):
            decode_stage("C:/nonexistent.iso")


if __name__ == "__main__":
    unittest.main()
