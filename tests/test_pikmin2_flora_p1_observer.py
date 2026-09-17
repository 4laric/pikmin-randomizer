"""Focused fail-closed tests for the flora P1 observer (#737)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experimental import pikmin2_flora_p1_observer as obs


def session(identity, converted=7, received=7):
    return "P2_FLORA_P1_SESSION identity=%s converted=%d received=%d hauled=0" % (
        identity, converted, received)


GOOD = chr(10).join([
    "P2_FLORA_P1_WINDOW size=960x540 pos=100,100 display=1920x1080 centered=1",
    "P2_FLORA_P1_SQUAD pikis=20 colors=Red,Blue,Yellow,Purple,White",
    session("Clover"), session("Tukushi"), session("Chiyogami"),
    "P2_FLORA_P1_DONE failures=0",
    "PASS P2_FLORA_P1_RUN sessions=3",
]) + chr(10)


class FloraObserverTests(unittest.TestCase):
    def test_good_run_passes(self):
        parsed = obs.parse(GOOD)
        ok, why = obs.check_run(parsed)
        self.assertTrue(ok, why)
        self.assertEqual(parsed["squads"], [(20, "Red,Blue,Yellow,Purple,White")])
        self.assertTrue(parsed["window"])

    def test_missing_window_fails(self):
        lines = [l for l in GOOD.splitlines() if "WINDOW" not in l]
        ok, why = obs.check_run(obs.parse(chr(10).join(lines) + chr(10)))
        self.assertFalse(ok)
        self.assertIn("window", why)

    def test_captain_down_blocks(self):
        ok, why = obs.check_run(obs.parse(GOOD + "P2_FIXTURE_CAPTAIN_DOWN tick=1" + chr(10)))
        self.assertFalse(ok)
        self.assertIn("captain-down", why)

    def test_missing_flora_fails(self):
        lines = [l for l in GOOD.splitlines() if "Tukushi" not in l]
        ok, why = obs.check_run(obs.parse(chr(10).join(lines) + chr(10)))
        self.assertFalse(ok)
        self.assertIn("Tukushi", why)

    def test_haul_violates_invariant(self):
        text = GOOD.replace(session("Clover"), session("Clover").replace("hauled=0", "hauled=1"))
        ok, why = obs.check_run(obs.parse(text))
        self.assertFalse(ok)
        self.assertIn("absorb-never-haul", why)

    def test_open_accounting_fails(self):
        text = GOOD.replace(session("Clover"), session("Clover", 7, 6))
        ok, why = obs.check_run(obs.parse(text))
        self.assertFalse(ok)
        self.assertIn("accounting", why)

    def test_injected_markers_fail(self):
        ok, why = obs.check_run(obs.parse(GOOD + "mHealth=0" + chr(10)))
        self.assertFalse(ok)
        self.assertIn("injection", why)

    def test_no_pass_fails(self):
        lines = [l for l in GOOD.splitlines() if not l.startswith("PASS ")]
        ok, why = obs.check_run(obs.parse(chr(10).join(lines) + chr(10)))
        self.assertFalse(ok)
        self.assertIn("PASS", why)

    def test_unknown_flora_rejected(self):
        with self.assertRaises(obs.ObserverError):
            obs._check_flora("Nope")

    def test_stage_keys_and_score(self):
        keys = obs.stage_keys("ch_MAT_route_rover")
        self.assertEqual(keys["save"], "p2_challenge_save_ch_MAT_route_rover")
        self.assertEqual(obs.compute_score(42, 120.5, 15), 690)
        with self.assertRaises(obs.ObserverError):
            obs.compute_score(-1, 10.0, 1)

    def test_gate_status(self):
        gates = obs.gate_status(GOOD)
        self.assertTrue(gates["run_markers"][0])
        self.assertTrue(gates["captain_guard"][0])
        self.assertTrue(gates["no_inject"][0])


if __name__ == "__main__":
    unittest.main()
