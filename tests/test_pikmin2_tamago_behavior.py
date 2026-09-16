"""Unit tests for the TamagoMushi source-behavior validator (#407)."""
import unittest

from experimental.pikmin2_tamago_behavior import (
    BEHAVIOR_POSITION, SPECIES, SQUAD_X, SQUAD_Z, TAMAGO_ID, TAMAGO_INDEX, validate)

GOOD_LOG = '\n'.join([
    'P2_TAMAGO_BIND generator=346004 source_id=68 visual_only=0',
    'P2_ENEMY_READY species=TamagoMushi native_family=Chappy generator=346004 x=60.0 y=30.0 '
    'z=1850.0 health=50.0 max_health=50.0 behavior=native source_FSM=implemented '
    'astonish=native_P1_approx honey=native',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_TAMAGO_STATE generator=346004 state=hide',
    'P2_TAMAGO_STATE generator=346004 state=appear',
    'P2_TAMAGO_STATE generator=346004 state=wait',
    'P2_TAMAGO_STATE generator=346004 state=walk',
    'P2_TAMAGO_ASTONISH generator=346004 pikmin=1',
    'P2_TAMAGO_POS generator=346004 state=walk clip=move phase=0.10 x=-100.00 z=1850.00',
    'P2_TAMAGO_POS generator=346004 state=walk clip=move phase=0.60 x=-80.00 z=1846.00',
])


class TamagoBehaviorTests(unittest.TestCase):
    def test_identity_and_position(self):
        self.assertEqual(SPECIES[TAMAGO_INDEX], 'TamagoMushi')
        self.assertEqual(TAMAGO_ID, 346004)
        distance = min((BEHAVIOR_POSITION[0] - x) ** 2 + (BEHAVIOR_POSITION[2] - z) ** 2
                       for x in SQUAD_X for z in SQUAD_Z) ** 0.5
        self.assertLess(distance, 100.0, 'TamagoMushi must start next to the squad')

    def test_validate_passes_on_source_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertEqual(result['astonish'], 1)
        self.assertGreater(result['motion_spread'], 5.0)

    def test_missing_astonish_fails(self):
        result = validate(GOOD_LOG.replace('P2_TAMAGO_ASTONISH generator=346004 pikmin=1', ''), code=0)
        self.assertFalse(result['checks']['astonish_receiver'])
        self.assertFalse(result['passed'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text')


if __name__ == '__main__':
    unittest.main()
