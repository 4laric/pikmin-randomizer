import struct,unittest
from experimental.pikmin2_qurione_material_patch import patch,descriptor
from experimental.pikmin2_convert import Writer
class QurionePatchTests(unittest.TestCase):
 def fixture(self):
  w=Writer();w.begin(48,2,2);w.pad()
  for _ in range(2):
   for _ in range(3):w.put('4hIfII',255,255,255,255,0,0.,0,0)
   w.data+=bytes([255])*16;w.put('I',1);w.data+=bytes([0,255,255,4,0,0,0,0]);w.data+=bytes([15,15,15,10,0,0,0,1,0,0,0,0]);w.data+=bytes([7,7,7,5,0,0,0,1,0,0,0,0])
  w.end();w.begin(16,1);w.pad();w.put('3f',1,2,3);w.end()
  rows=[dict(shape=i,material=i,register0=c,color=[15,2,10,15,0,0,1,1,0],alpha=[7,1,5,7,0,0,0,1,0] if i==0 else [5,7,7,7,0,0,0,1,0]) for i,c in enumerate(([226,226,226,255],[255,50,200,255]))]
  return bytes(w.data),rows
 def test_only_material_ranges(self):
  raw,rows=self.fixture();out=patch(raw,rows);self.assertEqual(len(raw),len(out));self.assertEqual(raw[280:],out[280:])
  self.assertEqual(struct.unpack_from('>4h',out,32),(226,226,226,255));self.assertEqual(struct.unpack_from('>4h',out,156),(255,50,200,255))
  allowed={j for start in (32,156) for lo,hi in ((0,8),(100,109),(112,121)) for j in range(start+lo,start+hi)}
  self.assertTrue(all(a==b or i in allowed for i,(a,b) in enumerate(zip(raw,out))))
 def test_reject_repeat_or_bad_source(self):
  raw,rows=self.fixture()
  with self.assertRaises(ValueError):patch(patch(raw,rows),rows)
  with self.assertRaises(ValueError):descriptor(b'unknown')
  with self.assertRaises(ValueError):patch(raw[:-1],rows)
 def test_reject_unknown_formula(self):
  raw,rows=self.fixture();rows[0]['color'][6]=0
  with self.assertRaises(ValueError):patch(raw,rows)
if __name__=='__main__':unittest.main()
