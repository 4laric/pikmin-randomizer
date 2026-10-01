"""Unit tests for the lane-13 Dwarf Orange FSM combat witness."""
import unittest

import experimental.pikmin2_dwarf_orange_fsm_witness as witness

FSM_LOG = '\n'.join([
    'P2_ENEMY_READY species=BlueKochappy source_id=44',
    'P2_DWARF_ORANGE_BANK',
    'P2_DWARF_ORANGE_ARENA_BIRTH id=211001 x=-150.0 y=30.0 z=1850.0 health=250.0',
    'P2_DWARF_ORANGE_ARENA_BIRTH id=211002 x=150.0 y=30.0 z=1550.0 health=130.0',
    'P2 window 960x540',
    'P2_KOCHAPPY_STATE generator=211001 state=walk',
    'P2_KOCHAPPY_ATTACK generator=211001 frame=8',
    'P2_KOCHAPPY_EAT generator=211001 eaten=1',
    'P2_KOCHAPPY_SWALLOW generator=211001 swallowed=1',
    'P2_KOCHAPPY_DEAD generator=211001 source_id=44',
    'P2_KOCHAPPY_CORPSE generator=211001',
    'DONE P2_DWARF_ORANGE_COMBAT',
])


class DwarfOrangeFsmWitnessTests(unittest.TestCase):
    def test_fsm_evidence_pass(self):
        result = witness.evidence(FSM_LOG, 0)
        self.assertTrue(result['passed'])
        self.assertTrue(all(result['checks'].values()))

    def test_fsm_evidence_requires_individual_markers(self):
        # eat: any line startswith 'P2_KOCHAPPY_EAT ' and contains ' eaten=1'
        no_eat = '\n'.join(line for line in FSM_LOG.splitlines()
                           if not line.startswith('P2_KOCHAPPY_EAT '))
        result = witness.evidence(no_eat, 0)
        self.assertFalse(result['checks']['eat'])
        self.assertFalse(result['passed'])

        # swallow: any line startswith 'P2_KOCHAPPY_SWALLOW ' and contains ' swallowed=1'
        no_swallow = '\n'.join(line for line in FSM_LOG.splitlines()
                               if not line.startswith('P2_KOCHAPPY_SWALLOW '))
        result = witness.evidence(no_swallow, 0)
        self.assertFalse(result['checks']['swallow'])
        self.assertFalse(result['passed'])

        # dead
        no_dead = '\n'.join(line for line in FSM_LOG.splitlines()
                            if 'P2_KOCHAPPY_DEAD ' not in line)
        result = witness.evidence(no_dead, 0)
        self.assertFalse(result['checks']['dead'])
        self.assertFalse(result['passed'])

        # corpse
        no_corpse = '\n'.join(line for line in FSM_LOG.splitlines()
                              if 'P2_KOCHAPPY_CORPSE ' not in line)
        result = witness.evidence(no_corpse, 0)
        self.assertFalse(result['checks']['corpse'])
        self.assertFalse(result['passed'])

        # completion
        no_completion = '\n'.join(line for line in FSM_LOG.splitlines()
                                  if 'DONE P2_DWARF_ORANGE_COMBAT' not in line)
        result = witness.evidence(no_completion, 0)
        self.assertFalse(result['checks']['completion'])
        self.assertFalse(result['passed'])

    def test_fsm_evidence_requires_zero_exit(self):
        self.assertFalse(witness.evidence(FSM_LOG, 1)['passed'])

    def test_fsm_evidence_requires_no_extinction(self):
        with_extinction = FSM_LOG + '\nP2 Extinction'
        result = witness.evidence(with_extinction, 0)
        self.assertFalse(result['checks']['no_extinction'])
        self.assertFalse(result['passed'])


if __name__ == '__main__':
    unittest.main()
