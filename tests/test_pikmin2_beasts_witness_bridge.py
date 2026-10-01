import copy
import unittest

from experimental.pikmin2_beasts_witness_bridge import checkpoint_witnesses
from experimental.pikmin2_beasts_checkpoint_reference import BeastsReferenceAdapter
from tests.test_pikmin2_beasts_checkpoint_reference import audit, party, context
from tests.test_pikmin2_beasts_generation import plan, suppressed
from tests.test_pikmin2_beasts_floor2_runtime import trace
from tests.test_pikmin2_beasts_party_snapshot import with_party


def native_trace():
    log=trace().replace('P2_BEASTS_READY','P2_BEASTS_GENERATION purple=19 flowers=2\nP2_BEASTS_READY',1)
    for index,generator in enumerate((62000,62001)):
        target=f'P2_VIOLET_CONVERT count=5\nP2_BEASTS_FLOWER_CONVERTED id={generator}'
        records=''.join(f'P2_VIOLET_WITNESS sequence={index*5+i+1} generator={generator} input=red\n' for i in range(5))
        log=log.replace(target,records+target)
    return with_party(log)


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.adapter=BeastsReferenceAdapter(audit(),'a'*64,{1:{},2:{},3:{}})
        self.first=self.adapter.initial('bridge',party(),1,{})
        self.second=self.adapter.apply(self.first,self.adapter.token(self.first),party(),1,{},[],context(19))

    def test_native_events_advance_and_replay_without_mutation(self):
        original=copy.deepcopy(self.second)
        result=checkpoint_witnesses(self.adapter,self.second,native_trace(),plan(19))
        self.assertFalse(result['native_ready']);self.assertFalse(result['native_handoff_authenticated'])
        self.assertEqual(len(result['events']),10)
        snapshot=result['party_snapshot']
        third=self.adapter.apply(self.second,result['token'],snapshot['squad'],snapshot['health'],{},result['events'],{})
        self.assertEqual(third['floor'],3)
        self.assertEqual(self.adapter.apply(third,result['token'],snapshot['squad'],snapshot['health'],{},result['events'],{}),third)
        self.assertEqual(self.second,original)
        with self.assertRaises(ValueError):self.adapter.launch_requirement(third)

    def test_wrong_context_party_floor_and_missing_native_evidence(self):
        changed=copy.deepcopy(self.second);changed['squad']=party(19)
        other=copy.deepcopy(self.second);other['context']=context(18)
        for state,log,readiness in ((self.first,native_trace(),plan(19)),(changed,native_trace(),plan(19)),
                                   (other,native_trace(),plan(19)),(self.second,trace(),plan(19)),
                                   (self.second,native_trace(),{'flowers':[]})):
            with self.subTest(state=state),self.assertRaises(ValueError):checkpoint_witnesses(self.adapter,state,log,readiness)

    def test_suppressed_generation_has_no_events(self):
        second=self.adapter.apply(self.first,self.adapter.token(self.first),party(),1,{},[],context(20))
        result=checkpoint_witnesses(self.adapter,second,with_party(suppressed(),20,0),plan(20))
        self.assertEqual(result['events'],[])
        third=self.adapter.apply(second,result['token'],party(),1,{},[],{})
        self.assertEqual(third['floor'],3)
