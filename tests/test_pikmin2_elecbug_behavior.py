"""Unit tests for the ElecBug source-behavior validator (#407)."""
import unittest

from experimental.pikmin2_elecbug_behavior import (
    BEHAVIOR_POSITION, ELECBUG_ID, ELECBUG_INDEX, SPECIES, SQUAD_X, SQUAD_Z, validate)

GOOD_LOG = '\n'.join([
    'P2_ELECBUG_BIND generator=346002 source_id=28 visual_only=0',
    'P2_ENEMY_READY species=ElecBug native_family=Chappy generator=346002 x=-180.0 y=30.0 '
    'z=1850.0 health=500.0 max_health=500.0 behavior=native source_FSM=implemented '
    'attack=discharge_receiver',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_ELECBUG_STATE generator=346002 state=charge',
    'P2_ELECBUG_DISCHARGE generator=346002 source_id=28 duration=3.000',
    'P2_ELECBUG_STATE generator=346002 state=discharge',
    'P2_ELECBUG_SHOCK generator=346002 pikmin=1',
    'P2_ELECBUG_STATE generator=346002 state=return',
])


class ElecBugBehaviorTests(unittest.TestCase):
    def test_identity_and_position(self):
        self.assertEqual(SPECIES[ELECBUG_INDEX], 'ElecBug')
        self.assertEqual(ELECBUG_ID, 346002)
        distance = min((BEHAVIOR_POSITION[0] - x) ** 2 + (BEHAVIOR_POSITION[2] - z) ** 2
                       for x in SQUAD_X for z in SQUAD_Z) ** 0.5
        self.assertLess(distance, 200.0, 'ElecBug must start inside the source sight radius')

    def test_validate_passes_on_source_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertEqual(result['shocks'], 1)
        self.assertEqual(result['discharges'], 1)

    def test_shock_without_discharge_fails(self):
        bad = GOOD_LOG.replace('P2_ELECBUG_DISCHARGE generator=346002 source_id=28 duration=3.000\n', '')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['shock_receiver'])
        self.assertFalse(result['passed'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text')


if __name__ == '__main__':
    unittest.main()
