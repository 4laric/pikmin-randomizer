"""Acceptance-result refusals; synthetic inputs do not prove native gameplay."""
import copy
import unittest
from randomizer.cave_floor import create,fingerprint
from experimental.pikmin2_cave_items import parse_items_text,items_from_layout,items_text
from scripts.play_pikmin2_cave import checkpoint
from scripts.run_pikmin2_cave_mixed_route import validate_boundary
from test_playable_cave import fixture_layout

class BoundaryTests(unittest.TestCase):
    def fixture(self):
        manifest=create('930','Player1')
        placement={'seed':7989240218121528064,'items':[{'slot_id':'forest_1:f1:leaf:0','host':'forest_1:f1:leaf:0','item':'treasure_water'}]}
        water=next(x for x in placement['items'] if x['item']=='treasure_water')
        ledger=f"P2_RECEIPTS_1\n{placement['seed']} treasure:forest_1:f1:{water['slot_id']} {water['host']} cave_treasure\n"
        budgets='P2_CAVE_BUD_STATE_1 '+str(placement['seed'])+' forest_1 1 2\n'+''.join(b['slot_id']+' '+str(2 if b['species']=='blue' else 1)+'\n' for b in manifest['table']['buds'])
        transfer='P2_CAVE_TRANSFER_1\n'+fingerprint(manifest)[:32]+'\n1 1 20\n'+'1 0\n'*18+'0 0\n2 0\n'
        state=checkpoint(transfer,budgets,ledger,manifest,placement)
        return state,manifest,placement

    def test_exact_mixed_boundary_and_budget(self):
        state,m,p=self.fixture();validate_boundary(state,m,p)

    def test_wrong_stock_and_wrong_budget_refuse(self):
        state,m,p=self.fixture();bad=copy.deepcopy(state);bad['squad'][-1]=[1,0]
        with self.assertRaisesRegex(ValueError,'stock'):validate_boundary(bad,m,p)
        bad=copy.deepcopy(state);bad['buds']=bad['buds'].replace(m['table']['buds'][0]['slot_id']+' 2',m['table']['buds'][0]['slot_id']+' 3')
        with self.assertRaisesRegex(ValueError,'bud budgets'):validate_boundary(bad,m,p)

    def test_missing_and_duplicate_water_receipts_refuse(self):
        state,m,p=self.fixture();state['receipts']='P2_RECEIPTS_1\n'
        with self.assertRaisesRegex(ValueError,'water receipt'):validate_boundary(state,m,p)
        state,m,p=self.fixture();state['receipts']+=state['receipts'].splitlines()[1]+'\n'
        with self.assertRaisesRegex(ValueError,'duplicate'):validate_boundary(state,m,p)

if __name__=='__main__':unittest.main()
