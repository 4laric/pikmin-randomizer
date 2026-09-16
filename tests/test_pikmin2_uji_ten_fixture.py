import unittest
from experimental.pikmin2_uji_ten_fixture import instrument,validate
class TenTests(unittest.TestCase):
 def test_framing(self):
  with self.assertRaises(ValueError):instrument('wrong')
 def test_receipt_validation(self):
  log='PASS Uji ten: receipts14 duplicates0 repairs_unchanged cargo100_separate connector_crossings10\n'
  for i in range(61000,61010):
   value=2 if i<61004 else 1
   log+=f'P2_POD_RECEIPT id=corpse:uji:{i} value={value} new=1 pokos=14 seeds=0\nP2_UJI_TEN_CROSS generator={i}\nP2_UJI_DUPLICATE id=corpse:uji:{i} value={value} duplicate_credit=0\n'
  self.assertEqual(validate(log)['corpse_pokos'],14)
  with self.assertRaises(ValueError):validate(log.replace('61009','61008'))
if __name__=='__main__':unittest.main()
