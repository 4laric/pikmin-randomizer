"""Unit tests for the Armor source-behavior validator (#407)."""
import unittest

from experimental.pikmin2_armor_behavior import (
    ARMOR_ID, ARMOR_INDEX, BEHAVIOR_POSITION, SPECIES, SQUAD_X, SQUAD_Z, validate)

GOOD_LOG = '\n'.join([
    'P2_ARMOR_BIND generator=346001 source_id=15 visual_only=0',
    'P2_ENEMY_READY species=Armor native_family=Chappy generator=346001 x=180.0 y=30.0 '
    'z=1850.0 health=300.0 max_health=300.0 behavior=native source_FSM=implemented '
    'attack=animation_event',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_ARMOR_STATE generator=346001 state=appear',
    'P2_ARMOR_STATE generator=346001 state=move',
    'P2_ARMOR_STATE generator=346001 state=attack2',
    'P2_ARMOR_BITE generator=346001 frame=20.0 pikmin=1',
    'P2_ARMOR_STATE generator=346001 state=eat',
    'P2_ARMOR_EAT generator=346001 pikmin=1',
    'P2_ARMOR_STATE generator=346001 state=move',
])


class ArmorBehaviorTests(unittest.TestCase):
    def test_identity_and_position(self):
        self.assertEqual(SPECIES[ARMOR_INDEX], 'Armor')
        self.assertEqual(ARMOR_ID, 346001)
        distance = min((BEHAVIOR_POSITION[0] - x) ** 2 + (BEHAVIOR_POSITION[2] - z) ** 2
                       for x in SQUAD_X for z in SQUAD_Z) ** 0.5
        self.assertLess(distance, 200.0, 'Armor must start inside the source sight radius')

    def test_validate_passes_on_source_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertTrue(result['checks']['animation_event_bite'])
        self.assertEqual(result['checks']['bite_frames'], [20.0])

    def test_bite_outside_window_fails(self):
        early = GOOD_LOG.replace('frame=20.0', 'frame=15.0')
        result = validate(early, code=0)
        self.assertFalse(result['checks']['animation_event_bite'])
        self.assertFalse(result['passed'])

    def test_duplicate_eat_fails(self):
        result = validate(GOOD_LOG + '\nP2_ARMOR_EAT generator=346001 pikmin=1', code=0)
        self.assertFalse(result['checks']['bite_eat_accounting'])
        self.assertFalse(result['passed'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text')


if __name__ == '__main__':
    unittest.main()
