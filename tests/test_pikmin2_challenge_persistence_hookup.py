"""Focused fail-closed tests for the challenge persistence hookup (#713).

Hermetic: synthetic logs and pinned vectors only. Real fixture logs are
validated by the observer lane, not by pytest.
"""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
ADAPTER_PATH = ROOT / "experimental" / "pikmin2_challenge_persistence_hookup.py"
_spec = importlib.util.spec_from_file_location("pikmin2_challenge_persistence_hookup", ADAPTER_PATH)
adapter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adapter)

STAGE = "ch_MAT_route_rover"

GOOD_LOG = """\
P2_CHALLENGE_PERSISTENCE_WINDOW size=960x540 pos=1,2 display=3x4 centered=1
P2_CHALLENGE_SAVE_KEY stage=ch_MAT_route_rover
P2_CHALLENGE_LOAD_KEY stage=ch_MAT_route_rover
P2_CHALLENGE_CLEAR stage=ch_MAT_route_rover
P2_CHALLENGE_HIGHSCORE stage=ch_MAT_route_rover
P2_CHALLENGE_UNLOCK stage=ch_MAT_route_rover
P2_CHALLENGE_RECEIPT_DEDUP stage=ch_MAT_route_rover
P2_CHALLENGE_REENTRY stage=ch_MAT_route_rover
P2_CHALLENGE_PERSISTENCE_RESOLVED stage=ch_MAT_route_rover ui_index=27 markers=7
PASS P2_CHALLENGE_PERSISTENCE_RUN markers=7
"""


class KeyTests(unittest.TestCase):
    def test_route_rover_keys(self):
        self.assertEqual(adapter.stage_keys(STAGE), {
            "save": "p2_challenge_save_ch_MAT_route_rover",
            "load": "p2_challenge_load_ch_MAT_route_rover",
            "clear": "p2_challenge_clear_ch_MAT_route_rover",
            "highscore": "p2_challenge_highscore_ch_MAT_route_rover",
            "unlock": "p2_challenge_unlock_ch_MAT_route_rover",
        })

    def test_kusachi_keys(self):
        keys = adapter.stage_keys("ch_NARI_01kusachi")
        self.assertEqual(keys["save"], "p2_challenge_save_ch_NARI_01kusachi")
        self.assertEqual(keys["unlock"], "p2_challenge_unlock_ch_NARI_01kusachi")

    def test_unknown_characters_rejected(self):
        for bad in ("", "a/b", "a b", "a-b", "../x", None, 42):
            with self.assertRaises(adapter.HookupError):
                adapter.stage_keys(bad)

    def test_marker_shapes(self):
        self.assertEqual(adapter.marker_for("challenge_save_key", STAGE),
                         "P2_CHALLENGE_SAVE_KEY stage=ch_MAT_route_rover")
        self.assertEqual(adapter.marker_for("reentry", STAGE),
                         "P2_CHALLENGE_REENTRY stage=ch_MAT_route_rover")

    def test_unknown_artifact_rejected(self):
        with self.assertRaises(adapter.HookupError):
            adapter.marker_for("challenge_save_typo", STAGE)

    def test_score_vectors(self):
        self.assertEqual(adapter.compute_score(42, 120.5, 15), 690)
        self.assertEqual(adapter.compute_score(0, 0.0, 0), 0)
        self.assertEqual(adapter.compute_score(1, 0.9, 0), 10)

    def test_score_refusals(self):
        for bad in ((-1, 1.0, 0), (0, -1.0, 0), (0, 1.0, -2),
                    (True, 1.0, 0), (0, float("nan"), 0), (0, "x", 0)):
            with self.assertRaises(adapter.HookupError):
                adapter.compute_score(*bad)


class LogTests(unittest.TestCase):
    def test_good_log_passes(self):
        ok, _ = adapter.check_run(adapter.parse(GOOD_LOG), STAGE)
        self.assertTrue(ok)

    def test_missing_marker_fails(self):
        short = "\n".join(l for l in GOOD_LOG.splitlines() if "RECEIPT_DEDUP" not in l)
        ok, why = adapter.check_run(adapter.parse(short), STAGE)
        self.assertFalse(ok)
        self.assertIn("receipt_dedup", why)

    def test_missing_pass_fails(self):
        short = "\n".join(l for l in GOOD_LOG.splitlines() if not l.startswith("PASS "))
        ok, why = adapter.check_run(adapter.parse(short), STAGE)
        self.assertFalse(ok)
        self.assertIn("PASS", why)

    def test_refusal_fails(self):
        bad = GOOD_LOG + "P2_CHALLENGE_PERSISTENCE_REFUSED reason=unknown-stage\n"
        ok, why = adapter.check_run(adapter.parse(bad), STAGE)
        self.assertFalse(ok)
        self.assertIn("refus", why)

    def test_captain_down_fails(self):
        bad = GOOD_LOG + "P2_FIXTURE_CAPTAIN_DOWN tick=5 outcome=BLOCKED\n"
        ok, _ = adapter.check_run(adapter.parse(bad), STAGE)
        self.assertFalse(ok)

    def test_injection_fails(self):
        for token in ("P2_LL_INJECT x=1", "mHealth=100"):
            ok, _ = adapter.check_run(adapter.parse(GOOD_LOG + token + "\n"), STAGE)
            self.assertFalse(ok, token)

    def test_wrong_stage_fails(self):
        ok, _ = adapter.check_run(adapter.parse(GOOD_LOG), "ch_MAT_crawler")
        self.assertFalse(ok)

    def test_gate_status(self):
        status = adapter.gate_status(GOOD_LOG, STAGE)
        self.assertTrue(status["run_markers"][0])
        self.assertTrue(status["captain_guard"][0])
        self.assertTrue(status["no_inject"][0])

    def test_empty_log_fails(self):
        ok, _ = adapter.check_run(adapter.parse(""), STAGE)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
