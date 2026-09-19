import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow import registry_archive, registry_wal
from workflow.handoff import Rejected
from workflow.registry import Registry
from workflow.storage import migrate
from workflow.wakeup import EventWaiter

DAY = 86400


class MaintenanceFixture(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.now = 100 * DAY
        self.reg = Registry(self.root/'output/workflow/registry.sqlite3', self.root, clock=lambda: self.now)
        self.reg.init()
        old, recent = self.now - 30 * DAY, self.now - DAY / 2
        with self.reg.transaction() as s:
            lane = lambda state, at: dict(state=state, integrated_at=at, progress_at=at, created_at=at - 10)
            s['lanes'] = {'old': lane('done', old), 'fresh': lane('done', recent), 'live': lane('running', old),
                          'busy': lane('done', old)}
            s['events'] = [dict(at=old + i, kind='k', lane=('old', 'live', None, 'busy')[i % 4], n=i) for i in range(300)]
            s['control'] = dict(controller=None, launches={
                'l1': dict(id='l1', lane='old', status='exited'), 'l2': dict(id='l2', lane='old', status='exited'),
                'l3': dict(id='l3', lane='fresh', status='exited'), 'l4': dict(id='l4', lane='busy', status='running')})
            s['actions'] = {'a1': dict(id='a1', lane='old', status='pending'), 'a2': dict(id='a2', lane='live', status='pending')}
        migrate(self.reg)
        self.before = self.reg.snapshot()


class WalTests(MaintenanceFixture):
    def test_report_only_then_switch_verifies_every_reader_and_reverts(self):
        report = registry_wal.switch(self.reg, 'wal')
        self.assertEqual((report['journal_mode'], report['applied'], report['quiesced']), ('delete', False, True))
        self.assertEqual(registry_wal.journal(self.reg.path), 'delete')
        report = registry_wal.switch(self.reg, 'wal', apply=True)
        self.assertEqual((report['journal_mode'], report['applied'], report['verified']), ('wal', True, True))
        self.assertEqual(self.reg.snapshot(), self.before)
        cursor = EventWaiter(self.reg.path).token()
        with self.reg.transaction(sections=(), append=[('events',)]) as s: self.reg.event(s, 'after-wal', None)
        self.assertEqual(EventWaiter(self.reg.path).wait(0, cursor)['reason'], 'changed')
        ro = sqlite3.connect(self.reg.path.as_uri() + '?mode=ro', uri=True)
        try: self.assertEqual(ro.execute('PRAGMA journal_mode').fetchone()[0], 'wal')
        finally: ro.close()
        self.assertTrue(registry_wal.switch(self.reg, 'delete', apply=True)['applied'])
        self.assertEqual(registry_wal.journal(self.reg.path), 'delete')

    def test_refuses_without_quiesce(self):
        with self.reg.transaction() as s: s['control']['controller'] = dict(host='h', pid=1, started='1')
        with self.assertRaisesRegex(Rejected, 'controller'):
            registry_wal.switch(self.reg, 'wal', apply=True, probe=lambda p: 'alive')
        holder = sqlite3.connect(self.reg.path); holder.execute('BEGIN IMMEDIATE')
        try:
            with self.assertRaisesRegex(Rejected, 'Another connection'):
                registry_wal.switch(self.reg, 'wal', apply=True, probe=lambda p: 'dead')
        finally: holder.rollback(); holder.close()
        self.assertEqual(registry_wal.journal(self.reg.path), 'delete')

    def test_failed_verification_restores_the_previous_mode(self):
        with patch.object(registry_wal, 'verify', side_effect=Rejected('reader broke')):
            with self.assertRaisesRegex(Rejected, 'restored delete'):
                registry_wal.switch(self.reg, 'wal', apply=True)
        self.assertEqual(registry_wal.journal(self.reg.path), 'delete')


class ArchiveTests(MaintenanceFixture):
    def test_dry_run_changes_nothing(self):
        report = registry_archive.archive(self.reg, 7)
        self.assertEqual((report['lanes'], report['events'], report['launches'], report['actions'], report['applied']),
                         (1, 75, 2, 1, False))
        self.assertEqual(report['skipped'], {'busy': 'launch in flight'})
        self.assertEqual(self.reg.snapshot(), self.before)
        self.assertFalse(registry_archive.default_path(self.root).exists())

    def test_move_preserves_every_record_and_is_idempotent(self):
        report = registry_archive.archive(self.reg, 7, apply=True)
        self.assertTrue(report['applied']); self.assertEqual(report['copied'], 78)
        after = self.reg.snapshot()
        self.assertNotIn('l1', after['control']['launches']); self.assertNotIn('a1', after['actions'])
        self.assertFalse(any(e['lane'] == 'old' for e in after['events']))
        self.assertEqual(after['lanes']['old']['archived'][0]['run'], report['run'])
        self.assertEqual(after['wake_revision'], len(self.before['events']))
        restored = registry_archive.merged(self.root, after)
        self.assertEqual(restored['events'], self.before['events'])
        self.assertEqual(restored['control']['launches'], self.before['control']['launches'])
        self.assertEqual(restored['actions'], self.before['actions'])
        tombless = copy.deepcopy(restored['lanes']); del tombless['old']['archived']
        self.assertEqual(tombless, self.before['lanes'])
        self.assertEqual(registry_archive.history(self.root, lane='old')['launches'].keys(), {'l1', 'l2'})
        again = registry_archive.archive(self.reg, 7, apply=True)
        self.assertFalse(again['applied']); self.assertEqual(again['lanes'], 0)

    def test_interrupted_runs_are_settled_without_loss_or_duplicates(self):
        with patch.object(registry_archive, 'remove', side_effect=Rejected('changed')):
            with self.assertRaises(Rejected):
                registry_archive.archive(self.reg, 7, apply=True, vacuum=False)
        self.assertEqual(self.reg.snapshot(), self.before)
        self.assertEqual(registry_archive.history(self.root)['events'], [])
        crash = []
        real_mark = registry_archive.mark
        def die(path, run, status):
            if status == 'moved': crash.append(run); raise OSError('killed before marking the run')
            return real_mark(path, run, status)
        with patch.object(registry_archive, 'mark', side_effect=die):
            with self.assertRaises(OSError):
                registry_archive.archive(self.reg, 7, apply=True, vacuum=False)
        after = self.reg.snapshot()
        self.assertEqual(registry_archive.merged(self.root, after)['events'], self.before['events'])
        self.assertEqual(registry_archive.history(self.root)['events'], [])  # Unsettled without the registry state.
        self.now += 60
        with self.reg.transaction() as s: s['lanes']['fresh'].update(integrated_at=self.now - 10 * DAY, progress_at=self.now - 10 * DAY, created_at=0)
        registry_archive.archive(self.reg, 7, apply=True, vacuum=False)
        db = sqlite3.connect(registry_archive.default_path(self.root))
        try:
            self.assertEqual(dict(db.execute('SELECT run, status FROM archive_runs').fetchall())[crash[0]], 'moved')
        finally: db.close()
        final = registry_archive.merged(self.root, self.reg.snapshot())
        self.assertEqual(final['events'], self.before['events'])
        self.assertEqual(final['control']['launches'], self.before['control']['launches'])

    def test_apply_refuses_while_the_controller_runs(self):
        with self.reg.transaction() as s: s['control']['controller'] = dict(host='h', pid=1, started='1')
        self.before = self.reg.snapshot()
        with self.assertRaisesRegex(Rejected, 'not confirmed stopped'):
            registry_archive.archive(self.reg, 7, apply=True, probe=lambda p: 'alive')
        self.assertEqual(self.reg.snapshot(), self.before)

    def test_vacuum_shrinks_the_file(self):
        with self.reg.transaction() as s:
            s['events'] += [dict(at=self.now - 30 * DAY, kind='bulk', lane='old', pad='x' * 2000) for _ in range(2000)]
        report = registry_archive.archive(self.reg, 7, apply=True)
        self.assertLess(report['bytes_after'], report['bytes_before'] / 2)


if __name__ == '__main__': unittest.main()
