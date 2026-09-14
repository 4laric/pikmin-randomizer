"""Unit tests for the UmiMushi source-behavior validator (#407/#167)."""
import unittest

from experimental.pikmin2_umimushi_behavior import (
    ARENA_POSITION, ATTACK_HIT, BEHAVIOR_POSITION, BITE_FRAME, SOURCE_ID,
    UMI_ID, UMI_INDEX, plan_positions, squad_distance, validate)

GOOD_LOG = '\n'.join([
    'P2_UMIMUSHI_BIND generator=374004 source_id=71 visual_only=0',
    'P2_BATCH3_BIND generator=374004 key=aquatic|UmiMushi visual_only=0 native_fsm=implemented',
    'P2_ENEMY_READY species=UmiMushi native_family=Chappy generator=374004 x=-108.0 y=30.0 '
    'z=1850.0 health=1500.0 max_health=1500.0 behavior=native source_FSM=implemented '
    'attack=animation_event water=absent',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_UMIMUSHI_STATE generator=374004 state=walk',
    'P2_UMIMUSHI_STATE generator=374004 state=flick',
    'P2_UMIMUSHI_FLICK generator=374004 frame=9 pikmin=6',
    'P2_UMIMUSHI_STATE generator=374004 state=attack',
    'P2_UMIMUSHI_BITE generator=374004 frame=39 pikmin=1',
    'P2_UMIMUSHI_STATE generator=374004 state=eat',
    'P2_UMIMUSHI_EAT generator=374004 pikmin=1',
    'P2_UMIMUSHI_POS generator=374004 state=walk clip=run1 phase=0.10 '
    'x=-108.00 y=30.00 z=1850.00',
    'P2_UMIMUSHI_POS generator=374004 state=attack clip=attack1 phase=0.20 '
    'x=-100.00 y=30.00 z=1838.00',
])


class UmiMushiBehaviorTests(unittest.TestCase):
    def test_identity_and_position(self):
        self.assertEqual(UMI_ID, 374004)
        self.assertEqual(SOURCE_ID, 71)
        self.assertEqual(UMI_INDEX, 3)
        self.assertLess(squad_distance(ARENA_POSITION), 700.0,
                        'UmiMushi arena default must be inside the source sight radius')
        distance = squad_distance(BEHAVIOR_POSITION)
        self.assertLess(distance, ATTACK_HIT,
                        'UmiMushi fixture must start inside the source attack hit radius')

    def test_plan_positions_overrides_the_far_arena_default(self):
        positions, override = plan_positions([ARENA_POSITION] * 5)
        self.assertIsNotNone(override)
        self.assertEqual(positions[UMI_INDEX], BEHAVIOR_POSITION)
        self.assertFalse(override['production_placement'])
        self.assertLess(squad_distance(positions[UMI_INDEX]), ATTACK_HIT)

    def test_plan_positions_keeps_a_near_actor(self):
        positions = [(120.0, 30.0, 1850.0)] * 5
        positions[UMI_INDEX] = BEHAVIOR_POSITION
        planned, override = plan_positions(positions)
        self.assertIsNone(override)
        self.assertEqual(planned[UMI_INDEX], BEHAVIOR_POSITION)

    def test_validate_passes_on_source_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertTrue(result['checks']['animation_event_bite'])
        self.assertTrue(result['checks']['batch3_bind'])
        self.assertTrue(result['checks']['flick'])
        self.assertEqual(result['checks']['bite_frames'], [BITE_FRAME])
        self.assertGreater(result['motion_spread'], 5.0)

    def test_bite_outside_window_fails(self):
        early = GOOD_LOG.replace('frame=39', 'frame=20')
        result = validate(early, code=0)
        self.assertFalse(result['checks']['animation_event_bite'])
        self.assertFalse(result['passed'])

    def test_duplicate_eat_fails(self):
        result = validate(GOOD_LOG + '\nP2_UMIMUSHI_EAT generator=374004 pikmin=1', code=0)
        self.assertFalse(result['checks']['bite_eat_accounting'])
        self.assertFalse(result['passed'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text')


if __name__ == '__main__':
    unittest.main()
