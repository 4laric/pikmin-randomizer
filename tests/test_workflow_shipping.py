"""Delivery classes, suggest, promotion batches: temporary repos with fake off-disk and local-path remotes."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tests.landing_git import commit, git
from workflow import inspect, review_packet, shipping
from workflow.dashboard import render_delivery
from workflow.handoff import Rejected
from workflow.registry import Registry


def done(key, root_commit=None, at=100, native_commit=None, base=None, head=None, **extra):
    lane = dict(lane=key, state='done', generation=1, integrated_at=at, created_at=1,
                root=dict(base=base or '0' * 40, head=head or '0' * 40, worktree='.'), native=None)
    if root_commit:
        lane['integration'] = dict(root_commit=root_commit, native_commit=native_commit)
    if native_commit:
        lane['native'] = dict(base='0' * 40, head='0' * 40, worktree='native')
    return dict(lane, **extra)


def write_tree_supported():
    """git merge-tree --write-tree arrived in git 2.38."""
    found = re.search(r'(\d+)\.(\d+)', subprocess.run(['git', '--version'], capture_output=True, text=True).stdout)
    return bool(found) and (int(found.group(1)), int(found.group(2))) >= (2, 38)


class Repos(unittest.TestCase):
    """main: base -> S; line: S -> P (pushed as origin/line) -> L; side: S -> O. origin is https (off-disk)."""
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = root = Path(temp.name).resolve() / 'root'
        commit(root, {'engine/src/a.cpp': 'a0\n', 'tools/x.py': 'x0\n', 'shared.txt': 'base\n'}, 'base')
        git(root, 'branch', '-M', 'main')
        self.S = commit(root, {'engine/src/s.cpp': 's\n'}, 'shipped')
        git(root, 'checkout', '-q', '-b', 'side')
        self.O = commit(root, {'side.txt': 'o\n', 'shared.txt': 'side\n'}, 'off line')
        git(root, 'checkout', '-q', '-b', 'line', 'main')
        self.P = commit(root, {'engine/src/a.cpp': 'a1\n', 'tools/x.py': 'x1\n', 'shared.txt': 'line\n'}, 'pushed')
        self.L = commit(root, {'engine/include/new.h': 'h\n', 'docs/new.md': 'd\n'}, 'on line')
        git(root, 'remote', 'add', 'origin', 'https://example.invalid/root.git')
        git(root, 'update-ref', 'refs/remotes/origin/main', self.S)
        git(root, 'update-ref', 'refs/remotes/origin/line', self.P)
        git(root, 'symbolic-ref', 'refs/remotes/origin/HEAD', 'refs/remotes/origin/main')
        native = root / 'native'
        self.N = commit(native, {'pc_port/n.cpp': 'n\n'}, 'native')
        git(native, 'branch', '-M', 'nline')
        git(native, 'remote', 'add', 'fork', str(root.parent / 'fork-on-disk'))  # A local path: never pushed.
        git(native, 'update-ref', 'refs/remotes/fork/nline', self.N)
        self.state = dict(lanes={
            'shipped': done('shipped', self.S, 100),
            'pushed': done('pushed', self.P, 200, base=self.S, head=self.P),
            'online': done('online', self.L, 300, native_commit=self.N, base=self.P, head=self.L, archived=[dict(run='r1')]),
            'offline': done('offline', self.O, 50),
            'missing': done('missing', 'f' * 40, 60),
            'nocode': done('nocode'),
            'unreceipted': done('unreceipted', base=self.S, head=self.P),  # Code, but no integration receipt.
            'busy': dict(done('busy', self.L), state='running')})

    def configure(self, **values):
        path = self.root / 'output/workflow/controller/config.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(values))

    def declare(self):
        self.configure(integration_lines=dict(root=dict(repo='.', ref='line'), native=dict(repo='native', ref='nline')),
                       release_target=dict(root=dict(repo='.', ref='origin/main')))

    def refs_and_objects(self):
        def listing(repo):
            objects = sorted(str(p.relative_to(repo)) for p in (repo / '.git/objects').rglob('*') if p.is_file())
            return git(repo, 'for-each-ref', '--format=%(refname) %(objectname) %(symref)'), objects
        return listing(self.root), listing(self.root / 'native')


class ReconcileTests(Repos):
    def test_every_class_per_repository(self):
        self.declare()
        report = shipping.reconcile(self.root, self.state, 1000)
        root, native = report['repos']['root'], report['repos']['native']
        self.assertEqual(root['counts'], {'shipped': 1, 'pushed': 1, 'integrated-on-line': 1, 'off-line': 1, 'missing': 1})
        self.assertEqual({k: report['receipts'][k]['root']['cls'] for k in ('shipped', 'pushed', 'online', 'offline', 'missing')},
                         {'shipped': 'shipped', 'pushed': 'pushed', 'online': 'integrated-on-line', 'offline': 'off-line',
                          'missing': 'missing'})
        self.assertEqual(report['lanes'], {'done': 7, 'done-no-code': 1, 'done-unreceipted': 1, 'receipts': 5, 'archived': 1,
                                           'unreceipted_lanes': ['unreceipted']})
        self.assertTrue(report['receipts']['online']['archived'])  # History archived by registry_archive: still classified.
        self.assertEqual((root['unpushed']['count'], root['unpushed']['oldest']['lane']), (2, 'offline'))
        self.assertEqual(sorted(root['unpushed']['lanes']), ['offline', 'online'])
        self.assertEqual((root['oldest_unshipped']['lane'], root['oldest_unshipped']['cls']), ('offline', 'off-line'))
        self.assertEqual(root['oldest_unshipped']['age_seconds'], 950)
        self.assertEqual((root['divergence']['ahead'], root['divergence']['behind']), (2, 0))
        self.assertEqual(root['line']['unpushed_commits'], 1)  # L is on the line but not on origin.
        # Native: no release target declared, and fork is a local path.
        self.assertEqual(native['counts'], {'undeclared': 1})
        self.assertEqual((native['target'], native['oldest_unshipped']), ('undeclared', 'undeclared'))
        self.assertFalse(native['remote']['off_disk'])
        self.assertEqual(native['unpushed']['count'], 1)

    def test_local_path_remote_never_counts_as_pushed(self):
        self.declare()
        git(self.root, 'remote', 'set-url', 'origin', str(self.root.parent / 'origin-on-disk'))
        report = shipping.reconcile(self.root, self.state, 1000)
        classes = {k: v['root']['cls'] for k, v in report['receipts'].items()}
        self.assertEqual(classes['pushed'], 'integrated-on-line')
        self.assertEqual(classes['shipped'], 'shipped')  # Shipped is ancestry to the target, not the remote's location.
        self.assertEqual(report['repos']['root']['unpushed']['count'], 4)
        for url, expected in (('https://github.com/a/b.git', True), ('git@github.com:a/b.git', True), ('ssh://h/x', True),
                              ('C:\\Users\\a\\repo', False), ('/srv/repo', False), ('file:///srv/repo', False),
                              ('\\\\server\\share\\repo', False), ('../repo', False), (None, False)):
            self.assertEqual(shipping.off_disk(url), expected, url)

    def test_undeclared_config_is_its_own_class(self):
        report = shipping.reconcile(self.root, self.state, 1000)
        root = report['repos']['root']
        self.assertEqual(root['counts'], {'undeclared': 4, 'missing': 1})
        self.assertEqual((root['line'], root['target'], root['oldest_unshipped']), ('undeclared', 'undeclared', 'undeclared'))
        self.assertEqual(root['unpushed']['count'], 2)  # Pushed facts need no config.
        self.configure(release_target=dict(root=dict(repo='.', ref='origin/main')))
        report = shipping.reconcile(self.root, self.state, 1000)
        classes = {k: v['root']['cls'] for k, v in report['receipts'].items()}
        self.assertEqual((classes['shipped'], classes['pushed'], classes['online']), ('shipped', 'pushed', 'undeclared'))
        # The target proves 'offline' (the oldest) unshipped even though no line is declared to name its class.
        oldest = report['repos']['root']['oldest_unshipped']
        self.assertEqual((oldest['lane'], oldest['cls'], oldest['age_seconds']), ('offline', 'undeclared', 950))
        few = dict(lanes={k: self.state['lanes'][k] for k in ('shipped', 'offline', 'online')})
        self.assertEqual(shipping.reconcile(self.root, few, 1000)['repos']['root']['oldest_unshipped']['lane'], 'offline')
        # A done lane with code but no receipt is not no-code.
        self.assertEqual(shipping.receipts(dict(lanes=dict(
            a=done('a'), b=done('b', head='1' * 40), c=dict(done('c'), root=dict(base='0' * 40, head='0' * 40, commits=['x'])),
            d=dict(done('d'), root=None, native=dict(base='2' * 40, head='3' * 40)))))[1:], (['a'], ['b', 'c', 'd']))

    def test_native_side_without_a_native_commit(self):
        self.declare()
        state = dict(lanes=dict(
            nochange=dict(done('nochange', self.S, 10), native=dict(base='1' * 40, head='1' * 40, commits=[], worktree='native')),
            changed=dict(done('changed', self.S, 20), native=dict(base='1' * 40, head='2' * 40, worktree='native')),
            empty=dict(done('empty', self.S, 30), native={}, integration=dict(root_commit=self.S, native_commit=''))))
        self.assertEqual([sorted(s) for _, _, s in shipping.receipts(state)[0]], [['root'], ['native', 'root'], ['root']])
        report = shipping.reconcile(self.root, state, 1000)
        self.assertEqual(report['repos']['native']['counts'], {'no-native-receipt': 1})  # Never 'missing'.
        self.assertEqual(report['receipts']['changed']['native'], dict(commit=None, cls='no-native-receipt', pushed=None))

    def test_malformed_or_unresolvable_declarations_refuse(self):
        self.configure(release_target=dict(root=dict(repo='.', ref='--upload-pack=x')))
        with self.assertRaises(Rejected): shipping.targets(self.root)
        self.configure(release_target=dict(root=dict(repo='.', ref='origin/nowhere')))
        report = shipping.reconcile(self.root, self.state, 1000)
        self.assertIn('not a commit', report['repos']['root']['error'])
        self.assertEqual(report['repos']['root']['counts'], {'unverifiable': 5})

    def test_caps_mark_truncated_rather_than_guess(self):
        self.declare()
        with patch.object(shipping, 'WALK', 2):
            report = shipping.reconcile(self.root, self.state, 1000)
        self.assertEqual(report['repos']['root']['counts'], {'truncated': 4, 'missing': 1})
        with patch.object(shipping, 'COMMITS', 1):
            report = shipping.reconcile(self.root, self.state, 1000)
        self.assertEqual(report['repos']['root']['truncated'], 3)
        self.assertEqual(report['repos']['root']['counts'].get('truncated'), 3)

    def test_merge_tree_conflicts_and_skip(self):
        self.declare()
        git(self.root, 'update-ref', 'refs/remotes/origin/main', self.O)  # Target now diverges on shared.txt.
        divergence = shipping.reconcile(self.root, self.state, 1000)['repos']['root']['divergence']
        self.assertEqual((divergence['ahead'], divergence['behind']), (2, 1))
        if not write_tree_supported(): self.skipTest('git merge-tree --write-tree needs git 2.38')
        self.assertEqual((divergence['conflicts'], divergence['conflict_paths']), (1, ['shared.txt']))
        real = shipping._git
        def old_git(repo, *args, **kw):
            if args[:1] == ('merge-tree',): raise Rejected('unknown option --write-tree')
            return real(repo, *args, **kw)
        with patch.object(shipping, '_git', old_git):
            divergence = shipping.reconcile(self.root, self.state, 1000)['repos']['root']['divergence']
        self.assertIsNone(divergence['conflicts'])
        self.assertIn('write-tree', divergence['conflicts_skipped'])

    def test_dashboard_caches_per_tip(self):
        self.declare()
        clock, calls, cache = [0.0], [], {}
        real = shipping.gather
        def counted(*a, **k):
            calls.append(1); return real(*a, **k)
        with patch.object(shipping, 'gather', counted):
            first = shipping.dashboard(self.root, self.state, 1000, clock=lambda: clock[0], cache=cache)
            with patch.object(shipping, 'tips_key', side_effect=AssertionError('tips re-read too soon')):
                shipping.dashboard(self.root, self.state, 1010, clock=lambda: clock[0] + 5, cache=cache)
            clock[0] = shipping.TIP_SECONDS + 1
            again = shipping.dashboard(self.root, self.state, 1020, clock=lambda: clock[0], cache=cache)
            self.assertEqual(len(calls), 1)  # Tips unchanged: no recompute.
            self.assertEqual(again['repos']['root']['counts'], first['repos']['root']['counts'])
            self.assertNotIn('receipts', again)
            more = commit(self.root, {'more.txt': 'm\n'})
            clock[0] = 2 * shipping.TIP_SECONDS + 2
            shipping.dashboard(self.root, self.state, 1030, clock=lambda: clock[0], cache=cache)
            self.assertEqual(len(calls), 2)  # The line tip moved.
            state = dict(lanes=dict(self.state['lanes'], extra=done('extra', more, 400)))
            shipping.dashboard(self.root, state, 1040, clock=lambda: clock[0], cache=cache)
            self.assertEqual(len(calls), 3)  # The receipt set changed.
        html = render_delivery(first)
        self.assertIn('unpushed', html); self.assertIn('off-line 1', html)
        self.assertIn('unavailable', render_delivery(dict(error='<boom>')))
        self.assertNotIn('<boom>', render_delivery(dict(error='<boom>')))
        self.assertIn('1 done-unreceipted', html); self.assertIn('unreceipted</p>', html)

    def test_dashboard_retries_a_failed_side_after_tip_seconds(self):
        self.declare()
        clock, cache, real, failures = [0.0], {}, shipping.present, [1]
        def flaky(*a, **k):
            if failures[0]:
                failures[0] -= 1
                raise OSError('WinError 1455')
            return real(*a, **k)
        with patch.object(shipping, 'present', flaky):
            first = shipping.dashboard(self.root, self.state, 1000, clock=lambda: clock[0], cache=cache)
            self.assertEqual(first['repos']['root']['counts'], {'unverifiable': 5})
            clock[0] = shipping.TIP_SECONDS + 1  # Tips unchanged, but the failed side is not reused.
            again = shipping.dashboard(self.root, self.state, 1100, clock=lambda: clock[0], cache=cache)
        self.assertEqual(again['repos']['root']['counts'].get('shipped'), 1)
        self.assertIsNone(again['repos']['root']['error'])


class SuggestTests(Repos):
    def test_suggest_counts_refs_divergence_and_prints_a_snippet(self):
        report = shipping.suggest(self.root, self.state)
        root = report['repos']['root']
        self.assertEqual({b['ref']: b['receipts'] for b in root['branches']}, {'line': 3, 'side': 2, 'main': 1})
        self.assertEqual({b['ref']: b['receipts'] for b in root['remote_refs']}, {'origin/line': 2, 'origin/main': 1})
        self.assertEqual((root['missing'], root['on_no_ref'], root['unpushed']), (1, 0, 2))
        self.assertEqual(root['default_target']['ref'], 'origin/main')
        top = root['candidates'][0]
        self.assertEqual((top['ref'], top['worktree'], top['vs_target']['ahead'], top['vs_target']['behind']), ('line', '.', 2, 0))
        self.assertEqual((root['between']['ours'], root['between']['theirs']), ('line', 'side'))
        if write_tree_supported():
            self.assertEqual((root['between']['conflicts'], root['between']['conflict_paths']), (1, ['shared.txt']))
        native = report['repos']['native']
        self.assertIsNone(native['default_target'])  # fork is a local path with no default branch: not guessed.
        self.assertEqual(native['unpushed'], 1)
        self.assertEqual(report['snippet'], dict(
            integration_lines=dict(root=dict(repo='.', ref='line'), native=dict(repo='native', ref='nline')),
            release_target=dict(root=dict(repo='.', ref='origin/main'))))
        self.assertFalse((self.root / 'output/workflow/controller/config.json').exists())  # Never written.
        self.assertEqual(report['snippet_warnings'], ['root: 1 receipt commits on other candidate lines are not on line: '
                                                      'declared as is they classify off-line; converge the lines first'])
        text = inspect.text('delivery-suggest', report)
        self.assertIn('"integration_lines"', text); self.assertIn('nothing was written', text)
        self.assertIn('WARNING: root: 1 receipt commits', text)

    def test_suggest_warns_when_the_top_lines_pair_different_waves(self):
        lanes = dict(self.state['lanes'], online=done('online', self.O, 300, native_commit=self.N))
        report = shipping.suggest(self.root, dict(lanes=lanes), conflicts=False)
        self.assertEqual(report['snippet']['integration_lines']['root']['ref'], 'line')
        self.assertIn('only 0 of 1 lanes whose native receipt is on nline have their root receipt on line',
                      report['snippet_warnings'][-1])


class PlanTests(Repos):
    def test_batches_split_by_path_class_with_receipts_and_packet_stub(self):
        self.declare()
        data = shipping.plan(self.root, self.state, 'root')
        self.assertEqual((data['line']['tip'], data['target']['tip'], data['merge_base']), (self.L, self.S, self.S))
        self.assertEqual([b['kind'] for b in data['batches']], ['modify-shared', 'modify', 'additive'])
        shared, other, additive = data['batches']
        self.assertEqual([f['path'] for f in shared['files']], ['engine/src/a.cpp'])
        self.assertEqual([(r['lane'], r['partial']) for r in shared['receipts']], [('pushed', True)])
        self.assertEqual([f['path'] for f in other['files']], ['shared.txt', 'tools/x.py'])
        self.assertEqual([r['lane'] for r in other['receipts']], ['pushed'])
        self.assertEqual([f['path'] for f in additive['files']], ['docs/new.md', 'engine/include/new.h'])
        self.assertEqual([r['lane'] for r in additive['receipts']], ['online'])
        self.assertEqual(data['receipts']['carried'], 2)
        self.assertEqual((data['receipts']['shipped'], data['receipts']['off_line'], data['receipts']['missing']), (1, 1, 1))
        inputs = {**shared['packet_inputs'], **additive['packet_inputs']}
        self.assertEqual(sorted(v['path'] for v in inputs.values()),
                         ['engine/include/new.h', 'engine/include/new.h', 'engine/src/a.cpp', 'engine/src/a.cpp'])
        self.assertTrue(all(v['commit'] == self.L for v in inputs.values() if v['role'] == 'candidate'))
        self.assertTrue(any(v.get('optional') for v in additive['packet_inputs'].values()))
        packet = dict(format='review-packet-v1', schema='promotion-root', issue=186, consumers=['c'], landers=['i'],
                      inputs=inputs, items=[dict(id='engine', gate='g', missing_change='m', integration_tokens=['t'],
                                                  maintained=[k for k, v in inputs.items() if v['role'] == 'maintained'])])
        review_packet.validate(packet)  # The stub drops into a review-packet-v1 packet unchanged.
        self.assertIn('## root-modify-shared-01', shipping.markdown(data))
        small = shipping.plan(self.root, self.state, 'root', limits={'additive': (1, 40)})
        self.assertEqual([b['kind'] for b in small['batches']].count('additive'), 2)

    def test_undeclared_refuses_unless_refs_are_named(self):
        with self.assertRaisesRegex(Rejected, 'integration_lines.root is undeclared'):
            shipping.plan(self.root, self.state, 'root')
        data = shipping.plan(self.root, self.state, 'root', line='line', target='origin/main')
        self.assertEqual(data['source'], dict(line='argument', target='argument'))
        with self.assertRaises(Rejected):
            shipping.plan(self.root, self.state, 'root', line='line', target='--output=x')

    def test_receipts_over_the_cap_are_not_evaluated_rather_than_missing(self):
        self.declare()
        with patch.object(shipping, 'COMMITS', 1):
            data = shipping.plan(self.root, self.state, 'root')
        self.assertTrue(data['truncated']['receipts'])
        self.assertEqual((data['receipts']['missing'], data['receipts']['not_evaluated'], data['receipts']['off_line']), (1, 3, 0))
        self.assertIn('receipts (3 receipt commits not evaluated)', shipping.markdown(data))

    def test_packet_stub_names_a_line_review_packet_can_verify(self):
        self.declare()
        data = shipping.plan(self.root, self.state, 'root')  # Target origin/main: a remote-tracking ref.
        batch = data['batches'][0]
        lines = {json.dumps(v['line'], sort_keys=True) for v in batch['packet_inputs'].values() if v['role'] == 'maintained'}
        self.assertEqual(lines, {json.dumps(dict(repo='output/promotion/root-modify-shared-01',
                                                 ref='promote/root-modify-shared-01'), sort_keys=True)})
        self.assertIn('origin/main is not a branch checked out', batch['maintained_line_required'])
        self.assertIn('maintained line required', shipping.markdown(data))
        line = json.loads(lines.pop())
        git(self.root, 'worktree', 'add', '-q', '-b', line['ref'], str(self.root / line['repo']), self.S)
        self.assertEqual(review_packet.line_repo(self.root, line)[1:], (self.S, []))
        # A target branch checked out in its declared repo is itself the maintained line.
        git(self.root, 'worktree', 'add', '-q', str(self.root / 'output/main'), 'main')
        self.configure(integration_lines=dict(root=dict(repo='.', ref='line')),
                       release_target=dict(root=dict(repo='output/main', ref='main')))
        batch = shipping.plan(self.root, self.state, 'root')['batches'][0]
        self.assertNotIn('maintained_line_required', batch)
        line = next(v['line'] for v in batch['packet_inputs'].values() if v['role'] == 'maintained')
        self.assertEqual(line, dict(repo='output/main', ref='main'))
        self.assertEqual(review_packet.line_repo(self.root, line)[1:], (self.S, []))

    def test_plan_output_stays_below_output_and_off_existing_files(self):
        self.declare()
        data = shipping.plan(self.root, self.state, 'root')
        config = self.root / 'output/workflow/controller/config.json'
        before = config.read_text()
        for out in ('output', 'output/workflow/controller/config', 'output/workflow/controller/config.json',
                    'output/workflow/throughput', 'plan', '../elsewhere/plan'):
            with self.assertRaises(Rejected, msg=out):
                shipping.write_plan(self.root, data, out)
        self.assertEqual(config.read_text(), before)
        self.assertFalse((self.root / 'output.json').exists() or (self.root / 'output.md').exists())
        written = shipping.write_plan(self.root, data, 'output/plans/p')
        self.assertEqual([Path(p).name for p in written], ['p.json', 'p.md'])
        with self.assertRaisesRegex(Rejected, 'exists'):
            shipping.write_plan(self.root, data, 'output/plans/p.json')
        self.assertEqual(shipping.write_plan(self.root, data, 'output/plans/p', force=True), written)


class ReadOnlyTests(Repos):
    def test_inspect_verbs_leave_registry_and_refs_unchanged(self):
        self.declare()
        reg = Registry(self.root / 'output/workflow/registry.sqlite3', self.root); reg.init()
        with reg.transaction() as state:
            state['lanes'].update(self.state['lanes'])
        before = hashlib.sha256(reg.path.read_bytes()).hexdigest(), self.refs_and_objects()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            for verb in (['delivery'], ['delivery', '--json'], ['delivery-suggest'], ['delivery-suggest', '--json'],
                         ['promotion-plan', 'root'], ['promotion-plan', 'root', '--json', '--out', 'output/plans/p1'],
                         ['promotion-plan', 'root', '--line', 'side', '--target', 'origin/main']):
                self.assertEqual(inspect.main(['--root', str(self.root), *verb]), 0, verb)
        self.assertEqual((hashlib.sha256(reg.path.read_bytes()).hexdigest(), self.refs_and_objects()), before)
        self.assertIn('integrated-on-line 1', out.getvalue())
        self.assertTrue((self.root / 'output/plans/p1.json').is_file() and (self.root / 'output/plans/p1.md').is_file())
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(inspect.main(['--root', str(self.root), 'promotion-plan', 'root', '--out', 'plan-outside']), 2)
        self.assertIn('below output/', err.getvalue())

    def test_machine_item_for_undeclared_release_target(self):
        items = inspect.machine(dict(lanes={}, control={}), 0, cfg={})
        self.assertIn('release_target_undeclared', [i['kind'] for i in items])
        items = inspect.machine(dict(lanes={}, control={}), 0, cfg=dict(release_target=dict(root=dict(repo='.', ref='m'))))
        self.assertNotIn('release_target_undeclared', [i['kind'] for i in items])
        kinds = lambda **kw: [i['kind'] for i in inspect.machine(dict(lanes={}, control={}), 0, **kw)]
        self.assertIn('release_target_malformed', kinds(cfg=dict(release_target='origin/main', integration_lines='x')))
        # With root, the canonical file decides (as workflow.shipping reads it), not the startup cfg.
        self.configure(release_target=dict(root=dict(repo='.', ref='origin/main')))
        self.assertNotIn('release_target_undeclared', kinds(cfg={}, root=self.root))
        self.configure(release_target='origin/main')
        self.assertIn('release_target_malformed', kinds(cfg=dict(release_target=dict(root=dict(repo='.', ref='m'))), root=self.root))
        self.configure()
        self.assertIn('release_target_undeclared', kinds(cfg=dict(release_target=dict(root=dict(repo='.', ref='m'))), root=self.root))


if __name__ == '__main__':
    unittest.main()
