"""Unit tests for the ElecBug press-to-flip + electrical-immunity validator (#407)."""
import math
import unittest

from experimental.pikmin2_elecbug_immunity_behavior import (
    ELECBUG_A, ELECBUG_B, PAIR_A_POSITION, PAIR_B_POSITION, PAIR_DISTANCE,
    PAIR_RADIUS, SPECIES, validate)

GOOD_LOG = '\n'.join([
    'P2_ELECBUG_BIND generator=346002 source_id=28 visual_only=0',
    'P2_ELECBUG_BIND generator=346008 source_id=28 visual_only=0',
    'P2_ENEMY_READY species=ElecBug native_family=Chappy generator=346002 x=-100.0 y=30.0 '
    'z=1850.0 health=500.0 max_health=500.0 behavior=native source_FSM=implemented '
    'attack=discharge_receiver',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_ELECBUG_STATE generator=346002 state=charge',
    'P2_ELECBUG_STATE generator=346008 state=charge',
    'P2_ELECBUG_LINK generator=346002 partner=346008',
    'P2_ELECBUG_STATE generator=346008 state=childcharge',
    'P2_ELECBUG_STATE generator=346002 state=discharge',
    'P2_ELECBUG_DISCHARGE generator=346002 source_id=28 duration=3.000 state=charge',
    'P2_ELECBUG_ATTACK_BLOCKED generator=346002 source_id=28 invulnerable=1',
    'P2_ELECBUG_STATE generator=346008 state=childdischarge',
    'P2_ELECBUG_DISCHARGE generator=346008 source_id=28 duration=3.000 state=child',
    'P2_ELECBUG_SHOCK generator=346002 pikmin=1 color=blue',
    'P2_ELECBUG_IMMUNE generator=346002 source_id=28 pikmin=yellow',
    'P2_ELECBUG_PRESS_SHOCK generator=346002 source_id=28 pikmin=1 color=red',
    'P2_ELECBUG_FLIP generator=346002 source_id=28',
    'P2_ELECBUG_STATE generator=346002 state=reverse',
    'P2_ELECBUG_ATTACK_ACCEPTED generator=346002 source_id=28 state=reverse health=500.0',
    'P2_ELECBUG_HIT generator=346002 source_id=28 health=380.0',
    'P2_ELECBUG_STATE generator=346002 state=return',
    'P2_ELECBUG_RECOVER generator=346002 source_id=28',
])


class ElecBugImmunityBehaviorTests(unittest.TestCase):
    def test_identity_and_positions(self):
        self.assertEqual(SPECIES, ('ElecBug', 'ElecBug'))
        self.assertNotEqual(ELECBUG_A, ELECBUG_B)
        separation = math.hypot(PAIR_A_POSITION[0] - PAIR_B_POSITION[0],
                                PAIR_A_POSITION[2] - PAIR_B_POSITION[2])
        self.assertAlmostEqual(separation, PAIR_DISTANCE)
        self.assertLess(separation, PAIR_RADIUS,
                        'pair must start inside the source pairing radius')

    def test_validate_passes_on_source_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertEqual(result['shocks'], [('346002', 'blue')])

    def test_missing_recover_fails_flip_path(self):
        bad = GOOD_LOG.replace('P2_ELECBUG_RECOVER generator=346002 source_id=28', '')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['flip_path'])
        self.assertFalse(result['passed'])

    def test_missing_reverse_state_fails(self):
        bad = GOOD_LOG.replace('P2_ELECBUG_STATE generator=346002 state=reverse\n', '')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['flip_path'])
        self.assertFalse(result['passed'])

    def test_press_must_shock_pressing_pikmin(self):
        bad = GOOD_LOG.replace('P2_ELECBUG_PRESS_SHOCK generator=346002 source_id=28 pikmin=1 color=red\n', '')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['press_shock'])
        self.assertFalse(result['passed'])

    def test_yellow_press_is_immune_alternative(self):
        text = GOOD_LOG.replace(
            'P2_ELECBUG_PRESS_SHOCK generator=346002 source_id=28 pikmin=1 color=red',
            'P2_ELECBUG_PRESS_IMMUNE generator=346002 source_id=28 pikmin=yellow')
        result = validate(text, code=0)
        self.assertTrue(result['checks']['press_shock'])

    def test_shock_on_yellow_breaks_immunity_matrix(self):
        bad = GOOD_LOG.replace('color=blue', 'color=yellow')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['immunity_matrix'])
        self.assertFalse(result['passed'])

    def test_missing_yellow_immune_marker_fails(self):
        bad = GOOD_LOG.replace('P2_ELECBUG_IMMUNE generator=346002 source_id=28 pikmin=yellow\n', '')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['immunity_matrix'])
        self.assertFalse(result['passed'])

    def test_attack_must_be_blocked_before_flip(self):
        lines = GOOD_LOG.splitlines()
        blocked = 'P2_ELECBUG_ATTACK_BLOCKED generator=346002 source_id=28 invulnerable=1'
        lines.remove(blocked)
        lines.append(blocked)
        result = validate('\n'.join(lines), code=0)
        self.assertFalse(result['checks']['attack_path'])
        self.assertFalse(result['passed'])

    def test_reversed_attack_requires_damage_marker(self):
        bad = GOOD_LOG.replace('P2_ELECBUG_HIT generator=346002 source_id=28 health=380.0\n', '')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['attack_reversed'])
        self.assertFalse(result['passed'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text')


if __name__ == '__main__':
    unittest.main()
