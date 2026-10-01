"""Isolated lane correction; real Git source drift and exact process fencing."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from workflow.handoff import Rejected, digest
from workflow.coordination import current, identity
from workflow.owner_identity import git_bytes, sha
from workflow.processes import identify, probe
from workflow.registry import Registry


class OwnerIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.git('init', str(self.root))
        (self.root / 'claimed.txt').write_text('baseline')
        self.git('-C', str(self.root), 'add', '.')
        self.git('-C', str(self.root), '-c', 'user.name=Test', '-c', 'user.email=test@example.test',
                 'commit', '-m', 'baseline')
        head = self.git('-C', str(self.root), 'rev-parse', 'HEAD').strip()
        self.tree = self.root / 'output/private'
        self.git('-C', str(self.root), 'worktree', 'add', '--detach', str(self.tree), head)
        (self.tree / 'claimed.txt').write_text('dirty owner bytes')
        (self.tree / 'new.txt').write_text('untracked owner bytes')
        self.reg = Registry(self.root / 'output/workflow/registry.sqlite3', self.root,
                            process_probe=lambda _: 'alive')
        self.reg.init()
        self.reg.register(dict(lane='owner', owner='Codex through 4laric', worker_id='worker', task_id='task',
            issue=1157, scope='Bounded owner regression', target_level='tooling', next_action='Prepare fixture',
            milestone='fixture', owned_files=['claimed.txt'], acceptance=['review'], pid=os.getpid(),
            root=dict(base=head, head=head, commits=[], dirty='', worktree=str(self.tree)), native=None))
        self.reg.checkpoint('owner', 1, 1, {'state': 'running'})
        self.old = self.reg.snapshot()['lanes']['owner']['process']
        self.new = dict(self.old, pid=self.old['pid'] + 10000, started='different-start')
        dirty = git_bytes(self.tree, 'status', '--porcelain').decode().replace('\r\n', '\n')
        self.receipt = dict(schema=1, correction_issue=1163, implementation_issue=1157,
            lane=self.reg.snapshot()['lanes']['owner'], old_process=self.old, new_process=self.new,
            actual_caller_chain=[self.new], owner_consent='Owner authorizes this exact correction',
            resources=[], queue=[], observed_worktrees=[dict(repo='root', path=str(self.tree), head=head,
                dirty=dirty, dirty_sha256=sha(dirty.encode()),
                tracked_diff_sha256=sha(git_bytes(self.tree, 'diff', '--binary')),
                files=[dict(path=p, sha256=digest(self.tree / p)) for p in ('claimed.txt', 'new.txt')])])
        self.path = self.root / 'output/consent.json'
        error = self.root / 'output/registration-error.json'
        error.write_text(json.dumps(dict(old=self.old, new=self.new, error='Historical identity copied into registration')))
        self.receipt.update(registration_error='Historical identity copied into registration',
                            registration_error_evidence=dict(path=str(error), sha256=digest(error)))
        self.save()
        self.chain = patch('workflow.owner_identity.approvals.ancestry', return_value=[self.new])
        self.rows = patch('workflow.owner_identity.processes.process_rows',
                          return_value=[dict(ProcessId=self.old['pid'], ParentProcessId=0, Name='old')])
        self.chain.start(); self.addCleanup(self.chain.stop)
        self.rows.start(); self.addCleanup(self.rows.stop)

    def git(self, *args):
        p = subprocess.run(['git', *args], capture_output=True, text=True, timeout=15)
        self.assertEqual(0, p.returncode, p.stderr)
        return p.stdout

    def save(self):
        self.path.write_text(json.dumps(self.receipt), encoding='utf-8')
        self.consent = dict(path=str(self.path), sha256=digest(self.path))

    def rejected(self, pattern):
        before = self.reg.snapshot()
        with self.assertRaisesRegex(Rejected, pattern):
            self.reg.correct_owner_identity(self.consent, apply=True)
        self.assertEqual(before, self.reg.snapshot())

    def test_preflight_then_apply_preserves_every_other_lane_field_and_archives_consent(self):
        before = self.reg.snapshot()
        self.assertFalse(self.reg.correct_owner_identity(self.consent)['applied'])
        self.assertEqual(before, self.reg.snapshot())
        audit = self.reg.correct_owner_identity(self.consent, apply=True)
        after = self.reg.snapshot()
        expected = copy.deepcopy(before['lanes']['owner'])
        expected['process'] = self.new; expected['revision'] += 1
        self.assertEqual(expected, after['lanes']['owner'])
        self.assertEqual(before['lanes']['owner'], audit['before'])
        self.assertEqual(self.consent['sha256'], digest(Path(audit['consent']['path'])))
        self.rejected('Stale whole-lane')

    def test_source_bytes_drift_without_status_change(self):
        (self.tree / 'claimed.txt').write_text('different dirty bytes')
        self.rejected('tracked bytes changed')

    def test_untracked_bytes_drift(self):
        (self.tree / 'new.txt').write_text('changed')
        self.rejected('file bytes changed')

    def test_unhashed_untracked_file(self):
        self.receipt['observed_worktrees'][0]['files'].pop(); self.save()
        self.rejected('Unhashed untracked')

    def test_consent_bytes_drift(self):
        self.path.write_text('{}')
        self.rejected('changed evidence')

    def test_clerical_error_and_hashed_support_required(self):
        self.receipt['registration_error'] = ''; self.save()
        self.rejected('clerical registration error')
        self.receipt['registration_error'] = 'Mistaken historical identity'
        self.receipt['registration_error_evidence']['sha256'] = '0' * 64; self.save()
        self.rejected('changed evidence')

    def test_final_new_identity_must_remain_alive(self):
        with patch.object(self.reg, 'probe', side_effect=['alive', 'alive', 'alive', 'unknown']):
            self.rejected('changed during process observation')

    def test_staged_changes_not_attested_by_plain_diff_refuse(self):
        self.git('-C', str(self.tree), 'add', 'claimed.txt')
        self.receipt['observed_worktrees'][0]['dirty'] = git_bytes(self.tree, 'status', '--porcelain').decode()
        self.receipt['observed_worktrees'][0]['dirty_sha256'] = sha(self.receipt['observed_worktrees'][0]['dirty'].encode())
        self.save()
        self.rejected('Staged source')

    def test_delivery_claims_and_session_pending_refuse(self):
        for kind in ('candidate', 'qa', 'claim', 'session', 'action', 'recovery'):
            with self.subTest(kind=kind):
                with self.reg.transaction() as s:
                    if kind == 'candidate': s['throughput'] = dict(candidates={'c': dict(producer='owner', current=True)})
                    if kind == 'qa': s['throughput'] = dict(qa={'q': dict(lane='owner')})
                    if kind == 'claim': s['planning_claims'] = {'p': dict(lane='owner')}
                    if kind == 'session': s['lanes']['owner']['session_pending'] = True
                    if kind == 'action': s['actions']['a'] = dict(lane='owner', status='claimed')
                    if kind == 'recovery': s['control'] = dict(terminal_recoveries={'r': dict(lane='owner', status='child_stop_requested')})
                if kind == 'session':
                    self.receipt['lane'] = self.reg.snapshot()['lanes']['owner']; self.save()
                self.rejected('candidate|subscription|planning claim|session adoption|action|terminal recovery')
                with self.reg.transaction() as s:
                    s.pop('throughput', None); s.pop('planning_claims', None); s.pop('control', None)
                    s['actions'] = {}; s['lanes']['owner'].pop('session_pending', None)
                self.receipt['lane'] = self.reg.snapshot()['lanes']['owner']; self.save()

    def test_queued_and_open_pool_work_refuses_without_launch(self):
        for collection in ('jobs', 'assignments'):
            for status in ('queued', 'assigned', 'dispatched', 'recovered', 'unknown'):
                with self.subTest(collection=collection, status=status):
                    with self.reg.transaction() as s:
                        s['throughput'] = {collection: {'job': dict(lane='owner', worker_id='worker', status=status)}}
                    self.rejected('queued pool execution')


    def test_whole_lane_cas(self):
        with self.reg.transaction() as s:
            s['lanes']['owner']['task_id'] = 'other-task'
        self.rejected('Stale whole-lane')

    def test_dead_unknown_or_reused_identity(self):
        for result in ('dead', 'unknown'):
            with self.subTest(result=result), patch.object(self.reg, 'probe', return_value=result):
                self.rejected('Both exact identities')

    def test_actual_ancestry_required(self):
        for chain in ([], [self.new, self.old], [dict(self.new, started='reused')]):
            with self.subTest(chain=chain), patch('workflow.owner_identity.approvals.ancestry', return_value=chain):
                self.rejected('actual caller ancestor')

    def test_old_descendants_or_unknown_snapshot_refuse(self):
        for rows in (None, [], [dict(ProcessId=self.old['pid'], ParentProcessId=0, Name='old'),
                               dict(ProcessId=99, ParentProcessId=self.old['pid'], Name='ninja')]):
            with self.subTest(rows=rows), patch('workflow.owner_identity.processes.process_rows', return_value=rows):
                self.rejected('descendants')

    def test_new_host_unrelated_children_allowed(self):
        with patch('workflow.owner_identity.processes.process_rows', return_value=[
                dict(ProcessId=self.old['pid'], ParentProcessId=0, Name='old'),
                dict(ProcessId=self.new['pid'], ParentProcessId=0, Name='host'),
                dict(ProcessId=99, ParentProcessId=self.new['pid'], Name='other-build')]):
            self.reg.correct_owner_identity(self.consent, apply=True)

    def test_old_coordination_archive_preserved_but_cannot_authorize_new_owner(self):
        agreement = dict(integration=dict(identity=identity(self.receipt['lane'])), participants=[])
        with self.reg.transaction() as s:
            s['coordination_agreements'] = {'old': agreement}
        self.reg.correct_owner_identity(self.consent, apply=True)
        state = self.reg.snapshot()
        self.assertEqual(agreement, state['coordination_agreements']['old'])
        with self.assertRaisesRegex(Rejected, 'Stale coordination'):
            current(self.reg, state, agreement)

    @unittest.skipUnless(os.name == 'nt', 'Live child observation uses Windows Toolhelp')
    def test_real_live_old_child_and_actual_caller_ancestor(self):
        child = subprocess.Popen([os.sys.executable, '-c', 'import time; time.sleep(60)'])
        def cleanup():
            child.terminate(); child.wait(timeout=10)
        self.addCleanup(cleanup)
        self.chain.stop(); self.rows.stop()
        from workflow.approvals import ancestry
        self.old = identify(child.pid)
        self.new = ancestry()[0]
        self.reg.probe = probe
        with self.reg.transaction() as s:
            s['lanes']['owner']['process'] = self.old
        self.receipt.update(lane=self.reg.snapshot()['lanes']['owner'], old_process=self.old,
                            new_process=self.new, actual_caller_chain=ancestry())
        self.save()
        audit = self.reg.correct_owner_identity(self.consent, apply=True)
        self.assertEqual(self.new, audit['after']['process'])
        self.assertEqual('alive', probe(self.old))

    def test_any_resource_request_or_active_launch_refuses(self):
        for section in ('leases', 'queue'):
            with self.reg.transaction() as s:
                s[section]['resource'] = dict(lane='owner')
            self.rejected('resource lease or request')
            with self.reg.transaction() as s:
                del s[section]['resource']
        for status in ('intent', 'spawned', 'running', 'exiting'):
            with self.reg.transaction() as s:
                s.setdefault('control', {}).setdefault('launches', {})['launch'] = dict(lane='owner', status=status)
            self.rejected('launch in flight')
            with self.reg.transaction() as s:
                del s['control']['launches']['launch']


if __name__ == '__main__':
    unittest.main()
