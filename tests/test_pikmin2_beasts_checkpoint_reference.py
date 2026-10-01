from copy import deepcopy
import unittest
import json
from experimental.pikmin2_beasts_checkpoint_reference import BeastsReferenceAdapter

def party(red=20,purple=0):return [dict(species='red',maturity=0) for _ in range(red)]+[dict(species='purple',maturity=1) for _ in range(purple)]
def audit():return dict(cave='forest_1',slots_per_flower=5,floors=[dict(floor=i,next_floor=i+1,geyser=False,clogged=False) for i in (1,2,3)])
FLOWERS=[f'forest_1:floor2:BlackPom:{i}' for i in range(2)]
def context(pop=0):return dict(global_plus_cave_purple=pop,spawned_flowers=FLOWERS if pop<20 else [])
def events():return [dict(id=f'conversion:{i}',flower=FLOWERS[i//5],input='red') for i in range(10)]

class BeastsCheckpointReferenceTests(unittest.TestCase):
    def test_history_json_roundtrip_and_tampering(self):
        second=self.floor2()
        third=self.adapter.apply(second,self.adapter.token(second),party(10,10),.5,second['receipts'],events(),{})
        restored=json.loads(json.dumps(third))
        self.assertEqual(self.adapter.validate(restored),third)
        for field,value in [('id','different'),('floor',1),('floor',True),('flower','unknown'),
                            ('flower',[]),('input','white'),('input',{}),('extra',1)]:
            bad=deepcopy(restored);bad['conversions']['conversion:0'][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):self.adapter.validate(bad)
        for value in (None,[],{},'record'):
            bad=deepcopy(restored);bad['conversions']['conversion:0']=value
            with self.subTest(record=value),self.assertRaises(ValueError):self.adapter.validate(bad)
        bad=deepcopy(restored);bad['conversions']['sixth']=dict(id='sixth',floor=2,flower=FLOWERS[0],input='red')
        with self.assertRaisesRegex(ValueError,'capacity'):self.adapter.validate(bad)
        bad=deepcopy(second);bad['conversions']=deepcopy(third['conversions'])
        with self.assertRaisesRegex(ValueError,'boundary'):self.adapter.validate(bad)
        for value in (None,[],42):
            with self.subTest(state=value),self.assertRaises(ValueError):self.adapter.validate(value)
            bad=deepcopy(second);bad['context']=value
            with self.subTest(context=value),self.assertRaises(ValueError):self.adapter.validate(bad)

    def test_failed_floor2_history_and_suppressed_spawn(self):
        second=self.floor2()
        failed=self.adapter.apply(second,self.adapter.token(second),[],0,second['receipts'],events(),{})
        self.assertEqual(self.adapter.validate(json.loads(json.dumps(failed))),failed)
        self.assertEqual(self.adapter.apply(failed,self.adapter.token(second),[],0,second['receipts'],events(),{}),failed)
        bad=deepcopy(failed);bad['context']=context(20);bad['budgets']={}
        with self.assertRaisesRegex(ValueError,'suppressed'):self.adapter.validate(bad)
    def setUp(self):
        self.adapter=BeastsReferenceAdapter(audit(),'a'*64,{1:{'treasure:floor1:key':50},2:{},3:{}})
        self.initial=self.adapter.initial('trip1',party(),1,{'old':480})
    def floor2(self,ctx=None):
        return self.adapter.apply(self.initial,self.adapter.token(self.initial),party(),.75,{'old':480,'treasure:floor1:key':50},[],context() if ctx is None else ctx)
    def test_descent_receipts_party_and_floor3_stop(self):
        second=self.floor2();original=deepcopy(second)
        third=self.adapter.apply(second,self.adapter.token(second),party(10,10),.5,second['receipts'],events(),{})
        self.assertEqual((third['floor'],third['revision'],third['status']),(3,2,'active'))
        self.assertEqual(len(third['squad']),20);self.assertEqual(third['receipts'],second['receipts'])
        self.assertEqual(second,original)
        with self.assertRaisesRegex(ValueError,'Floor3'):self.adapter.launch_requirement(third)
        self.assertFalse(self.adapter.launch_requirement(second)['native_ready'])
    def test_exact_replay_after_later_transition_and_conflict(self):
        second=self.floor2();third=self.adapter.apply(second,self.adapter.token(second),party(10,10),.5,second['receipts'],events(),{})
        replay=self.adapter.apply(third,self.adapter.token(self.initial),party(),.75,second['receipts'],[],context())
        self.assertEqual(replay,third)
        with self.assertRaisesRegex(ValueError,'Conflicting'):self.adapter.apply(third,self.adapter.token(self.initial),party(),.7,second['receipts'],[],context())
    def test_birth_gate_and_global_context(self):
        second=self.floor2(context(20));self.assertEqual(second['budgets'],{})
        with self.assertRaises(ValueError):self.adapter.apply(second,self.adapter.token(second),party(10,10),.5,second['receipts'],events(),{})
        bad=context(20);bad['spawned_flowers']=FLOWERS
        with self.assertRaises(ValueError):self.floor2(bad)
        with self.assertRaises(ValueError):self.floor2({})
        self.assertEqual(sum(self.floor2(context(19))['budgets'].values()),10)
    def test_per_instance_cap_duplicate_and_unwitnessed_growth(self):
        second=self.floor2()
        bad=events();bad[5]['flower']=FLOWERS[0]
        for witness,squad in ((bad,party(10,10)),(events()+[events()[0]],party(10,10)),([],party(10,10)),([],party(21))):
            with self.subTest(witness=witness),self.assertRaises(ValueError):self.adapter.apply(second,self.adapter.token(second),squad,.5,second['receipts'],witness,{})
    def test_same_color_refund_requires_actual_available_purple(self):
        second=self.floor2();same=[dict(id='same',flower=FLOWERS[0],input='purple')]
        with self.assertRaises(ValueError):self.adapter.apply(second,self.adapter.token(second),party(),.5,second['receipts'],same,{})
        witness=events()+same
        third=self.adapter.apply(second,self.adapter.token(second),party(10,10),.5,second['receipts'],witness,{})
        self.assertEqual(len(third['conversions']),11)
    def test_death_and_knockout_are_terminal_no_revival(self):
        for squad,health in (([],.5),(party(),0)):
            failed=self.adapter.apply(self.initial,self.adapter.token(self.initial),squad,health,self.initial['receipts'],[],{})
            self.assertEqual(failed['status'],'failed');self.assertEqual(failed['squad'],[])
            self.assertEqual(self.adapter.apply(failed,self.adapter.token(self.initial),squad,health,self.initial['receipts'],[],{}),failed)
            with self.assertRaises(ValueError):self.adapter.apply(failed,self.adapter.token(failed),party(),1,failed['receipts'],[],{})
            with self.assertRaises(ValueError):self.adapter.launch_requirement(failed)
    def test_receipt_regression_and_new_floor2_credit_rejected(self):
        second=self.floor2()
        for receipt in ({},{'old':481},{**second['receipts'],'fake':10}):
            with self.assertRaises(ValueError):self.adapter.apply(second,self.adapter.token(second),party(),.5,receipt,[],{})
    def test_profile_stale_token_invalid_health_and_casualties(self):
        second=self.floor2()
        with self.assertRaises(ValueError):self.adapter.apply(second,'stale',party(),.5,second['receipts'],[],{})
        other=BeastsReferenceAdapter(audit(),'b'*64,{1:{},2:{},3:{}})
        with self.assertRaises(ValueError):other.validate(second)
        for health in (float('nan'),float('inf'),2,-1):
            with self.assertRaises(ValueError):self.adapter.apply(second,self.adapter.token(second),party(),health,second['receipts'],[],{})
        third=self.adapter.apply(second,self.adapter.token(second),party(9,9),.5,second['receipts'],events(),{})
        self.assertEqual(len(third['squad']),18)
