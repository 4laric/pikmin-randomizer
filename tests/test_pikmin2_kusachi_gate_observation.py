"""Focused fail-closed tests for the kusachi gate observation adapter (#818)."""
import json
import tempfile
import unittest
from pathlib import Path

import importlib.util

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "pikmin2_kusachi_gate_observation",
    ROOT / "experimental" / "pikmin2_kusachi_gate_observation.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)

PASS_LOG = "\n".join([
    "P2_KUSACHI_CONTENT_WIRING_SELFTEST_PASS rows=7",
    "P2_CHALLENGE_CONTENT_WIRED roster=kusachi",
    "P2_KUSACHI_CONTENT_WIRING_STAGE floor=1",
    "PASS KUSACHI_CONTENT_WIRING observed=1200 wired=4",
    "P2_KUSACHI_SAVE ok", "P2_KUSACHI_RELOAD ok",
    "P2_KUSACHI_RETRY ok", "P2_KUSACHI_REENTRY ok",
])


class ObservationTests(unittest.TestCase):
    def test_pass_log_marks_wiring_and_persistence(self):
        v = adapter.verdict(self._write(PASS_LOG))
        self.assertTrue(v["markers"]["wired"])
        self.assertTrue(v["markers"]["stage"])
        self.assertTrue(v["markers"]["passed"])
        self.assertEqual(v["gates"]["identity_spawn"]["status"], "observed")
        self.assertEqual(v["persistence"]["status"], "observed")
        self.assertIs(v["admit"], False)

    def test_other_gates_stay_untested_on_wiring_only(self):
        v = adapter.verdict(self._write(PASS_LOG))
        for g in ("movement_animation", "attacks_receivers", "death_corpse",
                  "transport_reward", "cleanup_reentry"):
            self.assertEqual(v["gates"][g]["status"], "UNTESTED")

    def test_captain_down_blocks_everything(self):
        v = adapter.verdict(self._write(PASS_LOG + "\nP2_FIXTURE_CAPTAIN_DOWN tick=5 outcome=BLOCKED\n"))
        self.assertTrue(all(s["status"] == "BLOCKED" for s in v["gates"].values()))

    def test_failed_run_blocks_everything(self):
        v = adapter.verdict(self._write("FAIL KUSACHI_CONTENT_WIRING unwired observed=10 wired=0\n"))
        self.assertTrue(all(s["status"] == "BLOCKED" for s in v["gates"].values()))

    def test_incomplete_markers_stay_untested(self):
        v = adapter.verdict(self._write("P2_CHALLENGE_CONTENT_WIRED roster=kusachi\n"))
        self.assertTrue(all(s["status"] == "UNTESTED" for s in v["gates"].values()))
        self.assertEqual(v["persistence"]["status"], "UNTESTED")

    def test_empty_log_is_refused(self):
        with self.assertRaises(adapter.ObservationError):
            adapter.verdict(self._write("   \n"))

    def test_missing_log_is_refused(self):
        with self.assertRaises((FileNotFoundError, OSError)):
            adapter.verdict(Path(tempfile.mkdtemp()) / "nope.log")

    @staticmethod
    def _write(text):
        tmp = Path(tempfile.mkdtemp()) / "run.log"
        tmp.write_text(text, encoding="utf-8")
        return tmp


if __name__ == "__main__":
    unittest.main()
