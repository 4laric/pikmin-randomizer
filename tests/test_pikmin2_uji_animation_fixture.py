import unittest
from experimental.pikmin2_uji_animation_fixture import instrument_family,validate

class AnimationFixtureTests(unittest.TestCase):
 def log(self):
  s='PASS grounded Uji:\n'
  for i in range(61000,61010):
   for marker in ('P2_UJI_BIRTH id=','P2_UJI_GROUNDED id=','P2_UJI_GROUNDED_HIT id=','P2_UJI_GROUNDED_CROSS id='):s+=marker+str(i)+'\n'
   s+=f'P2_POD_RECEIPT id=corpse:uji:{i} value={2 if i<61004 else 1} new=1\n'
  return s
 def test_visual_and_lifecycle_gates(self):
  s=self.log()
  for kind in ('UjiA','UjiB'):
   for corpse in (0,1):s+=f'P2_UJI_VISUAL species={kind} corpse={corpse} clip=static pose=0\n'
  self.assertFalse(validate(s,False)['animated'])
  with self.assertRaises(ValueError):validate(s,True)
  s=self.log()
  for kind in ('UjiA','UjiB'):
   for pose in (0,1):s+=f'P2_UJI_VISUAL species={kind} corpse=0 clip=appear pose={pose}\n'
   s+=f'P2_UJI_VISUAL species={kind} corpse=1 clip=dead pose=11\n'
  self.assertTrue(validate(s,True)['animated'])
  with self.assertRaises(ValueError):validate(s.replace('PASS grounded Uji:','missing'),True)
 def test_instrumentation_fails_closed(self):
  with self.assertRaises(ValueError):instrument_family('changed native family')

if __name__=='__main__':unittest.main()
