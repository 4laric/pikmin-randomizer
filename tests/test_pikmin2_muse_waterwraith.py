"""Fail-closed tests for the muse Waterwraith observer (#503).

Gate 1 passes only on the full fixed-encounter birth triple (observed Fall
birth + fixed placement profile + two-species visual bank). Gate 2 passes
only on actor-owned captain chase markers with locomotion motion and measured
travel. Anything less — route-only, hold-only, pinned, missing legs — fails.
"""

import unittest

from experimental.pikmin2_muse_waterwraith import parse

BIRTH = "P2_WATERWRAITH_BIRTH phase=fall attached=1 id=99 helper=98"
PROFILE = (
    "P2_WATERWRAITH_REGISTER_PROFILE placement=0.000,40.000,229.667 yaw=0.0000 "
    "target=500.000,0.000,229.667"
)
VISUAL = "P2_WATERWRAITH_VISUAL_READY species=2 clips=16"
CHASE_RUN = "P2_WATERWRAITH_STEER tick=120 mode=chase motion=run band=near travel=12.5 escape=2"
CHASE_WALK = "P2_WATERWRAITH_STEER tick=60 mode=chase motion=walk band=mid travel=4.0 escape=2"
ROUTE = "P2_WATERWRAITH_STEER tick=30 mode=route motion=none band=- travel=30.0 escape=1"


def full_log():
    return "\n".join([BIRTH, PROFILE, VISUAL, ROUTE, CHASE_WALK, CHASE_RUN])


class MuseWaterwraithObserverTests(unittest.TestCase):
    def test_full_fixed_encounter_passes_both_gates(self):
        verdict = parse(full_log())
        self.assertTrue(verdict["gate1_ok"])
        self.assertTrue(verdict["gate2_ok"])
        self.assertEqual(verdict["chase_lines"], 2)
        self.assertAlmostEqual(verdict["chase_travel_max"], 12.5)
        self.assertEqual(verdict["escape_phases"], [1, 2])

    def test_missing_birth_fails_gate1(self):
        verdict = parse("\n".join([PROFILE, VISUAL, CHASE_RUN]))
        self.assertFalse(verdict["gate1_ok"])
        self.assertFalse(verdict["birth_ok"])

    def test_wrong_birth_phase_fails_gate1(self):
        bad = BIRTH.replace("phase=fall", "phase=walk")
        verdict = parse("\n".join([bad, PROFILE, VISUAL, CHASE_RUN]))
        self.assertFalse(verdict["gate1_ok"])

    def test_detached_birth_fails_gate1(self):
        bad = BIRTH.replace("attached=1", "attached=0")
        verdict = parse("\n".join([bad, PROFILE, VISUAL, CHASE_RUN]))
        self.assertFalse(verdict["gate1_ok"])

    def test_wrong_ids_fail_gate1(self):
        bad = BIRTH.replace("id=99 helper=98", "id=54 helper=0")
        verdict = parse("\n".join([bad, PROFILE, VISUAL, CHASE_RUN]))
        self.assertFalse(verdict["gate1_ok"])

    def test_missing_profile_fails_gate1(self):
        verdict = parse("\n".join([BIRTH, VISUAL, CHASE_RUN]))
        self.assertFalse(verdict["gate1_ok"])

    def test_missing_visual_fails_gate1(self):
        verdict = parse("\n".join([BIRTH, PROFILE, CHASE_RUN]))
        self.assertFalse(verdict["gate1_ok"])

    def test_route_only_fails_gate2(self):
        verdict = parse("\n".join([BIRTH, PROFILE, VISUAL, ROUTE]))
        self.assertTrue(verdict["gate1_ok"])
        self.assertFalse(verdict["gate2_ok"])
        self.assertEqual(verdict["chase_lines"], 0)

    def test_pinned_chase_fails_gate2(self):
        pinned = "P2_WATERWRAITH_STEER tick=120 mode=chase motion=run band=near travel=0.0 escape=2"
        verdict = parse("\n".join([BIRTH, PROFILE, VISUAL, pinned]))
        self.assertFalse(verdict["gate2_ok"])

    def test_wait_only_chase_fails_gate2(self):
        wait = "P2_WATERWRAITH_STEER tick=120 mode=chase motion=wait band=far travel=9.0 escape=2"
        verdict = parse("\n".join([BIRTH, PROFILE, VISUAL, wait]))
        self.assertFalse(verdict["gate2_ok"])

    def test_hold_only_fails_gate2(self):
        hold = "P2_WATERWRAITH_STEER tick=10 mode=hold motion=none band=- travel=0.0 escape=1"
        verdict = parse("\n".join([BIRTH, PROFILE, VISUAL, hold]))
        self.assertFalse(verdict["gate2_ok"])

    def test_empty_log_fails_both(self):
        verdict = parse("")
        self.assertFalse(verdict["gate1_ok"])
        self.assertFalse(verdict["gate2_ok"])
        self.assertEqual(verdict["steer_lines"], 0)

    def test_tired_and_refresh_are_informational(self):
        log = full_log() + "\nP2_WATERWRAITH_TIRED tick=400\nP2_WATERWRAITH_ROUTE_REFRESH tick=61"
        verdict = parse(log)
        self.assertTrue(verdict["tired_seen"])
        self.assertTrue(verdict["route_refresh_seen"])
        self.assertTrue(verdict["gate2_ok"])


if __name__ == "__main__":
    unittest.main()
