import unittest
from experimental.pikmin2_frog_runtime import validate,instrument_family

class RuntimeEvidenceTests(unittest.TestCase):
 def sample(self):
  text='PASS P2_FROG_RUNTIME birth4 controls2 corpses2 injected_attack=1\n'
  for i,t,r in [(201001,0,1),(201002,33,1),(201003,0,0),(201004,33,0)]:text+=f'P2_FROG_BIRTH id={i} type={t} registered={r}\n'
  for s in ('Frog','MaroFrog'):
   for c,p in [(0,0),(0,1),(1,11)]:text+=f'P2_FROG_DRAW species={s} corpse={c} clip=dead pose={p}\n'
  return text
 def test_complete_and_incomplete(self):
  text=self.sample();self.assertTrue(validate(text,0)['passed'])
  self.assertFalse(validate(text,1)['passed'])
  self.assertFalse(validate(text.replace('species=MaroFrog corpse=1','species=MaroFrog corpse=0'),0)['passed'])
  self.assertFalse(validate(text.replace('id=201004 type=33 registered=0','id=201004 type=33 registered=1'),0)['passed'])
 def test_duplicate_birth_rejected(self):
  self.assertFalse(validate(self.sample()+'P2_FROG_BIRTH id=201001 type=0 registered=1\n',0)['passed'])
 def test_death_animation_does_not_prove_natural_motion(self):
  self.assertFalse(validate('P2_FROG_INJECTED_ATTACK id=201001 accepted=1\n'+self.sample(),0)['passed'])
 def test_changed_source_fails_closed(self):
  with self.assertRaises(ValueError):instrument_family('changed renderer')

if __name__=='__main__':unittest.main()
