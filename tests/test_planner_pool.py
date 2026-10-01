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
    def test_typed_delivery_recovery_bypasses_unrelated_publication_wait(self):
        self.settings['planner_pool']['cross_partition_recovery']=True
        self.settings['planner_pool']['helpers'][0]['defer_for_review']=[str(self.f.inbox)]
        with self.reg.transaction() as s:
            original=s['lanes']['one']
            s['lanes']['gap']=dict(copy.deepcopy(original),lane='gap',worker_id='outside',state='blocked',issue=701,
                dependencies=['source'],outcome={'outcome':'blocked','evidence':{'path':str(self.f.brief),'sha256':digest(self.f.brief)}})
            s['lanes']['source']=dict(copy.deepcopy(original),lane='source',worker_id='outside-source',issue=702)
            s['throughput']['workstreams']['p2']['lanes'].append('gap')
            owner=s['throughput']['workstreams']['p2']['owner_lane']
            s['delivery_contracts']={'c':dict(id='c',consumer='gap',producer='source',owner=owner,
                kind='source_integration',requirement='source',acceptance_check='compile original consumer')}
        with patch('workflow.planner_pool.review_pending',return_value=True):self.tick()
        state=self.reg.snapshot()
        row=state['throughput_runtime']['autofill']['planner_pool']['scopes']['enemies']
        self.assertTrue(row['prerequisite_recovery'].startswith('delivery-recovery:'))
        self.assertIn('next-cycle-1',state['lanes'])

    def test_classification_uses_normal_queue_and_enforces_completion(self):
        self.settings['planner_pool']['cross_partition_recovery']=True
        self.settings['planner_pool']['helpers'][0]['defer_for_review']=[str(self.f.inbox)]
        with self.reg.transaction() as s:
            s['lanes']['gap']=dict(copy.deepcopy(s['lanes']['one']),lane='gap',worker_id='outside',
                state='blocked',issue=701,dependencies=['unknown input'],
                outcome={'outcome':'blocked','evidence':{'path':str(self.f.brief),'sha256':digest(self.f.brief)}})
        with patch('workflow.planner_pool.review_pending',return_value=True):self.tick()
        s=self.reg.snapshot();row=s['throughput_runtime']['autofill']['planner_pool']['scopes']['enemies']
        self.assertEqual(row['classification_target']['consumer'],'gap')
        self.assertTrue(row['actionable_support'])
        self.assertIn('next-cycle-1',s['lanes'])
        from workflow.support_actions import require_outcomes
        with self.assertRaisesRegex(Rejected,'complete dependency classification'):
            require_outcomes(s,'next-cycle-1')

    def test_internal_followup_uses_normal_queue_with_action_gate(self):
        self.settings['planner_pool']['cross_partition_recovery']=True
        self.settings['planner_pool']['helpers'][0]['defer_for_review']=[str(self.f.inbox)]
        with self.reg.transaction() as s:
            s['lanes']['gap']=dict(copy.deepcopy(s['lanes']['one']),lane='gap',worker_id='outside',
                state='blocked',issue=701,dependencies=['unknown input'],
                outcome={'outcome':'blocked','evidence':{'path':str(self.f.brief),'sha256':digest(self.f.brief)}})
            from workflow.dependency_classification import signature
            s['dependency_classifications']={'finding':dict(id='finding',at=1,consumer='gap',
                snapshot=signature(s['lanes']['gap']),evidence=s['lanes']['gap']['outcome']['evidence'],
                dispositions=[dict(requirement='unknown input',check='run original check',reason='missing wiring',
                    internal_blocker=dict(kind='missing_producer',missing='engine wiring',
                        next_action='prepare private engine repair',inspected_lanes=[]))])}
        with patch('workflow.planner_pool.review_pending',return_value=True):self.tick()
        s=self.reg.snapshot();row=s['throughput_runtime']['autofill']['planner_pool']['scopes']['enemies']
        self.assertTrue(row['prerequisite_recovery'].startswith('internal-followup:'))
        self.assertNotIn('classification_target',row)
        self.assertTrue(row['actionable_support'])
        self.assertIn('next-cycle-1',s['lanes'])
        from workflow.support_actions import require_outcomes
        with self.assertRaisesRegex(Rejected,'actionable outcome'):
            require_outcomes(s,'next-cycle-1')

    def test_uncapped_helpers_follow_demand_and_execution_reserve(self):
        from workflow.planner_pool import helper_target, support_target
        config=dict(max_active=None,backpressure_planning_limit=None,
                    integration_support_max_active=None,use_idle_capacity=True,reserve_workers=2)
        args=dict(helper_count=40,ready=0,unclaimed_ready=3,idle=35,active=0,integration={'depth':10})
        self.assertEqual(helper_target(config,**args),30)
        self.assertEqual(helper_target(config,**dict(args,helper_count=7)),7)
        self.assertEqual(helper_target(config,**dict(args,idle=5)),0)
        self.assertEqual(support_target(config,demanded=40,idle=35,active=0,unclaimed_ready=3),30)
        self.assertEqual(support_target(config,demanded=0,idle=35,active=0,unclaimed_ready=0),0)

    def test_backpressure_planning_is_bounded_and_preserves_ready_capacity(self):
        from workflow.planner_pool import helper_target
        config=dict(max_active=12,use_idle_capacity=True,reserve_workers=2,
                    backpressure_planning_limit=2)
        args=dict(helper_count=10,ready=0,unclaimed_ready=0,idle=20,active=0,
                  integration={'depth':4})
        self.assertEqual(helper_target(config,**args),2)
        self.assertEqual(helper_target(config,**dict(args,idle=3,unclaimed_ready=1)),0)
        self.assertEqual(helper_target(dict(config,backpressure_planning_limit=0),**args),0)
        self.assertEqual(helper_target(config,**dict(args,helper_count=0)),0)

    def test_support_capacity_preserves_execution_reserve_and_limit(self):
        from workflow.planner_pool import support_target
        config=dict(integration_support_max_active=2,reserve_workers=2)
        self.assertEqual(support_target(config,demanded=5,idle=10,active=0,unclaimed_ready=0),2)
        self.assertEqual(support_target(config,demanded=5,idle=3,active=0,unclaimed_ready=1),0)
        self.assertEqual(support_target(config,demanded=0,idle=10,active=0,unclaimed_ready=0),0)

    def test_support_provisions_and_dispatches_with_stopped_integrator(self):
        spec=self.f.make_spec('integration-support-test',999)
        spec['lane']['target_level']='planning-only'
        write(self.template,spec)
        self.settings['planner_pool']['helpers'][0]['sha256']=digest(self.template)
        with self.reg.transaction() as state:
            state['lanes']['owner']['process']={'health':'dead'}
        self.tick()
        lane='integration-support-test-cycle-1'
        self.assertIn(lane,self.reg.status()['lanes'])
        assignment=self.reg.assign_job('one',60)
        self.assertEqual(assignment['lane'],lane)
        launch=self.reg.plan_assignment(assignment['id'],['paid/muse'],60)
        self.assertEqual(launch['status'],'intent')

    def test_bounded_parallel_preparation_keeps_reserve_and_is_replay_safe(self):
        for i in range(4):
            key='spare-burst-'+str(i)
            self.f.f.add_lane(key)
            with self.reg.transaction() as state:
                state['lanes'][key].update(state='done',review_disposition={'summary':'accepted'})
            self.reg.register_pool_worker(key,['review'],['python'],'operator')
            spec=self.f.make_spec('planning-burst-'+str(i),970+i)
            spec['lane']['target_level']='planning-only'
            path=self.f.out/('burst-'+str(i)+'.json');write(path,spec)
            self.settings['planner_pool']['helpers'].append(dict(scope=key,template=str(path),sha256=digest(path)))
        self.settings['planner_pool']['helpers']=self.settings['planner_pool']['helpers'][1:]
        self.settings['planner_pool'].update(use_idle_capacity=True,max_active=10,provisions_per_tick=4,reserve_workers=2)
        with self.reg.transaction() as state:state['lanes']['owner']['process']={'health':'dead'}
        self.tick()
        self.assertEqual(len(self.reg.scheduling_status()['jobs']),3)
        self.tick()
        self.assertEqual(len(self.reg.scheduling_status()['jobs']),3)

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

    def test_idle_capacity_provisions_more_than_three_and_keeps_reserve(self):
        for i in range(6):
            key = 'spare-' + str(i)
            self.f.f.add_lane(key)
            with self.reg.transaction() as state:
                state['lanes'][key].update(state='done', review_disposition={'summary': 'accepted'})
            self.reg.register_pool_worker(key, ['review'], ['python'], 'operator')
            spec = self.f.make_spec('partition-' + str(i), 910 + i)
            path = self.f.out / ('template-' + str(i) + '.json')
            write(path, spec)
            self.settings['planner_pool']['helpers'].append(
                dict(scope=key, template=str(path), sha256=digest(path)))
        self.settings['planner_pool'].update(use_idle_capacity=True, max_active=24, reserve_workers=2)
        for _ in range(9): self.tick()
        self.assertEqual(len(self.reg.scheduling_status()['jobs']), 5)
        with self.reg.transaction() as state:
            self.assertEqual(_state(state)['planner_pool']['target'], 5)
            self.assertEqual(_state(state)['planner_pool']['active'], 5)

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

    def test_publication_helper_requires_unpublished_work(self):
        helper=self.settings['planner_pool']['helpers'][0]
        helper.update(kind='publication', review_inboxes=[str(self.f.out)])
        self.settings['planner_pool']['use_idle_capacity']=True
        self.tick(); self.assertFalse(self.reg.scheduling_status()['jobs'])
        write(self.f.out/'proposals-a.json',dict(items=[self.f.spec]))
        self.tick(); self.assertFalse(self.reg.scheduling_status()['jobs'])
        proposal=self.f.make_spec('unpublished',902)
        write(self.f.out/'proposals-a.json',dict(items=[proposal]))
        self.tick(); self.assertEqual(len(self.reg.scheduling_status()['jobs']),1)
        with self.reg.transaction() as s:
            instruction=_state(s)['planner_pool']['scopes']['enemies']['spec']['instruction']
        self.assertIn('merge_proposals',instruction)
        self.assertNotIn('never write the shared manifest',instruction)

    def test_publication_precedes_unstarted_discovery(self):
        spec=self.f.make_spec('review-helper',903)
        path=self.f.out/'review-template.json';write(path,spec)
        write(self.f.out/'proposals-a.json',dict(items=[self.f.make_spec('unpublished',904)]))
        self.settings['planner_pool']['helpers'].append(dict(scope='review',kind='publication',
            review_inboxes=[str(self.f.out)],template=str(path),sha256=digest(path)))
        self.tick()
        self.assertIn('review-helper-cycle-1',self.reg.status()['lanes'])
        self.assertNotIn('next-cycle-1',self.reg.status()['lanes'])

    def test_discovery_defers_while_its_proposals_await_review(self):
        self.settings['planner_pool']['helpers'][0]['defer_for_review']=[str(self.f.out)]
        write(self.f.out/'proposals-a.json',dict(items=[self.f.make_spec('unpublished',904)]))
        self.tick(); self.assertFalse(self.reg.scheduling_status()['jobs'])

    def test_publication_race_retries_without_losing_other_append(self):
        first=self.f.make_spec('first',901);second=self.f.make_spec('second',902)
        a=self.f.out/'first.json';b=self.f.out/'second.json'
        write(a,dict(items=[first]));write(b,dict(items=[second]))
        def concurrent_reader(number):
            merge_proposals(self.reg,self.f.manifest,b,lambda n:self.f.remote[n])
            return self.f.remote[number]
        with self.assertRaisesRegex(Rejected,'Manifest changed'):
            merge_proposals(self.reg,self.f.manifest,a,concurrent_reader)
        self.assertEqual(merge_proposals(self.reg,self.f.manifest,a,lambda n:self.f.remote[n]),['first'])
        self.assertEqual({s['id'] for s in json.loads(self.f.manifest.read_text())['items']},
                         {self.f.spec['id'],'first','second'})

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
