"""Unit tests for the Mar source-behavior validator (#375)."""
import unittest

from experimental.pikmin2_mar_behavior import (
    MAR_ID, MAR_POSITION, SIGHT, SQUAD_X, SQUAD_Z, validate)

GOOD_LOG = '\n'.join([
    'P2_MAR_BIND generator=375001 source_id=29 visual_only=0',
    'P2_ENEMY_READY species=Mar native_family=Mar generator=375001 x=-150.0 y=30.0 '
    'z=1850.0 health=3000.0 max_health=3000.0 behavior=native source_FSM=implemented '
    'attack=interactflick_wind',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_MAR_STATE generator=375001 state=wait',
    'P2_MAR_STATE generator=375001 state=chase',
    'P2_MAR_STATE generator=375001 state=attack',
    'P2_MAR_BLOW generator=375001 pikmin=1',
    'P2_MAR_STATE generator=375001 state=wait',
    'P2_MAR_POS generator=375001 state=wait clip=move1 phase=0.00 x=-150.00 z=1850.00',
    'P2_MAR_POS generator=375001 state=chase clip=move1 phase=0.30 x=-146.00 z=1840.00',
    'P2_MAR_POS generator=375001 state=attack clip=attack phase=0.50 x=-144.00 z=1836.00',
])


class MarBehaviorTests(unittest.TestCase):
    def test_identity_and_position(self):
        self.assertEqual(MAR_ID, 375001)
        distance = min((MAR_POSITION[0] - x) ** 2 + (MAR_POSITION[2] - z) ** 2
                       for x in SQUAD_X for z in SQUAD_Z) ** 0.5
        self.assertLess(distance, SIGHT, 'Mar must start inside the source sight radius')

    def test_validate_passes_on_source_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertEqual(result['checks']['blow_pikmin'], 1)
        self.assertGreater(result['motion_spread'], 5.0)
        self.assertIn('attack', result['states_seen'])

    def test_blow_without_pikmin_fails(self):
        result = validate(GOOD_LOG.replace('P2_MAR_BLOW generator=375001 pikmin=1',
                                           'P2_MAR_BLOW generator=375001 pikmin=0'), code=0)
        self.assertFalse(result['checks']['blow'])
        self.assertFalse(result['passed'])

    def test_missing_attack_state_fails(self):
        result = validate(GOOD_LOG.replace(
            'P2_MAR_STATE generator=375001 state=attack\n', ''), code=0)
        self.assertFalse(result['checks']['attack'])
        self.assertFalse(result['passed'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text')


if __name__ == '__main__':
    unittest.main()
