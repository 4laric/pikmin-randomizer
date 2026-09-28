import struct,unittest
from experimental.pikmin2_convert import Writer,u32
from experimental.pikmin2_frog_visual_audit import chunks
from experimental.pikmin2_frog_material_profile import profile,rewrite

class ProfileTests(unittest.TestCase):
 def model(self):
  w=Writer();w.begin(16,1);w.pad();w.put('3f',1,2,3);w.end();w.begin(48,2,2);w.pad()
  for i in range(2):w.data+=bytes(88);w.put('I',1);w.data+=bytes(32)
  for i in range(2):
   r=len(w.data);w.data+=bytes(152);struct.pack_into('>I',w.data,r,257);w.data[r+8:r+12]=bytes([255]*4);w.data[r+16:r+20]=bytes([255]*4);struct.pack_into('>I',w.data,r+76,1);struct.pack_into('>I',w.data,r+84,1)
  w.end();w.begin(65535);w.end();return bytes(w.data)
 def materials(self):return [dict(control=0x93,rgba=[204,204,204,255],stages=[bytes(32),bytes(32)]),dict(control=0,rgba=[255]*4,stages=[bytes(32)])]
 def test_only_material_chunk_and_intentionally_unlit(self):
  raw=self.model();after=rewrite(raw,self.materials());a,b=chunks(raw),chunks(after)
  self.assertEqual(a[16],b[16]);self.assertEqual(a[65535],b[65535]);self.assertEqual(u32(b[48],120),2)
  start=32+156+124;self.assertEqual(u32(b[48],start+36),0x93)
  self.assertEqual(b[48][start+8:start+12],bytes([204,204,204,255]))
  self.assertEqual(u32(b[48],start+152+36),0)
  self.assertEqual(a[48][280+152:280+304],b[48][start+152:start+304])
 def test_unknown_source_rejected(self):
  with self.assertRaises(ValueError):profile(b'not a source model','Frog')
  with self.assertRaises(ValueError):profile(b'not a source model','Iwagen')
 def test_changed_baseline_and_count_rejected(self):
  with self.assertRaises(ValueError):rewrite(self.model(),self.materials()[:1])
  first=rewrite(self.model(),self.materials())
  with self.assertRaises(ValueError):rewrite(first,self.materials())
 def test_unsupported_channel_profile_rejected(self):
  materials=self.materials();materials[0]['control']=0xffff
  with self.assertRaises(ValueError):rewrite(self.model(),materials)

if __name__=='__main__':unittest.main()
