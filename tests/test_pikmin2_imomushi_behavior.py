"""Unit tests for the Imomushi source-behavior validator (#407)."""
import unittest

from experimental.pikmin2_imomushi_behavior import (
    BEHAVIOR_POSITION, IMOMUSHI_ID, IMOMUSHI_INDEX, SPECIES, SQUAD_X, SQUAD_Z,
    validate)

GOOD_LOG = '\n'.join([
    'P2_IMOMUSHI_BIND generator=346003 source_id=65 visual_only=0',
    'P2_ENEMY_READY species=Imomushi native_family=Chappy generator=346003 x=-60.0 y=30.0 '
    'z=1850.0 health=200.0 max_health=200.0 behavior=native source_FSM=implemented '
    'plant_eat=source_backed_NA',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_IMOMUSHI_HIDDEN generator=346003 hidden=1',
    'P2_IMOMUSHI_STATE generator=346003 state=appear',
    'P2_IMOMUSHI_STATE generator=346003 state=move',
    'P2_IMOMUSHI_STATE generator=346003 state=gohome',
    'P2_IMOMUSHI_STATE generator=346003 state=dive',
    'P2_IMOMUSHI_POS generator=346003 state=move clip=move1 phase=0.10 x=-100.00 z=1850.00',
    'P2_IMOMUSHI_POS generator=346003 state=move clip=move1 phase=0.60 x=-80.00 z=1846.00',
])


class ImomushiBehaviorTests(unittest.TestCase):
    def test_identity_and_position(self):
        self.assertEqual(SPECIES[IMOMUSHI_INDEX], 'Imomushi')
        self.assertEqual(IMOMUSHI_ID, 346003)
        distance = min((BEHAVIOR_POSITION[0] - x) ** 2 + (BEHAVIOR_POSITION[2] - z) ** 2
                       for x in SQUAD_X for z in SQUAD_Z) ** 0.5
        self.assertLess(distance, 100.0, 'Imomushi must start next to the squad')

    def test_validate_passes_on_source_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertGreater(result['motion_spread'], 5.0)

    def test_missing_move_fails(self):
        result = validate(GOOD_LOG.replace('P2_IMOMUSHI_STATE generator=346003 state=move\n', ''), code=0)
        self.assertFalse(result['checks']['move'])
        self.assertFalse(result['passed'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text')


if __name__ == '__main__':
    unittest.main()
