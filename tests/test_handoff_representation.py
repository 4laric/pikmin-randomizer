import copy
import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock,patch
from workflow.handoff_representation import tick
from workflow.control import fingerprint

class HandoffRepresentationTests(unittest.TestCase):
    def setUp(self):
        lane=dict(lane='producer',generation=4,state='blocked',handoff=None,root={'head':'a'},native={'head':'b'},repair_history=[{}])
        self.state={'lanes':{'producer':lane},'control':{'launches':{}},'support_actions':{'p':dict(id='p',at=1,key='producer',action='integration_packet',target=dict(copy.deepcopy(lane),kind='export_preparation'),evidence={'path':'verified'},details={})}}
        self.reg=Mock();self.reg.snapshot.return_value=self.state;self.reg.recovery_safe.return_value=True
        @contextmanager
        def transaction():yield self.state
        self.reg.transaction=transaction
        self.reg.clock.return_value=100
        self.c=SimpleNamespace(reg=self.reg,config={'lanes':{'producer':{}},'models':['allowed']},available=lambda k:True)
        self.patch=patch('workflow.handoff_representation.error',return_value=None);self.patch.start();self.addCleanup(self.patch.stop)

    def test_one_resume_per_source_heads_not_per_packet_or_generation(self):
        tick(self.c);self.reg.plan_launch.assert_called_once()
        reason=self.reg.plan_launch.call_args.args[1]
        self.state['control']['launches']['old']={'lane':'producer','reason':reason,'status':'exited'}
        self.state['lanes']['producer']['generation']=5
        self.state['support_actions']['p']['target']['generation']=5
        tick(self.c);self.reg.plan_launch.assert_called_once()

    def test_live_claimed_existing_handoff_or_changed_pins_are_protected(self):
        for mode in ['live','handoff','pins','batch']:
            with self.subTest(mode=mode):
                original=copy.deepcopy(self.state)
                if mode=='live':self.reg.recovery_safe.return_value=False
                if mode=='handoff':self.state['lanes']['producer']['handoff']={'sha256':'x'}
                if mode=='pins':self.state['lanes']['producer']['native']['head']='changed'
                if mode=='batch':self.state['throughput']={'batches':{'b':{'state':'claimed','candidates':{'producer':{}}}}}
                tick(self.c);self.reg.plan_launch.assert_not_called()
                self.state.clear();self.state.update(original);self.reg.recovery_safe.return_value=True

    def test_invalid_packet_cannot_resume(self):
        with patch('workflow.handoff_representation.error',return_value='invalid bytes'):tick(self.c)
        self.reg.plan_launch.assert_not_called()

    def test_approved_delivery_without_export_repair_resumes_once(self):
        lane=self.state['lanes']['producer'];lane.pop('repair_history')
        lane['owned_files']=['native/fix.cpp','test.py']
        self.state['support_actions']['p']['target']['kind']='blocked_review'
        self.state['shared_preflight_decisions']={f:dict(lane='producer',file=f,status='approved',
            source_pins={'root':'a','native':'b'},generation=1) for f in lane['owned_files']}
        tick(self.c);self.reg.plan_launch.assert_not_called()  # Unauthenticated legacy rows never count.
        for f,d in self.state['shared_preflight_decisions'].items():d['approval']='row-'+f
        self.state['approvals']={'row-'+f:dict(id='row-'+f,kind='preflight') for f in lane['owned_files']}
        tick(self.c)
        self.reg.plan_launch.assert_called_once()
        reason=self.reg.plan_launch.call_args.args[1]
        self.state['control']['launches']['old']=dict(lane='producer',reason=reason,status='exited')
        tick(self.c);self.reg.plan_launch.assert_called_once()

    def test_partial_or_stale_approval_cannot_resume_nonrepair_delivery(self):
        lane=self.state['lanes']['producer'];lane.pop('repair_history')
        lane['owned_files']=['native/fix.cpp','test.py']
        self.state['support_actions']['p']['target']['kind']='blocked_review'
        self.state['shared_preflight_decisions']={'d':dict(lane='producer',file='test.py',status='approved',
            source_pins={'root':'a','native':'b'})}
        tick(self.c);self.reg.plan_launch.assert_not_called()
        self.state['shared_preflight_decisions']['e']=dict(lane='producer',file='native/fix.cpp',status='approved',
            source_pins={'root':'a','native':'stale'})
        tick(self.c);self.reg.plan_launch.assert_not_called()

    def test_completed_same_worker_slot_rearms_once(self):
        lane = self.state['lanes']['producer']
        lane.update(worker_id='w', progress_at=10, next_action='WIP limit: waiting for ready slot')
        tick(self.c)
        original = self.reg.plan_launch.call_args.args[1]
        self.state['control']['launches']['old'] = dict(lane='producer',reason=original,status='exited')
        other = dict(lane='other',worker_id='w',state='handoff_ready',generation=2,integrated_at=None)
        self.state['lanes']['other'] = other
        tick(self.c)
        self.assertEqual(self.reg.plan_launch.call_count, 1)
        other.update(state='done',integrated_at=20,integration={'root_commit':'receipt'})
        tick(self.c)
        self.assertEqual(self.reg.plan_launch.call_count, 2)
        reason = self.reg.plan_launch.call_args.args[1]
        self.assertNotEqual(reason, original)
        self.state['control']['launches']['retry'] = dict(lane='producer',reason=reason,status='exited')
        tick(self.c)
        self.assertEqual(self.reg.plan_launch.call_count, 2)

    def test_unrelated_or_preexisting_completion_does_not_rearm(self):
        from workflow.handoff_representation import released_slot
        lane = self.state['lanes']['producer']
        lane.update(worker_id='w',progress_at=10,next_action='WIP slot')
        self.state['lanes']['other'] = dict(worker_id='other',state='done',generation=1,
                                          integrated_at=20,integration={'root_commit':'r'})
        self.assertEqual(released_slot(self.state,lane), [])
        self.state['lanes']['other'].update(worker_id='w',integrated_at=9)
        self.assertEqual(released_slot(self.state,lane), [])
