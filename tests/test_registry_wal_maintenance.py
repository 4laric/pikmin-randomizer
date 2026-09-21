"""Bounded registry WAL maintenance: truncate above a cap, never fail or lose data.

The WAL is exercised directly: an open, idle connection keeps the file in place the way
the live controller's persistent processes do, without depending on transaction-close
checkpoint timing.
"""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from workflow.registry import Registry
from workflow.registry_wal import maintain, sizes, start_monitor


class WalMaintenanceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name).resolve()
        self.path = self.dir / 'registry.sqlite3'
        self.stub = SimpleNamespace(path=self.path, clock=lambda: 1234.0)

    def wal_database(self, rows=200):
        """A WAL-mode database with an open idle connection and `rows` committed rows."""
        conn = sqlite3.connect(self.path)
        self.addCleanup(conn.close)
        self.assertEqual(conn.execute('PRAGMA journal_mode=wal').fetchone()[0], 'wal')
        conn.execute('CREATE TABLE filler (x)')
        conn.execute('BEGIN IMMEDIATE')
        conn.executemany('INSERT INTO filler VALUES (?)', [(i,) for i in range(rows)])
        conn.commit()
        return conn

    def test_below_the_limit_leaves_the_wal_untouched(self):
        self.wal_database(rows=2)
        report = maintain(self.stub, limit_bytes=64 * 1024 * 1024)
        self.assertEqual(report['action'], 'none')
        self.assertIsNone(report['passive'])
        self.assertIsNone(report['truncate'])

    def test_wal_above_the_limit_is_truncated_without_data_loss(self):
        conn = self.wal_database(rows=400)
        self.assertGreater(sizes(self.path)['wal'], 4096)
        report = maintain(self.stub, limit_bytes=4096)
        self.assertEqual(report['action'], 'truncate')
        self.assertEqual(report['truncate'][0], 0)  # No reader blocked the truncate.
        self.assertLessEqual(report['after']['wal'], 4096)
        self.assertEqual(conn.execute('SELECT count(*) FROM filler').fetchone()[0], 400)

    def test_a_pinned_old_reader_never_raises_or_loses_data_and_the_next_pass_recovers(self):
        writer = self.wal_database(rows=200)
        reader = sqlite3.connect(self.path)
        self.addCleanup(reader.close)
        reader.execute('BEGIN')
        reader.execute('SELECT * FROM filler').fetchall()  # Old snapshot.
        writer.execute('BEGIN IMMEDIATE')
        writer.execute('INSERT INTO filler VALUES (9999)')
        writer.commit()
        report = maintain(self.stub, limit_bytes=1)
        self.assertIn(report['action'], ('passive', 'truncate'))
        self.assertEqual(report['truncate'][0], 1)  # The pinned reader blocked truncation.
        reader.rollback()
        after = maintain(self.stub, limit_bytes=1)  # Reader gone: the retry truncates.
        self.assertEqual(after['truncate'][0], 0)
        self.assertLessEqual(after['after']['wal'], 1)
        self.assertEqual(writer.execute('SELECT count(*) FROM filler').fetchone()[0], 201)

    def test_a_non_wal_registry_is_a_noop(self):
        conn = sqlite3.connect(self.path)
        self.addCleanup(conn.close)
        conn.execute('CREATE TABLE filler (x)')
        conn.commit()
        report = maintain(self.stub, limit_bytes=1)
        self.assertEqual(report['action'], 'none')
        self.assertEqual(report['journal'], 'delete')

    def test_monitor_is_idempotent_and_waits_the_configured_interval(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        root = Path(temp.name).resolve()
        reg = Registry(root / 'output/registry.sqlite3', root)
        reg.init()
        controller = SimpleNamespace(reg=reg, base=root / 'output/controller',
                                     config={'registry_wal': {'interval_seconds': 45}})
        with patch('workflow.registry_wal.threading.Thread') as thread, \
                patch('workflow.registry_wal.threading.Event') as event:
            event.return_value.is_set.side_effect = [False, True]
            stop = start_monitor(controller)
            self.assertIs(start_monitor(controller), stop)
            thread.call_args.kwargs['target']()
            event.return_value.wait.assert_called_once_with(45)


if __name__ == '__main__':
    unittest.main()
