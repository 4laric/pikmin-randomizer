import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import subprocess
import sys
import tempfile
import unittest

from tests import test_pikmin2_controller as fixtures
from workflow import blockers, inspect
from workflow.autofill import clustered_blockers
from workflow.consumer_wakeup import explain, tick
from workflow.control import fingerprint
from workflow.producer_contract import acceptance_lint

CHECKOUT = Path(__file__).resolve().parents[1]


def lane(key, state='blocked', issue=1, deps=(), **extra):
    return dict(dict(lane=key, state=state, issue=issue, dependencies=list(deps), generation=1, worker_id='w-' + key,
                     process={'pid': -1}, created_at=1, root=None, native=None), **extra)


def world(*lanes, **extra):
    return dict(dict(lanes={l['lane']: l for l in lanes}, leases={}, queue={}, control=dict(launches={}, notices={}),
                     support_actions={}, delivery_contracts={}), **extra)


class ReadOnlyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.f = fixtures.ControllerTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        from workflow import storage
        storage.migrate(self.f.reg)
        self.f.reg.finish('consumer', 1, 'blocked', 'Needs provider', self.f.ev, ['provider', '#186 review'])
        db = sqlite3.connect(self.f.reg.path); db.execute('PRAGMA journal_mode=WAL'); db.close()
        self.copy = Path(temp.name) / 'copy.sqlite3'
        src, dst = sqlite3.connect(self.f.reg.path), sqlite3.connect(self.copy)
        src.backup(dst); dst.close(); src.close()

    def test_verbs_read_a_read_only_wal_copy_without_transaction_paths(self):
        db = sqlite3.connect(self.copy)
        self.assertEqual(db.execute('PRAGMA journal_mode').fetchone()[0], 'wal'); db.close()
        os.chmod(self.copy, stat.S_IREAD); self.addCleanup(os.chmod, self.copy, stat.S_IREAD | stat.S_IWRITE)
        before = hashlib.sha256(self.copy.read_bytes()).hexdigest()
        script = ('import sys, json; from workflow import inspect\n'
                  'for verb in (["stuck"], ["needs-you"], ["lane", "consumer"], ["launches", "consumer"], '
                  '["assignment", "consumer"], ["config"]):\n'
                  '    assert inspect.main(["--db", sys.argv[1], "--root", sys.argv[2], *verb, "--json"]) == 0, verb\n'
                  'bad = sorted(m for m in ("workflow.registry", "workflow.write_gate") if m in sys.modules)\n'
                  'print(json.dumps(bad))')
        result = subprocess.run([sys.executable, '-c', script, str(self.copy), str(self.f.root)], cwd=CHECKOUT,
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout.strip().splitlines()[-1]), [])
        self.assertEqual(hashlib.sha256(self.copy.read_bytes()).hexdigest(), before)

    def test_source_has_no_write_path(self):
        text = (CHECKOUT / 'workflow/inspect.py').read_text(encoding='utf-8')
        for word in ('.transaction(', 'import Registry', 'from .registry', 'write_gate', 'BEGIN IMMEDIATE', 'selected('):
            self.assertNotIn(word, text)
        with self.assertRaises(inspect.Rejected):
            inspect.View(self.f.root).transaction()

    def test_sections_are_sealed_and_workspace_checked(self):
        state = inspect.read(self.copy, [('lanes',)])
        self.assertIn('consumer', state['lanes'])
        with self.assertRaises(Exception):
            state['control']['launches'].values()
        with self.assertRaises(inspect.Rejected):
            inspect.read(self.copy, [('lanes',)], root=self.f.root / 'elsewhere')


class StuckTests(unittest.TestCase):
    def test_refs_normalize_issue_forms_and_resolve_owners(self):
        state = world(lane('a', deps=['#186 shared-hook review (bridge)', '#50 producer landing']),
                      lane('b', issue=2, deps=['4laric/pikmin-randomizer#186', 'producer-lane: needs its commits']),
                      lane('producer-lane', state='done', issue=50),
                      lane('c', issue=3, deps=['#77', 'captain safety #632']))
        self.assertEqual(blockers.refs(state, 'a', blockers.owners(state)), ['issue:186', 'issue:50'])
        self.assertEqual(blockers.refs(state, 'b', blockers.owners(state)), ['issue:186', 'lane:producer-lane'])
        grouped = {g['ref']: g for g in blockers.groups(state)['groups']}
        self.assertEqual((grouped['issue:186']['count'], grouped['issue:186']['owner_state']), (2, 'decision'))
        self.assertEqual((grouped['issue:50']['owner'], grouped['issue:50']['owner_state']), ('producer-lane', 'done_unlanded'))
        self.assertIn('Integrator', grouped['issue:50']['next_action'])
        self.assertEqual(grouped['issue:77']['owner_state'], 'missing')
        self.assertNotIn('issue:632', grouped)

    def test_blocked_owner_chain_roots_and_cycles(self):
        state = world(lane('x', issue=10, deps=['#11 landing']), lane('y', issue=11, deps=['x must land first']),
                      lane('z', issue=12, deps=['#11']), lane('w', issue=13, deps=['#11']))
        result = blockers.groups(state)
        self.assertEqual(result['cycles'], [['x', 'y', 'x']])
        group = next(g for g in result['groups'] if g['ref'] == 'issue:11')
        self.assertEqual((group['count'], group['owner'], group['owner_state']), (3, 'y', 'blocked'))
        self.assertIn('circular', group['next_action'])

    def test_stuck_puts_needs_you_first_and_lists_parked_lanes(self):
        state = world(lane('a', deps=['#186'], parked=dict(reason='r', waiting_for='a new receipt'), wake_after=5000,
                           stall_streak=2, acceptance=['Guard landed with #186 review']),
                      lane('b', issue=2, deps=['#186']))
        report = inspect.stuck(state, 1000, cfg={})
        self.assertEqual(list(report)[:3], ['at', 'needs_you', 'machine'])
        self.assertEqual(report['groups'][0]['label'], '#186')
        self.assertEqual(report['parked'][0]['lane'], 'a')
        self.assertEqual(report['parked'][0]['refs'], ['#186'])
        self.assertEqual(report['catch22'][0]['lane'], 'a')
        self.assertIn('integration_lines_undeclared', [m['kind'] for m in report['machine']])
        text = inspect.text('stuck', report)
        self.assertLess(text.index('Needs you'), text.index('Blocked lanes'))
        small = inspect.bounded(report, groups=1, lanes=1)
        self.assertEqual((len(small['groups']), small['omitted']['groups']), (1, report['total_groups'] - 1))


class NeedsYouTests(unittest.TestCase):
    def ask(self, key, kind, required, at):
        return dict(action='external', key=key, at=at, reason='r', details=dict(owner='user', kind=kind, required=required))

    def test_asks_deduplicate_per_lane_and_kind_with_age_and_downstream(self):
        actions = {'1': self.ask('a', 'user_decision', 'Authorize rebasing onto the wave line', 100),
                   '2': self.ask('a', 'user_decision', 'Coordinator decision: authorize the rebase', 200),
                   '3': self.ask('a', 'user_decision', 'Authorize rebasing onto the wave line', 300),
                   '4': self.ask('a', 'user_asset', 'Stock chal0 default.gen', 300),
                   '5': self.ask('gone', 'user_asset', 'Retail white_* models', 300),
                   '6': self.ask('t', 'user_asset', 'Functional mingw64 g++: cc1plus exits 1', 400)}
        notices = {str(i): dict(lane='s', kind='unsupervised_lane', status='pending', at=10 + i,
                                detail=dict(error='Stopped lane has no controller launch config')) for i in range(2)}
        requests = {'r': dict(status='exhausted', scope='enemies-2', lanes=['c'], needs_human=dict(at=50, reason='Offered twice'))}
        state = world(lane('a', issue=5), lane('b', issue=6, deps=['#5']), lane('c', issue=7, deps=['b first']),
                      lane('gone', state='done', issue=8), lane('t', state='done', issue=9), lane('s', state='ready', issue=10),
                      support_actions=actions, throughput_runtime=dict(autofill=dict(prerequisite_requests=requests)))
        state['control']['notices'] = notices
        items = inspect.needs_you(state, 1000)
        decision = next(i for i in items if i['kind'] == 'user_decision')
        self.assertEqual((decision['asked'], decision['distinct_wordings'], decision['age_seconds']), (3, 2, 900))
        self.assertEqual(decision['downstream_lanes'], ['b', 'c'])
        self.assertEqual(decision['what'], 'Authorize rebasing onto the wave line')
        self.assertEqual(sorted(i['kind'] for i in items), ['prerequisite_needs_human', 'toolchain', 'unsupervised_lane',
                                                            'user_asset', 'user_decision'])
        self.assertEqual(next(i for i in items if i['kind'] == 'unsupervised_lane')['count'], 2)
        self.assertEqual(next(i for i in items if i['kind'] == 'toolchain')['lanes'], ['t'])


class ClusterTests(unittest.TestCase):
    def test_live_shaped_dependencies_cluster_on_structured_refs(self):
        state = world(
            lane('muki-rows', issue=748, deps=['Explicit #186 landing decision for the serialized wiring (issue #186 OPEN)']),
            lane('houdai', issue=735, deps=['Integrator: #748 MUKI rows landing + #730 ext for the full wiring follow-on']),
            lane('redblue', issue=744, deps=['#748 native MUKI stage rows landing (muki-rows running gen 3, no handoff)']),
            lane('damagumo', issue=740, deps=['muki-rows (#748): unblock MUKI rows', '4laric/pikmin-randomizer#186']),
            lane('bomb', issue=573, deps=['#186 shared-hook review (detonation driver path, dynamic-bridge source 93)']),
            lane('ext', issue=730, state='done', created_at=5),
            lane('nari', issue=537, deps=['pc_bbft.cpp boot serialization (follow-on blocked on #730 ext landing)']),
            lane('kusachi-a', issue=780, deps=['sustained live squad (diagnosis #787 has no engine change)']),
            lane('kusachi-b', issue=781, deps=['staged producer; extinction per diagnosis #787']),
            lane('diag', issue=787, state='done', integration=dict(root_commit='a' * 40)))
        clusters = {c['signature']: c for c in clustered_blockers(state)}
        self.assertEqual(clusters['#186']['count'], 3)
        self.assertEqual((clusters['#748']['count'], clusters['#748']['owner_state']), (3, 'blocked'))
        self.assertIn('Unblock muki-rows', clusters['#748']['next_action'])
        self.assertEqual((clusters['#730']['owner'], clusters['#730']['owner_state']), ('ext', 'done_unlanded'))
        self.assertEqual(clusters['#787']['lanes'], ['kusachi-a', 'kusachi-b'])
        self.assertFalse(any(c['covered'] for c in clusters.values()))


class PublicationTests(unittest.TestCase):
    def test_staffing_reports_the_assignment_worker_count_and_both_names(self):
        from workflow.analytics import staffing_recommendations
        state = dict(lanes={'x': lane('x', state='blocked', worker_id='a')}, throughput=dict(
            workers={'a': dict(worker_id='a', roles=['implementation'], capabilities=[]),
                     'b': dict(worker_id='b', roles=['implementation'], capabilities=[])},
            assignments={}, jobs={'j': dict(id='j', lane='y', role='implementation', capabilities=[], status='queued')}))
        result = staffing_recommendations(state, 1000, 60, process_probe=lambda p: 'dead', available={'a'})
        self.assertEqual((result['available_workers'], result['idle_workers']), (1, 1))
        self.assertEqual(result['workers_matching_ready_work'], result['compatible_idle_workers'])

    def test_dashboard_renders_needs_you_first_and_escaped(self):
        from workflow.dashboard import render_dashboard
        stuck = inspect.bounded(inspect.stuck(world(lane('a', deps=['#186 <b>'])), 1000, cfg={}))
        stuck['needs_you'] = [dict(kind='user_asset', lane='a', what='<script>', age_seconds=90, next='Supply it')]
        html = render_dashboard(dict(at=1000, stuck=stuck))
        self.assertLess(html.index('Needs you'), html.index('Monster families admitted'))
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>', html.split('<script type="module">')[0])


class LintTests(unittest.TestCase):
    def test_foreign_owner_criteria_are_flagged_and_negations_are_not(self):
        found = acceptance_lint(['Explicit #186 wiring decision', 'Guard landed with #186 review', 'no #186 decision needed',
                                 'Consumes the landed #649 fixture', 'Patch landed on the wave line', 'Maintained export done',
                                 'Hashed landing report', 'Integrator lands the rows', 'Handoff names no maintained export'])
        self.assertEqual([(f['index'], f['move_to']) for f in found],
                         [(0, 'shared_reviews'), (1, 'shared_reviews'), (4, 'remaining_work'), (5, 'remaining_work'),
                          (7, 'remaining_work')])
        self.assertEqual(acceptance_lint(None), [])


class NoticeLegacyTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ControllerTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.reg = self.f.reg

    def test_a_resolved_exact_identity_row_stays_resolved(self):
        detail = dict(path='r.json', error='Conflicting integration receipt')
        exact = fingerprint(['consumer', 'receipt_rejected', detail])
        with self.reg.transaction() as s:
            self.reg.control(s)['notices'][exact] = dict(id=exact, lane='consumer', kind='receipt_rejected', detail=detail,
                                                         status='resolved', at=1, decision='d')
        self.assertEqual(self.reg.notice('consumer', 'receipt_rejected', detail), exact)
        notices = self.reg.control_status()['notices']
        self.assertEqual([(k, n['status']) for k, n in notices.items()], [(exact, 'resolved')])
        other = self.reg.notice('consumer', 'receipt_rejected', dict(detail, path='r2.json'))
        self.assertNotEqual(other, exact)
        self.assertEqual(self.reg.control_status()['notices'][other]['status'], 'pending')


class WakeExplanationTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ControllerTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.r, self.c = self.f.reg, self.f.controller
        self.r.finish('consumer', 1, 'blocked', 'Missing source', self.f.ev, ['#1'])
        with self.r.transaction() as s:
            s['lanes']['provider'].update(state='done', integrated_at=1001, integration=dict(root_commit='b' * 40,
                native_commit=None, validation_path=self.f.ev['path'], validation_sha256=self.f.ev['sha256']))
            s['lanes']['helper-slice'] = dict(copy.deepcopy(s['lanes']['provider']), lane='helper-slice', state='running',
                                              worker_id='consumer', integration=None, issue=99)
        self.f.now += 1000

    def explain(self):
        state = self.r.snapshot()
        return explain(self.r, state, 'consumer', self.c.config['lanes'], lambda k: True, self.c.config)

    def test_busy_worker_is_explained_reserved_and_woken_when_free(self):
        from workflow.autofill import _workers
        self.r.register_pool_worker('consumer', ['implementation'], ['python'], 'test')
        with self.r.transaction() as s:
            lane = s['lanes']['consumer']
            lane['capacity_parked'] = dict(generation=lane['generation'], at=1, evidence=self.f.ev)
        found = self.explain()
        self.assertEqual((found['gate'], found['occupant'], found['reserved']), ('worker_busy', 'helper-slice', False))
        tick(self.c)
        self.assertFalse(self.r.control_status()['launches'])
        self.assertFalse([n for n in self.r.control_status()['notices'].values()
                          if n['kind'] == 'consumer_prerequisite_wakeup_blocked'])
        row = self.r.snapshot()['handoff_resume_reservations']['consumer']
        self.assertEqual((row['worker_id'], row['reason']), ('consumer', found['token']))
        self.assertTrue(self.explain()['reserved'])
        with self.r.transaction() as s: s['lanes']['helper-slice']['state'] = 'done'
        self.assertNotIn('consumer', {l['worker_id'] for l in _workers(self.r, self.r.snapshot())})  # Held for the wake.
        self.assertEqual(self.explain()['gate'], 'wake')
        tick(self.c)
        launch = next(iter(self.r.control_status()['launches'].values()))
        self.assertEqual(launch['reason'], found['token'])
        self.assertEqual(self.explain()['gate'], 'launch_in_flight')

    def test_inspect_lane_reports_the_gate_and_skipped_producers(self):
        with self.r.transaction() as s: s['lanes']['helper-slice']['state'] = 'done'
        with self.r.transaction() as s: s['lanes']['provider']['integration']['validation_sha256'] = 'bad'
        state = inspect.read(self.r.path, inspect.LANE, self.f.root)
        view = inspect.View(self.f.root, probe=self.r.probe, clock=self.r.clock)
        data = inspect.lane(state, 'consumer', view, self.c.config)
        self.assertEqual(data['wake']['gate'], 'no_new_receipt')
        self.assertIn('evidence', data['wake']['skipped']['provider'])
        self.assertIn('Prerequisite wake: no_new_receipt', inspect.text('lane', data))
        self.assertFalse(self.r.control_status()['notices'])  # Explaining records nothing.


if __name__ == '__main__':
    unittest.main()
