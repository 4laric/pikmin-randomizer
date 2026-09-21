"""The autofill planner path must not take the writer lock for read-only or meta-only work.

``prerequisite_queue.collect`` runs on every planner tick. It reads only the lanes
partition and the control launch list and writes only the autofill meta row plus the
events history, yet it previously opened a full-state ``Registry.transaction()`` that
decoded and re-serialized the whole documents registry (lanes, costs, events, jobs,
assignments, ...). On the live database that held the exclusive writer for seconds.
These tests pin the declared scope so a later edit cannot silently reintroduce it.
"""
import ast
import inspect
import textwrap
import unittest
from unittest.mock import patch

from tests import test_planner_pool as fixtures
from workflow.handoff import Rejected, digest
from workflow.prerequisite_queue import collect


def _unscoped_transaction_lines(func):
    """Line numbers of ``*.transaction()`` calls in *func* that pass no ``sections=``."""
    source = textwrap.dedent(inspect.getsource(func))
    tree = ast.parse(source)
    lines = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'transaction'
                and not any(keyword.arg == 'sections' for keyword in node.keywords)):
            lines.append(node.lineno)
    return lines


class PlannerScopeTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.PlannerPoolTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.reg, self.settings = self.f.reg, self.f.settings
        self.f.tick()
        report = self.f.f.out/'no-work.md'
        report.write_text('No-work: missing provider contract, source owner must implement it.')
        self.evidence = dict(path=str(report), sha256=digest(report))
        self.reg.finish('next-cycle-1', 1, 'review-ready', 'No-work: unowned prerequisite', self.evidence)
        self.f.tick()
        self.f.f.planner()
        self.f.controller.config['lanes']['planner'] = dict(self.f.controller.config['lanes']['planner'],
            output=str(self.f.f.out/'coordinator'))
        self.settings['planner_pool']['helpers'][0]['defer_for_review'] = [str(self.f.f.out)]

    def test_collect_never_opens_an_unscoped_transaction(self):
        self.assertEqual(_unscoped_transaction_lines(collect), [],
                         'prerequisite_queue.collect must declare its registry sections')

    def test_collect_actually_declares_the_expected_scope(self):
        seen = []
        original = self.reg.transaction

        def recording(*args, **kwargs):
            seen.append((kwargs.get('sections'), kwargs.get('append')))
            return original(*args, **kwargs)

        with patch.object(self.reg, 'transaction', side_effect=recording):
            collect(self.reg, self.settings)
        self.assertTrue(seen, 'collect did not open its (now scoped) transaction')
        self.assertNotIn(None, [sections for sections, _ in seen],
                         'collect passed sections=None (a full-state writer lock)')
        self.assertEqual(seen[0][0], [('lanes',), ('control', 'launches')])
        self.assertEqual(seen[0][1], [('events',)])

    def test_collect_scoped_run_equals_a_full_state_snapshot(self):
        # Behavioural equivalence: the scoped transaction writes the same requests.
        collect(self.reg, self.settings)
        requests = self.reg.snapshot()['throughput_runtime']['autofill']['prerequisite_requests']
        self.assertTrue(requests)

    def test_undeclared_partition_stays_sealed_for_the_scoped_transaction(self):
        # A mutation outside the declared scope must refuse and roll back, proving the
        # scope is real rather than a cosmetic keyword.
        from workflow import storage
        with self.reg.transaction(sections=[('lanes',)]) as state:
            sealed = [value for value in state.values() if isinstance(value, storage.Sealed)]
            self.assertTrue(sealed, 'expected at least one sealed partition')
            target = next(iter(sealed))
            self.assertRaises(Rejected, lambda: target['x'])
            self.assertRaises(Rejected, lambda: target.__setitem__('x', {}))


if __name__ == '__main__':
    unittest.main()
