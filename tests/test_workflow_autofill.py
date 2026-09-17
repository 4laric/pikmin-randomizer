"""Autonomous refill replay, priority and trust-boundary tests; no live workers."""
import copy
import hashlib
import json
import subprocess
import unittest
from unittest.mock import patch

from tests import test_workflow_scheduling as fixtures
from workflow.autofill import autofill_tick, autofill_status
from workflow.controller import Controller
from workflow.handoff import digest
from workflow.runner import write


class AutofillTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.SchedulingTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.reg, self.root = self.f.reg, self.f.root
        self.now = 1000
        self.reg.clock = lambda: self.now
        with self.reg.transaction() as state:
            state['lanes']['one'].update(state='done', review_disposition={'summary': 'accepted'})
        self.tree = self.root / 'output/source'
        self.tree.mkdir()
        self.git('init')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Test')
        (self.tree/'source.txt').write_text('pinned source')
        self.git('add', '.')
        self.git('commit', '-m', 'fixture')
        self.head = self.git('rev-parse', 'HEAD')
        self.out = self.root/'output/prepared'
        self.out.mkdir()
        self.brief, self.config = self.out/'brief.md', self.out/'opencode.json'
        self.brief.write_text('Review precisely the assigned acceptance scope. No ADMIT.')
        self.config.write_text('{}')
        self.inbox = self.root/'output/inbox'
        self.inbox.mkdir()
        self.manifest = self.root/'output/manifest.json'
        self.models = ['paid/muse']
        settings = dict(enabled=True, manifest=str(self.manifest), refill_cooldown_seconds=60)
        self.controller = Controller(self.reg, dict(output='output/controller', executable='unused', models=self.models,
            lanes={}, ram_high=90, ram_low=87, integrator_inbox=str(self.inbox), throughput=dict(autofill=settings)),
            spawn=lambda _: self.fail('Autofill cannot spawn'), memory=lambda: 60)
        self.remote = {}
        self.spec = self.make_spec('next', 900)
        self.save([self.spec])

    def git(self, *args):
        result = subprocess.run(['git','-C',str(self.tree),*args],capture_output=True,text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def make_spec(self, identity, issue, priority='enemy_acceptance'):
        tree=self.tree
        if identity != 'next':
            tree=self.root/'output'/('source-'+identity)
            subprocess.run(['git','clone','--shared',str(self.tree),str(tree)],check=True,capture_output=True)
        launch_out=self.out/identity
        launch_out.mkdir()
        body='Bounded '+identity+' acceptance issue. Codex through 4laric.'
        proof=dict(number=issue,state='OPEN',assignees=[{'login':'4laric'}],
                   url=f'https://github.com/4laric/pikmin-randomizer/issues/{issue}',body=body,updatedAt='2026-09-16T00:00:00Z')
        self.remote[issue]=proof
        path=self.out/(identity+'-issue.json')
        write(path,proof)
        return dict(id=identity,priority=priority,workstream='p2',role='review',capabilities=['python'],heavy=False,
            instruction='Complete '+identity+' review and applied disposition; no ADMIT',
            lane=dict(lane=identity,issue=issue,scope='Bounded '+identity,target_level='tooling',next_action='Verify acceptance',
                milestone='m',owned_files=['workflow/'+identity+'.py'],acceptance=['Verified disposition'],
                root=dict(base=self.head,head=self.head,commits=[],dirty='',worktree=str(tree)),native=None),
            launch=dict(root=str(tree),output=str(launch_out),brief=str(self.brief),config=str(self.config)),
            launch_hashes=dict(brief=digest(self.brief),config=digest(self.config)),
            issue_proof=dict(path=str(path),sha256=digest(path)),issue_body_sha256=hashlib.sha256(body.encode()).hexdigest())

    def save(self, items):
        write(self.manifest,dict(schema=1,repository='4laric/pikmin-randomizer',assignee='4laric',items=items))

    def tick(self):
        autofill_tick(self.controller, issue_reader=lambda n: copy.deepcopy(self.remote[n]))

    def second_worker(self):
        self.f.add_lane('two')
        with self.reg.transaction() as state:
            state['lanes']['two'].update(state='done',review_disposition={'summary':'accepted'})
        self.reg.register_pool_worker('two',['review'],['python'],'operator')

    def planner(self):
        self.f.add_lane('planner')
        self.controller.config['lanes']['planner']=self.spec['launch']
        self.controller.config['throughput']['autofill'].update(planner_lane='planner',low_watermark=4,planner_cooldown_seconds=300)

    def test_provision_and_replay_once_with_inherited_identity(self):
        self.tick(); self.tick()
        state=self.reg.status()
        lane=state['lanes']['next']
        self.assertEqual(lane['worker_id'],'one')
        self.assertEqual(lane['owner'],state['lanes']['one']['owner'])
        self.assertEqual(lane['task_id'],state['lanes']['one']['task_id'])
        pool=self.reg.scheduling_status()
        self.assertEqual(list(pool['jobs']),['autofill:next'])
        self.assertEqual(pool['jobs']['autofill:next']['focus'],'enemy_acceptance')
        self.assertEqual(pool['workstreams']['p2']['lanes'],['next'])
        self.assertFalse(self.reg.control_status()['launches'])

    def adaptation(self):
        self.spec.update(role='implementation', capabilities=['runtime-import'])
        self.save([self.spec])
        self.controller.config['throughput']['autofill']['worker_adaptation'] = dict(
            enabled=True, authorized_by='operator via issue 635', profiles=[dict(
                name='runtime-import', role='implementation', workstream='p2',
                requires=['python'], grants=['runtime-import'])])

    def test_adaptation_provisions_and_replays_once(self):
        self.adaptation()
        self.tick(); self.tick()
        self.assertEqual(self.reg.status()['lanes']['next']['worker_id'], 'one')
        self.assertEqual(self.reg.scheduling_status()['workers']['one']['capabilities'],
                         ['python', 'runtime-import'])
        with self.reg.transaction() as state:
            events = [e for e in state['events'] if e['kind'] == 'pool_worker_adapted']
        self.assertEqual(len(events), 1)
        self.assertEqual(list(self.reg.scheduling_status()['jobs']), ['autofill:next'])

    def test_adaptation_rejects_unsafe_or_unauthorized_workers(self):
        self.adaptation()
        with self.reg.transaction() as state:
            baseline = copy.deepcopy(state)
        cases = ['disabled', 'grant', 'requires', 'role', 'stream', 'live', 'unknown',
                 'unfinished', 'assignment', 'launch', 'reserved', 'owner', 'invalid-proof']
        policy = copy.deepcopy(self.controller.config['throughput']['autofill']['worker_adaptation'])
        for case in cases:
            with self.subTest(case=case):
                self.controller.config['throughput']['autofill']['worker_adaptation'] = copy.deepcopy(policy)
                p = self.controller.config['throughput']['autofill']['worker_adaptation']
                with self.reg.transaction() as state:
                    state.clear(); state.update(copy.deepcopy(baseline))
                    if case == 'disabled': p['enabled'] = False
                    if case in ('grant', 'requires'): p['profiles'][0]['grants' if case == 'grant' else 'requires'] = ['other']
                    if case == 'role': state['throughput']['workers']['one']['roles'] = ['review']
                    if case == 'stream': p['profiles'][0]['workstream'] = 'other'
                    if case in ('live', 'unknown'): state['lanes']['one']['process']['health'] = 'alive' if case == 'live' else 'unknown'
                    if case == 'unfinished': state['lanes']['one']['state'] = 'blocked'
                    if case == 'assignment': state['throughput']['assignments']['busy'] = dict(worker_id='one', status='assigned')
                    if case == 'launch': state.setdefault('control', {}).setdefault('launches', {})['busy'] = dict(lane='one', status='intent')
                    if case == 'reserved':
                        state.setdefault('throughput_runtime', {}).setdefault('autofill', {}).setdefault('items', {})['reserved'] = dict(
                            worker_id='one', previous_lane='one', phase='intent')
                    if case == 'owner': state['throughput']['workstreams']['other'] = dict(owner_lane='one')
                self.remote[900]['state'] = 'CLOSED' if case == 'invalid-proof' else 'OPEN'
                self.tick()
                self.assertNotIn('next', self.reg.status()['lanes'])
                self.assertEqual(self.reg.scheduling_status()['workers']['one']['capabilities'], ['python'])

    def test_crash_after_provision_resumes_same_worker(self):
        original=self.reg.provision_pool_lane
        def interrupted(*args):
            original(*args)
            raise OSError('crash after committed provision')
        with patch.object(self.reg,'provision_pool_lane',side_effect=interrupted): self.tick()
        self.assertEqual(self.reg.status()['lanes']['next']['worker_id'],'one')
        self.tick()
        self.assertEqual(autofill_status(self.reg)['items']['next']['phase'],'enqueued')

    def test_parked_owner_allows_full_provisioning_and_replay(self):
        self.reg.finish('owner', 1, 'review-ready', 'Batch complete; standby', self.f.evidence)
        with self.reg.transaction() as state:
            state['lanes']['owner']['process']['health'] = 'dead'
        self.tick()
        self.tick()
        self.assertEqual(autofill_status(self.reg)['items']['next']['phase'], 'enqueued')
        self.assertEqual(list(self.reg.scheduling_status()['jobs']), ['autofill:next'])

    def test_crash_after_enqueue_recovers_without_duplicate(self):
        original=self.reg.enqueue_job
        def interrupted(*args):
            original(*args)
            raise OSError('crash after job commit')
        with patch.object(self.reg,'enqueue_job',side_effect=interrupted): self.tick()
        self.tick()
        self.assertEqual(len(self.reg.scheduling_status()['jobs']),1)
        self.assertEqual(autofill_status(self.reg)['items']['next']['phase'],'enqueued')

    def test_changed_spec_refused_without_starving_independent_item(self):
        self.tick(); self.second_worker()
        changed=copy.deepcopy(self.spec);changed['instruction']='new unreviewed work'
        other=self.make_spec('other',901,'expansion')
        self.save([changed,other]);self.tick()
        self.assertIn('other',self.reg.status()['lanes'])
        self.assertEqual(autofill_status(self.reg)['items']['next']['status'],'blocked')

    def test_scope_overlap_releases_reservation_for_lower_priority(self):
        self.spec['lane']['owned_files']=['workflow/owner.py']
        other=self.make_spec('other',901,'expansion')
        self.save([self.spec,other]);self.tick()
        self.assertNotIn('next',self.reg.status()['lanes'])
        self.assertIn('other',self.reg.status()['lanes'])
        self.assertNotIn('previous_lane',autofill_status(self.reg)['items']['next'])

    def test_invalid_priority_does_not_abort_other_specs(self):
        self.spec['priority']='invented'
        other=self.make_spec('other',901,'expansion')
        self.save([self.spec,other]);self.tick()
        self.assertIn('other',self.reg.status()['lanes'])
        self.assertEqual(autofill_status(self.reg)['items']['next']['status'],'blocked')
        item = autofill_status(self.reg)['items']['next']
        self.assertEqual(item['dependency_kind'], 'workflow')
        self.assertIn('blocked_at', item)

    def test_enemy_priority_over_existing_content_and_one_per_tick(self):
        self.second_worker()
        content=self.make_spec('aaa-content',901,'existing_content')
        self.save([content,self.spec]);self.tick()
        self.assertIn('next',self.reg.status()['lanes'])
        self.assertNotIn('aaa-content',self.reg.status()['lanes'])
        self.tick()
        self.assertIn('aaa-content',self.reg.status()['lanes'])

    def test_issue_assignment_closed_or_scope_change_refuses(self):
        for change in ({'state':'CLOSED'},{'assignees':[]},{'body':'changed scope'}):
            self.remote[900]=dict(self.remote[900],**change)
            self.tick()
            self.assertNotIn('next',self.reg.status()['lanes'])

    def test_dirty_source_wrong_pin_or_modified_brief_blocks(self):
        (self.tree/'source.txt').write_text('dirty')
        self.tick();self.assertNotIn('next',self.reg.status()['lanes'])
        self.git('checkout','--','source.txt')
        self.brief.write_text('changed instruction')
        self.tick();self.assertNotIn('next',self.reg.status()['lanes'])

    def test_dispatch_refuses_brief_changed_after_provision(self):
        self.tick()
        self.assertTrue(self.controller.available('next'))
        self.config.write_text('{"permissions":"changed"}')
        self.assertFalse(self.controller.available('next'))

    def test_unknown_or_live_workers_are_not_reused(self):
        for health in ('alive','unknown'):
            with self.reg.transaction() as state: state['lanes']['one']['process']['health']=health
            self.tick();self.assertNotIn('next',self.reg.status()['lanes'])

    def test_high_ram_does_not_provision(self):
        self.controller.memory=lambda:90
        self.tick();self.assertNotIn('next',self.reg.status()['lanes'])

    def test_empty_backlog_requests_refill_with_bounded_cooldown(self):
        self.save([]);self.tick();self.tick()
        self.assertEqual(len(list(self.inbox.glob('*.md'))),1)
        self.now+=61;self.tick()
        self.assertEqual(len(list(self.inbox.glob('*.md'))),2)
        self.assertGreater(autofill_status(self.reg)['starvation_seconds'],0)
        self.save([self.spec]);self.tick()
        self.assertIn('next',self.reg.status()['lanes'])

    def test_persistent_planner_wakes_and_replays_only_after_cooldown(self):
        self.save([]);self.planner();self.tick();self.tick()
        launches=self.reg.control_status()['launches'];self.assertEqual(len(launches),1)
        with self.reg.transaction() as state:
            state['control']['launches'][next(iter(launches))]['status']='exited'
            state['lanes']['planner']['generation']+=1
            state['lanes']['planner']['state']='blocked'
        self.tick();self.assertEqual(len(self.reg.control_status()['launches']),1)
        self.now+=301;self.tick();self.assertEqual(len(self.reg.control_status()['launches']),2)
        self.assertFalse(list(self.inbox.glob('*.md')))

    def test_planner_live_or_inflight_is_normal_but_unknown_stays_visible(self):
        self.save([]);self.planner();self.tick()
        for health, expected_error in (('dead', None), ('alive', None), ('unknown', 'unknown')):
            with self.subTest(health=health):
                with self.reg.transaction() as state:
                    state['lanes']['planner']['process']['health']=health
                    state['throughput_runtime']['autofill']['last_planner_error']='stale error'
                self.tick()
                error=autofill_status(self.reg).get('last_planner_error')
                if expected_error is None:
                    self.assertIsNone(error)
                else:
                    self.assertIn(expected_error,error)
                self.assertEqual(len(self.reg.control_status()['launches']),1)
        with self.reg.transaction() as state:
            state['lanes']['planner'].update(state='done')
        self.tick()
        self.assertIn('not resumable',autofill_status(self.reg)['last_planner_error'])

    def test_content_backlog_cannot_suppress_enemy_planner(self):
        self.planner()
        content=[self.make_spec('content'+str(i),901+i,'expansion') for i in range(6)]
        self.save(content);self.tick()
        self.assertEqual(len(self.reg.control_status()['launches']),1)
        self.assertEqual(next(iter(self.reg.control_status()['launches'].values()))['lane'],'planner')

    def test_shared_private_worktree_rejected_and_worker_remains_available(self):
        self.second_worker();self.tick()
        other=self.make_spec('other',901,'expansion')
        other['lane']['root']['worktree']=self.spec['lane']['root']['worktree']
        other['launch']['root']=self.spec['launch']['root']
        self.save([self.spec,other]);self.tick()
        self.assertNotIn('other',self.reg.status()['lanes'])
        self.assertIn('worktree',autofill_status(self.reg)['items']['other']['reason'])

    def test_pool_dispatch_keeps_enemy_focus_ahead_of_content_repair(self):
        from workflow.throughput_controller import pool_tick
        self.second_worker()
        content=self.make_spec('content',901,'existing_content');content['role']='repair'
        self.save([content]);self.tick()
        self.save([content,self.spec]);self.tick()
        self.controller.config['throughput'].update(enabled=True,capture_costs=False,provisional_qa=False)
        self.controller.config['throughput']['autofill']['enabled']=False
        pool_tick(self.controller)
        launch=next(iter(self.reg.control_status()['launches'].values()))
        self.assertEqual(launch['lane'],'next')
        self.assertEqual(launch['focus'],'enemy_acceptance')

    def test_remote_rejection_cannot_be_reversed_by_cached_readiness(self):
        self.second_worker()
        second=self.make_spec('zz-enemy',901)
        self.save([self.spec,second]);self.tick()
        self.assertTrue(autofill_status(self.reg)['items']['zz-enemy']['ready'])
        self.remote[901]['state']='CLOSED'
        self.tick()
        item=autofill_status(self.reg)['items']['zz-enemy']
        self.assertFalse(item['ready'])
        self.assertEqual(item['status'],'blocked')
        self.assertNotIn('zz-enemy',self.reg.status()['lanes'])

    def test_queued_work_is_ready_not_active_or_starving(self):
        self.second_worker();self.tick();self.now+=61;self.tick()
        report=autofill_status(self.reg)
        self.assertEqual(report['ready_count'],1)
        self.assertEqual(report['active_enemy_count'],0)
        self.assertEqual(report['starvation_seconds'],0)

    def test_malformed_sibling_does_not_block_valid_spec(self):
        self.save([{'missing':'id'},dict(self.spec,id='malformed',priority='invented',lane={}),self.spec])
        self.tick()
        self.assertIn('next',self.reg.status()['lanes'])
        self.assertEqual(len(autofill_status(self.reg)['invalid_items']),2)

    def test_malformed_lane_priority_and_manifest_do_not_crash(self):
        self.save([dict(self.spec,id='null-lane',lane=None),dict(self.spec,id='list-priority',priority=[]),self.spec])
        self.tick()
        self.assertIn('next',self.reg.status()['lanes'])
        self.assertEqual(autofill_status(self.reg)['items']['null-lane']['status'],'blocked')
        write(self.manifest,[])
        self.tick()
        self.assertIn('Invalid autofill manifest',autofill_status(self.reg)['last_manifest_error'])

    def test_own_heavy_reservation_is_ready_then_reports_real_execution_state(self):
        self.spec['heavy']=True;self.save([self.spec]);self.tick()
        assignment=self.reg.assign_job('one',60)
        self.assertIsNotNone(assignment)
        self.tick()
        item=autofill_status(self.reg)['items']['next']
        self.assertTrue(item['ready'])
        self.assertIsNone(item['reason'])
        for state_name in ('running','waiting_resource','handoff_ready','review_ready'):
            with self.reg.transaction() as state:
                state['lanes']['next'].update(state=state_name,handoff_at=self.now)
                state['throughput_runtime']['autofill']['items']['next'].update(status='blocked',reason='Heavy build slots full')
            self.tick()
            item=autofill_status(self.reg)['items']['next']
            self.assertEqual(item['status'],state_name)
            self.assertIsNone(item['reason'])
            self.assertFalse(item['ready'])

    def test_invalid_json_wakes_fenced_planner_for_repair(self):
        self.planner();self.manifest.write_text('{invalid json')
        self.tick();self.tick()
        launches=list(self.reg.control_status()['launches'].values())
        self.assertEqual(len(launches),1)
        self.assertEqual(launches[0]['lane'],'planner')
        self.assertIn('repair the manifest',launches[0]['instruction'])
        self.assertTrue(autofill_status(self.reg)['last_manifest_error'])

    def test_invalid_pending_enemy_cannot_suppress_planner(self):
        self.planner();self.spec['capabilities']=['unauthorized']
        self.save([self.spec]);self.tick()
        report=autofill_status(self.reg)
        self.assertEqual(report['ready_count'],0)
        self.assertEqual(len(self.reg.control_status()['launches']),1)


from workflow.autofill import clustered_blockers


class ClusteredBlockersTests(unittest.TestCase):
    def test_shared_dependency_signature_across_lanes_is_surfaced(self):
        state = {'lanes': {
            'panmodoki38': {'state': 'blocked', 'dependencies': ['restart duplicate-cargo test capability'], 'scope': 'PanModoki38 acceptance'},
            'elecbug28': {'state': 'waiting_resource', 'dependencies': ['Restart Duplicate-Cargo Test Capability'], 'scope': 'ElecBug28 acceptance'},
        }}
        clusters = clustered_blockers(state)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0]['count'], 2)
        self.assertEqual(clusters[0]['lanes'], ['elecbug28', 'panmodoki38'])
        self.assertEqual(clusters[0]['signature'], 'restart duplicate-cargo test capability')

    def test_single_blocked_lane_is_not_a_cluster(self):
        state = {'lanes': {'panmodoki38': {'state': 'blocked', 'dependencies': ['restart duplicate-cargo test capability'], 'scope': ''}}}
        self.assertEqual(clustered_blockers(state), [])

    def test_existing_scoped_fix_suppresses_the_cluster(self):
        state = {'lanes': {
            'panmodoki38': {'state': 'blocked', 'dependencies': ['restart duplicate-cargo test capability'], 'scope': ''},
            'elecbug28': {'state': 'blocked', 'dependencies': ['restart duplicate-cargo test capability'], 'scope': ''},
            'fixture-fix': {'state': 'ready', 'dependencies': [], 'scope': 'Implement restart duplicate-cargo test capability'},
        }}
        self.assertEqual(clustered_blockers(state), [])

    def test_progress_detail_fallback_when_no_dependencies(self):
        state = {'lanes': {
            'a': {'state': 'blocked', 'dependencies': [], 'progress_detail': 'Needs shared fixture X', 'scope': ''},
            'b': {'state': 'blocked', 'dependencies': [], 'progress_detail': '  needs   SHARED fixture X  ', 'scope': ''},
        }}
        clusters = clustered_blockers(state)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0]['lanes'], ['a', 'b'])

    def test_differently_worded_blockers_do_not_cluster(self):
        state = {'lanes': {
            'a': {'state': 'blocked', 'dependencies': ['needs restart-duplicate-cargo capability'], 'scope': ''},
            'b': {'state': 'blocked', 'dependencies': ['restart duplicate-cargo test capability'], 'scope': ''},
        }}
        self.assertEqual(clustered_blockers(state), [])


if __name__ == '__main__': unittest.main()
