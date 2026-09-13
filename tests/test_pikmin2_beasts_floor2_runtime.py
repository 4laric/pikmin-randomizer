import copy
import unittest
from experimental.pikmin2_beasts_floor2_runtime import validate


PLAN = {'flowers':[{'generator_id':62000,'position':[-55,0,75]},
                   {'generator_id':62001,'position':[75,0,-95]}]}


def trace():
    lines = ['P2_ROOM_CARGO_FREE_READY cargo=0 repairs=1']
    for f in PLAN['flowers']:
        x,y,z = f['position']
        lines.append(f'P2_BEASTS_FLOWER id={f["generator_id"]} x={x} y={y} z={z} live_x={x} live_y={y} live_z={z} ground=0')
    lines.append('P2_BEASTS_READY reds=20 flowers=2 cargo=0')
    for flower in (62000,62001):
        lines.append(f'P2_BEASTS_APPROACH flower={flower} distance=73.3')
        for i in range((flower-62000)*5,(flower-61999)*5):
            lines.append(f'P2_BEASTS_THROW original={i} flower={flower}')
        lines.extend(['P2_VIOLET_CONVERT count=5',f'P2_BEASTS_FLOWER_CONVERTED id={flower} count=5'])
    lines.extend(['P2_BEASTS_SPROUTS reds=10 purple=0 sprouts=10',
                  'P2_BEASTS_CAPTAIN_PLUCK purple=1',
                  'PASS P2_BEASTS_FLOOR2 reds=10 purple=10 sprouts=0 cargo=0 pokos=0 repairs_unchanged=1'])
    return '\n'.join(lines)+'\n'


class BeastsRuntimeTests(unittest.TestCase):
    def test_same_color_refund_trace(self):
        lines=['P2_ROOM_CARGO_FREE_READY cargo=0 repairs=1','P2_BEASTS_REFUND_INITIAL reds=19 purple=1']
        lines.extend(line for line in trace().splitlines() if line.startswith('P2_BEASTS_FLOWER '))
        lines.append('P2_BEASTS_READY reds=19 flowers=2 cargo=0')
        for flower,indices in ((62000,range(6)),(62001,range(6,11))):
            lines.append(f'P2_BEASTS_APPROACH flower={flower} distance=73.3')
            for i in indices:
                lines.extend([f'P2_BEASTS_THROW original={i} flower={flower}',
                              f'P2_VIOLET_WITNESS sequence={i+1} generator={flower} input={"purple" if i==0 else "red"}'])
                if i==0:lines.append('P2_VIOLET_CONVERT count=1')
            lines.extend(['P2_VIOLET_CONVERT count=5',f'P2_BEASTS_FLOWER_CONVERTED id={flower} count={6 if flower==62000 else 5}'])
        lines.extend(['P2_BEASTS_SPROUTS reds=9 purple=0 sprouts=11','P2_BEASTS_CAPTAIN_PLUCK purple=1',
                      'PASS P2_BEASTS_FLOOR2 reds=9 purple=11 sprouts=0 cargo=0 pokos=0 repairs_unchanged=1'])
        log='\n'.join(lines)+'\n'
        self.assertEqual(len(validate(log,PLAN,refund=True)['witnesses']),11)
        with self.assertRaises(ValueError):validate(log,PLAN)
        for old,new in [('input=purple','input=red'),('sequence=11','sequence=10'),
                        ('count=6','count=5'),('reds=9 purple=11','reds=10 purple=10'),
                        ('original=5 flower=62000','original=5 flower=62001'),
                        ('P2_VIOLET_CONVERT count=1','P2_VIOLET_CONVERT count=0')]:
            with self.subTest(old=old),self.assertRaises(ValueError):validate(log.replace(old,new),PLAN,refund=True)

    def test_native_witnesses_required_and_tamper_rejected(self):
        log=trace()
        for index,generator in enumerate((62000,62001)):
            batch='\n'.join(f'P2_VIOLET_WITNESS sequence={index*5+i+1} generator={generator} input=red' for i in range(5))
            target=f'P2_VIOLET_CONVERT count=5\nP2_BEASTS_FLOWER_CONVERTED id={generator}'
            log=log.replace(target,batch+'\n'+target)
        self.assertEqual(len(validate(log,PLAN,require_witnesses=True)['witnesses']),10)
        with self.assertRaises(ValueError):validate(trace(),PLAN,require_witnesses=True)
        for old,new in [('sequence=2','sequence=1'),('generator=62001','generator=62000'),
                        ('input=red','input=purple'),('input=red','input=unknown'),
                        ('sequence=10','sequence=11'),('sequence=1 ','sequence=01 ')]:
            with self.subTest(old=old,new=new),self.assertRaises(ValueError):validate(log.replace(old,new),PLAN,require_witnesses=True)
        witness=next(line for line in log.splitlines() if line.startswith('P2_VIOLET_WITNESS'))
        for bad in (log+witness+'\n',log.replace(witness+'\n',''),witness+'\n'+log.replace(witness+'\n','')):
            with self.subTest(log=bad),self.assertRaises(ValueError):validate(bad,PLAN,require_witnesses=True)

    def test_complete_trace(self):
        result = validate(trace(),PLAN)
        self.assertEqual(result['final_population'],dict(red=10,purple=10,sprouts=0))
        self.assertEqual(result['conversions'],[5,5])

    def test_rejects_wrong_or_nonfinite_source_coordinates(self):
        for old,new in [('x=-55','x=-54'),('live_y=0','live_y=1'),('ground=0','ground=nan'),('id=62001','id=62000')]:
            with self.subTest(old=old),self.assertRaises(ValueError):validate(trace().replace(old,new),PLAN)
        other=copy.deepcopy(PLAN);other['flowers'][0]['position'][0]=-40
        with self.assertRaises(ValueError):validate(trace(),other)

    def test_rejects_incomplete_or_forbidden_evidence(self):
        for token in ('P2_BEASTS_CAPTAIN_PLUCK','P2_BEASTS_FLOWER_CONVERTED id=62001',
                      'P2_BEASTS_APPROACH flower=62000','P2_BEASTS_THROW original=9','P2_VIOLET_CONVERT'):
            log='\n'.join(line for line in trace().splitlines() if not line.startswith(token))
            with self.subTest(token=token),self.assertRaises(ValueError):validate(log,PLAN)
        for extra in ('FAIL native','P2_POD_RECEIPT id=x','P2_TREASURE_DELIVERED id=x',
                      'P2_ROOM_READY treasure=hidden','P2_VIOLET_CONVERT count=1'):
            with self.subTest(extra=extra),self.assertRaises(ValueError):validate(trace()+extra+'\n',PLAN)

    def test_rejects_duplicates_wrong_targets_and_population(self):
        for old,new in [('original=9 flower=62001','original=9 flower=62000'),
                        ('distance=73.3','distance=173.3'),('reds=10 purple=10','reds=11 purple=10')]:
            with self.subTest(old=old),self.assertRaises(ValueError):validate(trace().replace(old,new),PLAN)
        with self.assertRaises(ValueError):validate(trace()+trace().splitlines()[-1]+'\n',PLAN)


if __name__=='__main__':unittest.main()
