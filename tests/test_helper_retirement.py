import unittest
from tests import test_planner_pool as fixtures
from workflow.helper_retirement import tick
from workflow.handoff import digest


class HelperRetirementTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.PlannerPoolTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.f.tick();self.r=self.f.reg
        report=self.f.root/'output/blocked-report.txt';report.write_text('Missing actual input')
        self.r.finish('next-cycle-1',1,'blocked','Input remains missing',dict(path=str(report),sha256=digest(report)),['#999'])
        with self.r.transaction() as s:s['lanes']['next-cycle-1']['target_level']='planning-only'
        self.r.probe=lambda p:'dead'

    def test_retirement_preserves_failure_and_does_not_integrate(self):
        tick(self.r);first=self.r.snapshot()['lanes']['next-cycle-1'];tick(self.r)
        self.assertEqual(first,self.r.snapshot()['lanes']['next-cycle-1'])
        self.assertEqual(first['state'],'done')
        self.assertFalse(first['review_disposition']['resolved'])
        self.assertEqual(first['outcome']['outcome'],'blocked')
        self.assertEqual(first['dependencies'],['#999'])
        self.assertFalse(first.get('integration'))

    def test_live_unknown_and_implementation_are_not_retired(self):
        for health in ('alive','unknown'):
            self.r.probe=lambda p:health;tick(self.r)
            self.assertEqual(self.r.snapshot()['lanes']['next-cycle-1']['state'],'blocked')
        self.r.probe=lambda p:'dead'
        with self.r.transaction() as s:s['lanes']['next-cycle-1']['target_level']='runtime'
        tick(self.r);self.assertEqual(self.r.snapshot()['lanes']['next-cycle-1']['state'],'blocked')
