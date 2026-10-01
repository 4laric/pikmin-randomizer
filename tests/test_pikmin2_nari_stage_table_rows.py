"""Tests for the NARI row checker (#769): pins + log observer."""
import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

checker = importlib.import_module("experimental.pikmin2_nari_stage_table_rows")


def good_log():
    return "\n".join([
        "P2_NARI_STAGE_RESOLVED cave=ch_NARI_02tile ui_index=4 floors=2",
        "P2_NARI_STAGE_BOOT_POP cave=ch_NARI_02tile pops=50",
        "P2_NARI_STAGE_TICK cave=ch_NARI_02tile tick=0",
        "P2_NARI_STAGE_RESOLVED cave=ch_NARI_03toy ui_index=5 floors=2",
        "P2_NARI_STAGE_BOOT_POP cave=ch_NARI_03toy pops=100",
        "P2_NARI_STAGE_TICK cave=ch_NARI_03toy tick=0",
        "P2_NARI_STAGE_TABLE_DONE stages=2",
    ]) + "\n"


class TestChecker(unittest.TestCase):
    def test_pins_match_live_decode(self):
        self.assertEqual(checker.EXPECTED["ch_NARI_02tile"]["ui_index"], 4)
        self.assertEqual(checker.EXPECTED["ch_NARI_02tile"]["table_order"], 19)
        self.assertEqual(checker.EXPECTED["ch_NARI_02tile"]["boot_pops"], 50)
        self.assertEqual(checker.EXPECTED["ch_NARI_03toy"]["ui_index"], 5)
        self.assertEqual(checker.EXPECTED["ch_NARI_03toy"]["table_order"], 2)
        self.assertEqual(checker.EXPECTED["ch_NARI_03toy"]["boot_pops"], 100)
        self.assertEqual(sum(sum(r) for r in checker.EXPECTED["ch_NARI_03toy"]["roster"]), 100)

    def test_check_pins_accepts_expected(self):
        rows = {k: dict(v) for k, v in checker.EXPECTED.items()}
        self.assertEqual(checker.check_pins(rows), [])

    def test_check_pins_rejects_drift(self):
        rows = {k: dict(v) for k, v in checker.EXPECTED.items()}
        rows["ch_NARI_03toy"] = dict(rows["ch_NARI_03toy"], ui_index=6)
        self.assertIn("drift ch_NARI_03toy.ui_index", checker.check_pins(rows))

    def test_good_log_passes(self):
        v = checker.validate_log(good_log())
        self.assertTrue(v["passed"], v["failures"])
        self.assertEqual(v["done"], 2)

    def test_error_fails(self):
        v = checker.validate_log(good_log() + "P2_NARI_STAGE_ERROR missing_stage ui=999\n")
        self.assertFalse(v["passed"])

    def test_captain_down_fails(self):
        v = checker.validate_log(good_log() + "P2_FIXTURE_CAPTAIN_DOWN tick=1\n")
        self.assertTrue(v["captain_down"])
        self.assertFalse(v["passed"])


if __name__ == "__main__":
    unittest.main()
