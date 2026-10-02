"""Engine-free mocked staging controls; native gameplay remains required."""
import importlib.util,unittest,struct,tempfile,sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'scripts'
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('candidate47',P/'stage_p2_white_campaign.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
def row(name,kind=b'ikip'):
 r=bytearray(96);r[:8]=b'    0.0v';r[16:48]=name.ljust(32,b'\0');r[72:76]=kind;r[80:84]=b'50rp';return bytes(r)
class Controls(unittest.TestCase):
 def setup_data(self):
  reds=[row(b'red')for i in range(20)];items=[row(b'preview red onion',b'meti'),row(b'preview ship',b'meti'),row(b'preview treasure bolt',b'tlle')]
  self.source=b'1.0v'+struct.pack('>4fI',-85,0,0,45,23)+b''.join(reds+items)
  self.anchors=[row(b'blue goal'),row(b'red goal'),row(b'yellow goal'),row(b'ufo goal')];out=[]
  for i,r in enumerate(self.anchors):
   r=bytearray(r);struct.pack_into('>6f',r,48,*([(-498.186,0,1454.469),(206.573,30,1858.584)][i==3]if i in(1,3)else(0,0,0)),0,0,0);out.append(bytes(r))
  self.anchors=out;self.original=b'1.0v'+struct.pack('>4fI',47.6673,30,1919.7587,180,4)+b''.join(out)
  boss=bytearray(row(b'Pom',b'ssob'));boss[76:80]=b'\x02\0\0\0';self.boss=bytes(boss)
 def rewrite(self,original_hash=None):
  self.setup_data()
  with tempfile.TemporaryDirectory()as d:
   p=Path(d)/'dataDir/stages/practice';p.mkdir(parents=True);(p/'default.gen').write_bytes(self.original)
   with patch.object(s,'generator',return_value=self.source),patch.object(s,'digest',return_value=original_hash or s.PRACTICE_GENERATOR_SHA256),patch.object(s,'records',side_effect=lambda p:self.anchors if p.as_posix().endswith('practice/default.gen')else[self.boss]):return s.rewrite_generators(Path(d),True,True)
 def test_original_anchor_bytes_and_disclosed_start(self):
  b=self.rewrite();self.assertEqual(struct.unpack_from('>4f',b,4),(-350,0,1600,180));rows=[b[i:i+96]for i in range(24,len(b),96)]
  for uid,ix in[(23,1),(24,3)]:r=next(r for r in rows if struct.unpack_from('<I',r,8)[0]==uid);self.assertEqual(r[48:72],self.anchors[ix][48:72])
 def test_twenty_red_payload_and_ids_unchanged_except_setup(self):
  b=self.rewrite();rows=[b[i:i+96]for i in range(24,len(b),96)]
  for i,r in enumerate(rows[:20]):
   before=self.source[24+96*i:24+96*(i+1)];self.assertEqual(before[:8]+before[12:48]+before[60:],r[:8]+r[12:48]+r[60:]);self.assertEqual(struct.unpack_from('<I',r,8)[0],i+1);self.assertEqual(struct.unpack_from('>f',r,52)[0],0)
  self.assertEqual(len(rows),27);self.assertEqual(len({struct.unpack_from('<I',r,8)[0]for r in rows}),27)
 def test_all_three_budgeted_ivory_and_original_cargo_host(self):
  b=self.rewrite();rows=[b[i:i+96]for i in range(24,len(b),96)]
  for uid in(25,28,29):r=next(r for r in rows if struct.unpack_from('<I',r,8)[0]==uid);self.assertEqual(struct.unpack_from('>I',r,80)[0],69)
  r=next(r for r in rows if struct.unpack_from('<I',r,8)[0]==26);self.assertEqual(r[80:84],b'50rp');self.assertEqual(struct.unpack_from('>3f',r,48),(-100,0,1450))
 def test_changed_original_generator_refused(self):
  with self.assertRaisesRegex(ValueError,'Audited original Practice generator'):self.rewrite('0'*64)
 def test_practice_profile_without_retail_refused(self):
  with tempfile.TemporaryDirectory()as d:
   p=Path(d);(p/'dataDir/parms').mkdir(parents=True);(p/'dataDir/parms/pelMgr.bin').write_bytes(b'mock')
   with patch.object(s,'pellet_configs',return_value=[dict(model_id='pr05',carry_min=5,carrier_slots=10,matching_yield=5,other_yield=3)]),self.assertRaisesRegex(ValueError,'Original P2 retail diamond'):s.prepare(p,p,p,p,p/'fresh',None,True)
if __name__=='__main__':unittest.main()

