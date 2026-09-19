import unittest

from workflow.analytics import staffing_recommendations, throughput_metrics
from workflow.handoff import Rejected


class AnalyticsTests(unittest.TestCase):
    def test_sparse_records_unknown_not_zero(self):
        result = throughput_metrics({}, 10000)
        self.assertEqual(result['accepted_slices'], 0)
        self.assertIsNone(result['costs']['cost_per_accepted_slice'])
        self.assertIsNone(result['heavy_build']['utilization_percent'])
        self.assertIsNone(result['oldest_handoff'])

    def test_window_counts_no_duplicate_integration_or_review_acceptance(self):
        state = {'lanes': {'a': {'integration': {'id': 'receipt'}, 'integrated_at': 9000}},
                 'events': [{'kind': 'integrated', 'lane': 'a', 'at': 9000},
                            {'kind': 'review_accepted', 'lane': 'b', 'at': 9100},
                            {'kind': 'integrated', 'lane': 'old', 'at': 6400}]}
        result = throughput_metrics(state, 10000)
        self.assertEqual(result['accepted_slices'], 1)
        self.assertEqual(result['costs']['accepted_lanes_missing_cost'], ['a'])
        state['throughput'] = {'costs': {'one': {'lane': 'a', 'at': 9200, 'amount': 0, 'currency': 'USD'}}}
        self.assertEqual(throughput_metrics(state, 10000)['costs']['cost_per_accepted_slice'], {'USD': 0})

    def test_lease_intervals_clip_window_and_include_unexpired_live_owner(self):
        state = {'settings': {'max_heavy_builds': 2}, 'events': [
            {'kind': 'lease_acquired', 'resource': 'build:a', 'at': 100},
            {'kind': 'lease_released', 'resource': 'build:a', 'at': 950},
            {'kind': 'lease_acquired', 'resource': 'build:b', 'at': 920},
            {'kind': 'lease_acquired', 'resource': 'shared-runtime', 'at': 910}],
            'leases': {'build:b': {'acquired_at': 920, 'expires_at': 925}}}
        result = throughput_metrics(state, 1000, 100)['heavy_build']
        self.assertEqual(result['leased_seconds'], 130)
        self.assertEqual(result['utilization_percent'], 65)

    def test_dependency_wait_and_oldest_handoff(self):
        state = {'lanes': {'a': {'state': 'done', 'integrated_at': 800},
                           'b': {'state': 'blocked', 'dependencies': ['a']},
                           'external': {'state': 'blocked', 'dependencies': ['#123']},
                           'c': {'state': 'handoff_ready', 'handoff_at': 500}}}
        result = throughput_metrics(state, 1000)
        self.assertEqual(result['oldest_handoff']['age_seconds'], 500)
        self.assertEqual(result['dependency_ready_waits'][0]['wait_seconds'], 200)
        self.assertEqual(len(result['dependency_ready_waits']), 1)

    def test_resource_aware_staffing(self):
        state = {'settings': {'max_heavy_builds': 1}, 'leases': {'build:a': {}},
                 'throughput': {'jobs': {'a': {'role': 'review', 'state': 'queued'},
                                        'b': {'role': 'qa', 'status': 'queued', 'heavy': True},
                                        'c': {'role': 'repair', 'state': 'queued', 'dependencies': ['missing']}}}}
        result = staffing_recommendations(state, 1000, 60)
        self.assertEqual({r['role']: r['action'] for r in result['recommendations']}, {'qa': 'prepare', 'review': 'staff'})
        self.assertTrue(all(r['action'] == 'wait_ram' for r in staffing_recommendations(state, 1000, 90)['recommendations']))
        self.assertTrue(all(r['action'] == 'measure' for r in staffing_recommendations(state, 1000)['recommendations']))

    def test_reports_idle_worker_compatibility(self):
        state = {'settings': {'max_heavy_builds': 2}, 'leases': {},
                 'lanes': {'worker-a': {'state': 'done', 'process': {'health': 'dead'}},
                           'worker-b': {'state': 'done', 'process': {'health': 'dead'}}},
                 'throughput': {
                     'workers': {
                         'a': {'worker_id': 'a', 'roles': ['implementation'], 'capabilities': ['python']},
                         'b': {'worker_id': 'b', 'roles': ['review'], 'capabilities': ['native']},
                     },
                     'assignments': {},
                     'jobs': {
                         'ready': {'id': 'ready', 'lane': 'worker-a', 'worker_id': 'a', 'role': 'implementation',
                                   'capabilities': ['python'], 'status': 'queued'},
                         'unmatched': {'id': 'unmatched', 'lane': 'worker-b', 'worker_id': 'b', 'role': 'implementation',
                                       'capabilities': ['python'], 'status': 'queued'},
                     }}}
        result = staffing_recommendations(state, 1000, 60, process_probe=lambda p: p.get('health', 'unknown'))
        self.assertEqual(result['compatible_idle_workers'], 1)
        self.assertEqual([item['job'] for item in result['unmatched_ready_jobs']], ['unmatched'])

    def test_stopped_terminal_heavy_reservation_frees_reported_slot_only(self):
        assignment={'lane':'consumer','heavy':True,'status':'dispatched'}
        state={'settings':{'max_heavy_builds':2},'leases':{},
               'lanes':{'consumer':{'state':'blocked','process':{'health':'dead'}}},
               'throughput':{'assignments':{'a':assignment}}}
        probe=lambda p:p.get('health','unknown')
        self.assertEqual(staffing_recommendations(state,1000,60,process_probe=probe)['heavy_slots_available'],2)
        self.assertEqual(assignment['status'],'dispatched')
        state['lanes']['consumer']['process']['health']='unknown'
        self.assertEqual(staffing_recommendations(state,1000,60,process_probe=probe)['heavy_slots_available'],1)
        state['lanes']['consumer']['process']['health']='dead'
        state['leases']={'build:a':{'lane':'consumer','process':{'health':'dead'}},
                         'build:b':{'lane':'consumer','process':{'health':'dead'}}}
        self.assertEqual(staffing_recommendations(state,1000,60,process_probe=probe)['heavy_slots_available'],0)

    def test_non_finite_arguments_rejected(self):
        for value in (float('nan'), float('inf'), True, -1):
            with self.assertRaises(Rejected): throughput_metrics({}, value)
        with self.assertRaises(Rejected): staffing_recommendations({}, 1, 101)


if __name__ == '__main__':
    unittest.main()
