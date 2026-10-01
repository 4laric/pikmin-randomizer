"""Bounded, hash-preserving repair of dead-but-archived recovery evidence (#865)."""
import hashlib
import os
import tempfile
import unittest
from pathlib import Path

from workflow.operator import parked_scope_action
from workflow.recovery_evidence_repair import REPAIR_HISTORY, apply, plan, resolves
from workflow.registry import Registry


def sha(data):
    return hashlib.sha256(data).hexdigest()


class RecoveryEvidenceRepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.reg = Registry(self.root / 'output/coord/registry.sqlite3', self.root,
                            clock=lambda: 1000.0, process_probe=lambda _: 'alive')
        self.reg.init(dict(max_heavy_builds=1, heartbeat_seconds=10, progress_seconds=30))
        self.reg.register(dict(
            lane='one', owner='Codex through 4laric', worker_id='one', task_id='task-one',
            issue=865, scope='Bounded tool slice', target_level='tooling', next_action='Run checks',
            milestone='workflow', owned_files=['workflow/recovery_evidence_repair.py'],
            acceptance=['Dead-but-archived evidence repaired'], pid=os.getpid(),
            root=dict(base='a' * 40, head='a' * 40, commits=[], dirty='', worktree='.'), native=None))
        self.reg.checkpoint('one', 1, 1, {'state': 'running'})
        (self.root / 'output/workflow/evidence').mkdir(parents=True)

    def archive(self, data):
        sha256 = sha(data)
        (self.root / 'output/workflow/evidence' / sha256).write_bytes(data)
        return sha256

    def park(self, evidence, state='blocked'):
        with self.reg.transaction() as state_:
            lane = state_['lanes']['one']
            lane.update(state=state, outcome=dict(outcome='blocked', summary='x',
                        evidence=dict(evidence)), progress_evidence=dict(evidence))
        return self.reg

    def test_dead_but_archived_pointer_is_repaired_and_hash_preserved(self):
        sha256 = self.archive(b'blocked outcome report\n')
        self.park(dict(path='output/inbox/gone.md', sha256=sha256))
        planned = plan(self.root, self.reg.snapshot())
        self.assertEqual(len(planned), 2)
        self.assertEqual({p['field'] for p in planned}, {'outcome', 'progress_evidence'})
        applied = apply(self.reg)
        self.assertEqual(len(applied), 2)
        lane = self.reg.snapshot()['lanes']['one']
        self.assertEqual(lane['outcome']['evidence'], dict(
            path='output/workflow/evidence/' + sha256, sha256=sha256))
        self.assertEqual(lane['progress_evidence'], dict(
            path='output/workflow/evidence/' + sha256, sha256=sha256))
        self.assertTrue(resolves(self.root, lane['outcome']['evidence']))
        history = self.reg.snapshot().get(REPAIR_HISTORY)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['previous_path'], 'output/inbox/gone.md')
        self.assertIn('recovery_evidence_repaired', [e['kind'] for e in self.reg.snapshot()['events']])

    def test_repair_is_idempotent(self):
        sha256 = self.archive(b'blocked outcome report\n')
        self.park(dict(path='output/inbox/gone.md', sha256=sha256))
        self.assertEqual(len(apply(self.reg)), 2)
        self.assertEqual(len(plan(self.root, self.reg.snapshot())), 0)
        self.assertEqual(apply(self.reg), [])

    def test_stale_bytes_are_never_substituted(self):
        sha256 = self.archive(b'recorded bytes')
        live = self.root / 'output/inbox/report.md'
        live.parent.mkdir(parents=True, exist_ok=True)
        live.write_bytes(b'tampered bytes')
        self.park(dict(path='output/inbox/report.md', sha256=sha256))
        self.assertEqual(plan(self.root, self.reg.snapshot()), [])
        self.assertEqual(apply(self.reg), [])

    def test_unarchived_hash_is_refused(self):
        self.park(dict(path='output/inbox/gone.md', sha256='a' * 64))
        self.assertEqual(plan(self.root, self.reg.snapshot()), [])
        self.assertEqual(apply(self.reg), [])

    def test_malformed_hash_is_refused(self):
        self.park(dict(path='output/inbox/gone.md', sha256='not-a-hash'))
        self.assertEqual(plan(self.root, self.reg.snapshot()), [])

    def test_non_blocked_lane_is_never_touched(self):
        sha256 = self.archive(b'blocked outcome report\n')
        self.park(dict(path='output/inbox/gone.md', sha256=sha256), state='handoff_ready')
        self.assertEqual(plan(self.root, self.reg.snapshot()), [])
        self.assertEqual(apply(self.reg), [])

    def test_path_escaping_root_is_refused(self):
        sha256 = self.archive(b'blocked outcome report\n')
        outside = self.root.parent / 'outside.md'
        outside.write_bytes(b'blocked outcome report\n')
        self.park(dict(path='../outside.md', sha256=sha256))
        self.assertEqual(plan(self.root, self.reg.snapshot()), [])
        self.assertEqual(apply(self.reg), [])


    def test_operator_action_surfaces_repairable_pointers(self):
        diagnosis = dict(scope='x', status='unavailable', lanes=['owner'], owner_action='Refused: re-submit')
        action = parked_scope_action([diagnosis], {'x': {}}, repairs=[dict(lane='owner')])
        self.assertEqual(action['priority'], 0)
        self.assertEqual(action['repairable_blocked_lanes'], 1)
        self.assertIn('workflow.recovery_evidence_repair', action['next_action'])
        self.assertIn('#855', action['next_action'])
        self.assertIn('re-submit', action['next_action'])
        without = parked_scope_action([diagnosis], {'x': {}})
        self.assertEqual(without['priority'], 1)
        self.assertEqual(without['repairable_blocked_lanes'], 0)


if __name__ == '__main__':
    unittest.main()
