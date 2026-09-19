"""Synthetic coordination races and evidence checks; no game builds or launches."""
import concurrent.futures
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from workflow.handoff import GATES, Rejected, digest, validate_handoff
from workflow.processes import identify, probe
from workflow.registry import Registry


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.now = 1000.0
        self.health = 'alive'
        self.db = self.root / 'output/coord/registry.sqlite3'
        self.reg = Registry(self.db, self.root, clock=lambda: self.now, process_probe=lambda _: self.health)
        self.reg.init(dict(max_heavy_builds=1, heartbeat_seconds=10, progress_seconds=30))
        self.log = self.root / 'output/log.txt'
        self.log.write_text('test passed\nninja: no work to do.\n')
        self.evidence = {'path': str(self.log), 'sha256': digest(self.log)}

    def data(self, key='one', worker=None):
        return dict(lane=key, owner='Codex through 4laric', worker_id=worker or key,
                    task_id='task-' + key, issue={'one': 490, 'two': 491, 'three': 492}[key],
                    scope='Bounded tool slice', target_level='tooling', next_action='Run checks',
                    milestone='workflow', owned_files=['workflow/' + key + '.py'],
                    acceptance=['Concurrent claims remain exclusive'], pid=os.getpid(),
                    root=dict(base='a'*40, head='a'*40, commits=[], dirty='', worktree='.'), native=None)

    def register(self, key='one', worker=None):
        return self.reg.register(self.data(key, worker))

    def running(self, key='one'):
        self.register(key)
        return self.reg.checkpoint(key, 1, 1, {'state': 'running'})

    def handoff(self, lane=None, runtime=False):
        lane = lane or self.reg.status()['lanes']['one']
        data = {key: lane[key] for key in ('lane', 'owner', 'task_id', 'issue', 'generation', 'scope',
                                           'target_level', 'owned_files', 'root', 'native')}
        data.update(schema=1, parent_issue=186, kind='tooling', next_action='Review',
            changed_files=list(lane['owned_files']), evidence={'log': self.evidence}, remaining_work=[], shared_reviews=[],
            source_mapping=[{'description': 'Workflow contract', 'evidence': ['log']}],
            tests=[{'command': 'python -m unittest', 'exit_code': 0, 'evidence': ['log']}],
            gates={g: {'status': 'UNTESTED', 'method': 'unobserved', 'detail': 'Tooling-only slice'} for g in GATES},
            slice_acceptance=[{'criterion': lane['acceptance'][0], 'status': 'PASS', 'evidence': ['log']}],
            fixture_adoption={'status': 'N/A', 'reason': 'No native runtime change'})
        if runtime:
            build = self.root / 'output/build'
            build.mkdir(exist_ok=True)
            exe = build / 'fixture.exe'
            exe.write_bytes(b'synthetic executable')
            data['kind'] = 'runtime'
            data['native'] = copy.deepcopy(data['root'])
            data['fixture_adoption'] = {'status': 'PASS'} | {k: ['log'] for k in (
                'window', 'live_squad', 'active_gameplay', 'no_immediate_extinction', 'fresh_arena',
                'overlay_source', 'window_source', 'assets_config')}
            prov = dict(status='built', expected_native_head='a'*40, source=str(self.root), build=str(build),
                        observed_source={'head': 'a'*40, 'status': ''},
                        artifacts={str(exe): {'sha256': digest(exe)}})
            path = build / 'provenance.json'
            path.write_text(json.dumps(prov))
            data['evidence'] = data['evidence'] | {
                'exe': {'path': str(exe), 'sha256': digest(exe)},
                'provenance': {'path': str(path), 'sha256': digest(path)}}
            data['build'] = dict(command='cmake --build', directory=str(build), exit_code=0, evidence=['log'],
                dry_run=['log'], dry_run_exit_code=0, executable='exe', replacement_main=True, provenance='provenance')
        return data

    def save_handoff(self, data):
        path = self.root / 'output/handoff.json'
        path.write_text(json.dumps(data))
        return str(path)

    def test_process_identity_and_recycled_pid(self):
        identity = identify(os.getpid())
        self.assertEqual(probe(identity), 'alive')
        self.assertEqual(probe(identity | {'started': 'wrong'}), 'dead')
        self.assertEqual(probe(identity | {'host': 'different-host'}), 'unknown')
        child = subprocess.Popen([sys.executable, '-c', 'pass'])
        child.wait(timeout=10)
        with self.assertRaises(ProcessLookupError):
            identify(child.pid)

    def test_registry_only_under_output_and_init_no_overwrite(self):
        with self.assertRaises(Rejected):
            Registry(self.root / 'state.sqlite', self.root)
        with self.assertRaises(Rejected):
            self.reg.init()
        self.assertEqual(self.reg.status()['lanes'], {})

    def test_claim_is_atomic_between_connections(self):
        def claim(_):
            reg = Registry(self.db, self.root)
            try:
                reg.register(self.data())
                return True
            except Rejected:
                return False
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            self.assertEqual(sorted(pool.map(claim, range(2))), [False, True])

    def test_stale_revision_generation_and_heartbeat_not_progress(self):
        self.running()
        self.now += 20
        self.reg.heartbeat('one', 1)
        lane = self.reg.status()['lanes']['one']
        self.assertEqual(lane['progress_at'], 1000)
        self.assertEqual(lane['revision'], 2)
        with self.assertRaises(Rejected):
            self.reg.checkpoint('one', 1, 1, {'next_action': 'stale'})
        with self.assertRaises(Rejected):
            self.reg.heartbeat('one', 99)

    def test_wip_and_owned_files(self):
        self.register()
        with self.assertRaises(Rejected):
            self.register('two', worker='one')
        data = self.data('two')
        data['owned_files'] = self.data()['owned_files']
        with self.assertRaises(Rejected):
            self.reg.register(data)

    def test_live_expired_lease_not_reclaimed_and_capacity(self):
        self.register()
        self.register('two')
        first = self.reg.acquire('one', 1, 'build:output/a', os.getpid(), ttl=1)
        self.now += 10
        self.assertFalse(self.reg.acquire('two', 1, 'build:output/b', os.getpid())['acquired'])
        with self.assertRaises(Rejected):
            self.reg.release('one', 1, 'build:output/a', first['lease']['token'])
        self.health = 'unknown'
        self.assertFalse(self.reg.acquire('two', 1, 'build:output/b', os.getpid())['acquired'])
        self.health = 'dead'
        self.assertTrue(self.reg.acquire('two', 1, 'build:output/b', os.getpid())['acquired'])

    def test_confirmed_dead_lease_reclaimed_before_expiry(self):
        self.register();self.register('two')
        first=self.reg.acquire('one',1,'build:output/a',os.getpid(),ttl=3600)
        self.health='unknown'
        self.assertFalse(self.reg.acquire('two',1,'build:output/a',os.getpid())['acquired'])
        self.health='dead'
        second=self.reg.acquire('two',1,'build:output/a',os.getpid())
        self.assertTrue(second['acquired'])
        self.assertNotEqual(first['lease']['token'],second['lease']['token'])
        self.assertLess(self.now,first['lease']['expires_at'])
        self.assertTrue(any(e['kind']=='lease_reaped' for e in self.reg.snapshot()['events']))

    def test_resource_alias_token_and_fifo(self):
        self.register()
        self.register('two')
        self.register('three')
        a = self.reg.acquire('one', 1, 'build:output/a', os.getpid())
        b = self.reg.acquire('two', 1, 'build:output/a/../b', os.getpid())
        self.now += 1
        c = self.reg.acquire('three', 1, 'build:output/c', os.getpid())
        self.assertFalse(b['acquired'])
        self.assertFalse(c['acquired'])
        with self.assertRaises(Rejected):
            self.reg.renew('one', 1, 'build:output/a', 'wrong')
        self.health = 'dead'
        self.reg.release('one', 1, 'build:output/a', a['lease']['token'])
        self.assertFalse(self.reg.acquire('three', 1, 'build:output/c', os.getpid())['acquired'])
        self.assertTrue(self.reg.acquire('two', 1, 'build:output/b', os.getpid())['acquired'])

    def test_nonpolling_head_reserves_one_slot_not_entire_pool(self):
        for key in ('one','two','three'):self.running(key)
        self.reg.acquire('one',1,'build:output/occupied',os.getpid())
        head=self.reg.acquire('two',1,'build:output/head',os.getpid())
        self.assertFalse(head['acquired'])
        self.now += 1
        self.assertFalse(self.reg.acquire('three',1,'build:output/later',os.getpid())['acquired'])
        with self.reg.transaction() as s:s['settings']['max_heavy_builds']=3
        self.assertTrue(self.reg.acquire('three',1,'build:output/later',os.getpid())['acquired'])
        self.assertIn(head['request']['id'],self.reg.snapshot()['queue'])
        self.assertTrue(self.reg.acquire('two',1,'build:output/head',os.getpid())['acquired'])
        self.assertFalse(self.reg.acquire('one',1,'build:output/overflow',os.getpid())['acquired'])

    def test_spare_pool_capacity_does_not_bypass_directory_fifo(self):
        for key in ('one','two','three'):self.running(key)
        self.reg.acquire('one',1,'build:output/occupied',os.getpid())
        self.reg.acquire('two',1,'build:output/shared',os.getpid())
        self.now += 1
        with self.reg.transaction() as s:s['settings']['max_heavy_builds']=4
        self.assertFalse(self.reg.acquire('three',1,'build:output/shared',os.getpid())['acquired'])
        self.assertTrue(self.reg.acquire('two',1,'build:output/shared',os.getpid())['acquired'])
        self.assertFalse(self.reg.acquire('three',1,'build:output/shared',os.getpid())['acquired'])

    def test_simultaneous_lease_acquisition_is_exclusive(self):
        self.register()
        self.register('two')
        def acquire(key):
            reg = Registry(self.db, self.root)
            return reg.acquire(key, 1, 'shared-runtime', os.getpid())['acquired']
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            self.assertEqual(sorted(pool.map(acquire, ['one', 'two'])), [False, True])

    def test_watchdog_missed_heartbeat_never_recovers_live_or_unknown(self):
        self.running()
        self.now += 15
        actions = self.reg.watchdog()
        self.assertEqual([a['kind'] for a in actions], ['checkpoint'])
        self.assertEqual(actions, self.reg.watchdog())
        self.health = 'unknown'
        self.assertEqual(self.reg.watchdog()[0]['kind'], 'checkpoint')

    def test_waiting_worker_not_restarted_when_dead(self):
        self.running()
        self.reg.checkpoint('one', 1, 2, {'state': 'blocked', 'dependencies': ['#128']})
        self.health = 'dead'
        self.now += 31
        self.assertEqual(self.reg.watchdog()[0]['kind'], 'check_dependency')

    def test_watchdog_recovery_race_and_generation_fencing(self):
        self.running()
        self.health = 'dead'
        action = self.reg.watchdog()[0]
        self.assertEqual(action['kind'], 'recover')
        self.assertEqual(self.reg.watchdog()[0]['id'], action['id'])
        self.reg.claim_action(action['id'], 'dispatcher-a')
        with self.assertRaises(Rejected):
            self.reg.claim_action(action['id'], 'dispatcher-b')
        with self.assertRaises(Rejected):
            self.reg.claim_action(action['id'], 'dispatcher-a')
        replacement = {'task_id': 'replacement-task', 'pid': os.getpid()}
        result = self.reg.complete_action(action['id'], 'dispatcher-a', 'output/checkpoint', replacement)
        self.assertEqual(result, self.reg.complete_action(action['id'], 'dispatcher-a', 'output/checkpoint', replacement))
        self.assertEqual(self.reg.status()['lanes']['one']['generation'], 2)
        with self.assertRaises(Rejected):
            self.reg.heartbeat('one', 1)

    def test_phantom_shared_review_redispatched_when_producer_dead(self):
        lane = self.running()
        self.now += 40
        data = self.handoff(lane)
        data['shared_reviews'] = [{'file': 'workflow/never_touched.py', 'reason': 'Shared helper',
                                    'issue_url': 'https://example/issues/1', 'status': 'requested', 'evidence': ['log']}]
        self.reg.submit_handoff('one', 1, 2, self.save_handoff(data))
        self.assertEqual(self.reg.status()['lanes']['one']['state'], 'handoff_ready')
        self.health = 'dead'
        actions = self.reg.watchdog()
        self.assertEqual([a['kind'] for a in actions], ['recover'])
        self.assertIn('never_touched.py', actions[0]['reason'])
        self.reg.claim_action(actions[0]['id'], 'dispatcher-a')
        replacement = {'task_id': 'replacement-task', 'pid': os.getpid()}
        self.reg.complete_action(actions[0]['id'], 'dispatcher-a', 'output/checkpoint', replacement)
        lane = self.reg.status()['lanes']['one']
        self.assertEqual(lane['state'], 'ready')
        self.assertEqual(lane['generation'], 2)
        self.assertIsNone(lane['handoff'])

    def test_legitimate_pending_review_not_redispatched(self):
        lane = self.running()
        self.now += 40
        data = self.handoff(lane)
        data['changed_files'] = list(lane['owned_files']) + ['workflow/actually_touched.py']
        data['shared_reviews'] = [{'file': 'workflow/actually_touched.py', 'reason': 'Shared helper',
                                    'issue_url': 'https://example/issues/1', 'status': 'requested', 'evidence': ['log']}]
        self.reg.submit_handoff('one', 1, 2, self.save_handoff(data))
        self.health = 'dead'
        self.assertEqual(self.reg.watchdog(), [])

    def test_phantom_shared_review_not_redispatched_while_producer_live(self):
        lane = self.running()
        self.now += 40
        data = self.handoff(lane)
        data['shared_reviews'] = [{'file': 'workflow/never_touched.py', 'reason': 'Shared helper',
                                    'issue_url': 'https://example/issues/1', 'status': 'requested', 'evidence': ['log']}]
        self.reg.submit_handoff('one', 1, 2, self.save_handoff(data))
        self.health = 'alive'
        self.assertNotIn('recover', [a['kind'] for a in self.reg.watchdog()])

    def test_phantom_shared_review_not_redispatched_with_launch_in_flight(self):
        lane = self.running()
        self.now += 40
        data = self.handoff(lane)
        data['shared_reviews'] = [{'file': 'workflow/never_touched.py', 'reason': 'Shared helper',
                                    'issue_url': 'https://example/issues/1', 'status': 'requested', 'evidence': ['log']}]
        self.reg.submit_handoff('one', 1, 2, self.save_handoff(data))
        self.health = 'dead'
        with self.reg.transaction() as state:
            state.setdefault('control', {}).setdefault('launches', {})['x'] = dict(lane='one', status='running')
        self.assertEqual(self.reg.watchdog(), [])

    def test_live_resource_blocks_recovery_after_worker_death(self):
        self.running()
        self.reg.acquire('one', 1, 'shared-runtime', os.getpid())
        self.reg.probe = lambda identity: 'alive' if identity.get('resource_owner') else 'dead'
        with self.reg.transaction() as state:
            state['leases']['shared-runtime']['process']['resource_owner'] = True
        self.now += 31
        self.assertEqual(self.reg.watchdog()[0]['kind'], 'checkpoint')

    def test_failures_dedupe_and_escalate(self):
        self.running()
        for number in range(3):
            self.reg.failure('one', 1, str(number), 'same-crash', self.evidence)
        self.reg.failure('one', 1, '2', 'same-crash', self.evidence)
        self.health = 'dead'
        self.assertEqual(self.reg.watchdog()[0]['kind'], 'escalate')
        self.assertEqual(self.reg.status()['metrics']['failure_attempts'], 3)

    def test_handoff_tampering_and_methods(self):
        lane = self.running()
        data = self.handoff(lane)
        self.assertTrue(validate_handoff(self.root, data, lane)['reviewable'])
        self.assertFalse(validate_handoff(self.root, data, lane)['gameplay_accepted'])
        broken = copy.deepcopy(data)
        del broken['gates']['cleanup_reentry']
        with self.assertRaises(Rejected):
            validate_handoff(self.root, broken)
        self.log.write_text('changed')
        with self.assertRaises(Rejected):
            validate_handoff(self.root, data)

    def test_runtime_provenance_checked_not_built_and_wrong_exe(self):
        self.running()
        data = self.handoff(runtime=True)
        self.assertTrue(validate_handoff(self.root, data)['reviewable'])
        path = Path(data['evidence']['provenance']['path'])
        prov = json.loads(path.read_text())
        prov['status'] = 'checked_not_built'
        path.write_text(json.dumps(prov))
        data['evidence']['provenance']['sha256'] = digest(path)
        with self.assertRaisesRegex(Rejected, 'not built'):
            validate_handoff(self.root, data)
        prov['status'] = 'built'
        prov['artifacts'] = {}
        path.write_text(json.dumps(prov))
        data['evidence']['provenance']['sha256'] = digest(path)
        with self.assertRaisesRegex(Rejected, 'artifact hash'):
            validate_handoff(self.root, data)

    def test_handoff_review_and_integration_metrics(self):
        from tests.landing_git import source
        self.running()
        lane = source(self.reg, 'one', {'workflow/one.py': 'X = 1\n'})
        self.now += 40
        path = self.save_handoff(self.handoff(lane))
        lane = self.reg.submit_handoff('one', 1, 2, path)
        # A worker may prepare its next slice while one handoff waits.
        self.register('two', worker='one')
        self.now += 3601
        status = self.reg.status()
        self.assertTrue(status['dispatch']['pause_new_slices'])
        self.assertEqual(status['metrics']['handoff_queue'][0]['age_seconds'], 3601)
        self.reg.checkpoint('one', 1, 3, {'state': 'integrating'})
        self.reg.integrate('one', 1, 4, {'root_commit': lane['root']['head'], 'validation_path': str(self.log),
                                      'validation_sha256': digest(self.log)})
        self.assertEqual(self.reg.status()['metrics']['integrated_lead_seconds'], [3641])

    def test_no_done_without_handoff_and_changed_handoff_blocks_integration(self):
        lane = self.running()
        with self.assertRaises(Rejected):
            self.reg.checkpoint('one', 1, 2, {'state': 'done'})
        path = self.save_handoff(self.handoff(lane))
        self.reg.submit_handoff('one', 1, 2, path)
        Path(path).write_text('{}')
        with self.assertRaises(Rejected):
            self.reg.checkpoint('one', 1, 3, {'state': 'integrating'})

    def test_native_receipt_rejects_explicit_non_export_and_rolls_back(self):
        from unittest.mock import patch
        self.running()
        with self.reg.transaction() as state:
            state['lanes']['one'].update(state='integrating', native={'head':'a'*40})
        evidence=self.root/'output/no-export.json'
        evidence.write_text(json.dumps({'action':'none-performed'}))
        record=dict(root_commit='b'*40,native_commit='a'*40,native_dirty='',
                    validation_path=str(self.log),validation_sha256=digest(self.log),
                    export_evidence=str(evidence),export_sha256=digest(evidence))
        with patch.object(self.reg,'check_handoff',return_value={'pending_reviews':[]}),                 patch('workflow.landing.prove',return_value={}):  # Landing proof has its own tests.
            with self.assertRaisesRegex(Rejected,'explicitly records no export'):
                self.reg.integrate('one',1,2,record)
        self.assertEqual(self.reg.snapshot()['lanes']['one']['state'],'integrating')

    def test_cli_and_persistent_reopen(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/pikmin2_workflow.py'
        command = [sys.executable, str(script), '--root', str(self.root), '--db', str(self.db), 'status']
        result = subprocess.run(command, text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['settings']['max_heavy_builds'], 1)
        command[-1] = 'init'
        self.assertEqual(subprocess.run(command, capture_output=True, timeout=15).returncode, 2)

    def test_recovery_budget_survives_worker_replacement(self):
        self.running()
        self.health = 'dead'
        for attempt in range(3):
            action = self.reg.watchdog()[0]
            self.assertEqual(action['kind'], 'recover')
            self.reg.claim_action(action['id'], 'dispatcher')
            self.reg.complete_action(action['id'], 'dispatcher', 'checkpoint',
                                     {'task_id': str(attempt), 'pid': os.getpid()})
        self.assertEqual(self.reg.watchdog()[0]['kind'], 'escalate')

    def test_stale_recovery_not_claimed_after_progress_or_new_failure(self):
        self.running()
        self.health = 'dead'
        action = self.reg.watchdog()[0]
        self.now += 1
        self.reg.checkpoint('one', 1, 2, {}, self.evidence | {'summary': 'Fixed issue'})
        with self.assertRaises(Rejected):
            self.reg.claim_action(action['id'], 'dispatcher')
        action = self.reg.watchdog()[0]
        for i in range(3):
            self.reg.failure('one', 1, str(i), 'crash', self.evidence)
        with self.assertRaises(Rejected):
            self.reg.claim_action(action['id'], 'dispatcher')

    def test_overlapping_watchdogs_and_claimants(self):
        self.running()
        self.health = 'dead'
        def tick(_):
            reg = Registry(self.db, self.root, clock=lambda: self.now, process_probe=lambda _: 'dead')
            return reg.watchdog()[0]['id']
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            actions = list(pool.map(tick, range(2)))
        self.assertEqual(actions[0], actions[1])
        def claim(consumer):
            try:
                self.reg.claim_action(actions[0], consumer)
                return True
            except Rejected:
                return False
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            self.assertEqual(sorted(pool.map(claim, ['a', 'b'])), [False, True])

    def test_expired_dead_queue_does_not_block_new_waiter(self):
        self.register()
        self.register('two')
        self.register('three')
        a = self.reg.acquire('one', 1, 'build:output/a', os.getpid())
        self.reg.acquire('two', 1, 'build:output/b', os.getpid())
        self.now += 31
        self.health = 'dead'
        self.reg.release('one', 1, 'build:output/a', a['lease']['token'])
        self.assertTrue(self.reg.acquire('three', 1, 'build:output/c', os.getpid())['acquired'])

    def test_cancel_queue_and_waiting_state(self):
        self.running()
        self.register('two')
        self.reg.acquire('two', 1, 'shared-runtime', os.getpid())
        request = self.reg.acquire('one', 1, 'shared-runtime', os.getpid())['request']
        self.reg.checkpoint('one', 1, 2, {'state': 'waiting_resource'})
        self.now += 20
        self.reg.cancel_request('one', 1, request['id'])
        self.reg.checkpoint('one', 1, 3, {'state': 'running'})
        self.assertEqual(self.reg.status()['metrics']['completed_wait_seconds'][-1], 20)

    def test_pending_review_refresh_preserves_age_then_integrates(self):
        from tests.landing_git import source
        self.running()
        lane = source(self.reg, 'one', {'workflow/one.py': 'X = 1\n'})
        data = self.handoff(lane)
        data['changed_files'] += ['native/shared.cpp']
        data['shared_reviews'] = [dict(file='native/shared.cpp', reason='Receiver semantics',
            issue_url='https://github.com/4laric/pikmin-randomizer/issues/186', status='requested', evidence=['log'])]
        self.reg.submit_handoff('one', 1, 2, self.save_handoff(data))
        self.reg.checkpoint('one', 1, 3, {'state': 'integrating'})
        record = dict(root_commit=lane['root']['head'], validation_path=str(self.log), validation_sha256=digest(self.log))
        with self.assertRaisesRegex(Rejected, 'shared reviews'):
            self.reg.integrate('one', 1, 4, record)
        self.now += 99
        data['shared_reviews'][0]['status'] = 'approved'
        with self.assertRaisesRegex(Rejected, 'no matching authenticated decision'):  # A producer cannot approve itself.
            self.reg.submit_handoff('one', 1, 4, self.save_handoff(data))
        from tests.approval_auth import reviewer
        from workflow import review_decisions
        self.register('two'); reviewer(self, self.reg, 'two', owns=['one'])
        handoff = self.reg.status()['lanes']['one']['handoff']
        self.save_handoff(dict(data, shared_reviews=[dict(data['shared_reviews'][0], status='requested')]))
        review_decisions.record(self.reg, 'two', 1, 'one', 1, handoff['sha256'],
                                [dict(file='native/shared.cpp', status='approved', evidence=self.evidence)])
        self.reg.submit_handoff('one', 1, 4, self.save_handoff(data))  # Stamped from the ledger row.
        self.assertEqual(self.reg.status()['metrics']['handoff_queue'][0]['age_seconds'], 99)
        self.reg.checkpoint('one', 1, 5, {'state': 'integrating'})
        self.assertEqual(self.reg.integrate('one', 1, 6, record)['state'], 'done')

    def test_false_gate_pass_and_changed_source_rejected(self):
        lane = self.running()
        data = self.handoff(lane)
        data['gates']['identity_spawn'] = dict(status='PASS', method='source', detail='Claim', evidence=['log'])
        with self.assertRaises(Rejected):
            validate_handoff(self.root, data, lane)
        data = self.handoff(lane)
        data['root'] = dict(base='b'*40, head='b'*40, commits=[], dirty='', worktree='.')
        with self.assertRaises(Rejected):
            validate_handoff(self.root, data, lane)

    def test_failed_test_cannot_be_ready_handoff(self):
        lane = self.running()
        data = self.handoff(lane)
        data['tests'][0]['exit_code'] = 1
        self.assertTrue(validate_handoff(self.root, data)['reviewable'])
        self.assertFalse(validate_handoff(self.root, data)['slice_passed'])
        with self.assertRaises(Rejected):
            self.reg.submit_handoff('one', 1, 2, self.save_handoff(data))

    def test_evidence_outside_workspace_rejected(self):
        lane = self.running()
        data = self.handoff(lane)
        data['evidence'] = {'log': {'path': '../outside.log', 'sha256': 'fake'}}
        with self.assertRaisesRegex(Rejected, 'escapes workspace'):
            validate_handoff(self.root, data)

    def test_second_ready_handoff_rejected(self):
        lane = self.running()
        self.reg.submit_handoff('one', 1, 2, self.save_handoff(self.handoff(lane)))
        self.register('two', worker='one')
        lane = self.reg.checkpoint('two', 1, 1, {'state': 'running'})
        with self.assertRaisesRegex(Rejected, 'ready/integrating'):
            self.reg.submit_handoff('two', 1, 2, self.save_handoff(self.handoff(lane)))

    def test_dispatch_prefers_dependencies_then_gates(self):
        self.register()
        data = self.data('two')
        data['closes_gates'] = ['attacks_receivers']
        self.reg.register(data)
        self.register('three')
        self.reg.checkpoint('three', 1, 1, {'state': 'blocked', 'dependencies': ['one']})
        self.assertEqual(self.reg.status()['dispatch']['suggested_lanes'], ['one', 'two'])

    def test_unchanged_progress_evidence_cannot_reset_failure_budget(self):
        self.running()
        progress = self.evidence | {'summary': 'First observed progress'}
        self.reg.checkpoint('one', 1, 2, {}, progress)
        self.reg.failure('one', 1, 'attempt', 'crash', self.evidence)
        with self.assertRaisesRegex(Rejected, 'Unchanged evidence'):
            self.reg.checkpoint('one', 1, 3, {}, progress | {'summary': 'Still working'})
        self.assertEqual(self.reg.status()['lanes']['one']['failure_streak'], 1)


if __name__ == '__main__':
    unittest.main()
