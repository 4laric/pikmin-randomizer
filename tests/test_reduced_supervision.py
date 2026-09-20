import copy
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from workflow import reduced_supervision as rs
from workflow.no_progress import Parked
from tests.test_no_progress import Base


class InputsTests(unittest.TestCase):
    def setUp(self):
        self.lane = dict(lane='rd-test', state='blocked', dependencies=['producer #8'],
                         root={'head': 'a'}, native={'head': 'b'})
        self.state = dict(lanes={'rd-test': self.lane, 'producer': dict(issue=8, root={'head': 'c'})})
        rs.record_blocked(self.state, self.lane)

    def test_no_time_prompt_or_generation_escape(self):
        self.lane.update(next_action='try again', generation=999, wake_after=0, stall_streak=0)
        with self.assertRaises(Parked): rs.check_retry(self.state, self.lane)

    def test_source_delivery_and_approval_each_unblock(self):
        for kind in ('source', 'delivery', 'approval'):
            state = copy.deepcopy(self.state)
            if kind == 'source': state['lanes']['producer']['root']['head'] = 'd'
            if kind == 'delivery': state['lanes']['producer']['integration'] = {'root_commit': 'd'}
            if kind == 'approval': state['approvals'] = {'decision': {'lane': 'rd-test'}}
            rs.check_retry(state, state['lanes']['rd-test'])

    def test_unrelated_change_does_not_unblock(self):
        self.state['lanes']['unrelated'] = {'root': {'head': 'new'}}
        self.state['approvals'] = {'unrelated': {'lane': 'other'}}
        with self.assertRaises(Parked): rs.check_retry(self.state, self.lane)

    def test_legacy_and_live_recovery_are_not_blocked(self):
        self.lane.pop('reduced_blocked_inputs')
        rs.check_retry(self.state, self.lane)
        rs.record_blocked(self.state, self.lane)
        self.lane['state'] = 'running'
        rs.check_retry(self.state, self.lane)


class RegistryTests(Base):
    def setUp(self):
        super().setUp()
        with self.reg.transaction() as state:
            self.reg.control(state)
            lane = state['lanes'].pop('consumer')
            lane['lane'] = 'rd-test'
            state['lanes']['rd-test'] = lane

    def test_all_wake_reasons_refuse_unchanged_blocked_lane(self):
        self.reg.finish('rd-test', 1, 'blocked', 'Need producer', self.f.ev, ['#900'])
        self.stop('rd-test')
        for reason in ('dependency_ready', 'shepherd:x', 'operator: retry', 'provider-error:x'):
            with self.assertRaises(Parked):
                self.reg.plan_launch('rd-test', reason, 'Try', self.models)
        item = self.reg.plan_launch('rd-test', 'operator: deliberate check', 'Try', self.models,
                                   carry={'operator_retry_evidence': self.f.ev})
        self.assertEqual(item['status'], 'intent')

    def test_explicit_retry_requires_real_evidence(self):
        self.reg.finish('rd-test', 1, 'blocked', 'Need producer', self.f.ev, ['#900'])
        self.stop('rd-test')
        from workflow.handoff import Rejected
        with self.assertRaises(Rejected):
            self.reg.plan_launch('rd-test', 'operator: retry', 'Try', self.models,
                                 carry={'operator_retry_evidence': {'path': 'absent', 'sha256': 'bad'}})

    def test_changed_source_is_not_vetoed_by_legacy_timed_guard(self):
        self.reg.finish('rd-test', 1, 'blocked', 'Need producer', self.f.ev, ['#900'])
        self.stop('rd-test')
        with self.reg.transaction() as state:
            lane = state['lanes']['rd-test']
            lane.update(stall_streak=5, wake_after=self.f.now+999999)
            lane['root']['head'] = 'f' * 40
        item = self.reg.plan_launch('rd-test', 'consumer-prerequisite:new', 'Try', self.models)
        self.assertEqual(item['status'], 'intent')


class ReconcileTests(Base):
    def test_real_partitioned_snapshot(self):
        self.c.config['reduced_supervision'] = {'enabled': True}
        rs.tick(self.c)
        self.assertTrue((self.c.base/'reduced-supervision.json').is_file())

    def setup_request(self, generation=1):
        self.c.config['reduced_supervision'] = {'enabled': True}
        self.l = dict(lane='rd-test', state='handoff_ready', generation=1)
        self.reg.snapshot = Mock(return_value={'lanes': {'rd-test': self.l}})
        self.reg.recovery_safe = Mock(return_value=True)
        self.reg.receipt = Mock()
        self.path = self.f.root / 'output/reduced/rd-test/receipt-request.json'
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps({'key': 'rd-test', 'generation': generation, 'record': {}}))

    def test_request_replayed_via_fenced_api_and_interval_bounded(self):
        self.setup_request()
        rs.tick(self.c); rs.tick(self.c)
        self.reg.receipt.assert_called_once()
        self.assertEqual(json.loads((self.c.base/'reduced-supervision.json').read_text())['checked'][0]['action'], 'receipted')

    def test_stale_request_rejected_without_mutating_lane(self):
        self.setup_request(generation=2)
        rs.tick(self.c)
        self.reg.receipt.assert_not_called()

    def test_live_owner_is_protected(self):
        self.setup_request()
        self.reg.recovery_safe.return_value = False
        rs.tick(self.c)
        self.reg.receipt.assert_not_called()

    def test_invalid_evidence_failure_remains_visible(self):
        self.setup_request()
        self.reg.receipt.side_effect = rs.Rejected('Missing or changed evidence')
        rs.tick(self.c)
        report = json.loads((self.c.base/'reduced-supervision.json').read_text())
        self.assertEqual(report['checked'][0]['action'], 'needs_operator')
        self.assertIn('Missing or changed evidence', report['checked'][0]['error'])
