"""Tests for the #167 landing checker (#759): synthetic verdicts + live re-verification."""
import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

landing = importlib.import_module("experimental.pikmin2_jigumo_throughput_run_landing")


class TestLanding(unittest.TestCase):
    def test_expected_hashes_pinned(self):
        self.assertEqual(len(landing.EXPECTED), 3)
        for name, digest in landing.EXPECTED.items():
            self.assertRegex(digest, "^[0-9a-f]{64}$", name)

    def test_run_pins_complete(self):
        pins = landing.RUN_PINS
        self.assertRegex(pins["native_head"], "^[0-9a-f]{40}$")
        self.assertEqual(len(pins["root_commits"]), 5)
        for commit in pins["root_commits"]:
            self.assertRegex(commit, "^[0-9a-f]{40}$")
        self.assertEqual(pins["observer_tests"], 14)

    def test_live_hashes_match(self):
        report = landing.reverify()
        self.assertTrue(report["all_match"], report)
        for name in ("native.log", "result.json", "fixture.exe"):
            self.assertTrue(report[name]["match"], name)

    def test_live_verdict_intact(self):
        verdict = landing.validate_run()
        self.assertTrue(verdict["dead"])
        self.assertTrue(verdict["carcass"])
        self.assertGreater(verdict["ratio"], 25.0)
        self.assertFalse(verdict["captain_down"])
        self.assertEqual(verdict["injected"], [])
        self.assertTrue(verdict["passed"])
        self.assertTrue(verdict["evidence_intact"])


if __name__ == "__main__":
    unittest.main()
