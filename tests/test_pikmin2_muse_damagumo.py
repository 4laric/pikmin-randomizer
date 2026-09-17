"""Focused tests for the Damagumo56 acceptance observer (issue #173).

All logs here are SYNTHETIC and labelled as such: they exercise the reader's
verdict logic and fail-closed negatives. None is source or runtime evidence;
the future Damagumo fixture writes the same marker grammar for a real log.
"""
import unittest

from experimental.pikmin2_muse_damagumo import CHILD_COUNT, SOURCE_SPEED, validate

GOOD = "\n".join([
    "P2_MUSE_DAMAGUMO_READY squad=20 damagumo_gen=312004",
    "P2_MUSE_DAMAGUMO_BIND generator=312004 species=Damagumo native_fsm=implemented",
    "Experimental preview window set to 960x540 windowed and centered",
    "P2_MUSE_DAMAGUMO_SESSION navi=1",
    "P2_LONG_LEGS_STATE species=Damagumo generator=312004 state=Stay",
    "P2_LONG_LEGS_STATE species=Damagumo generator=312004 state=Land",
    "P2_LONG_LEGS_STATE species=Damagumo generator=312004 state=Wait",
    "P2_LONG_LEGS_STATE species=Damagumo generator=312004 state=Walk",
    "P2_LONG_LEGS_WALK species=Damagumo generator=312004 from=0.0,0.0 to=40.0,0.0 speed=100.0",
    "P2_LONG_LEGS_WALK_END species=Damagumo generator=312004 distance=38.5 seconds=0.40",
    "P2_LONG_LEGS_DEAD species=Damagumo generator=312004 health=0 prior_health=120.0",
    "P2_MUSE_DAMAGUMO_CHILD_BIRTH generator=312004 species=ShijimiChou count=25",
    "P2_MUSE_DAMAGUMO_REENTRY generator=312004 stale=0 fresh=1 rebind=1",
    "PASS P2_MUSE_DAMAGUMO",
])


class PositiveTests(unittest.TestCase):
    def test_canonical_run_passes(self):
        result = validate(GOOD)
        self.assertTrue(result["passed"], result["problems"])
        for gate in result["gates"].values():
            self.assertEqual(gate, "pass")
        self.assertEqual(result["squad"], 20)
        self.assertFalse(result["injected"])

    def test_source_pins(self):
        self.assertEqual(SOURCE_SPEED, 100.0)
        self.assertEqual(CHILD_COUNT, 25)


class NegativeTests(unittest.TestCase):
    def test_missing_bind_fails_identity(self):
        text = "\n".join(l for l in GOOD.splitlines()
                         if "DAMAGUMO_BIND" not in l)
        result = validate(text)
        self.assertFalse(result["passed"])
        self.assertEqual(result["gates"]["identity_spawn"], "fail")

    def test_missing_walk_end_fails_movement(self):
        text = "\n".join(l for l in GOOD.splitlines()
                         if "WALK_END" not in l)
        result = validate(text)
        self.assertEqual(result["gates"]["movement_animation"], "fail")

    def test_teleporting_walk_rejected(self):
        text = GOOD.replace("distance=38.5 seconds=0.40",
                            "distance=900.0 seconds=0.10")
        result = validate(text)
        self.assertEqual(result["gates"]["movement_animation"], "fail")

    def test_short_walk_rejected(self):
        text = GOOD.replace("distance=38.5 seconds=0.40",
                            "distance=5.0 seconds=0.40")
        result = validate(text)
        self.assertEqual(result["gates"]["movement_animation"], "fail")

    def test_injected_run_rejected_wholesale(self):
        result = validate(GOOD + "\nP2_MUSE_DAMAGUMO_INJECT health=1")
        self.assertFalse(result["passed"])
        self.assertTrue(result["injected"])
        self.assertIn("injected-markers-present", result["problems"])

    def test_mhealth_injection_marker_rejected(self):
        result = validate(GOOD + "\nmhealth_injected=1")
        self.assertFalse(result["passed"])
        self.assertTrue(result["injected"])

    def test_wrong_child_count_fails_birth(self):
        text = GOOD.replace("count=25", "count=30")
        result = validate(text)
        self.assertEqual(result["gates"]["death_corpse"], "fail")
        self.assertEqual(result["gates"]["transport_reward"], "fail")

    def test_child_generator_disagreement_rejected(self):
        text = GOOD.replace("CHILD_BIRTH generator=312004",
                            "CHILD_BIRTH generator=999999")
        result = validate(text)
        self.assertEqual(result["gates"]["death_corpse"], "fail")

    def test_negative_prior_health_without_dead_line(self):
        text = "\n".join(l for l in GOOD.splitlines() if "DEAD" not in l)
        result = validate(text)
        self.assertEqual(result["gates"]["attacks_receivers"], "fail")
        self.assertEqual(result["gates"]["death_corpse"], "fail")

    def test_family_birth_marker_accepted(self):
        text = "\n".join(l for l in GOOD.splitlines()
                         if "CHILD_BIRTH" not in l)
        text += "\nP2_LONG_LEGS_BIRTH species=Damagumo generator=312004 count=25"
        result = validate(text)
        self.assertEqual(result["gates"]["death_corpse"], "pass")
        self.assertEqual(result["gates"]["transport_reward"], "pass")

    def test_family_birth_wrong_count_rejected(self):
        text = "\n".join(l for l in GOOD.splitlines()
                         if "CHILD_BIRTH" not in l)
        text += "\nP2_LONG_LEGS_BIRTH species=Damagumo generator=312004 count=30"
        result = validate(text)
        self.assertEqual(result["gates"]["death_corpse"], "fail")

    def test_missing_reentry_fails_cleanup(self):
        text = "\n".join(l for l in GOOD.splitlines()
                         if "REENTRY" not in l)
        result = validate(text)
        self.assertEqual(result["gates"]["cleanup_reentry"], "fail")

    def test_rebind_without_fresh_pointer_rejected(self):
        text = GOOD.replace("stale=0 fresh=1 rebind=1",
                            "stale=1 fresh=0 rebind=1")
        result = validate(text)
        self.assertEqual(result["gates"]["cleanup_reentry"], "fail")

    def test_wrong_species_state_ignored(self):
        text = GOOD + "\nP2_LONG_LEGS_STATE species=Houdai generator=312004 state=Walk"
        result = validate(text)
        self.assertTrue(result["passed"], result["problems"])

    def test_missing_window_marker_fails(self):
        text = "\n".join(l for l in GOOD.splitlines()
                         if "960x540" not in l)
        result = validate(text)
        self.assertFalse(result["passed"])
        self.assertIn("missing-960x540-window", result["problems"])

    def test_extinction_screen_rejected(self):
        result = validate(GOOD + "\nExtinction")
        self.assertFalse(result["passed"])
        self.assertIn("missing-live-session", result["problems"])

    def test_empty_log_fails_closed(self):
        result = validate("")
        self.assertFalse(result["passed"])
        self.assertIn("gate-identity_spawn", result["problems"])

    def test_missing_completion_marker_fails(self):
        text = "\n".join(l for l in GOOD.splitlines()
                         if not l.startswith("PASS "))
        result = validate(text)
        self.assertFalse(result["passed"])
        self.assertIn("missing-completion-marker", result["problems"])


if __name__ == "__main__":
    unittest.main()