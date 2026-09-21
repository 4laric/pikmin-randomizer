import unittest

from tests import test_pikmin2_controller as fixtures
from workflow.handoff import Rejected
from workflow.integration_wakeup import tick, shared_reviews


class IntegrationWakeupTests(unittest.TestCase):
    def test_packet_retry_identity_ignores_unrelated_queue_churn(self):
        from workflow.integration_wakeup import demand_token
        packet=dict(stream='content',prepared_action='packet',handoff='provider',destination={'root':'a'*40})
        self.assertEqual(demand_token([packet,dict(job='helper-cycle-1')]),
                         demand_token([dict(job='helper-cycle-2'),packet,dict(item='waiting')]))
        self.assertNotEqual(demand_token([packet]),demand_token([dict(packet,prepared_action='corrected')]))
        self.assertNotEqual(demand_token([dict(item='one')]),demand_token([dict(item='two')]))

    def test_helper_and_self_jobs_do_not_wake_owner_but_implementation_does(self):
        from unittest.mock import patch
        with self.reg.transaction() as state:
            state['throughput_runtime']['autofill']['items']={}
            state['throughput']['jobs']={
                'helper':dict(lane='planning-next',workstream='content',status='queued'),
                'self':dict(lane='consumer',workstream='content',status='queued')}
        with patch.object(self.reg,'integration_owner_available',return_value=False):
            tick(self.controller)
            self.assertFalse(self.reg.control_status()['launches'])
            with self.reg.transaction() as state:
                state['throughput']['jobs']['producer']=dict(lane='provider',workstream='content',status='queued')
            tick(self.controller)
        self.assertEqual(len(self.reg.control_status()['launches']),1)

    def test_pinned_preparation_packet_wakes_existing_owner(self):
        with self.reg.transaction() as state:
            state['throughput_runtime']['autofill']['items']={}
            state['throughput']['workstreams']['content']['lanes']=['provider']
            lane=state['lanes']['provider'];lane.update(state='blocked',next_action='Private preparation ready')
            target={k:lane.get(k) for k in ('lane','generation','root','native','handoff')}
            state['support_actions']={'packet':dict(id='packet',action='integration_packet',key='provider',target=target,
                evidence=self.f.ev,details={'destination':{'root':'a'*40,'native':None}})}
        tick(self.controller);tick(self.controller)
        launches=list(self.reg.control_status()['launches'].values())
        self.assertEqual(len(launches),1)
        self.assertIn("'prepared_action': 'packet'",launches[0]['instruction'])
    def test_blocked_shared_review_wakes_standby_and_records_bounded_request(self):
        with self.reg.transaction() as state:
            state['throughput_runtime']['autofill']['items'] = {}
            state['throughput']['workstreams']['content']['lanes'] = ['provider']
            state['lanes']['provider'].update(state='blocked', next_action='Shared fixture registration needs #186 review')
        tick(self.controller); tick(self.controller)
        launches = list(self.reg.control_status()['launches'].values())
        self.assertEqual(len(launches), 1)
        self.assertEqual(len(launches[0]['shared_review_requests']), 1)
        self.assertIn("'shared_review': 'provider'", launches[0]['instruction'])

    def test_shared_review_retry_budget_ignores_other_queue_churn(self):
        with self.reg.transaction() as state:
            stream = dict(lanes=['provider'])
            lane = state['lanes']['provider']
            lane.update(state='done', review_disposition={'summary':'source review'},
                        next_action='Patch ready; shared #186 review needed')
            first = shared_reviews(state, stream, [])
            self.assertEqual(len(first), 1)
            prior = [dict(shared_review_requests=[first[0]['shared_review_id']], reason=str(n)) for n in range(2)]
            self.assertEqual(shared_reviews(state, stream, prior), [])
            lane['root']['head'] = 'f'*40
            self.assertEqual(len(shared_reviews(state, stream, prior)), 1)
            lane['integration'] = {'root_commit':'f'*40}
            self.assertEqual(shared_reviews(state, stream, []), [])
            lane.pop('integration'); lane['state'] = 'running'
            self.assertEqual(shared_reviews(state, stream, []), [])
            lane.update(state='blocked',next_action='Missing legal game assets')
            self.assertEqual(shared_reviews(state, stream, []), [])
            lane['next_action'] = 'Shared #186 review needed'
            state['lanes']['planning-old'] = dict(lane)
            self.assertEqual(shared_reviews(state, dict(lanes=['planning-old']), []), [])

    def setUp(self):
        self.f = fixtures.ControllerTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.reg, self.controller = self.f.reg, self.f.controller
        config = self.f.out / 'opencode.json'; config.write_text('{}')  # Integrator launches must carry the git guard.
        self.f.config['lanes']['consumer']['config'] = str(config)
        self.reg.finish('consumer', 1, 'review-ready', 'Previous batch completed', self.f.ev)
        with self.reg.transaction() as state:
            state['throughput'] = dict(workstreams={'content': dict(owner_lane='consumer', lanes=[])}, batches={})
            state['throughput_runtime'] = dict(autofill=dict(items={'new': dict(workstream='content',
                status='blocked', dependency_kind='integration_owner', spec_hash='new-spec')}))

    def test_new_demand_resumes_same_owner_preserving_report(self):
        with self.reg.transaction() as state:
            state['throughput']['workstreams']['content']['lanes'] = ['provider']
            state['lanes']['provider'].update(state='handoff_ready', handoff_at=1000)
        tick(self.controller)
        tick(self.controller)
        launches = list(self.reg.control_status()['launches'].values())
        self.assertEqual(len(launches), 1)
        self.controller.dispatch(launches[0])
        lane = self.reg.status()['lanes']['consumer']
        self.assertEqual(lane['generation'], 2)
        self.assertIsNone(lane['handoff_at'])
        self.assertEqual(lane['completed_turns'][0]['outcome']['summary'], 'Previous batch completed')
        self.assertEqual(launches[0]['session'], 'session-consumer')

    def test_live_owner_or_unknown_owner_does_not_resume(self):
        for health in ('alive', 'unknown'):
            self.reg.probe = lambda p: health
            tick(self.controller)
            self.assertFalse(self.reg.control_status()['launches'])

    def open_batch(self):
        with self.reg.transaction() as state:
            state['throughput_runtime']['autofill']['items'] = {}
            state['throughput']['batches']['open'] = dict(id='open', integrator='consumer',
                state='claimed', workstream='content', generation=1, revision=3,
                candidates={'provider': {'root': 'immutable-pin'}},
                builds=[{'evidence': self.f.ev}], isolated={'other': {'reason': 'preserve'}})

    def test_open_batch_resumes_same_owner_and_preserves_validation(self):
        self.open_batch()
        before = self.reg.scheduling_status()['batches']['open']
        tick(self.controller)
        tick(self.controller)
        launches = list(self.reg.control_status()['launches'].values())
        self.assertEqual(len(launches), 1)
        self.assertIn('Resume your existing claimed batches first', launches[0]['instruction'])
        self.controller.dispatch(launches[0])
        self.reg.bind_launch(launches[0]['id'], self.f.identity)
        after = self.reg.scheduling_status()['batches']['open']
        self.assertEqual((after['generation'], after['revision']), (2, 4))
        for key in ('candidates', 'builds', 'isolated', 'integrator', 'state'):
            self.assertEqual(after[key], before[key])
        self.assertEqual(len(after['recovery_history']), 1)
        self.assertEqual(launches[0]['session'], 'session-consumer')

    def test_arbitrary_review_lane_stays_fenced(self):
        with self.reg.transaction() as state:
            state['throughput']['workstreams'] = {}
        with self.assertRaises(Rejected):
            self.reg.plan_launch('consumer', 'integration-demand:forged', 'Resume', self.f.config['models'])

    def test_stale_batch_generation_rejects_before_launch(self):
        self.open_batch()
        with self.reg.transaction() as state:
            state['throughput']['batches']['open']['generation'] = 0
        tick(self.controller)
        self.assertFalse(self.reg.control_status()['launches'])

    def test_owner_change_between_plan_and_bind_rejects(self):
        self.open_batch()
        tick(self.controller)
        item = next(iter(self.reg.control_status()['launches'].values()))
        with self.reg.transaction() as state:
            state['throughput']['workstreams']['content']['owner_lane'] = 'provider'
        with self.assertRaises(Rejected):
            self.reg.bind_launch(item['id'], self.f.identity)
        self.assertEqual(self.reg.scheduling_status()['batches']['open']['generation'], 1)

    def test_open_batch_live_unknown_owner_or_protected_child_never_resumes(self):
        self.open_batch()
        for health in ('alive', 'unknown'):
            self.reg.probe = lambda p: health
            tick(self.controller)
            self.assertFalse(self.reg.control_status()['launches'])
        self.reg.probe = lambda p: 'unknown' if p.get('pid') == 42 else 'dead'
        with self.reg.transaction() as state:
            state['leases']['build'] = dict(lane='consumer', process={'pid': 42})
        tick(self.controller)
        self.assertFalse(self.reg.control_status()['launches'])

    def test_no_new_demand_does_not_poll_model(self):
        with self.reg.transaction() as state:
            state['throughput_runtime']['autofill']['items'] = {}
        tick(self.controller)
        self.assertFalse(self.reg.control_status()['launches'])

    def test_pending_review_wakes_owner_for_explicit_disposition_once(self):
        self.reg.finish('provider', 1, 'review-ready', 'Source prerequisite audit', self.f.ev)
        with self.reg.transaction() as state:
            state['throughput']['workstreams']['content']['lanes'] = ['provider']
        tick(self.controller); tick(self.controller)
        launches = list(self.reg.control_status()['launches'].values())
        self.assertEqual(len(launches), 1)
        self.assertIn('accept_review', launches[0]['instruction'])
        self.assertIn("'review': 'provider'", launches[0]['instruction'])

    def test_orphaned_review_ready_lane_wakes_integration_owner(self):
        self.reg.finish('provider', 1, 'review-ready', 'Orphaned source audit', self.f.ev)
        # provider is not a member of any workstream; the terminal packet must
        # still reach the standing integration owner instead of aging silently.
        tick(self.controller); tick(self.controller)
        launches = list(self.reg.control_status()['launches'].values())
        self.assertEqual(len(launches), 1)
        self.assertIn('accept_review', launches[0]['instruction'])
        self.assertIn("'orphaned': True", launches[0]['instruction'])

    def test_admission_only_demand_uses_verified_standby_without_model_call(self):
        tick(self.controller)
        self.assertFalse(self.reg.control_status()['launches'])

    def test_explicit_landing_decision_dependency_is_review_demand(self):
        state=self.reg.snapshot()
        state['lanes']['provider'].update(state='blocked',next_action='Implementation complete',
            dependencies=['Explicit #186 landing decision for serialized wiring'])
        self.assertEqual(len(shared_reviews(state,dict(lanes=['provider']),[])),1)
        state['lanes']['provider']['dependencies']=['Waiting for assets #186']
        self.assertEqual(shared_reviews(state,dict(lanes=['provider']),[]),[])

    def test_aging_report_obligation_survives_dispatch_and_blocks_empty_standby(self):
        self.reg.finish('provider', 1, 'review-ready', 'Source audit', self.f.ev)
        with self.reg.transaction() as state:
            state['throughput']['workstreams']['content']['lanes'] = ['provider']
        self.f.now += 1801
        tick(self.controller)
        launch = next(iter(self.reg.control_status()['launches'].values()))
        self.assertEqual(launch['review_obligations'][0]['lane'], 'provider')
        self.controller.dispatch(launch)
        self.reg.bind_launch(launch['id'], self.f.identity)
        owner = self.reg.snapshot()['lanes']['consumer']
        with self.assertRaisesRegex(Rejected, 'Aging reviews'):
            self.reg.finish('consumer', owner['generation'], 'review-ready', 'Nothing new', self.f.ev)
        self.reg.accept_review('provider', 1, 'Reviewed completed source audit only', self.f.ev)
        self.reg.finish('consumer', owner['generation'], 'review-ready', 'Review disposed', self.f.ev)

    def test_old_owner_report_does_not_pause_new_slices(self):
        self.f.now = 10000
        status = self.reg.status()
        self.assertFalse(status['dispatch']['pause_new_slices'])
        self.assertEqual(status['metrics']['handoff_queue'], [])

    def test_isolated_handoff_does_not_wake_owner_again(self):
        with self.reg.transaction() as state:
            state['throughput']['workstreams']['content']['lanes'] = ['provider']
            lane = state['lanes']['provider']
            lane.update(state='handoff_ready', handoff_at=1000)
            pin = {k:lane.get(k) for k in ('generation', 'revision', 'root', 'native', 'handoff')}
            state['throughput']['batches']['old'] = dict(id='old', state='closed', integrator='consumer',
                candidates={'provider':pin}, isolated={'provider':dict(reason='Missing prerequisite')})
        tick(self.controller)
        self.assertFalse(self.reg.control_status()['launches'])
