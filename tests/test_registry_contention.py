import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tests import test_pikmin2_controller as controller_fixtures
from tests.test_build_capacity import BuildCapacityTests
from workflow.analytics import _build_utilization
from workflow.registry import Registry
from workflow.storage import migrate
from workflow.wakeup import EventWaiter


class WakeupUnderDocumentsTests(unittest.TestCase):
    def test_waiter_notices_events_after_migration_and_from_sectioned_writes(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        root = Path(temp.name).resolve()
        reg = Registry(root/'output/registry.sqlite3', root); reg.init()
        with reg.transaction() as s: reg.event(s, 'before', None)
        migrate(reg)
        waiter = EventWaiter(reg.path)
        cursor = waiter.token()
        reg.status()
        self.assertEqual(waiter.wait(0, cursor)['reason'], 'timeout')
        with reg.transaction() as s: reg.event(s, 'full', None)
        self.assertEqual(waiter.wait(0, cursor)['reason'], 'changed')
        cursor = waiter.token()
        with reg.transaction(sections=(), append=[('events',)]) as s: reg.event(s, 'sectioned', None)
        self.assertEqual(waiter.wait(0, cursor)['reason'], 'changed')


class LeaseAccountingTests(unittest.TestCase):
    def test_recovery_drop_emits_lease_reaped_and_utilization_is_clamped(self):
        f = BuildCapacityTests(); f.setUp(); self.addCleanup(f.doCleanups)
        with f.reg.transaction() as s:
            s['leases']['build:x'] = dict(lane='one', generation=1, token='t', process={'health': 'dead'}, resource='build:x')
            s['leases']['shared-runtime'] = dict(lane='owner', generation=1, token='u', process={'health': 'alive'})
            f.reg.drop_leases(s, 'one', 'recovery')
        state = f.reg.snapshot()
        self.assertEqual(list(state['leases']), ['shared-runtime'])
        reaped = [e for e in state['events'] if e['kind'] == 'lease_reaped']
        self.assertEqual([(e['lane'], e['resource'], e['reason']) for e in reaped], [('one', 'build:x', 'recovery')])

    def test_legacy_silent_drops_close_at_launch_bound_and_never_exceed_100_percent(self):
        state = dict(settings={'max_heavy_builds': 1}, leases={}, actions={'r': {'kind': 'recover'}}, events=[
            dict(kind='lease_acquired', at=0, resource='build:a', lane='one'),
            dict(kind='lease_acquired', at=0, resource='build:b', lane='two'),
            dict(kind='launch_bound', at=10, lane='one'),
            dict(kind='action_completed', at=20, lane='two', action='r')])
        result = _build_utilization(state, 100, 0)
        self.assertEqual(result['leased_seconds'], 30)
        state['events'] = [dict(kind='lease_acquired', at=0, resource='build:%d' % i, lane='x') for i in range(5)]
        self.assertEqual(_build_utilization(state, 100, 0)['utilization_percent'], 100)

    def test_bind_launch_reports_the_leases_it_drops(self):
        f = controller_fixtures.ControllerTests(); f.setUp(); self.addCleanup(f.doCleanups)
        item = f.reg.plan_launch('consumer', 'test', 'Resume', f.config['models'])
        with f.reg.transaction() as s:
            s['lanes']['consumer']['process'] = {'pid': -1, 'created': 'old'}
            s['leases']['build:old'] = dict(lane='consumer', generation=1, token='t', process={'pid': -2})
        f.reg.bind_launch(item['id'], f.identity)
        state = f.reg.snapshot()
        self.assertEqual(state['leases'], {})
        self.assertIn(('lease_reaped', 'build:old', 'launch_bound'),
                      [(e['kind'], e.get('resource'), e.get('reason')) for e in state['events']])


class RamSampleOrderingTests(unittest.TestCase):
    def test_ram_is_sampled_under_the_writer_and_older_samples_never_overwrite(self):
        f = BuildCapacityTests(); f.setUp(); self.addCleanup(f.doCleanups)
        f.enable()
        held = []
        def memory():
            held.append(getattr(f.reg._transaction_local, 'active', False)); return 95
        f.controller.memory = memory
        from workflow.build_capacity import update
        update(f.controller)
        self.assertIn(True, held)  # The committed sample was taken while holding the writer.
        self.assertTrue(f.reg.snapshot()['build_capacity']['paused'])
        with f.reg.transaction() as s: s['build_capacity']['observed_at'] = f.now + 50
        f.controller.memory = lambda: 10
        update(f.controller)  # Clock is older than the stored observation: no stale clear.
        policy = f.reg.snapshot()['build_capacity']
        self.assertTrue(policy['paused']); self.assertEqual(policy['ram_percent'], 95)


class ProcessInventoryTests(unittest.TestCase):
    def test_non_ascii_command_lines_decode(self):
        from workflow import terminal_cleanup
        rows = [dict(ProcessId=5, ParentProcessId=1, Name='x.exe', CommandLine='x üÅ¥ 中')]
        fake = lambda *a, **k: SimpleNamespace(returncode=0, stdout=json.dumps(rows, ensure_ascii=False).encode('utf-8'))
        with patch.object(terminal_cleanup.os, 'name', 'nt'), patch.object(terminal_cleanup.subprocess, 'CREATE_NO_WINDOW', 0, create=True):
            self.assertEqual(terminal_cleanup.process_inventory(run=fake), rows)
            bad = lambda *a, **k: SimpleNamespace(returncode=0, stdout=b'[{"CommandLine":"\x81\x8f"}]')
            self.assertEqual(terminal_cleanup.process_inventory(run=bad)[0]['CommandLine'], '��')

    @unittest.skipUnless(os.name == 'nt', 'Windows process inventory')
    def test_live_inventory_reads_a_process_with_non_ascii_arguments(self):
        from workflow.terminal_cleanup import process_inventory
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)', 'üÅÉ¥'])
        self.addCleanup(child.kill)
        rows = process_inventory()
        mine = [r for r in rows if r['ProcessId'] == child.pid]
        self.assertEqual(len(mine), 1)
        self.assertIn('üÅÉ¥', mine[0]['CommandLine'])


class DashboardPublicationTests(unittest.TestCase):
    def setUp(self):
        self.f = controller_fixtures.ControllerTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.f.config['throughput'] = dict(enabled=True)

    def test_publish_takes_one_full_snapshot_and_bounds_history(self):
        from workflow.throughput_controller import publish_status
        f = self.f
        with f.reg.transaction() as s:
            pool = s.setdefault('throughput', {})
            # Live record shapes: jobs carry only queued_at; the assignment dates completion.
            pool['jobs'] = {'old%d' % i: dict(status='completed', queued_at=f.now - 30000, assignment='a-old%d' % i)
                            for i in range(300)}
            pool['jobs'].update({'recent%d' % i: dict(status='completed', queued_at=f.now - 30000 - i,
                                                      assignment='a-recent%d' % i) for i in range(250)})
            pool['jobs']['live'] = dict(status='queued', queued_at=0)
            pool['jobs']['queued-late'] = dict(status='cancelled', queued_at=f.now - 5)
            pool['assignments'] = {'a-old%d' % i: dict(status='completed', assigned_at=f.now - 30000,
                                                      completed_at=f.now - 29000) for i in range(300)}
            pool['assignments'].update({'a-recent%d' % i: dict(status='completed', assigned_at=f.now - 30000,
                                                               completed_at=f.now - 10 - i) for i in range(250)})
            pool['costs'] = {'c%d' % i: dict(at=f.now - 30000, amount=1) for i in range(50)}
        full, probes = [], []
        original = f.reg.snapshot
        def counted(**kw):
            if not kw: full.append(1)
            return original(**kw)
        with patch.object(f.reg, 'snapshot', side_effect=counted), \
                patch.object(f.reg, 'probe', side_effect=lambda p: probes.append(p) or 'dead'):
            publish_status(f.controller)
        self.assertEqual(len(full), 1)
        report = json.loads((f.controller.base / 'throughput.json').read_text())
        jobs = report['throughput']['jobs']
        self.assertIn('live', jobs); self.assertNotIn('old0', jobs); self.assertIn('queued-late', jobs)
        self.assertEqual(len(jobs), 201); self.assertIn('recent0', jobs); self.assertNotIn('recent249', jobs)
        self.assertIn('a-recent0', report['throughput']['assignments'])
        self.assertEqual(report['throughput']['costs'], {})
        self.assertEqual(report['publication']['maps']['throughput.jobs'], dict(published=201, total=552))
        self.assertEqual(len(f.reg.snapshot()['throughput']['jobs']), 552)  # The registry keeps every record.

    def test_idle_worker_count_uses_the_registry_dead_identity_cache(self):
        from workflow import analytics
        seen = []
        real = analytics.staffing_recommendations
        def spy(*args, **kw):
            seen.append(kw.get('process_probe')); return real(*args, **kw)
        with patch.object(analytics, 'staffing_recommendations', side_effect=spy):
            self.f.reg.throughput_status()
        self.assertEqual(seen, [self.f.reg.probe])

    def test_unchanged_admission_audit_and_idle_park_do_not_write(self):
        from workflow.admission_reconciliation import audit
        from workflow.worker_capacity import park_blocked
        f = self.f
        with f.reg.transaction() as s:
            s['lanes']['consumer'].update(admission_family=7)
        admission = dict(status='observed', ids=[7])
        rows = audit(f.reg, admission, {})
        self.assertEqual([r['lane'] for r in rows], ['consumer'])
        with patch.object(f.reg, 'transaction', side_effect=AssertionError('write')), \
                patch('workflow.storage.selected', side_effect=AssertionError('write')):
            self.assertEqual(audit(f.reg, admission, {}), rows)
            self.assertEqual(park_blocked(f.reg), [])

    def test_capacity_reads_ram_scalars_from_the_meta_row(self):
        f = self.f
        f.controller.capacity()
        with patch.object(f.reg, 'control_status', side_effect=AssertionError('decodes every launch')):
            self.assertTrue(f.controller.capacity())
            f.memory = 99
            self.assertFalse(f.controller.capacity())


class StageTimingWriteTests(unittest.TestCase):
    def test_observation_appends_a_tail_and_trims_hourly(self):
        from workflow import stage_timing
        f = controller_fixtures.ControllerTests(); f.setUp(); self.addCleanup(f.doCleanups)
        migrate(f.reg)
        stage_timing.observe(f.reg)
        calls = []
        original = f.reg.transaction
        def spy(sections=None, append=()):
            calls.append((None if sections is None else tuple(sections), tuple(append))); return original(sections=sections, append=append)
        with patch.object(f.reg, 'transaction', side_effect=spy):
            for step in range(3):
                with original() as s: s['lanes']['consumer']['state'] = ('blocked', 'running', 'blocked')[step]
                f.now += 60; stage_timing.observe(f.reg)
            f.now += 3600; stage_timing.observe(f.reg)
        self.assertEqual(calls[:3], [((), (('stage_timing', 'history'),))] * 3)
        self.assertEqual(calls[3], ((('stage_timing', 'history'),), ()))
        ledger = f.reg.snapshot()['stage_timing']
        self.assertEqual(len(ledger['history']), 3); self.assertEqual(ledger['trimmed_at'], f.now)

    def test_an_older_snapshot_published_after_a_newer_one_is_refused(self):
        from workflow import stage_timing
        from workflow.handoff import Rejected
        f = controller_fixtures.ControllerTests(); f.setUp(); self.addCleanup(f.doCleanups)
        migrate(f.reg)
        with f.reg.transaction() as s: s['lanes']['consumer']['state'] = 'blocked'
        stage_timing.observe(f.reg)
        f.now += 10; stamp_a = f.reg.clock(); older = f.reg.snapshot()  # Publisher A reads first ...
        with f.reg.transaction() as s: s['lanes']['consumer']['state'] = 'running'
        f.now += 1; stamp_b = f.reg.clock(); newer = f.reg.snapshot()   # ... B reads later, decodes first.
        stage_timing.observe(f.reg, newer, now=stamp_b)
        f.now += 1  # A finishes decoding last; a post-decode clock would now exceed B's.
        stage_timing.observe(f.reg, older, now=stamp_a)
        ledger = f.reg.snapshot()['stage_timing']
        self.assertEqual(ledger['current']['consumer']['stage'], 'execution')
        self.assertEqual(ledger['current']['consumer']['observed_since'], stamp_b)
        self.assertEqual([h['stage'] for h in ledger['history'] if h['lane'] == 'consumer'], ['dependency'])
        with self.assertRaises(Rejected): stage_timing.observe(f.reg, newer)


if __name__ == '__main__': unittest.main()
