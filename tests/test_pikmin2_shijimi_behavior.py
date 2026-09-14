"""Unit tests for the ShijimiChou source-behavior validator (#407)."""
import unittest

from experimental.pikmin2_shijimi_behavior import (
    IDS, LEADER_ID, SIGHT, SQUAD_X, SQUAD_Z, squad_distance, validate)

GOOD_LOG = '\n'.join([
    'P2_SHIJIMI_BIND generator=375004 source_id=77 visual_only=0',
    'P2_SHIJIMI_SOURCE generator=375004 source=2 leader=1 lethal=7.0 nectar_rate=0.20',
    'P2_ENEMY_READY species=ShijimiChou native_family=Chappy generator=375004 x=-104.0 '
    'y=30.0 z=1832.0 health=200.0 max_health=200.0 behavior=native '
    'source_FSM=implemented attack=none nectar=native group_leader=1',
    'P2_BATCH3_BIND generator=375004 key=flying|ShijimiChou visual_only=0 native_fsm=implemented',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_SHIJIMI_STATE generator=375004 state=wait',
    'P2_SHIJIMI_STATE generator=375004 state=fly',
    'P2_SHIJIMI_POS generator=375004 state=wait clip=move phase=0.00 x=-104.00 z=1832.00 leader=1 fly=0.0',
    'P2_SHIJIMI_POS generator=375004 state=fly clip=move phase=0.30 x=-90.00 z=1810.00 leader=1 fly=60.0',
    'P2_SHIJIMI_DEAD generator=375004 source_id=77 health=0',
    'P2_SHIJIMI_STATE generator=375004 state=fall',
    'P2_SHIJIMI_STATE generator=375004 state=dead',
    'P2_SHIJIMI_POS generator=375004 state=dead clip=dead phase=0.50 x=-88.00 z=1808.00 leader=1 fly=210.0',
    'P2_SHIJIMI_NECTAR generator=375004 source=77 spec=0 plant=1 roll=0',
    'P2_SHIJIMI_HONEY generator=375004 source_id=77',
    'P2_SHIJIMI_KILL generator=375004 source_id=77',
    'P2_SHIJIMI_CORPSE generator=375004 source_id=77 native=host_die',
    'P2_BATCH3_DRAW corpse=1 key=flying|ShijimiChou clip=dead',
])


class ShijimiBehaviorTests(unittest.TestCase):
    def test_identity_and_position(self):
        self.assertEqual(LEADER_ID, 375004)
        self.assertEqual(len(IDS), 3)
        self.assertLess(squad_distance((-104.0, 30.0, 1832.0)), SIGHT,
                        'leader must start inside the source sight radius')

    def test_validate_passes_on_source_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertEqual(result['honey_events'], ['375004'])
        self.assertGreater(result['motion_spread'], 5.0)
        self.assertIn('fly', result['states_seen'])
        self.assertTrue(result['checks']['corpse'])

    def test_missing_nectar_fails(self):
        result = validate(GOOD_LOG.replace(
            'P2_SHIJIMI_HONEY generator=375004 source_id=77\n', ''), code=0)
        self.assertFalse(result['checks']['nectar'])
        self.assertFalse(result['passed'])

    def test_missing_fly_state_fails(self):
        result = validate(GOOD_LOG.replace(
            'P2_SHIJIMI_STATE generator=375004 state=fly\n', ''), code=0)
        self.assertFalse(result['checks']['fly'])
        self.assertFalse(result['passed'])

    def test_death_detected(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['checks']['death'])
        self.assertTrue(result['checks']['dead'])
        self.assertTrue(result['checks']['kill'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text')


if __name__ == '__main__':
    unittest.main()
