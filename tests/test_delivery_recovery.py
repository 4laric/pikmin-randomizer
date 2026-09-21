import copy
import unittest
from workflow.delivery_recovery import allocations


class DeliveryRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.state=dict(lanes={'producer':dict(state='done',issue=1,root={'head':'a'}),
            'consumer':dict(state='blocked',issue=2,dependencies=['source'],outcome={'evidence':{'path':'x','sha256':'y'}})},
            throughput={'workstreams':{'s':{'owner_lane':'owner','lanes':['consumer']}}},
            delivery_contracts={'c':dict(id='c',consumer='consumer',producer='producer',owner='owner',
                kind='source_integration',requirement='source',acceptance_check='compile actual consumer')})
        self.helpers=[{'scope':'one'},{'scope':'two'}]

    def test_once_per_semantic_source_group_and_changed_source_rearms(self):
        first=allocations(self.state,self.helpers,{})
        self.assertEqual(len(first),1)
        row=first['one']; self.assertEqual(row['request']['lanes'],['consumer','producer'])
        self.state['throughput_runtime']={'autofill':{'prerequisite_recovery':{row['key']:{}}}}
        self.state['lanes']['producer']['generation']=25
        self.assertFalse(allocations(self.state,self.helpers,{}))
        self.state['lanes']['producer']['root']['head']='b'
        self.assertEqual(len(allocations(self.state,self.helpers,{})),1)

    def test_active_owners_and_reserved_work_and_published_proposal_protected(self):
        for status in ('running','ready','integrating','handoff_ready'):
            s=copy.deepcopy(self.state);s['lanes']['producer']['state']=status
            self.assertFalse(allocations(s,self.helpers,{}))
        self.assertFalse(allocations(self.state,self.helpers,{'two':{'recovery_targets':['consumer']}}))
        self.state['support_actions']={'x':{'key':'consumer','action':'proposal'}}
        self.assertFalse(allocations(self.state,self.helpers,{}))

    def test_multiple_consumers_of_same_producer_have_one_assignment(self):
        self.state['lanes']['consumer2']=copy.deepcopy(self.state['lanes']['consumer'])
        self.state['throughput']['workstreams']['s']['lanes'].append('consumer2')
        self.state['delivery_contracts']['d']=dict(self.state['delivery_contracts']['c'],id='d',consumer='consumer2')
        result=allocations(self.state,self.helpers,{})
        self.assertEqual(len(result),1)
        self.assertEqual(result['one']['request']['lanes'],['consumer','consumer2','producer'])

    def test_blocked_watch_proposal_does_not_hide_missing_source_delivery(self):
        self.state['lanes']['watch']={'state':'blocked','issue':3,'dependencies':[]}
        self.state['support_actions']={'x':{'key':'consumer','action':'proposal','details':{'proposal_id':'watch-v1'}}}
        self.state['throughput_runtime']={'autofill':{'items':{'watch-v1':{'lane':'watch'}}}}
        self.assertEqual(len(allocations(self.state,self.helpers,{})),1)

    def test_prepare_upstream_source_before_blocked_downstream_producer(self):
        self.state['lanes']['producer'].update(state='blocked',dependencies=['upstream'],outcome={'evidence':{'path':'z','sha256':'q'}})
        self.state['lanes']['upstream']={'state':'done','issue':3}
        self.state['throughput']['workstreams']['s']['lanes'].append('producer')
        self.state['delivery_contracts']['up']=dict(self.state['delivery_contracts']['c'],id='up',
            consumer='producer',producer='upstream',requirement='upstream')
        result=allocations(self.state,self.helpers,{})
        self.assertEqual(len(result),1)
        self.assertEqual(result['one']['request']['delivery_group']['producer'],'upstream')
