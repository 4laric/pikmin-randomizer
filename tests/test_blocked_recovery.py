import copy
import unittest
from workflow.blocked_recovery import allocations


class BlockedRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.lane=dict(state='blocked',issue=1,progress_at=1,started_at=1,dependencies=[],
            root={'head':'a'*40},outcome=dict(outcome='blocked',evidence=dict(path='report',sha256='b'*64)))
        self.state=dict(lanes={str(i):dict(copy.deepcopy(self.lane),issue=i) for i in range(1,4)})
        self.helpers=[dict(scope=str(i)) for i in range(3)]

    def test_distinct_targets_reuse_spare_partitions(self):
        result=allocations(self.state,self.helpers,{},2000)
        self.assertEqual(len(result),3)
        self.assertEqual(len({x['request']['lanes'][0] for x in result.values()}),3)

    def test_unchanged_input_not_repeated_heartbeat_does_not_rearm(self):
        first=allocations(self.state,self.helpers,{},2000)
        self.state['throughput_runtime']={'autofill':{'prerequisite_recovery':{v['key']:{} for v in first.values()}}}
        self.state['lanes']['1']['heartbeat_at']=9999
        self.assertFalse(allocations(self.state,self.helpers,{},10000))
        self.state['lanes']['1']['root']['head']='c'*40
        self.assertEqual(len(allocations(self.state,self.helpers,{},10000)),1)

    def test_new_evidence_is_not_a_new_input_and_legacy_keys_still_count(self):
        from workflow.control import fingerprint
        from workflow.planner_demand import inputs
        first=allocations(self.state,self.helpers,{},2000)
        self.state['throughput_runtime']={'autofill':{'prerequisite_recovery':{v['key']:{} for v in first.values()}}}
        for lane in self.state['lanes'].values():lane['outcome']['evidence']=dict(path='report-2',sha256='c'*64)
        self.assertFalse(allocations(self.state,self.helpers,{},10000))
        signal=inputs(self.state,[],['1'])
        legacy=fingerprint(['blocked-recovery-v1','1',fingerprint([signal,self.state['lanes']['1']['outcome']['evidence']])])
        self.state['throughput_runtime']['autofill']['prerequisite_recovery']={legacy:{}}
        self.assertNotIn('1',[x['request']['lanes'][0] for x in allocations(self.state,self.helpers,{},10000).values()])

    def test_active_assignments_and_real_producers_are_protected(self):
        records={'0':dict(recovery_targets=['1'])}
        self.state['lanes']['2']['dependencies']=['#3']
        self.state['lanes']['3']['state']='running'
        self.assertFalse(allocations(self.state,self.helpers,records,2000))

    def test_fresh_or_unproven_blockage_does_not_launch(self):
        self.state['lanes']['1']['progress_at']=1990
        self.state['lanes']['2']['outcome']={}
        self.state['lanes']['3']['state']='done'
        self.assertFalse(allocations(self.state,self.helpers,{},2000))

    def test_failed_recovery_gets_one_proposal_followup_only(self):
        first=allocations(self.state,self.helpers,{},2000)
        attempts={v['key']:dict(lane='planning-old') for v in first.values()}
        self.state['lanes']['planning-old']=dict(state='done',outcome=dict(outcome='blocked',evidence={'sha256':'x'}))
        self.state['throughput_runtime']={'autofill':{'prerequisite_recovery':attempts}}
        second=allocations(self.state,self.helpers,{},3000)
        self.assertEqual(len(second),3)
        self.assertTrue(all(x['request'].get('previous_recovery') for x in second.values()))
        attempts.update({v['key']:dict(lane='planning-old') for v in second.values()})
        self.assertFalse(allocations(self.state,self.helpers,{},4000))

    def test_active_support_target_is_not_duplicated(self):
        self.assertFalse(allocations(self.state,self.helpers,{'0':dict(support_targets=[{'lane':str(i)} for i in (1,2,3)])},2000))

    def test_review_ready_referral_without_action_is_not_a_resolved_recovery(self):
        first=allocations(self.state,self.helpers,{},2000)
        self.state['lanes']['planning-old']=dict(state='done',outcome=dict(outcome='review-ready',evidence={'sha256':'x'}))
        self.state['throughput_runtime']={'autofill':{'prerequisite_recovery':{v['key']:dict(lane='planning-old') for v in first.values()}}}
        self.assertEqual(len(allocations(self.state,self.helpers,{},3000)),3)
        self.state['support_actions']={'a':dict(reviewer='planning-old',key='1',action='proposal')}
        self.assertEqual(len(allocations(self.state,self.helpers,{},3000)),2)

    def test_named_shard_recovery_waits_for_own_partition(self):
        self.state={'lanes':{'shard-enemies-3-damagumo56-observer':copy.deepcopy(self.lane)}}
        helpers=[{'scope':'enemies-5'},{'scope':'enemies-3'}]
        result=allocations(self.state,helpers,{},2000)
        self.assertEqual(list(result),['enemies-3'])
        self.assertFalse(allocations(self.state,helpers,{'enemies-3':{'started_at':1}},2000))
