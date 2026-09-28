"""Tests for the lane-15 Qurione + ShijimiChou mixed-scene probe (#166)."""
import unittest

import experimental.pikmin2_lane15_mixed_runtime as mixed


GOOD_LOG = '\n'.join([
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_QURIONE_BIND generator=203001 source_id=16 visual_only=0',
    'P2_ENEMY_READY species=Qurione native_family=Qurione generator=203001 '
    'behavior=native source_FSM=implemented reward=P2_Egg',
    'P2_QURIONE_BANK poses=21 mod_bytes=410592',
    'P2_QURIONE_STATE generator=203001 state=appear',
    'P2_QURIONE_STATE generator=203001 state=move',
    'P2_QURIONE_STATE generator=203001 state=dead',
    'P2_QURIONE_DRAW corpse=0',
    'P2_SHIJIMI_BIND generator=204001 source_id=77 visual_only=0',
    'P2_ENEMY_READY species=ShijimiChou native_family=Chappy generator=204001 '
    'behavior=native source_FSM=implemented',
    'P2_SHIJIMI_BANK poses=6 mod_bytes=38976',
    'P2_SHIJIMI_DRAW corpse=0',
    'P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1',
])


def drop(fragment):
    return '\n'.join(line for line in GOOD_LOG.splitlines() if fragment not in line)


class Lane15MixedTests(unittest.TestCase):
    def test_all_pass(self):
        result = mixed.evidence(GOOD_LOG, 1)
        self.assertTrue(result['passed'])
        self.assertTrue(all(result['checks'].values()))
        self.assertEqual(result['qurione_states'], ['appear', 'dead', 'move'])

    def test_missing_identities_fail(self):
        self.assertFalse(mixed.evidence(drop('source_id=16'), 1)['checks']['qurione_bind'])
        self.assertFalse(mixed.evidence(drop('source_id=77'), 1)['checks']['shijimi_bind'])
        self.assertFalse(mixed.evidence(drop('P2_SHIJIMI_DRAW'), 1)['passed'])

    def test_extinction_fails(self):
        result = mixed.evidence(GOOD_LOG + '\nExtinction\n', 1)
        self.assertFalse(result['checks']['no_extinction'])
        self.assertFalse(result['passed'])

    def test_constants(self):
        self.assertEqual(mixed.QURIONE_GENERATOR, 203001)
        self.assertEqual(mixed.SHIJIMI_GENERATOR, 204001)
        self.assertEqual(mixed.CONTROL_GENERATOR, 204002)


if __name__ == '__main__':
    unittest.main()
