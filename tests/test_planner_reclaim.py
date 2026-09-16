import copy
import unittest
from tests.test_planner_pool import PlannerPoolTests
from workflow.autofill import autofill_tick, autofill_status, _state, _refresh_readiness
from workflow.planner_reclaim import reclaim_for


class PlannerReclaimTests(unittest.TestCase):
    def setUp(self):
        self.f = PlannerPoolTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.reg, self.controller = self.f.reg, self.f.controller
        self.f.tick()
        self.spec = self.f.f.make_spec('implementation', 999)
        self.f.f.save([self.spec])
        self.reader = lambda n: self.f.f.remote[n]
        from workflow.control import fingerprint
        with self.reg.transaction() as s:
            _state(s)['items'][self.spec['id']] = dict(spec_hash=fingerprint(self.spec), lane='implementation',
                                                     priority='enemy_acceptance', phase='pending', status='pending')
        _refresh_readiness(self.controller, [self.spec], self.reader)

    def test_ready_without_idle_then_reclaimed_and_provisioned(self):
        report=autofill_status(self.reg)
        self.assertEqual(report['idle_workers_count'], 0)
        self.assertEqual(report['awaiting_worker_count'], 1)
        self.assertTrue(report['items']['implementation']['ready'])
        autofill_tick(self.controller, issue_reader=self.reader)
        state=self.reg.status()
        self.assertIn('implementation', state['lanes'])
        old=state['lanes']['next-cycle-1']
        self.assertIn('cancelled_before_start', old)
        self.assertNotIn('review_disposition', old)
        self.assertEqual(state['metrics']['completed_slices'], 0)
        self.assertIsNone(reclaim_for(self.controller,self.spec))
        self.assertEqual(self.reg.scheduling_status()['jobs']['autofill:next-cycle-1']['status'],'cancelled')

    def test_intent_cancelled_but_spawn_artifact_protected(self):
        assignment=self.reg.assign_job('one',60)
        launch=self.reg.plan_assignment(assignment['id'],['paid/muse'],60)
        directory=self.controller.launch_directory(launch['id']);directory.mkdir(parents=True)
        (directory/'spawn.json').write_text('{}')
        self.assertIsNone(reclaim_for(self.controller,self.spec))
        (directory/'spawn.json').unlink(); directory.rmdir()
        self.assertEqual(reclaim_for(self.controller,self.spec),'next-cycle-1')
        self.assertEqual(self.reg.control_status()['launches'][launch['id']]['status'],'cancelled')
        self.assertEqual(self.reg.scheduling_status()['assignments'][assignment['id']]['status'],'cancelled')

    def test_execution_claims_and_unknown_process_protected(self):
        with self.reg.transaction() as s: original=copy.deepcopy(s['lanes']['next-cycle-1'])
        for changes in ({'generation':2}, {'started_at':1}, {'process':{'health':'unknown'}}, {'state':'running'}):
            with self.reg.transaction() as s: s['lanes']['next-cycle-1']={**original,**changes}
            self.assertIsNone(reclaim_for(self.controller,self.spec))
        with self.reg.transaction() as s:
            s['lanes']['next-cycle-1']=original
            s['planning_claims']={'topic:x':{'lane':'next-cycle-1'}}
        self.assertIsNone(reclaim_for(self.controller,self.spec))

    def test_invalid_or_incompatible_work_cannot_reclaim(self):
        with self.reg.transaction() as s: _state(s)['items']['implementation']['ready']=False
        self.assertIsNone(reclaim_for(self.controller,self.spec))
        with self.reg.transaction() as s:
            _state(s)['items']['implementation']['ready']=True
            self.reg.scheduling(s)['workers']['one']['capabilities']=[]
        self.assertIsNone(reclaim_for(self.controller,self.spec))
