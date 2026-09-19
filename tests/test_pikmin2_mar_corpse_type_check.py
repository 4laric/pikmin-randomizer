"""Focused fail-closed tests for the Mar corpse-type check (#772)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experimental import pikmin2_mar_corpse_type_check as check

GOOD = chr(10).join([
    "P2_MAR_CORPSE_TYPE_WINDOW size=960x540 pos=100,100 display=1920x1080 centered=1",
    "P2_MAR_CORPSE_TYPE value=1 expected=1",
    "P2_MAR_BECOME_PELLET_BOUND bound=1",
    "P2_MAR_DONE failures=0",
    "PASS P2_MAR_CORPSE_TYPE_RUN",
]) + chr(10)


class MarCorpseTypeTests(unittest.TestCase):
    def test_good_run_passes(self):
        parsed = check.parse(GOOD)
        ok, why = check.check_run(parsed)
        self.assertTrue(ok, why)

    def test_type_mismatch_fails(self):
        text = GOOD.replace("value=1 expected=1", "value=0 expected=1")
        ok, why = check.check_run(check.parse(text))
        self.assertFalse(ok)
        self.assertIn("corpse type", why)

    def test_unbound_fails(self):
        text = GOOD.replace("bound=1", "bound=0")
        ok, why = check.check_run(check.parse(text))
        self.assertFalse(ok)
        self.assertIn("bound", why)

    def test_missing_window_fails(self):
        lines = [l for l in GOOD.splitlines() if "WINDOW" not in l]
        ok, why = check.check_run(check.parse(chr(10).join(lines) + chr(10)))
        self.assertFalse(ok)
        self.assertIn("window", why)

    def test_captain_down_blocks(self):
        ok, why = check.check_run(check.parse(GOOD + "P2_FIXTURE_CAPTAIN_DOWN tick=1" + chr(10)))
        self.assertFalse(ok)
        self.assertIn("captain-down", why)

    def test_injected_blocks(self):
        ok, why = check.check_run(check.parse(GOOD + "mHealth=0" + chr(10)))
        self.assertFalse(ok)
        self.assertIn("injection", why)

    def test_no_pass_fails(self):
        lines = [l for l in GOOD.splitlines() if not l.startswith("PASS ")]
        ok, why = check.check_run(check.parse(chr(10).join(lines) + chr(10)))
        self.assertFalse(ok)
        self.assertIn("PASS", why)

    def test_gate_status(self):
        gates = check.gate_status(GOOD)
        self.assertTrue(gates["run_markers"][0])
        self.assertTrue(gates["captain_guard"][0])
        self.assertTrue(gates["no_inject"][0])


if __name__ == "__main__":
    unittest.main()
