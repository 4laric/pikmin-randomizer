"""P0 tests for the ch_MAT_t_hunter_otakara import adapter (issue #555).

Hermetic: all inputs are synthetic or tmp files. No test reads the lane
output directory, the disc image, or any hardcoded worktree path. Real-source
validation runs through the adapter main() and is recorded in run.log, not
in pytest.
"""
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
ADAPTER_PATH = (ROOT / "experimental" / "content_lanes"
                / "p2-challenge-ch_mat_t_hunter_otakara.py")
_spec = importlib.util.spec_from_file_location(
    "p2_challenge_ch_mat_t_hunter_otakara", ADAPTER_PATH)
adapter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adapter)

ENEMIES = {"FireOtakara", "WaterOtakara", "GasOtakara", "ElecOtakara"}
TREASURES = {"key", "saru_head", "badminton", "turi_uki", "toy_cat", "chocolate_l",
             "toy_ring_c_blue", "ichigo_l", "ahiru_head", "bird_hane",
             "be_dama_red", "be_dama_blue", "flower_blue", "wadou_kaichin"}

TEKI = [
    ("FireOtakara_be_dama_red", 10, 5),
    ("WaterOtakara_be_dama_blue", 10, 5),
    ("GasOtakara_flower_blue", 10, 5),
    ("FireOtakara_be_dama_red", 20, 1),
    ("WaterOtakara_be_dama_blue", 20, 1),
    ("GasOtakara_flower_blue", 20, 1),
    ("ElecOtakara_wadou_kaichin", 20, 1),
]
ITEMS = ["key", "saru_head", "badminton", "turi_uki", "toy_cat", "chocolate_l",
         "toy_ring_c_blue", "ichigo_l", "ahiru_head", "bird_hane"]


def floor_block(first=0, last=0, pool="1_MAT_manp_2_conc.txt",
                teki=None, items=None, cap_count=0):
    teki = TEKI if teki is None else teki
    items = ITEMS if items is None else items
    teki_txt = "\n\t".join([f"{len(teki)} \t# num"] +
                           [f"{a} {b} \t# weight\n\t{c} \t# type" for a, b, c in teki])
    item_txt = "\n\t".join([f"{len(items)} \t# num"] +
                           [f"{a} 10 \t# weight" for a in items])
    return (
        "{\n"
        f"\t{{f000}} 4 {first}\n\t{{f001}} 4 {last}\n"
        "\t{f002} 4 11\n\t{f003} 4 10\n\t{f004} 4 0\n\t{f014} 4 0\n"
        "\t{f005} 4 1\n\t{f006} 4 0.000000\n\t{f007} 4 1\n"
        f"\t{{f008}} -1 {pool}\n\t{{f009}} -1 normal_light_cha.ini\n"
        "\t{f00A} -1 none\n\t{f010} 4 0\n\t{f011} 4 2\n\t{f012} 4 0\n"
        "\t{f013} 4 0\n\t{f015} 4 1\n\t{f016} 4 0.000000\n\t{_eof} \n}\n"
        "# TekiInfo\n{\n\t" + teki_txt + "\n}\n"
        "# ItemInfo\n{\n\t" + item_txt + "\n}\n"
        "# GateInfo\n{\n\t0 \t# num\n}\n"
        "# CapInfo\n{\n\t" + f"{cap_count} \t# num" + "\n}"
    )


def good_text():
    return ("# CaveInfo\n{\n\t{c000} 4 1\n\t{_eof} \n}\n1 # FloorInfo\n"
            + floor_block() + "\n")


def good_details():
    return {
        "table_order": 13, "cave_id": "ch_MAT_t_hunter_otakara",
        "floors": 1, "floor_seconds": [180.0], "legacy_time": 300.0,
        "bitter_sprays": 0, "spicy_sprays": 0, "treasure_count_field": 6,
        "ui_index": 23,
        "pikmin_by_native_color_and_maturity": [[0, 0, 25], [0, 0, 25], [0, 0, 25],
                                                [0, 0, 0], [0, 0, 25], [0, 0, 0],
                                                [0, 0, 0]],
    }


class DecodeTests(unittest.TestCase):
    def test_valid_single_floor_definition(self):
        cave = adapter.decode(good_text(), ENEMIES, TREASURES)
        self.assertEqual((cave["definition_count"], cave["floor_count"]), (1, 1))

    def test_truncated_block_rejected(self):
        with self.assertRaises(ValueError):
            adapter.decode("# CaveInfo\n{\n\t{c000} 4 1\n", ENEMIES, TREASURES)

    def test_header_count_mismatch_rejected(self):
        bad = good_text().replace("{c000} 4 1", "{c000} 4 2")
        with self.assertRaises(ValueError):
            adapter.decode(bad, ENEMIES, TREASURES)

    def test_unknown_enemy_rejected(self):
        bad = good_text().replace("ElecOtakara_wadou_kaichin", "MysteryOtakara")
        with self.assertRaises(ValueError):
            adapter.decode(bad, ENEMIES, TREASURES)

    def test_unknown_carried_treasure_rejected(self):
        bad = good_text().replace("be_dama_red", "be_dama_mauve")
        with self.assertRaises(ValueError):
            adapter.decode(bad, ENEMIES, TREASURES)

    def test_unknown_item_rejected(self):
        bad = good_text().replace("bird_hane 10", "crown_jewel 10")
        with self.assertRaises(ValueError):
            adapter.decode(bad, ENEMIES, TREASURES)

    def test_carried_treasure_resolved(self):
        cave = adapter.decode(good_text(), ENEMIES, TREASURES)
        got = tuple((e["enemy_id"], e["carried_treasure"])
                    for e in cave["floors"][0]["enemies"])
        self.assertEqual(got, adapter.EXPECTED_FLOORS[0]["carried"])


class StageCheckTests(unittest.TestCase):
    def test_observed_rosters_pass(self):
        adapter.check_stage(adapter.decode(good_text(), ENEMIES, TREASURES))

    def test_wrong_unit_pool_rejected(self):
        bad = good_text().replace("1_MAT_manp_2_conc.txt", "9_MAT_other_conc.txt")
        cave = adapter.decode(bad, ENEMIES, TREASURES)
        with self.assertRaises(ValueError):
            adapter.check_stage(cave)

    def test_changed_weight_rejected(self):
        bad = good_text().replace("GasOtakara_flower_blue 20", "GasOtakara_flower_blue 11")
        cave = adapter.decode(bad, ENEMIES, TREASURES)
        with self.assertRaises(ValueError):
            adapter.check_stage(cave)

    def test_changed_carried_treasure_rejected(self):
        bad = good_text().replace("ElecOtakara_wadou_kaichin", "ElecOtakara_be_dama_red")
        cave = adapter.decode(bad, ENEMIES, TREASURES)
        with self.assertRaises(ValueError):
            adapter.check_stage(cave)

    def test_floor_range_gap_rejected(self):
        bad = good_text().replace("{f000} 4 0", "{f000} 4 1").replace("{f001} 4 0", "{f001} 4 1")
        cave = adapter.decode(bad, ENEMIES, TREASURES)
        with self.assertRaises(ValueError):
            adapter.check_stage(cave)

    def test_extra_cap_rejected(self):
        bad = good_text().replace("# CapInfo\n{\n\t0 \t# num\n}",
                                  "# CapInfo\n{\n\t1 \t# num\n\t0 \t# captype\n\t"
                                  "FireOtakara_be_dama_red 20 \t# weight\n\t1 \t# type\n}")
        cave = adapter.decode(bad, ENEMIES, TREASURES)
        with self.assertRaises(ValueError):
            adapter.check_stage(cave)

    def test_unexpected_gate_rows_rejected(self):
        bad = good_text().replace("# GateInfo\n{\n\t0 \t# num\n}",
                                  "# GateInfo\n{\n\t1 \t# num\n\tgateA 100 10\n}")
        cave = adapter.decode(bad, ENEMIES, TREASURES)
        with self.assertRaises(ValueError):
            adapter.check_stage(cave)


class MetadataCheckTests(unittest.TestCase):
    def test_baseline_passes(self):
        adapter.check_metadata(good_details())

    def test_timer_drift_rejected(self):
        details = good_details()
        details["floor_seconds"] = [120.0]
        with self.assertRaises(ValueError):
            adapter.check_metadata(details)

    def test_ui_index_drift_rejected(self):
        details = good_details()
        details["ui_index"] = 1
        with self.assertRaises(ValueError):
            adapter.check_metadata(details)

    def test_spray_drift_rejected(self):
        details = good_details()
        details["spicy_sprays"] = 2
        with self.assertRaises(ValueError):
            adapter.check_metadata(details)

    def test_roster_drift_rejected(self):
        details = good_details()
        details["pikmin_by_native_color_and_maturity"][3] = [0, 0, 25]
        with self.assertRaises(ValueError):
            adapter.check_metadata(details)

    def test_treasure_count_field_drift_rejected(self):
        details = good_details()
        details["treasure_count_field"] = 5
        with self.assertRaises(ValueError):
            adapter.check_metadata(details)


class BoundaryTests(unittest.TestCase):
    def test_missing_disc_image_rejected(self):
        with self.assertRaises(ValueError):
            adapter.read_disc_bytes(Path("/nonexistent/disc.iso"), adapter.CAVE_PATH)

    def test_hash_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            adapter.check_hash("0" * 64)

    def test_hash_match_accepted(self):
        adapter.check_hash(adapter.EXPECTED_SHA256)

    def test_size_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            adapter.check_hash(adapter.EXPECTED_SHA256, adapter.EXPECTED_SHA256_BYTES + 1)

    def test_missing_lane_entry_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lanes.json"
            path.write_text(json.dumps({"lanes": []}), encoding="utf-8")
            with self.assertRaises(ValueError):
                adapter.lane_details(path)

    def test_manifest_is_metadata_only(self):
        cave = adapter.decode(good_text(), ENEMIES, TREASURES)
        closure = {"unit_pools": {"p": {"sha256": "x", "units": ["u"]}},
                   "light": adapter.LIGHT_PATH}
        out = adapter.manifest(cave, good_details(), closure,
                               {"cave": adapter.EXPECTED_SHA256})
        self.assertFalse(out["generated"])
        self.assertEqual(out["ui_index"], 23)
        self.assertEqual(out["treasure_count_field"], 6)
        self.assertEqual([float(v) for v in out["floor_seconds"]], [180.0])
        for floor in out["floors"]:
            for key in ("position", "coordinates", "x", "y", "z", "instances"):
                self.assertNotIn(key, floor)
        self.assertIn("definition inputs", " ".join(out["limitations"]))


if __name__ == "__main__":
    unittest.main()
