"""Unit tests for the lane-13 Dwarf Orange natural-death cleanup witness (#120)."""
import unittest

import experimental.pikmin2_dwarf_orange_cleanup as cleanup

RED_COMBAT = 'class RoomApp : public PlugPikiApp {\n};\nint main(\n'

CLEANUP_LOG = '\n'.join([
    'P2_DWARF_ORANGE_ARENA_BIRTH id=211001 x=-150.0 y=30.0 z=1850.0 health=250.0',
    'P2_DWARF_ORANGE_ARENA_BIRTH id=211002 x=150.0 y=30.0 z=1550.0 health=130.0',
    'P2_KOCHAPPY_STATE generator=211001 state=dead',
    'P2_KOCHAPPY_DEAD generator=211001 source_id=44 health=0.0',
    'P2_KOCHAPPY_CORPSE generator=211001 source_id=44 native=host_escape_now',
    'P2_DWARF_ORANGE_DRAW corpse=1',
    'P2_DWARF_ORANGE_P1_HAUL tick=120 state=0 alive=1 distance=4.59 transport=11 goal=1',
    'P2_DWARF_ORANGE_P1_HAUL tick=600 state=1 alive=1 distance=544.74 transport=0 goal=1',
    'P2_DWARF_ORANGE_FORGET registered=1',
    'P2_KOCHAPPY_FSM_FORGET registered=1',
    'P2_DWARF_ORANGE_P1_REMOVED distance=544.7502',
    'PASS P2_DWARF_ORANGE_P1_CLEANUP distance=544.7502 reached=1',
])


class DwarfOrangeCleanupTests(unittest.TestCase):
    def test_cleanup_transform(self):
        out = cleanup.instrument(RED_COMBAT)
        self.assertIn('P2_DWARF_ORANGE_P1_REMOVED', out)
        self.assertIn('P2_DWARF_ORANGE_P1_POST_REMOVAL', out)
        self.assertIn('pc_p2_dwarf_orange', out)
        self.assertNotIn('P2_RED', out)
        self.assertNotIn('186001', out)
        self.assertNotIn('pc_p2_kochappy', out)

    def test_cleanup_evidence_pass(self):
        result = cleanup.evidence(CLEANUP_LOG, 0)
        self.assertTrue(result['passed'])
        self.assertTrue(all(result['checks'].values()))

    def test_cleanup_evidence_requires_forget(self):
        for marker in ('P2_DWARF_ORANGE_FORGET ', 'P2_KOCHAPPY_FSM_FORGET '):
            without = '\n'.join(line for line in CLEANUP_LOG.splitlines() if marker not in line)
            result = cleanup.evidence(without, 0)
            self.assertFalse(result['passed'])

    def test_cleanup_evidence_requires_removal_and_death(self):
        no_removed = CLEANUP_LOG.replace('P2_DWARF_ORANGE_P1_REMOVED distance=544.7502\n', '')
        self.assertFalse(cleanup.evidence(no_removed, 0)['checks']['corpse_removed'])
        no_death = CLEANUP_LOG.replace(
            'P2_KOCHAPPY_STATE generator=211001 state=dead\n', '')
        self.assertFalse(cleanup.evidence(no_death, 0)['checks']['fsm_death'])

    def test_cleanup_evidence_requires_completion_and_exit(self):
        no_pass = CLEANUP_LOG.replace('PASS P2_DWARF_ORANGE_P1_CLEANUP', 'PASS P2_DWARF_ORANGE_P1_DELIVERY')
        self.assertFalse(cleanup.evidence(no_pass, 0)['passed'])
        self.assertFalse(cleanup.evidence(CLEANUP_LOG, 1)['passed'])


if __name__ == '__main__':
    unittest.main()
