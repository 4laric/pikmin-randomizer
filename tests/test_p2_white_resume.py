"""Engine-free resume marker/card controls; not native gameplay acceptance."""
import importlib.util
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('white_resume53',ROOT/'scripts/run_p2_white_campaign.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
class ResumeControls(unittest.TestCase):
 def sample(self):
  sha='8c9ad61ed23513bf73f12f5ac4032c4dd56f8bfaf7f752a2d4862022f021a021'
  card=dict(generation=1,sha256=sha,native_block_size=32768,p1_stock=[0,0,0,25,0,0,0,0,0],native_saved_day=3)
  lines=['[Pikmin Randomizer] CAMPAIGN_RESUMED day=3',
   f'P2_WHITE_CAMPAIGN_RESUME_CHECKPOINT generation=1 sha256={sha}',
   'P2_WHITE_CAMPAIGN_RESUME_BASELINE stock=15 leaf=15 spent=15 pokos=180 consumed_source_absent=1 native_checkpoint_resumed=1',
   'P2_WHITE_CAMPAIGN_P1_RESUME_STOCK b_leaf=0 b_bud=0 b_flower=0 r_leaf=25 r_bud=0 r_flower=0 y_leaf=0 y_bud=0 y_flower=0',
   'P2_SHIP_CHOICE captain=0 species=4']
  lines += [f'P2_SHIP_WITHDRAW species=4 maturity=0 stored={n}' for n in range(14,-1,-1)]
  lines += ['P2_WHITE_CAMPAIGN_RESUME_PASS day=3 white=15 stock=0 leaf=15 spent=15 pokos=180 original_red_conserved=5 original_white_conserved=15 original_population=20 red_field=0 displacement=30.8829 native_checkpoint_resumed=1 ordinary_ship_keyboard=1']
  return '\n'.join(lines)+'\n',dict(exit_code=0,elapsed=28.919,timed_out=False,saved_card=card,current_card=dict(card),source_proof=True,expected_day=3)
 def test_matching_ordinary_day_and_readonly_checkpoint(self):
  t,k=self.sample();self.assertTrue(r.assess_resume(t,**k)['fresh_resume_passed'])
 def test_independent_generation_not_inferred_from_day(self):
  t,k=self.sample();t=t.replace('generation=1','generation=9');k['saved_card']['generation']=9;k['current_card']['generation']=9
  self.assertEqual(r.assess_resume(t,**k)['generation'],9)
 def test_checkpoint_marker_refusals(self):
  t,k=self.sample();marker=t.splitlines()[1]
  for replacement in ['',marker+'\n'+marker,marker.replace('generation=1','generation=0'),marker.replace('generation=1','generation=2'),marker.replace(k['saved_card']['sha256'],'0'*64),marker+' extra=1']:
   with self.subTest(replacement=replacement),self.assertRaises(ValueError):r.assess_resume(t.replace(marker,replacement),**k)
 def test_old_actual52_missing_checkpoint_refuses(self):
  t,k=self.sample();t='\n'.join(x for x in t.splitlines() if not x.startswith('P2_WHITE_CAMPAIGN_RESUME_CHECKPOINT'))
  with self.assertRaises(ValueError):r.assess_resume(t,**k)
 def test_day_marker_refusals(self):
  t,k=self.sample();marker=t.splitlines()[0]
  for replacement in ['',marker+'\n'+marker,marker.replace('day=3','day=2'),'[Pikmin Randomizer] CAMPAIGN_RESUMED generation=1']:
   with self.subTest(replacement=replacement),self.assertRaises(ValueError):r.assess_resume(t.replace(marker,replacement),**k)
 def test_changed_card_refuses(self):
  t,k=self.sample();k['current_card']['sha256']='0'*64
  with self.assertRaises(ValueError):r.assess_resume(t,**k)
 def test_native_effect_and_conservation_refusals(self):
  t,k=self.sample()
  for old,new in [('stored=14','stored=15'),('original_population=20','original_population=19'),('red_field=0','red_field=20'),('native_checkpoint_resumed=1','native_checkpoint_resumed=0'),('r_leaf=25','r_leaf=24'),('displacement=30.8829','displacement=30'),('P2_SHIP_CHOICE captain=0 species=4','P2_SHIP_CHOICE captain=0 species=0')]:
   with self.subTest(old=old),self.assertRaises(ValueError):r.assess_resume(t.replace(old,new),**k)
 def test_additional_receipt_or_save_refuses(self):
  t,k=self.sample()
  for extra in ['P2_WHITE_TREASURE_RECEIPT value=180','P2_SHIP_DEPOSIT species=4','[Pikmin Randomizer] CAMPAIGN_SAVED generation=2']:
   with self.subTest(extra=extra),self.assertRaises(ValueError):r.assess_resume(t+extra+'\n',**k)
 def test_runtime_and_source_refusals(self):
  t,k=self.sample()
  for key,value in [('exit_code',1),('elapsed',60.1),('timed_out',True),('source_proof',False)]:
   args=dict(k);args[key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):r.assess_resume(t,**args)
if __name__=='__main__':unittest.main()
