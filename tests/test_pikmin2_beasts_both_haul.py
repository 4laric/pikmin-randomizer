import unittest
from experimental import pikmin2_beasts_both_haul as both
class BothHaulTests(unittest.TestCase):
    def log(self,initial=0):
        t='a'*64;g=both.green.INSTANCE;d=both.donut.INSTANCE
        return f'''P2_CAVE_READY floor=3 survivors=20 health=1
P2_BEASTS_ENTRY_READY floor=3 token={t} descent=disabled
P2_BOTH_READY cargo=2 configs_distinct=1 survivors=20
P2_BOTH_POINT index=0 x=-85 y=0 z=-960 attached=0
P2_BOTH_POINT index=0 x=-85 y=8 z=-800 attached=20
P2_BOTH_POINT index=0 x=-85 y=8 z=-510 attached=20
P2_BOTH_POINT index=0 x=-85 y=8 z=-340 attached=20
P2_BOTH_POINT index=0 x=-85 y=8 z=-320 attached=20
P2_POD_RECEIPT id=treasure:{g} value=150 new={int(initial==0)} pokos=150 seeds=0
P2_BOTH_DELIVERED index=0 total=150 duplicate_credit=0
P2_BOTH_WALK goal=0 x=-85 y=0 z=-120
P2_BOTH_WALK goal=1 x=-85 y=0 z=85
P2_BOTH_WALK goal=2 x=150 y=20.5 z=0
P2_BOTH_WALK goal=3 x=150 y=20.5 z=-55
P2_BOTH_WALK goal=4 x=175 y=20.5 z=-55
P2_BOTH_APPROACH goals=5 survivors=20
P2_BOTH_POINT index=1 x=175 y=20.5 z=-55 attached=0
P2_BOTH_POINT index=1 x=150 y=28.5 z=0 attached=20
P2_BOTH_POINT index=1 x=0 y=8 z=70 attached=20
P2_BOTH_POINT index=1 x=-85 y=8 z=-200 attached=20
P2_BOTH_POINT index=1 x=-85 y=8 z=-230 attached=20
P2_POD_RECEIPT id=treasure:{d} value=230 new=1 pokos=380 seeds=0
P2_BOTH_DELIVERED index=1 total=380 duplicate_credit=0
PASS P2_BOTH_HAUL cargo=2 pokos=380 receipts=2 repairs_unchanged=1 descent=disabled
'''
    def validate(self,s,initial=0):return both.validate(s,'a'*64,initial,both.LEDGER,both.green.LEDGER)
    def test_fresh_and_actual_partial(self):
        for initial in (0,150):self.assertEqual(self.validate(self.log(initial),initial)['total'],380)
    def test_bad_receipt_party_trace_or_phase(self):
        for old,new in [('new=1 pokos=380','new=0 pokos=380'),('value=230','value=150'),('seeds=0','seeds=1'),('survivors=20 health=1','survivors=19 health=1'),('x=175','x=nan'),('attached=20','attached=11'),('configs_distinct=1','configs_distinct=0'),('P2_BOTH_APPROACH goals=5 survivors=20',''),('pokos=380 receipts=2','pokos=230 receipts=1')]:
            with self.subTest(old=old):
                with self.assertRaises(ValueError):self.validate(self.log().replace(old,new))
        with self.assertRaises(ValueError):self.validate(self.log()+'P2_POD_RECEIPT malformed\n')
        with self.assertRaises(ValueError):self.validate(self.log(150))
    def test_exact_ledgers(self):
        for ledger,partial in [(both.green.LEDGER,both.green.LEDGER),(both.LEDGER,both.LEDGER),(both.LEDGER+b'junk',both.green.LEDGER)]:
            with self.assertRaises(ValueError):both.validate(self.log(),'a'*64,0,ledger,partial)
