import copy
import unittest
from experimental.pikmin2_beasts_floor3_donut_runtime import validate,validate_plan,INSTANCE,LEDGER,RECEIPT


def plan():
    return dict(policy='P2_BEASTS_FLOOR3_HAUL_PLAN_1',cave='forest_1',floor=3,assembly_sha256='a',treasure_package_sha256='b',
        cargo=dict(instance=INSTANCE,model='donutswhite',source_row=0,source_slot=2,source_unit='room_block1_3_hiba_tsuchi',
            position=[175,20.5,-55],value=230,weight=15,slots=25,model_sha256='c'),pod=[-85,0,-280],
        route=dict(waypoint_ids=[6,4,3,0]),campaign_reward_authorized=False)


def evidence(replay=False):
    lines=['P2_CAVE_READY floor=3 survivors=20 health=1',f'P2_BEASTS_ENTRY_READY floor=3 token={"1"*64} descent=disabled',
        'P2_FLOOR3_DONUT_PHYSICS bottom_radius=20 cylinder_height=14 center_size=20 config_scale=1 carry_height=14',
        f'P2_FLOOR3_DONUT_READY token={"1"*64} generator=63001 value=230 weight=15 slots=25 initial_pokos={230 if replay else 0} x=175.000 y=20.500 z=-55.000',
        'P2_FLOOR3_DONUT_ASSIGNED carriers=20 native_transport=1 positions_unchanged=1']
    lines += [f'P2_FLOOR3_DONUT_POINT x={x} y={y} z={z} attached=20 ground=0' for x,y,z in [(175,20.5,-55),(120,20,15),(50,10,50),(-50,8,80),(-85,8,-120),(-85,8,-230)]]
    lines += ['P2_FLOOR3_DONUT_ROUTE west','P2_FLOOR3_DONUT_ROUTE pod_approach']
    lines += [f'[Pikipelago] P2_POD_RECEIPT id=treasure:{INSTANCE} value=230 new={new} pokos=230 seeds=0' for new in (0 if replay else 1,0)]
    lines += ['P2_FLOOR3_DONUT_DELIVERED max_attached=20 blockroom_route=1 duplicate_credit=0 reopened_receipts=1 pokos=230 repairs_unchanged=1',
        'PASS P2_FLOOR3_DONUT cargo=1 value=230 seeds=0 repairs_unchanged=1 descent=disabled']
    return '\n'.join(lines)+'\n'


class DonutRuntimeTests(unittest.TestCase):
    def test_exact_source_slot_settings_and_model(self):
        self.assertEqual(validate_plan(plan(),'a','b','c')['weight'],15)
        for key,value in [('instance','other'),('model','dia_c_green'),('source_row',1),('source_slot',0),('position',[175,0,-55]),('value',150),('weight',12),('slots',20),('model_sha256','changed')]:
            p=copy.deepcopy(plan());p['cargo'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_plan(p,'a','b','c')
        for args in [('x','b','c'),('a','x','c'),('a','b','x')]:
            with self.subTest(args=args),self.assertRaises(ValueError):validate_plan(plan(),*args)
        p=plan();p['route']['waypoint_ids']=[9,8,7,0]
        with self.assertRaises(ValueError):validate_plan(p,'a','b','c')

    def test_first_and_replay_with_quantified_donor_physics(self):
        for replay in (False,True):
            result=validate(evidence(replay),'1'*64,RECEIPT,LEDGER,replay=replay)
            self.assertEqual(result['value'],230);self.assertEqual(result['donor_physics']['bottom_radius'],20)
            self.assertEqual(result['donor_physics']['cylinder_height'],14)
        with self.assertRaises(ValueError):validate(evidence(True),'1'*64,RECEIPT,LEDGER)
        with self.assertRaises(ValueError):validate(evidence(),'1'*64,RECEIPT,LEDGER.replace(b'230',b'460'))

    def test_bad_trace_receipt_and_measurements(self):
        for old,new in [('floor=3','floor=2'),('value=230','value=150'),('new=0','new=1'),('seeds=0','seeds=1'),
            ('max_attached=20','max_attached=14'),('x=175 y=20.5','x=400 y=20.5'),('z=-230','z=-150'),
            ('P2_FLOOR3_DONUT_ROUTE west',''),('bottom_radius=20','bottom_radius=nan'),('config_scale=1','config_scale=0')]:
            with self.subTest(old=old),self.assertRaises(ValueError):validate(evidence().replace(old,new),'1'*64,RECEIPT,LEDGER)
        with self.assertRaises(ValueError):validate(evidence()+'P2_CAVE_TRANSFER\n','1'*64,RECEIPT,LEDGER)
