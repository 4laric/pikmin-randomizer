"""Integrated pool/controller tests with isolated registry and synthetic runner I/O."""
import json
import unittest

from tests import test_pikmin2_controller as fixtures
from workflow.dashboard import render_dashboard
from workflow.throughput_controller import capture_costs, pool_tick
from workflow.planner_pool import helper_target


class ThroughputIntegrationTests(unittest.TestCase):
    def setUp(self):
        # Composition retains the real Registry/Controller fixture without inheriting
        # its unrelated tests into this suite a second time.
        self.fixture = fixtures.ControllerTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.reg = self.fixture.reg
        self.controller = self.fixture.controller
        self.controller.config['throughput'] = dict(enabled=True, provisional_qa=False, capture_costs=False)
        self.controller.config.update(ram_high=90, ram_low=87)
        with self.reg.transaction() as state:
            state['lanes']['provider']['process'] = self.fixture.identity
        self.reg.set_workstream('p2', 'provider', ['consumer'])
        self.reg.register_pool_worker('consumer', ['review'], ['python'], 'test orchestrator')
        self.reg.enqueue_job(dict(id='review-one', lane='consumer', issue=2, workstream='p2', role='review',
                                  capabilities=['python'], instruction='Apply review disposition'))

    def test_helper_target_yields_to_ready_and_integration_backlog(self):
        config = dict(max_active=24, reserve_workers=0, use_idle_capacity=True, pause_integration_depth=2)
        self.assertEqual(helper_target(config, helper_count=9, ready=2, unclaimed_ready=2,
                                       idle=2, active=9, integration={'depth': 2, 'oldest_seconds': 10}), 0)
        self.assertEqual(helper_target(config, helper_count=9, ready=0, unclaimed_ready=0,
                                       idle=4, active=0, integration={'depth': 2, 'oldest_seconds': 10}), 0)
        self.assertEqual(helper_target(config, helper_count=9, ready=0, unclaimed_ready=0,
                                        idle=6, active=0, integration={}), 6)

    def test_fresh_handoff_does_not_starve_planning_but_backpressure_remains(self):
        config = dict(max_active=24, reserve_workers=0, use_idle_capacity=True)
        args = dict(helper_count=24, ready=1, unclaimed_ready=1, idle=7, active=3)
        self.assertEqual(helper_target(config, **args, integration={'depth': 1, 'oldest_seconds': 120}), 9)
        self.assertEqual(helper_target(config, **args, integration={'depth': 4, 'oldest_seconds': 120}), 0)
        self.assertEqual(helper_target(config, **args, integration={'depth': 1, 'oldest_seconds': 3600}), 0)

    def test_dynamic_planning_expands_and_reserves_execution_capacity(self):
        config = dict(max_active=24, reserve_workers=2, use_idle_capacity=True)
        args = dict(helper_count=30, ready=0, unclaimed_ready=0,
                    idle=9, active=3, integration={})
        self.assertEqual(helper_target(config, **args), 10)
        self.assertEqual(helper_target(config, **dict(args, idle=4)), 5)
        self.assertEqual(helper_target(config, **dict(args, ready=8, unclaimed_ready=8)), 2)
        self.assertEqual(helper_target(config, **dict(args, idle=40)), 24)
        self.assertEqual(helper_target(config, **dict(args, helper_count=4)), 4)
        self.assertEqual(helper_target(dict(config, max_active=0), **args), 0)

    def test_demand_mode_remains_bounded_by_low_watermark(self):
        config = dict(max_active=24, reserve_workers=2, items_per_helper=3, low_watermark=8)
        args = dict(helper_count=30, ready=0, unclaimed_ready=0,
                    idle=20, active=0, integration={})
        self.assertEqual(helper_target(config, **args), 3)
        self.assertEqual(helper_target(config, **dict(args, ready=8)), 0)

    def test_enabled_pool_plans_and_dispatches_once(self):
        pool_tick(self.controller)
        launch = next(iter(self.reg.control_status()['launches'].values()))
        self.controller.dispatch(launch)
        pool_tick(self.controller)
        self.controller.dispatch(self.reg.control_status()['launches'][launch['id']])
        self.assertEqual(len(self.reg.control_status()['launches']), 1)
        self.assertEqual(len(self.fixture.spawns), 1)
        lane = self.reg.status()['lanes']['consumer']
        self.assertEqual(lane['generation'], 2)
        self.assertEqual(lane['state'], 'running')
        self.assertTrue((self.controller.launch_directory(launch['id']) / 'start.json').exists())

    def test_missing_launch_configuration_releases_reservation(self):
        self.controller.config['lanes'].pop('consumer')
        pool_tick(self.controller)
        self.assertFalse(self.reg.control_status()['launches'])
        assignments = self.reg.scheduling_status()['assignments'].values()
        self.assertFalse(any(a['status'] in ('assigned', 'dispatched') for a in assignments))
        self.assertEqual(self.reg.scheduling_status()['jobs']['review-one']['status'], 'queued')

    def test_actual_accepted_review_releases_worker(self):
        pool_tick(self.controller)
        launch = next(iter(self.reg.control_status()['launches'].values()))
        self.controller.dispatch(launch)
        lane = self.reg.status()['lanes']['consumer']
        self.reg.finish('consumer', lane['generation'], 'review-ready', 'Evidence reviewed', self.fixture.ev)
        self.reg.accept_review('consumer', lane['generation'], 'Disposition applied', self.fixture.ev)
        with self.reg.transaction() as state:
            state['lanes']['consumer']['process'] = {'pid': -42, 'created': 'stopped-test-runner'}
            state['control']['launches'][launch['id']]['status'] = 'exited'
        pool_tick(self.controller)
        pool = self.reg.scheduling_status()
        self.assertEqual(pool['jobs']['review-one']['status'], 'completed')
        self.assertEqual(next(iter(pool['assignments'].values()))['status'], 'completed')
        self.assertIsNone(self.reg.assign_job('consumer', 60))

    def event(self, identity='step-1', amount=0.125, timestamp=1000000):
        return dict(type='step_finish', sessionID='session-consumer', timestamp=timestamp,
                    part=dict(id=identity, cost=amount))

    def write_events(self, name, events):
        path = self.fixture.out / name
        path.write_text(''.join(json.dumps(e) + '\n' for e in events), encoding='utf-8')
        return path

    def test_cost_duplicate_and_replay_are_counted_once(self):
        event = self.event()
        self.write_events('run-one.jsonl', [event, event])
        self.write_events('run-two.jsonl', [event])
        capture_costs(self.controller)
        capture_costs(self.controller)
        costs = self.reg.scheduling_status()['costs']
        self.assertEqual(len(costs), 1)
        self.assertEqual(sum(c['amount'] for c in costs.values()), 0.125)

    def test_cost_invalid_timestamp_and_zero_stay_unknown(self):
        self.write_events('run-invalid.jsonl', [self.event('zero', 0), self.event('negative-time', timestamp=-1),
                          self.event('text-time', timestamp='today'), self.event('nan-time', timestamp=float('nan')),
                          self.event('infinite-cost', amount=float('inf'))])
        capture_costs(self.controller)
        self.assertFalse(self.reg.scheduling_status().get('costs'))
        metrics = self.reg.throughput_status(ram_percent=60)['metrics']
        self.assertEqual(metrics['costs']['coverage'], 'unknown')
        self.assertIsNone(metrics['costs']['cost_per_accepted_slice'])

    def test_reused_session_keeps_original_cost_attribution(self):
        self.write_events('run-original.jsonl', [self.event()])
        capture_costs(self.controller)
        new = self.fixture.root / 'output/reused'
        new.mkdir()
        (new / 'run-replay.jsonl').write_text(json.dumps(self.event(timestamp=2000000)) + '\n')
        self.controller.config['lanes']['provider'] = {'output': str(new)}
        capture_costs(self.controller)
        costs = list(self.reg.scheduling_status()['costs'].values())
        self.assertEqual(len(costs), 1)
        self.assertEqual(costs[0]['lane'], 'consumer')
        self.assertEqual(costs[0]['at'], 1000)

    def test_missing_cost_source_does_not_block_other_logs(self):
        self.controller.config['lanes']['provider'] = {}
        self.write_events('run-valid.jsonl', [self.event()])
        capture_costs(self.controller)
        self.assertEqual(len(self.reg.scheduling_status()['costs']), 1)

    def test_disabled_pool_retains_durable_launch_spec(self):
        spec = self.controller.config['lanes'].pop('consumer')
        with self.reg.transaction() as state:
            state['throughput_runtime'] = {'launch_specs': {'consumer': spec}}
        self.controller.config['throughput']['enabled'] = False
        pool_tick(self.controller)
        self.assertEqual(self.controller.config['lanes']['consumer'], spec)
        self.assertFalse(self.reg.control_status()['launches'])

    def test_dashboard_escapes_registry_keys_and_values(self):
        report = self.reg.throughput_status(ram_percent=60)
        malicious = '<script>alert("x")</script>'
        report['throughput']['workstreams'][malicious] = {'owner': malicious}
        html = render_dashboard(report)
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('&quot;', html)


if __name__ == '__main__':
    unittest.main()
