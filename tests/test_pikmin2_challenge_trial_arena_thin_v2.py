"""Focused fail-closed tests for the trial-arena thin-v2 feasibility gate (#792)."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import p1_challenge_trial_arena_thin_v2 as thin


RETAIL = b"1.0v\x00\x00oo_l1\x00\x00PikiHead\x00PikiHeadItem\x00" + b"\x00" * 16


class TrialArenaThinTests(unittest.TestCase):
    def test_classify_binary(self):
        self.assertEqual(thin.classify_gen_bytes(RETAIL), "retail-binary")

    def test_classify_empty_refused(self):
        with self.assertRaises(thin.ThinError):
            thin.classify_gen_bytes(b"")

    def test_plan_retail_binary_blocked(self):
        plan = thin.thinning_plan(RETAIL, observed_me=100)
        self.assertFalse(plan["feasible"])
        self.assertEqual(plan["blocker"], "retail-binary-gen-needs-provider")
        self.assertIn("provider", plan["owner"])

    def test_plan_cap_math(self):
        plan = thin.thinning_plan(RETAIL, cap=100, observed_me=100, squad=20)
        self.assertEqual(plan["headroom"], 0)
        self.assertEqual(plan["required_reduction"], 20)
        plan2 = thin.thinning_plan(RETAIL, cap=100, observed_me=95, squad=20)
        self.assertEqual(plan2["required_reduction"], 15)

    def test_plan_text_unknown_blocked(self):
        plan = thin.thinning_plan(b"some text generators\n")
        self.assertFalse(plan["feasible"])
        self.assertEqual(plan["blocker"], "unrecognized-gen-format")

    def test_assess_retail_arena_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in thin.RETAIL_GENS:
                (Path(tmp) / name).write_bytes(RETAIL)
            record = thin.assess(tmp)
        self.assertEqual(record["verdict"], "blocked")
        self.assertFalse(record["feasible"])
        self.assertIn("owner B", record["owner"])
        self.assertEqual(len(record["generators"]), 2)

    def test_assess_missing_gen_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(thin.ThinError):
                thin.assess(tmp)

    def test_main_exits_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in thin.RETAIL_GENS:
                (Path(tmp) / name).write_bytes(RETAIL)
            self.assertEqual(thin.main(["--gen-dir", tmp]), 3)


class ThinArenaStagingTests(unittest.TestCase):
    CHAL4 = Path("C:/Users/alari/pikmin-randomizer/output/workflow/autofill/planning-shards/p1-challenge/prepared/p1-challenge-trial-runtime-acceptance-output/run-chal4/assets/dataDir/stages/chal4")

    @classmethod
    def setUpClass(cls):
        try:
            cls.tool = thin.load_thin_tool()
        except thin.ThinError as exc:
            raise unittest.SkipTest("thinning tool unreadable: %s" % exc)

    def test_tool_pin(self):
        self.assertEqual(thin.THIN_TOOL_COMMIT, "72149cbea61d5dbb203ba84825369a5836c5b46a")

    def test_assess_retail_buried(self):
        data = (self.CHAL4 / "default.gen").read_bytes()
        report = self.tool.assess(data)
        self.assertEqual(report["buried_total"], 100)

    def test_thin_reduces_buried(self):
        data = (self.CHAL4 / "default.gen").read_bytes()
        out, packet = self.tool.thin(data, cap=100, squad=20)
        self.assertLessEqual(packet["buried_after"], 80)
        self.assertTrue(packet["removed"])

    def test_stage_and_package(self):
        retail = self.CHAL4.parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            arena, manifest = thin.stage_thinned_arena(self.tool, retail, tmp)
            dest = arena / "dataDir/stages/chal4/default.gen"
            self.assertTrue(dest.is_file())
            self.assertFalse(dest.is_symlink())
            self.assertLessEqual(manifest["gens"]["default.gen"]["buried_after"], 80)
            package = thin.build_thin_package(tmp, manifest)
            self.assertTrue(package.is_file())


if __name__ == "__main__":
    unittest.main()
