"""Engine-free mocked marker/counter refusals; actual card SAVE remains required."""
import importlib.util,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'scripts';sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('candidate48',P/'run_p2_white_campaign.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
class CounterControls(unittest.TestCase):
 def sample(self,first=True):
  initial=0;ready=4 if first else 0
  default='P2_WHITE_CAMPAIGN_DEFAULT_FILE_READY initial_index=0 measured_index=4 native_successful_default_observer=1\n'if first else''
  baseline=f'P2_WHITE_CAMPAIGN_SAVE_READY initial_index=0 measured_index={ready} default_created={int(first)} backup_slot=1 source_notice_ready=1 generation_before=0\n'
  return default+baseline+'P2_WHITE_CAMPAIGN_SAVE_PASS\n',dict(native_save_index_before='0',native_save_ready_index=str(ready),native_save_index_after=str(ready+1))
 def test_actual_first_file_default_then_one_save(self):r.assess_save_counter(*self.sample(),1)
 def test_existing_file_one_save(self):r.assess_save_counter(*self.sample(False),1)
 def test_extra_save_refuses(self):
  t,s=self.sample();s['native_save_index_after']='6'
  with self.assertRaises(ValueError):r.assess_save_counter(t,s,1)
 def test_blind_plus_five_without_default_witness_refuses(self):
  t,s=self.sample();t='\n'.join(t.splitlines()[1:])
  with self.assertRaises(ValueError):r.assess_save_counter(t,s,1)
 def test_missing_readiness_refuses(self):
  t,s=self.sample();t='\n'.join(x for x in t.splitlines()if not x.startswith('P2_WHITE_CAMPAIGN_SAVE_READY'))
  with self.assertRaises(ValueError):r.assess_save_counter(t,s,1)
 def test_stale_generation_refuses(self):
  t,s=self.sample()
  with self.assertRaises(ValueError):r.assess_save_counter(t,s,2)
 def test_wrong_card_slot_refuses(self):
  t,s=self.sample();t=t.replace('backup_slot=1','backup_slot=0')
  with self.assertRaises(ValueError):r.assess_save_counter(t,s,1)
 def test_duplicate_baseline_refuses(self):
  t,s=self.sample();t=t+t.splitlines()[1]+'\n'
  with self.assertRaises(ValueError):r.assess_save_counter(t,s,1)
 def test_baseline_after_save_refuses(self):
  t,s=self.sample();t=t.splitlines()[0]+'\n'+t.splitlines()[2]+'\n'+t.splitlines()[1]+'\n'
  with self.assertRaises(ValueError):r.assess_save_counter(t,s,1)
 def test_unexplained_existing_counter_jump_refuses(self):
  t,s=self.sample(False);t=t.replace('measured_index=0','measured_index=4');s['native_save_ready_index']='4';s['native_save_index_after']='5'
  with self.assertRaises(ValueError):r.assess_save_counter(t,s,1)
if __name__=='__main__':unittest.main()
