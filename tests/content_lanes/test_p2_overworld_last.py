"""Focused P0 tests for the p2-overworld-last import contract (#151).

All retail-shaped inputs below are SYNTHETIC fixtures that exercise the
parser boundary only; they assert no retail fact. The only retail claim
tested is structural: 4 courses with `last` at index 3 (from
`MAX_LEVELS (4)` and the lane plan), enforced against real input when the
legal source is staged.
"""

import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

adapter = importlib.import_module("experimental.content_lanes.p2-overworld-last")

COURSE_BLOCK = """\
name {name}
folder courses/{name}
abe_folder user/Abe/courses/{name}
model {name}.mod
collision {name}.col
waterbox {name}.wbx
mapcode {name}.mpc
farm {name}.frm
route {name}.rte
start 10.0 20.0 30.0
startangle 45.0 deg
2
LimitA 1 10 3
LimitB 5 15 2
1
LoopA 1 30 1
2
caveA1 2 caveA1.txt
caveA2 0 caveA2.txt
7
"""

# SYNTHETIC 4-course fixture: tutorial/forest/yakushima/last.
SYNTHETIC_STAGES = "4\n" + "".join(
    COURSE_BLOCK.format(name=n)
    for n in ("tutorial", "forest", "yakushima", "last")
)


class TestOverworldLastAdapter(unittest.TestCase):
    def test_synthetic_happy_path(self):
        courses = adapter.parse_stages(SYNTHETIC_STAGES)
        self.assertEqual(len(courses), 4)
        course = adapter.select_course(courses, "last")
        self.assertEqual(course.index, 3)
        self.assertEqual(adapter.validate_course(course), [])
        closure = adapter.resource_closure(course)
        self.assertEqual(closure["model"], "courses/last/last.mod")
        self.assertEqual(closure["collision"], "courses/last/last.col")
        self.assertEqual(closure["waterbox"], "courses/last/last.wbx")
        self.assertEqual(closure["mapcode"], "courses/last/last.mpc")
        self.assertEqual(closure["farm"], "courses/last/last.frm")
        self.assertEqual(closure["route"], "user/Abe/courses/last/last.rte")
        manifest = adapter.build_manifest(course, "<synthetic>", "0" * 64)
        self.assertFalse(manifest["placements_emitted"])
        self.assertEqual(manifest["course"], "last")
        self.assertEqual(len(manifest["caves"]), 2)
        self.assertEqual(manifest["ground_otakara_max"], 7)
        for item in adapter.REQUIRED_INVENTORY:
            self.assertIn(item, manifest["required_inventory_coverage"])

    def test_missing_source_reports_prerequisite(self):
        with self.assertRaises(adapter.SourceMissingError) as ctx:
            adapter.load_source_bytes("definitely/not/stages.txt")
        self.assertIn("missing prerequisite", str(ctx.exception))
        self.assertIn("no values are invented", str(ctx.exception))

    def test_empty_file_rejected(self):
        with self.assertRaises(adapter.StagesDecodeError):
            adapter.parse_stages("")

    def test_wrong_course_count_rejected(self):
        import tempfile, os
        one = "1\n" + COURSE_BLOCK.format(name="last")
        fd, path = tempfile.mkstemp(suffix=".txt")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(one)
            with self.assertRaises(adapter.StagesDecodeError) as ctx:
                adapter.decode_course_file(path)
            self.assertIn("expected 4 courses", str(ctx.exception))
        finally:
            os.unlink(path)

    def test_unknown_course_rejected(self):
        courses = adapter.parse_stages(SYNTHETIC_STAGES)
        with self.assertRaises(adapter.StagesDecodeError):
            adapter.select_course(courses, "nowhere")

    def test_keyword_order_enforced(self):
        bad = SYNTHETIC_STAGES.replace("abe_folder", "folder", 1)
        with self.assertRaises(adapter.StagesDecodeError):
            adapter.parse_stages(bad)

    def test_unknown_keyword_rejected(self):
        bad = SYNTHETIC_STAGES.replace("name tutorial", "title tutorial", 1)
        with self.assertRaises(adapter.StagesDecodeError):
            adapter.parse_stages(bad)

    def test_bad_integer_rejected(self):
        bad = SYNTHETIC_STAGES.replace("\n2\ncaveA1", "\nZZ\ncaveA1", 1)
        with self.assertRaises(adapter.StagesDecodeError):
            adapter.parse_stages(bad)

    def test_nonfinite_float_rejected(self):
        bad = SYNTHETIC_STAGES.replace("start 10.0 20.0 30.0",
                                       "start 10.0 nan 30.0", 1)
        with self.assertRaises(adapter.StagesDecodeError):
            adapter.parse_stages(bad)

    def test_truncated_file_rejected(self):
        with self.assertRaises(adapter.StagesDecodeError):
            adapter.parse_stages(SYNTHETIC_STAGES[:200])

    def test_trailing_tokens_rejected(self):
        with self.assertRaises(adapter.StagesDecodeError):
            adapter.parse_stages(SYNTHETIC_STAGES + " junk")

    def test_duplicate_cave_id_flagged(self):
        courses = adapter.parse_stages(SYNTHETIC_STAGES)
        course = adapter.select_course(courses, "last")
        course.caves.append(adapter.CaveRow("caveA1", 1, "dup.txt"))
        defects = adapter.validate_course(course)
        self.assertTrue(any("duplicate cave id" in d for d in defects))

    def test_inverted_day_range_flagged(self):
        courses = adapter.parse_stages(SYNTHETIC_STAGES)
        course = adapter.select_course(courses, "last")
        course.limit_gen[0].minimum_day = 99
        defects = adapter.validate_course(course)
        self.assertTrue(any("inverted" in d for d in defects))

    def test_negative_otakara_flagged(self):
        courses = adapter.parse_stages(SYNTHETIC_STAGES)
        course = adapter.select_course(courses, "last")
        course.ground_otakara_max = -1
        defects = adapter.validate_course(course)
        self.assertTrue(any("ground_otakara_max" in d for d in defects))

    def test_empty_path_flagged(self):
        courses = adapter.parse_stages(SYNTHETIC_STAGES)
        course = adapter.select_course(courses, "last")
        course.paths["model"] = ""
        defects = adapter.validate_course(course)
        self.assertTrue(any("model" in d for d in defects))

    def test_non_utf8_source_rejected(self):
        import tempfile, os
        fd, path = tempfile.mkstemp(suffix=".txt")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(b"\xff\xfe\x00invalid")
            with self.assertRaises(adapter.StagesDecodeError):
                adapter.decode_course_file(path)
        finally:
            os.unlink(path)

    def test_decode_end_to_end_synthetic_file(self):
        import tempfile, os
        fd, path = tempfile.mkstemp(suffix=".txt")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(SYNTHETIC_STAGES)
            course, digest = adapter.decode_course_file(path)
            self.assertEqual(course.name, "last")
            self.assertEqual(len(digest), 64)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
