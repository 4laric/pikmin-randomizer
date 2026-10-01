import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from tests import test_workflow_delivery as delivery_fixtures
from tests.approval_auth import reviewer
from workflow.review_decisions import record,tick
from workflow.handoff import Rejected
from workflow.queue_pressure import support_allocations,integration_items

class QueuedReviewTests(unittest.TestCase):
    def setUp(self):
        self.f=delivery_fixtures.DeliveryTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.lane=self.f.ready(reviews=True);self.r=self.f.reg
        self.f.running('two');self.f.health='alive'
        with self.r.transaction() as s:s.setdefault('throughput',{})['workstreams']={'test':{'owner_lane':'two','lanes':['one']}}
        reviewer(self,self.r,'two',fake_diff=True)
        self.args=dict(reviewer='two',generation=1,key='one',producer_generation=1,handoff_sha256=self.lane['handoff']['sha256'],decisions=[dict(file='shared.cpp',status='approved',evidence=self.f.evidence)])
        self.c=SimpleNamespace(reg=self.r)
    def test_wait_apply_and_replay(self):
        receipt=record(self.r,**self.args);self.assertEqual(receipt,record(self.r,**self.args))
        tick(self.c);self.assertEqual(self.r.snapshot()['lanes']['one']['handoff'],self.lane['handoff'])
        self.f.health='dead';tick(self.c)
        state=self.r.snapshot();self.assertEqual(state['shared_review_decisions'][receipt['id']]['status'],'applied')
        self.assertEqual(self.r.check_handoff(state['lanes']['one'])['pending_reviews'],[])
        row=state['approvals'][receipt['approvals'][0]]
        self.assertEqual((row['kind'],row['reviewer']['launch'],row['reviewer']['models']),
                         ('handoff_review','launch-two',['test/reviewer-model']))
        self.assertEqual(state['throughput']['dispositions'][next(iter(state['throughput']['dispositions']))]['approval'],row['id'])
        tick(self.c);self.assertEqual(state['lanes']['one'],self.r.snapshot()['lanes']['one'])
    def test_mutation_failure_rolls_back(self):
        receipt=record(self.r,**self.args);self.f.health='dead'
        with patch.object(self.r,'check_wip',side_effect=Rejected('capacity changed')):tick(self.c)
        state=self.r.snapshot();self.assertEqual(state['lanes']['one'],self.lane)
        self.assertEqual(state['shared_review_decisions'][receipt['id']]['applied'],0)
        tick(self.c);self.assertEqual(self.r.snapshot()['shared_review_decisions'][receipt['id']]['status'],'applied')
    def test_pin_drift_stale(self):
        receipt=record(self.r,**self.args)
        with self.r.transaction() as s:s['lanes']['one']['generation']+=1
        tick(self.c);self.assertEqual(self.r.snapshot()['shared_review_decisions'][receipt['id']]['status'],'stale')
    def test_wrong_owner_and_changed_evidence(self):
        with self.r.transaction() as s:s['throughput']['workstreams']={}
        with self.assertRaises(Rejected):record(self.r,**self.args)
        with self.r.transaction() as s:s['throughput']['workstreams']={'test':{'owner_lane':'two','lanes':['one']}}
        receipt=record(self.r,**self.args);self.f.health='dead';self.f.log.write_text('changed')
        tick(self.c);self.assertEqual(self.r.snapshot()['shared_review_decisions'][receipt['id']]['applied'],0)
    def test_capacity_keeps_execution_reserve(self):
        from workflow.planner_pool import support_target
        cfg=dict(integration_support_max_active=8,reserve_workers=2)
        self.assertEqual(support_target(cfg,demanded=20,idle=19,active=0,unclaimed_ready=0),8)
        self.assertEqual(support_target(cfg,demanded=4,idle=19,active=0,unclaimed_ready=0),4)
        self.assertEqual(support_target(cfg,demanded=8,idle=5,active=0,unclaimed_ready=1),2)
    def grant_delegate(self):
        with self.r.transaction() as s:
            s['throughput']['workstreams']={}
            s['throughput_runtime']={'autofill':{'planner_pool':{'scopes':{'helper':dict(
                review_authority='shared-files-v1',spec={'lane':{'lane':'two'}},
                support_targets=copy.deepcopy(integration_items({'one':s['lanes']['one']})))}}}}
    def test_delegated_decision_applies_without_integration_authority(self):
        self.grant_delegate()
        receipt=record(self.r,**self.args)
        self.f.health='dead';tick(self.c)
        state=self.r.snapshot()
        self.assertEqual(state['shared_review_decisions'][receipt['id']]['status'],'applied')
        self.assertEqual(self.r.check_handoff(state['lanes']['one'])['pending_reviews'],[])
        self.assertNotEqual(state['lanes']['one']['state'],'done')
        self.assertFalse(state['lanes']['one'].get('integration'))
    def test_delegation_fences(self):
        for mutation in ('ungranted','completed','other_lane','generation','handoff','root','self'):
            with self.subTest(mutation=mutation):
                self.grant_delegate()
                with self.r.transaction() as s:
                    grant=s['throughput_runtime']['autofill']['planner_pool']['scopes']['helper']
                    target=grant['support_targets'][0]
                    if mutation=='ungranted':grant.pop('review_authority')
                    elif mutation=='completed':grant['completed_at']=1
                    elif mutation=='other_lane':target['lane']='other'
                    elif mutation=='generation':target['generation']+=1
                    elif mutation=='handoff':target['handoff']['sha256']='0'*64
                    elif mutation=='root':target['root']['commit']='0'*40
                    elif mutation=='self':grant['spec']['lane']['lane']='one'
                with self.assertRaises(Rejected):record(self.r,**self.args)
    def test_distinct_support_and_retained_inflight(self):
        with self.r.transaction() as s:
            for i in range(10):s['lanes']['h'+str(i)]=dict(copy.deepcopy(self.lane),lane='h'+str(i))
        helpers=[dict(scope=str(i),kind='integration_support',mode='preparation') for i in range(8)]
        records={};first=support_allocations(self.r,helpers,records,True)
        targets=[x[0]['lane'] for x in first.values()];self.assertEqual(len(set(targets)),8)
        records['0']={'support_targets':first['0']}
        second=support_allocations(self.r,helpers,records,True)
        self.assertEqual(second['0'],first['0']);self.assertEqual(len({x[0]['lane'] for x in second.values()}),8)

if __name__=='__main__':unittest.main()
