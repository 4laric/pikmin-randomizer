"""No-progress guard, consumed-receipt wakeups and recovery rebinds; temp registries only."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from tests import test_pikmin2_controller as fixtures
from workflow import no_progress
from workflow.consumer_verification import reconcile, report
from workflow.consumer_wakeup import consumed, tick as wake
from workflow.handoff import Rejected, digest
from workflow.runner import write

GAP = ['Waiting for gen 3 engine birth (#1)']


class Base(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ControllerTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.reg, self.c, self.models = self.f.reg, self.f.controller, self.f.config['models']

    def lane(self, key='consumer'):
        return self.reg.snapshot()['lanes'][key]

    def events(self, kind):
        return [e for e in self.reg.snapshot()['events'] if e['kind'] == kind]

    def stop(self, key='consumer'):
        with self.reg.transaction() as s:
            s['lanes'][key]['process'] = {'pid': -1, 'created': 'stopped'}
            for x in s['control']['launches'].values():
                if x['lane'] == key: x['status'] = 'exited'

    def cycle(self, dependencies=None, reason='operator: rerun', gen=None):
        """One relaunch that ends blocked; the default gap only renumbers its generation."""
        item = self.reg.plan_launch('consumer', reason, 'Continue', self.models)
        self.reg.bind_launch(item['id'], self.f.identity)
        lane = self.lane()
        self.reg.finish('consumer', lane['generation'], 'blocked', 'Gap unchanged', self.f.ev,
                        dependencies or [GAP[0].replace('gen 3', 'gen %d' % lane['generation'])])
        self.stop()
        return item

    def stalled(self):
        self.reg.finish('consumer', 1, 'blocked', 'Gap', self.f.ev, GAP)
        self.cycle(); self.cycle()
        self.assertEqual(self.lane()['stall_streak'], 2)


class StallTests(Base):
    def test_streak_counts_unchanged_generations_survives_bind_and_resets_on_progress(self):
        self.reg.finish('consumer', 1, 'blocked', 'Gap', self.f.ev, GAP)
        self.assertEqual(self.lane()['stall_streak'], 0)  # The first recorded signal has no baseline.
        self.cycle(); self.assertEqual(self.lane()['stall_streak'], 1)
        item = self.reg.plan_launch('consumer', 'operator: rerun', 'Continue', self.models)
        lane = self.reg.bind_launch(item['id'], self.f.identity)
        self.assertEqual((lane['stall_streak'], lane['failure_streak']), (1, 0))  # Bind never resets it.
        self.reg.finish('consumer', lane['generation'], 'blocked', 'Gap', self.f.ev, ['WAITING for  GEN 9 engine birth (#1).'])
        self.assertEqual(self.lane()['stall_streak'], 2)
        self.reg.finish('consumer', lane['generation'], 'blocked', 'Other words, same gen', self.f.ev, GAP)
        self.assertEqual(self.lane()['stall_streak'], 2)  # A repeated finish in one generation counts once.
        self.assertEqual(len(self.events('no_progress_generation')), 2)
        self.stop(); self.cycle(dependencies=['#2 a different gap'])
        self.assertEqual(self.lane()['stall_streak'], 0)
        self.assertNotIn('wake_inputs', self.lane())

    def test_handoff_submission_is_recorded_as_progress(self):
        from workflow.no_progress import record
        with self.reg.transaction() as s:
            lane = s['lanes']['consumer']
            lane['progress_signal'] = dict(generation=0, signal='old', baseline=None, base_streak=0, stalled=False)
            lane['stall_streak'] = 3
            lane['handoff'] = dict(sha256='new')
            record(self.reg, s, lane)
            self.assertEqual(lane['stall_streak'], 0)

    def test_report_cli_reads_without_writing(self):
        import contextlib, hashlib, io
        self.stalled()
        before = hashlib.sha256(self.reg.path.read_bytes()).hexdigest()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(no_progress.main(['--root', str(self.f.root)]), 0)
        self.assertEqual(json.loads(out.getvalue())['stalled'], ['consumer'])
        self.assertEqual(hashlib.sha256(self.reg.path.read_bytes()).hexdigest(), before)

    def test_backoff_doubles_and_caps(self):
        self.assertEqual([no_progress.backoff(n) for n in (2, 3, 4, 6, 9)], [900, 1800, 3600, 14400, 14400])
        for reason in no_progress.WAKES:
            self.assertTrue(no_progress.guarded(reason + 'x'))
        for reason in ('dead-runner:a', 'provider fallback:a', 'provider-error:a', 'permission-repair:a',
                       'provider-stall:a', 'operator: rerun', 'user: retry', 'shepherd:a', 'setup-heal:a'):
            self.assertFalse(no_progress.guarded(reason))


class ParkingTests(Base):
    def wake(self, reason='consumer-prerequisite:x', **kwargs):
        return self.reg.plan_launch('consumer', reason, 'Wake', self.models, **kwargs)

    def test_refusal_parks_visibly_and_repeats_without_the_writer_lock(self):
        self.stalled()
        with self.assertRaises(no_progress.Parked) as refused:
            self.wake(inputs=[])
        lane = self.lane()
        self.assertEqual(lane['wake_after'], self.f.now + 900)
        self.assertEqual((lane['parked']['stall_streak'], lane['parked']['reason']), (2, 'consumer-prerequisite:x'))
        self.assertEqual(len(self.events('lane_parked')), 1)
        notices = [n for n in self.reg.control_status()['notices'].values() if n['kind'] == 'no_progress_parked']
        self.assertEqual([n['detail']['error'] for n in notices], [str(refused.exception)])
        self.assertEqual((lane['state'], lane['dependencies']), ('blocked', GAP))  # Parking rewrites no dependency.
        original = self.reg.transaction
        self.reg.transaction = Mock(side_effect=AssertionError('parked refusal took the writer lock'))
        try:
            with self.assertRaises(no_progress.Parked):
                self.wake('shared-preflight-decision:y')
        finally:
            self.reg.transaction = original
        from workflow.analytics import throughput_metrics
        self.assertEqual([p['lane'] for p in throughput_metrics(self.reg.snapshot(), self.f.now)['no_progress_parked']],
                         ['consumer'])

    def test_new_input_or_due_recheck_admits_and_unparks(self):
        self.stalled()
        with self.assertRaises(no_progress.Parked):
            self.wake(inputs=[])
        item = self.wake('consumer-prerequisite:new', inputs=['receipt:p:b:None'])  # A substantive delta.
        self.assertEqual(item['inputs'], ['receipt:p:b:None'])
        self.assertNotIn('parked', self.lane())
        self.assertEqual(len(self.events('lane_unparked')), 1)
        self.reg.bind_launch(item['id'], self.f.identity)
        lane = self.lane()
        self.assertIn('receipt:p:b:None', lane['wake_inputs'])
        self.reg.finish('consumer', lane['generation'], 'blocked', 'Gap', self.f.ev, GAP)
        self.stop()
        self.assertEqual(self.lane()['stall_streak'], 3)
        with self.assertRaises(no_progress.Parked):
            self.wake('consumer-prerequisite:again', inputs=['receipt:p:b:None'])  # Already assessed.
        self.assertEqual(self.lane()['wake_after'], self.f.now + 1800)
        self.f.now += 1800
        self.assertEqual(self.wake('consumer-prerequisite:again', inputs=['receipt:p:b:None'])['status'], 'intent')

    def test_recovery_operator_and_obligation_reasons_are_never_parked(self):
        self.stalled()
        for reason in ('dead-runner:a', 'provider fallback:a', 'provider-error:a', 'permission-repair:a',
                       'provider-stall:a', 'operator: unpark', 'user: retry'):
            self.assertEqual(self.wake(reason)['reason'], reason)
            self.stop()
        self.assertEqual(self.wake('integration-demand:x', obligation=True)['status'], 'intent')
        self.assertNotIn('parked', self.lane())

    def test_legacy_lanes_are_not_parked_on_the_first_tick_after_deploy(self):
        self.reg.finish('consumer', 1, 'blocked', 'Gap', self.f.ev, GAP)
        with self.reg.transaction() as s:  # Written by the base code: no signal, no streak, many no-op launches.
            lane = s['lanes']['consumer']
            for field in ('progress_signal', 'stall_streak'): lane.pop(field)
            for n in range(20):
                self.reg.control(s)['launches']['old-%d' % n] = dict(id='old-%d' % n, lane='consumer', reason='consumer-prerequisite:%d' % n,
                                                              status='exited', generation=1, created_at=n)
        self.assertEqual(no_progress.verdict(self.lane(), [], self.f.now), None)
        item = self.wake(inputs=[])
        self.reg.bind_launch(item['id'], self.f.identity)
        self.reg.finish('consumer', self.lane()['generation'], 'blocked', 'Gap', self.f.ev, GAP)
        self.assertEqual(self.lane()['stall_streak'], 0)  # No baseline yet: the first finish after deploy only records.

    def test_repeated_notices_collapse_with_a_counter(self):
        for identity in ('a', 'b', 'c'):
            self.reg.notice('consumer', 'shared_preflight_decision_blocked', dict(id=identity, error='Dispatch already in flight'))
        self.f.now += 600
        self.reg.notice('consumer', 'shared_preflight_decision_blocked', dict(id='d', error='Dispatch already in flight'))
        notices = [n for n in self.reg.control_status()['notices'].values() if n['kind'] == 'shared_preflight_decision_blocked']
        self.assertEqual(len(notices), 1)
        self.assertEqual((notices[0]['repeats'], notices[0]['detail']['id']), (1, 'd'))
        self.reg.notice('consumer', 'integrator_guard_refused', dict(action='one', error='same'))
        self.reg.notice('consumer', 'integrator_guard_refused', dict(action='two', error='same'))
        self.assertEqual(sum(n['kind'] == 'integrator_guard_refused' for n in self.reg.control_status()['notices'].values()), 2)


class ConsumerWakeTests(Base):
    def setUp(self):
        super().setUp()
        self.reg.finish('consumer', 1, 'blocked', 'Missing source and approval', self.f.ev, ['#1', '#186 shared-hook review'])
        self.integrate('provider', 'b')
        path = self.f.root / 'consumer-check.log'; path.write_text('Consumer command output')
        self.check_ev = dict(path=str(path), sha256=digest(path))

    def integrate(self, key, commit, issue=None):
        if key not in self.reg.snapshot()['lanes']:
            self.f.add_lane(key, issue or 1)
        with self.reg.transaction() as s:
            s['lanes'][key].update(state='done', integrated_at=self.f.now + 1, integration=dict(
                root_commit=commit * 40, native_commit=None, validation_path=self.f.ev['path'],
                validation_sha256=self.f.ev['sha256']))

    def launches(self):
        return sorted((x for x in self.reg.control_status()['launches'].values() if x['lane'] == 'consumer'),
                      key=lambda x: x['created_at'])

    def dispatch(self, item):
        self.c.dispatch(item); self.reg.bind_launch(item['id'], self.f.identity)
        return self.lane()['generation']

    def submit(self, verification, generation, passed=False):
        return report(self.reg, verification, 'consumer', generation, passed,
                      dict(command='consumer-check', expected='resolved', observed='resolved' if passed else 'still broken'),
                      self.check_ev, prerequisite_resolved=passed)

    def test_consumed_receipts_are_not_rewoken_and_new_producers_wake_alone(self):
        wake(self.c)
        first = self.launches()[0]
        self.assertEqual(first['inputs'], ['receipt:provider:' + 'b' * 40 + ':None'])
        generation = self.dispatch(first); reconcile(self.c)
        self.submit(first['id'], generation)
        lane = self.lane()
        self.assertEqual(consumed(lane), {'provider': ['b' * 40, None]})
        self.reg.finish('consumer', generation, 'blocked', 'Still broken', self.check_ev, ['#1', '#3'])
        self.stop(); self.f.now += 900
        wake(self.c)
        self.assertEqual(len(self.launches()), 1)  # Checked at these pins: no wake for the same receipt.
        self.integrate('second', 'c', issue=3)
        wake(self.c)
        second = self.launches()[-1]
        self.assertEqual(len(self.launches()), 2)
        producers = json.loads(second['instruction'].split('Integrated prerequisites: ', 1)[1])
        self.assertEqual([p['lane'] for p in producers], ['second'])
        self.assertEqual(self.lane()['dependencies'], ['#1', '#3'])  # Consumed is not resolved.
        with self.reg.transaction() as s:
            s['lanes']['consumer']['root']['head'] = 'e' * 40
        self.assertEqual(consumed(self.lane()), {})  # New consumer pins: nothing counts as checked.

    def test_debounce_and_umbrella_issues(self):
        wake(self.c); self.stop()
        self.integrate('provider', 'c')
        wake(self.c)
        self.assertEqual(len(self.launches()), 1)  # Within the debounce window.
        self.f.now += 900
        wake(self.c)
        self.assertEqual(len(self.launches()), 2)
        self.stop(); self.f.now += 900
        self.integrate('hook-owner', 'd', issue=186)
        wake(self.c)
        self.assertEqual(len(self.launches()), 2)  # '#186' is an umbrella gate, not a producer mapping.
        self.c.config['consumer_wakeup'] = dict(umbrella_issues=[])
        wake(self.c)
        self.assertEqual(len(self.launches()), 3)

    def test_superseded_check_without_report_reissues_its_token(self):
        wake(self.c)
        first = self.launches()[0]
        reconcile(self.c)
        with self.reg.transaction() as s:  # The pre-rebind incident: gen moved on, the check was never rebound.
            s['control']['launches'][first['id']].update(status='exited', bound_generation=1)
            s['lanes']['consumer']['generation'] = 2
        reconcile(self.c)
        self.assertEqual(self.reg.snapshot()['consumer_verifications'][first['id']]['status'], 'superseded')
        self.f.now += 900
        wake(self.c)
        launches = self.launches()
        self.assertEqual([x['reason'] for x in launches], [first['reason']] * 2)
        reconcile(self.c)
        self.stop(); self.f.now += 900
        wake(self.c)
        self.assertEqual(len(self.launches()), 2)  # Its fresh record is pending, not superseded: no loop.

    def test_rate_limit_fallback_carries_and_rebinds_the_check(self):
        wake(self.c)
        first = self.launches()[0]
        reconcile(self.c)
        self.dispatch(first)
        self.reg.probe = lambda _: 'dead'
        write(self.c.launch_directory(first['id']) / 'result.json', {'kind': 'rate_limit', 'exit_code': 1})
        self.c.complete_runs()
        follow = self.launches()[-1]
        self.assertTrue(follow['reason'].startswith('provider fallback:'))
        self.assertEqual((follow['consumer_verification'], follow['inputs']), (first['id'], first['inputs']))
        self.reg.probe = lambda p: 'alive' if p == self.f.identity else 'dead'
        with self.reg.transaction() as s:
            s['lanes']['consumer']['process'] = {'pid': -1, 'created': 'rate-limited'}
        generation = self.dispatch(follow); reconcile(self.c)
        state = self.reg.snapshot()
        bound = state['control']['launches'][follow['id']]
        self.assertEqual(bound['consumer_verification'], follow['id'])
        self.assertIn('verification=' + follow['id'], bound['instruction'])
        self.assertEqual(state['consumer_verifications'][first['id']]['status'], 'superseded')
        self.assertEqual(state['consumer_verifications'][follow['id']]['status'], 'pending')
        with self.assertRaises(Rejected):
            self.submit(first['id'], generation)
        self.assertEqual(self.submit(follow['id'], generation)['status'], 'failed')


class HandoffRepresentationTests(unittest.TestCase):
    def test_passed_check_gets_one_bounded_turn_per_verification(self):
        from workflow.handoff_representation import tick
        lane = dict(lane='slice', generation=3, state='blocked', handoff=None, root={'head': 'a'}, native={'head': 'b'})
        check = dict(id='v1', consumer='slice', created_at=1, status='passed', prerequisite_resolved=True,
                     runtime={'kind': 'game_runtime'}, evidence={'path': 'e'}, source_pins={'root': 'a', 'native': 'b'})
        state = {'lanes': {'slice': lane}, 'control': {'launches': {}}, 'consumer_verifications': {'v1': check}}
        reg = Mock(); reg.snapshot.return_value = state; reg.recovery_safe.return_value = True
        c = SimpleNamespace(reg=reg, config={'lanes': {'slice': {}}, 'models': ['m/x']}, available=lambda k: True)
        tick(c)
        reason = reg.plan_launch.call_args.args[1]
        self.assertEqual((reason, reg.plan_launch.call_args.kwargs['inputs']),
                         ('handoff-representation:verification:v1', ['handoff-representation:verification:v1']))
        self.assertIn('remaining_work', reg.plan_launch.call_args.args[2])
        state['control']['launches']['x'] = dict(lane='slice', reason=reason, status='exited')
        tick(c); self.assertEqual(reg.plan_launch.call_count, 1)
        for change in (dict(status='failed'), dict(runtime=None), dict(source_pins={'root': 'z', 'native': 'b'})):
            state['consumer_verifications']['v2'] = dict(check, id='v2', created_at=2, **change)
            tick(c); self.assertEqual(reg.plan_launch.call_count, 1)
        state['consumer_verifications']['v2'] = dict(check, id='v2', created_at=2)
        tick(c); self.assertEqual(reg.plan_launch.call_count, 2)


if __name__ == '__main__':
    unittest.main()
