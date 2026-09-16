"""P0 tests for the ch_ABEM_tutorial import adapter (issue #534).

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

# The lane owns exactly its three reserved files (no __init__.py) and the
# adapter filename uses hyphens per the lane plan, so it is loaded from its
# path rather than as a package import.
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
ADAPTER_PATH = ROOT / "experimental" / "content_lanes" / "p2-challenge-ch_abem_tutorial.py"
_spec = importlib.util.spec_from_file_location(
    "p2_challenge_ch_abem_tutorial", ADAPTER_PATH)
adapter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adapter)

ENEMIES = {"Clover", "Tukushi", "Ooinu_s", "KareOoinu_s", "Chappy", "Kochappy",
           "Egg", "Ooinu_l", "KareOoinu_l"}
TREASURES = {"key", "gold_medal", "silver_medal", "wadou_kaichin", "be_dama_red"}


def floor_block(first, last, pool, teki_rows, item_rows, cap_rows):
    teki = "\n\t".join(["%d 	# num" % len(teki_rows)] +
                        [f"{a} {b} 	# weight\n\t{c} 	# type" for a, b, c in teki_rows])
    items = "\n\t".join(["%d 	# num" % len(item_rows)] +
                         [f"{a} {b} 	# weight" for a, b in item_rows])
    if cap_rows is None:
        cap = "0 	# num"
    else:
        cap = "\n\t".join(["%d 	# num" % len(cap_rows)] +
                           [f"0 	# captype\n\t{a} {b} 	# weight\n\t{c} 	# type"
                            for a, b, c in cap_rows])
    return (
        "{\n"
        f"\t{{f000}} 4 {first}\n\t{{f001}} 4 {last}\n"
        f"\t{{f008}} -1 {pool}\n\t{{f009}} -1 normal_light_cha.ini\n"
        "\t{f015} 4 1\n\t{_eof} \n}\n"
        "# TekiInfo\n{\n\t" + teki + "\n}\n"
        "# ItemInfo\n{\n\t" + items + "\n}\n"
        "# GateInfo\n{\n\t0 	# num\n}\n"
        "# CapInfo\n{\n\t" + cap + "\n}"
    )


def two_floor_text():
    floor1 = floor_block(
        0, 0, "1_units_cent3_tsuchi.txt",
        [("Clover", 4, 6), ("Tukushi", 1, 6), ("Ooinu_s", 2, 6), ("KareOoinu_s", 3, 6)],
        [("key", 10), ("gold_medal", 10), ("silver_medal", 10), ("wadou_kaichin", 10)],
        None)
    floor2 = floor_block(
        1, 1, "2_MAT_mid1_nor2_tsuchi.txt",
        [("Chappy_key", 10, 1), ("Kochappy_be_dama_red", 50, 1), ("Egg", 10, 0),
         ("Clover", 2, 6), ("Tukushi", 2, 6), ("Ooinu_s", 2, 6), ("Ooinu_l", 2, 6),
         ("KareOoinu_s", 2, 6), ("KareOoinu_l", 2, 6)],
        [("gold_medal", 10), ("silver_medal", 10), ("wadou_kaichin", 10)],
        [("Egg", 20, 1)])
    return ("# CaveInfo\n{\n\t{c000} 4 2\n\t{_eof} \n}\n2 # FloorInfo\n"
            + floor1 + "\n" + floor2 + "\n")


def good_details():
    return {"floors": 2, "floor_seconds": [100.0, 100.0], "bitter_sprays": 2,
            "spicy_sprays": 2,
            "pikmin_by_native_color_and_maturity": [[0, 0, 0], [50, 0, 0], [0, 0, 0],
                                                   [0, 0, 0], [0, 0, 0], [0, 0, 0],
                                                   [0, 0, 0]],
            "ui_index": 0, "treasure_count_field": 0}


class DecodeTests(unittest.TestCase):
    def test_valid_two_floor_definition(self):
        cave = adapter.decode(two_floor_text(), ENEMIES, TREASURES)
        self.assertEqual((cave["definition_count"], cave["floor_count"]), (2, 2))

    def test_truncated_block_rejected(self):
        with self.assertRaises(ValueError):
            adapter.decode("# CaveInfo\n{\n\t{c000} 4 2\n", ENEMIES, TREASURES)

    def test_header_count_mismatch_rejected(self):
        bad = two_floor_text().replace("{c000} 4 2", "{c000} 4 3")
        with self.assertRaises(ValueError):
            adapter.decode(bad, ENEMIES, TREASURES)

    def test_unknown_enemy_rejected(self):
        bad = two_floor_text().replace("KareOoinu_l 2", "MysteryFoe 2", 1)
        with self.assertRaises(ValueError):
            adapter.decode(bad, ENEMIES, TREASURES)

    def test_unknown_treasure_rejected(self):
        bad = two_floor_text().replace("wadou_kaichin 10", "crown_jewel 10")
        with self.assertRaises(ValueError):
            adapter.decode(bad, ENEMIES, TREASURES)

    def test_unexpected_gate_rows_rejected_by_stage_check(self):
        gated = two_floor_text().replace(
            "# GateInfo\n{\n\t0 	# num\n}\n# CapInfo\n{\n\t0 	# num\n}",
            "# GateInfo\n{\n\t1 	# num\n\tgateA 100 10\n}\n# CapInfo\n{\n\t0 	# num\n}",
            1)
        cave = adapter.decode(gated, ENEMIES, TREASURES)
        with self.assertRaises(ValueError):
            adapter.check_stage(cave)


class StageCheckTests(unittest.TestCase):
    def test_observed_rosters_pass(self):
        cave = adapter.decode(two_floor_text(), ENEMIES, TREASURES)
        adapter.check_stage(cave)  # must not raise

    def test_wrong_unit_pool_rejected(self):
        bad = two_floor_text().replace("2_MAT_mid1_nor2_tsuchi.txt",
                                       "9_MAT_other_tsuchi.txt", 1)
        cave = adapter.decode(bad, ENEMIES, TREASURES)
        with self.assertRaises(ValueError):
            adapter.check_stage(cave)

    def test_dropped_enemy_row_rejected(self):
        bad = two_floor_text().replace('\tKareOoinu_s 2 	# weight\n\t6 	# type\n', '', 1)
        with self.assertRaises(ValueError):
            adapter.decode(bad, ENEMIES, TREASURES)

    def test_floor_gap_rejected(self):
        bad = two_floor_text().replace("{f000} 4 1\n\t{f001} 4 1",
                                       "{f000} 4 2\n\t{f001} 4 2", 1)
        cave = adapter.decode(bad, ENEMIES, TREASURES)
        with self.assertRaises(ValueError):
            adapter.check_stage(cave)


class MetadataCheckTests(unittest.TestCase):
    def test_baseline_passes(self):
        adapter.check_metadata(good_details())  # must not raise

    def test_timer_drift_rejected(self):
        details = good_details()
        details["floor_seconds"] = [100.0, 200.0]
        with self.assertRaises(ValueError):
            adapter.check_metadata(details)

    def test_spray_drift_rejected(self):
        details = good_details()
        details["spicy_sprays"] = 9
        with self.assertRaises(ValueError):
            adapter.check_metadata(details)

    def test_roster_drift_rejected(self):
        details = good_details()
        details["pikmin_by_native_color_and_maturity"][2] = [0, 0, 5]
        with self.assertRaises(ValueError):
            adapter.check_metadata(details)


class BoundaryTests(unittest.TestCase):
    def test_missing_disc_image_rejected(self):
        with self.assertRaises(ValueError):
            adapter.read_disc_bytes(__import__("pathlib").Path("/nonexistent/disc.iso"),
                                    adapter.CAVE_PATH)

    def test_hash_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            adapter.check_hash("0" * 64)

    def test_hash_match_accepted(self):
        adapter.check_hash(adapter.EXPECTED_SHA256)  # must not raise

    def test_missing_lane_entry_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = __import__("pathlib").Path(tmp) / "lanes.json"
            path.write_text(json.dumps({"lanes": []}), encoding="utf-8")
            with self.assertRaises(ValueError):
                adapter.lane_details(path)

    def test_manifest_is_metadata_only(self):
        cave = adapter.decode(two_floor_text(), ENEMIES, TREASURES)
        details = good_details()
        closure = {"unit_pools": {"p": {"sha256": "x", "units": ["u"]}},
                   "light": adapter.LIGHT_PATH}
        out = adapter.manifest(cave, details, closure, {"cave": adapter.EXPECTED_SHA256})
        self.assertFalse(out["generated"])
        for floor in out["floors"]:
            for key in ("position", "coordinates", "placements", "spawns", "x", "y", "z"):
                self.assertNotIn(key, floor)
        self.assertIn("definition inputs", json.dumps(out["limitations"]))


if __name__ == "__main__":
    unittest.main()
