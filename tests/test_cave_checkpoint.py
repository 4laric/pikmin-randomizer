"""Native-derived vectors establish adapter policy, never gameplay acceptance."""
import unittest
from randomizer.cave_checkpoint import entry_text, transfer_text, read_transfer, wire_schema

TOKEN='0123456789abcdef0123456789abcdef'


class CheckpointWireTests(unittest.TestCase):
    def test_legacy_bytes_order_count_and_health_exact(self):
        party=dict(squad=[[0,2],[1,0],[2,1]],health=.5)
        self.assertEqual(entry_text(TOKEN,1,party),f'P2_CAVE_ENTRY_1 {TOKEN} 1 0.5 3\n0 2\n1 0\n2 1\n')
        wire=f'P2_CAVE_TRANSFER_1\n{TOKEN}\n1 0.5 3\n0 2\n1 0\n2 1\n'
        self.assertEqual(transfer_text(TOKEN,1,party),wire)
        self.assertEqual(read_transfer(wire,TOKEN,1),party)

    def test_native_wire1_has_purple3_and_mixed_maturity(self):
        # pc_p2_species_schema.h v1 maxPurple3, GlobalGameOptions.h Leaf0/Bud1/Flower2.
        party=dict(squad=[[3,2],[1,0],[3,1]],health=.75)
        self.assertEqual(wire_schema(party),1)
        self.assertEqual(read_transfer(transfer_text(TOKEN,2,party),TOKEN,2),party)

    def test_wire2_has_white4_and_never_downgrades_retained_version(self):
        party=dict(squad=[[3,1],[4,2],[1,0],[4,0]],health=.625,wire_schema=2)
        self.assertEqual(read_transfer(transfer_text(TOKEN,1,party),TOKEN,1),party)
        reduced=dict(squad=[[1,1]],health=.625,wire_schema=2)
        self.assertTrue(entry_text(TOKEN,2,reduced).startswith('P2_CAVE_ENTRY_2 '))
        self.assertEqual(read_transfer(transfer_text(TOKEN,2,reduced),TOKEN,2),reduced)

    def test_incompatible_unknown_and_malformed_wires_refuse(self):
        good=f'P2_CAVE_TRANSFER_2 {TOKEN} 1 .5 2 3 1 4 2'
        for wire in (good.replace('_2','_1'),good.replace('_2','_3'),good.replace('_2','_4'),
                     good.replace('4 2','5 2'),good.replace('4 2','4 3'),good+' 1 0',
                     good.replace('.5','nan'),good.replace('.5','0'),good.replace('.5','1_0'),
                     good.replace('2 3 1','3 3 1'),good.replace('4 2','-1 2')):
            with self.subTest(wire=wire),self.assertRaises(ValueError):read_transfer(wire,TOKEN,1)

    def test_boolean_or_empty_party_cannot_serialize(self):
        for party in (dict(squad=[],health=1),dict(squad=[[True,0]],health=1),
                      dict(squad=[[4,1]],health=1,wire_schema=1),dict(squad=[[1,0]]*101,health=1)):
            with self.subTest(party=party),self.assertRaises(ValueError):entry_text(TOKEN,1,party)
