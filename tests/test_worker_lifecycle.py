"""Crash, retry-budget, session-scope and supervision paths of the controller's worker lifecycle."""
import json
import socket
import time
import unittest
from unittest.mock import patch

from tests import test_pikmin2_controller as fixtures
from workflow.control import fingerprint
from workflow.handoff import Rejected
from workflow.runner import write

RUNNER = dict(host=socket.gethostname(), pid=4242, started='133000000000000000')  # FILETIME, 2022-06.


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ControllerTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.reg, self.c = self.f.reg, self.f.controller
        self.c.process_table = lambda: self.fail('process table not expected')
        self.c.boot_time = lambda: 0  # By default nothing started before the current boot.
        self.c.boot_id = lambda: 35

    def bound(self, **launch):
        """A dispatched launch whose runner (RUNNER) is the lane's recorded process."""
        item = self.f.plan()
        with self.reg.transaction() as state:
            state['control']['launches'][item['id']].update(launch)
        self.c.dispatch(item)
        with self.reg.transaction() as state:
            state['control']['launches'][item['id']]['process'] = RUNNER
            state['lanes']['consumer']['process'] = RUNNER
        return self.reg.control_status()['launches'][item['id']], self.c.launch_directory(item['id'])

    def launches(self):
        return list(self.reg.control_status()['launches'].values())

    def kinds(self):
        return [n['kind'] for n in self.reg.control_status()['notices'].values()]

    def dead(self):
        self.reg.probe = lambda p: 'dead'

    # Unreadable records after a crash.
    @unittest.skipUnless(__import__('os').name == 'nt', 'FILETIME boot proof is Windows-only')
    def test_nul_child_after_reboot_takes_dead_runner_recovery_with_evidence(self):
        item, directory = self.bound()
        (directory / 'child.json').write_bytes(b'\0' * 84)
        write(directory / 'boot.json', {'boot_id': 34})  # The runner's boot, not the current one.
        self.dead(); self.c.boot_time = lambda: time.time()
        self.c.complete_runs()
        old, follow = self.launches()
        self.assertEqual(old['status'], 'exited')
        self.assertTrue(follow['reason'].startswith('dead-runner:'))
        self.assertEqual((follow['dead_runner_retries'], follow['automatic_retries']), (1, 1))
        crash = json.loads((directory / 'crash.json').read_text())
        self.assertEqual(crash['reason'], 'completion_record_unreadable')
        self.assertEqual(crash['child_proof']['kind'], 'runner_started_before_boot')
        self.assertEqual(list(crash['damaged']), ['child.json'])
        self.assertEqual((directory / 'child.json').read_bytes(), b'\0' * 84)
        self.assertIn('crashed_launch_recovered', self.kinds())

    def test_clock_alone_never_proves_a_reboot(self):
        # A runner whose creation time predates the computed boot (clock corrected after it started)
        # but whose recorded boot counter is current, or missing, needs the process-table proof.
        for marker in ({'boot_id': 35}, None):
            with self.subTest(marker=marker):
                self.setUp()
                item, directory = self.bound()
                (directory / 'child.json').write_bytes(b'\0' * 84)
                if marker: write(directory / 'boot.json', marker)
                self.dead(); self.c.boot_time = lambda: time.time()
                self.c.process_table = lambda: [dict(ProcessId=5000, ParentProcessId=4242, Name='opencode.exe',
                                                     Started='133000000000000001')]
                self.c.complete_runs()
                self.assertEqual([l['status'] for l in self.launches()], ['running'])
                self.assertFalse((directory / 'crash.json').exists())

    def test_unreadable_child_stays_fenced_while_a_child_may_survive(self):
        item, directory = self.bound()
        (directory / 'child.json').write_bytes(b'\0' * 84)
        self.dead()
        survivor = dict(ProcessId=5000, ParentProcessId=4242, Name='opencode.exe', Started='133000000000000001')
        for rows in ([survivor], [dict(survivor, Started=None)], OSError('no inventory')):
            with self.subTest(rows=rows):
                def table(rows=rows):
                    if isinstance(rows, Exception): raise rows
                    return rows
                self.c.process_table = table
                self.c.complete_runs()
                launch = self.launches()[0]
                self.assertEqual(launch['status'], 'running')
                self.assertGreater(launch['completion_retry_after'], self.f.now)  # No process scan every tick.
                self.c.process_table = lambda: self.fail('backed off')
                self.c.complete_runs()
                self.f.now = launch['completion_retry_after'] + 1
        notice = [n for n in self.reg.control_status()['notices'].values() if n['kind'] == 'completion_record_unreadable']
        self.assertEqual(notice[0]['detail']['child'], 'unproven')

    def test_process_table_without_surviving_child_is_a_proof(self):
        item, directory = self.bound()
        (directory / 'child.json').write_bytes(b'\0' * 84)
        self.dead()
        older = dict(ProcessId=5000, ParentProcessId=4242, Name='x.exe', Started='132000000000000000')  # Recycled PID's.
        self.c.process_table = lambda: [older, dict(ProcessId=1, ParentProcessId=0, Name='System', Started='1')]
        self.c.complete_runs()
        self.assertEqual(len(self.launches()), 2)
        self.assertEqual(json.loads((directory / 'crash.json').read_text())['child_proof']['kind'], 'no_surviving_child')

    def test_live_runner_with_unreadable_child_is_not_a_crash(self):
        item, directory = self.bound()
        (directory / 'child.json').write_bytes(b'\0' * 84)
        self.reg.probe = lambda p: 'alive' if p == RUNNER else 'dead'
        self.c.complete_runs()
        self.assertEqual([l['status'] for l in self.launches()], ['running'])
        self.assertFalse((directory / 'crash.json').exists())

    # complete_runs plans before exiting; refusals reconcile instead of stranding.
    def test_refused_provider_retry_reconciles_the_lane(self):
        item, directory = self.bound()
        write(directory / 'result.json', {'kind': 'exit', 'exit_code': 1})
        with self.reg.transaction() as state:
            state['lanes']['consumer']['state'] = 'waiting_resource'
            state['control']['terminal_recoveries'] = {'j': dict(launch=item['id'], status='child_stop_requested',
                                                                 evidence={'failure': 'provider_failure'})}
        self.dead(); self.c.complete_runs()
        self.assertEqual([l['status'] for l in self.launches()], ['exited'])
        self.assertEqual(self.reg.status()['lanes']['consumer']['state'], 'reconciling')
        self.assertIn('recovery_retry_refused', self.kinds())

    def test_refused_rate_limit_retry_does_not_raise_every_sweep(self):
        item, directory = self.bound()
        write(directory / 'result.json', {'kind': 'rate_limit', 'exit_code': 1})
        with self.reg.transaction() as state:
            state['lanes']['consumer']['state'] = 'waiting_resource'
        self.dead(); self.c.complete_runs(); self.c.complete_runs()
        self.assertEqual([l['status'] for l in self.launches()], ['exited'])
        self.assertEqual(self.reg.status()['lanes']['consumer']['state'], 'reconciling')
        self.assertIn('free/muse', self.reg.control_status()['model_limits'])

    def test_refused_reconciliation_keeps_launch_open_backs_off_and_still_heartbeats(self):
        item, directory = self.bound()
        write(directory / 'result.json', {'kind': 'exit', 'exit_code': 0})
        self.dead()
        with patch.object(self.reg, 'finish', side_effect=Rejected('check_wip refused')), \
                patch.object(self.c, 'heartbeat_runs') as heartbeat:
            self.c.complete_runs()
            heartbeat.assert_called_once()
            launch = self.launches()[0]
            self.assertEqual(launch['status'], 'exiting')
            self.assertEqual(launch['completion_attempts'], 1)
            self.assertGreater(launch['completion_retry_after'], self.f.now)
            self.c.complete_runs()  # Backed off: no second attempt yet.
            self.assertEqual(self.launches()[0]['completion_attempts'], 1)
        self.assertIn('completion_deferred', self.kinds())
        self.f.now = launch['completion_retry_after'] + 1
        self.c.complete_runs()
        self.assertEqual(self.launches()[0]['status'], 'exited')
        self.assertEqual(self.reg.status()['lanes']['consumer']['state'], 'reconciling')

    def test_dead_runner_retry_marks_exit_in_the_planning_transaction(self):
        item, directory = self.bound()
        write(directory / 'child.json', {'pid': -7})
        self.dead()
        with patch.object(self.reg, 'plan_launch', side_effect=Rejected('Old worker or protected child still live/unknown')):
            self.c.complete_runs()
        # The refused plan left nothing exited; reconciliation carried the lane.
        self.assertEqual([l['status'] for l in self.launches()], ['exited'])
        self.assertEqual(self.reg.status()['lanes']['consumer']['state'], 'reconciling')

    def test_alternating_failures_share_every_counter_and_the_chain_cap(self):
        self.c.config['automatic_retry_limit'] = 3
        item, directory = self.bound()
        for step in range(4):
            if step % 2 == 0: write(directory / 'result.json', {'kind': 'rate_limit', 'exit_code': 1})
            else: write(directory / 'child.json', {'pid': -7})
            self.dead(); self.c.complete_runs()
            follow = self.launches()[-1]
            if follow['id'] == item['id']: break
            self.assertEqual(follow['automatic_retries'], step + 1)
            self.f.now += 1000
            self.reg.probe = lambda p: 'alive' if p == self.f.identity else 'dead'
            with self.reg.transaction() as state:
                state['lanes']['consumer']['process'] = {'pid': -999}
            self.c.dispatch(follow)
            with self.reg.transaction() as state:
                state['control']['launches'][follow['id']]['process'] = RUNNER
                state['lanes']['consumer']['process'] = RUNNER
            item, directory = self.reg.control_status()['launches'][follow['id']], self.c.launch_directory(follow['id'])
        chain = self.launches()
        self.assertEqual(len(chain), 4)
        self.assertEqual((chain[-1]['rate_limit_retries'], chain[-1]['dead_runner_retries']), (2, 1))
        self.assertIn('automatic_retry_exhausted', self.kinds())
        self.assertEqual(self.reg.status()['lanes']['consumer']['state'], 'reconciling')

    def test_recovery_continuation_is_never_parked(self):
        item, directory = self.bound()
        write(directory / 'child.json', {'pid': -7})
        with self.reg.transaction() as state:
            state['lanes']['consumer'].update(stall_streak=5, wake_after=self.f.now + 99999, wake_inputs=['x'])
        self.dead(); self.c.complete_runs()
        self.assertTrue(self.launches()[-1]['reason'].startswith('dead-runner:'))

    def test_only_a_requested_stop_journal_classifies_the_exit(self):
        item, directory = self.bound()
        write(directory / 'result.json', {'kind': 'exit', 'exit_code': 1})
        with self.reg.transaction() as state:
            state['control']['terminal_recoveries'] = {'j': dict(launch=item['id'], status='stopping',
                                                                 evidence={'failure': 'first_response_timeout'})}
        self.dead(); self.c.complete_runs()
        self.assertEqual(len(self.launches()), 1)
        self.assertEqual(self.reg.status()['lanes']['consumer']['state'], 'reconciling')

    def test_mid_tool_rate_limit_is_a_provider_failure_not_a_cooldown(self):
        item, directory = self.bound()
        write(directory / 'result.json', {'kind': 'exit', 'exit_code': 1, 'rate_limit': True,
                                           'rate_limit_phase': 'mid_tool', 'tools_started': True, 'turn_end': None})
        self.dead(); self.c.complete_runs()
        follow = self.launches()[-1]
        self.assertTrue(follow['reason'].startswith('provider-error:'))
        self.assertNotIn('free/muse', self.reg.control_status().get('model_limits', {}))

    def test_turn_end_stop_is_a_normal_exit(self):
        # The runner's own stop exits 1 and the session's log carries an old provider error: neither
        # makes it a provider failure. Without stopped_after_turn the same exit is one.
        for stopped in (True, False):
            with self.subTest(stopped=stopped):
                self.setUp()
                item, directory = self.bound()
                result = {'kind': 'exit', 'exit_code': 1, 'turn_end': {'source': 'stderr_exiting_loop'}}
                if stopped: result.update(stopped_after_turn=True, runner_stop={'reason': 'turn_end'})
                write(directory / 'result.json', result)
                (directory / 'events.jsonl').write_text(json.dumps(dict(type='error', sessionID=item['session'],
                    error=dict(name='APIError', data=dict(message='Rate limit exceeded', statusCode=429)))) + '\n')
                self.dead(); self.c.complete_runs()
                follow = [l for l in self.launches() if l['id'] != item['id']]
                if stopped:
                    self.assertEqual(follow, [])
                    self.assertEqual(self.reg.status()['lanes']['consumer']['state'], 'reconciling')
                else:
                    self.assertTrue(follow[0]['reason'].startswith('provider-error:'))
                self.assertEqual(self.reg.control_status()['launches'][item['id']]['status'], 'exited')
                self.assertNotIn('free/muse', self.reg.control_status().get('model_limits', {}))

    # Session scope.
    def test_fresh_session_is_adopted_then_resumed_within_the_lane(self):
        item, directory = self.bound(fresh_session=True)
        start = json.loads((directory / 'start.json').read_text())
        self.assertEqual((start['session'], start['fresh_session']), (None, True))
        self.assertTrue(start['prompt'].startswith('Start lane consumer in this fresh session'))
        ready = json.loads((self.f.out / 'session-ready.json').read_text())
        self.assertTrue(ready['fresh_session'])
        write(directory / 'session.json', dict(session='ses_otherLaunch1', action_id='someone-else'))
        self.reg.probe = lambda p: 'alive' if p == RUNNER else 'dead'
        self.c.complete_runs()
        self.assertEqual(self.reg.status()['lanes']['consumer']['task_id'], 'opencode:session-consumer')
        write(directory / 'session.json', dict(session='ses_newLane01', action_id=item['id']))
        self.c.complete_runs()
        lane = self.reg.snapshot()['lanes']['consumer']
        self.assertEqual(lane['task_id'], 'opencode:ses_newLane01')
        self.assertEqual(lane['session_history'][0]['session'], 'session-consumer')
        launch = self.launches()[0]
        self.assertEqual((launch['session'], launch['inherited_session']), ('ses_newLane01', 'session-consumer'))
        write(directory / 'child.json', {'pid': -7})
        self.dead(); self.c.complete_runs()
        follow = self.launches()[-1]
        self.assertEqual(follow['session'], 'ses_newLane01')
        self.assertNotIn('fresh_session', follow)

    def test_unadopted_fresh_session_retry_stays_fresh(self):
        item, directory = self.bound(fresh_session=True)
        write(directory / 'child.json', {'pid': -7})
        self.dead(); self.c.complete_runs()
        follow = self.launches()[-1]
        self.assertEqual(follow['session'], 'session-consumer')
        self.assertTrue(follow['fresh_session'])

    def test_unadopted_fresh_lane_starts_fresh_from_every_planner(self):
        with self.reg.transaction() as state:
            state['lanes']['consumer'].update(previous_lane='old-lane', session_pending=True)
        item, directory = self.bound(fresh_session=True)
        write(directory / 'result.json', {'kind': 'exit', 'exit_code': 0})  # Died before naming its session.
        self.dead(); self.c.complete_runs()
        self.assertEqual(self.reg.status()['lanes']['consumer']['state'], 'reconciling')
        self.reg.probe = lambda p: 'alive' if p == self.f.identity else 'dead'
        wake = self.reg.plan_launch('consumer', 'outcome-recovery:x', 'Continue', ['free/muse'], obligation=True)
        self.assertTrue(wake['fresh_session'])
        self.c.dispatch(wake)
        self.assertEqual(json.loads((self.c.launch_directory(wake['id']) / 'start.json').read_text())['session'], None)

    def test_adopted_or_pre_deploy_lane_resumes_its_session(self):
        with self.reg.transaction() as state:
            state['lanes']['consumer'].update(previous_lane='old-lane')  # Provisioned before session_pending existed.
        wake = self.reg.plan_launch('consumer', 'outcome-recovery:x', 'Continue', ['free/muse'], obligation=True)
        self.assertNotIn('fresh_session', wake)
        with self.reg.transaction() as state:
            state['control']['launches'].clear()
            state['lanes']['consumer'].update(session_pending=True)
        item, directory = self.bound(fresh_session=True)
        write(directory / 'session.json', dict(session='ses_newLane01', action_id=item['id']))
        self.reg.probe = lambda p: 'alive' if p == RUNNER else 'dead'
        self.c.complete_runs()
        self.assertNotIn('session_pending', self.reg.snapshot()['lanes']['consumer'])

    def test_failed_adoption_never_skips_completion_or_heartbeats(self):
        import sqlite3
        item, directory = self.bound(fresh_session=True)
        write(directory / 'session.json', dict(session='ses_newLane01', action_id=item['id']))
        self.reg.probe = lambda p: 'alive' if p == RUNNER else 'dead'
        with patch('workflow.storage.selected', side_effect=sqlite3.OperationalError('database is locked')), \
                patch.object(self.c, 'heartbeat_runs') as heartbeat:
            self.c.complete_runs()
        self.assertEqual([i['id'] for i in heartbeat.call_args[0][0]], [item['id']])
        error = json.loads((self.c.base / 'complete-runs-error.json').read_text())
        self.assertEqual((error['stage'], error['action']), ('adopt_session', item['id']))

    # Supervision and attention.
    def test_unsupervised_stopped_lane_raises_one_notice(self):
        with self.reg.transaction() as state:
            state['lanes']['provider']['state'] = 'ready'
        self.c.observe(); self.c.observe()
        notices = [n for n in self.reg.control_status()['notices'].values() if n['kind'] == 'unsupervised_lane']
        self.assertEqual([n['lane'] for n in notices], ['provider'])

    def test_parked_available_owner_is_not_reported_not_alive(self):
        lane = dict(lane='consumer', handoff_at=self.f.now)
        state = dict(lanes={'owner': dict(lane='owner', state='review_ready', process={'pid': -5})},
                     throughput=dict(workstreams={'w': dict(owner_lane='owner', lanes=['consumer'])}))
        with patch.object(self.reg, 'integration_owner_available', return_value=True):
            attention = self.c._integration_attention(state, lane)
        self.assertNotIn('integration_owner_not_alive', attention['blockers'])
        with patch.object(self.reg, 'integration_owner_available', return_value=False):
            self.assertIn('integration_owner_not_alive', self.c._integration_attention(state, lane)['blockers'])

    # Shepherd.
    def notices(self, count, kind='review_ready'):
        with self.reg.transaction() as state:
            c = self.reg.control(state)
            for i in range(count):
                c['notices']['n%02d' % i] = dict(id='n%02d' % i, lane='consumer', kind=kind, detail={}, status='pending', at=i)

    def test_shepherd_lockout_engages_on_the_failing_packet(self):
        self.c.config['shepherd'] = dict(enabled=True, models=['free/muse'], worktree=str(self.f.root))
        self.notices(20)
        offered = ['n%02d' % i for i in range(12)]
        with self.reg.transaction() as state:
            self.reg.control(state)['shepherd_failures'] = {fingerprint(sorted(offered)): 3}
        self.c.shepherd()
        self.assertEqual(self.f.spawns, [])
        attention = json.loads((self.c.base / 'shepherd-attention.json').read_text())
        self.assertEqual(attention['events'], offered)
        status = {k: n['status'] for k, n in self.reg.control_status()['notices'].items()}
        self.assertEqual({status[k] for k in offered}, {'escalated'})
        self.assertEqual(status['n12'], 'pending')

    def test_shepherd_start_is_written_with_the_spawn_and_stalls_collapse(self):
        self.c.config['shepherd'] = dict(enabled=True, models=['free/muse'], worktree=str(self.f.root))
        self.notices(3, kind='progress_stale')
        self.c.shepherd()
        directory = self.f.spawns[0]
        self.assertTrue((directory / 'start.json').is_file())
        packet = json.loads((directory / 'packet.json').read_text())
        self.assertEqual(list(packet['notices']), ['n02'])
        status = {k: n['status'] for k, n in self.reg.control_status()['notices'].items()}
        self.assertEqual(status, {'n00': 'superseded', 'n01': 'superseded', 'n02': 'pending'})

    def test_repeated_progress_stale_is_one_notice_per_generation(self):
        entry = self.c.config['lanes']['consumer']
        for detail in ('first', 'second'):
            with self.reg.transaction() as state:
                state['lanes']['consumer'].update(progress_detail=detail, progress_at=0)
            self.f.now += 100000
            self.c.observe()
        self.assertEqual(self.kinds().count('progress_stale'), 1)


if __name__ == '__main__':
    unittest.main()
