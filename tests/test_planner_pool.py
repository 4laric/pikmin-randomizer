import copy
import json
import unittest
from unittest.mock import patch
from tests import test_workflow_autofill as fixtures
from workflow.planner_pool import tick, merge_proposals
from workflow.autofill import _state
from workflow.handoff import digest, Rejected
from workflow.runner import write


class PlannerPoolTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.AutofillTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.reg, self.root, self.controller = self.f.reg, self.f.root, self.f.controller
        self.settings = self.controller.config['throughput']['autofill']
        self.settings.update(low_watermark=3)
        self.template = self.f.out/'helper.json'; write(self.template,self.f.spec)
        self.settings['planner_pool'] = dict(enabled=True,max_active=3,items_per_helper=1,reserve_workers=0,
            helpers=[dict(scope='enemies',template=str(self.template),sha256=digest(self.template))])

    def tick(self):
        tick(self.controller,self.settings,lambda n:self.f.remote[n])

    def test_provision_once_and_do_not_touch_manifest(self):
        before=self.f.manifest.read_bytes(); self.tick(); self.tick()
        self.assertEqual(len(self.reg.scheduling_status()['jobs']),1)
        self.assertEqual(self.f.manifest.read_bytes(),before)
        lane=self.reg.status()['lanes']['next-cycle-1']
        self.assertEqual(lane['task_id'],'opencode:session-one')

    def test_full_backlog_and_no_idle_suppress_helpers(self):
        with self.reg.transaction() as s:
            _state(s)['items']={str(i):dict(ready=True) for i in range(3)}
        self.tick(); self.assertFalse(self.reg.scheduling_status()['jobs'])
        with self.reg.transaction() as s:
            _state(s)['items']={}; s['lanes']['one']['state']='running'
        self.tick(); self.assertFalse(self.reg.scheduling_status()['jobs'])

    def test_live_helper_never_reassigned(self):
        self.tick()
        with self.reg.transaction() as s:
            s['lanes']['next-cycle-1'].update(state='running',process={'health':'alive'})
        self.tick(); self.assertEqual(len(self.reg.scheduling_status()['jobs']),1)

    def test_planning_completion_is_not_gameplay_acceptance(self):
        self.tick(); key='next-cycle-1'; lane=self.reg.status()['lanes'][key]
        self.reg.finish(key,lane['generation'],'review-ready','Partition planning report',self.f.f.evidence)
        self.tick()
        self.assertEqual(self.reg.status()['lanes'][key]['state'],'done')
        self.assertEqual(self.reg.status()['metrics']['completed_slices'],0)
        self.tick(); self.assertEqual(len(self.reg.scheduling_status()['jobs']),1)

    def test_protected_child_prevents_report_release(self):
        self.tick(); key='next-cycle-1'; lane=self.reg.status()['lanes'][key]
        self.reg.finish(key,lane['generation'],'review-ready','Planning report',self.f.f.evidence)
        with self.reg.transaction() as s:
            s['leases']['build:output/test'] = dict(lane=key,generation=lane['generation'],process={'health':'alive'},expires_at=9999)
        self.tick(); self.assertEqual(self.reg.status()['lanes'][key]['state'],'review_ready')

    def test_changed_template_rejected(self):
        self.template.write_text('{}')
        with self.assertRaises(Rejected): self.tick()

    def test_idle_fill_ignores_low_watermark_but_reserves_unclaimed_work(self):
        self.f.second_worker()
        self.settings['planner_pool'].update(use_idle_capacity=True)
        self.settings['low_watermark']=1
        with self.reg.transaction() as s:
            _state(s)['items']['implementation']=dict(ready=True,lane='not-provisioned')
        self.tick()
        self.assertEqual(len(self.reg.scheduling_status()['jobs']),1)

    def test_idle_fill_uses_all_available_workers_for_distinct_shards(self):
        self.f.second_worker()
        other=self.f.make_spec('more-helper',904)
        path=self.f.out/'more-template.json'; write(path,other)
        self.settings['planner_pool'].update(use_idle_capacity=True)
        self.settings['planner_pool']['helpers'].append(dict(scope='more',template=str(path),sha256=digest(path)))
        self.settings['low_watermark']=1
        self.tick(); self.tick(); self.tick()
        self.assertEqual(len(self.reg.scheduling_status()['jobs']),2)

    def test_idle_fill_cannot_take_workers_needed_for_implementation(self):
        self.settings['planner_pool'].update(use_idle_capacity=True)
        with self.reg.transaction() as s:
            _state(s)['items']['implementation']=dict(ready=True,lane='not-provisioned')
        self.tick(); self.assertFalse(self.reg.scheduling_status()['jobs'])

    def test_legacy_coordinator_must_exit_before_partition_handover(self):
        self.settings['planner_pool']['wait_for_launches']=['old']
        with self.reg.transaction() as s:
            self.reg.control(s)['launches']['old']=dict(status='running',lane='old-coordinator')
        self.tick(); self.assertFalse(self.reg.scheduling_status()['jobs'])
        with self.reg.transaction() as s:
            self.reg.control(s)['launches']['old']['status']='exited'
        self.tick(); self.assertEqual(len(self.reg.scheduling_status()['jobs']),1)

    def test_two_partitions_plan_in_parallel_without_duplicate_scope(self):
        self.f.second_worker()
        other=self.f.make_spec('second-helper',903)
        path=self.f.out/'second-template.json'; write(path,other)
        self.settings['planner_pool']['helpers'].append(dict(scope='dungeons',template=str(path),sha256=digest(path)))
        self.tick(); self.tick(); self.tick()
        self.assertEqual(len(self.reg.scheduling_status()['jobs']),2)
        with self.reg.transaction() as s:
            self.assertEqual(_state(s)['planner_pool']['active'],2)

    def test_full_backlog_allows_running_turn_to_finish_but_no_new_turn(self):
        self.tick()
        with self.reg.transaction() as s:
            for i in range(3): _state(s)['items']['ready-'+str(i)] = dict(ready=True)
        self.tick()
        self.assertEqual(len(self.reg.scheduling_status()['jobs']),1)
        with self.reg.transaction() as s: self.assertEqual(_state(s)['planner_pool']['target'],0)

    def test_already_claimed_ready_work_does_not_double_reserve_idle_workers(self):
        self.f.second_worker()
        self.settings['planner_pool']['reserve_workers']=1
        with self.reg.transaction() as s:
            _state(s)['items']['claimed']=dict(ready=True,lane='owner')
        self.tick()
        self.assertEqual(len(self.reg.scheduling_status()['jobs']),1)

    def test_serial_publication_idempotent_and_conflict_checked(self):
        spec=self.f.make_spec('proposal',901)
        proposal=self.f.out/'proposal.json';write(proposal,dict(items=[spec]))
        reader=lambda n:self.f.remote[n]
        self.assertEqual(merge_proposals(self.reg,self.f.manifest,proposal,reader),['proposal'])
        self.assertEqual(merge_proposals(self.reg,self.f.manifest,proposal,reader),[])
        other=self.f.make_spec('collision',902)
        other['lane']['owned_files']=spec['lane']['owned_files']
        write(proposal,dict(items=[other]))
        with self.assertRaises(Rejected): merge_proposals(self.reg,self.f.manifest,proposal,reader)
        self.assertEqual(len(json.loads(self.f.manifest.read_text())['items']),2)

    def test_lease_only_autofill_ignores_preparation_reservations(self):
        self.f.spec['heavy']=True
        self.f.save([self.f.spec])
        self.settings['planner_pool']['enabled']=False
        with self.reg.transaction() as s:
            s['build_capacity']={'lease_only':True}
            s['leases']['build:output/occupied']=dict(lane='owner',process={'health':'alive'},expires_at=9999)
        self.f.tick()
        self.assertIn('next',self.reg.status()['lanes'])


if __name__=='__main__': unittest.main()
