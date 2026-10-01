"""Unit tests for the Hana source-behavior validator (#407)."""
import unittest

from experimental.pikmin2_hana_behavior import (
    BEHAVIOR_POSITION, HANA_ID, HANA_INDEX, SPECIES, SQUAD_X, SQUAD_Z, validate)

GOOD_LOG = '\n'.join([
    'P2_HANA_BIND generator=346006 source_id=84 visual_only=0',
    'P2_ENEMY_READY species=Hana native_family=Chappy generator=346006 x=-100.0 y=30.0 '
    'z=1850.0 health=2500.0 max_health=2500.0 behavior=native source_FSM=implemented '
    'attack=animation_event',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_HANA_STATE generator=346006 state=sleep',
    'P2_HANA_STATE generator=346006 state=emerge',
    'P2_HANA_STATE generator=346006 state=walk',
    'P2_HANA_STATE generator=346006 state=attack',
    'P2_HANA_BITE generator=346006 frame=18.0 pikmin=1',
    'P2_HANA_EAT generator=346006 pikmin=1',
    'P2_HANA_STATE generator=346006 state=eat',
    'P2_HANA_STATE generator=346006 state=walk',
    'P2_HANA_POS generator=346006 state=sleep clip=type1 phase=0.00 x=-100.00 z=1850.00',
    'P2_HANA_POS generator=346006 state=walk clip=move1 phase=0.30 x=-100.00 z=1826.00',
])


class HanaBehaviorTests(unittest.TestCase):
    def test_identity_and_position(self):
        self.assertEqual(SPECIES[HANA_INDEX], 'Hana')
        self.assertEqual(HANA_INDEX, 5)
        self.assertEqual(HANA_ID, 346006)
        distance = min((BEHAVIOR_POSITION[0] - x) ** 2 + (BEHAVIOR_POSITION[2] - z) ** 2
                       for x in SQUAD_X for z in SQUAD_Z) ** 0.5
        self.assertLess(distance, 500.0, 'Hana must start inside the source sight wake radius')

    def test_validate_passes_on_source_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertTrue(result['checks']['animation_event_bite'])
        self.assertEqual(result['checks']['bite_frames'], [18.0])
        self.assertGreater(result['motion_spread'], 5.0)

    def test_bite_outside_window_fails(self):
        late = GOOD_LOG.replace('frame=18.0', 'frame=80.0')
        result = validate(late, code=0)
        self.assertFalse(result['checks']['animation_event_bite'])
        self.assertFalse(result['passed'])

    def test_duplicate_eat_fails(self):
        result = validate(GOOD_LOG + '\nP2_HANA_EAT generator=346006 pikmin=1', code=0)
        self.assertFalse(result['checks']['bite_eat_accounting'])
        self.assertFalse(result['passed'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text')


if __name__ == '__main__':
    unittest.main()
