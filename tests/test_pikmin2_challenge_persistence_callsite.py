"""Focused fail-closed tests for the challenge persistence callsite observer (#718).

Synthetic logs only; no builds, runs, or shared writes.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experimental import pikmin2_challenge_persistence_callsite as obs

STAGE = "ch_MAT_route_rover"
WINDOW = "P2_CHALLENGE_PERSISTENCE_CALLSITE_WINDOW size=960x540 pos=100,100 display=1920x1080 centered=1"
FLAG = "P2_CHALLENGE_STAGE_FLAG cave=" + STAGE
RESOLVED = "P2_CHALLENGE_PERSISTENCE_CALLSITE_RESOLVED stage=" + STAGE + " ui_index=27 markers=7"
PASS = "PASS P2_CHALLENGE_PERSISTENCE_CALLSITE_RUN markers=7"
STEMS = ("SAVE_KEY", "LOAD_KEY", "CLEAR", "HIGHSCORE", "UNLOCK", "RECEIPT_DEDUP", "REENTRY")
GOOD = chr(10).join([WINDOW, FLAG] + ["P2_CHALLENGE_%s stage=%s" % (s, STAGE) for s in STEMS] + [RESOLVED, PASS]) + chr(10)


class CallsiteObserverTests(unittest.TestCase):
    def test_good_run_passes(self):
        parsed = obs.parse(GOOD)
        ok, why = obs.check_run(parsed, STAGE)
        self.assertTrue(ok, why)
        self.assertEqual(parsed["stage_flag"], STAGE)
        self.assertEqual(parsed["resolved"], STAGE)

    def test_missing_window_fails(self):
        text = GOOD.replace(WINDOW + chr(10), "")
        ok, why = obs.check_run(obs.parse(text), STAGE)
        self.assertFalse(ok)
        self.assertIn("window", why)

    def test_captain_down_blocks(self):
        ok, why = obs.check_run(obs.parse(GOOD + "P2_FIXTURE_CAPTAIN_DOWN tick=1" + chr(10)), STAGE)
        self.assertFalse(ok)
        self.assertIn("captain-down", why)

    def test_missing_marker_fails(self):
        text = GOOD.replace("P2_CHALLENGE_CLEAR stage=%s" % STAGE + chr(10), "")
        ok, why = obs.check_run(obs.parse(text), STAGE)
        self.assertFalse(ok)
        self.assertIn("clear_flag", why)

    def test_duplicate_marker_not_idempotent(self):
        text = GOOD + "P2_CHALLENGE_SAVE_KEY stage=%s" % STAGE + chr(10)
        ok, why = obs.check_run(obs.parse(text), STAGE)
        self.assertFalse(ok)
        self.assertIn("idempotent", why)

    def test_injected_markers_fail(self):
        ok, why = obs.check_run(obs.parse(GOOD + "mHealth=0" + chr(10)), STAGE)
        self.assertFalse(ok)
        self.assertIn("injection", why)

    def test_wrong_stage_flag_fails(self):
        text = GOOD.replace("cave=" + STAGE, "cave=ch_NARI_01kusachi")
        ok, why = obs.check_run(obs.parse(text), STAGE)
        self.assertFalse(ok)
        self.assertIn("stage flag", why)

    def test_refusal_fails(self):
        text = GOOD + "P2_CHALLENGE_PERSISTENCE_REFUSED reason=unknown-stage" + chr(10)
        ok, why = obs.check_run(obs.parse(text), STAGE)
        self.assertFalse(ok)
        self.assertIn("refusals", why)

    def test_stage_keys_and_markers(self):
        keys = obs.stage_keys(STAGE)
        self.assertEqual(keys["save"], "p2_challenge_save_ch_MAT_route_rover")
        self.assertEqual(obs.marker_for("reentry", STAGE), "P2_CHALLENGE_REENTRY stage=" + STAGE)
        with self.assertRaises(obs.CallsiteError):
            obs.stage_keys("bad id!")

    def test_score_formula(self):
        self.assertEqual(obs.compute_score(42, 120.5, 15), 690)
        with self.assertRaises(obs.CallsiteError):
            obs.compute_score(-1, 10.0, 1)

    def test_gate_status(self):
        gates = obs.gate_status(GOOD, STAGE)
        self.assertTrue(gates["run_markers"][0])
        self.assertTrue(gates["captain_guard"][0])
        self.assertTrue(gates["no_inject"][0])


if __name__ == "__main__":
    unittest.main()
