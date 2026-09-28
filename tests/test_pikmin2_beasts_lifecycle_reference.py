import unittest
from experimental.pikmin2_beasts_lifecycle_reference import proper_slots,budgets,conversion_reference

class BeastsLifecycleReferenceTests(unittest.TestCase):
    def test_proper_block_not_base_duplicate(self):
        raw=b'{\n {ip01} 4 0\n {_eof}\n}\n{\n {ip01} 4 5\n {ip11} 4 1\n {ip13} 4 9\n {_eof}\n}'
        self.assertEqual(proper_slots(raw),5)
        with self.assertRaises(ValueError):proper_slots(raw+raw)
    def test_birth_gate(self):
        self.assertEqual(sum(budgets(5,19).values()),10)
        self.assertEqual(budgets(5,20),{})
        with self.assertRaises(ValueError):budgets(5,-1)
    def test_two_bud_conversion_and_refund(self):
        limits=budgets(5,0);flowers=list(limits)
        events=[dict(id=str(i),flower=flowers[i//5],input='red') for i in range(10)]
        result=conversion_reference(['red']*20,['red']*10+['purple']*10,events,limits)
        self.assertEqual(result['net_purple_outputs'],10)
        same=[dict(id=str(i),flower=flowers[0],input='purple') for i in range(20)]
        self.assertEqual(conversion_reference(['purple'],['purple'],same,limits)['used'],{})
        with self.assertRaises(ValueError):conversion_reference(['red']*20,['purple']*11,events+[dict(id='11',flower=flowers[0],input='red')],limits)
        with self.assertRaises(ValueError):conversion_reference(['red']*20,['purple']*10,events+[events[0]],limits)
    def test_population_and_unwitnessed_increase(self):
        with self.assertRaises(ValueError):conversion_reference(['red'],['red','purple'],[],budgets(5,0))
        with self.assertRaises(ValueError):conversion_reference(['red'],['purple'],[],budgets(5,0))
        self.assertEqual(conversion_reference(['red'],[],[],budgets(5,0))['net_purple_outputs'],0)
