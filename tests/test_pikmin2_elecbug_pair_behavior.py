"""Unit tests for the ElecBug two-beetle partner-link validator (#407)."""
import math
import unittest

from experimental.pikmin2_elecbug_pair_behavior import (
    ELECBUG_A, ELECBUG_B, PAIR_A_POSITION, PAIR_B_POSITION, PAIR_DISTANCE,
    PAIR_RADIUS, SPECIES, SQUAD_X, SQUAD_Z, validate)

GOOD_LOG = '\n'.join([
    'P2_ELECBUG_BIND generator=346002 source_id=28 visual_only=0',
    'P2_ELECBUG_BIND generator=346008 source_id=28 visual_only=0',
    'P2_ENEMY_READY species=ElecBug native_family=Chappy generator=346002 x=-100.0 y=30.0 '
    'z=1850.0 health=500.0 max_health=500.0 behavior=native source_FSM=implemented '
    'attack=discharge_receiver',
    'P2_ENEMY_READY species=ElecBug native_family=Chappy generator=346008 x=-40.0 y=30.0 '
    'z=1850.0 health=500.0 max_health=500.0 behavior=native source_FSM=implemented '
    'attack=discharge_receiver',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_ELECBUG_STATE generator=346002 state=charge',
    'P2_ELECBUG_STATE generator=346008 state=charge',
    'P2_ELECBUG_LINK generator=346002 partner=346008',
    'P2_ELECBUG_STATE generator=346008 state=childcharge',
    'P2_ELECBUG_STATE generator=346002 state=discharge',
    'P2_ELECBUG_DISCHARGE generator=346002 source_id=28 duration=3.000 state=charge',
    'P2_ELECBUG_STATE generator=346008 state=childdischarge',
    'P2_ELECBUG_DISCHARGE generator=346008 source_id=28 duration=3.000 state=child',
    'P2_ELECBUG_SHOCK generator=346002 pikmin=1',
    'P2_ELECBUG_STATE generator=346002 state=return',
    'P2_ELECBUG_STATE generator=346008 state=wait',
    'P2_ELECBUG_UNLINK generator=346002',
    'P2_ELECBUG_UNLINK generator=346008',
    'P2_ELECBUG_FLIP generator=346008 source_id=28',
    'P2_ELECBUG_RECOVER generator=346008 source_id=28',
])


def distance_to_squad(position):
    return min(math.hypot(position[0] - x, position[2] - z)
               for x in SQUAD_X for z in SQUAD_Z)


class ElecBugPairBehaviorTests(unittest.TestCase):
    def test_identity_and_positions(self):
        self.assertEqual(SPECIES, ('ElecBug', 'ElecBug'))
        self.assertNotEqual(ELECBUG_A, ELECBUG_B)
        separation = math.hypot(PAIR_A_POSITION[0] - PAIR_B_POSITION[0],
                                PAIR_A_POSITION[2] - PAIR_B_POSITION[2])
        self.assertAlmostEqual(separation, PAIR_DISTANCE)
        self.assertLess(separation, PAIR_RADIUS,
                        'pair must start inside the source pairing radius')
        for position in (PAIR_A_POSITION, PAIR_B_POSITION):
            self.assertLess(distance_to_squad(position), 200.0,
                            'both beetles must start inside the source sight radius')

    def test_validate_passes_on_source_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertEqual(result['links'], [(ELECBUG_A, ELECBUG_B)])
        self.assertEqual(result['shocks'], 1)

    def test_missing_link_fails(self):
        bad = GOOD_LOG.replace('P2_ELECBUG_LINK generator=346002 partner=346008\n', '')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['pair_link'])
        self.assertFalse(result['passed'])

    def test_self_link_fails(self):
        bad = GOOD_LOG.replace('generator=346002 partner=346008',
                               'generator=346002 partner=346002')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['pair_link'])
        self.assertFalse(result['checks']['no_self_link'])
        self.assertFalse(result['passed'])

    def test_flip_without_recover_fails(self):
        bad = GOOD_LOG.replace('P2_ELECBUG_RECOVER generator=346008 source_id=28', '')
        result = validate(bad, code=0)
        # flip_path is informational (needs an unattended press); it no longer
        # gates `passed`, so assert the check itself.
        self.assertFalse(result['checks']['flip_path'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text')


if __name__ == '__main__':
    unittest.main()
