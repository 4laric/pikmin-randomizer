import unittest

from tests import test_workflow_scheduling as fixtures
from workflow.handoff import Rejected
from workflow.autofill import _workers


class PlanningSupersessionTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.SchedulingTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.reg = self.f.reg
        self.old, self.new = 'planning-shard-test-cycle-1', 'planning-shard-test-cycle-2'
        self.f.add_lane(self.old, worker='planner')
        self.f.add_lane(self.new, worker='successor')
        self.reg.register_pool_worker('planner', ['review'], ['python'], 'test')
        with self.reg.transaction() as state:
            old, new = state['lanes'][self.old], state['lanes'][self.new]
            old.update(state='done', target_level='planning-only', outcome=dict(outcome='reconcile', evidence=self.f.evidence))
            new.update(**{k:old[k] for k in ('issue', 'scope', 'owned_files', 'target_level')}, state='done',
                       review_disposition=dict(summary='No-work report reviewed', evidence=self.f.evidence))
            state.setdefault('control', {})['launches'] = {'launch':dict(lane=self.old, status='exited',
                bound_generation=old['generation'], process=old['process'])}
            state['throughput']['jobs']['job'] = dict(role='review', status='assigned')
            state['throughput']['assignments']['assignment'] = dict(id='assignment', lane=self.old,
                worker_id='planner', status='dispatched', launch_id='launch', job='job')

    def retire(self, health='dead'):
        return self.reg.supersede_planning_assignment('assignment', {'health':health})

    def test_retirement_releases_worker_without_accepted_output(self):
        self.assertEqual(self.retire()['status'], 'superseded')
        self.assertEqual(self.retire()['status'], 'superseded')
        self.assertEqual(self.reg.status()['metrics']['completed_slices'], 0)
        with self.reg.transaction() as state:
            self.assertIsNone(state['lanes'][self.old].get('review_disposition'))
            self.assertIn('planner', [v['worker_id'] for v in _workers(self.reg, state)])

    def test_live_or_unknown_child_and_claims_stay_fenced(self):
        for health in ('alive', 'unknown'):
            with self.assertRaises(Rejected): self.retire(health)
        with self.reg.transaction() as state:
            state['planning_claims'] = {'topic:test':dict(lane=self.old)}
        with self.assertRaises(Rejected): self.retire()

    def test_unrelated_successor_or_implementation_cannot_retire(self):
        with self.reg.transaction() as state:
            state['lanes'][self.new]['issue'] += 1
        with self.assertRaises(Rejected): self.retire()
        with self.reg.transaction() as state:
            state['lanes'][self.old]['target_level'] = 'runtime'
        with self.assertRaises(Rejected): self.retire()
