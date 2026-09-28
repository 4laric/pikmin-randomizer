"""Unit tests for the TamagoMushi bounded group-behavior validator (#407/#165)."""
import unittest

from experimental.pikmin2_tamago_group_behavior import (
    FOLLOWER_IDS, GROUP_IDS, LEADER_ID, LEADER_POSITION, SQUAD_X, SQUAD_Z, validate)

GOOD_LOG = '\n'.join([
    'P2_TAMAGO_LEADER generator=346004 followers=4 surface_count=10 cave_count=30 '
    'source_group=createGroup',
    'P2_TAMAGO_GROUP leader=346004 follower=346014 source_id=68',
    'P2_TAMAGO_GROUP leader=346004 follower=346015 source_id=68',
    'P2_TAMAGO_GROUP leader=346004 follower=346016 source_id=68',
    'P2_TAMAGO_GROUP leader=346004 follower=346017 source_id=68',
    'P2_TAMAGO_BIND generator=346004 source_id=68 visual_only=0',
    'P2_ENEMY_READY species=TamagoMushi native_family=Chappy generator=346004 x=-100.0 y=30.0 '
    'z=1850.0 health=50.0 max_health=50.0 behavior=native source_FSM=implemented '
    'astonish=native_P1_approx honey=native',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_TAMAGO_STATE generator=346004 state=hide',
    'P2_TAMAGO_STATE generator=346004 state=appear',
    'P2_TAMAGO_STATE generator=346004 state=walk',
    'P2_TAMAGO_STATE generator=346014 state=appear',
    'P2_TAMAGO_STATE generator=346014 state=walk',
    'P2_TAMAGO_ASTONISH generator=346004 pikmin=1',
    'P2_TAMAGO_ASTONISH generator=346014 pikmin=1',
    'P2_TAMAGO_FOLLOW generator=346014 leader=346004 distance=30.00 state=walk x=-120.00 z=1850.00',
    'P2_TAMAGO_FOLLOW generator=346014 leader=346004 distance=42.00 state=walk x=-112.00 z=1848.00',
    'P2_TAMAGO_FOLLOW generator=346014 leader=346004 distance=37.00 state=walk x=-118.00 z=1844.00',
    'P2_TAMAGO_HONEY generator=346014 source_id=68',
])


class TamagoGroupBehaviorTests(unittest.TestCase):
    def test_identity_and_cluster(self):
        self.assertEqual(len(set(GROUP_IDS)), len(GROUP_IDS))
        self.assertEqual(LEADER_ID, min(GROUP_IDS))
        self.assertEqual(len(FOLLOWER_IDS), len(GROUP_IDS) - 1)
        distance = min((LEADER_POSITION[0] - x) ** 2 + (LEADER_POSITION[2] - z) ** 2
                       for x in SQUAD_X for z in SQUAD_Z) ** 0.5
        self.assertLess(distance, 100.0, 'leader must start next to the squad')

    def test_validate_passes_on_source_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertEqual(result['followers'], 4)
        self.assertGreater(result['follow_spread'], 5.0)

    def test_missing_group_bind_fails(self):
        stale = GOOD_LOG.replace('P2_TAMAGO_GROUP leader=346004 follower=346017 source_id=68\n', '')
        result = validate(stale, code=0)
        self.assertFalse(result['checks']['group_binds'])
        self.assertFalse(result['passed'])

    def test_missing_follow_motion_fails(self):
        stale = '\n'.join(line for line in GOOD_LOG.splitlines()
                          if not line.startswith('P2_TAMAGO_FOLLOW '))
        result = validate(stale, code=0)
        self.assertFalse(result['checks']['follow_motion'])
        self.assertFalse(result['passed'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text')


if __name__ == '__main__':
    unittest.main()
