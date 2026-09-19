"""Authenticated approvals ledger: forged, free-text and self approvals refuse; temporary git repos only."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from types import SimpleNamespace

from tests import test_pikmin2_workflow as workflow_fixtures
from tests.approval_auth import calling, identity, reviewer
from tests.landing_git import commit, git, source
from workflow import approvals, landing, landing_audit, review_decisions, shared_decisions
from workflow.handoff import Rejected, digest

SHARED = 'engine/hook.cpp'


class Base(unittest.TestCase):
    def setUp(self):
        self.f = f = workflow_fixtures.WorkflowTests('test_handoff_review_and_integration_metrics'); f.setUp()
        self.addCleanup(f.doCleanups)
        self.root, self.reg = f.root, f.reg
        f.running('one')
        source(self.reg, 'one', {'workflow/one.py': 'X = 1\n', SHARED: 'int a;\n'})
        for key in ('two', 'three'):
            f.register(key, worker=key)
        self.two = reviewer(self, self.reg, 'two', owns=['one'])
        self.evidence = f.evidence

    def lane(self, key='one'):
        return self.reg.snapshot()['lanes'][key]

    def submit(self, status='requested'):
        lane = self.lane()
        data = self.f.handoff(lane)
        data['changed_files'] = sorted(set(data['changed_files']) | {SHARED})
        data['shared_reviews'] = [dict(file=SHARED, reason='Shared hook', issue_url='https://x/186', status=status,
                                       evidence=['log'])]
        path = self.root / f'output/handoff-{status}-{lane["revision"]}.json'
        path.write_text(json.dumps(data))
        return self.reg.submit_handoff('one', lane['generation'], lane['revision'], str(path))

    def approve(self, status='approved', who='two'):
        lane = self.lane()
        return review_decisions.record(self.reg, who, self.lane(who)['generation'], 'one', lane['generation'],
                                       lane['handoff']['sha256'], [dict(file=SHARED, status=status, evidence=self.evidence)])

    def record(self, sha, **extra):
        return dict(root_commit=sha, validation_path=str(self.f.log), validation_sha256=digest(self.f.log), **extra)


class LedgerTests(Base):
    def test_forged_producer_approval_is_refused(self):
        for status in ('approved', 'rejected'):
            with self.assertRaisesRegex(Rejected, 'no matching authenticated decision'):
                self.submit(status)
        self.assertEqual(self.lane()['state'], 'running')

    def test_ledger_stamped_approval_is_accepted_and_integrates(self):
        lane = self.submit()
        self.assertEqual(lane['handoff']['result']['pending_reviews'], [SHARED])
        receipt = self.approve()
        row = self.reg.snapshot()['approvals'][receipt['approvals'][0]]
        diff = subprocess.run(['git', '-C', str(self.root), '--literal-pathspecs', *landing.INTERDIFF, lane['root']['base'],
                               lane['root']['head'], '--', SHARED], capture_output=True, check=True).stdout
        self.assertEqual(row['diff_sha256'], hashlib.sha256(diff).hexdigest())
        self.assertEqual((row['reviewer']['lane'], row['reviewer']['launch'], row['pins']),
                         ('two', 'launch-two', approvals.pins(lane)))
        self.assertIn('sha', row['code_revision'])
        self.assertEqual(self.reg.check_handoff(self.lane())['pending_reviews'], [])
        lane = self.submit('approved')  # A matching ledger row lets the producer echo the status.
        self.assertEqual(lane['handoff']['result']['reviews'][SHARED]['approval'], row['id'])
        lane = self.submit('requested')  # Honest producers get the ledger's status.
        self.assertEqual(lane['handoff']['result']['pending_reviews'], [])
        lane = self.reg.checkpoint('one', 1, lane['revision'], {'state': 'integrating'})
        done = self.reg.integrate('one', 1, lane['revision'], self.record(lane['root']['head']))
        self.assertEqual(done['integration_landing']['reviews'][SHARED]['approval'], row['id'])
        proof = done['integration_landing']  # The caller runs inside two's session: two reviewed and landed.
        self.assertEqual((proof['lander']['lane'], proof['self_reviewed']), ('two', [SHARED]))

    def test_later_rejection_and_moved_pins_reopen_the_review(self):
        self.submit(); self.approve(); self.f.now += 1; self.approve('rejected')
        self.assertEqual(self.reg.check_handoff(self.lane())['pending_reviews'], [SHARED])
        self.f.now += 1; self.approve()
        lane = self.reg.checkpoint('one', 1, self.lane()['revision'], {'state': 'running'})
        source(self.reg, 'one', {SHARED: 'int moved;\n'})
        with self.assertRaisesRegex(Rejected, 'no matching authenticated decision'):
            self.submit('approved')

    def test_mid_flight_producer_written_status_does_not_pass_integrate(self):
        lane = self.submit()
        data = json.loads(open(lane['handoff']['path'], encoding='utf-8').read())
        data['shared_reviews'][0]['status'] = 'approved'  # Written before the ledger existed.
        path = self.root / 'output/legacy-handoff.json'; path.write_text(json.dumps(data))
        with self.reg.transaction() as state:
            state['lanes']['one'].update(state='integrating', handoff=dict(path=str(path), sha256=digest(path),
                                         result=dict(lane['handoff']['result'], pending_reviews=[])))
        lane = self.lane()
        with self.assertRaisesRegex(Rejected, 'no authenticated approval in the approvals ledger.*' + SHARED):
            self.reg.integrate('one', 1, lane['revision'], self.record(lane['root']['head']))
        self.approve()  # Re-stamped once an authenticated decision exists at these pins.
        self.assertEqual(self.reg.integrate('one', 1, lane['revision'], self.record(lane['root']['head']))['state'], 'done')

    def test_free_text_and_unauthenticated_reviewers_are_refused(self):
        lane = self.submit(); self.f.health = 'dead'
        args = ('one', 1, lane['revision'], 'v1', lane['handoff']['sha256'], SHARED, 'approved')
        with self.assertRaisesRegex(Rejected, 'free-text reviewers are refused'):
            self.reg.dispose_review(*args, 'Codex through shared account 4laric', self.evidence)
        with self.reg.transaction() as state:  # Live and running, but no controller launch bound to it.
            state['lanes']['three'].update(state='running', process=identity('three'))
        self.reg._approval_live.add(tuple(sorted(identity('three').items())))
        with self.assertRaisesRegex(Rejected, 'no running controller launch'):
            self.reg.dispose_review(*args, 'three', self.evidence, reviewer_generation=1)
        self._approval_chain.clear()
        with self.assertRaisesRegex(Rejected, "not running inside the reviewer lane's live launch session"):
            self.reg.dispose_review(*args, 'two', self.evidence, reviewer_generation=1)
        with self.assertRaisesRegex(Rejected, "not running inside"):
            self.approve()
        calling(self, self.two)
        record = self.reg.dispose_review(*args, 'two', self.evidence, reviewer_generation=1)
        row = self.reg.snapshot()['approvals'][record['approval']]
        self.assertEqual((row['source'], row['reviewer']['models']), ('dispose_review', ['test/reviewer-model']))
        self.assertEqual(self.reg.check_handoff(self.lane())['pending_reviews'], [])

    def test_shared_decisions_always_authenticate(self):
        self.reg.checkpoint('one', 1, self.lane()['revision'], {'state': 'blocked', 'dependencies': ['#186']})
        self.f.health = 'dead'
        args = dict(key='one', generation=1, source_pins=shared_decisions.pins(self.lane()), file='workflow/one.py',
                    status='approved', reviewer='Codex through shared account', reason='Scoped', evidence=self.evidence)
        with self.assertRaisesRegex(Rejected, 'free-text reviewers are refused'):
            shared_decisions.record(self.reg, **args)
        with self.assertRaisesRegex(Rejected, 'own producer workstream'):
            reviewer(self, self.reg, 'three')
            shared_decisions.record(self.reg, **dict(args, reviewer='three', reviewer_generation=1))
        first = shared_decisions.record(self.reg, **dict(args, reviewer='two', reviewer_generation=1))
        self.assertEqual(self.reg.snapshot()['approvals'][first['approval']]['kind'], 'preflight')

    def test_packets_are_not_decisions_yet(self):
        with self.assertRaisesRegex(Rejected, 'review packets are not accepted'):
            approvals.packet_decision(packet='output/review-packet.json')

    def test_real_ancestry_is_this_process_parent_chain(self):
        out = subprocess.run([sys.executable, '-c', 'import json,os; from workflow import approvals; '
                              'print(json.dumps([os.getppid(), approvals.ancestry()]))'],
                             cwd=str(Path(__file__).resolve().parents[1]), capture_output=True, text=True, check=True).stdout
        parent, found = json.loads(out)
        self.assertEqual((found[0]['pid'], parent), (os.getpid(), os.getpid()))
        self.assertTrue(all(int(a['started']) <= int(b['started']) for a, b in zip(found[1:], found)))


class LandingReviewTests(Base):
    def setUp(self):
        super().setUp()
        self.submit(); self.approve()
        lane = self.reg.checkpoint('one', 1, self.lane()['revision'], {'state': 'integrating'})
        self.head = lane['root']['head']
        git(self.root, 'checkout', '-q', '-b', 'land', lane['root']['base'])
        self.landed = commit(self.root, {'workflow/one.py': 'X = 1\n', SHARED: 'int b;  /* ported */\n'}, 'port')
        self.interdiff = hashlib.sha256(subprocess.run(
            ['git', '-C', str(self.root), '--literal-pathspecs', *landing.INTERDIFF, self.head, self.landed, '--', SHARED],
            capture_output=True, check=True).stdout).hexdigest()
        self.three = reviewer(self, self.reg, 'three', owns=['one'])

    def review(self, status='approved', who='two', interdiff=None, key_generation=1):
        return approvals.landing_review(self.reg, who, 1, 'one', key_generation, self.head, self.landed,
                                        interdiff or self.interdiff, [SHARED], status, self.evidence, ['keep hook order'])

    def port(self):
        return dict(repo='root', file=SHARED, reviewed_blob=git(self.root, 'rev-parse', f'{self.head}:{SHARED}'),
                    landed_blob=git(self.root, 'rev-parse', f'{self.landed}:{SHARED}'), interdiff_sha256=self.interdiff,
                    reason='Adapted to the moved line', evidence=self.evidence)

    def integrate(self, *processes, lander=None):
        self._approval_chain[:] = list(processes)
        lane = self.lane()
        return self.reg.integrate('one', 1, lane['revision'], self.record(self.landed, ports=[self.port()]), lander)

    def test_interdiff_mismatch_is_refused(self):
        with self.assertRaisesRegex(Rejected, 'interdiff_sha256 must be ' + self.interdiff):
            self.review(interdiff='e' * 64)
        with self.assertRaisesRegex(Rejected, 'did not change'):
            approvals.landing_review(self.reg, 'two', 1, 'one', 1, self.head, self.landed, self.interdiff,
                                     ['workflow/other.py'], 'approved', self.evidence)

    def test_integrate_with_shared_port_and_landing_review_is_accepted(self):
        row = self.review()
        self.assertEqual((row['file_interdiffs'][SHARED], row['conditions'], row['reviewer']['lane']),
                         (self.interdiff, ['keep hook order'], 'two'))
        with self.assertRaisesRegex(Rejected, 'lander does not match'):
            self.integrate(self.three, lander=dict(lane='two', generation=1))
        done = self.integrate(self.three, lander=dict(lane='three', generation=1))
        proof = done['integration_landing']
        self.assertEqual((proof['lander']['lane'], proof['lander']['launch']), ('three', 'launch-three'))
        self.assertEqual(proof['root']['port_reviews'][SHARED], [row['id'], self.interdiff])
        self.assertEqual(proof['claimed_lander'], dict(lane='three', generation=1))

    def test_self_review_by_the_lander_is_refused(self):
        self.review(who='two')
        with self.assertRaisesRegex(Rejected, 'reviewed by its own lander'):
            self.integrate(self.two)

    def test_unauthenticated_lander_keeps_shared_port_refused(self):
        self.review(who='two')
        with self.assertRaisesRegex(Rejected, 'authenticated lander'):
            self.integrate(lander=dict(lane='three', generation=1))  # A claim is not an identity.
        self.assertEqual(self.lane()['state'], 'integrating')

    def test_later_rejection_supersedes_the_approval(self):
        self.review(); self.f.now += 1; self.review('rejected')
        with self.assertRaisesRegex(Rejected, 'requires a landing review approved'):
            self.integrate(self.three)

    def test_blocked_and_done_producers_accept_landing_reviews(self):
        self.reg.checkpoint('one', 1, self.lane()['revision'], {'state': 'running'})
        with self.assertRaisesRegex(Rejected, 'blocked, done, handoff_ready or integrating'):
            self.review()
        self.reg.checkpoint('one', 1, self.lane()['revision'], {'state': 'blocked', 'dependencies': ['#186 landing']})
        self.assertIsNone(self.lane()['handoff'])
        self.assertEqual(self.review()['status'], 'approved')
        with self.reg.transaction() as state:
            state['lanes']['one']['state'] = 'done'
        self.f.now += 1
        self.assertEqual(self.review('rejected', who='three')['status'], 'rejected')


class SharedHookTests(Base):
    HOOK = dict(kind='shared_hook', issue=186, files=[SHARED])

    def setUp(self):
        super().setUp()
        lane = self.lane()
        self.reg.finish('one', 1, 'blocked', 'Waiting for the #186 hook decision', self.evidence,
                        ['#186 shared-hook review'], shared_hooks=[self.HOOK])
        self.hook = self.lane()['shared_hooks'][0]
        self.commit = lane['root']['head']

    def decide(self, status='approved', key='one'):
        return approvals.shared_hook_decision(self.reg, 'two', 1, self.HOOK, [dict(key=key, generation=1)], status,
                                              self.evidence, ['bridge only'], commit=self.commit)

    def test_decision_satisfies_only_at_recorded_pins_and_wakes_once(self):
        rows = approvals.ledger(self.reg.snapshot())
        self.assertEqual(approvals.hook_state(rows, self.lane(), self.hook), (False, None))
        row = self.decide()[0]
        state = self.reg.snapshot()
        self.assertEqual(row['subject']['blobs'][SHARED], git(self.root, 'rev-parse', f'{self.commit}:{SHARED}'))
        self.assertTrue(approvals.hook_state(state['approvals'], self.lane(), self.hook)[0])
        self.assertIn('shared_hook_decided', [e['kind'] for e in state['events']])
        self.assertEqual(self.lane()['dependencies'], ['#186 shared-hook review'])  # Free text is never cleared.
        with self.reg.transaction() as s:
            s['lanes']['one']['task_id'] = 'opencode:session-one'
        self.f.health = 'dead'
        controller = SimpleNamespace(reg=self.reg, config=dict(lanes={'one': {}}, models=['test/model']),
                                     available=lambda key: True)
        approvals.tick(controller); approvals.tick(controller)
        launches = [x for x in self.reg.control_status()['launches'].values() if x['lane'] == 'one']
        self.assertEqual([x['reason'] for x in launches], ['shared-hook-decision:' + row['id']])
        with self.reg.transaction() as s:
            s['lanes']['one']['root']['head'] = 'c' * 40  # Pins moved: the decision no longer holds.
        self.assertFalse(approvals.hook_state(self.reg.snapshot()['approvals'], self.lane(), self.hook)[0])

    def test_rejection_and_foreign_lanes(self):
        self.decide('rejected')
        self.assertFalse(approvals.hook_state(self.reg.snapshot()['approvals'], self.lane(), self.hook)[0])
        with self.assertRaisesRegex(Rejected, 'holds no matching shared_hook'):
            self.decide(key='three')
        with self.assertRaisesRegex(Rejected, 'kind "shared_hook"'):
            approvals.hooks([dict(kind='shared_hook', issue=186)])


class LegacyReportTests(Base):
    def test_report_marks_unbacked_approvals_and_never_writes(self):
        lane = self.submit()
        data = json.loads(open(lane['handoff']['path'], encoding='utf-8').read())
        data['shared_reviews'][0]['status'] = 'approved'
        path = self.root / 'output/done-handoff.json'; path.write_text(json.dumps(data))
        with self.reg.transaction() as state:
            state['lanes']['one'].update(state='done', handoff=dict(path=str(path), sha256=digest(path)))
            state.setdefault('throughput', {}).setdefault('dispositions', {})['d1'] = dict(
                request=dict(file=SHARED, status='approved', reviewer='Codex through shared account 4laric'),
                snapshot=dict(handoff=dict(path=str(path), sha256=digest(path))), at=1)
        before = hashlib.sha256(self.reg.path.read_bytes()).hexdigest()
        out = self.root / 'output/legacy.json'
        self.assertEqual(landing_audit.main(['--approvals', '--root', str(self.root), '--db', str(self.reg.path),
                                             '--out', str(out)]), 1)
        self.assertEqual(hashlib.sha256(self.reg.path.read_bytes()).hexdigest(), before)
        report = json.loads(out.read_text())
        self.assertEqual(report['summary']['done_lanes_producer_written'], 1)
        self.assertEqual(report['summary']['free_text_dispositions'], 1)
        self.assertEqual({i['marking'] for i in report['items']}, {'unauthenticated-legacy'})
        self.assertEqual([i['lane'] for i in report['items'] if i['category'] == 'disposition'], ['one'])


if __name__ == '__main__':
    unittest.main()
