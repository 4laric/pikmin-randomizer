"""Failure injection for controller replay, provider failover and outcome boundaries."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import sys
import time
import unittest

from workflow.control import fingerprint
from workflow.controller import Controller
from workflow.handoff import Rejected, digest, validate_review
from workflow.processes import identify
from workflow.registry import Registry
from workflow.runner import write, decisions_from_text


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve(); self.now = 1000
        self.identity = identify(os.getpid())
        self.reg = Registry(self.root/'output/workflow/registry.sqlite3', self.root,
            clock=lambda: self.now, process_probe=lambda p: 'alive' if p == self.identity else 'dead')
        self.reg.init(); self.out = self.root/'output/lane'; self.out.mkdir()
        self.log = self.out/'review.txt'; self.log.write_text('Independent review; no fresh GL run')
        self.ev = dict(path=str(self.log), sha256=digest(self.log))
        self.add_lane('provider', 1); self.add_lane('consumer', 2)
        self.config = dict(executable='unused.exe', models=['free/muse', 'paid/muse'], output='output/controller',
            lanes={'consumer': dict(root=str(self.root), output=str(self.out), brief=str(self.log), config=str(self.log))})
        self.spawns = []; self.memory = 60
        def spawn(directory):
            self.spawns.append(directory)
            write(directory/'runner.json', self.identity)
        self.controller = Controller(self.reg, self.config, spawn=spawn, memory=lambda: self.memory)

    def add_lane(self, key, issue):
        self.reg.register(dict(lane=key, owner='Codex', worker_id=key, task_id='opencode:session-'+key,
            issue=issue, scope='one slice', target_level='candidate', next_action='work', milestone='m',
            owned_files=[key+'.py'], acceptance=['tested'], pid=os.getpid(),
            root=dict(base='a'*40,head='a'*40,commits=[],dirty='',worktree=str(self.root)),native=None))
        with self.reg.transaction() as state:
            state['lanes'][key]['process'] = {'pid': -1, 'created': key}
            state['lanes'][key]['state'] = 'running'

    def ready_dependency(self, version='v1'):
        with self.reg.transaction() as state:
            state['lanes']['provider']['state'] = 'done'
            state['lanes']['provider']['integration'] = {'root_commit': 'a'*40}
        self.reg.publish('provider', version, self.ev, 'verified candidate')
        lane = self.reg.status()['lanes']['consumer']
        self.reg.finish('consumer', lane['generation'], 'blocked', 'need provider', self.ev, ['provider'])

    def plan(self):
        return self.reg.plan_launch('consumer', 'test', 'Inspect previous work', self.config['models'])

    def test_duplicate_dependency_event_plans_once(self):
        self.ready_dependency(); self.controller.dependencies(); self.controller.dependencies()
        self.assertEqual(len(self.reg.control_status()['launches']), 1)

    def test_unbound_timeout_archives_dead_runner_and_reuses_intent(self):
        item=self.plan();directory=self.controller.launch_directory(item['id']);directory.mkdir(parents=True)
        write(directory/'runner.json',{'pid':-123,'started':'old'})
        write(directory/'result.json',{'kind':'registration_timeout'})
        write(directory/'spawn.json',{'at':0})
        self.assertTrue(self.controller.dispatch(item))
        self.assertEqual(self.reg.control_status()['launches'][item['id']]['status'],'running')
        self.assertEqual(len(list(directory.parent.glob(item['id']+'.unbound-*'))),1)
        self.assertEqual(len(self.spawns),1)

    def test_unbound_recovery_refuses_possible_child_or_live_runner(self):
        item=self.plan();directory=self.controller.launch_directory(item['id']);directory.mkdir(parents=True)
        write(directory/'runner.json',self.identity);write(directory/'result.json',{'kind':'registration_timeout'})
        self.assertFalse(self.controller.recover_unbound(item,directory))
        write(directory/'runner.json',{'pid':-123})
        for name in ('child.json','start.json'):
            write(directory/name,{})
            self.assertFalse(self.controller.recover_unbound(item,directory))
            (directory/name).unlink()

    def test_unbound_recovery_has_retry_budget(self):
        item=self.plan();directory=self.controller.launch_directory(item['id']);directory.mkdir(parents=True)
        write(directory/'runner.json',{'pid':-123});write(directory/'result.json',{'kind':'registration_timeout'})
        with self.reg.transaction() as s:s['control']['launches'][item['id']]['unbound_retries']=3
        self.assertFalse(self.controller.recover_unbound(item,directory))

    def test_same_version_not_resumed_after_consumption(self):
        self.ready_dependency(); self.controller.dependencies()
        item = next(iter(self.reg.control_status()['launches'].values())); self.controller.dispatch(item)
        with self.reg.transaction() as state:
            state['lanes']['consumer']['process'] = {'pid': -2}
            self.reg.control(state)['launches'][item['id']]['status'] = 'exited'
        lane = self.reg.status()['lanes']['consumer']
        self.reg.finish('consumer',lane['generation'],'blocked','still blocked',self.ev,['provider'])
        self.controller.dependencies()
        self.assertEqual(len(self.reg.control_status()['launches']),1)
        self.reg.publish('provider','v2',self.ev,'revised contract'); self.controller.dependencies()
        self.assertEqual(len(self.reg.control_status()['launches']),2)

    def test_unintegrated_provider_cannot_publish(self):
        with self.assertRaises(Rejected): self.reg.publish('provider','v1',self.ev,'contract')

    def test_artifact_versions_immutable(self):
        self.ready_dependency()
        with self.assertRaises(Rejected): self.reg.publish('provider','v1',self.ev,'different')

    def test_external_issue_does_not_auto_unblock(self):
        self.reg.finish('consumer',1,'blocked','need review',self.ev,['#437'])
        self.controller.dependencies(); self.assertFalse(self.reg.control_status()['launches'])

    def test_review_ready_is_not_runtime_acceptance(self):
        lane=self.reg.finish('consumer',1,'review-ready','evidence reviewed',self.ev)
        self.assertEqual(lane['state'],'review_ready')
        self.assertFalse(validate_review(self.root,lane['review'],lane)['gameplay_accepted'])
        self.assertFalse(any(a['lane']=='consumer' for a in self.reg.watchdog()))

    def test_review_cannot_claim_fresh_runtime(self):
        lane=self.reg.finish('consumer',1,'review-ready','reviewed',self.ev)
        data=lane['review'];data['fresh_runtime']=True
        with self.assertRaises(Rejected):validate_review(self.root,data,lane)

    def test_review_acknowledgement_does_not_publish_source_or_count_integration(self):
        self.reg.finish('consumer',1,'review-ready','reviewed',self.ev)
        self.reg.accept_review('consumer',1,'review received',self.ev)
        self.reg.accept_review('consumer',1,'review received',self.ev)
        self.assertEqual(self.reg.status()['metrics']['completed_slices'],0)
        with self.assertRaises(Rejected):self.reg.publish('consumer','v1',self.ev,'not a source integration')

    def test_missing_terminal_outcome_is_reconciliation(self):
        item=self.plan();self.controller.dispatch(item)
        self.reg.probe=lambda _: 'dead'
        write(self.controller.launch_directory(item['id'])/'result.json',{'kind':'exit','exit_code':0})
        self.controller.complete_runs()
        self.assertEqual(self.reg.status()['lanes']['consumer']['state'],'reconciling')
        self.assertEqual(len(self.reg.control_status()['launches']),1)

    def test_rate_limit_selects_paid_same_session(self):
        item=self.plan();self.controller.dispatch(item);self.reg.probe=lambda _: 'dead'
        write(self.controller.launch_directory(item['id'])/'result.json',{'kind':'rate_limit','exit_code':1})
        self.controller.complete_runs()
        items=list(self.reg.control_status()['launches'].values())
        self.assertEqual(items[-1]['session'],item['session'])
        self.assertEqual(self.reg.select_model(self.config['models']),'paid/muse')
        self.assertEqual(len(items),2)
        self.controller.complete_runs();self.assertEqual(len(self.reg.control_status()['launches']),2)

    def test_global_provider_cooldown_expires(self):
        self.reg.cool_provider('free',50)
        self.assertEqual(self.reg.select_model(['free/other','paid/muse']),'paid/muse')
        self.now+=51;self.assertEqual(self.reg.select_model(['free/other','paid/muse']),'free/other')

    def test_same_provider_fallback_keeps_session_and_priority(self):
        self.config['models'] = ['go/muse', 'go/deepseek']
        item = self.plan()
        with self.reg.transaction() as state:
            self.reg.control(state)['launches'][item['id']]['focus'] = 'enemy_acceptance'
        self.controller.dispatch(item); self.reg.probe = lambda _: 'dead'
        write(self.controller.launch_directory(item['id'])/'result.json', {'kind':'rate_limit'})
        self.controller.complete_runs(); self.controller.complete_runs()
        items = list(self.reg.control_status()['launches'].values())
        self.assertEqual(len(items), 2)
        self.assertEqual(items[-1]['session'], item['session'])
        self.assertEqual(items[-1]['focus'], 'enemy_acceptance')
        self.assertEqual(self.reg.select_model(items[-1]['models']), 'go/deepseek')
        self.assertEqual(self.reg.control_status()['model_limits']['go/muse']['count'], 1)
        self.assertFalse(self.reg.control_status()['providers'])

    def test_adaptive_penalty_replay_cap_and_quiet_reset(self):
        for index, seconds in enumerate([30, 60, 120, 240, 300, 300]):
            result = self.reg.model_rate_limit('go/muse', str(index))
            self.assertEqual(result['seconds'], seconds)
            self.assertEqual(self.reg.model_rate_limit('go/muse', str(index)), result)
            self.now += seconds
        self.now += 1801
        self.assertEqual(self.reg.model_rate_limit('go/muse', 'fresh')['seconds'], 30)

    def test_both_models_cooling_then_earliest_recovers(self):
        self.reg.model_rate_limit('go/muse', 'one', initial=60)
        self.reg.model_rate_limit('go/deepseek', 'two')
        self.assertIsNone(self.reg.select_model(['go/muse', 'go/deepseek']))
        self.now += 31
        self.assertEqual(self.reg.select_model(['go/muse', 'go/deepseek']), 'go/deepseek')

    def test_single_model_rate_limit_retains_delayed_retry(self):
        self.config['models'] = ['go/muse']
        item = self.plan(); self.controller.dispatch(item); self.reg.probe = lambda _: 'dead'
        write(self.controller.launch_directory(item['id'])/'result.json', {'kind':'rate_limit'})
        self.controller.complete_runs()
        retry = list(self.reg.control_status()['launches'].values())[-1]
        self.assertEqual(retry['status'], 'intent')
        self.assertIsNone(self.reg.select_model(retry['models']))
        self.now += 31
        self.assertEqual(self.reg.select_model(retry['models']), 'go/muse')

    def test_retry_budget_exhaustion_requires_reconciliation(self):
        item = self.plan(); self.controller.dispatch(item); self.reg.probe = lambda _: 'dead'
        with self.reg.transaction() as state:
            self.reg.control(state)['launches'][item['id']]['rate_limit_retries'] = 8
        write(self.controller.launch_directory(item['id'])/'result.json', {'kind':'rate_limit'})
        self.controller.complete_runs()
        self.assertEqual(len(self.reg.control_status()['launches']), 1)
        self.assertEqual(self.reg.status()['lanes']['consumer']['state'], 'reconciling')

    def test_rate_limit_after_tools_exited_keeps_same_session(self):
        self.config['models'] = ['go/muse', 'go/deepseek']
        item = self.plan(); self.controller.dispatch(item); self.reg.probe = lambda _: 'dead'
        write(self.controller.launch_directory(item['id'])/'result.json',
              {'kind':'exit', 'rate_limit':True, 'tools_started':True, 'exit_code':1})
        self.controller.complete_runs()
        retry = list(self.reg.control_status()['launches'].values())[-1]
        self.assertEqual(retry['session'], item['session'])
        self.assertEqual(self.reg.select_model(retry['models']), 'go/deepseek')

    def test_launch_pacing_survives_controller_restart(self):
        item = self.plan(); self.controller.dispatch(item)
        restarted = Controller(self.reg, self.config, spawn=lambda _: self.fail('Duplicate spawn'), memory=lambda:60)
        restarted.dispatch(item)
        self.assertEqual(self.reg.select_model(['free/muse']), None)
        self.now += 16
        self.assertEqual(self.reg.select_model(['free/muse']), 'free/muse')

    def test_cooling_model_does_not_spawn_or_bind(self):
        self.config['models'] = ['go/muse']
        item = self.plan(); self.reg.model_rate_limit('go/muse', 'prior')
        self.controller.dispatch(item)
        self.assertFalse(self.spawns)
        self.assertEqual(self.reg.control_status()['launches'][item['id']]['status'], 'intent')

    def test_intent_replay_idempotent(self):
        first=self.plan();second=self.plan();self.assertEqual(first['id'],second['id'])

    def test_crash_after_spawn_before_registration_reuses_runner(self):
        item=self.plan();directory=self.controller.launch_directory(item['id']);directory.mkdir(parents=True)
        write(directory/'spawn.json',{'at':self.now});write(directory/'runner.json',self.identity)
        self.controller.dispatch(item)
        self.assertFalse(self.spawns)
        self.assertTrue((directory/'start.json').exists())

    def test_crash_before_spawn_recording_is_fail_closed(self):
        item=self.plan();directory=self.controller.launch_directory(item['id']);directory.mkdir(parents=True)
        write(directory/'spawn.json',{'at':self.now});self.now+=121
        self.controller.dispatch(item);self.assertFalse(self.spawns)
        self.assertTrue(any(n['kind']=='uncertain_dispatch' for n in self.reg.control_status()['notices'].values()))

    def test_crash_after_bind_before_start_replayed(self):
        item=self.plan();directory=self.controller.launch_directory(item['id']);directory.mkdir(parents=True)
        write(directory/'spawn.json',{'at':self.now});write(directory/'runner.json',self.identity)
        self.reg.bind_launch(item['id'],self.identity)
        self.controller.tick()
        self.assertTrue((directory/'start.json').exists());self.assertFalse(self.spawns)

    def test_live_owner_prevents_resume(self):
        with self.reg.transaction() as state:state['lanes']['consumer']['process']=self.identity
        with self.assertRaises(Rejected):self.plan()

    def test_live_legacy_supervisor_prevents_adoption(self):
        self.config['lanes']['consumer']['legacy_supervisors']=[self.identity]
        self.ready_dependency();self.controller.dependencies()
        self.assertFalse(self.reg.control_status()['launches'])

    def test_generation_fence_rejects_old_worker(self):
        item=self.plan();self.controller.dispatch(item)
        with self.assertRaises(Rejected):self.reg.finish('consumer',1,'blocked','old',self.ev,['#1'])

    def test_capacity_hysteresis(self):
        self.memory=78;self.assertFalse(self.controller.capacity())
        self.memory=74;self.assertFalse(self.controller.capacity())
        self.memory=71;self.assertTrue(self.controller.capacity())

    def test_tampered_artifact_not_dispatched(self):
        self.ready_dependency();self.log.write_text('tampered')
        with self.assertRaises(Rejected):self.controller.dependencies()

    def test_controller_singleton(self):
        self.reg.controller_claim(self.identity)
        with self.assertRaises(Rejected):self.reg.controller_claim({'pid':999})

    def test_unsafe_shepherd_action_rejected(self):
        with self.assertRaises(Rejected):self.controller.apply_decisions({'notices':{'a':{'lane':'consumer'}}},[{'notice':'a','action':'admit'}])

    def test_stale_shepherd_decision_rejected(self):
        lane=self.reg.status()['lanes']['consumer'];packet=dict(id='p',notices={'a':{'lane':'consumer'}},lanes={'consumer':copy.deepcopy(lane)})
        with self.reg.transaction() as state:state['lanes']['consumer']['progress_at']+=1
        with self.assertRaises(Rejected):self.controller.apply_decisions(packet,[{'notice':'a','action':'notify','reason':'review'}])

    def decision_packet(self):
        notice=self.reg.notice('consumer','integration_needed',{'reason':'test'})
        lane=self.reg.status()['lanes']['consumer']
        return dict(id='packet',notices={notice:self.reg.control_status()['notices'][notice]},lanes={'consumer':lane}),notice

    def test_review_routing_preserves_existing_implementation_handoff(self):
        with self.reg.transaction() as state:
            state['lanes']['consumer'].update(state='handoff_ready',handoff={'path':'preserve','result':{'outstanding_gates':[]}},handoff_at=self.now)
        packet,notice=self.decision_packet()
        self.controller.apply_decisions(packet,[dict(notice=notice,action='review-ready',reason='Route this handoff')])
        lane=self.reg.status()['lanes']['consumer']
        self.assertEqual(lane['state'],'handoff_ready');self.assertEqual(lane['handoff']['path'],'preserve')

    def test_completed_while_model_thinks_is_not_reopened(self):
        packet,notice=self.decision_packet()
        with self.reg.transaction() as state:state['lanes']['consumer']['state']='done'
        self.controller.apply_decisions(packet,[dict(notice=notice,action='review-ready',reason='Outdated advice')])
        self.assertEqual(self.reg.status()['lanes']['consumer']['state'],'done')
        self.assertEqual(next(iter(self.reg.control_status()['decisions'].values()))['action'],'superseded')

    def test_same_notice_in_later_packet_is_not_delivered_twice(self):
        packet,notice=self.decision_packet();decision=dict(notice=notice,action='notify',reason='Review')
        self.controller.apply_decisions(packet,[decision]);packet['id']='another-packet'
        self.controller.apply_decisions(packet,[decision])
        self.assertEqual(len(self.reg.control_status()['decisions']),1)

    def test_large_model_response_executes_bounded_batch_without_discarding_all(self):
        notices={};decisions=[]
        for n in range(25):
            key=self.reg.notice('consumer','diagnosis',{'n':n})
            notices[key]=self.reg.control_status()['notices'][key]
            decisions.append(dict(notice=key,action='notify',reason='Finding '+str(n)))
        packet=dict(id='batch',notices=notices,lanes={'consumer':self.reg.status()['lanes']['consumer']})
        self.controller.apply_decisions(packet,decisions)
        self.assertEqual(len(self.reg.control_status()['decisions']),20)
        self.assertEqual(sum(n['status']=='pending' for n in self.reg.control_status()['notices'].values()),5)

    def test_changed_publication_keeps_previous_evidence_immutable(self):
        self.ready_dependency()
        self.config['publications']=[dict(producer='provider',path=str(self.log),description='contract')]
        self.controller.receipts()
        before=list(self.reg.control_status()['artifacts'].values())[-1]
        self.log.write_text('new reviewed contract');self.controller.receipts()
        self.reg.evidence(before['evidence'])

    def test_live_build_activity_suppresses_stall_notice(self):
        self.now=100000
        build=self.out/'build-1.log';build.write_text('compiling')
        os.utime(build,(self.now,self.now))
        with self.reg.transaction() as state:
            state['lanes']['consumer']['process']=self.identity
            state['leases']['build:test']={'lane':'consumer','generation':1,'process':self.identity}
        self.controller.observe()
        self.assertFalse(any(n['kind']=='progress_stale' for n in self.reg.control_status()['notices'].values()))

    def test_old_live_child_prevents_exit_recovery(self):
        item=self.plan();self.controller.dispatch(item)
        directory=self.controller.launch_directory(item['id'])
        write(directory/'result.json',{'kind':'exit','exit_code':1})
        write(directory/'child.json',{'pid':999})
        self.reg.probe=lambda p:'alive' if p.get('pid')==999 else 'dead'
        self.controller.complete_runs()
        self.assertEqual(self.reg.control_status()['launches'][item['id']]['status'],'running')

    def test_notifications_delivered_once(self):
        self.config['integrator_inbox']='output/inbox'
        with self.reg.transaction() as state:
            self.reg.control(state)['decisions']['one']={'action':'notify','reason':'Review completed slice'}
        self.controller.deliver_notifications()
        file=self.root/'output/inbox/900-controller-one.md';file.unlink() # Integrator consumed it.
        self.controller.deliver_notifications();self.assertFalse(file.exists())

    def test_integration_receipt_checks_real_ancestry_and_replays(self):
        from tests.test_pikmin2_workflow import WorkflowTests
        def run(*args):
            result=subprocess.run(['git','-C',str(self.root),*args],text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr);return result.stdout.strip()
        run('init');run('config','user.email','tests@example.invalid');run('config','user.name','Workflow tests')
        (self.root/'consumer.py').write_text('pass\n');run('add','consumer.py');run('commit','-m','candidate')
        head=run('rev-parse','HEAD')
        with self.reg.transaction() as state:
            state['lanes']['consumer']['root'].update(base=head,head=head)
        lane=self.reg.status()['lanes']['consumer']
        # Reuse a fully validated synthetic tooling handoff; integration itself uses real git objects.
        helper=WorkflowTests();helper.root=self.root;helper.evidence=self.ev
        data=helper.handoff(lane)
        path=self.out/'handoff.json';path.write_text(json.dumps(data))
        lane=self.reg.submit_handoff('consumer',1,lane['revision'],str(path))
        record=dict(root_commit=head,validation_path=str(self.log),validation_sha256=digest(self.log))
        self.reg.receipt('consumer',1,record,str(self.root))
        self.reg.receipt('consumer',1,record,str(self.root))
        self.assertEqual(self.reg.status()['metrics']['completed_slices'],1)
        changed=record|{'root_commit':'b'*40}
        with self.assertRaises(Rejected):self.reg.receipt('consumer',1,changed,str(self.root))

    def test_real_runner_waits_for_registration_and_rejects_duplicate(self):
        directory=self.root/'output/runner';directory.mkdir()
        (self.root/'run').write_text("import json\nprint(json.dumps({'type':'step_start','sessionID':'known-session'}))\nprint(json.dumps({'type':'text','part':{'text':'[]'}}))\n")
        proc=subprocess.Popen([sys.executable,'-m','workflow.runner',str(directory)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.addCleanup(lambda: proc.kill() if proc.poll() is None else None)
        for _ in range(50):
            if (directory/'runner.json').exists():break
            time.sleep(.1)
        self.assertTrue((directory/'runner.json').exists())
        self.assertFalse((directory/'child.json').exists())
        write(directory/'start.json',dict(executable=sys.executable,worktree=str(self.root),config=str(self.log),
            model='fake/model',session='known-session',prompt='test',action_id='test',read_only_shepherd=True))
        _,err=proc.communicate(timeout=15);self.assertEqual(proc.returncode,0,err)
        result=json.loads((directory/'result.json').read_text());self.assertEqual(result['session'],'known-session')
        self.assertEqual(json.loads((directory/'decisions.json').read_text()),[])
        replay=subprocess.run([sys.executable,'-m','workflow.runner',str(directory)],capture_output=True,timeout=15)
        self.assertNotEqual(replay.returncode,0)
        self.assertEqual(json.loads((directory/'result.json').read_text()),result)

    def test_shepherd_transport_requires_a_complete_json_array(self):
        self.assertEqual(decisions_from_text('```json\n[{"action":"notify"}]\n```'),[{'action':'notify'}])
        self.assertEqual(decisions_from_text('[]'),[])
        self.assertIsNone(decisions_from_text('Explanation, then [{"action":"resume"}]'))
        self.assertIsNone(decisions_from_text('{"action":"resume"}'))
        self.assertEqual(decisions_from_text('Reasoning summary.\n```json\n[]\n```'),[])
        self.assertIsNone(decisions_from_text('```json\n[]\n```\n```json\n[]\n```'))


if __name__=='__main__':unittest.main()
