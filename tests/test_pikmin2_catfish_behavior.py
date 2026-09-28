"""Unit tests for the Catfish source-behavior validator (#407)."""
import unittest

from experimental.pikmin2_catfish_behavior import (
    ATTACK_RANGE, BITE_FRAME, CATFISH_ID, CATFISH_INDEX, BEHAVIOR_POS,
    SQUAD_X, SQUAD_Z, validate)

GOOD_LOG = '\n'.join([
    'P2_CATFISH_BIND generator=374001 source_id=26 visual_only=0',
    'P2_BATCH3_BIND generator=374001 key=aquatic|Catfish visual_only=0 native_fsm=implemented',
    'P2_ENEMY_READY species=Catfish native_family=Namazu generator=374001 x=-108.0 y=30.0 '
    'z=1850.0 health=200.0 max_health=200.0 behavior=native source_FSM=implemented '
    'attack=animation_event water=absent',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_CATFISH_STATE generator=374001 state=wait',
    'P2_CATFISH_STATE generator=374001 state=attack',
    'P2_CATFISH_BITE generator=374001 frame=17.0 pikmin=1',
    'P2_CATFISH_EAT generator=374001 pikmin=1',
    'P2_CATFISH_POS generator=374001 state=attack clip=attack phase=0.20 '
    'x=-108.00 y=30.00 z=1850.00',
])


class CatfishBehaviorTests(unittest.TestCase):
    def test_identity_and_position(self):
        self.assertEqual(CATFISH_ID, 374001)
        self.assertEqual(CATFISH_INDEX, 0)
        distance = min((BEHAVIOR_POS[0] - x) ** 2 + (BEHAVIOR_POS[2] - z) ** 2
                       for x in SQUAD_X for z in SQUAD_Z) ** 0.5
        self.assertLess(distance, ATTACK_RANGE,
                        'Catfish fixture must start inside the source attack sweep')

    def test_validate_passes_on_source_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertTrue(result['checks']['animation_event_bite'])
        self.assertTrue(result['checks']['batch3_bind'])
        self.assertEqual(result['checks']['bite_frames'], [BITE_FRAME])

    def test_bite_outside_window_fails(self):
        early = GOOD_LOG.replace('frame=17.0', 'frame=15.0')
        result = validate(early, code=0)
        self.assertFalse(result['checks']['animation_event_bite'])
        self.assertFalse(result['passed'])

    def test_duplicate_eat_fails(self):
        result = validate(GOOD_LOG + '\nP2_CATFISH_EAT generator=374001 pikmin=1', code=0)
        self.assertFalse(result['checks']['bite_eat_accounting'])
        self.assertFalse(result['passed'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text')


if __name__ == '__main__':
    unittest.main()
