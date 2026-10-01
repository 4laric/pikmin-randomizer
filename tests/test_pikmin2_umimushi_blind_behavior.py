"""Unit tests for the Blind UmiMushi source-behavior validator (#407/#167)."""
import unittest

from experimental.pikmin2_umimushi_blind_behavior import (
    ATTACK_HIT, BLIND_FAR_ID, BLIND_FAR_INDEX, BLIND_FAR_POSITION, BLIND_ID, BLIND_INDEX,
    BLIND_LIFE, BLIND_MOVE_FRAMES, BLIND_POSITION, BLIND_SCALE, BLIND_SOURCE_ID,
    BLIND_TURN_RATE, BLIND_WAIT_FRAMES, BITE_FRAME, ORDINARY_ID, ORDINARY_SOURCE_ID,
    SIGHT, squad_distance, validate)

GOOD_LOG = '\n'.join([
    'P2_UMIMUSHI_BIND generator=374004 source_id=71 visual_only=0 blind=0',
    'P2_UMIMUSHI_BIND generator=374006 source_id=101 visual_only=0 blind=1',
    'P2_UMIMUSHI_BIND generator=374007 source_id=101 visual_only=0 blind=1',
    'P2_UMIMUSHI_BLIND generator=374006 scale=0.500 health=800.0 turn_rate=0.30 '
    'wait_frames=200 move_frames=200',
    'P2_UMIMUSHI_BLIND generator=374007 scale=0.500 health=800.0 turn_rate=0.30 '
    'wait_frames=200 move_frames=200',
    'P2_BATCH3_BIND generator=374004 key=aquatic|UmiMushi visual_only=0 native_fsm=implemented',
    'P2_BATCH3_BIND generator=374006 key=aquatic|UmiMushiBlind visual_only=0 '
    'native_fsm=implemented',
    'P2_BATCH3_BIND generator=374007 key=aquatic|UmiMushiBlind visual_only=0 '
    'native_fsm=implemented',
    'P2_ENEMY_READY species=UmiMushiBlind native_family=Chappy generator=374006 '
    'x=-108.0000000 y=30.0000000 z=1850.0000000 health=800.0 max_health=800.0 '
    'behavior=native source_FSM=implemented attack=animation_event water=absent',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_UMIMUSHI_STATE generator=374006 state=walk',
    'P2_UMIMUSHI_BLIND_WAIT generator=374006',
    'P2_UMIMUSHI_BLIND_MOVE generator=374006',
    'P2_UMIMUSHI_BLIND_MOVE generator=374007',
    'P2_UMIMUSHI_BLIND_WAIT generator=374007',
    'P2_UMIMUSHI_STATE generator=374006 state=attack',
    'P2_UMIMUSHI_BITE generator=374006 frame=39 pikmin=1',
    'P2_UMIMUSHI_STATE generator=374006 state=eat',
    'P2_UMIMUSHI_EAT generator=374006 pikmin=1',
    'P2_UMIMUSHI_POS generator=374006 state=walk clip=run1 phase=0.10 '
    'x=-108.00 y=30.00 z=1850.00',
    'P2_UMIMUSHI_POS generator=374006 state=attack clip=attack1 phase=0.20 '
    'x=-100.00 y=30.00 z=1838.00',
    'P2_UMIMUSHI_POS generator=374007 state=walk clip=run1 phase=0.10 '
    'x=200.00 y=30.00 z=1850.00',
    'P2_UMIMUSHI_POS generator=374007 state=walk clip=run1 phase=0.60 '
    'x=160.00 y=30.00 z=1840.00',
])


class UmiMushiBlindBehaviorTests(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(BLIND_ID, 374006)
        self.assertEqual(BLIND_SOURCE_ID, 101)
        self.assertEqual(ORDINARY_ID, 374004)
        self.assertEqual(ORDINARY_SOURCE_ID, 71)
        self.assertEqual(BLIND_FAR_ID, 374007)
        self.assertEqual(BLIND_INDEX, 2)  # focused roster: ordinary UmiMushi, P1 control, near Blind
        self.assertEqual(BLIND_FAR_INDEX, 3)
        self.assertEqual(BLIND_LIFE, 800.0)
        self.assertEqual(BLIND_SCALE, 0.5)
        self.assertEqual(BLIND_TURN_RATE, 0.30)
        self.assertEqual(BLIND_WAIT_FRAMES, 200.0)
        self.assertEqual(BLIND_MOVE_FRAMES, 200.0)

    def test_fixture_placement(self):
        self.assertLess(squad_distance(BLIND_POSITION), ATTACK_HIT)
        self.assertLess(squad_distance(BLIND_POSITION), SIGHT)
        self.assertGreater(squad_distance(BLIND_FAR_POSITION), ATTACK_HIT)
        self.assertLess(squad_distance(BLIND_FAR_POSITION), SIGHT)

    def test_validate_passes_on_source_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertTrue(result['checks']['animation_event_bite'])
        self.assertTrue(result['checks']['batch3_bind'])
        self.assertTrue(result['checks']['ordinary_batch3_bind'])
        self.assertTrue(result['checks']['blind_pacing'])
        self.assertEqual(result['checks']['bite_frames'], [BITE_FRAME])
        self.assertGreater(result['motion_spread'], 5.0)
        self.assertTrue(result['gates']['identity'])
        self.assertTrue(result['gates']['movement'])
        self.assertTrue(result['gates']['attack_receiver'])
        self.assertFalse(result['gates']['death'])
        self.assertFalse(result['gates']['cleanup'])

    def test_blind_bind_identity_is_required(self):
        broken = GOOD_LOG.replace(
            'P2_UMIMUSHI_BIND generator=374006 source_id=101 visual_only=0 blind=1',
            'P2_UMIMUSHI_BIND generator=374006 source_id=71 visual_only=0 blind=0')
        result = validate(broken, code=0)
        self.assertFalse(result['checks']['identity'])
        self.assertFalse(result['passed'])

    def test_blind_scale_config_is_required(self):
        broken = GOOD_LOG.replace('scale=0.500', 'scale=1.000')
        result = validate(broken, code=0)
        self.assertFalse(result['checks']['config'])
        self.assertFalse(result['passed'])

    def test_missing_pace_is_reported_but_not_gating(self):
        un = '\n'.join(line for line in GOOD_LOG.splitlines()
                       if 'P2_UMIMUSHI_BLIND_' not in line)
        result = validate(un, code=0)
        self.assertFalse(result['checks']['blind_pacing'])
        self.assertTrue(result['passed'], result['checks'])

    def test_bite_outside_window_fails(self):
        early = GOOD_LOG.replace('frame=39', 'frame=20')
        result = validate(early, code=0)
        self.assertFalse(result['checks']['animation_event_bite'])
        self.assertFalse(result['passed'])

    def test_duplicate_eat_fails(self):
        result = validate(GOOD_LOG + '\nP2_UMIMUSHI_EAT generator=374006 pikmin=1', code=0)
        self.assertFalse(result['checks']['bite_eat_accounting'])
        self.assertFalse(result['passed'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text')


if __name__ == '__main__':
    unittest.main()
