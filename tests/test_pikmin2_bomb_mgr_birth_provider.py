"""Provider bomb-mgr-birth tests (issue #616). Hermetic synthetic logs only;
real-source validation runs through the fixture and is logged, not pytest."""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
ADAPTER_PATH = ROOT / "experimental" / "pikmin2_bomb_mgr_birth_provider.py"
_spec = importlib.util.spec_from_file_location("pikmin2_bomb_mgr_birth_provider", ADAPTER_PATH)
adapter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adapter)

LIVE_LOG = """\
P2_BOMB_MGR_BIND generator=41001 source_id=36 visual_only=0
P2_ENEMY_READY species=Bomb native_family=BombMgr generator=41001 x=1.0 y=2.0 z=3.0 health=100.0 behavior=native source_FSM=bomb_wait reward=blast
P2_BOMB_MGR_SETTLE reds_parked=1 captain_staged=1 ready=1
P2_BOMB_MGR_REJECT generator=41001 reason=unregistered
P2_BOMB_MGR_NEGATIVE backed_by=manager reason=unregistered
P2_BOMB_MGR_BIRTH generator=41001 source_id=36 slot=0 generation=1
P2_BOMB_MGR_STAGED carrier=41001 fallback=1
P2_BOMB_MGR_POS generator=41001 x=1.00 y=2.00 z=4.00
P2_BOMB_MGR_POS generator=41001 x=1.50 y=2.00 z=5.00
P2_BOMB_MGR_POS generator=41001 x=2.00 y=2.00 z=6.00
P2_BOMB_MGR_RESET epoch=2
P2_BOMB_MGR_REENTRY reset=1
P2_BOMB_MGR_BIRTH generator=41001 source_id=36 slot=0 generation=1
P2_BOMB_MGR_REBIRTH carrier=41001
P2_BOMB_MGR_POS generator=41001 x=2.50 y=2.00 z=7.00
P2_BOMB_MGR_POS generator=41001 x=3.00 y=2.00 z=8.00
P2_BOMB_MGR_POS generator=41001 x=3.50 y=2.00 z=9.00
P2_BOMB_MGR_DONE carrier=41001 staged_fallback=1
"""


class ParseTests(unittest.TestCase):
    def test_birth_identity(self):
        ok, why = adapter.check_birth(adapter.parse(LIVE_LOG))
        self.assertTrue(ok, why)

    def test_wrong_source_id_rejected(self):
        bad = LIVE_LOG.replace("source_id=36", "source_id=37")
        ok, _ = adapter.check_birth(adapter.parse(bad))
        self.assertFalse(ok)

    def test_follow_needs_three_pos(self):
        short = "\n".join(l for l in LIVE_LOG.splitlines() if "POS" not in l)
        short += "\nP2_BOMB_MGR_POS generator=41001 x=1.00 y=2.00 z=3.00\n"
        ok, _ = adapter.check_follow(adapter.parse(short))
        self.assertFalse(ok)

    def test_nan_pos_fails(self):
        bad = LIVE_LOG.replace("x=2.00 y=2.00 z=6.00", "x=nan y=2.00 z=6.00")
        parsed = adapter.parse(bad)
        ok, _ = adapter.check_follow(parsed)
        self.assertFalse(ok)
        self.assertTrue(parsed["has_nan"])

    def test_reentry_same_carrier(self):
        ok, why = adapter.check_reentry(adapter.parse(LIVE_LOG))
        self.assertTrue(ok, why)

    def test_reentry_without_reset_fails(self):
        no_reset = "\n".join(l for l in LIVE_LOG.splitlines()
                             if "RESET" not in l and "REENTRY" not in l)
        ok, _ = adapter.check_reentry(adapter.parse(no_reset))
        self.assertFalse(ok)

    def test_rebirth_on_never_born_fails(self):
        extra = LIVE_LOG + "P2_BOMB_MGR_REBIRTH carrier=99999\n"
        ok, _ = adapter.check_reentry(adapter.parse(extra))
        self.assertFalse(ok)

    def test_unregistered_rejection(self):
        ok, why = adapter.check_rejection(adapter.parse(LIVE_LOG))
        self.assertTrue(ok, why)

    def test_missing_rejection_fails(self):
        no_reject = "\n".join(l for l in LIVE_LOG.splitlines() if "REJECT" not in l)
        ok, _ = adapter.check_rejection(adapter.parse(no_reject))
        self.assertFalse(ok)

    def test_unittest_summary(self):
        log = LIVE_LOG + "P2_BOMB_MGR_UNITTEST checks=49 failures=0\n"
        ok, why = adapter.check_unittest(adapter.parse(log))
        self.assertTrue(ok, why)

    def test_unittest_failures_rejected(self):
        log = LIVE_LOG + "P2_BOMB_MGR_UNITTEST checks=49 failures=1\n"
        ok, _ = adapter.check_unittest(adapter.parse(log))
        self.assertFalse(ok)

    def test_captain_down_flagged(self):
        bad = LIVE_LOG + "P2_FIXTURE_CAPTAIN_DOWN tick=5 outcome=BLOCKED\n"
        status = adapter.gate_status(bad)
        self.assertFalse(status["captain_guard"][0])

    def test_gate_table_honest(self):
        status = adapter.gate_status(
            LIVE_LOG + "P2_BOMB_MGR_UNITTEST checks=49 failures=0\n")
        self.assertEqual(status["identity_spawn"][0], "PASS")
        self.assertEqual(status["cleanup_reentry"][0], "PASS")
        self.assertEqual(status["transport_reward"][0], "N/A")
        for gate in ("movement_animation", "attacks_receivers", "death_corpse"):
            self.assertEqual(status[gate][0], "UNTESTED", gate)
        self.assertTrue(status["no_nan"][0])
        self.assertTrue(status["captain_guard"][0])

    def test_empty_log_untested(self):
        status = adapter.gate_status("")
        self.assertEqual(status["identity_spawn"][0], "UNTESTED")
        self.assertEqual(status["cleanup_reentry"][0], "UNTESTED")

    def test_source_id_constant(self):
        self.assertEqual(adapter.SOURCE_ID, 36)


if __name__ == "__main__":
    unittest.main()
