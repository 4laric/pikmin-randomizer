"""Landing validation tests for the #745 spawn repair (#756).

Synthetic log fixtures plus read-only checks against the pinned evidence
bundle. No engine, no runtime, no ADMIT.
"""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "impact_spawn_repair_landing",
        ROOT / "experimental" / "pikmin2_impact_spawn_repair_landing.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R = _load()

GOOD = """P2_CHALLENGE_PARK_ALIVE pikis=21
P2_CHALLENGE_SQUAD pikis=40
P2_CHALLENGE_BOOT level=0 slot=chal0
PASS P2_CHALLENGE_GUARDED_BOOT boot1 squad_alive
"""


class LogValidationTests(unittest.TestCase):
    def test_good_log_passes(self):
        result = R.validate_log(GOOD)
        self.assertTrue(result["spawn_boot"], result)
        self.assertTrue(result["clean"], result)

    def test_missing_marker_fails(self):
        result = R.validate_log("P2_CHALLENGE_PARK_ALIVE pikis=21\n")
        self.assertFalse(result["spawn_boot"])
        self.assertIn("SQUAD", result["reason"])

    def test_captain_down_rejected(self):
        result = R.validate_log(GOOD + "P2_FIXTURE_CAPTAIN_DOWN tick=9\n")
        self.assertFalse(result["spawn_boot"])
        self.assertFalse(result["clean"])

    def test_extinction_rejected(self):
        self.assertFalse(R.validate_log(GOOD + "GAMEEND_PikminExtinction\n")["clean"])

    def test_empty_log_fails(self):
        self.assertFalse(R.validate_log("")["spawn_boot"])


class PinnedEvidenceTests(unittest.TestCase):
    def test_pins_match_745_report(self):
        self.assertEqual(R.NATIVE_COMMIT, "2e54daf994a408e469e39e3a4b2b7b2e420d5f2a")
        self.assertEqual(R.ROOT_COMMIT, "49f3ba3a6012550ce53c250ce710b85313a547d4")
        self.assertEqual(R.EXE_SHA256,
                         "3d5fe18a5b6398019017ae58017f1bffb9bdb91c76ab2b71de38d9d9d3ec21a3")
        self.assertEqual(R.LOG_SHA256,
                         "2ce41e11f88812bb016b97e7114ca0ec03a8976132395a4bab1d4629fd0df145")

    def test_live_bundle_verifies(self):
        result = R.verify()
        self.assertTrue(result["verified"], result)
        self.assertTrue(result["spawn_boot"])


if __name__ == "__main__":
    unittest.main()
