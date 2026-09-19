"""Review packets read committed blobs, re-pin only through audited records and decide only through the controller."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

from tests import test_pikmin2_workflow as workflow_fixtures
from tests.approval_auth import caller, identity, reviewer
from tests.landing_git import commit as _commit, git
from workflow import approvals, review_packet, review_packet_migration
from workflow.handoff import Rejected
from workflow.processes import identify
from workflow.review_packet import DriftError

CHECKOUT = Path(__file__).resolve().parents[1]
PATH = 'tools/review_packets/test.json'
MGR = 'int unrelated = 1;\n\nvoid birth(int id)\n{\n    spawn(id);\n}\n'
HOOKED = 'int unrelated = 1;\n\nvoid birth(int id)\n{\n    spawn(id);\n    notify(id);\n}\n'
CMAKE = 'add_library(core\n  src/other.cpp\n)\n'
HOOK = dict(kind='shared_hook', issue=186, item_id='example-birth-hook')


def commit(repo, files, message='change'):
    """Commit in a repository whose status compares bytes exactly, whatever the host's core.autocrlf."""
    sha = _commit(repo, files, message)
    git(repo, 'config', 'core.autocrlf', 'false')
    return sha


class Base(unittest.TestCase):
    def setUp(self):
        self.f = f = workflow_fixtures.WorkflowTests('test_handoff_review_and_integration_metrics'); f.setUp()
        self.addCleanup(f.doCleanups)
        self.root, self.reg, self.evidence = f.root, f.reg, f.evidence
        f.running('one')
        for key in ('two', 'three'):
            f.register(key, worker=key)
        self.line = self.root / 'native'
        commit(self.line, {'CMakeLists.txt': CMAKE, 'src/mgr.cpp': MGR}, 'line')
        git(self.line, 'branch', '-M', 'line')
        self.cand = commit(self.root / 'output/cand', {'src/mgr.cpp': HOOKED}, 'candidate')
        self.publish()
        self.two = reviewer(self, self.reg, 'two')

    def packet(self, **extra):
        return dict(format='review-packet-v1', schema='test-186', issue=186, consumers=['one'], landers=[],
                    inputs=dict(cand=dict(role='candidate', repo='output/cand', commit=self.cand, path='src/mgr.cpp'),
                                mgr=dict(role='maintained', line=dict(repo='native', ref='line'), path='src/mgr.cpp',
                                         region=dict(begin='void birth(', end='\n}'))),
                    items=[dict(id='engine-hook', gate='engine hook', candidates=['cand'], candidate_tokens=['notify('],
                                maintained=['mgr'], required_tokens=['spawn('], integration_tokens=['notify('],
                                built_by=True, missing_change='Land the notify hook and build the file')], **extra)

    def publish(self, packet=None):
        self.packet_commit = commit(self.root, {PATH: json.dumps(packet or self.packet())}, 'packet')
        return self.packet_commit

    def rows(self):
        return self.reg.snapshot(section=('packet_pins',))

    def verify(self):
        return review_packet.verify(self.root, PATH, None, self.rows())

    def repin(self, who='two', approve=True, **extra):
        caller(self, identity(who))
        return review_packet.repin(self.reg, PATH, 'mgr', who, 1, self.evidence, approve=approve, **extra)

    def land(self, files):
        return commit(self.line, files, 'land')


class BlobPinTests(Base):
    def test_candidate_is_pinned_by_blob_and_ignores_its_working_copy(self):
        self.repin()
        (self.root / 'output/cand/src/mgr.cpp').write_text('dirty bytes, never read\n')
        result = self.verify()
        blob = git(self.root / 'output/cand', 'rev-parse', f'{self.cand}:src/mgr.cpp')
        self.assertEqual(result['pins']['cand'], dict(commit=self.cand, blob=blob))
        self.assertEqual(result['decided_by'], 'packet:test-186@' + git(self.root, 'rev-parse', f'HEAD:{PATH}'))
        packet = self.packet(); packet['inputs']['cand']['blob'] = 'f' * 40
        self.publish(packet)
        with self.assertRaisesRegex(DriftError, 'Candidate cand: blob'):
            self.verify()

    def test_uncommitted_packet_is_refused_and_a_commit_reads_the_committed_blob(self):
        (self.root / PATH).write_text('{"format": "tampered"}')
        with self.assertRaisesRegex(DriftError, 'commit the packet first'):
            review_packet.load(self.root, PATH)
        packet, _, sha = review_packet.load(self.root, PATH, self.packet_commit)
        self.assertEqual((packet['schema'], sha), ('test-186', self.packet_commit))
        with self.assertRaisesRegex(Rejected, 'Packets live in'):
            review_packet.load(self.root, 'output/p.json')

    def test_dirty_untracked_nested_and_wrong_branch_maintained_inputs_refuse(self):
        spec = self.packet()['inputs']['mgr']
        (self.line / 'src/mgr.cpp').write_text(HOOKED)
        with self.assertRaisesRegex(DriftError, r'src/mgr.cpp is dirty \(M\)'):
            review_packet.observe(self.root, spec)
        git(self.line, 'checkout', '--', 'src/mgr.cpp')
        (self.line / 'src/new.cpp').write_text('int n;\n')
        with self.assertRaisesRegex(DriftError, 'src/new.cpp is untracked'):
            review_packet.observe(self.root, dict(spec, path='src/new.cpp', optional=True))
        commit(self.line / 'research', {'src/mgr.cpp': HOOKED}, 'nested')
        with self.assertRaisesRegex(DriftError, 'research is a nested repository'):
            review_packet.observe(self.root, dict(spec, path='research/src/mgr.cpp'))
        git(self.line, 'checkout', '-q', '-b', 'other')
        with self.assertRaisesRegex(DriftError, 'has other checked out, not the declared line line'):
            review_packet.observe(self.root, spec)

    def test_template_packet_is_valid(self):
        packet = json.loads((CHECKOUT / 'tools/review_packets/template.json').read_text(encoding='utf-8'))
        self.assertEqual(review_packet.validate(packet)['format'], review_packet.FORMAT)


class RegionTests(Base):
    def test_region_hash_is_stable_under_unrelated_edits(self):
        spec = self.packet()['inputs']['mgr']
        before = review_packet.observe(self.root, spec)['pin']
        self.land({'src/mgr.cpp': MGR.replace('unrelated = 1', 'unrelated = 2') + '\nint more;\n'})
        after = review_packet.observe(self.root, spec)['pin']
        self.assertNotEqual(before['blob'], after['blob'])
        self.assertEqual(before['region_sha256'], after['region_sha256'])
        self.assertEqual(review_packet.region(MGR.replace('\n', '\r\n').replace('(id);', '(id);  '), spec['region']),
                         review_packet.region(MGR, spec['region']))
        self.land({'src/mgr.cpp': HOOKED})
        self.assertNotEqual(review_packet.observe(self.root, spec)['pin']['region_sha256'], before['region_sha256'])
        with self.assertRaisesRegex(DriftError, 'not unique'):
            review_packet.region('void birth(\n}\nvoid birth(\n}', spec['region'])

    def test_unrelated_edit_needs_a_recorded_repin_that_any_authenticated_lane_may_write(self):
        first = self.repin()
        self.assertEqual(self.verify()['decision'], 'CHANGES_REQUIRED')
        self.land({'src/mgr.cpp': MGR + '\nint more;\n'})
        with self.assertRaisesRegex(DriftError, 'moved from its audited pin'):
            self.verify()
        reviewer(self, self.reg, 'one')
        row = self.repin('one', approve=False)  # The consumer may record it: the reviewed region is unchanged.
        self.assertEqual((row['approval'], row['region_changed'], row['supersedes']), ('region-unchanged', False, first['id']))
        self.assertEqual(row['old_pin'], first['new_pin'])
        self.assertEqual(self.verify()['pins']['mgr']['record'], row['id'])
        self.assertEqual(self.repin('one', approve=False)['recorded'], row['id'])  # Nothing moved: no new record.


class BuiltByTests(Base):
    def test_built_by_needs_the_path_in_the_line_manifest(self):
        self.land({'src/mgr.cpp': HOOKED}); self.repin()
        item = self.verify()['items'][0]
        self.assertEqual(item['status'], 'CHANGES_REQUIRED')
        self.assertIn('src/mgr.cpp is not built by CMakeLists.txt', item['problems'][0])
        self.land({'CMakeLists.txt': CMAKE.replace('src/other.cpp', 'src/other.cpp\n  src/mgr.cpp')})
        result = self.verify()  # The manifest moved, the pinned file did not: no re-pin needed.
        self.assertEqual((result['decision'], result['items'][0]['built_by']['mgr']['listed']), ('APPROVED', True))
        (self.line / 'CMakeLists.txt').write_text(CMAKE)
        with self.assertRaisesRegex(DriftError, 'Build manifest refused'):
            self.verify()

    def test_listed_matches_whole_paths_outside_comments(self):
        self.assertTrue(review_packet.listed('add(${ROOT}/src/a.cpp)', 'src/a.cpp', 'CMakeLists.txt'))
        self.assertTrue(review_packet.listed('set(S "src/a.cpp")', 'src/a.cpp', 'CMakeLists.txt'))
        self.assertFalse(review_packet.listed('add(other/src/a.cpp)', 'src/a.cpp', 'CMakeLists.txt'))
        self.assertFalse(review_packet.listed('# src/a.cpp\nadd(x)', 'src/a.cpp', 'CMakeLists.txt'))
        self.assertTrue(review_packet.listed('add(a.cpp)', 'src/a.cpp', 'src/CMakeLists.txt'))


class RepinTests(Base):
    def test_first_pin_needs_an_approving_reviewer_that_is_not_consumer_or_lander(self):
        with self.assertRaisesRegex(DriftError, 'has no audited pin'):
            self.verify()
        with self.assertRaisesRegex(Rejected, 'reviewed region changed'):
            self.repin(approve=False)
        reviewer(self, self.reg, 'one')
        with self.assertRaisesRegex(Rejected, 'Self re-pin refused: one'):
            self.repin('one')
        reviewer(self, self.reg, 'three')
        touched = git(self.line, 'rev-parse', 'HEAD')
        with self.reg.transaction() as state:  # three landed the commit that last changed the file.
            state['lanes']['three']['integration'] = dict(root_commit='a' * 40, native_commit=touched)
        with self.assertRaisesRegex(Rejected, 'Self re-pin refused: three'):
            self.repin('three')
        caller(self)  # Outside any launch session.
        with self.assertRaisesRegex(Rejected, 'not running inside'):
            review_packet.repin(self.reg, PATH, 'mgr', 'two', 1, self.evidence, approve=True)
        shown = []
        row = self.repin(show=shown.append)
        self.assertEqual((row['actor']['lane'], row['actor']['launch'], row['old_pin'], row['approval']),
                         ('two', 'launch-two', None, 'reviewer'))
        self.assertEqual(row['region_diff_sha256'], hashlib.sha256(shown[0].encode()).hexdigest())
        self.assertIn('+void birth(int id)', shown[0])
        self.assertEqual(row['new_pin']['commit'], git(self.line, 'rev-parse', 'line'))
        self.assertIn('packet_repinned', [e['kind'] for e in self.reg.snapshot()['events']])

    def test_changed_region_shows_the_diff_and_dry_run_records_nothing(self):
        self.repin(); self.land({'src/mgr.cpp': HOOKED})
        before = self.rows()
        shown = []
        plan = self.repin(approve=False, show=shown.append, dry_run=True)
        self.assertEqual((plan['dry_run'], plan['region_changed'], self.rows()), (True, True, before))
        self.assertIn('+    notify(id);', shown[0])
        reviewer(self, self.reg, 'one')
        with self.assertRaisesRegex(Rejected, 'Self re-pin refused'):
            self.repin('one')
        self.assertEqual(self.repin()['approval'], 'reviewer')
        self.assertEqual(self.verify()['decision'], 'CHANGES_REQUIRED')  # Still not built by the line.


class DecisionTests(Base):
    def setUp(self):
        super().setUp()
        self.f.health = 'alive'
        self.reg.finish('one', 1, 'blocked', 'Waiting for the #186 packet', self.evidence, ['#186 packet'], shared_hooks=[HOOK])
        self.hook = self.lane()['shared_hooks'][0]
        self.land({'src/mgr.cpp': HOOKED, 'CMakeLists.txt': CMAKE.replace('other.cpp', 'other.cpp src/mgr.cpp')})
        self.repin()

    def lane(self):
        return self.reg.snapshot()['lanes']['one']

    def controller(self, process=None):
        with self.reg.transaction() as state:
            self.reg.control(state)['controller'] = process or identify(os.getpid())
        return SimpleNamespace(reg=self.reg, base=self.root / 'output/workflow/controller')

    def request(self):
        caller(self, self.two)
        return review_packet.request(self.reg, 'two', 1, PATH, [dict(key='one', generation=1)], HOOK)

    def test_controller_records_the_verified_packet_decision(self):
        controller = self.controller()
        asked = self.request()
        self.assertEqual(self.request()['id'], asked['id'])  # One open request per packet, hook and lanes.
        self.assertEqual(approvals.hook_state(self.reg.snapshot().get('approvals', {}), self.lane(), self.hook), (False, None))
        done = review_packet.tick(controller)
        self.assertIsNone(review_packet.tick(controller))  # Polled at most once per POLL_SECONDS.
        blob = git(self.root, 'rev-parse', f'HEAD:{PATH}')
        row = self.reg.snapshot()['approvals'][done['approvals'][0]]
        self.assertEqual((row['kind'], row['source'], row['status'], row['decided_by']),
                         ('shared_hook', 'review_packet', 'approved', 'packet:test-186@' + blob))
        self.assertEqual((row['reviewer']['controller'], row['reviewer']['requested_by']['lane']),
                         (identify(os.getpid()), 'two'))
        self.assertEqual(json.loads(Path(row['evidence']['path']).read_text())['decision'], 'APPROVED')
        self.assertTrue(approvals.hook_state(self.reg.snapshot()['approvals'], self.lane(), self.hook)[0])
        self.assertEqual(done['status'], 'decided')

    def test_changes_required_is_a_rejection_with_conditions(self):
        self.land({'CMakeLists.txt': CMAKE})  # The line stops building the file.
        self.request()
        done = review_packet.tick(self.controller())
        row = self.reg.snapshot()['approvals'][done['approvals'][0]]
        self.assertEqual((row['status'], row['conditions']),
                         ('rejected', ['engine-hook: Land the notify hook and build the file']))

    def test_drift_refuses_the_request_and_records_nothing(self):
        asked = self.request()
        self.land({'src/mgr.cpp': MGR})  # Reverted on the line after the audited pin.
        self.controller()
        done = approvals.packet_decision(self.reg, asked['id'])
        self.assertEqual(done['status'], 'refused')
        self.assertIn('moved from its audited pin', done['error'])
        self.assertEqual([r for r in self.reg.snapshot().get('approvals', {}).values() if r['source'] == 'review_packet'], [])

    def test_agents_cannot_write_packet_decisions(self):
        asked = self.request()
        self.controller(self.two)  # The registry's controller is some other process.
        with self.assertRaisesRegex(Rejected, 'only by the running controller process'):
            approvals.packet_decision(self.reg, asked['id'])
        self.assertEqual(self.reg.snapshot().get('approvals', {}), {})
        self.assertEqual(self.reg.snapshot()['packet_requests'][asked['id']]['status'], 'requested')
        with self.assertRaises(SystemExit):  # No approvals CLI verb writes packet decisions.
            approvals.main(['packet-decision', '--root', str(self.root), '--request', 'x.json'])
        caller(self)
        with self.assertRaisesRegex(Rejected, 'not running inside'):  # Requests themselves are authenticated.
            review_packet.request(self.reg, 'two', 1, PATH, [dict(key='one', generation=1)], HOOK)

    def test_verify_cli_writes_nothing(self):
        before = self.reg.path.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            code = review_packet.main(['verify', '--root', str(self.root), '--db', str(self.reg.path), '--packet', PATH])
        self.assertEqual((code, json.loads(stdout.getvalue())['decision']), (0, 'APPROVED'))
        self.assertEqual(self.reg.path.read_bytes(), before)
        self.assertFalse((self.root / 'output/workflow/review-packets').exists())


LEGACY = '''
SCHEMA = "legacy-v1"
CANONICAL_ROOT = "C:/canonical"
_C = CANONICAL_ROOT + "/output/cand"
INPUTS = {
    "maintained_research": {"path": "native/research/src/mgr.cpp", "sha256": "0"},
    "candidate_hook": {"path": _C + "/src/mgr.cpp", "sha256": "%s", "commit": "%s"},
}
ABSENT_OKINPUTS = {"maintained_new": "native/src/new.cpp"}
REVIEW_ITEMS = (
    {"id": "engine-hook", "gate": "engine hook", "maintained_input": "maintained_research",
     "maintained_required_tokens": ("spawn(",), "integration_tokens": ("notify(",),
     "candidate_inputs": ("candidate_hook",), "candidate_commit": "%s",
     "missing_change": "x", "downstream": ()},
)
import os
os.remove("never executed")
'''


class MigrationTests(Base):
    def test_report_refuses_working_copy_inputs_and_names_the_line_version(self):
        self.land({'research/src/mgr.cpp': 'void birth(int id)\n{\n    notify(id);\n}\n',
                   'CMakeLists.txt': CMAKE + 'add_library(r research/src/mgr.cpp)\n'})
        git(self.line, 'checkout', '-q', '-b', 'maintained', 'line~1')
        git(self.line, 'worktree', 'add', '-q', str(self.root / 'output/line-wt'), 'line')
        commit(self.line / 'research', {'src/mgr.cpp': MGR}, 'nested')  # Untracked by native at `maintained`.
        (self.line / 'research/src/mgr.cpp').write_text(HOOKED)
        (self.root / 'output/cand/src/mgr.cpp').write_text(HOOKED + '// local edit\n')
        work = hashlib.sha256((self.root / 'output/cand/src/mgr.cpp').read_bytes()).hexdigest()
        legacy = self.root / 'output/legacy.py'
        legacy.write_text(LEGACY % (work, self.cand, self.cand))
        result = review_packet_migration.report(self.root, legacy, {'native': 'native'},
                                                {'native': dict(repo='output/line-wt', ref='line')})
        item = result['items'][0]
        self.assertEqual(result['summary'], {'engine-hook': 'REFUSED'})
        text = '\n'.join(item['reasons'])
        self.assertIn('research is a nested repository', text)
        self.assertIn('src/mgr.cpp is dirty (M)', text)
        self.assertIn('research/src/mgr.cpp is not built by native/CMakeLists.txt at maintained', text)
        self.assertTrue(item['integration_line']['maintained_research']['built'])
        need = '\n'.join(item['would_need'])
        self.assertIn('line files lack spawn(', need)
        self.assertIn('instead of uncommitted working-copy bytes', need)
        self.assertEqual(item['candidates']['candidate_hook']['commit_blob'],
                         git(self.root / 'output/cand', 'rev-parse', f'{self.cand}:src/mgr.cpp'))


if __name__ == '__main__':
    unittest.main()
