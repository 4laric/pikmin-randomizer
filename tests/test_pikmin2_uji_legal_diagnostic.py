import unittest
from experimental.pikmin2_uji_legal_diagnostic import instrument,HOOK
class LegalTests(unittest.TestCase):
 def test_framing(self):
  with self.assertRaises(ValueError):instrument('wrong')
 def test_no_bypass(self):
  self.assertIn('stimulate(InteractAttack',HOOK)
  for forbidden in ['mHealth=0','mStateID=','dieSoon','mSRT.t=']:self.assertNotIn(forbidden,HOOK)
if __name__=='__main__':unittest.main()
