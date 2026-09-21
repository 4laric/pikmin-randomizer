import copy
import unittest
from unittest.mock import patch

from tests import test_workflow_autofill as fixtures
from workflow.autofill import _workers
from workflow.worker_capacity import park_blocked, parked
from workflow.handoff import Rejected
from workflow.worker_roster import roster


class WorkerCapacityTests(unittest.TestCase):
    def test_pending_delivery_has_priority_but_reservation_expires(self):
        park_blocked(self.reg)
        state=self.reg.snapshot();lane=state['lanes']['one']
        self.assertTrue(_workers(self.reg,state))
        state['handoff_resume_reservations']={'one':dict(worker_id=lane['worker_id'],
            generation=lane['generation'],reason='delivery',expires_at=self.reg.clock()+120)}
        self.assertFalse(_workers(self.reg,state))
        state['handoff_resume_reservations']['one']['expires_at']=self.reg.clock()-1
        self.assertTrue(_workers(self.reg,state))
        state['handoff_resume_reservations']['one'].update(expires_at=self.reg.clock()+120,generation=0)
        self.assertTrue(_workers(self.reg,state))

    def setUp(self):
        self.f = fixtures.AutofillTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.reg = self.f.reg
        with self.reg.transaction() as state:
            state['lanes']['one'].pop('review_disposition')
            state['lanes']['one']['state'] = 'ready'
        self.reg.finish('one', 1, 'blocked', 'Waiting for producer', self.f.f.evidence, ['#123'])

    def test_reuse_preserves_blocker_and_prevents_concurrent_resume(self):
        before = copy.deepcopy(self.reg.snapshot()['lanes']['one'])
        self.assertEqual(park_blocked(self.reg), ['one'])
        self.assertEqual(park_blocked(self.reg), [])
        self.assertEqual(len(_workers(self.reg, self.reg.snapshot())), 1)
        self.f.tick()
        state = self.reg.snapshot()
        for key in ('state', 'dependencies', 'owned_files', 'outcome', 'task_id'):
            self.assertEqual(state['lanes']['one'][key], before[key])
        self.assertEqual(state['lanes']['next']['worker_id'], 'one')
        with self.assertRaisesRegex(Rejected, 'active slice'):
            self.reg.plan_launch('one', 'resume', 'Resume old work', ['paid/muse'])
        a = self.reg.assign_job('one', 60)
        self.assertEqual(a['lane'], 'next')

    def test_live_unknown_leases_and_pending_launches_protect_capacity(self):
        for health in ('alive', 'unknown'):
            with self.reg.transaction() as state:
                state['lanes']['one']['process']['health'] = health
            self.assertEqual(park_blocked(self.reg), [])
        with self.reg.transaction() as state:
            state['lanes']['one']['process']['health'] = 'dead'
            state['leases']['build:private'] = dict(lane='one', process=dict(health='alive'))
        self.assertEqual(park_blocked(self.reg), [])
        with self.reg.transaction() as state:
            state['leases'].clear()
            state['queue']['q'] = dict(lane='one', process=dict(health='unknown'))
        self.assertEqual(park_blocked(self.reg), [])
        with self.reg.transaction() as state:
            state['queue'].clear()
        self.reg.plan_launch('one', 'resume', 'Resume old work', ['paid/muse'])
        self.assertEqual(park_blocked(self.reg), [])

    def test_generation_and_launch_invalidate_reuse(self):
        park_blocked(self.reg)
        self.reg.plan_launch('one', 'resume', 'Resume old work', ['paid/muse'])
        self.assertEqual(_workers(self.reg, self.reg.snapshot()), [])
        lane = self.reg.snapshot()['lanes']['one']
        lane['generation'] += 1
        self.assertFalse(parked(lane))

    def test_assignment_parked_is_not_completed(self):
        with self.reg.transaction() as state:
            pool = self.reg.scheduling(state)
            pool['jobs']['job'] = dict(status='assigned')
            pool['assignments']['a'] = dict(id='a', job='job', lane='one', worker_id='one',
                                          status='dispatched', launch_id='launch')
            self.reg.control(state)['launches']['launch'] = dict(lane='one', status='exited', bound_generation=1)
        park_blocked(self.reg)
        state = self.reg.snapshot()
        self.assertEqual(state['throughput']['assignments']['a']['status'], 'parked')
        self.assertEqual(state['throughput']['jobs']['job']['status'], 'parked')
        view = roster(state, {'one'}, {})
        self.assertEqual(view['blocked_lanes'], 1)
        self.assertEqual(view['parked_lanes'], 1)
        self.assertEqual(view['counts'], {'Idle': 1})

    def test_missing_evidence_and_assignment_generation_refuse_parking(self):
        with self.reg.transaction() as state:
            self.reg.scheduling(state)['assignments']['a'] = dict(lane='one', status='assigned', generation=999)
        self.assertEqual(park_blocked(self.reg), [])

    def test_owner_and_handoff_are_never_parked(self):
        with self.reg.transaction() as state:
            state['throughput']['workstreams']['p2']['owner_lane'] = 'one'
        self.assertEqual(park_blocked(self.reg), [])
        with self.reg.transaction() as state:
            state['throughput']['workstreams']['p2']['owner_lane'] = 'owner'
            state['lanes']['one']['handoff'] = {'pending': True}
        self.assertEqual(park_blocked(self.reg), [])

    def test_new_live_identity_prevents_reuse_of_parked_lane(self):
        park_blocked(self.reg)
        with self.reg.transaction() as state:
            state['lanes']['one']['process']['health'] = 'alive'
        self.assertEqual(_workers(self.reg, self.reg.snapshot()), [])

    def test_changed_evidence_refuses_parking(self):
        with self.reg.transaction() as state:
            state['lanes']['one']['outcome']['evidence']['sha256'] = 'bad'
        self.assertEqual(park_blocked(self.reg), [])

    def test_evidence_changed_after_the_committed_read_refuses_parking(self):
        path = self.reg.evidence(self.f.f.evidence)
        original, writes = self.reg.transaction, []
        def change_then_write(**kw):  # After the pre-lock hash, before the writer rechecks.
            writes.append(1); path.write_text('changed after the read', encoding='utf-8'); return original(**kw)
        with patch.object(self.reg, 'transaction', side_effect=change_then_write):
            self.assertEqual(park_blocked(self.reg), [])
        self.assertEqual(writes, [1])
        self.assertFalse(parked(self.reg.snapshot()['lanes']['one']))
