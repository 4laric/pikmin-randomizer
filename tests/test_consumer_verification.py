import copy
import json
import unittest
from tests import test_consumer_wakeup as wake_fixtures
from workflow.consumer_wakeup import tick
from workflow.consumer_verification import reconcile, report, metrics, repairs
from workflow.handoff import Rejected, digest


class VerificationTests(unittest.TestCase):
    def test_later_generation_gets_new_pending_check_without_copying_success(self):
        from workflow.consumer_verification import bind_context
        reconcile(self.c)
        with self.r.transaction() as state:
            old=state['consumer_verifications'][self.launch['id']]
            old.update(status='unverified')
            lane=state['lanes']['consumer'];lane['generation']+=1
            new=dict(id='recovery',created_at=self.f.now+1,instruction='Resume existing source',
                     lane='consumer',bound_generation=lane['generation'],reason='recovery')
            state['control']['launches']['recovery']=new
            bind_context(self.r,state,new,lane)
            self.assertIn('verification=recovery',new['instruction'])
            self.assertEqual(state['consumer_verifications']['recovery']['status'],'pending')
            self.assertEqual(state['consumer_verifications']['recovery']['consumer_generation'],lane['generation'])
            self.assertEqual(old['status'],'unverified')
        with self.assertRaises(Rejected):self.submit(generation=self.generation+1)

    def setUp(self):
        self.fixture=wake_fixtures.ConsumerWakeupTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.f=self.fixture.f;self.r=self.fixture.r;self.c=self.fixture.c
        tick(self.c)
        self.launch=next(iter(self.r.control_status()['launches'].values()))
        self.c.dispatch(self.launch)
        self.generation=self.state()['lanes']['consumer']['generation']
        path=self.f.root/'consumer-check.log';path.write_text('Actual consumer command and observed success')
        self.ev={'path':str(path),'sha256':digest(path)}
        self.check={'command':'compile owned consumer fixture','expected':'exit0','observed':'exit0'}

    def state(self):
        with self.r.transaction() as state: return copy.deepcopy(state)

    def submit(self, **kwargs):
        data=dict(verification=self.launch['id'],consumer='consumer',generation=self.generation,
                  passed=True,prerequisite_resolved=True,check=self.check,evidence=self.ev)
        data.update(kwargs);return report(self.r,**data)

    def test_integration_and_dispatch_are_not_success(self):
        reconcile(self.c)
        self.assertEqual(metrics(self.state(),self.f.now)['verified_unblocks'],0)
        self.assertEqual(metrics(self.state(),self.f.now)['pending'],1)

    def runtime_evidence(self):
        with self.r.transaction() as s:
            s['lanes']['consumer'].update(target_level='runtime',native={'head':'a'*40})
        exe=self.f.root/'game.exe';exe.write_bytes(b'synthetic test executable')
        log=self.f.root/'native.log';log.write_text('PASS ACTUAL_CONSUMER')
        result=self.f.root/'run-result.json'
        result.write_text(json.dumps(dict(argv=[str(exe)],passed=True,exit_code=0,timed_out=False,
                                         markers={'PASS ACTUAL_CONSUMER':True})))
        ev=lambda p:dict(path=str(p),sha256=digest(p))
        return dict(kind='game_runtime',native_head='a'*40,executable=ev(exe),log=ev(log),result=ev(result))

    def test_runtime_requires_matching_successful_run(self):
        proof=self.runtime_evidence()
        with self.assertRaises(Rejected):self.submit()
        for field,value in [('kind','diagnostic'),('native_head','b'*40)]:
            bad=copy.deepcopy(proof);bad[field]=value
            with self.assertRaises(Rejected):self.submit(runtime=bad)
        path=self.f.root/'run-result.json';original=path.read_text()
        for change in ({'timed_out':True},{'exit_code':1},{'markers':{}},{'argv':['wrong.exe']}):
            data=json.loads(original);data.update(change);path.write_text(json.dumps(data))
            proof['result']['sha256']=digest(path)
            with self.assertRaises(Rejected):self.submit(runtime=proof)
        path.write_text(original);proof['result']['sha256']=digest(path)
        self.submit(runtime=proof)

    def test_blocked_runtime_legacy_pass_becomes_repair_demand(self):
        self.submit()
        with self.r.transaction() as s:s['lanes']['consumer']['target_level']='runtime'
        self.r.finish('consumer',self.generation,'blocked','Engine path still missing',self.ev,['#186'])
        reconcile(self.c);reconcile(self.c)
        self.assertEqual(self.state()['consumer_verifications'][self.launch['id']]['status'],'unverified')
        self.assertEqual(len(repairs(self.state())),1)

    def test_diagnostic_success_requires_explicit_resolution(self):
        for value in (None, False, 'true'):
            with self.assertRaises(Rejected): self.submit(prerequisite_resolved=value)
        self.submit(passed=False, prerequisite_resolved=False,
                    check=dict(command='reproduce defect', expected='FAILURE_REPRODUCED exit 0',
                               observed='FAILURE_REPRODUCED exit 0'))
        self.assertEqual(metrics(self.state(),self.f.now)['verified_unblocks'],0)

    def test_legacy_pass_is_unverified_preserving_report_and_repair_demand(self):
        self.submit()
        with self.r.transaction() as state:
            record=state['consumer_verifications'][self.launch['id']]
            del record['prerequisite_resolved']
        self.assertEqual(metrics(self.state(),self.f.now)['verified_unblocks'],0)
        self.r.finish('consumer',self.generation,'blocked','Original defect persists',self.ev,['#1'])
        reconcile(self.c); reconcile(self.c)
        state=self.state();record=state['consumer_verifications'][self.launch['id']]
        self.assertEqual(record['status'],'unverified')
        self.assertEqual(record['reported_status'],'passed')
        self.assertEqual(record['check'],self.check)
        self.assertEqual(record['evidence'],self.ev)
        self.assertEqual(len(repairs(state)),1)
        self.assertEqual(sum(e['kind']=='consumer_resolution_unverified' for e in state['events']),1)

    def test_only_live_fenced_consumer_with_independent_evidence_can_pass(self):
        with self.assertRaises(Rejected):self.submit(generation=1)
        with self.assertRaises(Rejected):self.submit(evidence=self.f.ev)
        with self.assertRaises(Rejected):self.submit(check={'command':'compile'})
        with self.assertRaises(Rejected):self.submit(evidence=dict(self.ev,sha256='bad'))
        self.r.probe=lambda _: 'unknown'
        with self.assertRaises(Rejected):self.submit()
        self.r.probe=lambda _: 'alive'
        self.submit()
        self.assertEqual(metrics(self.state(),self.f.now)['verified_unblocks'],1)
        with self.assertRaises(Rejected):self.submit()

    def test_blocked_outcome_creates_one_unverified_repair_group(self):
        self.r.finish('consumer',self.generation,'blocked','Same compiler defect',self.ev,['#1'])
        reconcile(self.c);reconcile(self.c)
        state=self.state();self.assertEqual(metrics(state,self.f.now)['verified_unblocks'],0)
        self.assertEqual(len(repairs(state)),1)
        other=copy.deepcopy(state['lanes']['consumer']);state['lanes']['other']=other
        record=copy.deepcopy(next(iter(state['consumer_verifications'].values())))
        record.update(id='other-check',consumer='other')
        state['consumer_verifications']['other-check']=record
        self.assertEqual(len(repairs(state)),1)
        self.assertEqual(len(repairs(state)[0]['consumers']),2)

    def test_pass_for_original_gap_survives_other_blocker(self):
        self.submit()
        self.r.finish('consumer',self.generation,'blocked','Different gameplay blocker',self.ev,['#186'])
        reconcile(self.c)
        self.assertEqual(repairs(self.state()),[])
        self.assertEqual(metrics(self.state(),self.f.now)['verified_unblocks'],1)

    def test_new_generation_supersedes_unreported_attempt(self):
        with self.r.transaction() as state:state['lanes']['consumer']['generation']+=1
        reconcile(self.c)
        self.assertEqual(metrics(self.state(),self.f.now)['pending'],0)

    def test_historical_completion_without_report_is_not_pending_or_passed(self):
        with self.r.transaction() as state:
            state['lanes']['consumer'].update(state='done',outcome=None)
        reconcile(self.c)
        self.assertEqual(metrics(self.state(),self.f.now)['pending'],0)
        self.assertEqual(metrics(self.state(),self.f.now)['verified_unblocks'],0)
