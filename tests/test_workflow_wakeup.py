import json
from pathlib import Path
import tempfile
import unittest

from workflow.registry import Registry
from workflow.wakeup import EventWaiter


class WakeupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.reg = Registry(self.root / 'output/registry.sqlite3', self.root)
        self.reg.init()
        self.mail = self.root / 'output/inbox'
        self.mail.mkdir()
        self.waiter = EventWaiter(self.reg.path, [self.mail], self.root / 'output/STOP')

    def test_read_only_status_does_not_wake(self):
        cursor = self.waiter.token()
        self.reg.status()
        self.assertEqual(self.waiter.wait(0, cursor)['reason'], 'timeout')

    def test_registry_event_wakes_with_existing_cursor(self):
        cursor = self.waiter.token()
        with self.reg.transaction() as state:
            self.reg.event(state, 'test', None)
        self.assertEqual(self.waiter.wait(0, cursor)['reason'], 'changed')

    def test_mailbox_arrival_and_stop(self):
        cursor = self.waiter.token()
        (self.mail / 'approval.md').write_text('ADMIT 54')
        self.assertEqual(self.waiter.wait(0, cursor)['reason'], 'changed')
        (self.root / 'output/STOP').touch()
        self.assertEqual(self.waiter.wait(0)['reason'], 'stopped')

    def test_bounded_wait_and_poll_observes_new_mail(self):
        now = [0.0]
        def sleep(seconds):
            now[0] += seconds
            (self.mail / 'new').write_text('ready')
        waiter = EventWaiter(self.reg.path, [self.mail], clock=lambda: now[0], sleep=sleep)
        self.assertEqual(waiter.wait(15)['reason'], 'changed')
        self.assertLessEqual(now[0], .5)
        for value in [-1, 61, True, float('nan')]:
            with self.assertRaises(ValueError):
                waiter.wait(value)

    def test_paced_wait_holds_a_change_wake_to_the_minimum_tick_spacing(self):
        now = [100.0]
        def sleep(seconds):
            now[0] += seconds
            with self.reg.transaction() as state: self.reg.event(state, 'test', None)
        waiter = EventWaiter(self.reg.path, [], self.root / 'output/STOP', clock=lambda: now[0], sleep=sleep)
        self.assertEqual(waiter.paced(15, 99.0, 5)['reason'], 'changed')
        self.assertGreaterEqual(now[0], 104.0); self.assertLess(now[0], 105.0)  # Not the 15 s timeout.
        now[0] = 200.0
        self.assertEqual(waiter.paced(15, 190.0, 5)['reason'], 'changed'); self.assertEqual(now[0], 200.5)
        (self.root / 'output/STOP').touch(); now[0] = 300.0
        self.assertEqual(waiter.paced(15, 300.0, 5)['reason'], 'stopped'); self.assertEqual(now[0], 300.0)
        for value in [-1, 16, True]:
            with self.assertRaises(ValueError): waiter.paced(15, 0, value)


if __name__ == '__main__':
    unittest.main()
