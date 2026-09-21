import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from workflow.handoff import Rejected
from workflow.operator import parked_scope_action
from workflow.planner_evidence_disposition import STATUS, dispose, dispositions
from workflow.registry import Registry


class PlannerEvidenceDispositionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.reg = Registry(self.root / 'output/workflow/registry.sqlite3', self.root)
        self.reg.init()
        self.proof = self.root / 'output' / 'audit.json'
        self.proof.parent.mkdir(parents=True, exist_ok=True)
        self.proof.write_text('{"scopes": "unavailable"}', encoding='utf-8')
        self.evidence = dict(path='output/audit.json',
                             sha256=hashlib.file_digest(self.proof.open('rb'), 'sha256').hexdigest())
        with self.reg.transaction() as state:
            state['lanes']['consumer'] = dict(lane='consumer', state='blocked',
                                              dependencies=['#9'], outcome={'outcome': 'blocked'})
        self.diagnoses = [
            dict(scope='a', status='unavailable', lanes=['consumer'],
                 owner_action='Owner re-submit a'),
            dict(scope='b', status='unavailable', lanes=['consumer'],
                 owner_action='Owner re-submit b'),
        ]

    def tearDown(self):
        self.tmp.cleanup()

    def test_dispose_records_and_is_idempotent(self):
        before = self.reg.snapshot()
        rows = dispose(self.reg, ['a', 'b'], reason='bytes lost everywhere',
                       evidence=self.evidence, recorded={'a': {'path': 'gone', 'sha256': '1' * 64}})
        self.assertEqual([row['scope'] for row in rows], ['a', 'b'])
        after = self.reg.snapshot()
        self.assertEqual(after['lanes'], before['lanes'])
        self.assertEqual(after['lanes']['consumer'], before['lanes']['consumer'])
        stored = dispositions(after)
        self.assertEqual(stored['a']['status'], STATUS)
        self.assertEqual(stored['a']['recorded_evidence'], {'path': 'gone', 'sha256': '1' * 64})
        replay = dispose(self.reg, ['a', 'b'], reason='bytes lost everywhere',
                         evidence=self.evidence, recorded={'a': {'path': 'gone', 'sha256': '1' * 64}})
        self.assertEqual([row['at'] for row in replay], [stored['a']['at'], stored['b']['at']])
        events = [e for e in self.reg.snapshot()['events'] if e.get('kind') == 'planner_evidence_disposed']
        self.assertEqual(len(events), 2)

    def test_conflicting_and_weak_evidence_rejected(self):
        dispose(self.reg, ['a'], reason='first', evidence=self.evidence)
        with self.assertRaises(Rejected):
            dispose(self.reg, ['a'], reason='different reason', evidence=self.evidence)
        with self.assertRaises(Rejected):
            dispose(self.reg, ['c'], reason='x',
                    evidence=dict(path='output/audit.json', sha256='f' * 64))
        with self.assertRaises(Rejected):
            dispose(self.reg, ['c'], reason='   ', evidence=self.evidence)

    def test_operator_action_suppresses_disposed_scopes(self):
        action = parked_scope_action(self.diagnoses, {'a': {}}, None)
        self.assertIsNotNone(action)
        self.assertEqual(action['reason'].split()[0], '2')
        dispose(self.reg, ['a'], reason='lost', evidence=self.evidence)
        disposed = dispositions(self.reg.snapshot())
        action = parked_scope_action(copy.deepcopy(self.diagnoses), None, None,
                                     disposed=disposed)
        self.assertEqual([row['scope'] for row in action['scopes']], ['b'])
        self.assertIn('1 planner scopes', action['reason'])
        self.assertEqual([row['scope'] for row in action['disposed']], ['a'])
        action = parked_scope_action(copy.deepcopy(self.diagnoses[1:]), None, None,
                                     disposed=disposed)
        self.assertIsNotNone(action)
        self.assertEqual(action['scopes'][0]['scope'], 'b')


if __name__ == '__main__':
    unittest.main()
