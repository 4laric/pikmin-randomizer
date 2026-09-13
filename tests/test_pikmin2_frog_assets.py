import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from experimental.pikmin2_frog_assets import event_frames,profile,corpse,check_budget,CLIP_BYTES,TOTAL_BYTES,extract
class FrogAssetsTests(unittest.TestCase):
 def test_preserve_event_loop_boundaries_deterministically(self):
  events=[[0,0],[4,2],[28,3],[34,1]]
  frames=event_frames(35,events)
  self.assertEqual(frames,event_frames(35,events));self.assertEqual(len(frames),12)
  self.assertTrue({0,4,28,34}.issubset(frames));self.assertEqual(frames,sorted(set(frames)))
  self.assertEqual(event_frames(1,[]),[0])
 def test_reject_bad_sampling(self):
  for duration,events,cap in ((0,[],12),(30,[[30,2]],12),(30,[[True,2]],12),(30,[],True),(30,[[x,2] for x in range(14)],12)):
   with self.assertRaises(ValueError):event_frames(duration,events,cap)
 def test_parameter_blocks_remain_separate(self):
  raw=b'{ {fp00} 4 800 {fp12} 4 360 {fp20} 4 200 {fp24} 4 10 {fp01} 4 40 {_eof} } { {fp01} 4 1 {fp02} 4 320 {fp03} 4 0.2 {fp04} 4 300 {_eof} }'
  result=profile(raw);self.assertEqual(result['fields']['air_time'],1);self.assertEqual(result['fields']['sight_radius'],360)
  self.assertEqual(result['parameter_blocks'][0]['fp01'],40)
  with self.assertRaises(ValueError):profile(raw.replace(b'0.2',b'nan'))
  with self.assertRaises(ValueError):profile(raw+raw)
 def test_budget_boundaries(self):
  check_budget(TOTAL_BYTES-1,CLIP_BYTES-1,1)
  for args in ((TOTAL_BYTES,0,1),(0,CLIP_BYTES,1),(0,0,0),(0,0,True)):
   with self.assertRaises(RuntimeError):check_budget(*args)
 def test_corpse_nonfinite_and_invalid(self):
  data=dict(min='7',max='14',pikicountmin='8',pikicountmax='8',money='5',radius='30',p_radius='22',height='14',offset=['0','0','0'])
  self.assertEqual(corpse(data)['money'],5)
  with self.assertRaises(ValueError):corpse(dict(data,radius='nan'))
  with self.assertRaises(ValueError):corpse(dict(data,max='6'))
 def test_refuse_overwrite_before_source_access(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'keep').write_text('unchanged')
   with self.assertRaises(ValueError):extract(root/'absent.iso',root/'absent-source',root)
   self.assertEqual((root/'keep').read_text(),'unchanged')
 def test_wrong_region_has_no_output(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);iso=root/'source.iso';iso.write_bytes(b'GPVJ0100')
   with patch('experimental.pikmin2_frog_assets.disc_files',return_value={}),patch('experimental.pikmin2_frog_assets.subprocess.check_output',return_value='a'*40):
    with self.assertRaises(ValueError):extract(iso,root,root/'output')
   self.assertFalse((root/'output').exists())
if __name__=='__main__':unittest.main()
