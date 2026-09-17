"""P1 tests for the yakushima surface-session import path (#150).

Synthetic boundary tests cover the strict pairs validator, the real-shape
block decoder (farm-absent), the P1 stager, the boundary verdicts and the
pin-gap paths. A real-bytes class pins the observed retail block. No
runtime run, no playability claim.
"""
import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
ADAPTER_PATH = ROOT / "experimental" / "content_lanes" / "p2-overworld-yakushima.py"
_spec = importlib.util.spec_from_file_location("p2_overworld_yakushima_p1", ADAPTER_PATH)
yaku = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(yaku)


def good_pairs(with_farm=True):
    pairs = [
        ("name", "yakushima"),
        ("folder", "user/Kando/map/yakushima"),
        ("abe_folder", "user/Abe/map/yakushima"),
        ("model", "yakushima.bmd"),
        ("collision", "collision.bin"),
        ("waterbox", "waterbox.txt"),
        ("mapcode", "mapcode.bin"),
    ]
    if with_farm:
        pairs.append(("farm", "farm.txt"))
    pairs += [
        ("route", "route.txt"),
        ("start", [1.0, 2.0, 3.0]),
        ("startangle", 90.0),
        ("limit_gens", [{"name": "0-29.txt", "minimum_day": 0,
                         "maximum_day": 29, "day_limit": 29}]),
        ("loop_gens", []),
        ("cave_otakara", [{"cave_id": "y_01", "otakara_count": 11,
                           "definition_file": "yakushima_1.txt"}]),
        ("ground_otakara_max", 7),
    ]
    return pairs


REAL_BLOCK = """{
\tname\t\tyakushima
\tfolder\t\tuser/Kando/map/yakushima
\tabe_folder\tuser/Abe/map/yakushima
\tmodel\t\tyakushima.bmd
\tcollision\tcollision.bin
\twaterbox\twaterbox.txt
\tmapcode\t\tmapcode.bin
\troute\t\troute.txt
\tstart\t\t-369.326 80.000 974.444
\tstartangle\t99.695
 \tend
\t#
\t#\tLimitGenInfo (nonloop)
\t#
\t6
\t\t0-1.txt\t\t0\t1\t1
\t\t0-29.txt\t0\t29\t29
\t\t0-9.txt\t0\t9\t9
\t\t10-29.txt\t10\t29\t29
\t\t20-29.txt\t20\t29\t29
\t\t3-3.txt\t3\t3\t3
\t#
\t#\tLimitGenInfo (loop)
\t#
\t3
\t\t30-39.txt\t30\t39\t39
\t\t40-49.txt\t40\t49\t49
\t\t50-59.txt\t50\t59\t59
\t#
\t#\tCaveOtakara
\t#
\t5
\t\t{y_01}\t\t11\t\tyakushima_1.txt
\t\t{y_02}\t\t14\t\tyakushima_2.txt
\t\t{y_03}\t\t14\t\tyakushima_3.txt
\t\t{y_04}\t\t13\t\tyakushima_4.txt
\t\t{test}\t\t0\t\tcaveinfo.txt
\t#
\t#\tGround Otakara
\t#
\t7
}
"""


class StrictPairsTests(unittest.TestCase):
    def test_strict_pairs_with_farm(self):
        record = yaku.decode_course_pairs(good_pairs())
        self.assertEqual(record["name"], "yakushima")
        self.assertEqual(record["farm"], "farm.txt")

    def test_strict_pairs_rejects_farm_absent(self):
        with self.assertRaises(yaku.CourseDecodeError):
            yaku.decode_course_pairs(good_pairs(with_farm=False))

    def test_strict_pairs_rejects_bad_order(self):
        pairs = good_pairs()
        pairs[0], pairs[1] = pairs[1], pairs[0]
        with self.assertRaises(yaku.CourseDecodeError):
            yaku.decode_course_pairs(pairs)


class BlockDecodeTests(unittest.TestCase):
    def test_real_shape_decodes_without_farm(self):
        record = yaku.decode_course_block(REAL_BLOCK)
        self.assertEqual(record["name"], "yakushima")
        self.assertIsNone(record["farm"])
        self.assertEqual(record["start"], [-369.326, 80.0, 974.444])
        self.assertEqual(len(record["limit_gens"]), 6)
        self.assertEqual(len(record["loop_gens"]), 3)
        self.assertEqual([r["cave_id"] for r in record["cave_otakara"]],
                         ["y_01", "y_02", "y_03", "y_04", "test"])
        self.assertEqual(record["ground_otakara_max"], 7)

    def test_missing_course_rejected(self):
        with self.assertRaises(yaku.CourseDecodeError):
            yaku.decode_course_block(REAL_BLOCK.replace("yakushima", "nowhere", 1))

    def test_unbalanced_rejected(self):
        with self.assertRaises(yaku.CourseDecodeError):
            yaku.decode_course_block("{ name yakushima")

    def test_inverted_days_rejected(self):
        bad = REAL_BLOCK.replace("0-29.txt\t0\t29\t29", "0-29.txt\t29\t0\t29")
        with self.assertRaises(yaku.CourseDecodeError):
            yaku.decode_course_block(bad)


class P1StagingTests(unittest.TestCase):
    def test_stage_and_drive_all_pass(self):
        import tempfile
        record = yaku.decode_course_block(REAL_BLOCK)
        with tempfile.TemporaryDirectory() as tmp:
            staged = yaku.stage_p1_run(record, Path(tmp) / "run")
            self.assertEqual(staged["contract_schema"], "p2-surface-session-1")
            self.assertIn(staged["contract_source"],
                            ("tree", "pin:b08e3bdc2dfb758c0d48e4dab074081a0ee34246"))
            report = yaku.drive_session_boundaries(Path(tmp) / "run")
            for name, result in report["boundaries"].items():
                self.assertEqual(result["verdict"], "pass", name)
            self.assertTrue(report["wake"]["course_record_decoded"])
            self.assertTrue(report["wake"]["cave_entrances_known"])
            for name, result in report["missing_integration"].items():
                self.assertFalse(result["ok"], name)

    def test_stage_rejects_non_yakushima(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(yaku.P1GapError):
                yaku.stage_p1_run({"name": "forest"}, Path(tmp) / "run")

    def test_drive_rejects_unreadable_layout(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(yaku.P1GapError):
                yaku.drive_session_boundaries(Path(tmp) / "empty")

    def test_contract_gap_when_unresolvable(self):
        import unittest.mock as mock
        with mock.patch.dict("sys.modules", {"experimental.pikmin2_surface_session_contract": None}):
            with mock.patch("subprocess.run") as run:
                run.return_value.returncode = 1
                run.return_value.stdout = b""
                with self.assertRaises(yaku.P1GapError):
                    yaku.load_surface_contract()


class RealBytesTests(unittest.TestCase):
    ISO = Path("C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso")
    PIN_SHA = "4de9008c99e799b99b2746c0156846eeb7ad50895ad110fc7f2070db6de1fff8"

    @classmethod
    def setUpClass(cls):
        if not cls.ISO.is_file():
            raise unittest.SkipTest("legal ISO absent")
        from experimental.pikmin2_assets import disc_files
        catalog = disc_files(cls.ISO)
        at, size = catalog["user/Abe/stages.txt"]
        with cls.ISO.open("rb") as handle:
            handle.seek(at)
            cls.raw = handle.read(size)
        cls.text = cls.raw.decode("shift_jis")

    def test_real_block_decodes(self):
        record = yaku.decode_course_block(self.text)
        self.assertEqual(record["name"], "yakushima")
        self.assertIsNone(record["farm"])
        self.assertEqual([r["cave_id"] for r in record["cave_otakara"]][:4],
                         ["y_01", "y_02", "y_03", "y_04"])
        self.assertEqual(yaku.sha256_bytes(self.raw), self.PIN_SHA)

    def test_real_p1_boundaries_pass(self):
        import tempfile
        record = yaku.decode_course_block(self.text)
        with tempfile.TemporaryDirectory() as tmp:
            yaku.stage_p1_run(record, Path(tmp) / "run")
            report = yaku.drive_session_boundaries(Path(tmp) / "run")
            for name, result in report["boundaries"].items():
                self.assertEqual(result["verdict"], "pass", name)


if __name__ == "__main__":
    unittest.main()
