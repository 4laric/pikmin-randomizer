"""Unit tests for the Hanachirashi source-behavior validator (#407)."""
import unittest

from experimental.pikmin2_hanachirashi_behavior import (
    HANA_ID, HANA_POSITION, SIGHT, SQUAD_X, SQUAD_Z, validate)

GOOD_LOG = '\n'.join([
    'P2_HANACHIRASHI_BIND generator=375002 source_id=55 visual_only=0',
    'P2_ENEMY_READY species=Hanachirashi native_family=Mar generator=375002 x=-50.0 y=30.0 '
    'z=1850.0 health=1800.0 max_health=1800.0 behavior=native source_FSM=implemented '
    'attack=interactflick_wither',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_HANACHIRASHI_STATE generator=375002 state=wait',
    'P2_HANACHIRASHI_STATE generator=375002 state=chase',
    'P2_HANACHIRASHI_STATE generator=375002 state=attack',
    'P2_HANACHIRASHI_BLOW generator=375002 pikmin=1',
    'P2_HANACHIRASHI_STATE generator=375002 state=laugh',
    'P2_HANACHIRASHI_STATE generator=375002 state=wait',
    'P2_HANACHIRASHI_POS generator=375002 state=wait clip=move1 phase=0.00 x=-50.00 z=1850.00',
    'P2_HANACHIRASHI_POS generator=375002 state=chase clip=move1 phase=0.30 x=-46.00 z=1840.00',
    'P2_HANACHIRASHI_POS generator=375002 state=attack clip=attack phase=0.50 x=-44.00 z=1836.00',
])


class HanachirashiBehaviorTests(unittest.TestCase):
    def test_identity_and_position(self):
        self.assertEqual(HANA_ID, 375002)
        distance = min((HANA_POSITION[0] - x) ** 2 + (HANA_POSITION[2] - z) ** 2
                       for x in SQUAD_X for z in SQUAD_Z) ** 0.5
        self.assertLess(distance, SIGHT, 'Hanachirashi must start inside the source sight radius')

    def test_validate_passes_on_source_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertEqual(result['checks']['blow_pikmin'], 1)
        self.assertTrue(result['checks']['laugh'])
        self.assertGreater(result['motion_spread'], 5.0)
        self.assertIn('attack', result['states_seen'])

    def test_blow_without_pikmin_fails(self):
        result = validate(GOOD_LOG.replace(
            'P2_HANACHIRASHI_BLOW generator=375002 pikmin=1',
            'P2_HANACHIRASHI_BLOW generator=375002 pikmin=0'), code=0)
        self.assertFalse(result['checks']['blow'])
        self.assertFalse(result['passed'])

    def test_missing_attack_state_fails(self):
        result = validate(GOOD_LOG.replace(
            'P2_HANACHIRASHI_STATE generator=375002 state=attack\n', ''), code=0)
        self.assertFalse(result['checks']['attack'])
        self.assertFalse(result['passed'])

    def test_laugh_state_detected(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['checks']['laugh'])
        self.assertIn('laugh', result['states_seen'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text')


if __name__ == '__main__':
    unittest.main()
