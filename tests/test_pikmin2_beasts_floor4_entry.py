import unittest
from experimental.pikmin2_beasts_floor4_entry import entry_text,stage_profile
from experimental.pikmin2_beasts_floor3_runtime import validate
from tests.test_pikmin2_beasts_floor3_runtime import party,evidence


class FloorFourEntryTests(unittest.TestCase):
    def test_distinct_native_header_floor_and_species(self):
        lines=entry_text(party(),'d'*64).splitlines()
        self.assertEqual(lines[:3],['P2_BEASTS_FLOOR4_ENTRY_1','d'*64,'4 0.625 20'])
        self.assertEqual(lines[3:6],['1 0','1 1','1 2'])
        self.assertEqual(lines[13:16],['3 1','3 2','3 0'])
        for token in ('a'*32,'a'*63,'a'*65,'A'*64,True,None):
            with self.subTest(token=token),self.assertRaises(ValueError):stage_profile(None,None,None,None,None,party(),token)

    def test_wrong_native_floor_cannot_satisfy_diagnostic_entry(self):
        token='d'*64
        log=f'P2_CAVE_READY floor=4 survivors=20 health=0.625\nP2_BEASTS_ENTRY_READY floor=4 token={token} descent=disabled\n'+evidence()
        log=log.replace('P2_FLOOR3_SURVEY_READY',f'P2_FLOOR3_BOUNDARY_VERIFIED token={token} descent=disabled\nP2_FLOOR3_SURVEY_READY')
        self.assertEqual(validate(log,party(),boundary_token=token,native_floor=4)['points'],12)
        for bad in (log.replace('floor=4','floor=3'),log.replace(token,'c'*64,1),log+'P2_CAVE_TRANSFER floor=4\n'):
            with self.subTest(log=bad[:80]),self.assertRaises(ValueError):validate(bad,party(),boundary_token=token,native_floor=4)
        with self.assertRaises(ValueError):validate(log,party(),boundary_token=token,native_floor=3)


if __name__=='__main__':unittest.main()
