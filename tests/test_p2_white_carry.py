"""Independent evidence refusal controls. Synthetic logs are NOT gameplay."""
import importlib.util,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('carry_oracle',Path(__file__).resolve().parents[1]/'scripts/run_p2_white_carry.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def valid():
 lines=['P2_WHITE_CARRY_WINDOW width=960 height=540 centered=1','P2_WHITE_CARRY_BASELINE red=20 white=0 heads=0 bodies=20 cargo_min=1 cargo_max=1 initial_pokos=0','P2_WHITE_CARRY_PLUCKED red=19 white=1 heads=0 bodies=20 spent=1 ordinary_birth_pluck=1']
 for i in range(10):lines.append(f'P2_WHITE_CARRY_SAMPLE frame={100+i} cargo_uid=26 white_uid=91 carrier_white=1 carrier_red=0 carrier_other=0 carrier_bodies=1 strength=1 native_strength=1 speed_power=3 mode=9 body_total=20 heads=0 x={i*4} y=0 z=0 goal_distance={100-i*4}')
 lines+=['[Pikipelago] P2_POD_RECEIPT id=treasure:white_carry_smoke value=1 new=1 pokos=1 seeds=0','P2_WHITE_CARRY_PASS cargo_removed=1 stable_frames=60 red=19 white=1 heads=0 bodies=20 pokos=1']
 return '\n'.join(lines)
class Oracle(unittest.TestCase):
 def invoke(self,text,**overrides):
  args=dict(economy='P2_ECONOMY_1\ntreasure:white_carry_smoke 1\n',receipt='treasure=white_carry_smoke count=1 pokos=1\n',exit_code=0,elapsed_seconds=49,timed_out=False,source_proof=True);args.update(overrides);return m.assess(text,**args)
 def test_synthetic_schema_only(self):self.assertTrue(self.invoke(valid())['slice_passed'])
 def test_distinct_failures(self):
  changes=[('carrier_red=0','carrier_red=1'),('carrier_white=1','carrier_white=0'),('carrier_bodies=1','carrier_bodies=2'),('strength=1 native_strength=1','strength=3 native_strength=3'),('speed_power=3','speed_power=1'),('mode=9','mode=1'),('body_total=20','body_total=19'),('heads=0 x=','heads=1 x='),('frame=109','frame=111'),('white_uid=91 carrier_white=1','white_uid=92 carrier_white=1'),('centered=1','centered=0'),('cargo_min=1','cargo_min=15'),('ordinary_birth_pluck=1','ordinary_birth_pluck=0'),('stable_frames=60','stable_frames=1'),('cargo_removed=1','cargo_removed=0')]
  for old,new in changes:
   with self.subTest(old=old):
    changed=valid().replace(old,new,1)
    with self.assertRaises(ValueError):self.invoke(changed)
 def test_no_stationary_or_wrong_direction(self):
  for text in [valid().replace('x=36','x=0'),valid().replace('goal_distance=64','goal_distance=110')]:
   with self.assertRaises(ValueError):self.invoke(text)
 def test_receipt_requires_exactonce_durable(self):
  row='[Pikipelago] P2_POD_RECEIPT id=treasure:white_carry_smoke value=1 new=1 pokos=1 seeds=0'
  for text in (valid()+'\n'+row,valid().replace(row,''),valid().replace('new=1','new=0')):
   with self.assertRaises(ValueError):self.invoke(text)
  with self.assertRaises(ValueError):self.invoke(valid(),receipt='wrong\n')
 def test_order_and_ledger_refusals(self):
  lines=valid().splitlines()
  with self.assertRaises(ValueError):self.invoke('\n'.join(lines[:2]+lines[3:]+lines[2:3]))
  for ledger in ('','P2_ECONOMY_1\ntreasure:white_carry_smoke 2\n','P2_ECONOMY_1\ntreasure:white_carry_smoke 1\ntreasure:extra 1\n'):
   with self.assertRaises(ValueError):self.invoke(valid(),economy=ledger)
 def test_guard_source_timing_refusals(self):
  for args in ({'exit_code':86},{'elapsed_seconds':60.01},{'timed_out':True},{'source_proof':False}):
   with self.assertRaises(ValueError):self.invoke(valid(),**args)
  with self.assertRaises(ValueError):self.invoke(valid()+'\nP2_FIXTURE_CAPTAIN_DOWN')
if __name__=='__main__':unittest.main()
