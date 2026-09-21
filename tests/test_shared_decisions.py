import unittest
from tests import test_pikmin2_controller as fixtures
from tests.approval_auth import reviewer
from workflow.shared_decisions import record,tick,pins,approved_scope
from workflow.handoff import Rejected

class SharedDecisionTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ControllerTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.r,self.c=self.f.reg,self.f.controller
        self.r.finish('consumer',1,'blocked','Shared review needed',self.f.ev,['#186','#assets'])
        lane=self.r.status()['lanes']['consumer']
        reviewer(self,self.r,'provider',owns=['consumer'],fake_diff=True)
        self.args=dict(key='consumer',generation=1,source_pins=pins(lane),file=lane['owned_files'][0],
                       status='approved',reviewer='provider',reviewer_generation=1,
                       reason='Reviewed exact diagnostic marker only',evidence=self.f.ev)
    def launches(self):
        return [x for x in self.r.control_status()['launches'].values() if x['lane']=='consumer']
    def test_free_text_or_unowned_reviewer_refused(self):
        with self.assertRaisesRegex(Rejected,'free-text reviewers are refused'):
            record(self.r,**dict(self.args,reviewer='Codex through shared account',reviewer_generation=None))
        with self.r.transaction() as s:s['throughput']['workstreams']={}
        with self.assertRaisesRegex(Rejected,'own producer workstream'):record(self.r,**self.args)
    def test_decision_replay_wakes_once_preserving_unrelated_dependencies(self):
        first=record(self.r,**self.args);self.assertEqual(first,record(self.r,**self.args))
        tick(self.c);tick(self.c)
        self.assertEqual(len(self.launches()),1)
        self.assertEqual(self.r.status()['lanes']['consumer']['dependencies'],['#186','#assets'])
    def test_invalid_evidence_file_and_source_rejected(self):
        for override in [dict(file='unowned'),dict(source_pins={}),dict(evidence=dict(path='absent',sha256='a'*64))]:
            with self.subTest(override=override),self.assertRaises((Rejected,OSError,ValueError)):
                record(self.r,**dict(self.args,**override))
    def test_changed_source_or_live_worker_cannot_consume_decision(self):
        record(self.r,**self.args)
        self.r.probe=lambda p:'unknown';tick(self.c)
        self.assertFalse(self.launches())
        self.r.probe=lambda p:'dead'
        with self.r.transaction() as s:s['lanes']['consumer']['root']['head']='c'*40
        tick(self.c);self.assertFalse(self.launches())

    def test_reapproval_at_same_pins_does_not_restart_new_generation(self):
        record(self.r,**self.args);tick(self.c)
        with self.r.transaction() as s:
            next(x for x in s['control']['launches'].values() if x['lane']=='consumer').update(status='exited',bound_generation=1)
            s['lanes']['consumer']['generation']=2
        record(self.r,**dict(self.args,generation=2,reason='Reaffirmed unchanged diff'))
        tick(self.c)
        self.assertEqual(len(self.launches()),1)
        with self.r.transaction() as s:s['lanes']['consumer']['root']['head']='c'*40
        lane=self.r.snapshot()['lanes']['consumer']
        record(self.r,**dict(self.args,generation=2,source_pins=pins(lane)))
        tick(self.c)
        self.assertEqual(len(self.launches()),2)

    def test_scope_suppression_requires_all_current_clean_files_and_no_rejection(self):
        record(self.r,**self.args)
        state=self.r.snapshot();lane=state['lanes']['consumer']
        lane['owned_files']=[self.args['file']]
        self.assertTrue(approved_scope(state,lane))
        lane['owned_files'].append('new.cpp');self.assertFalse(approved_scope(state,lane))
        lane['owned_files'].pop();lane['root']['dirty']=' M changed.cpp'
        self.assertFalse(approved_scope(state,lane));lane['root']['dirty']=''
        d=next(iter(state['shared_preflight_decisions'].values()))
        state['shared_preflight_decisions']['rejected']=dict(d,status='rejected',at=d['at']+1)
        self.assertFalse(approved_scope(state,lane))

    def test_intervening_rejection_allows_fresh_approval(self):
        first=record(self.r,**self.args);tick(self.c)
        with self.r.transaction() as s:
            next(x for x in s['control']['launches'].values() if x['lane']=='consumer').update(status='exited',bound_generation=1)
            old=s['shared_preflight_decisions'][first['id']]
            s['shared_preflight_decisions']['rejection']=dict(old,status='rejected',at=old['at']+1)
            s['lanes']['consumer']['generation']=2
        self.f.now+=2  # The fresh approval follows the rejection.
        record(self.r,**dict(self.args,generation=2,reason='Approval reinstated after rejection review'))
        tick(self.c)
        self.assertEqual(len(self.launches()),2)

    def test_only_rejections_and_the_completing_approval_launch(self):
        with self.r.transaction() as s:s['lanes']['consumer']['owned_files']=['consumer.py','consumer_b.py']
        record(self.r,**self.args);tick(self.c)
        self.assertEqual(self.launches(),[])  # Recorded, but the owned-file set is not yet complete.
        self.f.now+=1
        second=record(self.r,**dict(self.args,file='consumer_b.py'));tick(self.c)
        self.assertEqual([x['reason'] for x in self.launches()],['shared-preflight-decision:'+second['id']])
        with self.r.transaction() as s:
            for x in s['control']['launches'].values():
                if x['lane']=='consumer':x.update(status='exited',bound_generation=1)
        self.f.now+=1
        record(self.r,**dict(self.args,reason='Re-reviewed the same diff'));tick(self.c)
        self.assertEqual(len(self.launches()),1)  # A repeat approval at the same pins launches nothing.
        self.f.now+=1
        record(self.r,**dict(self.args,status='rejected',reason='Marker must not ship'));tick(self.c)
        self.assertEqual(len(self.launches()),2)
