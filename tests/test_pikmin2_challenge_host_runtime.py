"""Focused tests for experimental/pikmin2_challenge_host_runtime.py.

Covers the run-log verifier truth table: PASS only on ordered bridge
evidence with zero failure markers; anything else is not a pass. No engine,
assets, or display needed.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from experimental.pikmin2_challenge_host_runtime import verify_run_log


class HostRuntimeVerifyTest(unittest.TestCase):
    def test_full_pass(self):
        log = ("P2_CHALLENGE_MODE_BOOT cave=ch_NARI_01kusachi ui_index=3\n"
               "P2CHALLENGE_WIRING_TICK squad_alive=20 squad_reds=0\n"
               "P2_CHALLENGE_MODE_TICK cave=ch_NARI_01kusachi\n"
               "P2_CHALLENGE_MODE_DONE cave=ch_NARI_01kusachi end=timeout\n"
               "PASS CHALLENGE_HOST_RUNTIME observed=600\n")
        result = verify_run_log(log)
        self.assertTrue(result["engine_bridge_boot"])
        self.assertGreater(result["tick_markers"], 0)
        self.assertTrue(result["done_marker"])
        self.assertTrue(result["overall_pass"])
        self.assertEqual(result["failure_markers"], [])

    def test_boot_without_ticks_is_not_pass(self):
        result = verify_run_log("P2_CHALLENGE_MODE_BOOT cave=x\n")
        self.assertTrue(result["engine_bridge_boot"])
        self.assertFalse(result["overall_pass"])

    def test_ticks_without_boot_is_not_pass(self):
        result = verify_run_log("P2CHALLENGE_WIRING_TICK squad_alive=5\n")
        self.assertFalse(result["engine_bridge_boot"])
        self.assertFalse(result["overall_pass"])

    def test_captain_down_blocks_pass(self):
        log = ("P2_CHALLENGE_MODE_BOOT cave=x\n"
               "P2CHALLENGE_WIRING_TICK squad_alive=5\n"
               "P2_FIXTURE_CAPTAIN_DOWN tick=9 outcome=BLOCKED\n")
        result = verify_run_log(log)
        self.assertFalse(result["overall_pass"])
        self.assertIn("P2_FIXTURE_CAPTAIN_DOWN", result["failure_markers"])

    def test_fail_marker_blocks_pass(self):
        log = ("P2_CHALLENGE_MODE_BOOT cave=x\n"
               "P2CHALLENGE_WIRING_TICK squad_alive=5\n"
               "P2_CHALLENGE_MODE_DONE cave=x end=timeout\n"
               "FAIL CHALLENGE_HOST_RUNTIME timeout observed=3\n")
        result = verify_run_log(log)
        self.assertFalse(result["overall_pass"])
        self.assertIn("FAIL CHALLENGE_HOST_RUNTIME", result["failure_markers"])

    def test_empty_log(self):
        result = verify_run_log("")
        self.assertFalse(result["engine_bridge_boot"])
        self.assertEqual(result["tick_markers"], 0)
        self.assertFalse(result["overall_pass"])


if __name__ == "__main__":
    unittest.main()
