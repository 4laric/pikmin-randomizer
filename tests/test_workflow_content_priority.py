"""Existing actionable work precedes new content without blocking spare capacity."""
import copy
import unittest
from unittest.mock import patch

from tests import test_pikmin2_controller as fixtures
from workflow.handoff import Rejected
from workflow.scheduling import job_priority
from workflow.throughput_controller import pool_tick


class ContentPriorityTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ControllerTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.reg, self.controller = self.fixture.reg, self.fixture.controller
        self.fixture.add_lane('expansion', 3)
        self.controller.config['lanes']['expansion'] = copy.deepcopy(self.controller.config['lanes']['consumer'])
        self.controller.config['throughput'] = dict(enabled=True, provisional_qa=False, capture_costs=False)
        self.controller.config.update(ram_high=90, ram_low=87)
        with self.reg.transaction() as state:
            state['lanes']['provider']['process'] = self.fixture.identity
        self.reg.set_workstream('p2', 'provider')
        # Register expansion first to catch insertion-order bias.
        for key in ('expansion', 'consumer'):
            self.reg.register_pool_worker(key, ['review', 'implementation'], [], 'test orchestrator')

    def enqueue(self, key, role='review', work_class=None):
        record = dict(id=key, lane=key, issue=self.reg.status()['lanes'][key]['issue'],
                      workstream='p2', role=role, instruction='Complete scoped issue work')
        if work_class is not None:
            record['work_class'] = work_class
        return self.reg.enqueue_job(record)

    def test_default_existing_and_invalid_class(self):
        self.assertEqual(self.enqueue('consumer')['work_class'], 'existing')
        for value in ('urgent', [], 1):
            with self.assertRaises(Rejected):
                self.enqueue('expansion', work_class=value)

    def test_job_order_class_before_role_then_fifo(self):
        jobs = [dict(id='new', role='repair', work_class='expansion', queued_at=1),
                dict(id='old', role='implementation', queued_at=10),
                dict(id='review', role='review', queued_at=11)]
        self.assertEqual([j['id'] for j in sorted(jobs, key=job_priority)], ['review', 'old', 'new'])

    def test_pool_prefers_existing_implementation_over_expansion_review(self):
        self.enqueue('expansion', work_class='expansion')
        self.enqueue('consumer', role='implementation')
        pool_tick(self.controller)
        launches = list(self.reg.control_status()['launches'].values())
        self.assertEqual([l['lane'] for l in launches], ['consumer'])
        self.assertEqual(launches[0]['work_class'], 'existing')

    def test_running_existing_does_not_block_expansion(self):
        self.enqueue('consumer')
        self.enqueue('expansion', work_class='expansion')
        with self.reg.transaction() as state:
            state['lanes']['consumer']['process'] = self.fixture.identity
        pool_tick(self.controller)
        launches = list(self.reg.control_status()['launches'].values())
        self.assertEqual([l['lane'] for l in launches], ['expansion'])
        self.assertEqual(launches[0]['work_class'], 'expansion')
        self.assertEqual(self.reg.status()['lanes']['consumer']['generation'], 1)

    def test_blocked_existing_does_not_block_expansion(self):
        self.enqueue('consumer')
        self.enqueue('expansion', work_class='expansion')
        self.reg.finish('consumer', 1, 'blocked', 'Needs unavailable dependency', self.fixture.ev, ['#999'])
        pool_tick(self.controller)
        self.assertEqual([l['lane'] for l in self.reg.control_status()['launches'].values()], ['expansion'])

    def tick_only_dispatch(self):
        # Exercise the real generic priority/dispatch path; isolate unrelated
        # shepherd/recovery work that is covered by its own existing tests.
        names = ('receipts', 'complete_runs', 'dependencies', 'observe', 'shepherd', 'deliver_notifications')
        patches = [patch.object(self.controller, name) for name in names]
        for active in patches:
            active.start()
            self.addCleanup(active.stop)
        with patch('workflow.provider_recovery.recover'), patch('workflow.throughput_controller.pool_tick'):
            self.controller.tick()

    def test_generic_legacy_intent_precedes_earlier_expansion_intent(self):
        self.enqueue('expansion', work_class='expansion')
        assignment = self.reg.assign_job('expansion', 60)
        new = self.reg.plan_assignment(assignment['id'], self.controller.config['models'], 60)
        old = self.reg.plan_launch('consumer', 'dependency_ready', 'Resume existing slice', self.controller.config['models'])
        self.tick_only_dispatch()
        launches = self.reg.control_status()['launches']
        self.assertEqual(launches[old['id']]['status'], 'running')
        self.assertEqual(launches[new['id']]['status'], 'intent')
        self.assertEqual(len(self.fixture.spawns), 1)

    def test_unavailable_existing_intent_does_not_starve_expansion(self):
        self.enqueue('expansion', work_class='expansion')
        assignment = self.reg.assign_job('expansion', 60)
        new = self.reg.plan_assignment(assignment['id'], self.controller.config['models'], 60)
        old = self.reg.plan_launch('consumer', 'legacy', 'Continue existing work', self.controller.config['models'])
        self.controller.config['lanes']['consumer']['legacy_supervisors'] = [self.fixture.identity]
        self.tick_only_dispatch()
        launches = self.reg.control_status()['launches']
        self.assertEqual(launches[old['id']]['status'], 'intent')
        self.assertEqual(launches[new['id']]['status'], 'running')
        self.assertEqual(len(self.fixture.spawns), 1)

    def test_old_queued_records_without_class_replay_as_existing(self):
        self.enqueue('consumer')
        with self.reg.transaction() as state:
            del state['throughput']['jobs']['consumer']['work_class']
        self.enqueue('consumer')  # Backwards-compatible idempotent request.
        assignment = self.reg.assign_job('consumer', 60)
        self.assertEqual(self.reg.plan_assignment(assignment['id'], self.controller.config['models'], 60)['work_class'], 'existing')


if __name__ == '__main__':
    unittest.main()
