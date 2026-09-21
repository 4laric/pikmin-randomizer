import copy
import os
import socket
import tempfile
import unittest
from pathlib import Path

from workflow.handoff import Rejected
from workflow.registry import Registry
from workflow.stream_owner import activate, prepare

ROOT_COMMIT = 'a' * 40
NATIVE_COMMIT = 'b' * 40
DEAD_PID = 99999999


class StreamOwnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.reg = Registry(self.root / 'output/workflow/registry.sqlite3', self.root)
        self.reg.init()
        with self.reg.transaction() as state:
            state['development_streams'] = dict(schema=1, streams={
                'actors-assets': dict(
                    id='actors-assets', name='Actors and assets', status='awaiting-owner',
                    owner=None, ready_batch=None, candidates={}, maintained_receipts={},
                    maintained_base=dict(root=ROOT_COMMIT, native=NATIVE_COMMIT),
                    worktrees=dict(
                        root=dict(path='output/development-streams/actors-assets/root',
                                  branch='codex/stream-actors-assets'),
                        native=dict(path='output/development-streams/actors-assets/native',
                                    branch='codex/stream-actors-assets')),
                ),
            })
            state.setdefault('throughput', {}).setdefault('workers', {})['w1'] = dict(
                worker_id='w1', roles=['implementation'], capabilities=['source-review'],
                authorized_by='test')
            state['lanes']['previous-lane'] = dict(
                lane='previous-lane', owner='Codex through shared account 4laric',
                worker_id='w1', task_id='manual:previous', issue=9, scope='previous slice',
                target_level='tooling', milestone='test', closes_gates=[],
                next_action='held', owned_files=['docs/previous.md'], acceptance=['previous'],
                root=dict(base=ROOT_COMMIT, commits=[], head=ROOT_COMMIT, dirty='',
                          worktree='output/development-streams/actors-assets/root'),
                native=None, state='blocked', revision=3, generation=2,
                process=dict(host=socket.gethostname(), pid=DEAD_PID, started='1'),
                dependencies=['#9'], heartbeat_at=1.0, progress_at=1.0, created_at=1.0)
        self.observed = dict(root=dict(commit=ROOT_COMMIT), native=dict(commit=NATIVE_COMMIT))
        self.worktrees = dict(
            root=dict(exists=True, is_git=True, branch='codex/stream-actors-assets',
                      head=ROOT_COMMIT, ancestor_of_base=True,
                      path='output/development-streams/actors-assets/root'),
            native=dict(exists=True, is_git=True, branch='codex/stream-actors-assets',
                        head=NATIVE_COMMIT, ancestor_of_base=True,
                        path='output/development-streams/actors-assets/native'))

    def tearDown(self):
        self.tmp.cleanup()

    def prepare(self, **overrides):
        payload = dict(stream='actors-assets', worker_id='w1', issue=861,
                       observed=self.observed, worktrees=self.worktrees)
        payload.update(overrides)
        return prepare(self.reg, **payload)

    def test_prepare_packet_is_read_only_and_pinned(self):
        before = self.reg.snapshot()
        packet = self.prepare()
        after = self.reg.snapshot()
        self.assertEqual(before['lanes'], after['lanes'])
        self.assertEqual(before['development_streams'], after['development_streams'])
        self.assertEqual(packet['lane'], 'stream-owner-actors-assets')
        self.assertEqual(packet['previous_lane'], 'previous-lane')
        self.assertEqual(packet['root']['base'], ROOT_COMMIT)
        self.assertEqual(packet['root']['head'], ROOT_COMMIT)
        self.assertEqual(packet['maintained_base'],
                         dict(root=ROOT_COMMIT, native=NATIVE_COMMIT))

    def test_prepare_rejects_unknown_worker_and_missing_implementation_role(self):
        with self.assertRaises(Rejected):
            self.prepare(worker_id='nobody')
        with self.reg.transaction() as state:
            state['throughput']['workers']['w1']['roles'] = ['review']
        with self.assertRaises(Rejected):
            self.prepare()

    def test_prepare_rejects_open_assignment_and_live_lane(self):
        with self.reg.transaction() as state:
            state['throughput'].setdefault('assignments', {})['a1'] = dict(
                id='a1', worker_id='w1', status='dispatched', lane='previous-lane')
        with self.assertRaises(Rejected):
            self.prepare()
        with self.reg.transaction() as state:
            state['throughput']['assignments'].clear()
            state['lanes']['previous-lane']['process'] = dict(
                host=socket.gethostname(), pid=os.getpid(), started='1')
            state['lanes']['previous-lane']['state'] = 'running'
        with self.assertRaises(Rejected):
            self.prepare()

    def test_prepare_rejects_owned_stream_and_ready_batch(self):
        with self.reg.transaction() as state:
            state['development_streams']['streams']['actors-assets']['owner'] = dict(
                lane='other-owner', worker_id='w9', generation=1)
        with self.assertRaises(Rejected):
            self.prepare()
        with self.reg.transaction() as state:
            record = state['development_streams']['streams']['actors-assets']
            record['owner'] = None
            record['ready_batch'] = 'candidate-1'
        with self.assertRaises(Rejected):
            self.prepare()

    def test_prepare_rejects_stale_maintained_base(self):
        stale = dict(root=dict(commit='c' * 40), native=dict(commit=NATIVE_COMMIT))
        with self.assertRaises(Rejected):
            self.prepare(observed=stale)

    def test_activate_registers_and_binds_live_generation(self):
        packet = self.prepare()
        result = activate(self.reg, packet, os.getpid(), 'manual:stream-owner-actors-assets',
                          observed=self.observed, worktrees=self.worktrees)
        self.assertFalse(result['replayed'])
        self.assertEqual(result['generation'], 1)
        state = self.reg.snapshot()
        lane = state['lanes']['stream-owner-actors-assets']
        self.assertEqual(lane['worker_id'], 'w1')
        self.assertEqual(lane['issue'], 861)
        self.assertIsNone(lane.get('integration'))
        self.assertNotIn('integrated', [e.get('kind') for e in state.get('events', [])])
        owner = state['development_streams']['streams']['actors-assets']['owner']
        self.assertEqual(owner['lane'], 'stream-owner-actors-assets')
        self.assertEqual(owner['generation'], 1)
        self.assertEqual(owner['worker_id'], 'w1')
        self.assertEqual(state['development_streams']['streams']['actors-assets']['status'], 'active')

    def test_activate_requires_live_pid_and_does_not_mutate_on_failure(self):
        packet = self.prepare()
        before = self.reg.snapshot()['development_streams']
        with self.assertRaises(Rejected):
            activate(self.reg, packet, DEAD_PID, 'manual:stream-owner-actors-assets',
                     observed=self.observed, worktrees=self.worktrees)
        self.assertEqual(self.reg.snapshot()['development_streams'], before)
        with self.assertRaises(Rejected):
            activate(self.reg, packet, os.getpid(), '',
                     observed=self.observed, worktrees=self.worktrees)

    def test_activate_replay_is_idempotent_for_the_bound_owner(self):
        packet = self.prepare()
        first = activate(self.reg, packet, os.getpid(), 'manual:stream-owner-actors-assets',
                         observed=self.observed, worktrees=self.worktrees)
        second = activate(self.reg, packet, os.getpid(), 'manual:stream-owner-actors-assets',
                          observed=self.observed, worktrees=self.worktrees)
        self.assertEqual(second['lane'], first['lane'])
        self.assertEqual(second['generation'], first['generation'])
        self.assertTrue(second['replayed'])
        self.assertNotIn('integrated', [e.get('kind') for e in self.reg.snapshot().get('events', [])])


if __name__ == '__main__':
    unittest.main()

