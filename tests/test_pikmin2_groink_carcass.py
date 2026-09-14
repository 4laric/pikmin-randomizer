"""Tests for the Groink carcass regeneration / replacement-object revival policy (#198/#209).

Mirrors the source `doBecomeCarcass` / `doUpdateCarcass` contract and keeps the
Python reference in lock-step with the native `p2_groink_carcass` CTest.
"""
import unittest

from experimental.pikmin2_groink_carcass import (
    Carcass, Event, Parms, fixed_parms, roaming_parms)


class GroinkCarcassTests(unittest.TestCase):
    def setUp(self):
        self.parms = roaming_parms()  # max 1200, fp11=30, fp12=10

    def test_become_resets_state_and_preserves_identity(self):
        c = Carcass(position=(10.0, 0.0, -4.0), face_dir=1.25,
                    existence_length=999.0, in_piklopedia=True)
        c.gauge_timer = 42.0
        c.health = 300.0
        c.pellet_alive = False
        c.become()
        self.assertEqual((c.gauge_timer, c.health), (0.0, 0.0))
        self.assertTrue(c.pellet_alive and not c.gauge_active and not c.revived)
        self.assertEqual(c.position, (10.0, 0.0, -4.0))
        self.assertAlmostEqual(c.face_dir, 1.25)
        self.assertAlmostEqual(c.existence_length, 999.0)
        self.assertTrue(c.in_piklopedia)

    def test_gauge_delay_precedes_regeneration(self):
        c = Carcass().become()
        for _ in range(29):
            self.assertEqual(c.step(self.parms, 1.0).event, Event.NONE.value)
            self.assertEqual(c.health, 0.0)
        self.assertAlmostEqual(c.gauge_timer, 29.0)
        out = c.step(self.parms, 1.0)
        self.assertEqual(out.event, Event.GAUGE_ACTIVE.value)
        self.assertTrue(c.gauge_active)
        self.assertEqual(c.health, 0.0)

    def test_gauge_active_fires_once(self):
        c = Carcass().become()
        c.step(self.parms, 30.0)  # crossing
        out = c.step(self.parms, 1.0)  # first regeneration step
        self.assertEqual(out.event, Event.NONE.value)

    def test_regeneration_rate_is_max_over_respawn(self):
        c = Carcass().become()
        for _ in range(30):
            c.step(self.parms, 1.0)
        out = c.step(self.parms, 1.0)
        self.assertEqual(out.event, Event.NONE.value)
        self.assertAlmostEqual(c.health, 120.0, places=3)

    def test_revival_at_full_health_carries_identity(self):
        c = Carcass(position=(10.0, 0.0, -4.0), face_dir=1.25,
                    existence_length=999.0, in_piklopedia=True).become()
        out = None
        for _ in range(40):
            out = c.step(self.parms, 1.0)
        self.assertEqual(out.event, Event.REVIVE.value)
        self.assertTrue(c.revived and not c.pellet_alive)
        self.assertAlmostEqual(c.health, 1200.0)
        self.assertEqual(out.birth.position, (10.0, 0.0, -4.0))
        self.assertAlmostEqual(out.birth.face_dir, 1.25)
        self.assertAlmostEqual(out.birth.existence_length, 999.0)
        self.assertTrue(out.birth.in_piklopedia)
        # Revived carcass is terminal.
        self.assertEqual(c.step(self.parms, 1.0).event, Event.NONE.value)

    def test_fixed_variant_rate_and_identity(self):
        parms = fixed_parms()  # max 700, fp11=30, fp12=10 -> 70/s
        c = Carcass(position=(1.0, 2.0, 3.0), face_dir=-0.5,
                    existence_length=80.0).become()
        out = None
        for _ in range(40):
            out = c.step(parms, 1.0)
        self.assertEqual(out.event, Event.REVIVE.value)
        self.assertAlmostEqual(c.health, 700.0)
        self.assertEqual(out.birth.position, (1.0, 2.0, 3.0))
        self.assertAlmostEqual(out.birth.face_dir, -0.5)
        self.assertFalse(out.birth.in_piklopedia)

    def test_varying_respawn_rate(self):
        parms = Parms(max_health=700.0, health_gauge_timer=5.0, respawn_rate=20.0)
        c = Carcass().become()
        c.step(parms, 5.0)  # gauge crosses
        c.step(parms, 1.0)
        self.assertAlmostEqual(c.health, 35.0, places=3)
        out = None
        for _ in range(19):
            out = c.step(parms, 1.0)
        self.assertEqual(out.event, Event.REVIVE.value)
        self.assertAlmostEqual(c.health, 700.0)

    def test_pellet_death_before_gauge_blocks_revival(self):
        c = Carcass().become()
        c.step(self.parms, 10.0)
        c.pellet_alive = False
        out = c.step(self.parms, 1.0)
        self.assertEqual(out.event, Event.NONE.value)
        self.assertEqual(c.health, 0.0)
        self.assertFalse(c.revived and c.gauge_active)

    def test_pellet_death_after_gauge_inactivates_once(self):
        c = Carcass().become()
        c.step(self.parms, 30.0)
        self.assertTrue(c.gauge_active)
        c.pellet_alive = False
        out = c.step(self.parms, 1.0)
        self.assertEqual(out.event, Event.GAUGE_INACTIVE.value)
        self.assertFalse(c.gauge_active)
        self.assertEqual((c.gauge_timer, c.health), (0.0, 0.0))
        self.assertEqual(c.step(self.parms, 1.0).event, Event.NONE.value)

    def test_invalid_inputs_reject_without_mutation(self):
        c = Carcass().become()
        c.gauge_timer = 30.0
        for parms, delta in ((Parms(1200.0, 0.0, 10.0), 1.0),
                             (Parms(1200.0, 30.0, 0.0), 1.0),
                             (Parms(0.0, 30.0, 10.0), 1.0),
                             (self.parms, 0.0),
                             (self.parms, -1.0)):
            self.assertEqual(c.step(parms, delta).event, Event.NONE.value)
        self.assertAlmostEqual(c.gauge_timer, 30.0)
        self.assertEqual(c.health, 0.0)


if __name__ == '__main__':
    unittest.main()
