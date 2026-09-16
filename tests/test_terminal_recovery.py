"""Adversarial idle-loop recovery; no real processes are stopped."""
import json
import os
import unittest

from tests import test_pikmin2_controller as fixtures
from workflow.provider_recovery import recover, recover_terminal, safe_descendants
from workflow.runner import write


class TerminalRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ControllerTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.f.now = 2000
        self.reg, self.controller = self.f.reg, self.f.controller
        self.runner = dict(pid=700, host='test', started='runner')
        self.child = dict(pid=701, host='test', started='child')
        self.alive = [self.runner, self.child]
        self.reg.probe = lambda p: 'alive' if p in self.alive else 'dead'
        self.controller.config['terminal_idle_recovery'] = dict(enabled=True, quiet_seconds=60)
        self.directory = self.controller.launch_directory('managed')
        self.directory.mkdir(parents=True)
        write(self.directory / 'runner.json', self.runner)
        write(self.directory / 'child.json', self.child)
        write(self.directory / 'start.json', dict(action_id='managed', session='session-consumer'))
        self.events, self.errors = self.directory / 'events.jsonl', self.directory / 'stderr.log'
        self.events.write_text('')
        os.utime(self.events, (1000, 1000))
        self.marker = 'timestamp=1970-01-01T00:16:40Z level=INFO run=abc message="exiting loop" session.id=session-consumer\n'
        self.errors.write_text(self.marker)
        self.stopped = []
        with self.reg.transaction() as state:
            state['lanes']['consumer'].update(process=self.runner, state='done', generation=2)
            self.reg.control(state)['launches']['managed'] = dict(id='managed', lane='consumer', status='running',
                bound_generation=2, generation=1, session='session-consumer', process=self.runner)

    def rows(self):
        return [dict(ProcessId=700, ParentProcessId=1, Name='python.exe'),
                dict(ProcessId=701, ParentProcessId=700, Name='opencode.exe'),
                dict(ProcessId=702, ParentProcessId=701, Name='conhost.exe')]

    def stop(self, identity):
        self.stopped.append(identity)
        self.alive.remove(identity)

    def recover(self, **kwargs):
        recover_terminal(self.controller, table=kwargs.get('table', self.rows), stop=kwargs.get('stop', self.stop))

    def test_stops_child_only_and_replay_does_not_forge_result(self):
        self.recover()
        self.recover()
        self.assertEqual(self.stopped, [self.child])
        self.assertIn(self.runner, self.alive)
        self.assertFalse((self.directory / 'result.json').exists())
        self.assertEqual(self.reg.status()['lanes']['consumer']['state'], 'done')
        self.assertEqual(self.reg.control_status()['launches']['managed']['status'], 'running')
        self.assertEqual(len(self.reg.control_status()['terminal_recoveries']), 1)

    def test_exact_cleanup_after_exit_is_ignored(self):
        self.errors.write_text(self.marker + 'timestamp=1970-01-01T00:33:19Z level=INFO run=abc message=cleanup prune=7.days\n')
        self.recover()
        self.assertEqual(self.stopped, [self.child])

    def test_new_work_unknown_cleanup_and_partial_line_block(self):
        for extra in ('timestamp=1970-01-01T00:20:00Z level=INFO message="tool running"\n',
                      'timestamp=1970-01-01T00:20:00Z level=INFO run=abc message=cleanup task=running\n',
                      'partial new output'):
            self.errors.write_text(self.marker + extra)
            self.recover()
        self.assertFalse(self.stopped)

    def test_wrong_session_and_recent_boundary_block(self):
        self.errors.write_text(self.marker.replace('session-consumer', 'session-other'))
        self.recover()
        self.errors.write_text(self.marker.replace('00:16:40', '00:32:50'))
        self.recover()
        self.assertFalse(self.stopped)

    def test_quiet_minimum_sixty_seconds(self):
        self.controller.config['terminal_idle_recovery']['quiet_seconds'] = 1
        self.errors.write_text(self.marker.replace('00:16:40', '00:32:50'))
        self.recover()
        self.assertFalse(self.stopped)

    def test_pending_tool_malformed_or_new_stdout_block(self):
        events = [dict(type='tool_use', timestamp=999000, part=dict(id='one', state=dict(status='running'))),
                  dict(type='step_finish', timestamp=1000000)]
        self.events.write_text(''.join(json.dumps(e) + '\n' for e in events))
        os.utime(self.events, (1000, 1000))
        self.recover()
        self.events.write_text('{malformed\n')
        os.utime(self.events, (1000, 1000))
        self.recover()
        self.events.write_text(json.dumps(dict(type='step_finish', timestamp=1100000)) + '\n')
        os.utime(self.events, (1100, 1100))
        self.recover()
        self.assertFalse(self.stopped)

    def test_live_or_unknown_lease_blocks(self):
        with self.reg.transaction() as state:
            state['leases']['build:private'] = dict(lane='consumer', process=self.child)
        self.recover()
        self.reg.probe = lambda p: 'unknown' if p == self.child else 'alive'
        self.recover()
        self.assertFalse(self.stopped)

    def test_unknown_identity_extra_descendant_or_wrong_parent_blocks(self):
        self.recover(table=lambda: self.rows() + [dict(ProcessId=703, ParentProcessId=701, Name='ninja.exe')])
        self.recover(table=lambda: [dict(p, ParentProcessId=1) if p['ProcessId'] == 701 else p for p in self.rows()])
        self.reg.probe = lambda p: 'unknown'
        self.recover()
        self.assertFalse(self.stopped)

    def test_generation_change_and_result_file_block(self):
        with self.reg.transaction() as state:
            state['lanes']['consumer']['generation'] = 3
        self.recover()
        with self.reg.transaction() as state:
            state['lanes']['consumer']['generation'] = 2
        write(self.directory / 'result.json', {'kind': 'exit', 'exit_code': 0})
        self.recover()
        self.assertFalse(self.stopped)

    def test_activity_arriving_after_initial_inspection_blocks_stop(self):
        def table():
            self.errors.write_text(self.marker + 'new active work\n')
            return self.rows()
        self.recover(table=table)
        self.assertFalse(self.stopped)

    def test_activity_during_final_process_inspection_blocks_stop(self):
        calls = []
        def table():
            calls.append(1)
            if len(calls) == 2:
                self.errors.write_text(self.marker + 'tool starts after initial check\n')
            return self.rows()
        self.recover(table=table)
        self.assertFalse(self.stopped)

    def test_terminal_states_and_missing_outcome_running_preserved(self):
        for state_name in ('review_ready', 'handoff_ready', 'blocked', 'running'):
            self.alive[:] = [self.runner, self.child]
            with self.reg.transaction() as state:
                state['lanes']['consumer'].update(state=state_name, handoff_at=1000)
            self.recover()
            self.assertEqual(self.reg.status()['lanes']['consumer']['state'], state_name)
        self.assertEqual(self.stopped, [self.child] * 4)

    def test_hook_runs_without_provider_retry_models_and_opt_in_required(self):
        self.controller.config['terminal_idle_recovery']['enabled'] = False
        recover(self.controller, table=self.rows, stop=self.stop)
        self.assertFalse(self.stopped)
        self.controller.config['terminal_idle_recovery']['enabled'] = True
        recover(self.controller, table=self.rows, stop=self.stop)
        self.assertEqual(self.stopped, [self.child])

    def test_recycled_parent_pid_does_not_claim_older_watchdog(self):
        owners = [dict(self.runner, started='200'), dict(self.child, started='201')]
        rows = [dict(self.rows()[0], Started='200'), dict(self.rows()[1], Started='201'),
                dict(self.rows()[2], Started='202'),
                dict(ProcessId=900, ParentProcessId=700, Name='powershell.exe', Started='100'),
                dict(ProcessId=901, ParentProcessId=900, Name='opencode.exe', Started='150')]
        self.assertTrue(safe_descendants(owners, rows))
        rows[-2]['Started'] = '203'
        self.assertFalse(safe_descendants(owners, rows))

    def test_missing_or_malformed_creation_time_cannot_exclude_busy_child(self):
        owners = [dict(self.runner, started='200'), dict(self.child, started='201')]
        rows = [dict(self.rows()[0], Started='200'), dict(self.rows()[1], Started='201'),
                dict(ProcessId=900, ParentProcessId=700, Name='powershell.exe', Started='100')]
        for missing in (None, '', 'yesterday', -1):
            rows[-1]['Started'] = missing
            self.assertFalse(safe_descendants(owners, rows))
        rows[-1]['Started'] = '100'
        rows[0].pop('Started')
        self.assertFalse(safe_descendants(owners, rows))

    def test_recycled_owner_pid_refuses_tree(self):
        owners = [dict(self.runner, started='200'), dict(self.child, started='201')]
        rows = [dict(self.rows()[0], Started='300'), dict(self.rows()[1], Started='301')]
        self.assertFalse(safe_descendants(owners, rows))

    def test_fresh_stdout_or_unrecognized_identity_blocks(self):
        os.utime(self.events, (1999, 1999))
        self.recover()
        os.utime(self.events, (1000, 1000))
        write(self.directory / 'child.json', {'pid': 701})
        self.recover()
        self.assertFalse(self.stopped)


if __name__ == '__main__':
    unittest.main()
