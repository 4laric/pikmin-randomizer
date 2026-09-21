import copy
import unittest
from workflow.dependency_classification import allocations, record, signature, require_outcomes
from workflow.delivery_contracts import record as contract
from workflow.handoff import Rejected
from tests.test_delivery_contracts import DeliveryContractTests

class ClassificationTests(unittest.TestCase):
    def setUp(self):
        self.f=DeliveryContractTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.reg=self.f.reg
        with self.reg.transaction() as s:
            s['lanes']['consumer']['outcome']={'evidence':self.f.f.ev}
            s['lanes']['owner']['state']='running'
            token=signature(s['lanes']['consumer'])
            s['throughput_runtime']={'autofill':{'planner_pool':{'scopes':{'one':{
                'spec':{'lane':{'lane':'owner'}},'classification_target':{'consumer':'consumer','snapshot':token}}}}}}
        self.args=dict(reviewer='owner',generation=1,consumer='consumer',snapshot=token,
                       dispositions=[],evidence=self.f.f.ev)

    def internal(self, **overrides):
        finding=dict(kind='missing_producer',missing='Native callsite lacks the required birth wiring',
            next_action='Prepare a private wiring repair with the original consumer command as acceptance',
            inspected_lanes=['consumer','provider'])
        finding.update(overrides)
        return dict(requirement='Source required',check='Run native consumer; observe actor birth',
                    reason='Compared consumer failure with source callsite; no wired producer',internal_blocker=finding)

    def test_internal_finding_completes_classification_without_resolving_consumer(self):
        from workflow.internal_followup import allocations as followups, queue_status
        record(self.reg,**dict(self.args,dispositions=[self.internal()]))
        s=self.reg.snapshot();require_outcomes(s,'owner')
        self.assertEqual(s['lanes']['consumer']['state'],'blocked')
        self.assertFalse(s.get('delivery_contracts'))
        rows=followups(s,[{'scope':'two'}],{})
        self.assertEqual(rows['two']['request']['lanes'],['consumer'])
        self.assertEqual(queue_status(s)[0]['status'],'pending')
        s['throughput_runtime']['autofill']['prerequisite_recovery']={rows['two']['key']:{'lane':'owner'}}
        self.assertFalse(followups(s,[{'scope':'two'}],{}))
        self.assertEqual(queue_status(s)[0]['status'],'assigned')

    def test_internal_finding_requires_precise_evidence_and_real_owner(self):
        for changes in ({'missing':''},{'next_action':''},{'inspected_lanes':['invented']},
                        {'kind':'owner_blocked','owner_lane':'invented'}, {'kind':'user_asset'}):
            with self.assertRaises(Rejected):record(self.reg,**dict(self.args,dispositions=[self.internal(**changes)]))

    def test_followup_respects_active_owners_and_other_assignments(self):
        from workflow.internal_followup import allocations as followups
        record(self.reg,**dict(self.args,dispositions=[self.internal(kind='owner_blocked',owner_lane='provider')]))
        s=self.reg.snapshot();helpers=[{'scope':'two'}]
        self.assertFalse(followups(s,helpers,{}))  # Existing owner work is routed to its owner.
        s['lanes']['provider']['state']='running'
        self.assertFalse(followups(s,helpers,{}))
        s['lanes']['provider']['state']='blocked'
        self.assertFalse(followups(s,helpers,{'other':{'followup_owner_lanes':['provider']}}))

    def test_old_failed_contract_gets_one_v2_attempt_without_resetting_history(self):
        from workflow.control import fingerprint
        s=self.reg.snapshot();key='classification:'+fingerprint(['consumer',signature(s['lanes']['consumer'])])
        s['throughput_runtime']['autofill']['prerequisite_recovery']={key:{'lane':'old'}}
        new=allocations(s,[{'scope':'two'}],{})['two']
        self.assertTrue(new['key'].startswith('classification-v2:'))
        s['throughput_runtime']['autofill']['prerequisite_recovery'][new['key']]={'lane':'owner'}
        self.assertFalse(allocations(s,[{'scope':'two'}],{}))
        self.assertIn(key,s['throughput_runtime']['autofill']['prerequisite_recovery'])

    def test_distinct_assignments_and_semantic_attempt_bound(self):
        s=self.reg.snapshot();s['lanes']['second']=copy.deepcopy(s['lanes']['consumer'])
        helpers=[{'scope':'a'},{'scope':'b'}]
        result=allocations(s,helpers,{})
        self.assertEqual({x['request']['lanes'][0] for x in result.values()},{'consumer','second'})
        s['throughput_runtime']['autofill']['prerequisite_recovery']={x['key']:{} for x in result.values()}
        s['lanes']['consumer']['generation']=22
        self.assertFalse(allocations(s,helpers,{}))
        s['lanes']['consumer']['dependencies'].append('new')
        self.assertEqual(len(allocations(s,helpers,{})),1)

    def test_failed_attempt_visible_and_does_not_starve_next_consumer(self):
        from workflow.dependency_classification import queue_status
        from workflow.delivery_contracts import audit
        s=self.reg.snapshot();helpers=[{'scope':'a'}]
        first=allocations(s,helpers,{})['a']
        s['throughput_runtime']['autofill']['prerequisite_recovery']={first['key']:{'lane':'failed'}}
        s['lanes']['failed']={'state':'done'}
        s['lanes']['second']=dict(copy.deepcopy(s['lanes']['consumer']),issue=99)
        second=allocations(s,helpers,{})['a']
        self.assertEqual(second['request']['lanes'],['second'])
        rows=queue_status(s,audit(s)['unclassified'])
        self.assertEqual(next(r['status'] for r in rows if r['consumer']=='consumer'),'needs_attention')

    def test_reservations_and_active_launch_are_excluded(self):
        s=self.reg.snapshot()
        self.assertFalse(allocations(s,[{'scope':'b'}],{'a':{'recovery_targets':['consumer']}}))
        s.setdefault('control',{})['launches']={'x':{'lane':'consumer','status':'running'}}
        self.assertFalse(allocations(s,[{'scope':'b'}],{}))

    def test_no_work_partial_and_unsubstantiated_rejected(self):
        with self.assertRaises(Rejected):require_outcomes(self.reg.snapshot(),'owner')
        with self.assertRaises(Rejected):record(self.reg,**self.args)
        d=dict(requirement='Source required',check='run consumer check',reason='examined failure',action_id='invented')
        with self.assertRaises(Rejected):record(self.reg,**dict(self.args,dispositions=[d]))

    def test_contract_disposition_does_not_unblock_and_stale_rejected(self):
        c=contract(self.reg,**self.f.args)
        d=dict(requirement='Source required',check='run consumer check',reason='examined failure',contract_id=c['id'])
        record(self.reg,**dict(self.args,dispositions=[d]))
        require_outcomes(self.reg.snapshot(),'owner')
        self.assertEqual(self.reg.snapshot()['lanes']['consumer']['state'],'blocked')
        with self.reg.transaction() as s:s['lanes']['consumer']['dependencies'].append('new')
        with self.assertRaises(Rejected):record(self.reg,**dict(self.args,dispositions=[d]))
        with self.assertRaises(Rejected):record(self.reg,**dict(self.args,generation=0,dispositions=[d]))

if __name__=='__main__':unittest.main()
