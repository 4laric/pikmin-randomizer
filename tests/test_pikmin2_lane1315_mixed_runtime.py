"""Tests for the lane 13/15 three-identity mixed-scene probe."""
import unittest

import experimental.pikmin2_lane1315_mixed_runtime as mixed


GOOD_LOG = '\n'.join([
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy '
    'generator=211001 health=250.0 max_health=250.0 behavior=P1 purple_stun=bluekochappy_5s',
    'P2_DWARF_ORANGE_BANK poses=64 mod_bytes=1024000',
    'P2_DWARF_ORANGE_DRAW corpse=0',
    'P2_QURIONE_BIND generator=203001 source_id=16',
    'P2_ENEMY_READY species=Qurione behavior=native source_FSM=implemented reward=P2_Egg',
    'P2_QURIONE_DRAW corpse=0',
    'P2_SHIJIMI_BIND generator=204001 source_id=77',
    'P2_ENEMY_READY species=ShijimiChou behavior=native source_FSM=implemented',
    'P2_SHIJIMI_DRAW corpse=0',
])


def drop(fragment):
    return '\n'.join(line for line in GOOD_LOG.splitlines() if fragment not in line)


class Lane1315MixedTests(unittest.TestCase):
    def test_all_pass(self):
        result = mixed.evidence(GOOD_LOG, 1)
        self.assertTrue(result['passed'])
        self.assertTrue(all(result['checks'].values()))

    def test_each_identity_required(self):
        self.assertFalse(mixed.evidence(drop('source_id=44'), 1)['checks']['orange_bind'])
        self.assertFalse(mixed.evidence(drop('source_id=16'), 1)['checks']['qurione_bind'])
        self.assertFalse(mixed.evidence(drop('source_id=77'), 1)['checks']['shijimi_bind'])
        self.assertFalse(mixed.evidence(drop('P2_QURIONE_DRAW'), 1)['passed'])

    def test_extinction_fails(self):
        self.assertFalse(mixed.evidence(GOOD_LOG + '\nExtinction\n', 1)['passed'])

    def test_constants(self):
        self.assertEqual(mixed.ORANGE_GENERATOR, 211001)


if __name__ == '__main__':
    unittest.main()
