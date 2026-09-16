"""Focused P0 tests for the Awakening Wood import adapter (#149).

Uses synthetic stages.txt text only; no retail assets are read and no
placements are emitted. Covers the happy path, malformed/missing inputs,
the no-invention boundary and manifest validation.
"""
import json
import importlib.util
import unittest
from pathlib import Path


def _load_adapter():
    path = Path(__file__).resolve().parents[2] / "experimental" / "content_lanes" / "p2-overworld-forest.py"
    spec = importlib.util.spec_from_file_location("p2_overworld_forest_adapter", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


forest = _load_adapter()


GOOD = """1
{
name forest
start 0 0 0
end
0
0
2
{ f_01 } 3 cave_forest_1.txt
{ f_02 } 5 cave_forest_2.txt
7
}
"""

TWO_COURSES = """2
{
name tutorial
start 0 0 0
end
0
0
1
{ t_01 } 2 cave_tutorial_1.txt
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


class ForestAdapterTests(unittest.TestCase):
    def test_decode_filters_forest_and_preserves_order(self):
        links = forest.decode_forest(TWO_COURSES)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["course_id"], "forest")
        self.assertEqual(links[0]["cave_tag"], "f_01")
        self.assertEqual(links[0]["source_path"],
                         "user/Mukki/mapunits/caveinfo/cave_forest_1.txt")

    def test_decode_two_caves_sorted(self):
        links = forest.decode_forest(GOOD)
        self.assertEqual([link["cave_tag"] for link in links], ["f_01", "f_02"])
        self.assertEqual([link["cave_table_index"] for link in links], [0, 1])

    def test_missing_forest_fails_closed(self):
        text = TWO_COURSES.replace("name forest", "name yakushima")
        with self.assertRaisesRegex(ValueError, "forest course missing"):
            forest.decode_forest(text)

    def test_missing_or_empty_input_fails(self):
        for bad in (None, "", "   ", 123, b"bytes"):
            with self.assertRaises(ValueError):
                forest.decode_forest(bad)

    def test_malformed_table_fails(self):
        with self.assertRaises(ValueError):
            forest.decode_forest("not a stage table")
        # Declared count disagrees with blocks.
        with self.assertRaises(ValueError):
            forest.decode_forest(GOOD.replace("1\n{", "2\n{", 1))

    def test_duplicate_tag_rejected_by_parser(self):
        dup = GOOD.replace("{ f_02 }", "{ f_01 }")
        with self.assertRaisesRegex(ValueError, "Duplicate cave tag"):
            forest.decode_forest(dup)

    def test_manifest_marks_unplayable_and_lists_closure(self):
        manifest = forest.build_manifest(GOOD, "a" * 64)
        self.assertFalse(manifest["playable"])
        self.assertEqual(manifest["cave_count"], 2)
        self.assertEqual(manifest["stages_sha256"], "a" * 64)
        paths = [row["path"] for row in manifest["resource_closure"]]
        self.assertEqual(paths[0], "user/Abe/stages.txt")
        self.assertIn("user/Mukki/mapunits/caveinfo/cave_forest_1.txt", paths)
        self.assertEqual([row["item"] for row in manifest["required_inventory"]],
                         list(forest.REQUIRED_INVENTORY))
        # No runtime placements emitted anywhere (policy text aside).
        self.assertNotIn('"placement":', json.dumps(manifest))
        self.assertNotIn("placement_status", json.dumps(manifest))
        self.assertTrue(forest.validate_manifest(manifest))

    def test_manifest_rejects_bad_hash_and_count(self):
        with self.assertRaises(ValueError):
            forest.build_manifest(GOOD, "short")
        manifest = forest.build_manifest(GOOD)
        manifest["cave_count"] = 99
        with self.assertRaisesRegex(ValueError, "cave_count"):
            forest.validate_manifest(manifest)
        manifest = forest.build_manifest(GOOD)
        manifest["playable"] = True
        with self.assertRaisesRegex(ValueError, "playability"):
            forest.validate_manifest(manifest)

    def test_missing_prerequisite_is_exact(self):
        text = forest.missing_prerequisite()
        self.assertIn("user/Abe/stages.txt", text)
        self.assertIn("GPVE01", text)

    def test_sha256_helper_rejects_non_bytes(self):
        with self.assertRaises(ValueError):
            forest.sha256_bytes("not-bytes")
        self.assertEqual(len(forest.sha256_bytes(b"abc")), 64)


if __name__ == "__main__":
    unittest.main()

class RealSourceTests(unittest.TestCase):
    """Real-bytes path against the supported local ISO (no synthetic data)."""

    ISO = Path("C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso")
    PIN_SHA = "4de9008c99e799b99b2746c0156846eeb7ad50895ad110fc7f2070db6de1fff8"
    PIN_BYTES = 3275
    PIN_TAGS = ["f_01", "f_02", "f_03", "f_04", "test"]

    @classmethod
    def setUpClass(cls):
        found = forest.locate_source(cls.ISO)
        if not found["available"]:
            raise unittest.SkipTest(found["prerequisite"])
        from experimental.pikmin2_assets import disc_files
        catalog = disc_files(cls.ISO)
        at, size = catalog["user/Abe/stages.txt"]
        with cls.ISO.open("rb") as handle:
            handle.seek(at)
            cls.raw = handle.read(size)
        cls.packet = forest.build_manifest(
            cls.raw.decode("shift_jis"), forest.sha256_bytes(cls.raw))

    def test_source_hash_and_size_pinned(self):
        self.assertEqual(len(self.raw), self.PIN_BYTES)
        self.assertEqual(forest.sha256_bytes(self.raw), self.PIN_SHA)
        self.assertEqual(self.packet["stages_sha256"], self.PIN_SHA)

    def test_five_forest_caves_in_order(self):
        tags = [link["cave_tag"] for link in self.packet["cave_links"]]
        self.assertEqual(tags, self.PIN_TAGS)
        self.assertEqual(self.packet["cave_count"], 5)
        self.assertTrue(forest.validate_manifest(self.packet))

    def test_closure_lists_cave_definitions(self):
        paths = [row["path"] for row in self.packet["resource_closure"]]
        self.assertEqual(paths[0], "user/Abe/stages.txt")
        for name in ("forest_1.txt", "forest_4.txt"):
            self.assertTrue(any(name in p for p in paths), name)

    def test_decode_source_file_helper(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "stages.txt"
            target.write_bytes(self.raw)
            packet = forest.decode_source_file(target)
            self.assertEqual(packet["stages_sha256"], self.PIN_SHA)
            self.assertEqual(packet["cave_count"], 5)

    def test_decode_source_file_missing_raises(self):
        with self.assertRaises((OSError, ValueError)):
            forest.decode_source_file(Path("C:/nonexistent/stages.txt"))

    def test_locate_source_reports_prerequisite(self):
        found = forest.locate_source(Path("C:/nonexistent/pikmin2.iso"))
        self.assertFalse(found["available"])
        self.assertIn("user/Abe/stages.txt", found["prerequisite"])
