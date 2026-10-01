"""Focused fail-closed tests for the Mar airborne-reach technique (#709).

Hermetic: synthetic logs and synthetic executed cadences only. The real #375
logs are validated by the observer, not by pytest.
"""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
ADAPTER_PATH = ROOT / "experimental" / "pikmin2_mar_airborne_reach_technique.py"
_spec = importlib.util.spec_from_file_location("pikmin2_mar_airborne_reach_technique", ADAPTER_PATH)
adapter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adapter)

GOOD_LOG = """\
P2_MAR_BIND generator=375001 source_id=29 visual_only=0
P2_MUSE_MAR_READY squad=20 mar_gen=375001 health=3000.00
P2_MAR_STATE generator=375001 state=wait
P2_MAR_STATE generator=375001 state=chase
P2_MAR_STATE generator=375001 state=attack
P2_MAR_BLOW generator=375001 pikmin=6
P2_MAR_POS generator=375001 state=attack clip=attack phase=0.50 x=1.00 z=2.00
P2_MUSE_MAR_HP health=2985.00 squad=20 atk=20 events=1 tick=340
P2_MUSE_MAR_HP health=270.00 squad=20 atk=20 events=167 tick=22140
P2_MUSE_MAR_DRAIN events=167 min=270.00 start=3000.00
"""

GOOD_STEPS = [
    {"action": "wait_for_chase", "mar_state": "chase", "height": 10.0},
    {"action": "preposition_squad", "mar_state": "chase", "height": 10.0},
    {"action": "throw_on_landing", "mar_state": "attack", "height": 3.0},
    {"action": "swarm_attack", "mar_state": "attack", "height": 3.0},
    {"action": "reclump_after_blow", "mar_state": "attack", "height": 3.0},
    {"action": "hold_between_windows", "mar_state": "wait", "height": 80.0},
    {"action": "complete_kill", "mar_state": "attack", "height": 3.0},
]


class ParseTests(unittest.TestCase):
    def test_parse_bind_and_ready(self):
        parsed = adapter.parse(GOOD_LOG)
        self.assertEqual(parsed["binds"][0], ("375001", "29"))
        self.assertEqual(parsed["ready"][-1], "20")

    def test_constants(self):
        self.assertEqual(adapter.SOURCE_ID, 29)
        self.assertEqual(adapter.FLIGHT_HEIGHT, 80.0)
        self.assertEqual(adapter.TOUCHDOWN_BAND, 12.0)
        self.assertEqual(adapter.GENERATOR_375001, 375001)


class PreconditionTests(unittest.TestCase):
    def test_good_log_preconditions_pass(self):
        ok, failures = adapter.check_preconditions(adapter.parse(GOOD_LOG))
        self.assertTrue(ok, failures)

    def test_missing_bind_fails(self):
        text = "\n".join(l for l in GOOD_LOG.splitlines() if "BIND" not in l)
        ok, failures = adapter.check_preconditions(adapter.parse(text))
        self.assertFalse(ok)
        self.assertTrue(any("mar_not_bound" in f for f in failures))

    def test_wrong_source_id_fails(self):
        text = GOOD_LOG.replace("source_id=29", "source_id=28")
        ok, _ = adapter.check_preconditions(adapter.parse(text))
        self.assertFalse(ok)

    def test_captain_down_fails(self):
        text = GOOD_LOG + "P2_FIXTURE_CAPTAIN_DOWN tick=5 outcome=BLOCKED\n"
        ok, failures = adapter.check_preconditions(adapter.parse(text))
        self.assertFalse(ok)
        self.assertTrue(any("captain_down" in f for f in failures))

    def test_squad_below_minimum_fails(self):
        ok, _ = adapter.check_preconditions(adapter.parse(GOOD_LOG), required_squad=30)
        self.assertFalse(ok)

    def test_nan_position_fails(self):
        ok, failures = adapter.check_preconditions(adapter.parse(GOOD_LOG + "x=nan\n"))
        self.assertFalse(ok)

    def test_dead_mar_fails(self):
        text = GOOD_LOG.replace("health=3000.00", "health=0.00").replace("health=2985.00", "health=0.00").replace("health=270.00", "health=0.00")
        ok, _ = adapter.check_preconditions(adapter.parse(text))
        self.assertFalse(ok)


class ReachTests(unittest.TestCase):
    def test_low_window_reachable(self):
        ok, _ = adapter.check_landing_window(adapter.parse(GOOD_LOG), 3.0)
        self.assertTrue(ok)

    def test_band_edge_reachable(self):
        ok, _ = adapter.check_landing_window(adapter.parse(GOOD_LOG), 12.0)
        self.assertTrue(ok)

    def test_hover_unreachable(self):
        ok, why = adapter.check_landing_window(adapter.parse(GOOD_LOG), 80.0)
        self.assertFalse(ok)
        self.assertIn("out_of_reach", why)

    def test_swing_height_unreachable(self):
        ok, _ = adapter.check_landing_window(adapter.parse(GOOD_LOG), 20.0)
        self.assertFalse(ok)

    def test_nan_height_rejected(self):
        ok, _ = adapter.check_landing_window(adapter.parse(GOOD_LOG), float("nan"))
        self.assertFalse(ok)

    def test_entry_geometry_inside(self):
        ok, _ = adapter.check_entry_geometry(150.0, 0.5)
        self.assertTrue(ok)

    def test_entry_geometry_far(self):
        ok, _ = adapter.check_entry_geometry(250.0, 0.0)
        self.assertFalse(ok)

    def test_entry_geometry_angle(self):
        ok, _ = adapter.check_entry_geometry(100.0, 1.2)
        self.assertFalse(ok)

    def test_reachable_window_observed(self):
        ok, _ = adapter.reachable_from(adapter.parse(GOOD_LOG))
        self.assertTrue(ok)

    def test_no_window_untested(self):
        text = "\n".join(l for l in GOOD_LOG.splitlines() if "state=attack" not in l)
        ok, why = adapter.reachable_from(adapter.parse(text))
        self.assertFalse(ok)
        self.assertIn("no ATTACK window", why)


class CadenceTests(unittest.TestCase):
    def test_canonical_steps_run(self):
        steps = adapter.cadence_steps()
        self.assertEqual([s["step"] for s in steps], list(range(1, len(steps) + 1)))
        self.assertTrue(all(s["action"] and s["observable"] and s["rule"] for s in steps))

    def test_good_cadence_valid(self):
        ok, _ = adapter.check_cadence(GOOD_STEPS, adapter.parse(GOOD_LOG))
        self.assertTrue(ok)

    def test_attack_at_flight_height_rejected(self):
        bad = [dict(s) for s in GOOD_STEPS]
        bad[3]["height"] = 80.0
        ok, why = adapter.check_cadence(bad, adapter.parse(GOOD_LOG))
        self.assertFalse(ok)
        self.assertIn("out_of_reach", why)

    def test_reissue_active_attack_rejected(self):
        bad = [dict(s) for s in GOOD_STEPS]
        bad[3]["reissued_active_attack"] = True
        ok, why = adapter.check_cadence(bad, adapter.parse(GOOD_LOG))
        self.assertFalse(ok)
        self.assertIn("re-issued", why)

    def test_no_throw_rejected(self):
        bad = [s for s in GOOD_STEPS if s["action"] != "throw_on_landing"]
        ok, why = adapter.check_cadence(bad, adapter.parse(GOOD_LOG))
        self.assertFalse(ok)
        self.assertIn("throw", why)

    def test_hold_outside_hover_rejected(self):
        bad = [dict(s) for s in GOOD_STEPS]
        step = next(s for s in bad if s["action"] == "hold_between_windows")
        step["mar_state"] = "attack"
        ok, why = adapter.check_cadence(bad, adapter.parse(GOOD_LOG))
        self.assertFalse(ok)
        self.assertIn("hold", why)

    def test_empty_cadence_rejected(self):
        ok, _ = adapter.check_cadence([], adapter.parse(GOOD_LOG))
        self.assertFalse(ok)

    def test_malformed_step_rejected(self):
        ok, _ = adapter.check_cadence([{"height": 3.0}], adapter.parse(GOOD_LOG))
        self.assertFalse(ok)

    def test_no_low_window_rejected(self):
        bad = [s for s in GOOD_STEPS if s["action"] not in ("throw_on_landing", "swarm_attack", "reclump_after_blow")]
        ok, _ = adapter.check_cadence(bad, adapter.parse(GOOD_LOG))
        self.assertFalse(ok)


class StatusTests(unittest.TestCase):
    def test_status_passes_on_good_log(self):
        status = adapter.technique_status(adapter.parse(GOOD_LOG), GOOD_STEPS)
        self.assertTrue(status["preconditions"][0])
        self.assertTrue(status["reachable"][0])
        self.assertTrue(status["captain_guard"][0])
        self.assertTrue(status["no_nan"][0])
        self.assertTrue(status["cadence"][0])

    def test_status_flags_captain_down(self):
        status = adapter.technique_status(adapter.parse(GOOD_LOG + "P2_FIXTURE_CAPTAIN_DOWN\n"))
        self.assertFalse(status["captain_guard"][0])

    def test_status_without_cadence_has_no_claim(self):
        status = adapter.technique_status(adapter.parse(GOOD_LOG))
        self.assertNotIn("cadence", status)


if __name__ == "__main__":
    unittest.main()
