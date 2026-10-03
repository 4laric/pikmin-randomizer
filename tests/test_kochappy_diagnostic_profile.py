import unittest
from scripts.run_pikmin2_purple_kochappy import diagnostic_seconds
class Profile(unittest.TestCase):
 def test_default_all_modes(self):
  for mode in ('ready','positive','forced-down','paused-down'):
   self.assertEqual(diagnostic_seconds(mode),60)
   self.assertEqual(diagnostic_seconds(mode,True),60)
 def test_explicit_positive(self):self.assertEqual(diagnostic_seconds('positive',True,True),180)
 def test_invalid(self):
  for args in [('positive',False,True),('ready',True,True),('forced-down',True,True),('paused-down',True,True),('unknown',True,False),('positive',1,False),('positive',True,1)]:
   with self.subTest(args=args),self.assertRaises(ValueError):diagnostic_seconds(*args)
