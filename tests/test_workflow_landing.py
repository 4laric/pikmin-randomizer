"""Integration receipts must contain the reviewed bytes; temporary git repos only."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from tests import test_pikmin2_workflow as workflow_fixtures
from tests.landing_git import commit, git, head, source
from workflow import landing, landing_audit
from workflow.handoff import Rejected, digest


def fixture():
    item = workflow_fixtures.WorkflowTests('test_handoff_review_and_integration_metrics'); item.setUp()
    return item


class Base(unittest.TestCase):
    def setUp(self):
        self.f = f = fixture(); self.addCleanup(f.doCleanups)
        self.root, self.reg = f.root, f.reg

    def integrating(self, files, reviews=(), key='one'):
        """Lane with a one-commit source range and a validated handoff, checkpointed to integrating."""
        self.f.running(key)
        lane = source(self.reg, key, files)
        data = self.f.handoff(lane)
        data['changed_files'] = sorted(set(data['changed_files']) | {r['file'] for r in reviews})
        data['shared_reviews'] = [dict(file=r['file'], reason='Shared hook', issue_url='https://x/186',
                                       status='approved', evidence=['log']) for r in reviews]
        lane = self.reg.submit_handoff(key, 1, lane['revision'], self.f.save_handoff(data))
        return self.reg.checkpoint(key, 1, lane['revision'], {'state': 'integrating'})

    def record(self, commit_sha, **extra):
        return dict(root_commit=commit_sha, validation_path=str(self.f.log), validation_sha256=digest(self.f.log), **extra)

    def integrate(self, lane, record, lander=None):
        return self.reg.integrate(lane['lane'], lane['generation'], lane['revision'], record, lander)

    def landing_branch(self, files):
        """A commit on a separate line from the lane base (a cherry-pick, not a merge)."""
        lane = self.reg.snapshot()['lanes']['one']
        git(self.root, 'checkout', '-q', '-b', 'land-' + os.urandom(3).hex(), lane['root']['base'])
        return commit(self.root, files, 'land')

    def port(self, file, reviewed, landed, repo='root'):
        evidence = self.root / 'output/port.md'; evidence.write_text('interdiff reviewed by lander\n')
        return dict(repo=repo, file=file, reviewed_blob=reviewed, landed_blob=landed,
                    interdiff_sha256=hashlib.sha256(b'interdiff').hexdigest(), reason='Adapted to moved line',
                    evidence=dict(path=str(evidence), sha256=digest(evidence)))

    def blob(self, sha, path):
        return git(self.root, 'rev-parse', f'{sha}:{path}')


class LandingTests(Base):
    def test_identical_blob_on_another_line_is_proven(self):
        lane = self.integrating({'workflow/one.py': 'X = 1\n', 'workflow/old.py': 'gone\n'})
        landed = self.landing_branch({'workflow/one.py': 'X = 1\n', 'workflow/old.py': 'gone\n'})
        done = self.integrate(lane, self.record(landed), dict(lane='one', generation=1))
        proof = done['integration_landing']
        self.assertEqual((proof['kind'], proof['root']['head_is_ancestor'], proof['root']['line_check']),
                         ('landed', False, 'undeclared'))
        self.assertEqual({f[0]: f[4] for f in proof['root']['files']}, {'workflow/one.py': 'blob', 'workflow/old.py': 'blob'})
        self.assertIsNone(proof['native'])
        self.assertEqual(done['integration'], self.record(landed))  # The submitted receipt stays exact.

    def test_ancestor_is_proven_even_after_later_edits(self):
        lane = self.integrating({'workflow/one.py': 'X = 1\n'})
        later = commit(self.root, {'workflow/one.py': 'X = 2\n'})
        proof = self.integrate(lane, self.record(later))['integration_landing']
        self.assertTrue(proof['root']['head_is_ancestor'])
        self.assertEqual(proof['root']['files'][0][4], 'ancestor')
        self.assertIsNone(proof['lander'])

    def test_missing_absent_different_and_deleted_files_refuse_per_file(self):
        commit(self.root, {'workflow/doomed.py': 'old\n'})
        lane = self.integrating({'workflow/one.py': 'X = 1\n', 'workflow/two.py': 'Y\n', 'workflow/doomed.py': None})
        with self.assertRaisesRegex(Rejected, 'root_commit b{40} does not exist'):
            self.integrate(lane, self.record('b' * 40))
        landed = self.landing_branch({'workflow/one.py': 'X = 99\n'})
        with self.assertRaises(Rejected) as caught:
            self.integrate(lane, self.record(landed))
        text = str(caught.exception)
        self.assertIn('root:workflow/one.py differs', text)
        self.assertIn('root:workflow/two.py is absent', text)
        self.assertIn('root:workflow/doomed.py was deleted by the lane but is present', text)
        self.assertIn('declare a port', text)
        self.assertEqual(self.reg.snapshot()['lanes']['one']['state'], 'integrating')

    def test_non_shared_port_is_stored_with_the_lander(self):
        lane = self.integrating({'workflow/one.py': 'X = 1\n', 'workflow/two.py': 'Y\n'})
        landed = self.landing_branch({'workflow/one.py': 'X = 1  # adapted\n', 'workflow/two.py': 'Y\n'})
        port = self.port('workflow/one.py', self.blob(lane['root']['head'], 'workflow/one.py'),
                         self.blob(landed, 'workflow/one.py'))
        self.f.register('two', worker='two')
        with self.assertRaisesRegex(Rejected, 'port blobs differ from git'):
            self.integrate(lane, self.record(landed, ports=[dict(port, landed_blob='c' * 40)]))
        with self.assertRaisesRegex(Rejected, 'Stale ownership generation'):
            self.integrate(lane, self.record(landed, ports=[port]), dict(lane='two', generation=7))
        with self.assertRaisesRegex(Rejected, 'needs exactly'):
            self.integrate(lane, self.record(landed, ports=[dict(port, extra=1)]))
        done = self.integrate(lane, self.record(landed, ports=[port]), dict(lane='two', generation=1))
        proof = done['integration_landing']
        self.assertEqual(proof['ports'], [port])
        self.assertEqual(proof['lander'], dict(lane='two', generation=1))
        self.assertEqual({f[0]: f[4] for f in proof['root']['files']}, {'workflow/one.py': 'port', 'workflow/two.py': 'blob'})

    def test_needless_or_foreign_ports_refuse(self):
        lane = self.integrating({'workflow/one.py': 'X = 1\n'})
        blob = self.blob(lane['root']['head'], 'workflow/one.py')
        with self.assertRaisesRegex(Rejected, 'needs no port'):
            self.integrate(lane, self.record(lane['root']['head'], ports=[self.port('workflow/one.py', blob, blob)]))
        with self.assertRaisesRegex(Rejected, 'did not change: root:workflow/other.py'):
            self.integrate(lane, self.record(lane['root']['head'], ports=[self.port('workflow/other.py', blob, blob)]))

    def test_shared_review_and_engine_ports_require_a_landing_review(self):
        files = {'workflow/one.py': 'X = 1\n', 'workflow/shared.py': 'HOOK = 1\n', 'engine/pc_port/hook.cpp': 'int a;\n'}
        lane = self.integrating(files, reviews=[{'file': 'workflow/shared.py'}])
        landed = self.landing_branch({'workflow/one.py': 'X = 1\n', 'workflow/shared.py': 'HOOK = 2\n',
                                      'engine/pc_port/hook.cpp': 'int b;\n'})
        for name in ('workflow/shared.py', 'engine/pc_port/hook.cpp'):
            port = self.port(name, self.blob(lane['root']['head'], name), self.blob(landed, name))
            with self.assertRaisesRegex(Rejected, 'shared-file port requires a landing review: root:' + name):
                self.integrate(lane, self.record(landed, ports=[port]))
        self.assertTrue(landing.shared_file('native', 'pc_port/pc_p2_cave.cpp', []))
        self.assertTrue(landing.shared_file('native', 'x.cpp', ['native/x.cpp']))
        self.assertFalse(landing.shared_file('root', 'workflow/x.py', []))

    def test_already_landed_is_explicit_and_blob_checked(self):
        self.f.running()
        with self.reg.transaction() as state:  # No lane changes: base == head.
            base = commit(self.root, {'workflow/one.py': 'X = 1\n'})
            state['lanes']['one']['root'] = dict(base=base, head=base, commits=[], dirty='', worktree=str(self.root))
        lane = self.reg.snapshot()['lanes']['one']
        lane = self.reg.submit_handoff('one', 1, lane['revision'], self.f.save_handoff(self.f.handoff(lane)))
        lane = self.reg.checkpoint('one', 1, lane['revision'], {'state': 'integrating'})
        with self.assertRaisesRegex(Rejected, "record kind 'already_landed'"):
            self.integrate(lane, self.record(base))
        with self.assertRaisesRegex(Rejected, 'kind must be'):
            self.integrate(lane, self.record(base, kind='noop'))
        proof = self.integrate(lane, self.record(base, kind='already_landed'))['integration_landing']
        self.assertEqual((proof['kind'], proof['files_changed']), ('already_landed', 0))

    def test_already_landed_names_the_commit_that_contains_the_bytes(self):
        lane = self.integrating({'workflow/one.py': 'X = 1\n'})
        earlier = self.landing_branch({'workflow/one.py': 'X = 1\n'})
        elsewhere = self.landing_branch({'workflow/unrelated.py': 'Z\n'})  # Like #721/#724: files absent.
        with self.assertRaisesRegex(Rejected, 'workflow/one.py is absent'):
            self.integrate(lane, self.record(elsewhere, kind='already_landed'))
        blob = self.blob(lane['root']['head'], 'workflow/one.py')
        with self.assertRaisesRegex(Rejected, 'cannot carry ports'):
            self.integrate(lane, self.record(earlier, kind='already_landed',
                                             ports=[self.port('workflow/one.py', blob, blob)]))
        proof = self.integrate(lane, self.record(earlier, kind='already_landed'))['integration_landing']
        self.assertEqual((proof['kind'], proof['root']['commit']), ('already_landed', earlier))

    def declare(self, ref, repo='.'):
        config = self.root / landing.CONFIG; config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(json.dumps(dict(output='output/workflow/controller',
                                          integration_lines=dict(root=dict(repo=repo, ref=ref)))))

    def test_declared_line_must_reach_the_receipt_commit(self):
        lane = self.integrating({'workflow/one.py': 'X = 1\n'})
        line = self.landing_branch({'workflow/one.py': 'X = 1\n'})
        git(self.root, 'branch', '-f', 'maintained', line)
        self.declare('maintained')
        with self.assertRaisesRegex(Rejected, 'not reachable from declared line maintained'):
            self.integrate(lane, self.record(lane['root']['head']))
        proof = self.integrate(lane, self.record(line))['integration_landing']
        self.assertEqual(proof['root']['line_check'], dict(ref='maintained', tip=line, reachable=True))

    def test_declared_line_shape_and_unknown_ref_refuse(self):
        lane = self.integrating({'workflow/one.py': 'X = 1\n'})
        self.declare('no-such-line')
        with self.assertRaisesRegex(Rejected, 'Landing git call failed \\(rev-parse'):
            self.integrate(lane, self.record(lane['root']['head']))
        self.declare('--all')
        with self.assertRaisesRegex(Rejected, 'integration_lines must map'):
            self.integrate(lane, self.record(lane['root']['head']))
        (self.root / landing.CONFIG).write_text('{broken')
        with self.assertRaisesRegex(Rejected, 'config unreadable'):
            self.integrate(lane, self.record(lane['root']['head']))

    def native_lane(self):
        self.f.running()
        source(self.reg, 'one', {'workflow/one.py': 'X = 1\n'})
        lane = source(self.reg, 'one', {'pc_port/pc_p2_x.cpp': 'int x;\n'}, repo='native')
        data = self.f.handoff(lane)
        lane = self.reg.submit_handoff('one', 1, lane['revision'], self.f.save_handoff(data))
        return self.reg.checkpoint('one', 1, lane['revision'], {'state': 'integrating'})

    def native_record(self, root_sha, native_sha):
        export = self.root / 'output/export.log'; export.write_text('exported\n')
        return self.record(root_sha, native_commit=native_sha, native_dirty='', export_evidence=str(export),
                           export_sha256=digest(export))

    def test_native_commit_must_exist_in_the_native_repo(self):
        lane = self.native_lane()
        with self.assertRaisesRegex(Rejected, 'native_commit .* does not exist in .*native'):
            self.integrate(lane, self.native_record(lane['root']['head'], lane['root']['head']))
        proof = self.integrate(lane, self.native_record(lane['root']['head'], lane['native']['head']))['integration_landing']
        self.assertEqual(proof['native']['files'][0][0], 'pc_port/pc_p2_x.cpp')

    def test_nested_non_repository_never_falls_back_to_the_parent(self):
        commit(self.root, {'workflow/base.py': '\n'})
        (self.root / 'native').mkdir()
        with self.assertRaisesRegex(Rejected, 'not a git working tree root'):
            landing.repository(self.root, 'native', {})

    def test_proof_runs_outside_the_lock_and_rechecks_pins(self):
        lane = self.integrating({'workflow/one.py': 'X = 1\n'})
        real = landing.prove
        def moving(*args, **kwargs):
            proof = real(*args, **kwargs)
            with self.reg.transaction() as state:
                state['lanes']['one']['root'] = dict(state['lanes']['one']['root'], dirty='M x')
            return proof
        with patch.object(landing, 'prove', moving):
            with self.assertRaisesRegex(Rejected, 'changed while proving'):
                self.integrate(lane, self.record(lane['root']['head']))

    def test_git_failures_and_timeouts_refuse(self):
        def slow(*args, **kwargs):
            raise subprocess.TimeoutExpired(args[0], landing.TIMEOUT)
        with patch.object(landing.subprocess, 'run', slow):
            with self.assertRaisesRegex(Rejected, 'Landing git call failed'):
                landing.git(self.root, 'rev-parse', 'HEAD')
        with self.assertRaisesRegex(Rejected, 'Landing git call failed'):
            landing.git(self.root, 'rev-parse', '--verify', 'nothing-here')

    def test_receipt_replay_still_checks_ancestry_then_proves(self):
        lane = self.integrating({'workflow/one.py': 'X = 1\n'})
        landed = self.landing_branch({'workflow/one.py': 'X = 1\n'})
        with self.assertRaisesRegex(Rejected, 'Git verification failed'):
            self.reg.receipt('one', 1, self.record(landed), str(self.root))
        record = self.record(lane['root']['head'])
        done = self.reg.receipt('one', 1, record, str(self.root), lander=dict(lane='one', generation=1))
        self.assertEqual(done['integration_landing']['lander'], dict(lane='one', generation=1))
        self.assertEqual(self.reg.receipt('one', 1, record, str(self.root))['integration'], record)


class AuditTests(Base):
    def test_audit_reports_mismatches_and_never_writes(self):
        lane = self.integrating({'workflow/one.py': 'X = 1\n'})
        self.integrate(lane, self.record(lane['root']['head']))
        lane = self.integrating({'workflow/two.py': 'Y\n'}, key='two')
        with self.reg.transaction() as state:  # Legacy receipts: written before the proof existed.
            state['lanes']['two'].update(state='done', integration=self.record(state['lanes']['two']['root']['base']))
            state['lanes']['three'] = dict(copy.deepcopy(state['lanes']['two']), lane='three',
                                           integration=self.record('d' * 40))
        before = (self.f.db.read_bytes(), self.f.db.stat().st_mtime_ns, len(self.reg.snapshot()['events']))
        out = self.root / 'audit.json'
        code = landing_audit.main(['--root', str(self.root), '--db', str(self.f.db), '--out', str(out)])
        self.assertEqual(code, 1)
        self.assertEqual(before, (self.f.db.read_bytes(), self.f.db.stat().st_mtime_ns, len(self.reg.snapshot()['events'])))
        report = json.loads(out.read_text())
        self.assertEqual(report['summary'], dict(absent=1, clean=1, mismatched=2, missing_commit=1, no_changes=0, receipts=3))
        found = {r['lane']: [p['kind'] for p in r['problems']] for r in report['receipts']}
        self.assertEqual(found, dict(one=[], two=['absent'], three=['missing_commit']))
        self.assertEqual(landing_audit.main(['--root', str(self.root), '--db', str(self.f.db), '--lane', 'one']), 0)

    def test_audit_runs_through_the_pinned_entry(self):
        entry = Path(__file__).resolve().parents[1] / 'scripts/workflow_module.py'
        p = subprocess.run([sys.executable, str(entry), 'landing_audit', '--root', str(self.root), '--db', str(self.f.db)],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)['summary'], {})


class IntegratorGuardTests(Base):
    def controller(self):
        from workflow.controller import Controller
        return Controller(self.reg, dict(output='output/workflow/controller', lanes={}, models=['p/m']))

    def test_rendered_integrator_config_denies_destructive_git(self):
        from workflow.managed_config import INTEGRATOR_GIT_DENY, integrator_guard, load_config
        config = self.root / 'output/opencode.json'
        config.write_bytes(b'{\n  "$schema": "https://opencode.ai/config.json",}')  # OpenCode's own insertion into {}.
        with self.reg.transaction() as state:
            state.setdefault('throughput', {})['workstreams'] = {'species': dict(owner_lane='integrator')}
        item = dict(lane='integrator', reason='manual')
        rendered = self.controller().integrator_config(item, str(config))
        bash = rendered['permission']['bash']
        self.assertEqual(set(bash), set(INTEGRATOR_GIT_DENY))  # Unmatched commands keep OpenCode's default.
        for pattern in INTEGRATOR_GIT_DENY:
            self.assertEqual(bash[pattern], 'deny')
        text = ' '.join(bash)
        for command in ('merge*-X*ours', 'merge*-X*theirs', 'merge*-s*ours', 'reset*--hard', 'clean*-*f',
                        'checkout -- ', 'push*--force'):
            self.assertIn(command, text)
        self.assertIsNone(self.controller().integrator_config(dict(lane='producer', reason='manual'), str(config)))
        demand = self.controller().integrator_config(dict(lane='producer', reason='integration-demand:x'),
                                                     dict(permission=dict(bash={'*': 'allow', 'git push *': 'deny'})))
        self.assertEqual(list(demand['permission']['bash'])[:2], ['*', 'git push *'])
        self.assertEqual(integrator_guard(dict(permission={'*': 'deny'})), dict(permission={'*': 'deny'}))
        self.assertEqual(integrator_guard(dict(permission='ask'))['permission']['bash']['*'], 'ask')
        self.assertIsNone(integrator_guard(dict(permission=dict(bash=3))))
        broken = self.root / 'output/broken.json'; broken.write_text('{nope')
        self.assertIsNone(load_config(broken))
        with self.assertRaisesRegex(Rejected, 'cannot carry the destructive-git guard'):
            self.controller().integrator_config(item, str(broken))


class ReleaseRefTests(unittest.TestCase):
    def test_ref_without_the_release_test_list_leaves_no_worktree(self):
        from tests.test_workflow_provenance import PrepareReleaseTests
        f = PrepareReleaseTests('test_clean_worktree_path_ref_resolves_to_its_commit'); f.setUp(); self.addCleanup(f.doCleanups)
        git(f.root, 'rm', '-q', 'tests/workflow_release_tests.txt'); git(f.root, 'commit', '-qm', 'not a release')
        with self.assertRaisesRegex(Rejected, 'has no tests/workflow_release_tests.txt'):
            f.prepare(head(f.root))
        self.assertFalse((f.root / 'output/workflow/release').exists())
        self.assertEqual(f.calls, [])
        with self.assertRaisesRegex(Rejected, 'repository-relative'):
            f.prepare(f.sha, tests='../x.txt')
        self.assertTrue(f.prepare(f.sha)['created'])


if __name__ == '__main__':
    unittest.main()
