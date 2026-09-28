"""Focused tests for experimental/pikmin2_kusachi_content_engine_wiring.py.

Covers the wiring-log verifier truth table: PASS only on a positive bound
count with zero failure markers; anything else is not a pass. No engine,
assets, or display needed.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from experimental.pikmin2_kusachi_content_engine_wiring import verify_run_log


class WiringVerifyTest(unittest.TestCase):
    def test_full_pass(self):
        log = ("P2_CHALLENGE_CONTENT_WIRED wired=20 total=20 target_color=0\n"
               "PASS KUSACHI_CONTENT_WIRING observed=120 wired=20\n")
        result = verify_run_log(log)
        self.assertEqual(result["content_wired"], 20)
        self.assertTrue(result["overall_pass"])
        self.assertEqual(result["failure_markers"], [])

    def test_zero_wired_is_not_pass(self):
        log = ("P2_CHALLENGE_CONTENT_WIRED wired=0 total=20 target_color=0\n"
               "FAIL KUSACHI_CONTENT_WIRING unwired observed=600 wired=0\n")
        result = verify_run_log(log)
        self.assertEqual(result["content_wired"], 0)
        self.assertFalse(result["overall_pass"])

    def test_no_wired_line_is_not_pass(self):
        result = verify_run_log("P2_KUSACHI_CONTENT_WIRING_WAIT observed=3 wired=0\n")
        self.assertEqual(result["content_wired"], 0)
        self.assertFalse(result["overall_pass"])

    def test_captain_down_blocks_pass(self):
        log = ("P2_CHALLENGE_CONTENT_WIRED wired=20 total=20 target_color=0\n"
               "P2_FIXTURE_CAPTAIN_DOWN tick=9 outcome=BLOCKED\n")
        result = verify_run_log(log)
        self.assertFalse(result["overall_pass"])
        self.assertIn("P2_FIXTURE_CAPTAIN_DOWN", result["failure_markers"])

    def test_best_count_wins(self):
        log = ("P2_CHALLENGE_CONTENT_WIRED wired=5 total=20 target_color=0\n"
               "P2_CHALLENGE_CONTENT_WIRED wired=20 total=20 target_color=0\n"
               "PASS KUSACHI_CONTENT_WIRING observed=120 wired=20\n")
        result = verify_run_log(log)
        self.assertEqual(result["content_wired"], 20)
        self.assertTrue(result["overall_pass"])

    def test_empty_log(self):
        result = verify_run_log("")
        self.assertEqual(result["content_wired"], 0)
        self.assertFalse(result["overall_pass"])


if __name__ == "__main__":
    unittest.main()
