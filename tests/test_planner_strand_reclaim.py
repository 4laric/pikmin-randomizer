"""Bounded reclaim of stranded prerequisite-recovery chains (planner_strand_reclaim)."""
import copy
import os
import tempfile
import unittest
from pathlib import Path

from workflow.control import fingerprint
from workflow.dependency_classification import signature
from workflow.operator import strand_reclaim_action, report
from workflow.planner_strand_reclaim import RECLAIM_HISTORY, apply, plan
from workflow.registry import Registry


def lane_record(key, issue, deps, state='blocked'):
    return dict(lane=key, state=state, issue=issue, dependencies=deps,
                root=dict(head='a' * 40), native=None, generation=1, revision=1,
                next_action='waiting on prerequisite')


class PlannerStrandReclaimTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.reg = Registry(self.root / 'output/coord/registry.sqlite3', self.root,
                            clock=lambda: 1000.0, process_probe=lambda _: 'alive')
        self.reg.init(dict(max_heavy_builds=1, heartbeat_seconds=10, progress_seconds=30))

    def classification_state(self, helper_state='done'):
        consumer = lane_record('consumer-x', 123, ['#1 missing thing'])
        helper = lane_record('helper', 1, [], state=helper_state)
        snapshot = signature(consumer)
        identity = 'classification-v2:' + fingerprint(['consumer-x', snapshot])
        state = dict(
            lanes={'consumer-x': consumer, 'helper': helper},
            throughput=dict(workstreams={}),
            throughput_runtime={'autofill': {'prerequisite_recovery': {
                identity: dict(scope='s', request_id=identity, input_snapshot=snapshot,
                               lane='helper', created_at=1)}}},
            dependency_classifications={}, delivery_contracts={},
            support_actions={}, consumer_verifications={})
        return state, identity, snapshot

    def internal_state(self, helper_state='done'):
        consumer = lane_record('consumer-x', 123, ['#1 missing thing'])
        helper = lane_record('helper', 1, [], state=helper_state)
        snapshot = signature(consumer)
        finding = dict(requirement='#1 missing thing', check='run the consumer', reason='none exists',
                       internal_blocker=dict(kind='missing_producer', missing='exact artifact',
                                             next_action='stage a bounded producer', inspected_lanes=[]))
        row = dict(consumer='consumer-x', snapshot=snapshot, reviewer='helper', generation=1,
                   dispositions=[finding], evidence=dict(path='output/reports/r.md', sha256='b' * 64),
                   id='cls-1', at=5)
        identity = 'internal-followup:' + fingerprint(['consumer-x', snapshot])
        state = dict(
            lanes={'consumer-x': consumer, 'helper': helper},
            throughput=dict(workstreams={}),
            throughput_runtime={'autofill': {'prerequisite_recovery': {
                identity: dict(scope='s', request_id=identity, input_snapshot=snapshot,
                               lane='helper', created_at=1)}}},
            dependency_classifications={'cls-1': row}, delivery_contracts={},
            support_actions={}, consumer_verifications={})
        return state, identity

    def seed_registry(self, state):
        with self.reg.transaction() as current:
            for key in ('lanes', 'throughput', 'throughput_runtime',
                        'dependency_classifications', 'delivery_contracts',
                        'support_actions', 'consumer_verifications'):
                current[key] = copy.deepcopy(state[key])

    def test_classification_strand_is_detected_and_reclaimed_once(self):
        state, identity, _ = self.classification_state()
        strands = plan(state)
        self.assertEqual([s['identity'] for s in strands], [identity])
        self.assertEqual(strands[0]['kind'], 'classification')
        self.seed_registry(state)
        applied = apply(self.reg)
        self.assertEqual([s['identity'] for s in applied], [identity])
        after = self.reg.snapshot()
        self.assertNotIn(identity, after['throughput_runtime']['autofill']['prerequisite_recovery'])
        history = after['throughput_runtime']['autofill'][RECLAIM_HISTORY]
        self.assertEqual(history[identity]['prior']['lane'], 'helper')
        self.assertIn('planner_strand_reclaimed', [e['kind'] for e in after['events']])
        self.assertEqual(plan(after), [])
        self.assertEqual(apply(self.reg), [])

    def test_live_helper_is_not_reclaimed(self):
        state, _, _ = self.classification_state(helper_state='running')
        self.assertEqual(plan(state), [])
        self.seed_registry(state)
        self.assertEqual(apply(self.reg), [])

    def test_recorded_classification_is_not_stranded(self):
        state, _, snapshot = self.classification_state()
        state['dependency_classifications'] = {'c1': dict(consumer='consumer-x', snapshot=snapshot,
            dispositions=[], evidence=dict(path='p', sha256='c' * 64), id='c1', at=1,
            reviewer='helper', generation=1)}
        self.assertEqual(plan(state), [])

    def test_internal_followup_strand_is_detected(self):
        state, identity = self.internal_state()
        strands = plan(state)
        self.assertEqual([s['identity'] for s in strands], [identity])
        self.assertEqual(strands[0]['kind'], 'internal-follow-up')

    def test_delivered_support_action_prevents_internal_reclaim(self):
        state, identity = self.internal_state()
        state['support_actions'] = {'a1': dict(reviewer='helper', key='consumer-x', action='proposal')}
        self.assertEqual(plan(state), [])

    def test_operator_action_surfaces_strands(self):
        state, identity, _ = self.classification_state()
        action = strand_reclaim_action(state)
        self.assertEqual(action['priority'], 1)
        self.assertEqual(action['lane'], 'planner-strand-reclaim')
        self.assertEqual(len(action['strands']), 1)
        self.assertIn('workflow.planner_strand_reclaim', action['next_action'])
        self.assertIsNone(strand_reclaim_action(dict(lanes={}, throughput_runtime={})))

    def test_report_includes_strand_action(self):
        state, _, _ = self.classification_state()
        with tempfile.TemporaryDirectory() as directory:
            data = report(state, 50, Path(directory))
        self.assertTrue([a for a in data['actions'] if a['lane'] == 'planner-strand-reclaim'])

    def test_registry_round_trip_preserves_strand_history(self):
        state, identity, _ = self.classification_state()
        self.seed_registry(state)
        apply(self.reg)
        reloaded = self.reg.snapshot()
        self.assertIn(identity, reloaded['throughput_runtime']['autofill'][RECLAIM_HISTORY])


if __name__ == '__main__':
    unittest.main()
