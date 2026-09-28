"""Focused tests for experimental/pikmin2_challenge_runtime_bridge_port.py.

Verifies the #722 evidence bundle (real lane out/ dir) plus fail-closed
negatives on tampered copies. No engine, build, or display needed.
"""
import json
import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from experimental.pikmin2_challenge_runtime_bridge_port import verify_bundle

OUT_DIR = ("C:/Users/alari/pikmin-randomizer/output/workflow/autofill/"
           "prerequisites/challenge-runtime-bridge-port-native/out")


class BridgeEvidenceTest(unittest.TestCase):
    def test_real_bundle_passes(self):
        ok, report, problems = verify_bundle(OUT_DIR)
        self.assertEqual(problems, [])
        self.assertTrue(ok)
        self.assertTrue(report["checks"]["build"])
        self.assertTrue(report["checks"]["marker_run"]["boot_marker"])
        self.assertGreater(report["checks"]["marker_run"]["tick_markers"], 0)
        self.assertTrue(report["checks"]["marker_run"]["boot_before_ticks"])

    def _copied(self, tmp):
        dst = os.path.join(tmp, "out")
        shutil.copytree(OUT_DIR, dst)
        return dst

    def test_captain_down_blocks(self):
        import tempfile
        tmp = tempfile.mkdtemp(prefix="bridge-ev-")
        self.addCleanup(shutil.rmtree, tmp, True)
        dst = self._copied(tmp)
        with open(os.path.join(dst, "marker-run.log"), "a",
                  encoding="utf-8") as f:
            f.write("P2_FIXTURE_CAPTAIN_DOWN tick=9 outcome=BLOCKED\n")
        ok, _report, problems = verify_bundle(dst)
        self.assertFalse(ok)
        self.assertTrue(any("tick stream" in p for p in problems))

    def test_missing_boot_blocks(self):
        import tempfile
        tmp = tempfile.mkdtemp(prefix="bridge-ev-")
        self.addCleanup(shutil.rmtree, tmp, True)
        dst = self._copied(tmp)
        path = os.path.join(dst, "marker-run.log")
        text = open(path, encoding="utf-8").read().replace(
            "P2_CHALLENGE_MODE_BOOT", "P2_CHALLENGE_MODE_NO_MARKER")
        open(path, "w", encoding="utf-8").write(text)
        ok, _report, problems = verify_bundle(dst)
        self.assertFalse(ok)
        self.assertTrue(any("tick stream" in p for p in problems))

    def test_missing_record_refused(self):
        import tempfile
        tmp = tempfile.mkdtemp(prefix="bridge-ev-empty-")
        self.addCleanup(shutil.rmtree, tmp, True)
        ok, _report, problems = verify_bundle(tmp)
        self.assertFalse(ok)
        self.assertTrue(any("unreadable build record" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
