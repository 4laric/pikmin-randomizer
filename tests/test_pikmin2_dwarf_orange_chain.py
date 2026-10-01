"""Unit tests for the lane-13 Dwarf Orange delivery and re-entry probes (#120)."""
import unittest

import experimental.pikmin2_dwarf_orange_delivery as delivery
import experimental.pikmin2_dwarf_orange_reentry as reentry


RED_COMBAT = 'class RoomApp : public PlugPikiApp {\n};\nint main(\n'

DELIVERY_LOG = '\n'.join([
    'P2_DWARF_ORANGE_ARENA_BIRTH id=211001 x=-150.0 y=30.0 z=1850.0 health=250.0',
    'P2_DWARF_ORANGE_ARENA_BIRTH id=211002 x=150.0 y=30.0 z=1550.0 health=130.0',
    'P2_DWARF_ORANGE_DRAW corpse=1',
    'P2_DWARF_ORANGE_P1_HAUL tick=60 state=0 alive=1 distance=59.1559 transport=18 goal=0',
    'P2_DWARF_ORANGE_P1_HAUL tick=240 state=0 alive=1 distance=175.2125 transport=8 goal=1',
    'PASS P2_DWARF_ORANGE_P1_DELIVERY distance=341.1657 reached=1 p2_receipts=not_applicable',
])


def reentry_log(ticks=True):
    rows = ['P2_DWARF_ORANGE_REENTRY old_manager=0x1 new_manager=0x2 old_actor=0x3 '
            'new_actor=0x4 old_registry=clear before_setup=130 new_red=250 control=130 birth=pass']
    if ticks:
        for tick in range(121, 241):
            for ident in (211001, 211002):
                rows.append(f'P2_DWARF_ORANGE_ARENA_TICK tick={tick} id={ident} state=15 '
                            f'motion=2 frame={tick}.5')
    rows.append('PASS P2_DWARF_ORANGE_REENTRY observation')
    return '\n'.join(rows)


class DwarfOrangeChainTests(unittest.TestCase):
    def test_delivery_transform(self):
        out = delivery.instrument(RED_COMBAT)
        self.assertIn('P2_DWARF_ORANGE_P1_DELIVERY', out)
        self.assertIn('pc_p2_dwarf_orange', out)
        self.assertNotIn('P2_RED', out)
        self.assertNotIn('186001', out)
        self.assertNotIn('pc_p2_kochappy', out)

    def test_delivery_evidence_pass_and_reject(self):
        result = delivery.evidence(DELIVERY_LOG, 0)
        self.assertTrue(result['passed'])
        self.assertTrue(all(result['checks'].values()))
        stalled = '\n'.join(line for line in DELIVERY_LOG.splitlines()
                            if 'P1_HAUL' not in line)
        self.assertFalse(delivery.evidence(stalled, 0)['checks']['transport'])
        self.assertFalse(delivery.evidence(DELIVERY_LOG.replace('distance=341.1657', 'distance=42.0'), 0)['passed'])

    def test_reentry_transform(self):
        out = reentry.instrument(RED_COMBAT)
        self.assertIn('P2_DWARF_ORANGE_REENTRY', out)
        self.assertIn('new_red=250', out)
        self.assertNotIn('new_red=200', out)
        self.assertNotIn('P2_RED', out)
        self.assertNotIn('186001', out)

    def test_reentry_evidence(self):
        self.assertTrue(reentry.evidence(reentry_log(), 0)['passed'])
        blocked = reentry.evidence('\n'.join([
            'P2_DWARF_ORANGE_REENTRY ',
            'FAIL p2 room: arena actor not live/unfrozen',
        ]), 1)
        self.assertFalse(blocked['passed'])
        self.assertFalse(blocked['checks']['replacement'])


if __name__ == '__main__':
    unittest.main()
