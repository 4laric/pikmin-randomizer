"""Delivery classes, suggest, promotion batches: temporary repos with fake off-disk and local-path remotes."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
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
        self.assertEqual(report['lanes'], {'done': 6, 'done-no-code': 1, 'receipts': 5, 'archived': 1})
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
        classes = {k: v['root']['cls'] for k, v in shipping.reconcile(self.root, self.state, 1000)['receipts'].items()}
        self.assertEqual((classes['shipped'], classes['pushed'], classes['online']), ('shipped', 'pushed', 'undeclared'))

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
        if divergence.get('conflicts') is not None:
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
        if root['between'].get('conflicts') is not None:
            self.assertEqual(root['between']['conflicts'], 1)
        native = report['repos']['native']
        self.assertIsNone(native['default_target'])  # fork is a local path with no default branch: not guessed.
        self.assertEqual(native['unpushed'], 1)
        self.assertEqual(report['snippet'], dict(
            integration_lines=dict(root=dict(repo='.', ref='line'), native=dict(repo='native', ref='nline')),
            release_target=dict(root=dict(repo='.', ref='origin/main'))))
        self.assertFalse((self.root / 'output/workflow/controller/config.json').exists())  # Never written.
        text = inspect.text('delivery-suggest', report)
        self.assertIn('"integration_lines"', text); self.assertIn('nothing was written', text)


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
        self.assertIn('under output/', err.getvalue())

    def test_machine_item_for_undeclared_release_target(self):
        items = inspect.machine(dict(lanes={}, control={}), 0, cfg={})
        self.assertIn('release_target_undeclared', [i['kind'] for i in items])
        items = inspect.machine(dict(lanes={}, control={}), 0, cfg=dict(release_target=dict(root=dict(repo='.', ref='m'))))
        self.assertNotIn('release_target_undeclared', [i['kind'] for i in items])


if __name__ == '__main__':
    unittest.main()
