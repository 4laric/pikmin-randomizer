import copy
import tempfile
import unittest
from pathlib import Path

from workflow.handoff import Rejected
from workflow.registry import Registry, rotate_slow_log
from workflow.storage import migrate


class SlowLogRotationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()

    def test_rotation_bounds_files_and_ignores_small_log(self):
        path = self.root / 'slow-transactions.jsonl'
        self.assertFalse(rotate_slow_log(path, max_bytes=10, keep=2))  # missing file
        for _ in range(4):
            path.write_text('x' * 50, encoding='utf-8')
            self.assertTrue(rotate_slow_log(path, max_bytes=10, keep=2))
        names = sorted(p.name for p in self.root.glob('slow-transactions.jsonl*'))
        self.assertEqual(names, ['slow-transactions.jsonl.1', 'slow-transactions.jsonl.2'])
        path.write_text('x' * 5, encoding='utf-8')
        self.assertFalse(rotate_slow_log(path, max_bytes=10, keep=2))
        self.assertEqual(path.read_text(encoding='utf-8'), 'x' * 5)


class SectionedCostTests(unittest.TestCase):
    def setUp(self):
        self.fresh()

    def fresh(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.reg = Registry(self.root / 'output/registry.sqlite3', self.root, clock=lambda: 100.0)
        self.reg.init()
        with self.reg.transaction() as s:
            s['lanes'] = {'w': {'state': 'running', 'revision': 1}}
            s['throughput'] = {'costs': {}, 'jobs': {'keep': {'status': 'queued'}}}
            s['control'] = {'launches': {'keep': {'status': 'done'}}, 'ram_paused': False}

    def both(self, test):
        for migrated in (False, True):
            with self.subTest(migrated=migrated):
                self.fresh()
                if migrated:
                    migrate(self.reg)
                test()

    def test_cost_ingestion_is_section_scoped(self):
        def check():
            before = self.reg.snapshot()
            count = self.reg.report_cost_batch([
                {'event_id': 'e1', 'lane': 'w', 'amount': 0.25, 'at': 1000.0},
                {'event_id': 'e2', 'lane': 'w', 'amount': 0.5, 'at': 1001.0}])
            self.assertEqual(count, 2)
            after = self.reg.snapshot()
            self.assertEqual(after['throughput']['costs'], {
                'e1': {'id': 'e1', 'lane': 'w', 'amount': 0.25, 'currency': 'USD', 'at': 1000.0},
                'e2': {'id': 'e2', 'lane': 'w', 'amount': 0.5, 'currency': 'USD', 'at': 1001.0}})
            # Undeclared partitions are sealed by the sectioned transaction, never touched.
            self.assertEqual(after['throughput']['jobs'], before['throughput']['jobs'])
            self.assertEqual(after['control']['launches'], before['control']['launches'])
            self.assertEqual(after['lanes'], before['lanes'])
            self.assertEqual(len(after['events']), len(before['events']) + 2)
            # Replaying an existing event adds nothing (idempotent dedupe).
            self.assertEqual(self.reg.report_cost_batch(
                [{'event_id': 'e1', 'lane': 'w', 'amount': 0.25, 'at': 1000.0}]), 0)
            # An unknown lane is refused before any write, atomically.
            with self.assertRaises(Rejected):
                self.reg.report_cost_batch([{'event_id': 'e3', 'lane': 'nope', 'amount': 1.0}])
            # A malformed event in a mixed batch also refuses the whole batch.
            with self.assertRaises(Rejected):
                self.reg.report_cost_batch([
                    {'event_id': 'e4', 'lane': 'w', 'amount': 0.1},
                    {'event_id': 'e5', 'lane': 'w'}])
            self.assertEqual(self.reg.snapshot()['throughput']['costs'], after['throughput']['costs'])
        self.both(check)

    def test_single_report_cost_matches_and_validates_lane(self):
        def check():
            self.reg.report_cost('only', 'w', 1.5, at=2000.0)
            self.assertEqual(
                self.reg.snapshot()['throughput']['costs']['only'],
                {'id': 'only', 'lane': 'w', 'amount': 1.5, 'currency': 'USD', 'at': 2000.0})
            self.assertEqual(self.reg.report_cost('only', 'w', 1.5, at=2000.0)['amount'], 1.5)
            with self.assertRaises(Rejected):
                self.reg.report_cost('bad', 'missing', 1.0)
        self.both(check)

    def test_direct_report_still_validates_lane_by_default(self):
        before = self.reg.snapshot()
        with self.assertRaises(Rejected):
            with self.reg.transaction() as s:
                self.reg._report_cost(s, 'e9', 'missing', 1.0)
        self.assertEqual(self.reg.snapshot(), before)


if __name__ == '__main__':
    unittest.main()
