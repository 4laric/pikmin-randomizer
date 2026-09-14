"""Tests for the four-identity cohort mixed-scene probe."""
import unittest

import experimental.pikmin2_cohort_mixed_runtime as mixed


GOOD_LOG = '\n'.join([
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1',
    'P2_ENEMY_READY species=YellowKochappy native_family=Chappy generator=5001 behavior=P1',
    'P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=211001 '
    'health=250.0 max_health=250.0 behavior=P1',
    'P2_QURIONE_BIND generator=203001 source_id=16',
    'P2_ENEMY_READY species=Qurione behavior=native source_FSM=implemented reward=P2_Egg',
    'P2_SHIJIMI_BIND generator=204001 source_id=77',
    'P2_ENEMY_READY species=ShijimiChou behavior=native source_FSM=implemented',
    'P2_DWARF_ORANGE_DRAW corpse=0',
    'P2_SNOW_DRAW corpse=0',
    'P2_QURIONE_DRAW corpse=0',
    'P2_SHIJIMI_DRAW corpse=0',
])


def drop(fragment):
    return '\n'.join(line for line in GOOD_LOG.splitlines() if fragment not in line)


class CohortMixedTests(unittest.TestCase):
    def test_all_pass(self):
        result = mixed.evidence(GOOD_LOG, 1)
        self.assertTrue(result['passed'])
        self.assertTrue(all(result['checks'].values()))

    def test_each_identity_required(self):
        self.assertFalse(mixed.evidence(drop('species=BlueKochappy'), 1)['checks']['dwarf_orange'])
        self.assertFalse(mixed.evidence(drop('species=YellowKochappy'), 1)['checks']['snow'])
        self.assertFalse(mixed.evidence(drop('P2_QURIONE_BIND'), 1)['checks']['qurione'])
        self.assertFalse(mixed.evidence(drop('P2_SHIJIMI_BIND'), 1)['checks']['shijimi'])

    def test_extinction_fails(self):
        self.assertFalse(mixed.evidence(GOOD_LOG + '\nExtinction\n', 1)['passed'])

    def test_constants(self):
        self.assertEqual(mixed.QURIONE_IDS, (203001,))
        self.assertEqual(mixed.SHIJIMI_IDS, (204001, 204002))


if __name__ == '__main__':
    unittest.main()
