"""Unit tests for the DangoMushi source-behavior validator (#407/#174)."""
import unittest

from experimental.pikmin2_dangomushi_behavior import (
    ARENA_POSITION, BEHAVIOR_POSITION, DANGO_ID, DANGO_INDEX, PRIVATE_RADIUS,
    SIGHT, plan_positions, squad_distance, validate)

GOOD_LOG = '\n'.join([
    'P2_DANGOMUSHI_BIND generator=376003 source_id=94 visual_only=0',
    'P2_ENEMY_READY species=DangoMushi native_family=Chappy generator=376003 x=50.0 y=30.0 '
    'z=1850.0 health=3000.0 max_health=3000.0 behavior=native source_FSM=implemented '
    'attack=interactflick_roll',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_DANGOMUSHI_STATE generator=376003 state=stay',
    'P2_DANGOMUSHI_STATE generator=376003 state=appear',
    'P2_DANGOMUSHI_STATE generator=376003 state=move',
    'P2_DANGOMUSHI_STATE generator=376003 state=attack',
    'P2_DANGOMUSHI_ROLL generator=376003 frame=23.0',
    'P2_DANGOMUSHI_HIT generator=376003 pikmin=1',
    'P2_DANGOMUSHI_STATE generator=376003 state=turn',
    'P2_DANGOMUSHI_TURN_WINDOW generator=376003 frame=32.4 stickable=1 invulnerable=0',
    'P2_DANGOMUSHI_TURN_WINDOW generator=376003 frame=108.9 stickable=0 invulnerable=1',
    'P2_DANGOMUSHI_HAZARD generator=376003 rocks=10 lifetime=30.0 egg=1',
    'P2_DANGOMUSHI_DAMAGE_REJECTED generator=376003 stickable=0 invulnerable=1 state=attack',
    'P2_DANGOMUSHI_DAMAGE_ACCEPTED generator=376003 stickable=1 state=turn',
    'P2_DANGOMUSHI_STATE generator=376003 state=recover',
    'P2_DANGOMUSHI_STATE generator=376003 state=flick',
    'P2_DANGOMUSHI_STATE generator=376003 state=wait',
    'P2_DANGOMUSHI_POS generator=376003 state=move clip=move phase=0.30 x=50.00 z=1850.00',
    'P2_DANGOMUSHI_POS generator=376003 state=attack clip=attack phase=0.40 x=30.00 z=1820.00',
])


class DangoMushiBehaviorTests(unittest.TestCase):
    def test_identity_and_position(self):
        self.assertEqual(DANGO_INDEX, 2)
        self.assertEqual(DANGO_ID, 376003)
        distance = squad_distance(ARENA_POSITION)
        self.assertLess(distance, SIGHT, 'DangoMushi must start inside the source sight radius')
        self.assertLess(distance, PRIVATE_RADIUS, 'DangoMushi must start inside the Stay wake radius')

    def test_plan_positions_keeps_arena_default_when_already_near(self):
        positions = [ARENA_POSITION] * 4
        planned, override = plan_positions(positions)
        self.assertIsNone(override)
        self.assertEqual(planned[DANGO_INDEX], ARENA_POSITION)
        self.assertEqual(planned, tuple(positions))

    def test_plan_positions_overrides_a_far_actor(self):
        positions = [(50.0, 30.0, 1850.0)] * 4
        positions[DANGO_INDEX] = (900.0, 30.0, 1850.0)
        planned, override = plan_positions(positions)
        self.assertIsNotNone(override)
        self.assertEqual(planned[DANGO_INDEX], BEHAVIOR_POSITION)
        self.assertFalse(override['production_placement'])
        self.assertLess(squad_distance(planned[DANGO_INDEX]), PRIVATE_RADIUS)

    def test_validate_passes_on_source_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertTrue(result['checks']['roll_event'])
        self.assertEqual(result['checks']['roll_frames'], [23.0])
        self.assertTrue(result['checks']['hit_in_roll_window'])
        self.assertEqual(result['checks']['hit_pikmin'], 1)
        self.assertTrue(result['checks']['turn_window'])
        self.assertTrue(result['checks']['damage_rejected'])
        self.assertTrue(result['checks']['damage_accepted'])
        self.assertTrue(result['checks']['window_applied'])
        self.assertTrue(result['checks']['hazard_rain'])
        self.assertTrue(result['checks']['hazard_egg'])
        self.assertGreater(result['motion_spread'], 5.0)

    def test_missing_damage_gate_fails(self):
        stripped = GOOD_LOG.replace(
            'P2_DANGOMUSHI_DAMAGE_REJECTED generator=376003 stickable=0 invulnerable=1 '
            'state=attack\n', '')
        result = validate(stripped, code=0)
        self.assertFalse(result['checks']['window_applied'])
        self.assertFalse(result['passed'])

    def test_damage_accepted_is_informational(self):
        # DAMAGE_ACCEPTED is not required: a run may not land an in-window attack.
        stripped = GOOD_LOG.replace(
            'P2_DANGOMUSHI_DAMAGE_ACCEPTED generator=376003 stickable=1 state=turn\n', '')
        result = validate(stripped, code=0)
        self.assertFalse(result['checks']['damage_accepted'])
        self.assertTrue(result['passed'])

    def test_missing_turn_window_fails(self):
        stripped = GOOD_LOG.replace(
            'P2_DANGOMUSHI_TURN_WINDOW generator=376003 frame=32.4 stickable=1 invulnerable=0\n', ''
        ).replace(
            'P2_DANGOMUSHI_TURN_WINDOW generator=376003 frame=108.9 stickable=0 invulnerable=1\n', '')
        result = validate(stripped, code=0)
        self.assertFalse(result['checks']['turn_window'])
        self.assertFalse(result['passed'])

    def test_hazard_over_budget_fails(self):
        over = GOOD_LOG.replace('rocks=10', 'rocks=11')
        result = validate(over, code=0)
        self.assertFalse(result['checks']['hazard_rain'])
        self.assertFalse(result['passed'])

    def test_hit_outside_roll_fails(self):
        outside = GOOD_LOG.replace(
            'P2_DANGOMUSHI_STATE generator=376003 state=attack\n'
            'P2_DANGOMUSHI_ROLL generator=376003 frame=23.0\n', '')
        result = validate(outside, code=0)
        self.assertFalse(result['checks']['hit_in_roll_window'])
        self.assertFalse(result['passed'])

    def test_roll_outside_source_window_fails(self):
        late = GOOD_LOG.replace('frame=23.0', 'frame=60.0')
        result = validate(late, code=0)
        self.assertFalse(result['checks']['roll_event'])
        self.assertFalse(result['passed'])

    def test_unbounded_hits_fail(self):
        result = validate(GOOD_LOG + '\nP2_DANGOMUSHI_HIT generator=376003 pikmin=1', code=0)
        self.assertFalse(result['checks']['hit_bounded'])
        self.assertFalse(result['passed'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text')


if __name__ == '__main__':
    unittest.main()
