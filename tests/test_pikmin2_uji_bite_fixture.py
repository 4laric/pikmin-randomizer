import unittest
from experimental.pikmin2_uji_bite_fixture import HOOK,instrument,validate
class BiteFixtureTests(unittest.TestCase):
 def test_no_direct_actor_forcing(self):
  self.assertNotIn('InteractAttack',HOOK);self.assertNotIn('startMotion',HOOK)
  self.assertNotRegex(HOOK,r'(mStateID|mHealth|mSRT\.t)\s*=(?!=)')
  self.assertIn('getCreaturePointer(2)==prey',HOOK)
  with self.assertRaises(ValueError):instrument('changed')
 def test_complete_visual_behavior_evidence(self):
  log='PASS Uji natural bite/eat:\n'
  for clip in ('attack2','eat'):
   for pose in (0,1):log+=f'P2_UJI_VISUAL species=UjiB corpse=0 clip={clip} pose={pose}\n'
  self.assertTrue(validate(log,True)['natural_eat'])
  with self.assertRaises(ValueError):validate(log.replace('clip=eat','clip=move'),True)
  with self.assertRaises(ValueError):validate(log.replace('PASS Uji natural bite/eat:','missing'),True)
if __name__=='__main__':unittest.main()
