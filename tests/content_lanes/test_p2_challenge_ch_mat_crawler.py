"""Focused P0 tests for the ch_MAT_crawler import adapter (issue #562).

Synthetic inputs only (no disc image): malformed stage blocks, contract
divergences, missing pools and unreadable sources must fail closed with
ContractMismatch, never with invented values.
"""
import importlib.util as _importlib_util
import unittest
from pathlib import Path

# Reserved filename contains dashes; load the exact reserved path under alias.
_ADAPTER_PATH = (Path(__file__).resolve().parents[2] / "experimental" / "content_lanes"
                 / "p2-challenge-ch_mat_crawler.py")
_SPEC = _importlib_util.spec_from_file_location("p2_challenge_ch_mat_crawler", _ADAPTER_PATH)
_adapter = _importlib_util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_adapter)

ContractMismatch = _adapter.ContractMismatch
decode_pool_live = _adapter.decode_pool_live
decode_stage = _adapter.decode_stage
lane_contract = _adapter.lane_contract
parse_stage_block = _adapter.parse_stage_block
read_iso_file = _adapter.read_iso_file
split_stage_blocks = _adapter.split_stage_blocks
verify_cave_contract = _adapter.verify_cave_contract
verify_closure = _adapter.verify_closure
verify_stage = _adapter.verify_stage

LANES = "C:/Users/alari/pikmin-randomizer/docs/PIKMIN_CONTENT_IMPORT_LANES.json"
ISO = "C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso"

BLOCK = """{
\t4 \t# version
\tch_MAT_crawler.txt
\t# PikiCounter
\t0 \t# col0 happa0
\t0 \t# col0 happa1
\t30 \t# col0 happa2
\t0 \t# col1 happa0
\t0 \t# col1 happa1
\t30 \t# col1 happa2
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
\t0 \t# col5 happa2
\t0 \t# col6 happa0
\t0 \t# col6 happa1
\t0 \t# col6 happa2
\t500.000000 \t# time
\t3 \t# dope black
\t4 \t# dope red
\t2 \t# floor num
\t0 \t# otakara num
\t29 \t# 2d index
\t170.000000 \t# 1""" + "\u968e\u306e\u79d2\u6570" + """
\t120.000000 \t# 2""" + "\u968e\u306e\u79d2\u6570" + """
}"""


def stage():
    return dict(cave_file="ch_MAT_crawler.txt",
                pikmin=[[0, 0, 30], [0, 0, 30], [0, 0, 0], [0, 0, 0],
                        [0, 0, 0], [0, 0, 0], [0, 0, 0]],
                legacy_time=500.0, bitter_sprays=3, spicy_sprays=4, floors=2,
                treasure_count=0, ui_index=29, floor_seconds=[170.0, 120.0])


def contract():
    return dict(lane="p2-challenge-ch_mat_crawler", source_id="ch_MAT_crawler",
                cave_path="user/Mukki/mapunits/caveinfo/ch_MAT_crawler.txt",
                floors=2, pikmin=[[0, 0, 30], [0, 0, 30], [0, 0, 0], [0, 0, 0],
                                  [0, 0, 0], [0, 0, 0], [0, 0, 0]],
                legacy_time=500.0, bitter_sprays=3, spicy_sprays=4,
                treasure_count=0, ui_index=29, floor_seconds=[170.0, 120.0])


def cave():
    return dict(
        cave_id="ch_MAT_crawler",
        source="user/Mukki/mapunits/caveinfo/ch_MAT_crawler.txt",
        floor_count=2, definition_count=2, floors=[
            dict(first_floor=1, last_floor=1,
                 parameters={"f008": "4_units_c_e_j_l_conc.txt"},
                 enemies=[dict(source_token="Hana_silver_medal", enemy_id="Hana",
                               carried_treasure="silver_medal", source_weight=10, placement_type=1)],
                 treasures=[dict(treasure_id="key", source_weight=10)],
                 gates=[dict(gate_id="gate", life=4000.0, selection_weight=1)], caps=[]),
            dict(first_floor=2, last_floor=2,
                 parameters={"f008": "1_units_manh_conc.txt"},
                 enemies=[dict(source_token="SnakeWhole_key", enemy_id="SnakeWhole",
                               carried_treasure="key", source_weight=10, placement_type=1)],
                 treasures=[], gates=[], caps=[])])


def catalog():
    return {"unit_pools": {
        "1_units_manh_conc.txt": {"source": "user/Mukki/mapunits/units/1_units_manh_conc.txt",
                                  "units": [{"name": "room_manh_2_conc"}]}}}


class MatCrawlerContractTests(unittest.TestCase):
    def test_stage_block_parses(self):
        parsed = parse_stage_block(BLOCK)
        self.assertEqual(parsed["cave_file"], "ch_MAT_crawler.txt")
        self.assertEqual(parsed["pikmin"][:2], [[0, 0, 30]] * 2)
        self.assertEqual(parsed["floor_seconds"], [170.0, 120.0])
        self.assertEqual(parsed["bitter_sprays"], 3)
        self.assertEqual(parsed["spicy_sprays"], 4)
        report = verify_stage(parsed, contract())
        self.assertEqual(report["starting_pikmin"], 60)

    def test_matching_cave_verifies(self):
        coverage = verify_cave_contract(cave(), contract())
        self.assertEqual([row["unit_pool"] for row in coverage],
                         ["4_units_c_e_j_l_conc.txt", "1_units_manh_conc.txt"])
        self.assertEqual(coverage[0]["gates"][0]["life"], 4000.0)
        self.assertEqual(coverage[0]["enemies"][0]["carried_treasure"], "silver_medal")

    def test_closure_baseline_hit_and_missing_pool_fail_closed(self):
        # Baseline covers floor 2 only; without an ISO a missing pool fails
        # closed rather than inventing closure.
        with self.assertRaises(ContractMismatch):
            verify_closure(cave(), catalog())

    @unittest.skipUnless(Path(ISO).is_file(), "local disc image unavailable")
    def test_live_pool_decode_against_disc(self):
        entry, digest = decode_pool_live(ISO, "4_units_c_e_j_l_conc.txt")
        self.assertEqual(entry["source"], "user/Mukki/mapunits/units/4_units_c_e_j_l_conc.txt")
        self.assertEqual(len(digest), 64)
        self.assertIn("room_4x4c_4_conc", [u["name"] for u in entry["units"]])

    def test_real_lanes_document_loads(self):
        loaded = lane_contract(LANES)
        self.assertEqual(loaded["floors"], 2)
        self.assertEqual(loaded["floor_seconds"], [170.0, 120.0])
        self.assertEqual(loaded["ui_index"], 29)
        self.assertEqual(loaded["legacy_time"], 500.0)
        self.assertEqual(loaded["pikmin"][0], [0, 0, 30])

    def test_stage_block_problems_fail_closed(self):
        with self.assertRaises(ContractMismatch):
            split_stage_blocks("no blocks here")
        with self.assertRaises(ContractMismatch):
            parse_stage_block(BLOCK + "trailing")
        with self.assertRaises(ContractMismatch):
            parse_stage_block(BLOCK.replace("{", "", 1))
        with self.assertRaises(ContractMismatch):
            verify_stage(stage() | {"ui_index": 30}, contract())
        with self.assertRaises(ContractMismatch):
            verify_stage(stage() | {"floor_seconds": [170.0, 130.0]}, contract())
        with self.assertRaises(ContractMismatch):
            verify_stage(stage() | {"bitter_sprays": 0}, contract())

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
            read_iso_file("C:/nonexistent.iso", "user/Mukki/mapunits/caveinfo/ch_MAT_crawler.txt")
        with self.assertRaises(ContractMismatch):
            decode_stage("C:/nonexistent.iso")
        with self.assertRaises(ContractMismatch):
            decode_pool_live("C:/nonexistent.iso", "4_units_c_e_j_l_conc.txt")


def packet():
    return dict(lane="p2-challenge-ch_mat_crawler", source_id="ch_MAT_crawler",
                source_sha256="ab" * 32, floor_count=2,
                stage=dict(starting_pikmin=60, floor_seconds=[170.0, 120.0]),
                coverage=[
                    dict(floor=1, last=1, unit_pool="4_units_c_e_j_l_conc.txt",
                         enemies=[dict(source_token="Hana_silver_medal")],
                         treasures=[dict(treasure_id="key")],
                         gates=[dict(gate_id="gate")], caps=[]),
                    dict(floor=2, last=2, unit_pool="1_units_manh_conc.txt",
                         enemies=[dict(source_token="SnakeWhole_key")],
                         treasures=[], gates=[], caps=[])])


class MatCrawlerP1StagingTests(unittest.TestCase):
    def test_stage_run_layout(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            paths = _adapter.stage_run_layout(packet(), contract(), Path(directory) / "run")
            self.assertEqual(sorted(paths), ["markers.txt", "run-config.json",
                                             "squad.json", "stage-manifest.json"])
            manifest = _adapter.verify_run_layout(Path(directory) / "run")
            self.assertEqual(manifest["squad_total"], 60)
            self.assertEqual(manifest["floor_seconds"], [170.0, 120.0])
            self.assertEqual(manifest["ui_index"], 29)
            self.assertIn("challenge_host_mode",
                          manifest["unsupported_semantics"])

    def test_squad_list(self):
        rows = _adapter.squad_list(contract()["pikmin"])
        self.assertEqual(rows, [{"color": 0, "maturity": 2, "count": 30},
                                {"color": 1, "maturity": 2, "count": 30}])
        with self.assertRaises(ContractMismatch):
            _adapter.squad_list([[0, 0]])
        with self.assertRaises(ContractMismatch):
            _adapter.squad_list([[0, 0, -1]] + [[0, 0, 0]] * 6)

    def test_staging_divergences_fail_closed(self):
        import tempfile
        bad = packet()
        bad["floor_count"] = 3
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ContractMismatch):
                _adapter.stage_run_layout(bad, contract(), Path(directory) / "run")
        bad = packet()
        bad["stage"] = dict(bad["stage"], starting_pikmin=61)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ContractMismatch):
                _adapter.stage_run_layout(bad, contract(), Path(directory) / "run")
        bad = packet()
        bad["coverage"][0]["last"] = 2
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ContractMismatch):
                _adapter.stage_run_layout(bad, contract(), Path(directory) / "run")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ContractMismatch):
                _adapter.verify_run_layout(directory)


if __name__ == "__main__":
    unittest.main()
