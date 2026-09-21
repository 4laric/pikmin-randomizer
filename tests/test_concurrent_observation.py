import unittest
from unittest.mock import patch
from tests import test_pikmin2_controller as fixtures
from workflow.throughput_controller import capture_costs
from workflow.planner_pool import accept_helper_report
from workflow.handoff import Rejected


class ConcurrentObservationTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ControllerTests(); self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def test_admission_during_cost_scan_uses_stable_configuration(self):
        from workflow.handoff import local_path
        def resolve(root, path):
            self.f.config['lanes']['new-lane'] = dict(self.f.config['lanes']['consumer'])
            return local_path(root, path)
        with patch('workflow.throughput_controller.local_path', side_effect=resolve):
            capture_costs(self.f.controller)
        self.assertIn('new-lane', self.f.config['lanes'])

    def test_competing_acceptance_preserves_winning_receipt(self):
        r = self.f.reg
        lane = r.finish('consumer', 1, 'review-ready', 'Report complete', self.f.ev)
        original = r.accept_review
        def accept(*args):
            original('consumer', 1, 'Integrator accepted report', self.f.ev)
            return original(*args)
        with patch.object(r, 'accept_review', side_effect=accept):
            accepted = accept_helper_report(r, lane)
        self.assertEqual(accepted['state'], 'done')
        self.assertEqual(accepted['review_disposition']['summary'], 'Integrator accepted report')

    def test_unaccepted_rejection_is_not_treated_as_success(self):
        r = self.f.reg
        lane = r.finish('consumer', 1, 'review-ready', 'Report complete', self.f.ev)
        with patch.object(r, 'accept_review', side_effect=Rejected('refused')):
            with self.assertRaises(Rejected): accept_helper_report(r, lane)
