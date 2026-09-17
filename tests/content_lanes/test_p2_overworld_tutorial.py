"""Focused P0 tests for the Valley of Repose import adapter (#148).

Synthetic stages.txt texts cover the happy path plus malformed/missing
inputs and manifest validation; a real-bytes class pins the observed retail
bytes (skipped only if the legal ISO is absent). No placements are emitted.
"""
import importlib.util
import unittest
from pathlib import Path


def _load_adapter():
    path = Path(__file__).resolve().parents[2] / "experimental" / "content_lanes" / "p2-overworld-tutorial.py"
    spec = importlib.util.spec_from_file_location("p2_overworld_tutorial_adapter", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tutorial = _load_adapter()


GOOD = """1
{
name tutorial
start 0 0 0
end
0
0
3
{ t_01 } 2 cave_tutorial_1.txt
{ t_02 } 3 cave_tutorial_2.txt
{ t_03 } 4 cave_tutorial_3.txt
11
}
"""

TWO_COURSES = """2
{
name tutorial
start 0 0 0
end
0
0
2
{ t_01 } 2 cave_tutorial_1.txt
{ test } 9 caveinfo.txt
4
}
{
name forest
start 0 0 0
end
0
0
1
{ f_01 } 3 cave_forest_1.txt
7
}
"""


class TutorialAdapterTests(unittest.TestCase):
    def test_decode_filters_tutorial_and_preserves_order(self):
        links = tutorial.decode_tutorial(TWO_COURSES)
        self.assertEqual(len(links), 2)
        self.assertTrue(all(link["course_id"] == "tutorial" for link in links))
        self.assertEqual(links[0]["cave_tag"], "t_01")
        self.assertEqual(links[0]["source_path"],
                         "user/Mukki/mapunits/caveinfo/cave_tutorial_1.txt")

    def test_decode_three_caves_sorted(self):
        links = tutorial.decode_tutorial(GOOD)
        self.assertEqual([link["cave_tag"] for link in links], ["t_01", "t_02", "t_03"])
        self.assertEqual([link["cave_table_index"] for link in links], [0, 1, 2])

    def test_test_row_preserved(self):
        links = tutorial.decode_tutorial(TWO_COURSES)
        test = [link for link in links if link["cave_tag"] == "test"]
        self.assertEqual(len(test), 1)
        self.assertEqual(test[0]["source_path"],
                         "user/Mukki/mapunits/caveinfo/caveinfo.txt")

    def test_missing_tutorial_fails_closed(self):
        text = TWO_COURSES.replace("name tutorial", "name yakushima")
        with self.assertRaisesRegex(ValueError, "tutorial course missing"):
            tutorial.decode_tutorial(text)

    def test_missing_or_empty_input_fails(self):
        for bad in (None, "", "   ", 123, b"bytes"):
            with self.assertRaises(ValueError):
                tutorial.decode_tutorial(bad)

    def test_malformed_table_fails(self):
        with self.assertRaises(ValueError):
            tutorial.decode_tutorial("not a stage table")
        with self.assertRaises(ValueError):
            tutorial.decode_tutorial(GOOD.replace("1\n{", "2\n{", 1))

    def test_duplicate_tag_rejected_by_parser(self):
        dup = GOOD.replace("{ t_02 }", "{ t_01 }")
        with self.assertRaisesRegex(ValueError, "Duplicate cave tag"):
            tutorial.decode_tutorial(dup)

    def test_manifest_marks_unplayable_and_lists_closure(self):
        manifest = tutorial.build_manifest(GOOD, "b" * 64)
        self.assertFalse(manifest["playable"])
        self.assertEqual(manifest["cave_count"], 3)
        self.assertEqual(manifest["stages_sha256"], "b" * 64)
        self.assertEqual(manifest["lane"], "p2-overworld-tutorial")
        self.assertEqual(manifest["issue"], 148)
        paths = [row["path"] for row in manifest["resource_closure"]]
        self.assertEqual(paths[0], "user/Abe/stages.txt")
        self.assertIn("user/Mukki/mapunits/caveinfo/cave_tutorial_1.txt", paths)
        self.assertEqual([row["item"] for row in manifest["required_inventory"]],
                         list(tutorial.REQUIRED_INVENTORY))
        import json
        self.assertNotIn('"placement":', json.dumps(manifest))
        self.assertNotIn("placement_status", json.dumps(manifest))
        self.assertTrue(tutorial.validate_manifest(manifest))

    def test_manifest_rejects_bad_hash_and_count(self):
        with self.assertRaises(ValueError):
            tutorial.build_manifest(GOOD, "short")
        manifest = tutorial.build_manifest(GOOD)
        manifest["cave_count"] = 99
        with self.assertRaisesRegex(ValueError, "cave_count"):
            tutorial.validate_manifest(manifest)
        manifest = tutorial.build_manifest(GOOD)
        manifest["playable"] = True
        with self.assertRaisesRegex(ValueError, "playability"):
            tutorial.validate_manifest(manifest)

    def test_missing_prerequisite_is_exact(self):
        text = tutorial.missing_prerequisite()
        self.assertIn("user/Abe/stages.txt", text)
        self.assertIn("GPVE01", text)

    def test_sha256_helper_rejects_non_bytes(self):
        with self.assertRaises(ValueError):
            tutorial.sha256_bytes("not-bytes")
        self.assertEqual(len(tutorial.sha256_bytes(b"abc")), 64)


class RealSourceTests(unittest.TestCase):
    """Real-bytes path against the supported local ISO (no synthetic data)."""

    ISO = Path("C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso")
    PIN_SHA = "4de9008c99e799b99b2746c0156846eeb7ad50895ad110fc7f2070db6de1fff8"
    PIN_BYTES = 3275
    PIN_TAGS = ["t_01", "t_02", "t_03", "test"]

    @classmethod
    def setUpClass(cls):
        found = tutorial.locate_source(cls.ISO)
        if not found["available"]:
            raise unittest.SkipTest(found["prerequisite"])
        from experimental.pikmin2_assets import disc_files
        catalog = disc_files(cls.ISO)
        at, size = catalog["user/Abe/stages.txt"]
        with cls.ISO.open("rb") as handle:
            handle.seek(at)
            cls.raw = handle.read(size)
        cls.packet = tutorial.build_manifest(
            cls.raw.decode("shift_jis"), tutorial.sha256_bytes(cls.raw))

    def test_source_hash_and_size_pinned(self):
        self.assertEqual(len(self.raw), self.PIN_BYTES)
        self.assertEqual(tutorial.sha256_bytes(self.raw), self.PIN_SHA)
        self.assertEqual(self.packet["stages_sha256"], self.PIN_SHA)

    def test_four_tutorial_rows_in_order(self):
        tags = [link["cave_tag"] for link in self.packet["cave_links"]]
        self.assertEqual(tags, self.PIN_TAGS)
        self.assertEqual(self.packet["cave_count"], 4)
        self.assertTrue(tutorial.validate_manifest(self.packet))

    def test_closure_lists_cave_definitions(self):
        paths = [row["path"] for row in self.packet["resource_closure"]]
        self.assertEqual(paths[0], "user/Abe/stages.txt")
        for name in ("tutorial_1.txt", "tutorial_3.txt", "caveinfo.txt"):
            self.assertTrue(any(name in p for p in paths), name)

    def test_decode_source_file_helper(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "stages.txt"
            target.write_bytes(self.raw)
            packet = tutorial.decode_source_file(target)
            self.assertEqual(packet["stages_sha256"], self.PIN_SHA)
            self.assertEqual(packet["cave_count"], 4)

    def test_decode_source_file_missing_raises(self):
        with self.assertRaises((OSError, ValueError)):
            tutorial.decode_source_file(Path("C:/nonexistent/stages.txt"))

    def test_locate_source_reports_prerequisite(self):
        found = tutorial.locate_source(Path("C:/nonexistent/pikmin2.iso"))
        self.assertFalse(found["available"])
        self.assertIn("user/Abe/stages.txt", found["prerequisite"])


if __name__ == "__main__":
    unittest.main()
