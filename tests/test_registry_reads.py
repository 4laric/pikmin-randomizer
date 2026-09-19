import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from workflow.registry import Registry
from workflow.handoff import Rejected


class RegistryReadTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.reg = Registry(self.root / 'output/registry.sqlite3', self.root)
        self.reg.init()

    def test_status_reads_committed_version_during_pending_write(self):
        writer = sqlite3.connect(self.reg.path, timeout=.1)
        try:
            writer.execute('BEGIN IMMEDIATE')
            state = self.reg.snapshot()
            state['settings']['max_heavy_builds'] = 4
            writer.execute('UPDATE registry SET body=?', (json.dumps(state),))
            self.assertEqual(self.reg.status()['settings']['max_heavy_builds'], 2)
            writer.commit()
            self.assertEqual(self.reg.status()['settings']['max_heavy_builds'], 4)
        finally:
            writer.close()

    def test_reporting_computation_does_not_hold_writer_lock(self):
        def calculate(state, now, **kwargs):
            # Simulate a worker publishing progress while reporting is computing.
            with closing(sqlite3.connect(self.reg.path, timeout=.1)) as worker:
                worker.execute('BEGIN IMMEDIATE')
                worker.execute('UPDATE registry SET body=body')
                worker.commit()
            return {}
        with patch('workflow.analytics.throughput_metrics', side_effect=calculate):
            self.reg.throughput_status()

    def test_snapshot_detached_and_validated(self):
        snapshot = self.reg.snapshot()
        snapshot['settings']['max_heavy_builds'] = 99
        self.assertEqual(self.reg.snapshot()['settings']['max_heavy_builds'], 2)
        with closing(sqlite3.connect(self.reg.path)) as db:
            snapshot['root'] = 'wrong-workspace'
            db.execute('UPDATE registry SET body=?', (json.dumps(snapshot),))
            db.commit()
        with self.assertRaises(Rejected):
            self.reg.snapshot()
