import copy
import unittest

from tests import test_planner_pool as fixtures
from workflow.autofill import _planner_tick
from workflow.handoff import digest, Rejected
from workflow.planner_pool import merge_proposals
from workflow.prerequisite_queue import collect, dispatched, resolve, links, recovery_demand
from workflow.runner import write


class PrerequisiteQueueTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.PlannerPoolTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.reg, self.settings = self.f.reg, self.f.settings
        self.f.tick()
        report = self.f.f.out/'no-work.md'; report.write_text('No-work: missing provider contract, source owner must implement it.')
        self.evidence = dict(path=str(report),sha256=digest(report))
        self.reg.finish('next-cycle-1',1,'review-ready','No-work: unowned prerequisite',self.evidence)
        self.f.tick()
        self.f.f.planner()
        self.f.controller.config['lanes']['planner'] = dict(self.f.controller.config['lanes']['planner'],
            output=str(self.f.f.out/'coordinator'))
        self.settings['planner_pool']['helpers'][0]['defer_for_review'] = [str(self.f.f.out)]

    def live_coordinator(self):
        with self.reg.transaction() as s:
            s['lanes']['planner'].update(state='running',process={'health':'alive'})

    def test_linked_blocked_chain_recovers_without_no_work_or_open_request(self):
        helper=dict(self.settings['planner_pool']['helpers'][0],prerequisite_lanes=['owner'])
        with self.reg.transaction() as s:
            lane=s['lanes']['owner'];lane.update(state='blocked',progress_at=1,started_at=1,
                outcome=dict(outcome='blocked',evidence=self.evidence),dependencies=['missing engine anchor'])
            s['throughput_runtime']['autofill']['prerequisite_requests']={}
            recovery=recovery_demand(s,helper,2000)
            self.assertEqual(recovery['request']['status'],'stranded')
            other=recovery_demand(s,dict(helper,scope='another-scope'),2000)
            self.assertEqual(recovery['key'],other['key'])
            s['throughput_runtime']['autofill']['prerequisite_recovery']={recovery['key']:{}}
            self.assertIsNone(recovery_demand(s,helper,9000))
            lane['dependencies']=['new concrete failure']
            self.assertIsNotNone(recovery_demand(s,helper,9000))
            lane['state']='running'
            self.assertIsNone(recovery_demand(s,helper,9000))

    def test_cross_partition_recovery_runs_despite_no_work_cooldown(self):
        self.settings['planner_pool']['cross_partition_recovery']=True
        self.settings['planner_pool']['helpers'][0].pop('defer_for_review',None)
        with self.reg.transaction() as s:
            s['lanes']['owner'].update(state='blocked',progress_at=1,started_at=1,
                outcome=dict(outcome='blocked',evidence=self.evidence),dependencies=['unowned missing input'])
            s['throughput_runtime']['autofill']['planner_pool']['scopes']['enemies']['completed_at']=self.reg.clock()
        self.f.f.now+=301
        self.settings['planner_pool']['prerequisite_recovery_seconds']=300
        self.f.tick()
        row=self.reg.snapshot()['throughput_runtime']['autofill']['planner_pool']['scopes']['enemies']
        self.assertEqual(row['recovery_targets'],['owner'])
        self.assertIn('PREREQUISITE RECOVERY',row['spec']['instruction'])
        self.assertIn(row['spec']['lane']['lane'],self.reg.snapshot()['lanes'])

    def request(self):
        return collect(self.reg,self.settings)[0]

    def test_recovery_admits_real_helper_once_after_coordinator_exhaustion(self):
        request = self.request()
        with self.reg.transaction() as s:
            s['throughput_runtime']['autofill']['prerequisite_requests'][request['id']]['status'] = 'exhausted'
        self.f.f.now += 901
        self.f.tick()
        with self.reg.transaction() as s:
            data = s['throughput_runtime']['autofill']
            record = data['planner_pool']['scopes']['enemies']
            self.assertIn('PREREQUISITE RECOVERY', record['spec']['instruction'])
            self.assertEqual(len(data['prerequisite_recovery']), 1)
            self.assertIn(record['spec']['lane']['lane'], s['lanes'])
            self.assertIsNone(recovery_demand(s, self.settings['planner_pool']['helpers'][0], self.reg.clock()))
        self.f.tick()
        self.assertEqual(len(self.reg.scheduling_status()['jobs']), 2)

    def test_new_report_at_same_inputs_keeps_the_request_its_cap_and_one_needs_human(self):
        request = self.request()
        path = self.f.f.out/'no-work-2.md'; path.write_text('No-work again: the same unowned provider contract.')
        again = dict(path=str(path), sha256=digest(path))
        with self.reg.transaction() as s:
            data = s['throughput_runtime']['autofill']
            data['planner_pool']['scopes'][request['scope']]['no_work']['report'] = again
            data['prerequisite_requests'][request['id']].update(status='dispatched', launches=['one', 'two'])
        self.assertEqual(collect(self.reg, self.settings), [])
        self.assertEqual(collect(self.reg, self.settings), [])
        state = self.reg.snapshot(); data = state['throughput_runtime']['autofill']
        self.assertEqual(list(data['prerequisite_requests']), [request['id']])
        row = data['prerequisite_requests'][request['id']]
        self.assertEqual((row['status'], row['report']), ('exhausted', again))
        self.assertIn('operator must link a producer', row['needs_human']['reason'])
        self.assertEqual(sum(e['kind'] == 'prerequisite_needs_human' for e in state['events']), 1)

    def test_recovery_waits_for_pending_age_and_never_races_dispatched_coordinator(self):
        request = self.request(); helper = self.settings['planner_pool']['helpers'][0]
        with self.reg.transaction() as s:
            self.assertIsNone(recovery_demand(s, helper, self.reg.clock()))
            self.assertIsNotNone(recovery_demand(s, helper, self.reg.clock()+901))
            s['throughput_runtime']['autofill']['prerequisite_requests'][request['id']]['status'] = 'dispatched'
            self.assertIsNone(recovery_demand(s, helper, self.reg.clock()+901))

    def test_recovery_deduplicates_semantic_inputs_not_report_or_heartbeat(self):
        request = self.request(); helper = self.settings['planner_pool']['helpers'][0]
        with self.reg.transaction() as s:
            data = s['throughput_runtime']['autofill']
            r = data['prerequisite_requests'][request['id']]; r['status'] = 'exhausted'
            recovery = recovery_demand(s, helper, self.reg.clock())
            data['prerequisite_recovery'] = {recovery['key']: {'lane':'past-recovery'}}
            r['report'] = {'path':'another-report','sha256':'a'*64}
            s['lanes']['owner']['heartbeat'] = self.reg.clock()+1000
            self.assertIsNone(recovery_demand(s, helper, self.reg.clock()+9000))
            s['lanes']['owner']['root']['head'] = 'f'*40
            self.assertIsNotNone(recovery_demand(s, helper, self.reg.clock()+9000))

    def test_recovery_preserves_live_producer_wait_but_handles_stranded_owner(self):
        request = self.request(); helper = dict(self.settings['planner_pool']['helpers'][0], prerequisite_lanes=['owner'])
        with self.reg.transaction() as s:
            s['throughput_runtime']['autofill']['prerequisite_requests'][request['id']]['status'] = 'exhausted'
            self.assertIsNone(recovery_demand(s, helper, self.reg.clock()))
            s['lanes']['owner']['state'] = 'blocked'
            self.assertIsNotNone(recovery_demand(s, helper, self.reg.clock()))

    def resolve(self, request, lanes, outcome='linked'):
        return resolve(self.reg,'planner',1,request['id'],outcome,lanes,
                       'Verified prerequisite disposition',self.evidence)

    def test_detects_deduplicates_and_wakes_without_any_proposal(self):
        first = self.request(); self.assertEqual(self.request()['id'],first['id'])
        self.assertTrue(_planner_tick(self.f.controller,self.settings,'manifest'))
        launches = list(self.reg.control_status()['launches'].values())
        self.assertEqual(len(launches),1)
        self.assertIn('PREREQUISITE PROMOTION EXCEPTION',launches[0]['instruction'])
        self.assertEqual(launches[0]['prerequisite_request_ids'],[first['id']])
        self.assertFalse(collect(self.reg,self.settings))

    def test_new_resolution_contract_bypasses_old_turn_cooldown(self):
        self.request()
        with self.reg.transaction() as s:
            s['throughput_runtime']['autofill']['last_planner_request'] = dict(
                at=self.reg.clock(), id='old-contract', status='planned')
        self.assertTrue(_planner_tick(self.f.controller,self.settings,'manifest'))
        with self.reg.transaction() as s:
            self.assertEqual(s['throughput_runtime']['autofill']['last_planner_request']['resolution_version'],3)

    def test_published_job_links_and_drives_completion_wakeup(self):
        request=self.request(); self.live_coordinator()
        spec=self.f.f.make_spec('provider-contract',990)
        path=self.f.f.out/'proposals-provider.json';write(path,{'items':[spec]})
        merge_proposals(self.reg,self.f.f.manifest,path,lambda n:self.f.f.remote[n])
        self.resolve(request,['provider-contract'])
        # Replay is idempotent and requires no mutable controller config edits.
        self.resolve(request,['provider-contract'])
        self.f.f.now+=4000;self.f.tick()
        with self.reg.transaction() as s:
            self.assertEqual(links(s,self.settings['planner_pool']['helpers'][0]),['provider-contract'])
            self.assertIn('enemies',s['throughput_runtime']['autofill']['planner_pool']['sleeping_scopes'])
            s['lanes']['provider-contract']=dict(s['lanes']['owner'],lane='provider-contract',issue=990,
                state='done',review_disposition={'summary':'Contract accepted'})
        self.f.tick()
        self.assertEqual(len(self.reg.scheduling_status()['jobs']),2)

    def test_reuses_existing_producer_and_skips_already_assigned_gaps(self):
        request=self.request();self.live_coordinator();self.resolve(request,['owner'])
        self.assertFalse(collect(self.reg,self.settings))

    def test_blocked_producer_link_reopens_once_without_waking_healthy_work(self):
        request=self.request(); self.live_coordinator(); self.resolve(request,['owner'])
        self.assertFalse(collect(self.reg,self.settings))
        with self.reg.transaction() as s:
            s['lanes']['owner'].update(state='blocked', dependencies=['#missing'])
        reopened=self.request()
        self.assertNotEqual(reopened['id'],request['id'])
        self.assertEqual(reopened['stranded_producers'],['owner'])
        self.assertIn('owner',reopened['lanes'])
        self.assertEqual(self.request()['id'],reopened['id'])
        with self.assertRaisesRegex(Rejected,'circular wait'):
            self.resolve(reopened,['owner'])
        with self.reg.transaction() as s:
            s['lanes']['owner']['state']='running'
        self.assertFalse(collect(self.reg,self.settings))

    def test_completed_only_links_are_rejected_without_mutation(self):
        request=self.request(); self.live_coordinator()
        with self.reg.transaction() as s:
            s['lanes']['owner'].update(state='done', integration={'root_commit':'a'*40})
        with self.assertRaisesRegex(Rejected, 'Completed producers'):
            self.resolve(request, ['owner'])
        with self.reg.transaction() as s:
            self.assertEqual(s['throughput_runtime']['autofill']['prerequisite_requests'][request['id']]['status'], 'pending')

    def test_internal_referral_cannot_dismiss_blocked_consumer(self):
        request=self.request(); self.live_coordinator()
        with self.reg.transaction() as s:
            s['lanes']['one']['state']='blocked'
            s['throughput_runtime']['autofill']['prerequisite_requests'][request['id']]['lanes']=['one']
        with self.assertRaisesRegex(Rejected, 'Blocked consumers require'):
            self.resolve(request, [], 'no_action')
        result=resolve(self.reg,'planner',1,request['id'],'no_action',[],
            'Legal source asset must be supplied by user',self.evidence,
            external_input={'kind':'user_asset','owner':'user','detail':'Legal local source ISO bytes missing'})
        self.assertEqual(result['status'],'no_action')

    def test_old_resolution_is_reaudited_once(self):
        request=self.request(); self.live_coordinator()
        with self.reg.transaction() as s:
            requests=s['throughput_runtime']['autofill']['prerequisite_requests']
            old=requests.pop(request['id']); old.update(id='legacy', status='linked')
            old.pop('resolution_version'); requests['legacy']=old
        fresh=self.request()
        self.assertEqual(fresh['resolution_version'],3)
        self.assertEqual(self.request()['id'],fresh['id'])
        self.resolve(fresh, [], 'no_action')
        self.assertFalse(collect(self.reg,self.settings))

    def test_unpublished_or_planner_targets_and_stale_generation_rejected(self):
        request=self.request();self.live_coordinator()
        for key in ['not-published','planning-fake','planner']:
            with self.assertRaises(Rejected):self.resolve(request,[key])
        with self.assertRaises(Rejected):
            resolve(self.reg,'planner',2,request['id'],'linked',['owner'],'why',self.evidence)

    def test_changed_report_cannot_be_dispositioned(self):
        request=self.request();self.live_coordinator()
        with self.reg.transaction() as s:
            s['throughput_runtime']['autofill']['planner_pool']['scopes']['enemies']['no_work']['report']={'path':'changed','sha256':'b'*64}
        with self.assertRaisesRegex(Rejected,'report changed'):self.resolve(request,['owner'])

    def test_no_action_needs_evidence_and_reopens_on_changed_inputs(self):
        request=self.request();self.live_coordinator();self.resolve(request,[],'no_action')
        self.assertFalse(collect(self.reg,self.settings))
        with self.reg.transaction() as s:s['lanes']['owner']['root']['head']='b'*40
        self.assertNotEqual(self.request()['id'],request['id'])

    def test_unanswered_requests_retry_twice_then_remain_visible(self):
        request=self.request()
        for i in range(2):
            key='attempt-'+str(i)
            with self.reg.transaction() as s:
                self.reg.control(s)['launches'][key]={'status':'exited'}
            dispatched(self.reg,[request],key)
            pending=collect(self.reg,self.settings)
            self.assertEqual(bool(pending),i==0)
        with self.reg.transaction() as s:
            self.assertEqual(s['throughput_runtime']['autofill']['prerequisite_requests'][request['id']]['status'],'exhausted')
            s['lanes']['owner']['progress_at']=99999
        self.assertFalse(collect(self.reg,self.settings))
        with self.reg.transaction() as s:
            s['lanes']['owner']['root']['head']='c'*40
        refreshed=self.request()
        self.assertNotEqual(refreshed['id'],request['id'])
        self.assertEqual(refreshed['launches'],[])

    def test_report_hash_drift_does_not_create_requests(self):
        with self.reg.transaction() as s:
            s['throughput_runtime']['autofill']['planner_pool']['scopes']['enemies']['no_work']['report']['sha256']='0'*64
        self.assertFalse(collect(self.reg,self.settings))
