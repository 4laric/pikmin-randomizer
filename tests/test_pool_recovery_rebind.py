"""Recovery binding preserves pool ownership across real generation transitions."""
import copy
import unittest

from tests import test_workflow_throughput_integration as fixtures
from workflow.handoff import Rejected
from workflow.throughput_controller import pool_tick


class PoolRecoveryRebindTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ThroughputIntegrationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.reg = self.fixture.reg
        pool_tick(self.fixture.controller)
        self.old = next(iter(self.reg.control_status()['launches'].values()))
        self.fixture.controller.dispatch(self.old)
        self.old = copy.deepcopy(self.reg.control_status()['launches'][self.old['id']])
        self.new_process = {'host': 'fixture', 'pid': 999999, 'started': 'new-runner'}
        self.reg.probe = lambda p: 'alive' if p == self.new_process else 'dead'
        with self.reg.transaction() as state:
            state['control']['launches'][self.old['id']]['status'] = 'exited'
            state['lanes']['consumer']['state'] = 'reconciling'
        self.old['status'] = 'exited'
        self.new = self.reg.plan_launch('consumer', 'permission-stall', 'Continue existing work', ['paid/muse'])

    def assignment(self):
        return next(iter(self.reg.scheduling_status()['assignments'].values()))

    def bind(self):
        return self.reg.bind_launch(self.new['id'], self.new_process)

    def test_rebind_is_atomic_and_idempotent_preserving_old_launch(self):
        lane = self.bind()
        item = copy.deepcopy(self.assignment())
        self.assertEqual(item['launch_id'], self.new['id'])
        self.assertEqual(item['generation'], lane['generation'])
        self.assertEqual(len(item['recovery_history']), 1)
        self.assertEqual(self.reg.control_status()['launches'][self.old['id']], self.old)
        self.bind()
        self.reg.reconcile_pool_recovery(self.new['id'])
        self.assertEqual(self.assignment(), item)

    def test_reconcile_already_bound_running_recovery_without_worker_change(self):
        with self.reg.transaction() as state:
            lane = state['lanes']['consumer']
            lane.update(generation=lane['generation']+1, revision=lane['revision']+1, state='running', process=self.new_process)
            state['control']['launches'][self.new['id']].update(status='running', process=self.new_process, bound_generation=lane['generation'])
        before = copy.deepcopy(self.reg.status()['lanes']['consumer'])
        self.reg.reconcile_pool_recovery(self.new['id'])
        self.assertEqual(self.reg.status()['lanes']['consumer'], before)
        self.assertEqual(self.assignment()['launch_id'], self.new['id'])

    def test_wrong_session_generation_or_unexited_launch_refused(self):
        cases = [('session', 'unrelated-session'), ('bound_generation', 999), ('status', 'running')]
        for field, value in cases:
            with self.subTest(field=field):
                with self.reg.transaction() as state:
                    state['control']['launches'][self.old['id']][field] = value
                with self.assertRaises(Rejected): self.bind()
                self.assertEqual(self.reg.status()['lanes']['consumer']['generation'], self.old['bound_generation'])
                self.assertEqual(self.assignment()['launch_id'], self.old['id'])
                with self.reg.transaction() as state:
                    state['control']['launches'][self.old['id']][field] = self.old[field]

    def test_wrong_worker_and_duplicate_assignment_refused(self):
        identity = self.assignment()['id']
        with self.reg.transaction() as state:
            state['throughput']['assignments'][identity]['worker_id'] = 'different-worker'
        with self.assertRaises(Rejected): self.bind()
        with self.reg.transaction() as state:
            records = state['throughput']['assignments']
            records[identity]['worker_id'] = 'consumer'
            records['duplicate'] = copy.deepcopy(records[identity])
        with self.assertRaises(Rejected): self.bind()
        self.assertEqual(self.assignment()['launch_id'], self.old['id'])

    def test_stale_historical_reconcile_cannot_capture_new_execution(self):
        self.bind()
        with self.reg.transaction() as state:
            state['lanes']['consumer']['generation'] += 1
        with self.assertRaises(Rejected): self.reg.reconcile_pool_recovery(self.new['id'])

    def test_completion_succeeds_after_recovery_with_applied_disposition(self):
        lane = self.bind()
        evidence = self.fixture.fixture.ev
        self.reg.finish('consumer', lane['generation'], 'review-ready', 'Recovered review', evidence)
        self.reg.accept_review('consumer', lane['generation'], 'Applied review', evidence)
        self.reg.probe = lambda p: 'dead'
        with self.reg.transaction() as state:
            state['control']['launches'][self.new['id']]['status'] = 'exited'
        result = self.reg.complete_assignment(self.assignment()['id'], evidence)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(self.reg.scheduling_status()['jobs']['review-one']['status'], 'completed')


if __name__ == '__main__':
    unittest.main()
