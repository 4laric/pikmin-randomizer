"""Focused tests for experimental/pikmin2_impact_gating_fix.py.

Covers the run-log verifier truth table: attributed stall and squad spawn
both pass; silent freeze and captain-down never pass. No engine, assets, or
display needed.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from experimental.pikmin2_impact_gating_fix import verify_run_log


class GatingFixVerifyTest(unittest.TestCase):
    def test_attributed_stall_passes(self):
        log = ("P2_CHALLENGE_PARK nx=1.0 ny=0.0 nz=2.0\n"
               "P2_CHALLENGE_PARK_ALIVE pikis=0\n"
               "P2_CHALLENGE_GATE_DIAG gate=movie observed=5 alive=0 frames=600\n"
               "P2_CHALLENGE_GATE_DIAG gate=movie observed=5 alive=0 frames=900\n")
        result = verify_run_log(log)
        self.assertEqual(result["gate_diagnostics"], ["movie"])
        self.assertEqual(result["park_alive"], 0)
        self.assertTrue(result["attributed_stall"])
        self.assertFalse(result["squad_spawned"])
        self.assertTrue(result["overall_pass"])
        self.assertEqual(result["failure_markers"], [])

    def test_squad_spawn_passes(self):
        log = ("P2_CHALLENGE_PARK_ALIVE pikis=0\n"
               "P2_CHALLENGE_SQUAD pikis=20\n"
               "P2_CHALLENGE_BOOT level=0 slot=chal0\n"
               "PASS P2_CHALLENGE_GUARDED_BOOT boot1 squad_alive\n")
        result = verify_run_log(log)
        self.assertTrue(result["squad_spawned"])
        self.assertTrue(result["overall_pass"])

    def test_silent_freeze_fails(self):
        log = ("P2_CHALLENGE_PARK nx=1.0 ny=0.0 nz=2.0\n"
               "P2_CHALLENGE_PARK_ALIVE pikis=0\n")
        result = verify_run_log(log)
        self.assertFalse(result["attributed_stall"])
        self.assertFalse(result["squad_spawned"])
        self.assertFalse(result["overall_pass"])

    def test_empty_log_fails(self):
        result = verify_run_log("")
        self.assertFalse(result["overall_pass"])
        self.assertEqual(result["gate_diagnostics"], [])

    def test_captain_down_blocks_pass(self):
        log = ("P2_CHALLENGE_GATE_DIAG gate=navi observed=5 alive=0 frames=600\n"
               "P2_FIXTURE_CAPTAIN_DOWN tick=9 outcome=BLOCKED\n")
        result = verify_run_log(log)
        self.assertFalse(result["overall_pass"])
        self.assertIn("P2_FIXTURE_CAPTAIN_DOWN", result["failure_markers"])

    def test_multiple_gates_listed(self):
        log = ("P2_CHALLENGE_GATE_DIAG gate=pause observed=5 alive=3 frames=600\n"
               "P2_CHALLENGE_GATE_DIAG gate=ui observed=5 alive=3 frames=900\n")
        result = verify_run_log(log)
        self.assertEqual(result["gate_diagnostics"], ["pause", "ui"])
        self.assertTrue(result["overall_pass"])


if __name__ == "__main__":
    unittest.main()
