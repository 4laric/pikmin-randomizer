"""Acceptance-result refusals; synthetic inputs do not prove native gameplay."""
import copy
import os
from pathlib import Path
import subprocess
import sys
import time
import tempfile
import unittest
from randomizer.cave_floor import create,fingerprint
from experimental.pikmin2_cave_items import parse_items_text,items_from_layout,items_text
from experimental.pikmin2_cave_lane41_generator import _seed_uint64,write_native_table
from scripts.play_pikmin2_cave import checkpoint
from scripts.run_pikmin2_cave_mixed_route import validate_boundary,child_deadline_seconds
from tests.test_playable_cave import fixture_layout

class BoundaryTests(unittest.TestCase):
    def test_finite_route_and_restore_deadlines_unknown_scenario_refused(self):
        self.assertEqual(child_deadline_seconds('route'),120)
        self.assertEqual(child_deadline_seconds('restore'),60)
        self.assertEqual(child_deadline_seconds('route_all'),180)
        self.assertEqual(child_deadline_seconds('restore_all'),60)
        with self.assertRaisesRegex(ValueError,'unknown native scenario'):
            child_deadline_seconds('campaign')

    def fixture(self):
        manifest=create('930','Player1')
        placement={'seed':_seed_uint64(manifest['table']['seed']),'items':[{'slot_id':'forest_1:f1:leaf:0','host':'forest_1:f1:leaf:0','item':'treasure_water'}]}
        water=next(x for x in placement['items'] if x['item']=='treasure_water')
        ledger=f"P2_RECEIPTS_1\n{placement['seed']} treasure:forest_1:f1:{water['slot_id']} {water['host']} cave_treasure\n"
        budgets='P2_CAVE_BUD_STATE_1 '+str(placement['seed'])+' forest_1 1 2\n'+''.join(b['slot_id']+' '+str(2 if b['species']=='blue' else 1)+'\n' for b in manifest['table']['buds'])
        transfer='P2_CAVE_TRANSFER_1\n'+fingerprint(manifest)[:32]+'\n1 1 20\n'+'1 0\n'*18+'0 0\n2 0\n'
        state=checkpoint(transfer,budgets,ledger,manifest,placement)
        return state,manifest,placement

    def test_exact_mixed_boundary_and_budget(self):
        state,m,p=self.fixture();validate_boundary(state,m,p)

    def full_fixture(self):
        state,m,p=self.fixture()
        electric=dict(slot_id='forest_1:f1:leaf:1',host='forest_1:f1:leaf:1',item='treasure_elec')
        p['items'].append(electric)
        state['receipts']+=f"{p['seed']} treasure:forest_1:f1:{electric['slot_id']} {electric['host']} cave_treasure\n"
        return state,m,p

    def test_full_scope_requires_both_canonical_receipts_exactly_once(self):
        state,m,p=self.full_fixture();validate_boundary(state,m,p,True)
        state['receipts']='\n'.join(state['receipts'].splitlines()[:2])+'\n'
        with self.assertRaisesRegex(ValueError,'canonical receipt'):validate_boundary(state,m,p,True)
        state,m,p=self.full_fixture();state['receipts']+=state['receipts'].splitlines()[-1]+'\n'
        with self.assertRaisesRegex(ValueError,'duplicate'):validate_boundary(state,m,p,True)

    def test_canonical_seed_uses_actual_native_table_serialization(self):
        state,m,p=self.full_fixture()
        with tempfile.TemporaryDirectory() as directory:
            table=write_native_table(m['table'],Path(directory)/'floor.txt')
            native_seed=int(table.read_text().splitlines()[1].split()[1])
        self.assertEqual(p['seed'],native_seed)
        self.assertNotEqual(native_seed,int(m['table']['seed']))
        validate_boundary(state,m,p,True)
        p['seed']=int(m['table']['seed'])
        with self.assertRaisesRegex(ValueError,'placement seed'):validate_boundary(state,m,p,True)

    def test_full_scope_rejects_incompatible_placement_and_descriptor(self):
        state,m,p=self.full_fixture();p['seed']+=1
        with self.assertRaisesRegex(ValueError,'placement seed'):validate_boundary(state,m,p,True)
        state,m,p=self.full_fixture();p['items'][1]['host']='forest_1:f1:leaf:0'
        with self.assertRaisesRegex(ValueError,'host binding'):validate_boundary(state,m,p,True)
        state,m,p=self.full_fixture();m['table']['treasures'][1]['slot_id']='forest_1:f1:leaf:0'
        with self.assertRaisesRegex(ValueError,'incompatible'):validate_boundary(state,m,p,True)

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

class ActualOwnedGroupTests(unittest.TestCase):
    @unittest.skipIf(os.name=='nt','actual POSIX retained process-group control')
    def test_retained_exit_and_timeout_cleanup(self):
        from scripts.fixture_platform import owned_process_options,wait_owned_process,terminate_owned_process
        for natural_exit in (True,False):
            with self.subTest(natural_exit=natural_exit):
                script='import os,time; pid=os.fork();\nif pid==0: time.sleep(30)\nelse: time.sleep(.1 if '+str(natural_exit)+' else 30)'
                child=subprocess.Popen([sys.executable,'-c',script],**owned_process_options())
                unrelated=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
                try:
                    if natural_exit:self.assertEqual(wait_owned_process(child,2),0)
                    else:
                        with self.assertRaises(subprocess.TimeoutExpired):wait_owned_process(child,.1)
                    self.assertIsNone(child.returncode) # kernel leader has not been reaped
                    receipt=terminate_owned_process(child)
                    self.assertTrue(receipt['child_reaped']);self.assertTrue(receipt['group_absent'])
                    self.assertTrue(receipt['leader_retained_until_signal']);self.assertEqual(receipt['signal_attempts'],1)
                    self.assertIs(terminate_owned_process(child),receipt)
                    self.assertIsNone(unrelated.poll())
                finally:
                    terminate_owned_process(child)
                    unrelated.terminate();unrelated.wait(timeout=3)

if __name__=='__main__':unittest.main()
