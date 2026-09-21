import copy
import unittest
from unittest.mock import patch

from tests import test_pikmin2_controller as fixtures
from workflow.integration_repair import tick, invalid_handoffs
from workflow.analytics import throughput_metrics
from workflow.queue_pressure import update, integration_items
from workflow.handoff import Rejected


class IntegrationRepairTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ControllerTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.reg, self.c = self.f.reg, self.f.controller
        self.c.config['queue_pressure'] = {'enabled': True}
        self.c.base.mkdir(parents=True, exist_ok=True)
        with self.reg.transaction() as s:
            lane = s['lanes']['consumer']
            lane.update(state='handoff_ready', handoff_at=1,
                        handoff={'path':'old.json','sha256':'a'*64,'result':{'outstanding_gates':[]}})
            self.original = copy.deepcopy(lane)
            pin = {k:copy.deepcopy(lane.get(k)) for k in ('generation','revision','root','native','handoff')}
            s['throughput'] = {'batches': {'isolated': dict(id='isolated', state='closed',
                candidates={'consumer':pin}, isolated={'consumer':{'reason':'Builder prerequisite missing'}})}}

    def test_dispatches_once_same_owner_archives_pins_and_rebinds(self):
        tick(self.c); tick(self.c)
        launches = list(self.reg.control_status()['launches'].values())
        self.assertEqual(len(launches), 1)
        self.assertEqual(launches[0]['session'], 'session-consumer')
        self.c.dispatch(launches[0])
        lane = self.reg.status()['lanes']['consumer']
        self.assertEqual(lane['state'], 'running')
        self.assertEqual(lane['generation'], 2)
        self.assertIsNone(lane['handoff'])
        self.assertIsNone(lane['handoff_at'])
        self.assertEqual(lane['repair_history'][0]['handoff'], self.original['handoff'])
        with self.reg.transaction() as s:
            repairs = throughput_metrics(s, self.f.now)['blocked_handoff_repairs']
            self.assertEqual(repairs[0]['status'], 'running')
        tick(self.c)
        self.assertEqual(len(self.reg.control_status()['launches']), 1)

    def test_invalid_evidence_returns_to_existing_owner_once(self):
        with self.reg.transaction() as s:s['throughput']['batches']={}
        self.c.config['invalid_handoff_recovery']=True
        tick(self.c);tick(self.c)
        state=self.reg.snapshot()
        self.assertTrue(state['lanes']['consumer']['review_repair']['pin']['invalid_evidence'])
        self.assertEqual(state['lanes']['consumer']['handoff'],self.original['handoff'])
        launches=list(self.reg.control_status()['launches'].values())
        self.assertEqual(len(launches),1)
        self.c.dispatch(launches[0])
        self.assertEqual(self.reg.snapshot()['lanes']['consumer']['state'],'running')

    def test_valid_evidence_and_live_or_claimed_handoffs_are_preserved(self):
        with self.reg.transaction() as s:s['throughput']['batches']={}
        with patch.object(self.reg,'_delivery_read_handoff',return_value={}):invalid_handoffs(self.reg)
        self.assertNotIn('review_repair',self.reg.snapshot()['lanes']['consumer'])
        with patch.object(self.reg,'probe',return_value='alive'):invalid_handoffs(self.reg)
        self.assertNotIn('review_repair',self.reg.snapshot()['lanes']['consumer'])
        with self.reg.transaction() as s:
            s['throughput']['batches']['active']=dict(state='claimed',candidates={'consumer':{}},isolated={})
        invalid_handoffs(self.reg)
        self.assertNotIn('review_repair',self.reg.snapshot()['lanes']['consumer'])

    def test_live_unknown_and_protected_resources_do_not_resume(self):
        original_probe = self.reg.probe
        for health in ('alive','unknown'):
            self.reg.probe = lambda p: health
            tick(self.c)
            self.assertFalse(self.reg.control_status()['launches'])
        self.reg.probe = original_probe
        with self.reg.transaction() as s:
            s['leases']['build:private'] = dict(lane='consumer', process=self.f.identity)
        tick(self.c)
        self.assertFalse(self.reg.control_status()['launches'])

    def test_changed_pins_between_intent_and_bind_reject(self):
        tick(self.c)
        launch = next(iter(self.reg.control_status()['launches'].values()))
        with self.reg.transaction() as s: s['lanes']['consumer']['revision'] += 1
        with self.assertRaisesRegex(Rejected, 'isolated'):
            self.reg.bind_launch(launch['id'], self.f.identity)

    def test_unisolated_handoff_and_claimed_candidate_do_not_resume(self):
        with self.reg.transaction() as s:
            s['throughput']['batches']['active'] = dict(state='claimed', candidates={'consumer':{}}, isolated={})
        tick(self.c); self.assertFalse(self.reg.control_status()['launches'])
        with self.reg.transaction() as s: s['throughput']['batches'] = {}
        tick(self.c); self.assertFalse(self.reg.control_status()['launches'])

    def test_repair_loop_is_bounded(self):
        with self.reg.transaction() as s:
            for i in range(2):
                self.reg.control(s)['launches'][str(i)] = dict(lane='consumer', status='exited', reason='integration-repair:'+str(i))
        tick(self.c)
        self.assertEqual(len(self.reg.control_status()['launches']), 2)
        self.assertTrue(any(n['kind']=='integration_repair_exhausted' for n in self.reg.control_status()['notices'].values()))

    def test_independent_diagnosis_allows_one_extra_attempt_after_exhaustion(self):
        with self.reg.transaction() as s:
            for i in range(2):
                self.reg.control(s)['launches'][str(i)]=dict(lane='consumer',status='exited',reason='integration-repair:'+str(i))
            lane=s['lanes']['consumer']
            candidate={k:copy.deepcopy(lane.get(k)) for k in ('generation','revision','root','native','handoff')}
            lane['review_repair']=dict(candidate=candidate,pin=dict(independent_action='fresh',reason='New diagnosis'))
            s['support_actions']={'fresh':dict(key='consumer',action='repair',evidence=self.f.ev)}
        tick(self.c);tick(self.c)
        launches=self.reg.control_status()['launches']
        self.assertEqual(len(launches),3)
        latest=next(v for k,v in launches.items() if k not in ('0','1'))
        with self.reg.transaction() as s:s['control']['launches'][latest['id']]['status']='exited'
        tick(self.c)
        self.assertEqual(len(self.reg.control_status()['launches']),3)

    def test_isolation_visible_but_not_backpressure_and_new_pins_return(self):
        self.f.now = 10000
        update(self.c)
        with self.reg.transaction() as s:
            self.assertEqual(s['queue_pressure']['stages']['integration']['depth'], 0)
            self.assertEqual(s['queue_pressure']['stages']['repair']['depth'], 1)
            metrics = throughput_metrics(s, self.f.now)
            self.assertIsNone(metrics['oldest_handoff'])
            self.assertEqual(len(metrics['blocked_handoff_repairs']), 1)
            self.assertFalse(integration_items(s['lanes'], batches=s['throughput']['batches']))
        self.assertFalse(self.reg.status()['dispatch']['pause_new_slices'])
        with self.reg.transaction() as s: s['lanes']['consumer']['revision'] += 1
        self.f.now += 61
        update(self.c)
        with self.reg.transaction() as s:
            self.assertEqual(s['queue_pressure']['stages']['integration']['depth'], 1)
            self.assertEqual(s['queue_pressure']['stages']['repair']['depth'], 0)

    def test_pressure_history_from_old_schema_survives(self):
        update(self.c)
        with self.reg.transaction() as s:
            for h in s['queue_pressure']['history']:
                h['keys'].pop('repair'); h['events'].pop('repair')
        self.f.now += 61
        update(self.c)
