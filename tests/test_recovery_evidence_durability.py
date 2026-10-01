"""Blocked/recovery evidence must survive transient worker-inbox cleanup (#855)."""
import os
import tempfile
import unittest
from pathlib import Path

from workflow.handoff import Rejected, digest
from workflow.registry import Registry


class RecoveryEvidenceDurabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.reg = Registry(self.root / 'output/coord/registry.sqlite3', self.root,
                            clock=lambda: 1000.0, process_probe=lambda _: 'alive')
        self.reg.init(dict(max_heavy_builds=1, heartbeat_seconds=10, progress_seconds=30))
        self.log = self.root / 'output/inbox/report.md'
        self.log.parent.mkdir(parents=True)
        self.log.write_text('blocked outcome report\n')
        self.evidence = {'path': str(self.log), 'sha256': digest(self.log)}
        self.reg.register(dict(
            lane='one', owner='Codex through 4laric', worker_id='one', task_id='task-one',
            issue=855, scope='Bounded tool slice', target_level='tooling', next_action='Run checks',
            milestone='workflow', owned_files=['workflow/one.py'], acceptance=['Evidence durable'], pid=os.getpid(),
            root=dict(base='a' * 40, head='a' * 40, commits=[], dirty='', worktree='.'), native=None))
        self.reg.checkpoint('one', 1, 1, {'state': 'running'})

    def finish_blocked(self):
        return self.reg.finish('one', 1, 'blocked', 'Needs producer', self.evidence, ['#186'])

    def test_blocked_outcome_is_archived_before_inbox_cleanup(self):
        lane = self.finish_blocked()
        stored = lane['outcome']['evidence']
        self.assertEqual(stored['sha256'], self.evidence['sha256'])
        self.assertNotEqual(stored['path'], str(self.log))
        self.assertEqual(lane['progress_evidence'], stored)
        self.log.unlink()
        resolved = self.reg.evidence(stored)
        self.assertEqual(digest(resolved), self.evidence['sha256'])

    def test_missing_recorded_path_resolves_only_on_exact_hash(self):
        self.finish_blocked()
        self.log.unlink()
        archived = self.reg.archived_evidence(self.evidence)
        self.assertIsNotNone(archived)
        self.assertEqual(self.reg.recovery_evidence(dict(path=str(self.log), sha256=self.evidence['sha256'])), archived)
        with self.assertRaises(Rejected):
            self.reg.recovery_evidence(dict(path=str(self.log), sha256='b' * 64))

    def test_archive_fallback_never_accepts_non_hex_or_unarchived_hash(self):
        self.assertIsNone(self.reg.archived_evidence({'path': str(self.log), 'sha256': 'bad'}))
        self.log.unlink()
        with self.assertRaises(Rejected):
            self.reg.evidence({'path': str(self.log), 'sha256': 'c' * 64})

    def test_blocked_finish_replay_is_idempotent_after_archive(self):
        first = self.finish_blocked()
        replay = self.finish_blocked()
        self.assertEqual(first['outcome'], replay['outcome'])


if __name__ == '__main__':
    unittest.main()
