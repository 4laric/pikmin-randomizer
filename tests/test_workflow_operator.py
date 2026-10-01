import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from workflow.operator import parked_scope_action, parked_scope_diagnoses, report
from workflow.integration_wakeup import receipt_gaps
from workflow.processes import identify


class OperatorTests(unittest.TestCase):
    def state(self):
        return dict(lanes={'a':dict(lane='a',state='handoff_ready',generation=2,revision=4,native=None,handoff_at=10)},
                    throughput=dict(workstreams={'species':{}},batches={'b':dict(state='closed',workstream='species',
                        candidates={'a':{'generation':2}},isolated={})}))

    def test_closed_batch_gap_is_visible_without_mutation(self):
        state=self.state();before=copy.deepcopy(state)
        data=report(state,50)
        self.assertEqual(data['actions'][0]['batch'],'b')
        self.assertEqual(data['handoffs'][0]['age_seconds'],40)
        self.assertEqual(state,before)

    def test_review_ready_is_reported_separately_from_handoffs(self):
        state=self.state()
        state['lanes']['a'].update(state='review_ready',issue=134,handoff_at=10,
                                  next_action='Review pinned proof')
        data=report(state,50)
        self.assertEqual(data['handoffs'],[])
        self.assertEqual(data['reviews'],[dict(lane='a',issue=134,state='review_ready',
            generation=2,revision=4,age_seconds=40,next_action='Review pinned proof',
            source_pin_errors=[],evidence_errors=[],disposition_ready=True)])

    def test_ready_review_surfaces_actionable_disposition(self):
        state=self.state()
        state['lanes']['a'].update(state='review_ready',issue=134,handoff_at=10,
                                  next_action='Review pinned proof')
        data=report(state,50)
        action=next(item for item in data['actions'] if item['lane']=='a')
        self.assertEqual(action['priority'],1)
        self.assertIn('prepared accept-review request',action['next_action'])
        stale=report(state,10+1800)
        action=next(item for item in stale['actions'] if item['lane']=='a')
        self.assertEqual(action['priority'],0)
        self.assertEqual(action['age_seconds'],1800)
        self.assertIn('review_followup deferral',action['next_action'])

    def test_review_ready_exposes_drifted_evidence(self):
        state=self.state()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            proof=root/'output'/'proof.md';proof.parent.mkdir(parents=True)
            proof.write_text('submitted')
            state['lanes']['a'].update(state='review_ready',issue=134,handoff_at=10,
                owner='Codex through shared account 4laric',task_id='opencode:ses_test',
                review=dict(schema=1,kind='review',fresh_runtime=False,conclusion='reviewed',
                    lane='a',owner='Codex through shared account 4laric',
                    task_id='opencode:ses_test',issue=134,generation=2,
                    evidence={'review':{'path':'output/proof.md',
                        'sha256':hashlib.sha256(b'submitted').hexdigest()}}))
            good=report(state,50,root)
            self.assertTrue(good['reviews'][0]['disposition_ready'])
            proof.write_text('changed after review')
            data=report(state,50,root)
        review=data['reviews'][0]
        self.assertFalse(review['disposition_ready'])
        self.assertTrue(review['evidence_errors'])
        action=next(item for item in data['actions'] if item['lane']=='a')
        self.assertEqual(action['priority'],0)
        self.assertIn('accept-review disposition',action['next_action'])

    def test_review_ready_exposes_stale_real_worktree_pin(self):
        import subprocess
        state=self.state()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            tree=root/'review-source';tree.mkdir()
            subprocess.run(['git','init'],cwd=tree,check=True,capture_output=True)
            subprocess.run(['git','config','user.email','test@example.invalid'],cwd=tree,check=True)
            subprocess.run(['git','config','user.name','Workflow Test'],cwd=tree,check=True)
            proof=tree/'proof.txt';proof.write_text('base')
            subprocess.run(['git','add','proof.txt'],cwd=tree,check=True)
            subprocess.run(['git','commit','-m','base'],cwd=tree,check=True,capture_output=True)
            base=subprocess.run(['git','rev-parse','HEAD'],cwd=tree,check=True,
                capture_output=True,text=True).stdout.strip()
            proof.write_text('reviewed')
            subprocess.run(['git','commit','-am','reviewed'],cwd=tree,check=True,capture_output=True)
            state['lanes']['a'].update(state='review_ready',root=dict(
                base=base,head=base,commits=[],dirty='',worktree=str(tree)))
            data=report(state,50,root)
        self.assertEqual(len(data['reviews'][0]['source_pin_errors']),1)
        self.assertIn('root HEAD is',data['reviews'][0]['source_pin_errors'][0])
        action=next(item for item in data['actions'] if item['lane']=='a')
        self.assertEqual(action['priority'],0)
        self.assertEqual(action['generation'],2)
        self.assertEqual(action['revision'],4)
        self.assertIn('do not integrate stale pins',action['next_action'])

    def test_completed_isolated_or_new_generation_not_reconciled(self):
        for update in ({'integration':{'root_commit':'x'}},{'generation':3},{'state':'blocked'}):
            state=self.state();state['lanes']['a'].update(update)
            self.assertEqual(receipt_gaps(state,'species'),[])
        state=self.state();state['throughput']['batches']['b']['isolated']['a']={}
        self.assertEqual(receipt_gaps(state,'species'),[])

    def test_native_export_requirement_and_capacity_next_action(self):
        state=self.state();state['lanes']['a']['native']={'head':'x'}
        state['throughput_runtime']={'autofill':{'items':{'job':dict(lane='next',phase='pending',
            dependency_kind='worker_capacity',status='blocked',reason='No compatible worker')}}}
        data=report(state,50)
        self.assertIn('export',data['actions'][0]['next_action'])
        self.assertIn('adaptation',data['actions'][1]['next_action'])

    def test_export_debt_is_one_action_with_exact_details_separate(self):
        state=self.state()
        state['throughput']['batches']={}
        state['lanes']={
            key:dict(lane=key,state='done',generation=1,revision=1,
                     native={'head':'native'},issue=number,
                     integration={'export_evidence':f'missing-{key}.json','export_sha256':'bad'})
            for key,number in (('old-a',10),('old-b',11),('old-c',12))
        }
        with tempfile.TemporaryDirectory() as directory:
            data=report(state,50,Path(directory))
        self.assertEqual(len(data['actions']),1)
        self.assertEqual(data['actions'][0]['lane'],'maintained-export-repair')
        self.assertIn('3 integrated lanes',data['actions'][0]['reason'])
        self.assertEqual([row['lane'] for row in data['export_repairs']],
                         ['old-a','old-b','old-c'])

    def test_reconciled_export_debt_is_consumed_and_new_debt_still_acts(self):
        from types import SimpleNamespace
        from workflow import export_repair
        state=self.state()
        state['throughput']['batches']={}
        state['lanes']={
            key:dict(lane=key,state='done',generation=1,revision=1,native={'head':'native'},
                     issue=number,integration={'export_evidence':f'missing-{key}.json','export_sha256':'bad'})
            for key,number in (('old-a',10),('old-b',11))
        }
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            evidence=root/'output'/'maintained-export.json'
            evidence.parent.mkdir(parents=True,exist_ok=True)
            evidence.write_text('{"action":"exported"}',encoding='utf-8')
            export_repair.record(SimpleNamespace(root=root,snapshot=lambda:state),None,
                                 'output/maintained-export.json',now=60.0)
            data=report(state,50,root)
            self.assertEqual(data['export_repairs'],[])
            self.assertEqual([row['lane'] for row in data['export_reconciled']],['old-a','old-b'])
            self.assertFalse([item for item in data['actions'] if item['lane']=='maintained-export-repair'])
            state['lanes']['old-c']=dict(lane='old-c',state='done',generation=1,revision=1,
                native={'head':'native'},issue=12,
                integration={'export_evidence':'missing-old-c.json','export_sha256':'bad'})
            data=report(state,50,root)
        repair=next(item for item in data['actions'] if item['lane']=='maintained-export-repair')
        self.assertIn('1 integrated lanes',repair['reason'])
        self.assertEqual([row['lane'] for row in data['export_repairs']],['old-c'])
        self.assertEqual([row['lane'] for row in data['export_reconciled']],['old-a','old-b'])

    def test_reconciled_export_debt_removes_undispatched_line_demand(self):
        from types import SimpleNamespace
        from workflow import export_repair
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.write_config(root,{'other':{}})
            state=self.unavailable_state(root,{'host':'other-host','pid':1,'started':'1'})
            state['throughput']['batches']={}
            state['lanes']['work']=dict(lane='work',state='done',generation=1,revision=1,
                native={'head':'native'},issue=10,
                integration={'export_evidence':'missing.json','export_sha256':'bad'})
            before=report(state,50,root)
            self.assertTrue([a for a in before['actions'] if a['lane']=='integration-line-unavailable'])
            evidence=root/'output'/'maintained-export.json'
            evidence.parent.mkdir(parents=True,exist_ok=True)
            evidence.write_text('{"action":"exported"}',encoding='utf-8')
            export_repair.record(SimpleNamespace(root=root,snapshot=lambda:state),None,
                                 'output/maintained-export.json',now=60.0)
            after=report(state,50,root)
        self.assertFalse([item for item in after['actions'] if item['lane']=='maintained-export-repair'])
        self.assertEqual([row['lane'] for row in after['export_reconciled']],['work'])


    def unavailable_state(self, root, process):
        return dict(
            lanes={'work':dict(lane='work',state='handoff_ready',generation=1,revision=2,native=None,handoff_at=10),
                   'integ':dict(lane='integ',state='blocked',generation=5,revision=9,process=process)},
            throughput=dict(workstreams={'species':dict(owner_lane='integ')},batches={}),
            throughput_runtime={})

    def write_config(self, root, lanes):
        path=root/'output'/'workflow'/'controller'/'config.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(dict(lanes=lanes)),encoding='utf-8')

    def test_undispatched_integration_line_surfaces_one_action(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.write_config(root,{'other':{}})
            state=self.unavailable_state(root,{'host':'other-host','pid':1,'started':'1'})
            data=report(state,50,root)
        outage=next(item for item in data['actions'] if item['lane']=='integration-line-unavailable')
        self.assertEqual(outage['priority'],0)
        self.assertEqual(outage['demand']['handoffs'],1)
        self.assertFalse(outage['owners'][0]['configured'])
        self.assertFalse(outage['owners'][0]['dispatchable'])
        self.assertIn('config.json',outage['next_action'])

    def test_dispatchable_configured_owner_has_no_outage(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.write_config(root,{'integ':{}})
            state=self.unavailable_state(root,identify(os.getpid()))
            state['lanes']['integ']['state']='running'
            data=report(state,50,root)
        self.assertFalse([item for item in data['actions'] if item['lane']=='integration-line-unavailable'])

    def test_no_integration_demand_has_no_outage(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.write_config(root,{'other':{}})
            state=self.unavailable_state(root,{'host':'other-host','pid':1,'started':'1'})
            state['lanes'].pop('work')
            data=report(state,50,root)
        self.assertFalse([item for item in data['actions'] if item['lane']=='integration-line-unavailable'])

    def parked_diagnosis(self, scope, status, lanes, owner_action=None, refreshed=None):
        return dict(scope=scope,status=status,lanes=lanes,owner_action=owner_action,
                    refreshed=refreshed,applied=False,dispatched=False)

    def test_parked_recovery_scopes_aggregate_with_owner_actions_and_divergence(self):
        diagnoses=[
            self.parked_diagnosis('enemies-1','unavailable',['lane-a'],
                owner_action='Refused: owner lane-a must re-submit the exact evidence'),
            self.parked_diagnosis('provider-runtime-fixtures','refreshable',['lane-b'],
                refreshed=dict(report=dict(path='output/workflow/evidence/'+'d'*64,sha256='d'*64)))]
        action=parked_scope_action(diagnoses,{'enemies-1':{},'resolved-since':{}})
        self.assertEqual(action['lane'],'planner-repair-evidence-parked')
        self.assertEqual(action['priority'],0)
        self.assertEqual(action['refreshable'],['provider-runtime-fixtures'])
        self.assertEqual(action['canonical_only'],['provider-runtime-fixtures'])
        self.assertEqual(action['controller_only'],['resolved-since'])
        self.assertIn('#855',action['next_action'])
        self.assertIn('re-submit',action['next_action'])
        row=next(r for r in action['scopes'] if r['scope']=='enemies-1')
        self.assertEqual(row['lanes'],['lane-a'])
        self.assertIn('lane-a',row['owner_action'])

    def test_parked_recovery_scopes_unavailable_only_is_priority_one(self):
        action=parked_scope_action(
            [self.parked_diagnosis('x','unavailable',[],owner_action='Refused: owner re-submits')],{})
        self.assertEqual(action['priority'],1)
        self.assertEqual(action['refreshable'],[])

    def test_parked_recovery_scopes_none_without_diagnoses(self):
        self.assertIsNone(parked_scope_action([],{'enemies-2':{}}))

    def test_parked_recovery_scopes_fail_closed_without_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.assertEqual(parked_scope_diagnoses(root,self.state(),50),[])
            data=report(self.state(),50,root)
        self.assertFalse([item for item in data['actions'] if item['lane']=='planner-repair-evidence-parked'])

    def test_parked_recovery_scope_reported_from_live_reproduction(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'output/workflow/evidence').mkdir(parents=True)
            config=dict(throughput=dict(autofill=dict(planner_pool=dict(
                enabled=True,prerequisite_recovery_seconds=300,
                helpers=[dict(scope='enemies-2',prerequisite_lanes=['owner'])]))))
            path=root/'output/workflow/controller/config.json';path.parent.mkdir(parents=True)
            path.write_text(json.dumps(config),encoding='utf-8')
            evidence=dict(path='output/run/gone.md',sha256='b'*64)
            state=dict(
                lanes={'owner':dict(lane='owner',state='blocked',issue=42,root={},native=None,
                    dependencies=['#42 missing input'],handoff=None,integration=None,
                    progress_at=1,started_at=1,worker_id='w',
                    outcome=dict(outcome='blocked',evidence=evidence))},
                throughput_runtime={'autofill':{'prerequisite_requests':{},'prerequisite_recovery':{}}},
                throughput={},
                planner_pool={'scopes':{'enemies-2':{'completed_at':1}}})
            data=report(state,2000,root)
        parked=next(item for item in data['actions'] if item['lane']=='planner-repair-evidence-parked')
        self.assertEqual(parked['priority'],1)
        self.assertEqual([row['scope'] for row in parked['scopes']],['enemies-2'])
        self.assertEqual(parked['scopes'][0]['status'],'unavailable')
        self.assertEqual(parked['scopes'][0]['lanes'],['owner'])
        self.assertEqual(parked['canonical_only'],['enemies-2'])
