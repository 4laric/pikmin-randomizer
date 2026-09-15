import copy
import unittest
from experimental.pikmin2_beasts_floor3_haul_runtime import validate,validate_plan,INSTANCE,LEDGER,RECEIPT


def plan():
    return dict(policy='P2_BEASTS_FLOOR3_HAUL_PLAN_1',cave='forest_1',floor=3,assembly_sha256='a',treasure_package_sha256='b',
        cargo=dict(instance=INSTANCE,model='dia_c_green',source_row=1,source_slot=0,source_unit='room_north_1_hiba_tsuchi',
            position=[-85,0,-960],value=150,weight=12,slots=20,model_sha256='c'),pod=[-85,0,-280],
        route=dict(waypoint_ids=[9,8,7,0]),campaign_reward_authorized=False)


def evidence(replay=False):
    lines=['P2_CAVE_READY floor=3 survivors=20 health=1',f'P2_BEASTS_ENTRY_READY floor=3 token={"c"*64} descent=disabled',
        f'P2_FLOOR3_HAUL_READY token={"c"*64} generator=63000 value=150 weight=12 slots=20 initial_pokos={150 if replay else 0} x=-85.000 y=0.000 z=-960.000',
        'P2_FLOOR3_HAUL_ASSIGNED carriers=20 native_transport=1 positions_unchanged=1']
    lines += [f'P2_FLOOR3_HAUL_POINT x=-85 y=8 z={z} attached=20 ground=0' for z in (-960,-800,-650,-500,-400,-330)]
    lines += ['P2_FLOOR3_HAUL_SEAM north','P2_FLOOR3_HAUL_SEAM south']
    lines += [f'[Pikipelago] P2_POD_RECEIPT id=treasure:{INSTANCE} value=150 new={new} pokos=150 seeds=0' for new in (0 if replay else 1,0)]
    lines += ['P2_FLOOR3_HAUL_DELIVERED max_attached=20 seams=2 duplicate_credit=0 reopened_receipts=1 pokos=150 repairs_unchanged=1',
        'PASS P2_FLOOR3_HAUL cargo=1 value=150 seeds=0 repairs_unchanged=1 descent=disabled']
    return '\n'.join(lines)+'\n'


class HaulRuntimeTests(unittest.TestCase):
    def test_source_identity_and_provenance(self):
        self.assertEqual(validate_plan(plan(),'a','b','c')['weight'],12)
        for key,value in [('instance','other'),('source_row',0),('source_slot',1),('position',[0,0,0]),('value',151),('weight',5),('slots',25),('model_sha256','changed')]:
            p=copy.deepcopy(plan());p['cargo'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_plan(p,'a','b','c')
        for args in [('x','b','c'),('a','x','c'),('a','b','x')]:
            with self.subTest(args=args),self.assertRaises(ValueError):validate_plan(plan(),*args)
        p=plan();p['route']['waypoint_ids']=[0,7,8,9]
        with self.assertRaises(ValueError):validate_plan(p,'a','b','c')

    def test_actual_and_reopened_receipt_contract(self):
        for replay in (False,True):
            self.assertEqual(validate(evidence(replay),'c'*64,RECEIPT,LEDGER,replay=replay)['value'],150)
        with self.assertRaises(ValueError):validate(evidence(True),'c'*64,RECEIPT,LEDGER)
        for raw in (LEDGER+b'extra 150\n',LEDGER.replace(b'150',b'300'),b''):
            with self.subTest(raw=raw),self.assertRaises(ValueError):validate(evidence(),'c'*64,RECEIPT,raw)
        with self.assertRaises(ValueError):validate(evidence(),'c'*64,RECEIPT.replace(b'count=1',b'count=2'),LEDGER)

    def test_native_trace_and_credit_mutations(self):
        replacements=[('floor=3','floor=2'),('value=150','value=151'),('new=0','new=1'),('seeds=0','seeds=1'),
            ('max_attached=20','max_attached=11'),('x=-85 y=8','x=100 y=8'),('z=-960 attached','z=-500 attached'),
            ('P2_FLOOR3_HAUL_SEAM north',''),('reopened_receipts=1','reopened_receipts=2'),('z=-330','z=-350')]
        for old,new in replacements:
            with self.subTest(old=old),self.assertRaises(ValueError):validate(evidence().replace(old,new),'c'*64,RECEIPT,LEDGER)
        with self.assertRaises(ValueError):validate(evidence()+'P2_CAVE_TRANSFER\n','c'*64,RECEIPT,LEDGER)
