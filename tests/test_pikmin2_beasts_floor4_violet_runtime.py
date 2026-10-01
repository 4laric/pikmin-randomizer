import copy
import unittest
from experimental.pikmin2_beasts_floor4_violet_runtime import validate,validate_plan,audit_approach,APPROACH,IDENTITY,POSITION


def plan(population=20):
    return dict(policy='P2_BEASTS_FLOOR4_VIOLET_PLAN_1',cave='forest_1',floor=4,assembly_sha256='c'*64,slots_per_flower=5,
        flower=dict(identity=IDENTITY,generator_id=62002,instance=2,unit='room_north3_1_tsuchi',source_slot=0,source=dict(type=8),position=POSITION),
        generation_context=dict(global_plus_cave_purple=population,spawned_generators=[62002],conversion_budgets={IDENTITY:5},suppression_applies=False,native_global_population_verified=False))


def evidence():
    lines=['P2_CAVE_READY floor=4 survivors=20 health=1',f'P2_BEASTS_ENTRY_READY floor=4 token={"a"*64} descent=disabled',
        'P2_FLOOR4_VIOLET_FLOWER generator=62002 x=295 y=0 z=-875 live_x=295 live_y=0 live_z=-875 ground=0',
        f'P2_FLOOR4_VIOLET_BOUNDARY token={"a"*64} descent=disabled','P2_BEASTS_READY reds=20 flowers=1 cargo=0']
    lines += [f'P2_FLOOR4_VIOLET_POINT index={i} x={x} y=0 z={z} ground=0' for i,(x,z) in enumerate(APPROACH)]
    lines += [f'P2_FLOOR4_VIOLET_THROW original={i} generator=62002' for i in range(5)]
    lines += [f'P2_VIOLET_WITNESS sequence={i+1} generator=62002 input=red' for i in range(5)]
    lines += ['P2_VIOLET_CONVERT count=5','P2_FLOOR4_VIOLET_SPROUTS reds=15 purple=0 sprouts=5','P2_BEASTS_CAPTAIN_PLUCK purple=1','P2_BEASTS_PARTY health=1 count=20']
    lines += [f'P2_BEASTS_SURVIVOR index={i} species={"red" if i<15 else "purple"} maturity=0' for i in range(20)]
    lines += ['P2_BEASTS_PARTY_END','PASS P2_BEASTS_FLOOR4_VIOLET reds=15 purple=5 sprouts=0 cargo=0 pokos=0 repairs_unchanged=1']
    return '\n'.join(lines)+'\n'


class VioletRuntimeTests(unittest.TestCase):
    def test_declared_population_not_native_population(self):
        for population in (0,19,20,21,2147483647):
            with self.subTest(population=population):self.assertEqual(validate_plan(plan(population),'c'*64)['generator_id'],62002)
        for population in (True,-1,2147483648,20.0):
            with self.subTest(population=population),self.assertRaises(ValueError):validate_plan(plan(population),'c'*64)

    def test_source_plan_rejection(self):
        for key,value in [('identity','forest_1:floor2:BlackPom:0'),('position',[0,0,0]),('generator_id',62000),('instance',1),('source_slot',1)]:
            p=copy.deepcopy(plan());p['flower'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_plan(p,'c'*64)
        with self.assertRaises(ValueError):validate_plan(plan(),'d'*64)
        for key,value in [('suppression_applies',True),('native_global_population_verified',True),('spawned_generators',[])]:
            p=plan();p['generation_context'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_plan(p,'c'*64)

    def test_native_evidence_and_mutations(self):
        log=evidence();result=validate(log,'a'*64)
        self.assertEqual(len(result['witnesses']),5);self.assertEqual(result['approach_points'],9)
        replacements=[('floor=4','floor=2'),('health=1\n','health=0.5\n'),('generator=62002','generator=62001'),
            ('input=red','input=purple'),('P2_VIOLET_CONVERT count=5','P2_VIOLET_CONVERT count=4'),
            ('live_x=295','live_x=125'),('index=8 x=295','index=8 x=195'),('P2_BEASTS_CAPTAIN_PLUCK purple=1',''),
            ('species=purple maturity=0','species=purple maturity=1')]
        for old,new in replacements:
            with self.subTest(old=old),self.assertRaises(ValueError):validate(log.replace(old,new), 'a'*64)
        for suffix in ('P2_CAVE_TRANSFER floor=4\n','P2_BEASTS_ENTRY_READY floor=3 token=x descent=disabled\n','P2_FLOOR4_VIOLET_THROW malformed\n'):
            with self.subTest(suffix=suffix),self.assertRaises(ValueError):validate(log+suffix,'a'*64)

    def test_void_approach_rejected(self):
        with self.assertRaises(ValueError):audit_approach(dict(vertices=[],triangles=[]))
