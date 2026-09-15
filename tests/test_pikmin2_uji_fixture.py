import unittest
from experimental.pikmin2_uji_fixture import instrument
class UjiFixtureTests(unittest.TestCase):
 def test_changed_fixture_rejected(self):
  with self.assertRaises(ValueError):instrument('unrelated')
 def test_hook_precedes_shared_cargo(self):
  text=instrument('class RoomApp : public PlugPikiApp {\n        if(cargoCarryFixture(n))return result;')
  self.assertLess(text.index('if(ujiFixture(n))'),text.index('if(cargoCarryFixture(n))'))
if __name__=='__main__':unittest.main()
from experimental.pikmin2_uji_fixture import validate
class ReceiptTests(unittest.TestCase):
 def test_distinct_receipts_and_duplicates(self):
  log='P2_UJI_PAIR registered=2 source_values=1,2\nP2_UJI_CORPSES real_transport_assigned=1 corpse_relocation=0\nPASS Uji proxy:\n'
  for identity,value in [(60000,1),(60001,2)]:
   for new in [1,0]:log+=f'P2_POD_RECEIPT id=corpse:uji:{identity} value={value} new={new} pokos=3 seeds=0\n'
  for identity,value in [(60000,1),(60001,2)]:log+=f'P2_UJI_DUPLICATE id=corpse:uji:{identity} value={value} duplicate_credit=0\n'
  self.assertEqual(validate(log)['total_pokos'],3)
  with self.assertRaises(ValueError):validate(log.replace('60001','60000'))
