"""Focused fail-closed tests for the flora hookup callsite observer (#723)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experimental import pikmin2_flora_hookup_engine_callsite as obs

GOOD = chr(10).join([
    "P2_FLORA_HOOKUP_WINDOW size=960x540 pos=100,100 display=1920x1080 centered=1",
    "P2_FLORA_HOOKUP_ADMIT species=BluePom swallowed=3 ok=1",
    "P2_FLORA_HOOKUP_CONVERT species=BluePom sprouts=3 slots=3 refund=0",
    "P2_FLORA_HOOKUP_SPROUT species=BluePom index=0 received=1",
    "P2_FLORA_HOOKUP_SPROUT species=BluePom index=1 received=1",
    "P2_FLORA_HOOKUP_SPROUT species=BluePom index=2 received=1",
    "P2_FLORA_HOOKUP_ADMIT species=RandPom swallowed=1 ok=1",
    "P2_FLORA_HOOKUP_CONVERT species=RandPom sprouts=9 slots=0 refund=0",
    "P2_FLORA_HOOKUP_SCENERY identity=Clover slot=0 bound=0",
    "P2_FLORA_HOOKUP_DONE failures=0",
    "PASS P2_FLORA_HOOKUP_RUN suites=3",
]) + chr(10)


class HookupObserverTests(unittest.TestCase):
    def test_good_run_passes(self):
        parsed = obs.parse(GOOD)
        ok, why = obs.check_run(parsed)
        self.assertTrue(ok, why)
        self.assertTrue(parsed["window"])
        self.assertEqual(len(parsed["sprouts"]), 3)

    def test_missing_window_fails(self):
        text = GOOD.split(chr(10), 1)[1]
        ok, why = obs.check_run(obs.parse(text))
        self.assertFalse(ok)
        self.assertIn("window", why)

    def test_captain_down_blocks(self):
        ok, why = obs.check_run(obs.parse(GOOD + "P2_FIXTURE_CAPTAIN_DOWN tick=1" + chr(10)))
        self.assertFalse(ok)
        self.assertIn("captain-down", why)

    def test_missing_convert_fails(self):
        lines = [l for l in GOOD.splitlines() if "CONVERT" not in l]
        ok, why = obs.check_run(obs.parse(chr(10).join(lines) + chr(10)))
        self.assertFalse(ok)
        self.assertIn("CONVERT", why)

    def test_done_nonzero_fails(self):
        text = GOOD.replace("failures=0", "failures=2")
        ok, why = obs.check_run(obs.parse(text))
        self.assertFalse(ok)
        self.assertIn("nonzero", why)

    def test_injected_markers_fail(self):
        ok, why = obs.check_run(obs.parse(GOOD + "mHealth=0" + chr(10)))
        self.assertFalse(ok)
        self.assertIn("injection", why)

    def test_no_pass_fails(self):
        lines = [l for l in GOOD.splitlines() if not l.startswith("PASS ")]
        ok, why = obs.check_run(obs.parse(chr(10).join(lines) + chr(10)))
        self.assertFalse(ok)
        self.assertIn("PASS", why)

    def test_stage_keys_and_score(self):
        keys = obs.stage_keys("ch_MAT_route_rover")
        self.assertEqual(keys["save"], "p2_challenge_save_ch_MAT_route_rover")
        self.assertEqual(obs.compute_score(42, 120.5, 15), 690)
        with self.assertRaises(obs.HookupError):
            obs.stage_keys("bad id!")
        with self.assertRaises(obs.HookupError):
            obs.compute_score(-1, 10.0, 1)

    def test_unknown_species_refused(self):
        with self.assertRaises(obs.HookupError):
            obs._check_species("Nope")

    def test_gate_status(self):
        gates = obs.gate_status(GOOD)
        self.assertTrue(gates["run_markers"][0])
        self.assertTrue(gates["captain_guard"][0])
        self.assertTrue(gates["no_inject"][0])


if __name__ == "__main__":
    unittest.main()
