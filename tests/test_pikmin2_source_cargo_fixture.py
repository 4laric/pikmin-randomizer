import unittest
from experimental.pikmin2_source_cargo_fixture import instrument,validate


class SourceCargoTests(unittest.TestCase):
    def test_changed_source_rejected(self):
        with self.assertRaises(ValueError):instrument('not the fixture')
    def test_invalid_expectations(self):
        for values in [(-1,5,10),(100,0,10),(100,5,129),(True,5,10)]:
            with self.subTest(values=values),self.assertRaises(ValueError):instrument('',*values)
    def test_complete_evidence(self):
        log='P2_SOURCE_CARGO_PASS value=100 weight=5 slots=10 seams=2 duplicate_credit=0 repairs_unchanged=1\nPASS p2 second floor:\n'
        for n in [1,0]:log+=f'P2_POD_RECEIPT id=treasure:juji_key_fc value=100 new={n} pokos=100 seeds=0\n'
        self.assertEqual(validate(log,'treasure=juji_key_fc count=1 pokos=100')['seams'],2)
        with self.assertRaises(ValueError):validate(log,'treasure=dia_a_red count=1 pokos=100')
        with self.assertRaises(ValueError):validate(log.replace('new=0','new=1'),'treasure=juji_key_fc count=1 pokos=100')


if __name__=='__main__':unittest.main()
