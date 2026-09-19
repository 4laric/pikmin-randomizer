"""Focused tests for the ch_MUKI_redblue P1 runtime observer (#744)."""
import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

observer = importlib.import_module("experimental.pikmin2_muki_redblue_p1_runtime")


def refusal_log():
    return "\n".join([
        "P2_MUKI_REDBLUE_P1_BASELINE red=8 blue=0",
        "P2_MUKI_REDBLUE_P1_WINDOW width=960 height=540 centered_call=1",
        "P2_MUKI_REDBLUE_P1_NAVI_PARKED x=60.0 y=30.0 z=1200.0 guard=p2_fixture_captain_guard sha256=d2f678c9",
        "P2_MUKI_REDBLUE_P1_CONTROL_OK control=chal0 index=0",
        "P2_MUKI_REDBLUE_P1_SELECT_RESOLVED cave=ch_MUKI_redblue source=staged-boot-request selector=#743",
        "BLOCKED P2_MUKI_REDBLUE_P1_BOOT engine-table-row-pending stage=ch_MUKI_redblue missing=#748",
    ]) + "\n"


def boot_log():
    return refusal_log().replace(
        "BLOCKED P2_MUKI_REDBLUE_P1_BOOT engine-table-row-pending stage=ch_MUKI_redblue missing=#748",
        "P2_MUKI_REDBLUE_P1_ROW_RESOLVED stage=ch_MUKI_redblue index=17") + (
        "PASS P2_MUKI_REDBLUE_P1_BOOT stage=ch_MUKI_redblue\n")


class TestObserver(unittest.TestCase):
    def test_refusal_chain_reports_blocked(self):
        v = observer.validate(refusal_log())
        self.assertEqual(v["baseline_red"], 8)
        self.assertTrue(v["window_ok"])
        self.assertTrue(v["control_ok"])
        self.assertTrue(v["select_resolved"])
        self.assertFalse(v["row_resolved"])
        self.assertFalse(v["boot_pass"])
        self.assertTrue(v["row_pending"])
        self.assertFalse(v["captain_down"])
        self.assertEqual(v["injected"], [])
        self.assertFalse(v["passed"])
        self.assertEqual(v["gates"]["boot"], "BLOCKED")
        self.assertEqual(v["gates"]["guard"], "PASS")

    def test_boot_chain_passes(self):
        v = observer.validate(boot_log())
        self.assertTrue(v["row_resolved"])
        self.assertTrue(v["boot_pass"])
        self.assertTrue(v["passed"])
        self.assertEqual(v["gates"]["boot"], "PASS")

    def test_missing_control_fails(self):
        v = observer.validate(refusal_log().replace(
            "P2_MUKI_REDBLUE_P1_CONTROL_OK control=chal0 index=0\n", ""))
        self.assertFalse(v["control_ok"])
        self.assertIn("control-chal0-unresolved", v["failures"])

    def test_captain_down_blocks(self):
        v = observer.validate(refusal_log() + (
            "P2_FIXTURE_CAPTAIN_DOWN tick=9 hp=0.5 orima_dead=0 dead_state=1 outcome=BLOCKED\n"))
        self.assertTrue(v["captain_down"])
        self.assertFalse(v["passed"])

    def test_injected_marker_fails(self):
        v = observer.validate(refusal_log() + "P2_BOMBOTAKARA_INJECT 1 2 staged\n")
        self.assertTrue(v["injected"])
        self.assertFalse(v["passed"])

    def test_boot_request_resolves_redblue(self):
        text = observer.boot_request_text()
        self.assertIn("P2_CHALLENGE_STAGE_SELECT_1", text)
        self.assertIn("cave ch_MUKI_redblue ", text)


if __name__ == "__main__":
    unittest.main()
