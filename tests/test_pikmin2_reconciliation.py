"""Fenced handoff reconciliation (#511); isolated registry, no game builds."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from workflow.handoff import GATES, Rejected, digest
from workflow.processes import probe as live_probe
from workflow.registry import Registry


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.now = 1000.0
        self.health = 'dead'
        self.db = self.root / 'output/coord/registry.sqlite3'
        self.reg = Registry(self.db, self.root, clock=lambda: self.now,
                            process_probe=lambda _: self.health)
        self.reg.init(dict(max_heavy_builds=1, heartbeat_seconds=10, progress_seconds=30))
        self.log = self.root / 'output/log.txt'
        self.log.write_text('test passed\nninja: no work to do.\n')
        self.note = self.root / 'output/note.txt'
        self.note.write_text('reconcile diagnosis\n')
        (self.root / 'output').mkdir(exist_ok=True)

    def evidence(self, path=None):
        path = Path(path) if path else self.log
        return {'path': str(path), 'sha256': digest(path)}

    def data(self, key='one'):
        return dict(lane=key, owner='Codex through 4laric', worker_id=key,
                    task_id='opencode:task-' + key, issue=511,
                    scope='Bounded reconcile slice', target_level='tooling', next_action='Run checks',
                    milestone='workflow', owned_files=['workflow/' + key + '.py'],
                    acceptance=['Blocked handoff returns without new work'], pid=os.getpid(),
                    root=dict(base='a' * 40, head='a' * 40, commits=[], dirty='', worktree='.'),
                    native=None)

    def handoff_doc(self, lane, reviews=None):
        data = {key: lane[key] for key in ('lane', 'owner', 'task_id', 'issue', 'generation',
                                           'scope', 'target_level', 'owned_files', 'root', 'native')}
        data.update(schema=1, parent_issue=186, kind='tooling', next_action='Review',
            changed_files=list(lane['owned_files']), evidence={'log': self.evidence()},
            remaining_work=[], shared_reviews=reviews or [],
            source_mapping=[{'description': 'Reconcile contract', 'evidence': ['log']}],
            tests=[{'command': 'python -m unittest', 'exit_code': 0, 'evidence': ['log']}],
            gates={g: {'status': 'UNTESTED', 'method': 'unobserved', 'detail': 'Tooling-only slice'}
                   for g in GATES},
            slice_acceptance=[{'criterion': lane['acceptance'][0], 'status': 'PASS', 'evidence': ['log']}],
            fixture_adoption={'status': 'N/A', 'reason': 'No native runtime change'})
        return data

    def save_handoff(self, data, name='handoff.json'):
        path = self.root / ('output/' + name)
        path.write_text(json.dumps(data))
        return str(path)

    def blocked_with_handoff(self, key='one', reviews=None):
        self.reg.register(self.data(key))
        self.reg.checkpoint(key, 1, 1, {'state': 'running'})
        lane = self.reg.status()['lanes'][key]
        path = self.save_handoff(self.handoff_doc(lane, reviews))
        self.reg.submit_handoff(key, 1, 2, path)
        lane = self.reg.status()['lanes'][key]
        self.reg.finish(key, 1, 'blocked', 'Parked mid-integration', self.evidence(),
                        dependencies=['#492'])
        return self.reg.status()['lanes'][key]

    def reconcile(self, key='one', revision=None, summary='Reconcile valid handoff'):
        lane = self.reg.status()['lanes'][key]
        return self.reg.reconcile_handoff(key, lane['generation'], revision or lane['revision'],
                                          summary, self.evidence(self.note))

    def test_happy_path_restores_ready_and_integrates(self):
        before = self.blocked_with_handoff()
        old_handoff = copy.deepcopy(before['handoff'])
        lane = self.reconcile()
        self.assertEqual(lane['state'], 'handoff_ready')
        self.assertEqual(lane['handoff'], old_handoff)
        self.assertEqual(lane['revision'], before['revision'] + 1)
        self.assertIsNone(lane['outcome'])
        self.assertEqual(lane['dependencies'], [])
        self.assertEqual(lane['reconcile']['pending_reviews'], [])
        validation = self.root / 'output/checks.log'
        validation.write_text('checker exit 0\n')
        record = {'root_commit': 'b' * 40, 'validation_path': 'output/checks.log',
                  'validation_sha256': digest(validation)}
        lane = self.reg.checkpoint('one', 1, lane['revision'], {'state': 'integrating'})
        lane = self.reg.integrate('one', 1, lane['revision'], record)
        self.assertEqual(lane['state'], 'done')

    def test_stale_generation_and_revision_rejected(self):
        self.blocked_with_handoff()
        with self.assertRaises(Rejected):
            self.reg.reconcile_handoff('one', 99, 4, 'stale gen', self.evidence(self.note))
        with self.assertRaises(Rejected):
            self.reg.reconcile_handoff('one', 1, 1, 'stale rev', self.evidence(self.note))
        self.assertEqual(self.reg.status()['lanes']['one']['state'], 'blocked')

    def test_live_and_unknown_owner_refused(self):
        self.blocked_with_handoff()
        for health in ('alive', 'unknown'):
            self.health = health
            with self.assertRaises(Rejected):
                self.reconcile()
            self.assertEqual(self.reg.status()['lanes']['one']['state'], 'blocked')
        self.health = 'dead'

    def test_handoff_file_drift_refused(self):
        self.blocked_with_handoff()
        path = self.root / 'output/handoff.json'
        doc = json.loads(path.read_text())
        doc['remaining_work'] = ['silently edited']
        path.write_text(json.dumps(doc))
        with self.assertRaisesRegex(Rejected, 'Handoff changed after submission'):
            self.reconcile()

    def test_evidence_drift_refused(self):
        self.blocked_with_handoff()
        self.log.write_text('changed after submission\n')
        with self.assertRaisesRegex(Rejected, 'Evidence hash mismatch'):
            self.reconcile()

    def test_only_blocked_lanes_reconcile(self):
        self.reg.register(self.data())
        with self.assertRaises(Rejected):
            self.reconcile()
        self.reg.checkpoint('one', 1, 1, {'state': 'running'})
        with self.assertRaises(Rejected):
            self.reconcile()
        lane = self.reg.status()['lanes']['one']
        path = self.save_handoff(self.handoff_doc(lane))
        self.reg.submit_handoff('one', 1, 2, path)
        with self.assertRaises(Rejected):
            self.reconcile()

    def test_blocked_without_handoff_rejected(self):
        self.reg.register(self.data())
        self.reg.finish('one', 1, 'blocked', 'No handoff yet', self.evidence(), dependencies=['#492'])
        with self.assertRaises(Rejected):
            self.reconcile()

    def test_pending_reviews_survive_reconcile(self):
        reviews = [{'file': 'shared/mod.py', 'reason': 'Consumed hook', 'issue_url': 'http://x/1',
                    'status': 'requested', 'evidence': ['log']}]
        self.blocked_with_handoff(reviews=reviews)
        lane = self.reconcile()
        self.assertEqual(lane['reconcile']['pending_reviews'], ['shared/mod.py'])
        lane = self.reg.checkpoint('one', 1, lane['revision'], {'state': 'integrating'})
        validation = self.root / 'output/checks.log'
        validation.write_text('checker exit 0\n')
        record = {'root_commit': 'b' * 40, 'validation_path': 'output/checks.log',
                  'validation_sha256': digest(validation)}
        with self.assertRaisesRegex(Rejected, 'Resolve shared reviews before integration'):
            self.reg.integrate('one', 1, lane['revision'], record)

    def test_in_flight_launch_refused(self):
        self.blocked_with_handoff()
        self.reg.plan_launch('one', 'Resume attempt', 'Continue bounded slice',
                             ['opencode-go/muse-spark-1.3-contributor'])
        with self.assertRaisesRegex(Rejected, 'dispatch in flight'):
            self.reconcile()

    def test_live_lease_refused_then_dead_lease_tolerated(self):
        self.blocked_with_handoff()
        sleeper = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])

        def stop_sleeper():
            try:
                sleeper.kill()
            except OSError:
                pass
            try:
                sleeper.wait(timeout=10)
            except Exception:
                pass
        self.addCleanup(stop_sleeper)
        lease = self.reg.acquire('one', 1, 'build:output/a', sleeper.pid)
        self.assertTrue(lease['acquired'])
        held = lease['lease']['process']
        self.reg.probe = lambda ident: live_probe(ident) if ident == held else 'dead'
        with self.assertRaisesRegex(Rejected, 'lease held'):
            self.reconcile()
        sleeper.kill()
        sleeper.wait(timeout=10)
        self.assertEqual(live_probe(held), 'dead')
        lane = self.reconcile()
        self.assertEqual(lane['state'], 'handoff_ready')


if __name__ == '__main__':
    unittest.main()
