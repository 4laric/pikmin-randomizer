"""Delivery regression tests use temporary registries and synthetic native bytes."""
import copy
import json
import unittest

from workflow.delivery import DeliveryMixin
from workflow.handoff import Rejected, digest
from workflow.registry import Registry
from tests import test_pikmin2_workflow as baseline


DeliveryRegistry = Registry


class DeliveryTests(unittest.TestCase):
    def test_submission_freezes_evidence_before_it_can_be_rotated(self):
        with self.reg.transaction() as state:state['settings']['freeze_handoffs_on_submit']=True
        lane=self.ready(runtime=True)
        original=copy.deepcopy(lane['handoff'])
        self.log.write_text('rotated')
        self.assertTrue(self.reg.check_handoff(lane)['slice_passed'])
        self.assertEqual(original,self.reg.snapshot()['lanes']['one']['handoff'])
        self.assertIn('delivery',original['path'])

    setUp = baseline.WorkflowTests.setUp
    data = baseline.WorkflowTests.data
    register = baseline.WorkflowTests.register
    running = baseline.WorkflowTests.running
    handoff = baseline.WorkflowTests.handoff
    save_handoff = baseline.WorkflowTests.save_handoff

    def ready(self, runtime=False, reviews=False, null_build=False):
        self.reg = DeliveryRegistry(self.db, self.root, clock=lambda: self.now,
                                    process_probe=lambda _: self.health)
        lane = self.running()
        if runtime:
            lane = self.reg.checkpoint('one', 1, lane['revision'], {'native': copy.deepcopy(lane['root'])})
        data = self.handoff(lane, runtime)
        if null_build:data['build']=None
        if reviews:
            data['shared_reviews'] = [dict(file='shared.cpp', reason='shared behavior', issue_url='https://github.com/4laric/pikmin-randomizer/issues/526', status='requested', evidence=['log'])]
            data['changed_files'].append('shared.cpp')
        self.reg.submit_handoff('one', 1, lane['revision'], self.save_handoff(data))
        self.health = 'dead'
        return self.reg.status()['lanes']['one']

    def test_null_build_tooling_snapshot_and_review(self):
        lane=self.ready(reviews=True,null_build=True)
        original=lane['handoff']['sha256']
        snapshot=self.reg.snapshot_handoff('one',1,lane['revision'],'null-build')
        frozen=json.loads(self.reg.evidence(snapshot['handoff']).read_text())
        self.assertIsNone(frozen['build'])
        self.reg.dispose_review('one',1,lane['revision'],'null-approved',original,
                                'shared.cpp','approved','reviewer',self.evidence)
        updated=self.reg.status()['lanes']['one']
        self.assertEqual([],self.reg.check_handoff(updated)['pending_reviews'])
        self.assertFalse(updated['handoff']['result']['gameplay_accepted'])

    def test_runtime_still_requires_build(self):
        with self.assertRaises(Rejected):self.ready(runtime=True,null_build=True)

    def test_snapshot_retains_evidence_after_original_changes_and_rejects_drift(self):
        lane = self.ready(runtime=True)
        snapshot = self.reg.snapshot_handoff('one', 1, lane['revision'], 'v1')
        self.log.write_text('original log rotated')
        self.assertEqual(snapshot, self.reg.snapshot_handoff('one', 1, lane['revision'], 'v1'))
        self.reg._delivery_validate(snapshot, lane)
        path = self.root / snapshot['evidence']['log']['path']
        path.write_text('tampered frozen bytes')
        with self.assertRaises(Rejected):
            self.reg.snapshot_handoff('one', 1, lane['revision'], 'v1')

    def test_disposition_applies_new_handoff_replays_and_preserves_gates(self):
        lane = self.ready(reviews=True)
        original = lane['handoff']['sha256']
        result = self.reg.dispose_review('one', 1, lane['revision'], 'approved-1', original,
                                         'shared.cpp', 'approved', 'reviewer', self.evidence)
        updated = self.reg.status()['lanes']['one']
        self.assertNotEqual(original, updated['handoff']['sha256'])
        self.assertEqual([], self.reg.check_handoff(updated)['pending_reviews'])
        self.assertFalse(updated['handoff']['result']['gameplay_accepted'])
        self.assertEqual(result, self.reg.dispose_review('one', 1, lane['revision'], 'approved-1', original,
                                                       'shared.cpp', 'approved', 'reviewer', self.evidence))
        with self.assertRaises(Rejected):
            self.reg.dispose_review('one', 1, updated['revision'], 'approved-1', original,
                                    'shared.cpp', 'rejected', 'reviewer', self.evidence)

    def test_frozen_submission_survives_original_log_rotation(self):
        lane = self.ready(runtime=True)
        snapshot = self.reg.snapshot_handoff('one', 1, lane['revision'], 'integration-v1')
        lane = self.reg.submit_handoff('one', 1, lane['revision'], snapshot['handoff']['path'])
        self.log.write_text('original log rotated after submission')
        self.assertTrue(self.reg.check_handoff(lane)['slice_passed'])
        self.assertEqual(lane['handoff']['sha256'], snapshot['handoff']['sha256'])

    def test_disposition_fences_owner_generation_revision_and_source(self):
        lane = self.ready(reviews=True)
        def apply(generation=1, revision=lane['revision'], sha=lane['handoff']['sha256']):
            return self.reg.dispose_review('one', generation, revision, 'v1', sha,
                                           'shared.cpp', 'approved', 'reviewer', self.evidence)
        for health in ('alive', 'unknown'):
            self.health = health
            with self.assertRaises(Rejected):
                apply()
        self.health = 'dead'
        for args in ({'generation': 2}, {'revision': 1}, {'sha': '0' * 64}):
            with self.assertRaises(Rejected):
                apply(**args)
        self.assertEqual(lane, self.reg.status()['lanes']['one'])

    def candidate(self):
        lane = self.ready(runtime=True, reviews=True)
        candidate = self.reg.publish_candidate('one', 1, lane['revision'], 'v1')
        qa = self.running('two')
        with self.reg.transaction() as state:
            state['lanes']['two']['task_id'] = 'opencode:session-two'
        qa = self.reg.checkpoint('two', 1, qa['revision'], {'state': 'blocked', 'dependencies': ['one']})
        self.reg.subscribe_candidate_qa('two', 1, qa['revision'], 'one', 'session-two')
        return lane, qa, candidate

    def test_candidate_qa_preserves_dependencies_replays_unbound_claim(self):
        lane, qa, candidate = self.candidate()
        before = self.reg.status()['lanes']['two']
        ready = self.reg.candidate_qa_ready()
        self.assertEqual(1, len(ready))
        claim = self.reg.claim_candidate_qa('two', 1, qa['revision'], candidate['pin'])
        self.assertEqual(claim, self.reg.claim_candidate_qa('two', 1, qa['revision'], candidate['pin']))
        self.assertEqual(1, len(self.reg.candidate_qa_ready()))
        result = self.reg.record_candidate_qa('two', 1, candidate['pin'], 'PASS', self.evidence)
        self.assertTrue(result['provisional'])
        self.assertFalse(result['gameplay_accepted'])
        self.assertFalse(result['integrated'])
        self.assertEqual(before, self.reg.status()['lanes']['two'])
        self.assertEqual([], self.reg.candidate_qa_ready())

    def test_superseded_candidate_invalidates_results_and_rejects_replay(self):
        lane, qa, old = self.candidate()
        self.reg.claim_candidate_qa('two', 1, qa['revision'], old['pin'])
        self.reg.record_candidate_qa('two', 1, old['pin'], 'PASS', self.evidence)
        new = self.reg.publish_candidate('one', 1, lane['revision'], 'v2')
        self.assertNotEqual(old['pin'], new['pin'])
        with self.assertRaises(Rejected):
            self.reg.record_candidate_qa('two', 1, old['pin'], 'PASS', self.evidence)
        with self.reg.transaction() as state:
            self.assertFalse(state['throughput']['qa']['two']['attempts'][old['pin']]['valid'])
        self.assertEqual(new['pin'], self.reg.candidate_qa_ready()[0]['pin'])

    def test_candidate_replay_validates_hash_and_live_qa_is_not_ready(self):
        lane, qa, candidate = self.candidate()
        self.assertEqual(candidate, self.reg.publish_candidate('one', 1, lane['revision'], 'v1'))
        self.health = 'alive'
        self.assertEqual([], self.reg.candidate_qa_ready())
        with self.assertRaises(Rejected):
            self.reg.claim_candidate_qa('two', 1, qa['revision'], candidate['pin'])
        self.health = 'dead'
        path = self.root / candidate['snapshot']['evidence']['exe']['path']
        path.write_bytes(b'changed executable')
        with self.assertRaises(Rejected):
            self.reg.publish_candidate('one', 1, lane['revision'], 'v1')

    def test_bound_launch_suppresses_second_dispatch(self):
        lane, qa, candidate = self.candidate()
        self.reg.claim_candidate_qa('two', 1, qa['revision'], candidate['pin'])
        with self.reg.transaction() as state:
            self.reg.control(state)['launches']['launch-one'] = dict(lane='two', generation=1, status='completed', session='session-two', version=candidate['pin'], reason='candidate_qa:' + candidate['pin'], instruction='QA pin ' + candidate['pin'])
        bound = self.reg.bind_candidate_qa_launch('two', candidate['pin'], 'launch-one')
        self.assertEqual('launch-one', bound['launch_id'])
        self.assertEqual([], self.reg.candidate_qa_ready())
        with self.assertRaises(Rejected):
            self.reg.claim_candidate_qa('two', 1, qa['revision'], candidate['pin'])

    def test_real_launch_binding_accepts_only_bound_generation(self):
        lane, qa, candidate = self.candidate()
        candidate_pin = candidate['pin']
        self.reg.claim_candidate_qa('two', 1, qa['revision'], candidate_pin)
        launch = self.reg.plan_launch('two', 'candidate_qa:' + candidate_pin,
                                      'Provisional QA ' + candidate_pin, ['paid/muse'], candidate_pin)
        # Crash after durable intent before the QA binding remains recoverable.
        self.assertEqual(1, len(self.reg.candidate_qa_ready()))
        self.reg.claim_candidate_qa('two', 1, qa['revision'], candidate_pin)
        self.reg.bind_candidate_qa_launch('two', candidate_pin, launch['id'])
        process = {'pid': 9999, 'started': 'new', 'host': 'synthetic'}
        self.reg.probe = lambda value: 'alive' if value == process else 'dead'
        resumed = self.reg.bind_launch(launch['id'], process)
        self.assertEqual(2, resumed['generation'])
        self.assertEqual(['one'], resumed['dependencies'])
        result = self.reg.record_candidate_qa('two', 2, candidate_pin, 'PASS', self.evidence)
        self.assertTrue(result['provisional'])
        with self.assertRaises(Rejected):
            self.reg.record_candidate_qa('two', 1, candidate_pin, 'PASS', self.evidence)

    def test_snapshot_refuses_stale_generation_and_source_drift(self):
        lane = self.ready()
        with self.assertRaises(Rejected):
            self.reg.snapshot_handoff('one', 2, lane['revision'], 'v1')
        self.log.write_text('source drift')
        with self.assertRaises(Rejected):
            self.reg.snapshot_handoff('one', 1, lane['revision'], 'v1')

    def test_atomic_queue_is_idempotent_and_retains_integration_dependency(self):
        lane, qa, candidate = self.candidate()
        args = ('two', 1, qa['revision'], candidate['pin'], 'QA ' + candidate['pin'], ['paid/muse'])
        launch = self.reg.queue_candidate_qa(*args)
        self.assertEqual(launch, self.reg.queue_candidate_qa(*args))
        self.assertEqual([], self.reg.candidate_qa_ready())
        state = self.reg.status()
        self.assertEqual(['one'], state['lanes']['two']['dependencies'])
        self.assertEqual(1, len(self.reg.control_status()['launches']))


if __name__ == '__main__':
    unittest.main()

