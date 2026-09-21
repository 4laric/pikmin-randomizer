import threading
import unittest
from unittest.mock import patch
from tests import test_pikmin2_controller as fixtures
from workflow.fast_dispatch import model_choices, start_monitor, run_cycle


class FastDispatchTests(unittest.TestCase):
    def test_assignment_releases_blocked_capacity_before_assigning_without_maintenance(self):
        order=[]
        with patch('workflow.worker_capacity.park_blocked',side_effect=lambda reg:order.append('park')), \
             patch('workflow.helper_preparation.refresh_reservations',side_effect=lambda reg:order.append('counts')), \
             patch('workflow.throughput_controller.assign_pending',side_effect=lambda c:order.append('assign')), \
             patch.object(self.c,'complete_runs',side_effect=AssertionError('slow maintenance')):
            run_cycle(self.c,'assignment')
        self.assertEqual(order,['park','counts','assign'])

    def test_idle_workers_without_jobs_do_not_trigger_assignment_probes(self):
        from workflow.throughput_controller import assign_pending
        self.c.config['throughput']={'enabled':True}
        with patch.object(self.r,'scheduling_status',return_value=dict(jobs={},assignments={},workers={
                str(i):dict(worker_id=str(i)) for i in range(30)})), \
             patch.object(self.r,'assign_job') as assign:
            assign_pending(self.c)
        assign.assert_not_called()

    def test_independent_stage_failure_does_not_stop_dispatch_and_recovers(self):
        with patch.object(self.c,'complete_runs',side_effect=ValueError('bad terminal report')), \
             patch.object(self.c,'dispatch_pending') as dispatch:
            run_cycle(self.c)
            dispatch.assert_called_once()
        self.assertEqual(self.c._dispatch_stage_health['completion']['failures'],1)
        self.assertEqual(self.c._dispatch_stage_health['dispatch']['status'],'ok')
        with patch.object(self.c,'complete_runs'),patch.object(self.c,'dispatch_pending'):
            run_cycle(self.c)
        self.assertEqual(self.c._dispatch_stage_health['completion']['failures'],0)

    def setUp(self):
        self.f = fixtures.ControllerTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.c, self.r = self.f.controller, self.f.reg
        self.f.config['provider_fallbacks'] = {'free/muse': 'paid/muse'}

    def test_first_provider_failure_pins_fallback_even_when_cooling(self):
        first = self.f.plan()
        with self.r.transaction() as s:
            s['control']['launches'][first['id']].update(model='free/muse', status='exited')
        follow = self.r.plan_launch('consumer', 'provider fallback:' + first['id'], 'Continue', self.f.config['models'])
        self.assertEqual(model_choices(self.c, follow), ['paid/muse'])
        self.r.model_rate_limit('paid/muse', 'other', initial=60)
        self.assertFalse(self.c.dispatch(follow))
        self.assertEqual(self.f.spawns, [])
        self.f.now += 60
        self.assertTrue(self.c.dispatch(follow))
        self.assertEqual(self.r.control_status()['launches'][follow['id']]['model'], 'paid/muse')

    def test_permission_failure_does_not_pin_provider(self):
        first = self.f.plan()
        with self.r.transaction() as s:
            s['control']['launches'][first['id']].update(model='free/muse', status='exited')
        follow = self.r.plan_launch('consumer', 'permission-repair:' + first['id'], 'Continue', self.f.config['models'])
        self.assertEqual(model_choices(self.c, follow), self.f.config['models'])

    def test_monitor_dispatches_without_scheduler_and_has_one_owner(self):
        observed = threading.Event()
        with patch.object(self.c, 'complete_runs') as complete, \
                patch.object(self.c, 'dispatch_pending', side_effect=lambda n: observed.set()) as dispatch:
            stop = start_monitor(self.c)
            try:
                self.assertIs(start_monitor(self.c), stop)
                self.assertTrue(observed.wait(3))
                # Maintenance runs independently and need not precede launch.
                dispatch.assert_called_once()
                with patch('workflow.throughput_controller.pool_tick'):
                    self.c.tick()
                dispatch.assert_called_once()
            finally:
                stop.set()
                for thread in self.c._dispatch_threads:thread.join(3)

    def test_launch_does_not_wait_for_slow_maintenance_or_assignment(self):
        blocked=threading.Event();release=threading.Event();launched=threading.Event()
        def slow(*args):blocked.set();release.wait(3)
        with patch.object(self.c,'complete_runs',side_effect=slow), \
             patch('workflow.throughput_controller.assign_pending',side_effect=slow), \
             patch.object(self.c,'dispatch_pending',side_effect=lambda n:launched.set()):
            stop=start_monitor(self.c)
            try:
                self.assertTrue(blocked.wait(1))
                self.assertTrue(launched.wait(1),'Launch blocked behind independent maintenance')
            finally:
                stop.set();release.set()
                for thread in self.c._dispatch_threads:thread.join(3)

    def test_unchanged_ram_check_avoids_writer_but_hysteresis_still_updates(self):
        self.c.memory=lambda:50
        self.c.capacity()
        with patch.object(self.r,'transaction',side_effect=AssertionError('unnecessary writer')):
            self.assertTrue(self.c.capacity())
        self.c.memory=lambda:99
        self.assertFalse(self.c.capacity())
        self.c.memory=lambda:50
        self.assertTrue(self.c.capacity())
