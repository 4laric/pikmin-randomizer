import os
from types import SimpleNamespace
import unittest

from tests.test_workflow_scheduling import SchedulingTests
from workflow.build_capacity import update
from workflow.analytics import staffing_recommendations, _build_utilization


class BuildCapacityTests(unittest.TestCase):
    setUp = SchedulingTests.setUp
    add_lane = SchedulingTests.add_lane
    job = SchedulingTests.job

    def enable(self, ram=60):
        self.now = 1000
        self.reg.clock = lambda: self.now
        self.controller = SimpleNamespace(reg=self.reg, memory=lambda:ram,
            config={'build_capacity': {'enabled': True, 'base': 1, 'maximum': 3}})
        update(self.controller)

    def second(self):
        self.add_lane('two')
        self.reg.register_pool_worker('two', ['review'], ['python'], 'orchestrator')

    def test_prepare_and_dispatch_while_actual_build_pool_full(self):
        self.enable(); self.second()
        self.assertTrue(self.reg.acquire('owner', 1, 'build:output/owner', os.getpid())['acquired'])
        for key in ('one', 'two'):
            self.reg.enqueue_job(self.job(key, heavy=True))
            assignment = self.reg.assign_job(key, 60)
            self.assertIsNotNone(assignment)
            self.assertEqual(self.reg.plan_assignment(assignment['id'], ['paid/muse'], 60)['status'], 'intent')
        self.assertFalse(self.reg.acquire('one', 1, 'build:output/one', os.getpid())['acquired'])

    def test_growth_capped_with_waiters_and_no_directory_overlap(self):
        self.enable(); self.second()
        self.assertTrue(self.reg.acquire('owner', 1, 'build:output/owner', os.getpid())['acquired'])
        self.assertFalse(self.reg.acquire('one', 1, 'build:output/one', os.getpid())['acquired'])
        update(self.controller)
        self.assertEqual(self.reg.status()['settings']['max_heavy_builds'], 2)
        self.assertTrue(self.reg.acquire('one', 1, 'build:output/one', os.getpid())['acquired'])
        self.assertFalse(self.reg.acquire('two', 1, 'build:output/one', os.getpid())['acquired'])
        for _ in range(5):
            self.now += 61; update(self.controller)
        self.assertEqual(self.reg.status()['settings']['max_heavy_builds'], 3)

    def test_high_ram_and_stale_sample_pause_only_new_builds(self):
        self.enable()
        first = self.reg.acquire('owner', 1, 'build:output/owner', os.getpid())
        self.controller.memory = lambda:88
        update(self.controller)
        self.assertFalse(self.reg.acquire('one', 1, 'build:output/one', os.getpid())['acquired'])
        self.assertTrue(self.reg.acquire('owner', 1, 'build:output/owner', os.getpid())['acquired'])
        self.reg.renew('owner', 1, 'build:output/owner', first['lease']['token'])
        self.controller.memory = lambda:84; update(self.controller)
        with self.reg.transaction() as state: self.assertTrue(state['build_capacity']['paused'])
        self.controller.memory = lambda:70; update(self.controller)
        self.now += 61
        with self.reg.transaction() as state:
            state['settings']['max_heavy_builds'] = 3
        self.assertFalse(self.reg.acquire('one', 1, 'build:output/one', os.getpid())['acquired'])

    def test_dashboard_counts_actual_leases_not_preparation(self):
        self.enable(); self.reg.enqueue_job(self.job(heavy=True)); self.reg.assign_job('one', 60)
        with self.reg.transaction() as state:
            report = staffing_recommendations(state, self.now, 60, process_probe=self.reg.probe)
        self.assertEqual(report['heavy_slots_available'], 1)
        self.assertEqual(report['heavy_leases'], 0)
        self.assertEqual(report['heavy_preparing_lanes'], 1)

    def test_growth_requires_headroom_and_respects_ramp(self):
        self.enable(81)
        with self.reg.transaction() as state:
            state['queue']['test'] = dict(id='test', requested_at=self.now,
                resource='build:output/a', process={'health':'alive'})
        update(self.controller)
        self.assertEqual(self.reg.status()['settings']['max_heavy_builds'], 1)
        self.controller.memory = lambda:60
        update(self.controller)
        self.assertEqual(self.reg.status()['settings']['max_heavy_builds'], 2)
        update(self.controller)
        self.assertEqual(self.reg.status()['settings']['max_heavy_builds'], 2)

    def test_utilization_uses_historical_capacity(self):
        state = dict(settings={'max_heavy_builds':4}, events=[
            dict(kind='lease_acquired', at=0, resource='build:a'),
            dict(kind='build_capacity_changed', at=50, previous=2, capacity=4)])
        self.assertAlmostEqual(_build_utilization(state, 100, 0)['utilization_percent'], 100/3)

    def test_idle_worker_with_preparing_lane_can_expand(self):
        self.enable(); self.second()
        self.reg.enqueue_job(self.job(heavy=True)); self.reg.assign_job('one', 60)
        update(self.controller)
        self.assertEqual(self.reg.status()['settings']['max_heavy_builds'], 2)
        self.now += 61; update(self.controller)
        self.assertEqual(self.reg.status()['settings']['max_heavy_builds'], 2)


if __name__ == '__main__': unittest.main()
