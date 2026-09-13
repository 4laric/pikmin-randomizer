from copy import deepcopy
import unittest

from experimental.pikmin2_beasts_floor3_entry import entry_text, stage_checkpoint
from experimental.pikmin2_beasts_floor3_runtime import validate
from tests.test_pikmin2_beasts_floor3_runtime import party,evidence


class FloorThreeEntryTests(unittest.TestCase):
    def test_explicit_profile_and_red_native_species(self):
        lines=entry_text(party(),'a'*64).splitlines()
        self.assertEqual(lines[:3],['P2_BEASTS_FLOOR3_ENTRY_1','a'*64,'3 0.625 20'])
        self.assertEqual(lines[3:6],['1 0','1 1','1 2'])
        self.assertEqual(lines[13:16],['3 1','3 2','3 0'])
        for token in ('a'*32,'a'*63,'A'*64,'g'*64,True,None):
            with self.subTest(token=token),self.assertRaises(ValueError):entry_text(party(),token)

    def test_wrong_checkpoint_floor_rejected_before_assets(self):
        class Adapter:
            def validate(self,state):return state
        for state in (dict(floor=2,status='active'),dict(floor=3,status='failed')):
            with self.subTest(state=state),self.assertRaises(ValueError):stage_checkpoint(Adapter(),state,None,None,None,None,None)

    def test_token_readback_and_no_fourth_floor_handoff(self):
        token='b'*64
        prefix=f'P2_CAVE_READY floor=3 survivors=20 health=0.625\nP2_BEASTS_ENTRY_READY floor=3 token={token} descent=disabled\n'
        verified=f'P2_FLOOR3_BOUNDARY_VERIFIED token={token} descent=disabled\n'
        log=prefix+evidence().replace('P2_FLOOR3_SURVEY_READY',verified+'P2_FLOOR3_SURVEY_READY')
        self.assertEqual(validate(log,party(),boundary_token=token)['points'],12)
        for bad in (log.replace('token='+token,'token='+'c'*64,1),log+'P2_CAVE_TRANSFER floor=3\n',
                    log.replace('floor=3 survivors','floor=2 survivors'),log+verified,
                    log+'P2_BEASTS_ENTRY_READY malformed\n'):
            with self.subTest(bad=bad[:80]),self.assertRaises(ValueError):validate(bad,party(),boundary_token=token)
        with self.assertRaises(ValueError):validate(log,party())


if __name__=='__main__':unittest.main()
