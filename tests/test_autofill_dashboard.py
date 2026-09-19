"""Backlog observations render honestly and never become HTML or admissions."""
import unittest

from workflow.dashboard import render_dashboard


class AutofillDashboardTests(unittest.TestCase):
    def test_enemy_domain_override_preserves_state_and_helper_filters(self):
        from workflow.autofill import active_enemy_lanes
        state={'settings':{'enemy_acceptance_lanes':['armor','tadpole','helper']},'lanes':{
            'armor':{'state':'running'},'tadpole':{'state':'ready'},'helper':{'state':'running'},
            'enemy':{'state':'waiting_resource'},'blocked':{'state':'blocked'}}}
        items={k:dict(lane=k,phase='enqueued',priority='existing_content') for k in ('armor','tadpole','helper')}
        items['helper']['planner_helper']=True
        items['duplicate']=dict(items['armor'])
        for k in ('enemy','blocked'):items[k]=dict(lane=k,phase='enqueued',priority='enemy_acceptance')
        self.assertEqual(active_enemy_lanes(state,items),['armor','enemy'])

    def report(self):
        return {'at': 1000, 'metrics': {'accepted_slices_per_hour': 4.0}, 'autofill': {
            'enabled': True, 'ready_count': 3, 'idle_workers_count': 2, 'active_enemy_count': 1,
            'starvation_seconds': 180, 'updated_at': 999, 'last_manifest_error': None,
            'last_refill_request': {'at': 990, 'path': 'output/refill.json'},
            'items': {'repair': {'lane': 'enemy-repair', 'status': 'blocked', 'reason': 'Missing source-bound build'}}}}

    def test_backlog_capacity_blockers_and_starvation_are_visible(self):
        html = render_dashboard(self.report())
        self.assertIn('Ready backlog</span><strong>3', html)
        self.assertIn('Active enemy work</span><strong>1', html)
        self.assertIn('Idle authorized workers</span><strong>2', html)
        self.assertIn('Queue starvation', html)
        self.assertIn('3.0 min', html)
        self.assertIn('Missing source-bound build', html)
        self.assertIn('output/refill.json', html)

    def test_missing_status_is_unknown_not_zero_or_starvation(self):
        html = render_dashboard({})
        self.assertIn('Ready backlog</span><strong>Unavailable', html)
        self.assertIn('Active enemy work</span><strong>Unavailable', html)
        self.assertIn('Unavailable: no autofill observation', html)
        self.assertNotIn('Queue starvation:', html)

    def test_slice_rate_never_claims_enemy_admission(self):
        html = render_dashboard(self.report())
        self.assertIn('Integrated slices / hour</span><strong>4.0', html)
        self.assertIn('An accepted slice is not an enemy admission', html)
        self.assertIn('enemy ADMIT status is unavailable', html)
        self.assertNotIn('Accepted / hour', html)

    def test_nested_blocked_and_manifest_text_is_escaped(self):
        report = self.report()
        malicious = '<script>alert("x")</script>'
        report['autofill']['items']['repair'].update(lane=malicious, reason=malicious)
        report['autofill']['last_manifest_error'] = malicious
        report['autofill']['last_refill_request']['path'] = malicious
        html = render_dashboard(report)
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('&quot;', html)

    def test_disabled_autofill_does_not_report_active_starvation(self):
        report = self.report()
        report['autofill']['enabled'] = False
        html = render_dashboard(report)
        self.assertIn('Disabled', html)
        self.assertNotIn('Queue starvation:', html)

    def test_malformed_counter_is_unavailable_and_blocker_list_is_bounded(self):
        report = self.report()
        report['autofill']['ready_count'] = True
        report['autofill']['starvation_seconds'] = float('nan')
        report['autofill']['items'] = {str(i): {'lane': str(i), 'status': 'blocked', 'reason': 'test'} for i in range(12)}
        html = render_dashboard(report)
        self.assertIn('Ready backlog</span><strong>Unavailable', html)
        self.assertIn('additional blocked items', html)
        self.assertNotIn('Queue starvation:', html)


if __name__ == '__main__':
    unittest.main()
