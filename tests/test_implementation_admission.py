import threading
import unittest
from tests import test_workflow_autofill as fixtures
from workflow.implementation_admission import tick
from workflow.autofill import _refresh_readiness
from workflow.handoff import Rejected
from unittest.mock import patch


class ImplementationAdmissionTests(unittest.TestCase):
    def test_capacity_block_is_retried_without_main_readiness_refresh(self):
        self.f.tick()
        with self.f.reg.transaction() as state:
            item=state['throughput_runtime']['autofill']['items']['next']
            item.update(status='blocked',ready=False,dependency_kind='worker_capacity',
                        updated_at=self.f.reg.clock()-31)
        self.assertEqual(tick(self.f.controller,self.f.remote.__getitem__),['next'])
        self.assertEqual(tick(self.f.controller,self.f.remote.__getitem__),[])

    def test_other_blocker_is_not_retried_as_capacity(self):
        self.f.tick()
        with self.f.reg.transaction() as state:
            state['throughput_runtime']['autofill']['items']['next'].update(
                status='blocked',ready=False,dependency_kind='ownership',updated_at=0)
        self.assertEqual(tick(self.f.controller,self.f.remote.__getitem__),[])

    def setUp(self):
        self.f = fixtures.AutofillTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.f.controller._admission_monitor = threading.Event()

    def test_multiple_ready_jobs_admitted_without_main_tick_or_duplicate_replay(self):
        self.f.second_worker()
        second = self.f.make_spec('another', 901)
        self.f.save([self.f.spec, second])
        self.f.tick()
        self.assertNotIn('next', self.f.reg.snapshot()['lanes'])
        admitted = tick(self.f.controller, self.f.remote.__getitem__)
        self.assertEqual(set(admitted), {'next', 'another'})
        self.assertEqual(tick(self.f.controller, self.f.remote.__getitem__), [])
        state = self.f.reg.snapshot()
        self.assertNotEqual(state['lanes']['next']['worker_id'], state['lanes']['another']['worker_id'])

    def test_completed_history_does_not_take_writer_lock(self):
        self.f.tick()
        with self.f.reg.transaction() as state:
            state['throughput_runtime']['autofill']['items']['next']['status'] = 'completed'
        with patch.object(self.f.reg, 'transaction', side_effect=AssertionError('historical write')):
            _refresh_readiness(self.f.controller, [self.f.spec], self.f.remote.__getitem__)

    def test_nested_writer_is_rejected_without_thirty_second_deadlock(self):
        with self.f.reg.transaction():
            with self.assertRaisesRegex(Rejected, 'Nested registry'):
                with self.f.reg.transaction():
                    pass

    def test_recovered_owner_retries_without_readiness_scan(self):
        self.f.tick()
        with self.f.reg.transaction() as state:
            item=state['throughput_runtime']['autofill']['items']['next']
            item.update(status='blocked',ready=False,dependency_kind='integration_owner',updated_at=self.f.reg.clock()-31)
        with patch.object(self.f.reg,'integration_owner_available',return_value=False):
            self.assertEqual(tick(self.f.controller,self.f.remote.__getitem__),[])
        self.assertEqual(tick(self.f.controller,self.f.remote.__getitem__),['next'])
        self.assertEqual(tick(self.f.controller,self.f.remote.__getitem__),[])
