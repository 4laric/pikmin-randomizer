import unittest
from tests import test_pikmin2_controller as fixtures
from workflow.outcome_recovery import tick


class OutcomeRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ControllerTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.reg, self.c = self.f.reg, self.f.controller
        self.reg.finish('consumer',1,'reconcile',
            'Worker exited without terminal outcome; inspect existing artifacts before another attempt',self.f.ev)

    def test_single_retry_even_after_second_missing_outcome(self):
        tick(self.c); tick(self.c)
        self.assertEqual(len(self.reg.control_status()['launches']),1)
        with self.reg.transaction() as s:
            for x in s['control']['launches'].values(): x['status']='exited'
        tick(self.c)
        self.assertEqual(len(self.reg.control_status()['launches']),1)

    def test_live_and_unknown_owners_not_restarted(self):
        for health in ('alive','unknown'):
            self.reg.probe=lambda p:health
            tick(self.c)
            self.assertFalse(self.reg.control_status()['launches'])
