"""Focused fail-closed tests for the Kurage57 death/transport observer (#768)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experimental import pikmin2_kurage_death_transport_observer as obs


def cap(t):
    return "P2_KURAGE_CAPTURE target=%d result=Captured" % t


def good_pass(first):
    lines = ["P2_KURAGE57_ACTOR id=57 variant=Greater squad=10"]
    lines += [cap(t) for t in range(first, first + 5)]
    lines += ["P2_KURAGE_DEATH released=2 killed=3",
              "P2_KURAGE_CORPSE corpse=1 hauled=1"]
    return lines


GOOD = chr(10).join(
    ["P2_KURAGE57_WINDOW size=960x540 pos=100,100 display=1920x1080 centered=1"]
    + good_pass(0) + ["P2_KURAGE_TRANSPORT fresh=1 replay=0 doublecount=0"]
    + good_pass(5) + ["P2_KURAGE_TRANSPORT fresh=0 replay=1 doublecount=0",
                      "P2_KURAGE_REENTRY pass=2 matched=1",
                      "P2_KURAGE_DONE failures=0",
                      "PASS P2_KURAGE57_RUN passes=2"]) + chr(10)


class KurageObserverTests(unittest.TestCase):
    def test_good_run_passes(self):
        parsed = obs.parse(GOOD)
        ok, why = obs.check_run(parsed)
        self.assertTrue(ok, why)
        self.assertEqual(len(parsed["captures"]), 10)

    def test_missing_window_fails(self):
        lines = [l for l in GOOD.splitlines() if "WINDOW" not in l]
        ok, why = obs.check_run(obs.parse(chr(10).join(lines) + chr(10)))
        self.assertFalse(ok)
        self.assertIn("window", why)

    def test_captain_down_blocks(self):
        ok, why = obs.check_run(obs.parse(GOOD + "P2_FIXTURE_CAPTAIN_DOWN tick=1" + chr(10)))
        self.assertFalse(ok)
        self.assertIn("captain-down", why)

    def test_open_accounting_fails(self):
        text = GOOD.replace("P2_KURAGE_DEATH released=2 killed=3",
                            "P2_KURAGE_DEATH released=1 killed=3", 1)
        ok, why = obs.check_run(obs.parse(text))
        self.assertFalse(ok)
        self.assertIn("accounting", why)

    def test_doublecount_fails(self):
        text = GOOD.replace("doublecount=0", "doublecount=1")
        ok, why = obs.check_run(obs.parse(text))
        self.assertFalse(ok)
        self.assertIn("double-count", why)

    def test_reentry_mismatch_fails(self):
        text = GOOD.replace("matched=1", "matched=0")
        ok, why = obs.check_run(obs.parse(text))
        self.assertFalse(ok)
        self.assertIn("re-entry", why)

    def test_injected_blocks(self):
        ok, why = obs.check_run(obs.parse(GOOD + "mHealth=0" + chr(10)))
        self.assertFalse(ok)
        self.assertIn("injection", why)

    def test_no_pass_fails(self):
        lines = [l for l in GOOD.splitlines() if not l.startswith("PASS ")]
        ok, why = obs.check_run(obs.parse(chr(10).join(lines) + chr(10)))
        self.assertFalse(ok)
        self.assertIn("PASS", why)

    def test_gate_status(self):
        gates = obs.gate_status(GOOD)
        self.assertTrue(gates["run_markers"][0])
        self.assertTrue(gates["captain_guard"][0])
        self.assertTrue(gates["no_inject"][0])


if __name__ == "__main__":
    unittest.main()
