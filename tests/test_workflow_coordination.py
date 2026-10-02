"""Real private git worktrees; isolated synthetic registry, no game/host changes."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from workflow.coordination import identity
from workflow.handoff import Rejected, digest
from workflow.registry import Registry


class CoordinationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.git('init', str(self.root))
        self.git('-C', str(self.root), '-c', 'user.name=Test', '-c', 'user.email=test@example.test',
                 'commit', '--allow-empty', '-m', 'baseline')
        self.sha = self.git('-C', str(self.root), 'rev-parse', 'HEAD').strip()
        for key in ('owner', 'integration', 'other'):
            self.git('-C', str(self.root), 'worktree', 'add', '--detach', str(self.root / 'output' / key), self.sha)
        self.reg = Registry(self.root / 'output/workflow/registry.sqlite3', self.root, process_probe=lambda _: 'alive')
        self.reg.init({'max_heavy_builds': 1})
        self.log = self.root / 'output/communication.json'
        self.log.write_text(json.dumps({'issue': 1144, 'detail': 'Actual bounded integration-owner authorization and preservation'}))
        self.evidence = {'path': str(self.log), 'sha256': digest(self.log)}
        for key in ('owner', 'integration'):
            self.reg.register(self.data(key))
            self.reg.checkpoint(key, 1, 1, {'state': 'running'})
        self.chain = [self.lane('integration')['process']]

    def git(self, *args):
        p = subprocess.run(['git', *args], capture_output=True, text=True, timeout=15)
        self.assertEqual(0, p.returncode, p.stderr)
        return p.stdout

    def data(self, key):
        return dict(lane=key, owner='Codex through 4laric', worker_id=key, task_id='task-' + key,
                    issue={'owner': 1133, 'integration': 1144, 'other': 1145}[key], scope='Bounded issue scope',
                    target_level='tooling', next_action='Prepare reviewed candidate', milestone='integration',
                    owned_files=['shared.py'] if key == 'owner' else [key + '.py'], acceptance=['Editing access only'],
                    pid=os.getpid(), root=dict(base=self.sha, head=self.sha, commits=[], dirty='',
                                              worktree='output/' + key), native=None)

    def lane(self, key):
        return self.reg.snapshot()['lanes'][key]

    def request(self):
        return dict(lane='integration', generation=1, revision=self.lane('integration')['revision'], issue=1144,
                    scope='Issue 1144: preserve UX while preparing private combined candidate', authorization=self.evidence,
                    participants=[dict(lane='owner', generation=1, source=identity(self.lane('owner')), files=['shared.py'],
                                       basis='owner-communication', preservation='Preserve reviewed UX behavior; review actual candidate',
                                       evidence=[self.evidence])])

    def agree(self, request=None):
        return self.reg.coordinate(request or self.request(), chain=self.chain)

    def amend(self, row, additions=None):
        return self.reg.amend_scope('integration', 1, self.lane('integration')['revision'], [row['id']],
                                    additions or ['shared.py'], 'Reviewed issue 1144 scope', chain=self.chain)

    def test_private_overlap_preserves_producer_and_delivery_state(self):
        before = self.lane('owner')
        row = self.agree()
        amended = self.amend(row)
        self.assertIn('shared.py', amended['owned_files'])
        self.assertEqual(before, self.lane('owner'))
        self.assertEqual('running', amended['state'])
        self.assertIsNone(amended['handoff'])
        self.assertTrue(row['editing_only'])
        self.assertEqual({}, self.reg.snapshot().get('approvals', {}))
        self.assertEqual(row['id'], self.reg.check_coordination(row['id'])['id'])

    def test_ordinary_claim_stays_exclusive(self):
        d = self.data('other'); d['owned_files'] = ['shared.py']
        with self.assertRaisesRegex(Rejected, 'overlap'):
            self.reg.register(d)

    def test_one_agreement_does_not_cover_another_producer(self):
        self.reg.register(self.data('other'))
        row = self.agree()
        with self.assertRaisesRegex(Rejected, 'Uncoordinated'):
            self.amend(row, ['shared.py', 'other.py'])
        self.assertNotIn('shared.py', self.lane('integration')['owned_files'])

    def test_stale_generation_rejected(self):
        row = self.agree()
        with self.reg.transaction() as s:
            s['lanes']['owner']['generation'] += 1
        with self.assertRaisesRegex(Rejected, 'Stale coordination'):
            self.amend(row)

    def test_stale_source_record_rejected(self):
        row = self.agree()
        with self.reg.transaction() as s:
            s['lanes']['owner']['root']['dirty'] = ' M shared.py'
        with self.assertRaisesRegex(Rejected, 'Stale coordination'):
            self.reg.check_coordination(row['id'])

    def test_stale_task_process_rejected(self):
        row = self.agree()
        with self.reg.transaction() as s:
            s['lanes']['owner']['task_id'] = 'different-session'
        with self.assertRaisesRegex(Rejected, 'Stale coordination'):
            self.amend(row)

    def test_actual_consumer_head_drift_rejected(self):
        row = self.agree()
        self.git('-C', str(self.root / 'output/integration'), '-c', 'user.name=Test',
                 '-c', 'user.email=test@example.test', 'commit', '--allow-empty', '-m', 'candidate')
        with self.assertRaisesRegex(Rejected, 'HEAD differs'):
            self.amend(row)

    def test_shared_checkout_refused(self):
        source = copy.deepcopy(self.lane('owner')['root'])
        l = self.lane('integration')
        self.reg.checkpoint('integration', 1, l['revision'], {'root': source})
        with self.assertRaisesRegex(Rejected, 'Shared checkout'):
            self.agree()

    def test_maintained_checkout_refused(self):
        source = copy.deepcopy(self.lane('integration')['root']); source['worktree'] = '.'
        l = self.lane('integration')
        self.reg.checkpoint('integration', 1, l['revision'], {'root': source})
        with self.assertRaisesRegex(Rejected, 'private checkout'):
            self.agree()

    def test_readonly_canonical_producer_reference_is_allowed(self):
        source = copy.deepcopy(self.lane('owner')['root']); source['worktree'] = '.'
        l = self.lane('owner')
        self.reg.checkpoint('owner', 1, l['revision'], {'root': source})
        before = self.lane('owner')
        row = self.agree()
        self.amend(row)
        self.assertEqual(str(self.root), row['participants'][0]['checkouts']['root']['path'])
        self.assertEqual(before, self.lane('owner'))
        self.assertEqual(row['id'], self.reg.check_coordination(row['id'])['id'])

    def test_ordinary_producer_checkout_is_readonly_and_cannot_be_consumer(self):
        ordinary = self.root / 'legacy-checkout'
        self.git('clone', '--no-hardlinks', str(self.root), str(ordinary))
        source = copy.deepcopy(self.lane('owner')['root']); source['worktree'] = 'legacy-checkout'
        l = self.lane('owner')
        self.reg.checkpoint('owner', 1, l['revision'], {'root': source})
        row = self.agree()
        self.amend(row)
        l = self.lane('integration')
        self.reg.checkpoint('integration', 1, l['revision'], {'root': source})
        with self.assertRaisesRegex(Rejected, 'private checkout'):
            self.agree()

    def test_inactive_legacy_owner_does_not_require_new_handoff(self):
        with self.reg.transaction() as s:
            s['lanes']['owner'].update(state='handoff_ready', handoff={'path': 'missing', 'sha256': 'bad'})
            s['lanes']['owner']['root']['worktree'] = 'output/removed-legacy-worktree'
        request = self.request()
        request['participants'][0]['basis'] = 'user-authorized-legacy-preservation'
        row = self.agree(request)
        self.amend(row)
        self.assertTrue(row['participants'][0]['checkouts']['root']['missing'])
        self.assertEqual({'path': 'missing', 'sha256': 'bad'}, self.lane('owner')['handoff'])

    def test_no_early_completion_or_receipt(self):
        self.amend(self.agree())
        l = self.lane('integration')
        with self.assertRaisesRegex(Rejected, 'Invalid state transition'):
            self.reg.checkpoint('integration', 1, l['revision'], {'state': 'done'})
        self.assertIsNone(self.lane('owner')['integrated_at'])

    def test_worker_wip_not_bypassed(self):
        d = self.data('other'); d['worker_id'] = 'integration'
        with self.assertRaisesRegex(Rejected, 'one active slice'):
            self.reg.register(d)

    def test_local_leases_untouched(self):
        with self.reg.transaction() as s:
            s['leases']['build:private'] = {'lane': 'owner', 'process': self.lane('owner')['process']}
        leases = self.reg.snapshot()['leases']
        self.amend(self.agree())
        self.assertEqual(leases, self.reg.snapshot()['leases'])
        self.assertEqual(1, self.reg.snapshot()['settings']['max_heavy_builds'])

    def test_actor_process_and_revision_fences(self):
        with self.assertRaisesRegex(Rejected, 'registered integration process'):
            self.reg.coordinate(self.request(), chain=[])
        row = self.agree()
        with self.assertRaisesRegex(Rejected, 'Stale lane revision'):
            self.reg.amend_scope('integration', 1, 1, [row['id']], ['shared.py'], 'scope', chain=self.chain)

    def test_changed_communication_evidence_rejected(self):
        row = self.agree()
        self.log.write_text('changed evidence')
        with self.assertRaisesRegex(Rejected, 'changed evidence'):
            self.amend(row)

    def test_path_and_issue_scope_fences(self):
        request = self.request(); request['participants'][0]['files'] = ['../shared.py']
        with self.assertRaisesRegex(Rejected, 'normalized'):
            self.agree(request)
        request = self.request(); request['issue'] = 999
        with self.assertRaisesRegex(Rejected, 'lane issue'):
            self.agree(request)

    def extend_unclaimed(self, additions=None, agreements=None, **overrides):
        request = dict(key='integration', generation=1, revision=self.lane('integration')['revision'],
                       agreement_ids=[] if agreements is None else agreements,
                       additions=['unclaimed.py'] if additions is None else additions,
                       scope='Issue 1144: bounded unclaimed source extension', chain=self.chain)
        request.update(overrides)
        return self.reg.amend_scope(**request)

    def native_checkout(self):
        repo = self.root / 'native'; self.git('init', str(repo))
        self.git('-C', str(repo), '-c', 'user.name=Test', '-c', 'user.email=test@example.test',
                 'commit', '--allow-empty', '-m', 'native baseline')
        head = self.git('-C', str(repo), 'rev-parse', 'HEAD').strip()
        self.git('-C', str(repo), 'worktree', 'add', '--detach', str(self.root / 'output/native-integration'), head)
        with self.reg.transaction() as state:
            state['lanes']['integration']['native'] = dict(base=head, head=head, commits=[], dirty='',
                                                          worktree='output/native-integration')
        return head

    def test_unclaimed_extension_preserves_other_owners_and_acceptance(self):
        before = self.reg.snapshot()
        amended = self.extend_unclaimed(['new.py', 'sub/new.py'])
        after = self.reg.snapshot()
        self.assertEqual(before['lanes']['owner'], after['lanes']['owner'])
        self.assertEqual(before['leases'], after['leases'])
        self.assertEqual(before['lanes']['integration']['revision'] + 1, amended['revision'])
        self.assertEqual([], amended['coordination'][-1]['agreements'])
        self.assertEqual(before['lanes']['integration']['owned_files'] + ['new.py', 'sub/new.py'], amended['owned_files'])
        for field in ('state', 'handoff', 'integrated_at', 'acceptance', 'root', 'native'):
            self.assertEqual(before['lanes']['integration'][field], amended[field])
        self.assertEqual({}, after.get('coordination_agreements', {}))
        self.assertEqual({}, after.get('approvals', {}))

    def test_empty_agreements_cannot_take_unfinished_local_claim(self):
        for key in ('shared.py', 'SHARED.PY'):
            with self.subTest(key=key), self.assertRaisesRegex(Rejected, 'Uncoordinated'):
                self.extend_unclaimed([key])
        self.assertNotIn('shared.py', self.lane('integration')['owned_files'])

    def test_remote_claim_and_same_issue_are_never_waived(self):
        for issue, files in ((1194, ['directory']), (1144, ['other-remote.py'])):
            with self.subTest(issue=issue):
                with self.reg.transaction() as state:
                    state.setdefault('remote', {})['jobs'] = {'real-test-job': dict(id='real-test-job', state='queued',
                                                                                 issue=issue, owned_files=files)}
                before = self.lane('integration')
                with self.assertRaisesRegex(Rejected, 'reserved by remote'):
                    self.extend_unclaimed(['directory/new.py'])
                self.assertEqual(before, self.lane('integration'))

    def test_unclaimed_extension_rejects_malformed_agreements(self):
        for value in (None, 'id', {}, 1, [None], [{}], [1], [''], ['   ']):
            with self.subTest(value=value), self.assertRaisesRegex(Rejected, 'agreement IDs'):
                self.extend_unclaimed(agreement_ids=value)
        with self.assertRaisesRegex(Rejected, 'Unknown or mismatched'):
            self.extend_unclaimed(agreements=['unknown'])

    def test_unclaimed_extension_keeps_normalized_keys_and_scope_required(self):
        for value in ([], '../escape.py', ['../escape.py'], ['/absolute.py'], ['a\\b'], ['a//b'], ['x', 'X'], [None]):
            with self.subTest(value=value), self.assertRaises(Rejected):
                self.extend_unclaimed(value)
        for scope in ('', '   ', None, 7):
            with self.subTest(scope=scope), self.assertRaisesRegex(Rejected, 'issue-backed scope'):
                self.extend_unclaimed(scope=scope)

    def test_unclaimed_extension_requires_live_actor_ancestry_and_current_fences(self):
        for changes, message in ((dict(chain=[]), 'registered integration process'),
                                 (dict(generation=2), 'Stale ownership generation'),
                                 (dict(revision=1), 'Stale lane revision')):
            with self.subTest(changes=changes), self.assertRaisesRegex(Rejected, message):
                self.extend_unclaimed(**changes)
        self.reg.probe = lambda _: 'dead'
        with self.assertRaisesRegex(Rejected, 'Live integration actor'):
            self.extend_unclaimed()
        self.reg.probe = lambda _: 'alive'
        with self.reg.transaction() as state:
            state['lanes']['integration']['state'] = 'blocked'
        with self.assertRaisesRegex(Rejected, 'Live integration actor'):
            self.extend_unclaimed()

    def test_unclaimed_extension_keeps_worker_wip_limit(self):
        with self.reg.transaction() as state:
            state['lanes']['owner']['worker_id'] = 'integration'
        with self.assertRaisesRegex(Rejected, 'one active slice'):
            self.extend_unclaimed()

    def test_unclaimed_extension_checks_actual_root_head(self):
        self.git('-C', str(self.root / 'output/integration'), '-c', 'user.name=Test',
                 '-c', 'user.email=test@example.test', 'commit', '--allow-empty', '-m', 'head drift')
        with self.assertRaisesRegex(Rejected, 'HEAD differs'):
            self.extend_unclaimed()

    def test_unclaimed_extension_checks_missing_and_maintained_checkout(self):
        for tree, message in (('output/absent', 'checkout missing'), ('.', 'private checkout')):
            with self.reg.transaction() as state:
                state['lanes']['integration']['root']['worktree'] = tree
            with self.subTest(tree=tree), self.assertRaisesRegex(Rejected, message):
                self.extend_unclaimed()

    def test_unclaimed_extension_rejects_ordinary_or_redirected_git_checkout(self):
        clone = self.root / 'output/ordinary'
        self.git('clone', '--no-hardlinks', str(self.root), str(clone))
        with self.reg.transaction() as state:
            state['lanes']['integration']['root']['worktree'] = 'output/ordinary'
        with self.assertRaisesRegex(Rejected, 'Linked private git worktree'):
            self.extend_unclaimed()
        forged = self.root / 'output/redirected'; forged.mkdir()
        (forged / '.git').write_text('gitdir: ' + str(self.root / '.git'))
        with self.reg.transaction() as state:
            state['lanes']['integration']['root']['worktree'] = 'output/redirected'
        with self.assertRaisesRegex(Rejected, 'worktree identity'):
            self.extend_unclaimed()

    def test_unclaimed_native_extension_requires_source_and_actual_head(self):
        for key in ('native/pc_port/new.h', 'NATIVE/pc_port/new.h'):
            with self.subTest(key=key), self.assertRaisesRegex(Rejected, 'Source record required for native'):
                self.extend_unclaimed([key])
        self.native_checkout()
        amended = self.extend_unclaimed(['native/pc_port/new.h'])
        self.assertIn('native/pc_port/new.h', amended['owned_files'])
        self.git('-C', str(self.root / 'output/native-integration'), '-c', 'user.name=Test',
                 '-c', 'user.email=test@example.test', 'commit', '--allow-empty', '-m', 'native drift')
        with self.assertRaisesRegex(Rejected, 'HEAD differs'):
            self.extend_unclaimed(['native/pc_port/second.h'])

    def test_mixed_extension_checks_each_repository_even_with_agreement(self):
        row = self.agree()
        with self.assertRaisesRegex(Rejected, 'Source record required for native'):
            self.extend_unclaimed(['shared.py', 'native/pc_port/new.h'], agreements=[row['id']])
        self.assertNotIn('shared.py', self.lane('integration')['owned_files'])
        self.native_checkout()
        # Updating the source identity makes the former agreement stale; genuine
        # current communication must be recorded again instead of reusing it.
        with self.assertRaisesRegex(Rejected, 'Unknown or mismatched'):
            self.extend_unclaimed(['shared.py', 'native/pc_port/new.h'], agreements=[row['id']])
        amended = self.extend_unclaimed(['shared.py', 'native/pc_port/new.h'], agreements=[self.agree()['id']])
        self.assertIn('shared.py', amended['owned_files'])

    def test_unclaimed_mixed_extension_checks_root_and_native(self):
        self.native_checkout()
        amended = self.extend_unclaimed(['root-new.py', 'native/pc_port/new.h'])
        self.assertIn('root-new.py', amended['owned_files'])
        self.assertIn('native/pc_port/new.h', amended['owned_files'])


if __name__ == '__main__':
    unittest.main()
