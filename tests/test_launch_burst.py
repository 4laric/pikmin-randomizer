import unittest
from unittest.mock import patch

from tests import test_pikmin2_controller as fixtures
from workflow.launch_budget import reserve
from workflow.handoff import Rejected


class LaunchBurstTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ControllerTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.reg, self.controller = self.f.reg, self.f.controller
        self.f.config.update(models=['paid/muse'], model_launch_burst=4, model_launch_spacing=30,
                             launches_per_tick=4)
        self.items = []
        for i in range(6):
            key = 'burst-' + str(i)
            self.f.add_lane(key, i + 10)
            self.f.config['lanes'][key] = dict(self.f.config['lanes']['consumer'])
            self.items.append(self.reg.plan_launch(key, 'test', 'Bounded work', ['paid/muse']))

    def test_four_same_model_starts_then_window_refills(self):
        self.assertEqual(self.controller.dispatch_pending(4), 4)
        self.assertEqual(len(self.f.spawns), 4)
        self.assertEqual(self.controller.dispatch_pending(4), 0)
        self.f.now += 30
        self.assertEqual(self.controller.dispatch_pending(4), 2)
        self.assertEqual(len(self.f.spawns), 6)

    def test_replay_reservation_is_not_charged_twice(self):
        action = self.items[0]['id']
        reserve(self.reg, action, 'paid/muse', burst=4, spacing=30)
        reserve(self.reg, action, 'paid/muse', burst=4, spacing=30)
        self.assertEqual(self.reg.control_status()['model_launch_windows']['paid/muse']['used'], 1)
        self.assertTrue(self.controller.dispatch(self.items[0]))
        self.assertFalse(self.controller.dispatch(self.items[0]))
        self.assertEqual(len(self.f.spawns), 1)
        self.assertEqual(self.reg.control_status()['model_launch_windows']['paid/muse']['used'], 1)

    def test_cooldowns_and_ram_still_stop_burst(self):
        self.reg.cool_provider('paid', 60)
        self.assertEqual(self.controller.dispatch_pending(4), 0)
        self.f.now += 60
        self.reg.model_rate_limit('paid/muse', 'limit', initial=60)
        self.assertEqual(self.controller.dispatch_pending(4), 0)
        self.f.now += 60
        def spawn(directory):
            self.f.spawns.append(directory)
            from workflow.runner import write
            write(directory / 'runner.json', self.f.identity)
            self.f.memory = 99
        self.controller.spawn = spawn
        self.assertEqual(self.controller.dispatch_pending(4), 1)
        self.assertEqual(len(self.f.spawns), 1)

    def test_early_and_late_pass_share_one_tick_budget(self):
        calls = []
        def dispatch(budget):
            calls.append(budget)
            return 3 if len(calls) == 1 else 0
        with patch.object(self.controller, 'dispatch_pending', side_effect=dispatch), \
                patch('workflow.resource_wakeup.tick', side_effect=lambda c: self.assertEqual(calls, [4])):
            self.controller.tick()
        self.assertEqual(calls, [4, 1])
