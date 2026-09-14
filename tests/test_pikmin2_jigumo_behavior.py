"""Unit tests for the Jigumo source-behavior validator (#407)."""
import unittest

from experimental.pikmin2_jigumo_behavior import (
    ATTACK_RANGE, JIGUMO_ID, JIGUMO_INDEX, BEHAVIOR_POS, SATTACK_BITE_FRAME,
    SQUAD_X, SQUAD_Z, squad_distance, validate)

GOOD_LOG = '\n'.join([
    'P2_JIGUMO_BIND generator=374003 source_id=63 visual_only=0',
    'P2_BATCH3_BIND generator=374003 key=aquatic|Jigumo visual_only=0 native_fsm=implemented',
    'P2_ENEMY_READY species=Jigumo native_family=Chappy generator=374003 x=0.0 y=30.0 '
    'z=1850.0 health=500.0 max_health=500.0 behavior=native source_FSM=implemented '
    'attack=animation_event nest=2',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_JIGUMO_STATE generator=374003 state=appear',
    'P2_JIGUMO_STATE generator=374003 state=wait',
    'P2_JIGUMO_STATE generator=374003 state=sattack',
    'P2_JIGUMO_BITE generator=374003 frame=13 pikmin=1',
    'P2_JIGUMO_EAT generator=374003 pikmin=1',
    'P2_JIGUMO_POS generator=374003 state=sattack clip=sattack1 phase=0.20 '
    'x=0.00 y=30.00 z=1850.00',
])


class JigumoBehaviorTests(unittest.TestCase):
    def test_identity_and_position(self):
        self.assertEqual(JIGUMO_ID, 374003)
        self.assertEqual(JIGUMO_INDEX, 2)
        self.assertLess(squad_distance(BEHAVIOR_POS), ATTACK_RANGE,
                        'Jigumo fixture must start inside the source attack sweep')
        self.assertLess(squad_distance(BEHAVIOR_POS), 400.0,
                        'Jigumo fixture must start inside the source sight radius')

    def test_validate_passes_on_source_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertTrue(result['checks']['animation_event_bite'])
        self.assertTrue(result['checks']['batch3_bind'])
        self.assertEqual(result['checks']['bite_frames'], [SATTACK_BITE_FRAME])

    def test_bite_outside_window_fails(self):
        early = GOOD_LOG.replace('frame=13 ', 'frame=99 ')
        result = validate(early, code=0)
        self.assertFalse(result['checks']['animation_event_bite'])
        self.assertFalse(result['passed'])

    def test_duplicate_eat_fails(self):
        result = validate(GOOD_LOG + '\nP2_JIGUMO_EAT generator=374003 pikmin=1', code=0)
        self.assertFalse(result['checks']['bite_eat_accounting'])
        self.assertFalse(result['passed'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text')


if __name__ == '__main__':
    unittest.main()
