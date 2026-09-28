"""Tests for the Groink carcass recovery / replacement-object revival policy.

Mirrors the native ``p2_groink_carcass`` contract (``MiniHoudai.cpp:282-325``)
and keeps the Python twin in lock-step with the source semantics.
"""
import unittest

from experimental.pikmin2_groink_carcass import (
    Birth, Command, Config, P2GroinkCarcass, Step, birth)


class GroinkCarcassTests(unittest.TestCase):
    def test_become_resets_state_and_birth_carries_identity(self):
        p = P2GroinkCarcass()
        self.assertFalse(p.ready)
        self.assertEqual(p.timer, 0.0)
        self.assertEqual(p.health, 0.0)
        self.assertTrue(p.become(Config(1.0, 2.0, 500.0)))
        self.assertTrue(p.ready)
        self.assertEqual(p.timer, 0.0)
        self.assertEqual(p.health, 0.0)
        b = birth(position=(10.0, 1.0, -3.0), face_dir=1.25,
                  existence_length=999.0, in_piklopedia=True)
        self.assertIsInstance(b, Birth)
        self.assertEqual(b.position, (10.0, 1.0, -3.0))
        self.assertEqual(b.face_dir, 1.25)
        self.assertEqual(b.existence_length, 999.0)
        self.assertTrue(b.in_piklopedia)

    def test_gauge_delay_elapses_before_regeneration_and_activates_once(self):
        p = P2GroinkCarcass()
        p.become(Config(1.0, 10.0, 1200.0))
        for _ in range(3):
            s = p.step(0.25, True, True)
            self.assertTrue(s.valid)
            self.assertEqual(s.commands, ())
        self.assertEqual(p.health, 0.0)
        self.assertAlmostEqual(p.timer, 0.75, places=6)
        s = p.step(0.25, True, True)
        self.assertTrue(s.valid)
        self.assertEqual(s.commands, (Command.ActivateGauge,))
        self.assertEqual(p.health, 0.0)
        self.assertAlmostEqual(p.timer, 1.0, places=6)
        s = p.step(0.25, True, True)
        self.assertTrue(s.valid)
        self.assertEqual(s.commands, ())
        self.assertGreater(p.health, 0.0)

    def test_regeneration_rate_is_max_over_recovery_per_second(self):
        p = P2GroinkCarcass()
        p.become(Config(30.0, 10.0, 1200.0))
        for _ in range(120):
            p.step(0.25, True, True)
        self.assertEqual(p.health, 0.0)
        for _ in range(4):
            p.step(0.25, True, True)
        self.assertAlmostEqual(p.health, 120.0, places=6)

    def test_full_health_emits_kill_then_birth_and_does_not_clamp(self):
        p = P2GroinkCarcass()
        p.become(Config(0.25, 0.1, 100.0))
        s = p.step(0.25, True, True)
        self.assertEqual(s.commands, (Command.ActivateGauge,))
        self.assertEqual(p.health, 0.0)
        s = p.step(0.25, True, True)
        self.assertEqual(s.commands, (Command.KillPellet, Command.RequestBirth))
        self.assertEqual(p.health, 250.0)
        self.assertGreater(p.health, 100.0)

    def test_no_rebirth_retry_after_request(self):
        p = P2GroinkCarcass()
        p.become(Config(0.25, 0.1, 100.0))
        p.step(0.25, True, True)
        p.step(0.25, True, True)
        for _ in range(5):
            s = p.step(0.25, True, True)
            self.assertTrue(s.valid)
            self.assertEqual(s.commands, ())
        self.assertEqual(p.health, 250.0)

    def test_dead_pellet_before_gauge_no_reset(self):
        cfg = Config(1.0, 10.0, 100.0)
        p = P2GroinkCarcass()
        p.become(cfg)
        p.step(0.25, True, False)
        s = p.step(0.25, False, False)
        self.assertTrue(s.valid)
        self.assertEqual(s.commands, ())
        self.assertAlmostEqual(p.timer, 0.25, places=6)
        self.assertEqual(p.health, 0.0)
        q = P2GroinkCarcass()
        q.become(cfg)
        q.step(0.25, True, True)
        s = q.step(0.25, False, True)
        self.assertTrue(s.valid)
        self.assertEqual(s.commands, ())
        self.assertAlmostEqual(q.timer, 0.25, places=6)
        self.assertEqual(q.health, 0.0)

    def test_dead_pellet_after_gauge_resets_once(self):
        p = P2GroinkCarcass()
        p.become(Config(0.25, 10.0, 100.0))
        p.step(0.25, True, True)
        s = p.step(0.25, False, True)
        self.assertTrue(s.valid)
        self.assertEqual(s.commands, (Command.DeactivateGauge,))
        self.assertEqual(p.timer, 0.0)
        self.assertEqual(p.health, 0.0)
        s = p.step(0.25, False, True)
        self.assertTrue(s.valid)
        self.assertEqual(s.commands, ())

    def test_gauge_manager_false_suppresses_gauge_commands(self):
        p = P2GroinkCarcass()
        p.become(Config(0.25, 10.0, 100.0))
        s = p.step(0.25, True, False)
        self.assertEqual(s.commands, ())
        self.assertAlmostEqual(p.timer, 0.25, places=6)
        q = P2GroinkCarcass()
        q.become(Config(0.25, 10.0, 100.0))
        q.step(0.25, True, True)
        s = q.step(0.25, False, False)
        self.assertEqual(s.commands, ())
        self.assertAlmostEqual(q.timer, 0.25, places=6)
        self.assertEqual(q.health, 0.0)

    def test_zero_gauge_delay_valid_and_no_activate_on_zero_delta(self):
        p = P2GroinkCarcass()
        self.assertTrue(p.become(Config(0.0, 1.0, 100.0)))
        s = p.step(0.0, True, True)
        self.assertTrue(s.valid)
        self.assertEqual(s.commands, ())
        self.assertEqual(p.timer, 0.0)
        self.assertEqual(p.health, 0.0)

    def test_zero_max_health_no_recovery_request(self):
        p = P2GroinkCarcass()
        p.become(Config(0.0, 1.0, 0.0))
        s = p.step(0.25, True, True)
        self.assertTrue(s.valid)
        self.assertEqual(s.commands, ())
        self.assertEqual(p.health, 0.0)

    def test_invalid_config_rejected_without_state_change(self):
        p = P2GroinkCarcass()
        self.assertFalse(p.become(Config(1.0, 0.0, 100.0)))
        self.assertFalse(p.ready)
        self.assertFalse(p.become(Config(float('nan'), 1.0, 100.0)))
        self.assertFalse(p.become(Config(1.0, float('inf'), 100.0)))
        self.assertFalse(p.become(Config(-0.1, 1.0, 100.0)))
        self.assertFalse(p.become(Config(1.0, 1.0, -1.0)))
        self.assertFalse(p.become(Config(1e6 + 1.0, 1.0, 100.0)))
        self.assertFalse(p.ready)
        self.assertEqual(p.timer, 0.0)
        self.assertEqual(p.health, 0.0)

    def test_invalid_step_delta_rejects_without_mutation(self):
        p = P2GroinkCarcass()
        p.become(Config(0.25, 10.0, 100.0))
        p.step(0.1, True, True)
        timer_before = p.timer
        health_before = p.health
        for bad in (-0.1, 0.26, float('nan'), float('inf')):
            s = p.step(bad, True, True)
            self.assertFalse(s.valid)
            self.assertEqual(s.commands, ())
        self.assertEqual(p.timer, timer_before)
        self.assertEqual(p.health, health_before)

    def test_not_ready_step_is_invalid(self):
        p = P2GroinkCarcass()
        s = p.step(0.25, True, True)
        self.assertFalse(s.valid)
        self.assertEqual(s.commands, ())

    def test_inactive_tick_pauses_without_mutation(self):
        p = P2GroinkCarcass()
        p.become(Config(0.25, 10.0, 100.0))
        p.step(0.1, True, True)
        timer_before = p.timer
        health_before = p.health
        s = p.step(0.1, True, True, active_tick=False)
        self.assertTrue(s.valid)
        self.assertEqual(s.commands, ())
        self.assertEqual(p.timer, timer_before)
        self.assertEqual(p.health, health_before)
        q = P2GroinkCarcass()
        qs = q.step(0.1, True, True, active_tick=False)
        self.assertFalse(qs.valid)

    def test_birth_descriptor_roundtrip(self):
        b = birth((1.5, -2.0, 3.25), 0.75, 45.0, True)
        self.assertIsInstance(b, Birth)
        self.assertEqual(b.position, (1.5, -2.0, 3.25))
        self.assertEqual(b.face_dir, 0.75)
        self.assertEqual(b.existence_length, 45.0)
        self.assertTrue(b.in_piklopedia)
        d = birth()
        self.assertEqual(d.position, (0, 0, 0))
        self.assertEqual(d.face_dir, 0.0)
        self.assertEqual(d.existence_length, -1.0)
        self.assertFalse(d.in_piklopedia)


if __name__ == '__main__':
    unittest.main()
