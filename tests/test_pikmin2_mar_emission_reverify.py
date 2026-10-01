"""Focused unit tests for the mar emission re-verify marker parser (#814)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experimental"))
from pikmin2_mar_emission_reverify import check_markers


class MarkerTests(unittest.TestCase):
    def test_pass_with_bound_pellet(self):
        text = ("P2_MAR_CORPSE_EMITTED_OBSERVED generator=375001 source_id=29 pellet=0x1a2b3c\n"
                "P2_MAR_CORPSE_RECEIPT_RESOLVED generator=375001 source_id=29\n"
                "PASS P2_MAR_CORPSE_EMISSION corpse=1 receipt=1 injected=0\n")
        facts = check_markers(text)
        self.assertTrue(facts["pass_marker"])
        self.assertTrue(facts["emitted"])
        self.assertTrue(facts["pellet_bound"])
        self.assertTrue(facts["receipt"])
        self.assertFalse(facts["captain_down"])
        self.assertIsNone(facts["fail"])

    def test_no_corpse_failure_mode(self):
        text = ("P2_MAR_CORPSE_OBSERVED_DEAD generator=375001 min_health=0.0\n"
                "P2_MAR_CORPSE_WAIT tick=3600 corpse=0\n"
                "FAIL P2_MAR_CORPSE no_corpse_pellet\n")
        facts = check_markers(text)
        self.assertFalse(facts["pass_marker"])
        self.assertFalse(facts["emitted"])
        self.assertFalse(facts["pellet_bound"])
        self.assertEqual(facts["fail"], "no_corpse_pellet")

    def test_nil_pellet_is_not_bound(self):
        text = "P2_MAR_CORPSE_EMITTED_OBSERVED generator=375001 source_id=29 pellet=(nil)\n"
        facts = check_markers(text)
        self.assertTrue(facts["emitted"])
        self.assertFalse(facts["pellet_bound"])

    def test_captain_down_flagged(self):
        text = ("P2_FIXTURE_CAPTAIN_DOWN tick=12 hp=0.000 orima_dead=0 "
                "dead_state=1 outcome=BLOCKED\n")
        facts = check_markers(text)
        self.assertTrue(facts["captain_down"])

    def test_guard_hash_constant(self):
        import pikmin2_mar_emission_reverify as driver
        self.assertEqual(driver.GUARD_SHA256,
                         "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474")


if __name__ == "__main__":
    unittest.main()
