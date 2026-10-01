import copy
import unittest
from tests import test_pikmin2_controller as fixtures
from workflow.delivery_contracts import record, status, audit, owner_work
from workflow.handoff import Rejected


class DeliveryContractTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ControllerTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.reg=self.f.reg
        self.f.add_lane('owner',3)
        with self.reg.transaction() as s:
            s['lanes']['consumer'].update(state='blocked',dependencies=['Source required'])
            s['lanes']['provider'].update(state='done',review_disposition={'summary':'Report only'})
            s['throughput']={'workstreams':{'s':{'owner_lane':'owner','lanes':['consumer','provider']}}}
        self.args=dict(consumer='consumer',consumer_generation=1,producer='provider',kind='consumer_behavior',
            requirement='Source required',acceptance_check='Run consumer test; original failure absent',
            owner='owner',evidence=self.f.ev)

    def test_report_never_satisfies_source_and_owner_retains_gap(self):
        row=record(self.reg,**self.args);s=self.reg.snapshot()
        self.assertEqual(status(s,row),'awaiting_source')
        self.assertEqual(owner_work(s,'owner')[0]['producer'],'provider')
        self.assertEqual(audit(s)['unclassified'],[])
        s['lanes']['provider']['integration']={'root_commit':'a','native_commit':None}
        self.assertEqual(status(s,row),'awaiting_consumer')

    def test_only_exact_current_contract_consumer_success_closes_behavior(self):
        row=record(self.reg,**self.args);s=self.reg.snapshot()
        s['lanes']['provider']['integration']={'root_commit':'a','native_commit':None}
        check=dict(consumer='consumer',delivery_contracts=[row['id']],created_at=1,status='passed',
            prerequisite_resolved=True,consumer_generation=1,source_pins={'root':'a'*40,'native':None},
            producers=[{'lane':'provider','root_commit':'a','native_commit':None}])
        s['consumer_verifications']={'check':check}
        self.assertEqual(status(s,row),'verified')
        check['consumer_generation']=0
        self.assertEqual(status(s,row),'awaiting_consumer')
        check['consumer_generation']=1;check['delivery_contracts']=[]
        self.assertEqual(status(s,row),'awaiting_consumer')
        check['delivery_contracts']=[row['id']];check['status']='failed'
        self.assertEqual(status(s,row),'consumer_failed')

    def test_review_artifact_is_explicitly_different(self):
        row=record(self.reg,**dict(self.args,kind='review_artifact'))
        self.assertEqual(status(self.reg.snapshot(),row),'delivered')

    def test_cycles_stale_generation_and_wrong_owner_rejected(self):
        record(self.reg,**self.args)
        for overrides in [dict(consumer_generation=0),dict(owner='provider'),dict(producer='consumer')]:
            with self.assertRaises(Rejected):record(self.reg,**dict(self.args,**overrides))
        with self.reg.transaction() as s:s['lanes']['provider']['state']='blocked'
        with self.assertRaisesRegex(Rejected,'Circular'):
            record(self.reg,**dict(self.args,consumer='provider',producer='consumer'))

    def test_idempotent_replacement_preserves_history(self):
        row=record(self.reg,**self.args)
        self.assertEqual(record(self.reg,**self.args)['id'],row['id'])
        replacement=record(self.reg,**dict(self.args,acceptance_check='Run strengthened test',supersedes=row['id']))
        s=self.reg.snapshot()
        self.assertFalse(s['delivery_contracts'][row['id']]['active'])
        self.assertTrue(s['delivery_contracts'][replacement['id']]['active'])

    def test_unclassified_and_owner_change_remain_visible(self):
        self.assertEqual(len(audit(self.reg.snapshot())['unclassified']),1)
        row=record(self.reg,**self.args);s=self.reg.snapshot()
        s['throughput']['workstreams']['s']['owner_lane']='replacement'
        self.assertEqual(status(s,row),'owner_changed')


if __name__=='__main__':unittest.main()
