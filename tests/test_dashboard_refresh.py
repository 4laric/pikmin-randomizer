import json
import threading
import unittest
from unittest.mock import patch

from tests import test_pikmin2_controller as fixtures
from workflow.dashboard_refresh import start_monitor


class DashboardRefreshTests(unittest.TestCase):
    def test_independent_publisher_retries_failure_and_starts_only_once(self):
        f = fixtures.ControllerTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        f.config['dashboard_refresh_seconds'] = 5
        observed = threading.Event()
        calls = []
        def publish(controller):
            calls.append(1)
            if len(calls) == 1:
                raise ValueError('temporary reader failure')
            observed.set()
        with patch('workflow.throughput_controller.publish_status', side_effect=publish):
            stop = start_monitor(f.controller)
            try:
                self.assertIs(start_monitor(f.controller), stop)
                # No scheduler tick is running; publishing still recovers.
                self.assertTrue(observed.wait(8))
                self.assertEqual(len(calls), 2)
                error = json.loads((f.controller.base / 'dashboard-refresh-error.json').read_text())
                self.assertEqual(error['error'], 'temporary reader failure')
            finally:
                stop.set()

    def test_main_tick_does_not_compete_with_monitor(self):
        f = fixtures.ControllerTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        f.config['throughput'] = dict(enabled=True)
        f.controller._dashboard_monitor = threading.Event()
        with patch('workflow.throughput_controller.pool_tick'), \
                patch('workflow.throughput_controller.publish_status') as publish:
            f.controller.tick()
        publish.assert_not_called()
