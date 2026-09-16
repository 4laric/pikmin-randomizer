"""Focused tests for the yakushima P0 import adapter (#150).

All decoded records here are explicitly SYNTHETIC fixtures exercising the
importer boundary (key order, types, counts, inventory mapping). No value
below is claimed as a retail fact; actual user/Abe/stages.txt bytes remain
the recorded missing prerequisite.
"""
import importlib.util
import unittest
from pathlib import Path

ADAPTER = Path(__file__).resolve().parents[2] / "experimental" / "content_lanes" / "p2-overworld-yakushima.py"


def load_adapter():
    spec = importlib.util.spec_from_file_location("p2_overworld_yakushima", ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SYNTHETIC_RECORD = [
    ("name", "yakushima"),
    ("folder", "yakushima"),
    ("abe_folder", "abe_yakushima"),
    ("model", "yakushima_model.mod"),
    ("collision", "yakushima_collision.txt"),
    ("waterbox", "yakushima_water.txt"),
    ("mapcode", "yakushima_mapcode.txt"),
    ("farm", "yakushima_farm.txt"),
    ("route", "yakushima_route.txt"),
    ("start", [1.0, 2.0, 3.0]),
    ("startangle", 90.0),
    ("limit_gens", [{"name": "SYN_GEN", "minimum_day": 1, "maximum_day": 5, "day_limit": 3}]),
    ("loop_gens", []),
    ("cave_otakara", [{"cave_id": "ABCD", "otakara_count": 2, "definition_file": "caveinfo/synth.txt"}]),
    ("ground_otakara_max", 7),
]


class YakushimaAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_adapter()

    def test_well_formed_synthetic_record_decodes(self):
        record = self.mod.decode_course_pairs([list(p) if isinstance(p, list) else p for p in SYNTHETIC_RECORD])
        self.assertEqual(record["name"], "yakushima")
        self.assertEqual(record["start"], [1.0, 2.0, 3.0])
        self.assertEqual(record["ground_otakara_max"], 7)
        self.assertEqual(len(record["limit_gens"]), 1)
        self.assertEqual(record["cave_otakara"][0]["cave_id"], "ABCD")

    def test_lane_identity_constants(self):
        self.assertEqual((self.mod.COURSE_ID, self.mod.LABEL, self.mod.ISSUE), ("yakushima", "Perplexing Pool", 150))
        self.assertEqual(self.mod.SOURCE_PATH, "user/Abe/stages.txt")
        self.assertEqual(len(self.mod.REQUIRED_INVENTORY), 5)

    def test_misordered_keys_rejected_with_exact_expectation(self):
        bad = list(SYNTHETIC_RECORD)
        bad[0], bad[1] = bad[1], bad[0]
        with self.assertRaises(self.mod.CourseDecodeError) as ctx:
            self.mod.decode_course_pairs(bad)
        self.assertIn("key order must be", str(ctx.exception))

    def test_missing_key_rejected(self):
        bad = [p for p in SYNTHETIC_RECORD if p[0] != "waterbox"]
        with self.assertRaises(self.mod.CourseDecodeError):
            self.mod.decode_course_pairs(bad)

    def test_non_list_record_rejected(self):
        with self.assertRaises(self.mod.CourseDecodeError):
            self.mod.decode_course_pairs({"name": "yakushima"})

    def test_bad_scalar_types_rejected(self):
        for key, value in (("model", ""), ("collision", "/abs/path.txt"),
                           ("farm", "a/../b.txt"), ("start", [1.0, 2.0]),
                           ("start", [1.0, float("nan"), 3.0]), ("startangle", "north"),
                           ("name", ""), ("ground_otakara_max", -1),
                           ("ground_otakara_max", True)):
            bad = [(k, value if k == key else v) for k, v in SYNTHETIC_RECORD]
            with self.subTest(key=key, value=value):
                with self.assertRaises(self.mod.CourseDecodeError):
                    self.mod.decode_course_pairs(bad)

    def test_bad_schedule_rows_rejected(self):
        base = dict(SYNTHETIC_RECORD)
        for row in ({"name": "", "minimum_day": 1, "maximum_day": 2, "day_limit": 0},
                    {"name": "G", "minimum_day": 5, "maximum_day": 2, "day_limit": 0},
                    {"name": "G", "minimum_day": -1, "maximum_day": 2, "day_limit": 0},
                    {"name": "G", "minimum_day": 1, "maximum_day": 2},
                    {"name": "G", "minimum_day": 1, "maximum_day": 2, "day_limit": 0, "extra": 1}):
            bad = [(k, [row] if k == "limit_gens" else v) for k, v in SYNTHETIC_RECORD]
            with self.subTest(row=row):
                with self.assertRaises(self.mod.CourseDecodeError):
                    self.mod.decode_course_pairs(bad)
        _ = base

    def test_bad_cave_rows_rejected(self):
        for row in ({"cave_id": "ABC", "otakara_count": 1, "definition_file": "c.txt"},
                    {"cave_id": "ABCDE", "otakara_count": 1, "definition_file": "c.txt"},
                    {"cave_id": "ABCD", "otakara_count": -1, "definition_file": "c.txt"},
                    {"cave_id": "ABCD", "otakara_count": 1, "definition_file": "c.bin"},
                    {"cave_id": "ABCD", "otakara_count": 1}):
            bad = [(k, [row] if k == "cave_otakara" else v) for k, v in SYNTHETIC_RECORD]
            with self.subTest(row=row):
                with self.assertRaises(self.mod.CourseDecodeError):
                    self.mod.decode_course_pairs(bad)

    def test_closure_covers_all_required_inventory(self):
        record = self.mod.decode_course_pairs(list(SYNTHETIC_RECORD))
        closure = self.mod.resource_closure(record)
        self.assertEqual(set(closure), set(self.mod.REQUIRED_INVENTORY))
        # No disc staged: record-derived items are honestly missing-source.
        self.assertEqual(closure["terrain/collision/water"]["collision"]["status"], "missing-source")
        # Structures and return anchors have no loader field: unsupported-reference.
        self.assertEqual(closure["Onions/ship/bridges/gates"]["status"], "unsupported-reference")
        self.assertEqual(
            closure["all cave entrances and return anchors"]["return_anchors"]["status"],
            "unsupported-reference",
        )

    def test_closure_with_inventory_marks_presence(self):
        record = self.mod.decode_course_pairs(list(SYNTHETIC_RECORD))
        closure = self.mod.resource_closure(record, {"yakushima_collision.txt"})
        self.assertEqual(closure["terrain/collision/water"]["collision"]["status"], "present")
        self.assertEqual(closure["terrain/collision/water"]["waterbox"]["status"], "missing-source")

    def test_missing_prerequisites_exact(self):
        prereqs = self.mod.missing_prerequisites()
        self.assertEqual(len(prereqs), 3)
        self.assertIn("user/Abe/stages.txt", prereqs[0])
        self.assertIn("SHA-256", prereqs[0])
        for issue in ("#128", "#132", "#146", "#158", "#161"):
            self.assertTrue(any(issue in p for p in prereqs), issue)

    def test_packet_makes_no_playability_claim(self):
        packet = self.mod.implementation_packet(test_log_sha256="0" * 64)
        self.assertEqual(packet["source_sha256"], None)
        self.assertEqual(packet["floors"], 0)
        self.assertIn("no claim of playability", packet["playability"])
        text = str(packet)
        self.assertNotIn("PASS", text)


if __name__ == "__main__":
    unittest.main()
