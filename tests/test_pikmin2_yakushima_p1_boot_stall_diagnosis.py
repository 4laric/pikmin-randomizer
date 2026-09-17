"""Focused tests for experimental/pikmin2_yakushima_p1_boot_stall_diagnosis.py.

Verifies the #717 evidence bundle (real lane out/ dir) plus fail-closed
negatives on tampered copies. No engine, build, or display needed.
"""
import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from experimental.pikmin2_yakushima_p1_boot_stall_diagnosis import verify_bundle

OUT_DIR = ("C:/Users/alari/pikmin-randomizer/output/workflow/autofill/"
           "prerequisites/yakushima-p1-boot-stall-diagnosis/out")


class DiagnosisEvidenceTest(unittest.TestCase):
    def test_real_bundle_passes(self):
        ok, report, problems = verify_bundle(OUT_DIR)
        self.assertEqual(problems, [])
        self.assertTrue(ok)
        self.assertTrue(report["checks"]["missing_asset_stall"])
        self.assertTrue(report["checks"]["staged_asset_idle"])
        self.assertTrue(report["checks"]["build"])

    def _copied(self, tmp):
        dst = os.path.join(tmp, "out")
        shutil.copytree(OUT_DIR, dst)
        return dst

    def test_removing_timeout_marker_fails(self):
        import tempfile
        tmp = tempfile.mkdtemp(prefix="yak-diag-")
        self.addCleanup(shutil.rmtree, tmp, True)
        dst = self._copied(tmp)
        path = os.path.join(dst, "diagnosis-run-jaudioon.log")
        text = open(path, encoding="utf-8").read().replace(
            "P2_YAKUSHIMA_P1_DIAG_TIMEOUT", "P2_YAKUSHIMA_P1_DIAG_NO_MARKER")
        open(path, "w", encoding="utf-8").write(text)
        ok, _report, problems = verify_bundle(dst)
        self.assertFalse(ok)
        self.assertTrue(any("stall shape" in p for p in problems))

    def test_idle_log_with_captain_down_fails(self):
        import tempfile
        tmp = tempfile.mkdtemp(prefix="yak-diag-")
        self.addCleanup(shutil.rmtree, tmp, True)
        dst = self._copied(tmp)
        path = os.path.join(dst, "diagnosis-run-staged-assets.log")
        with open(path, "a", encoding="utf-8") as f:
            f.write("P2_FIXTURE_CAPTAIN_DOWN tick=9 outcome=BLOCKED\n")
        ok, _report, problems = verify_bundle(dst)
        self.assertFalse(ok)
        self.assertTrue(any("idle-running" in p for p in problems))

    def test_missing_logs_refused(self):
        import tempfile
        tmp = tempfile.mkdtemp(prefix="yak-diag-empty-")
        self.addCleanup(shutil.rmtree, tmp, True)
        ok, _report, problems = verify_bundle(tmp)
        self.assertFalse(ok)
        self.assertTrue(any("missing log" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
