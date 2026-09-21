import copy
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow import storage
from workflow.handoff import Rejected
from workflow.registry import Registry
from workflow.storage import migrate


class SectionedTransactionTests(unittest.TestCase):
    def setUp(self):
        self.fresh()

    def fresh(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.reg = Registry(self.root/'output/registry.sqlite3', self.root, clock=lambda: 100.0)
        self.reg.init()
        with self.reg.transaction() as s:
            s['lanes'] = {'z': {'state': 'blocked'}, 'a': {'state': 'done'}}
            s['events'] = [{'i': i} for i in range(250)]
            s['control'] = {'launches': {'z': {'status': 'running'}}, 'ram_paused': False}
            s['stage_timing'] = {'history': [{'i': i} for i in range(140)], 'current': {}}
            s['queue_pressure'] = {'at': 1}

    def both(self, test):
        for migrated in (False, True):
            with self.subTest(migrated=migrated):
                self.fresh()
                if migrated: migrate(self.reg)
                test()

    def test_declared_write_matches_full_transaction_and_appends_events(self):
        def check():
            before = self.reg.snapshot()
            with self.reg.transaction(sections=[('lanes',)], append=[('events',)]) as s:
                s['lanes']['z']['state'] = 'ready'; s['lanes']['new'] = {'state': 'ready'}; del s['lanes']['a']
                for i in range(10): self.reg.event(s, 'x', 'z', n=i)
                s['queue_pressure'] = {'at': 2}
            expected = copy.deepcopy(before)
            expected['lanes'] = {'z': {'state': 'ready'}, 'new': {'state': 'ready'}}
            expected['events'] += [dict(at=self.reg.clock(), kind='x', lane='z', n=i) for i in range(10)]
            expected['wake_revision'] = before.get('wake_revision', len(before['events'])) + 10
            expected['queue_pressure'] = {'at': 2}
            after = self.reg.snapshot()
            self.assertEqual(after, expected)
            self.assertEqual(list(after['lanes']), ['z', 'new'])
        self.both(check)

    def test_undeclared_use_refuses_and_rolls_back(self):
        def check():
            before = self.reg.snapshot()
            attempts = [lambda s: s['control']['launches'].get('z'),
                        lambda s: len(s['lanes']),
                        lambda s: s['control'].update(launches={}),
                        lambda s: s['stage_timing']['history'][0],
                        lambda s: s['events'].append({'x': 1}),
                        lambda s: copy.deepcopy(s['control']),
                        lambda s: s.setdefault('throughput', {}).setdefault('jobs', {})]
            for attempt in attempts:
                with self.assertRaises(Rejected):
                    with self.reg.transaction(sections=[('leases',)]) as s:
                        s['queue_pressure'] = {'changed': True}
                        attempt(s)
                self.assertEqual(self.reg.snapshot(), before)
            with self.assertRaises(Rejected):
                with self.reg.transaction(sections=[('events',)], append=[('stage_timing', 'history')]) as s:
                    s['stage_timing']['history'][-1]
            with self.assertRaises(Rejected):
                with self.reg.transaction(sections=[('no_such',)]): pass
        self.both(check)

    def test_history_tail_crosses_chunk_boundaries(self):
        def check():
            before = self.reg.snapshot()
            with self.reg.transaction(sections=[], append=[('stage_timing', 'history')]) as s:
                self.assertEqual(len(s['stage_timing']['history']), len(before['stage_timing']['history']))
                s['stage_timing']['history'].extend({'n': i} for i in range(300))
            self.assertEqual(self.reg.snapshot()['stage_timing']['history'],
                             before['stage_timing']['history'] + [{'n': i} for i in range(300)])
            with self.reg.transaction(sections=[('stage_timing', 'history')]) as s:
                s['stage_timing']['history'] = s['stage_timing']['history'][256:]
            self.assertEqual(self.reg.snapshot()['stage_timing']['history'],
                             (before['stage_timing']['history'] + [{'n': i} for i in range(300)])[256:])
        self.both(check)

    def test_sectioned_snapshot_seals_other_partitions(self):
        def check():
            state = self.reg.snapshot(sections=[('lanes',)])
            self.assertEqual(state['lanes'], self.reg.snapshot()['lanes'])
            self.assertEqual(state['queue_pressure'], {'at': 1})
            with self.assertRaises(Rejected): state['control']['launches'].values()
            with self.assertRaises(Rejected): list(state['events'])
        self.both(check)

    def test_meta_only_write_touches_only_the_meta_row(self):
        migrate(self.reg)
        db = sqlite3.connect(self.reg.path)
        try:
            db.execute('CREATE TABLE changes (section TEXT, key TEXT)')
            for kind in ('UPDATE', 'INSERT', 'DELETE'):
                row = 'old' if kind == 'DELETE' else 'new'
                db.execute(f'CREATE TRIGGER audit_{kind} AFTER {kind} ON registry_documents BEGIN '
                           f'INSERT INTO changes VALUES ({row}.section,{row}.key); END')
            db.commit()
            with self.reg.transaction(sections=()) as s: s['queue_pressure'] = {'at': 5}
            self.assertEqual(db.execute('SELECT * FROM changes').fetchall(), [('', '')])
            db.execute('DELETE FROM changes'); db.commit()
            with self.reg.transaction(sections=(), append=[('events',)]) as s: self.reg.event(s, 'y', None)
            self.assertEqual(sorted(db.execute('SELECT * FROM changes').fetchall()), [('', ''), ('["events"]', '128')])
            with self.reg.transaction(sections=(), append=[('events',)]) as s:
                for _ in range(5): self.reg.event(s, 'fill', None)  # Exactly two full chunks now.
            db.execute('DELETE FROM changes'); db.commit()
            with self.reg.transaction(sections=(), append=[('events',)]) as s: self.reg.event(s, 'next', None)
            self.assertEqual(sorted(db.execute('SELECT * FROM changes').fetchall()), [('', ''), ('["events"]', '256')])
            self.assertEqual(len(self.reg.snapshot()['events']), 257)
            db.execute('DELETE FROM changes'); db.commit()
            with self.reg.transaction(sections=[('lanes',)]) as s: s['lanes']['z']['x'] = 1
            self.assertEqual(db.execute('SELECT * FROM changes').fetchall(), [('["lanes"]', 'z')])
        finally: db.close()

    def test_concurrent_sectioned_and_full_writers_keep_every_update(self):
        migrate(self.reg)
        errors = []
        def work(sectioned):
            try:
                reg = Registry(self.reg.path, self.root)
                for _ in range(8):
                    if sectioned:
                        with reg.transaction(sections=[('lanes',)], append=[('events',)]) as s:
                            s['lanes']['z']['n'] = s['lanes']['z'].get('n', 0) + 1; reg.event(s, 'n', 'z')
                    else:
                        with reg.transaction() as s:
                            s['lanes']['a']['n'] = s['lanes']['a'].get('n', 0) + 1; reg.event(s, 'n', 'a')
            except Exception as exc: errors.append(exc)
        threads = [threading.Thread(target=work, args=(i % 2 == 0,)) for i in range(4)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(errors, [])
        state = self.reg.snapshot()
        self.assertEqual((state['lanes']['z']['n'], state['lanes']['a']['n'], len(state['events'])), (16, 16, 282))


class BusyRetryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.reg = Registry(self.root/'output/registry.sqlite3', self.root)
        self.reg.init()

    def test_retry_backs_off_with_jitter_then_reports_a_clear_error(self):
        calls, sleeps = [], []
        def locked():
            calls.append(1); raise sqlite3.OperationalError('database is locked')
        with self.assertRaises(storage.RegistryBusy) as caught:
            storage.retry(locked, 'writer lock', attempts=3, sleep=sleeps.append, jitter=lambda: .5)
        self.assertEqual(len(calls), 3); self.assertEqual(sleeps, [.2, .4])
        self.assertIn('Registry busy: writer lock still locked after 3 attempts', str(caught.exception))
        self.assertIn('nothing was committed', str(caught.exception))
        with self.assertRaises(sqlite3.OperationalError) as other:
            storage.retry(lambda: (_ for _ in ()).throw(sqlite3.OperationalError('no such table')), 'x', sleep=sleeps.append)
        self.assertNotIsInstance(other.exception, storage.RegistryBusy)

    def test_busy_budget_stays_within_the_former_single_wait(self):
        self.assertLessEqual(storage.budget(), storage.BUSY_BUDGET)
        sleeps = []
        with self.assertRaises(storage.RegistryBusy):
            storage.retry(lambda: (_ for _ in ()).throw(sqlite3.OperationalError('database is locked')), 'x',
                          sleep=sleeps.append, jitter=lambda: 1.0)
        self.assertEqual(len(sleeps), storage.BUSY_ATTEMPTS - 1)
        self.assertAlmostEqual(storage.BUSY_ATTEMPTS * storage.BUSY_TIMEOUT + sum(sleeps), storage.budget())
        db = sqlite3.connect(self.reg.path, timeout=storage.BUSY_TIMEOUT)  # The per-attempt SQLite wait.
        self.assertEqual(db.execute('PRAGMA busy_timeout').fetchone()[0], storage.BUSY_TIMEOUT * 1000); db.close()

    def test_transaction_waits_out_a_held_writer_and_fails_clearly_after_budget(self):
        holder = sqlite3.connect(self.reg.path, check_same_thread=False); holder.execute('BEGIN IMMEDIATE')
        with patch.object(storage, 'BUSY_TIMEOUT', .05), patch.object(storage, 'BUSY_ATTEMPTS', 2):
            with self.assertRaises(storage.RegistryBusy):
                with self.reg.transaction() as s: s['x'] = 1
            timer = threading.Timer(.3, holder.rollback); timer.start()
            with patch.object(storage, 'BUSY_ATTEMPTS', 30):
                with self.reg.transaction(sections=()) as s: s['x'] = 2
            timer.join()
        holder.close()
        self.assertEqual(self.reg.snapshot()['x'], 2)

    def test_workflow_cli_reports_busy_with_its_own_exit_code(self):
        import importlib.util, io, contextlib, json
        spec = importlib.util.spec_from_file_location('cli', Path(__file__).resolve().parents[1]/'scripts/pikmin2_workflow.py')
        cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
        request = self.root/'output/request.json'; request.write_text('{"key": "x", "generation": 1}')
        holder = sqlite3.connect(self.reg.path); holder.execute('BEGIN EXCLUSIVE')
        err = io.StringIO()
        try:
            with patch.object(storage, 'BUSY_TIMEOUT', .05), patch.object(storage, 'BUSY_ATTEMPTS', 2), \
                    contextlib.redirect_stderr(err):
                code = cli.main(['--root', str(self.root), '--db', str(self.reg.path), 'heartbeat', '--request', str(request)])
        finally: holder.rollback(); holder.close()
        self.assertEqual(code, 75)
        self.assertTrue(json.loads(err.getvalue())['busy'])


if __name__ == '__main__': unittest.main()
