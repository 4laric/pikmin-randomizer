import threading
import unittest
from unittest.mock import patch
from tests import test_workflow_autofill as fixtures
from workflow.helper_refill import start_monitor
from workflow.autofill import autofill_status


class HelperRefillTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.AutofillTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def test_preparation_runs_without_scheduler_and_main_does_not_duplicate(self):
        seen = threading.Event()
        with patch('workflow.planner_pool.tick', side_effect=lambda *a: seen.set()) as tick:
            stop = start_monitor(self.f.controller)
            try:
                self.assertIs(start_monitor(self.f.controller), stop)
                self.assertTrue(seen.wait(3))
                self.f.tick()
                tick.assert_called_once()
            finally:
                stop.set()

    def test_current_lane_state_replaces_stale_reservation_count(self):
        with self.f.reg.transaction() as state:
            from workflow.autofill import _state
            _state(state)['planner_pool'] = dict(active=99, scopes={
                'finished': dict(spec={'lane': {'lane': 'one'}}),
                'pending': dict(spec={'lane': {'lane': 'not-yet-provisioned'}})})
        status = autofill_status(self.f.reg)['planner_pool']
        self.assertEqual(status['active'], 1)
        self.assertEqual(status['recovery'], 0)
        self.assertEqual(status['prepared'], 1)
