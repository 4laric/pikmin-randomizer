import copy
import unittest

from tests import test_planner_pool as fixtures
from workflow.planner_demand import dispatch_priority, no_work_observation, demand
from workflow.handoff import digest
from workflow.autofill import _planner_tick
from workflow.runner import write


class PlannerDemandTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.PlannerPoolTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.reg = self.f.reg

    def finish_no_work(self):
        self.f.tick()
        path = self.f.f.out / 'no-work.md'
        path.write_text('No-work. Waiting for owner source provider and issue #525. No new proposals.')
        self.reg.finish('next-cycle-1', 1, 'review-ready', 'No-work: provider prerequisite unchanged',
                        dict(path=str(path), sha256=digest(path)))
        self.f.tick()

    def test_completed_no_work_sleeps_past_cooldown_then_dependency_wakes(self):
        self.finish_no_work()
        self.f.f.now += 1000
        self.f.tick()
        self.assertEqual(len(self.reg.scheduling_status()['jobs']), 1)
        with self.reg.transaction() as s:
            pool = s['throughput_runtime']['autofill']['planner_pool']
            self.assertIn('enemies', pool['sleeping_scopes'])
            s['lanes']['owner']['heartbeat_at'] = self.f.f.now
            s['lanes']['owner']['revision'] += 1
        self.f.tick()
        self.assertEqual(len(self.reg.scheduling_status()['jobs']), 1)
        with self.reg.transaction() as s:
            s['lanes']['owner']['root']['head'] = 'b'*40
        self.f.tick()
        self.assertEqual(len(self.reg.scheduling_status()['jobs']), 2)

    def test_external_change_recheck_is_bounded(self):
        self.finish_no_work()
        self.f.f.now += 3601
        self.f.tick()
        self.assertEqual(len(self.reg.scheduling_status()['jobs']), 2)

    def test_explicit_prerequisite_stays_parked_until_accepted_then_wakes(self):
        self.finish_no_work()
        self.f.settings['planner_pool']['helpers'][0]['prerequisite_lanes'] = ['new-provider']
        self.f.f.now += 4000
        self.f.tick()
        self.assertEqual(len(self.reg.scheduling_status()['jobs']), 1)
        with self.reg.transaction() as s:
            s['lanes']['new-provider'] = dict(s['lanes']['owner'], lane='new-provider', issue=991, state='done')
        self.f.tick()  # done without an accepted disposition is insufficient
        self.assertEqual(len(self.reg.scheduling_status()['jobs']), 1)
        with self.reg.transaction() as s:
            s['lanes']['new-provider']['review_disposition'] = {'summary':'Provider contract accepted'}
        self.f.tick()
        self.assertEqual(len(self.reg.scheduling_status()['jobs']), 2)

    def test_unrelated_lane_changes_do_not_wake_referenced_dependency(self):
        self.finish_no_work()
        with self.reg.transaction() as s:
            record = s['throughput_runtime']['autofill']['planner_pool']['scopes']['enemies']
            s['lanes']['unrelated'] = dict(s['lanes']['owner'], lane='unrelated', issue=999)
            self.assertFalse(demand(self.reg, s, record)[0])

    def test_missing_or_changed_evidence_cannot_suppress_work(self):
        self.finish_no_work()
        with self.reg.transaction() as s:
            record = s['throughput_runtime']['autofill']['planner_pool']['scopes']['enemies']
            lane = s['lanes']['next-cycle-1']
            lane['review_disposition']['archived_evidence']['sha256'] = '0'*64
            self.assertIsNone(no_work_observation(self.reg, s, record))

    def test_old_planner_beats_new_high_priority_but_not_execution(self):
        old = dict(lane='planning-old',created_at=0,focus='existing_content',work_class='expansion')
        new = dict(lane='planning-new',created_at=990,focus='enemy_acceptance')
        execution = dict(lane='implementation',created_at=999,work_class='expansion')
        lanes = {i['lane']:dict(state='ready',dependencies=[]) for i in [old,new,execution]}
        ordered = sorted([new,old,execution],key=lambda i:dispatch_priority(i,lanes,1000))
        self.assertEqual(ordered,[execution,old,new])
        # Once both are overdue, FIFO also defeats recurring high-priority work.
        newer_old = dict(new,created_at=100)
        self.assertLess(dispatch_priority(old,lanes,1000),dispatch_priority(newer_old,lanes,1000))

    def test_parallel_coordinator_waits_for_actual_publication_demand(self):
        self.f.f.planner()
        settings = self.f.settings
        settings['planner_pool']['helpers'][0]['defer_for_review'] = [str(self.f.f.out)]
        self.assertFalse(_planner_tick(self.f.controller, settings, 'manifest'))
        self.assertFalse(self.reg.control_status()['launches'])
        proposal = self.f.f.make_spec('fresh-proposal', 990)
        write(self.f.f.out/'proposals-fresh.json', {'items':[proposal]})
        self.assertTrue(_planner_tick(self.f.controller, settings, 'manifest'))
