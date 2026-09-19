import copy
import unittest
from types import SimpleNamespace
from tests import test_workflow_delivery as fixtures
from workflow.handoff import Rejected
from workflow.support_actions import record, extra_targets, require_outcomes
from workflow.shared_decisions import record as shared, pins
from workflow.integration_repair import tick


class SupportActionsTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.DeliveryTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.target=self.f.ready(reviews=True);self.r=self.f.reg;self.f.running('two')
        with self.r.transaction() as s:
            s['lanes']['two']['process']={'helper':True}
            target={k:copy.deepcopy(self.target.get(k)) for k in ('lane','generation','root','native','handoff')}
            s['throughput_runtime']={'autofill':{'planner_pool':{'scopes':{'slot':dict(
                spec={'lane':{'lane':'two'}},review_authority='shared-files-v1',actionable_support=True,support_targets=[target])}}}}
        self.r.probe=lambda p:'alive' if p.get('helper') else 'dead'
        self.args=dict(reviewer='two',generation=1,key='one',action='integration_packet',reason='Private preparation complete',
                       evidence=self.f.evidence,details={'destination':{'root':'a'*40,'native':None}})

    def test_prose_only_cannot_finish_and_packet_is_durable(self):
        with self.assertRaises(Rejected):self.r.finish('two',1,'review-ready','Refer to integrator',self.f.evidence)
        first=record(self.r,**self.args)
        self.assertEqual(first,record(self.r,**self.args))
        self.r.finish('two',1,'review-ready','Prepared concrete packet',self.f.evidence)
        self.assertEqual(self.r.snapshot()['lanes']['two']['state'],'review_ready')

    def test_wrong_target_stale_and_false_external_are_rejected(self):
        with self.assertRaises(Rejected):record(self.r,**dict(self.args,key='two'))
        with self.assertRaises(Rejected):record(self.r,**dict(self.args,action='external',details={'owner':'integrator'}))
        with self.r.transaction() as s:s['lanes']['one']['generation']+=1
        with self.assertRaises(Rejected):record(self.r,**self.args)
        record(self.r,**dict(self.args,action='stale',details={}))
        require_outcomes(self.r.snapshot(),'two')

    def test_blocked_review_is_assignable_and_decision_requires_exact_grant(self):
        with self.r.transaction() as s:
            l=s['lanes']['one'];l.update(state='blocked',next_action='#186 shared review',owned_files=['shared.cpp'])
        self.assertEqual(extra_targets(self.r,self.r.snapshot())[0]['kind'],'blocked_review')
        args=dict(key='one',generation=1,source_pins=pins(self.target),file='shared.cpp',status='approved',
                  reviewer='two',reviewer_generation=1,reason='Exact scoped diff inspected',evidence=self.f.evidence)
        shared(self.r,**args);require_outcomes(self.r.snapshot(),'two')
        with self.r.transaction() as s:s['lanes']['one']['root']['head']='e'*40
        with self.assertRaises(Rejected):shared(self.r,**dict(args,source_pins=pins(self.r.snapshot()['lanes']['one'])))

    def test_independent_diagnosis_grants_only_one_extra_repair_for_source(self):
        with self.r.transaction() as s:
            l=s['lanes']['one'];candidate={k:copy.deepcopy(l.get(k)) for k in ('generation','revision','root','native','handoff')}
            l['review_repair']=dict(candidate=candidate,pin=dict(reason='Missing evidence',generation=1,revision=l['revision']))
        action=dict(self.args,action='repair',details={'instruction':'Recreate truthful packet from pinned test logs'})
        first=record(self.r,**action);self.assertEqual(first,record(self.r,**action))
        with self.assertRaises(Rejected):record(self.r,**dict(action,reason='Second retry'))
        self.assertEqual(self.r.snapshot()['lanes']['one']['review_repair']['pin']['independent_action'],first['id'])

    def export_target(self):
        with self.r.transaction() as s:
            lane=s['lanes']['one'];lane.update(state='blocked',handoff=None)
            lane['native']={'head':'c'*40}
            lane['repair_history']=[dict(isolation=dict(reason='Missing maintained native export evidence'),handoff_at=1)]
        target=extra_targets(self.r,self.r.snapshot())[0]
        with self.r.transaction() as s:
            s['throughput_runtime']['autofill']['planner_pool']['scopes']['slot']['support_targets']=[target]
        return target

    def test_blocked_export_history_is_distinct_assignable_work(self):
        target=self.export_target()
        self.assertEqual(target['kind'],'export_preparation')
        from workflow.queue_pressure import support_allocations
        helpers=[dict(scope='review',kind='integration_support'),
                 dict(scope='prep',kind='integration_support',mode='preparation')]
        result=support_allocations(self.r,helpers,{},True,True)
        self.assertEqual(result['review'],[])
        self.assertEqual(result['prep'][0]['lane'],'one')
        self.r.probe=lambda p:'unknown'
        self.assertEqual(extra_targets(self.r,self.r.snapshot()),[])

    def test_export_referral_rejected_and_artifacts_archived(self):
        self.export_target()
        with self.assertRaises(Rejected):record(self.r,**self.args)
        details=dict(destination=dict(root='a'*40,native='b'*40),source_native='c'*40,
                     export_patch=self.patch(),export_validation=self.f.evidence,
                     apply_commands=['git apply --check reviewed.patch'])
        packet=record(self.r,**dict(self.args,details=details))
        self.assertIn('evidence',packet['details']['export_patch']['path'])
        require_outcomes(self.r.snapshot(),'two')
        from workflow.export_preparation import status
        self.assertEqual(status(self.r)[0]['status'],'packet ready for integrator')
        with self.r.transaction() as s:s['lanes']['one']['native']['head']='d'*40
        with self.assertRaises(Rejected):record(self.r,**dict(self.args,details=details))

    def patch(self, encoding='utf-8'):
        from workflow.handoff import digest
        path=self.r.root/'output/export.patch'
        path.write_text('diff --git a/engine/test.cpp b/engine/test.cpp\n--- a/engine/test.cpp\n+++ b/engine/test.cpp\n@@ -1 +1 @@\n-old\n+new\n',encoding=encoding)
        return dict(path=str(path),sha256=digest(path))

    def test_utf16_packet_rejected_and_historical_packet_gets_repair_demand(self):
        target=self.export_target()
        details=dict(destination=dict(root='a'*40,native='b'*40),source_native='c'*40,
                     export_patch=self.patch('utf-16'),export_validation=self.f.evidence,
                     apply_commands=['git apply --check export.patch'])
        with self.assertRaisesRegex(Rejected,'UTF-16'):record(self.r,**dict(self.args,details=details))
        with self.r.transaction() as s:
            s['support_actions']={'bad':dict(id='bad',key='one',reviewer='two',target=target,
                                           action='integration_packet',details=details,at=1)}
        candidate=extra_targets(self.r,self.r.snapshot())[0]
        self.assertEqual(candidate['export_packet_repair']['packet'],'bad')
        from workflow.export_preparation import status
        self.assertIn('packet_error',status(self.r)[0])
        self.assertNotEqual(status(self.r)[0]['status'],'packet ready for integrator')

    def test_shared_approval_does_not_complete_export_assignment(self):
        self.export_target()
        with self.r.transaction() as s:
            s['shared_review_decisions']={'approval':dict(reviewer='two',lane='one',generation=1)}
        with self.assertRaises(Rejected):require_outcomes(self.r.snapshot(),'two')

    def test_unconsumed_export_gets_bounded_reassessment(self):
        from workflow.export_feedback import stalled
        from workflow.export_preparation import status
        self.export_target()
        details=dict(destination=dict(root='a'*40,native='b'*40),source_native='c'*40,
                     export_patch=self.patch(),export_validation=self.f.evidence,
                     apply_commands=['git apply --check reviewed.patch'])
        packet=record(self.r,**dict(self.args,details=details))
        with self.r.transaction() as state:
            state.setdefault('throughput',{}).setdefault('workstreams',{})['test']=dict(owner_lane='owner',lanes=['one'])
            state.setdefault('control',{}).setdefault('launches',{}).update({
                'a':dict(lane='owner',status='exited',bound_generation=1,created_at=1,instruction=packet['id']),
                'b':dict(lane='owner',status='running',bound_generation=2,created_at=2,instruction=packet['id'])})
        self.assertIsNone(stalled(self.r.snapshot(),packet))
        with self.r.transaction() as state:state['control']['launches']['b']['status']='exited'
        feedback=stalled(self.r.snapshot(),packet)
        self.assertEqual(len(feedback['attempts']),2)
        self.assertEqual(extra_targets(self.r,self.r.snapshot())[0]['export_packet_repair'],feedback)
        self.assertNotEqual(status(self.r)[0]['status'],'packet ready for integrator')
        # Changed prose/validation does not produce another repair identity.
        other=record(self.r,**dict(self.args,details=details,reason='Same patch, new prose'))
        self.assertEqual(stalled(self.r.snapshot(),other),feedback)
        with self.r.transaction() as state:
            state['control']['launches']['c']=dict(lane='owner',status='exited',bound_generation=3,
                created_at=3,instruction=other['id'])
        self.assertEqual(stalled(self.r.snapshot(),other),feedback)
        with self.r.transaction() as state:state['lanes']['one']['native']['head']='d'*40
        self.assertIsNone(stalled(self.r.snapshot(),packet))

    def test_new_export_destination_or_patch_needs_its_own_attempts(self):
        from workflow.export_feedback import stalled
        self.export_target()
        details=dict(destination=dict(root='a'*40,native='b'*40),source_native='c'*40,
                     export_patch=self.patch(),export_validation=self.f.evidence,
                     apply_commands=['git apply --check reviewed.patch'])
        packet=record(self.r,**dict(self.args,details=details))
        with self.r.transaction() as state:
            state.setdefault('throughput',{}).setdefault('workstreams',{})['test']=dict(owner_lane='owner',lanes=['one'])
            state.setdefault('control',{}).setdefault('launches',{}).update({
                str(i):dict(lane='owner',status='exited',bound_generation=i,created_at=i,instruction=packet['id'])
                for i in (1,2)})
        changed=copy.deepcopy(packet);changed['details']['destination']['root']='e'*40
        with self.r.transaction() as state:state['support_actions']['new']=dict(changed,id='new')
        self.assertIsNone(stalled(self.r.snapshot(),changed))

    def test_staged_proposal_requires_validation_and_recovery_assignment(self):
        import json
        from unittest.mock import patch
        from workflow.handoff import digest
        target=self.export_target()
        target.pop('kind')
        with self.r.transaction() as state:
            row=state['throughput_runtime']['autofill']['planner_pool']['scopes']['slot']
            row.pop('support_targets');row['recovery_action_targets']=[target]
        path=self.r.root/'output/proposals.json'
        spec={'id':'actual-repair','lane':{'lane':'private-repair'}}
        path.write_text(json.dumps({'items':[spec]}))
        args=dict(self.args,action='proposal',details=dict(consumer='one',proposal_id='actual-repair',
                  proposal={'path':str(path),'sha256':digest(path)}))
        with patch('workflow.autofill.validate_spec',side_effect=Rejected('Bad launch proof')):
            with self.assertRaises(Rejected):record(self.r,**args)
        with patch('workflow.autofill.validate_spec') as validate:
            action=record(self.r,**args)
            validate.assert_called_once_with(self.r,spec)
        self.assertEqual(action['action'],'proposal')
        require_outcomes(self.r.snapshot(),'two')
        self.assertIsNone(self.r.snapshot()['lanes']['one'].get('integration'))
        with self.assertRaises(Rejected):record(self.r,**dict(args,details=dict(args['details'],consumer='wrong')))
