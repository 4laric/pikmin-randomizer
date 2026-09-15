import struct,unittest
from experimental.pikmin2_qurione_material_audit import entry,tev_rgb
class QurioneMaterialTests(unittest.TestCase):
 def test_source_pink_cannot_be_flat_white(self):
  self.assertEqual(tev_rgb([255,50,200,255],[255]*4),[255.,100.,255.])
  self.assertEqual(tev_rgb([226,226,226,255],[255]*4),[255.]*3)
 def test_dark_raster_preserves_tint(self):
  self.assertEqual(tev_rgb([255,50,200,255],[0,0,0,255]),[0.,0.,0.])
  self.assertLess(tev_rgb([255,50,200,255],[128]*4)[1],128)
 def test_bad_inputs(self):
  for c in ([256,0,0,0],[-1,0,0,0],[1,2,3],[True,0,0,0]):
   with self.assertRaises(ValueError):tev_rgb(c,[255]*4)
  with self.assertRaises(ValueError):entry(bytes(140),32,0,4)
 def test_table_bounds(self):
  m=bytearray(140);struct.pack_into('>I',m,32,136)
  self.assertEqual(entry(m,32,0,4),bytes(4))
  with self.assertRaises(ValueError):entry(m,32,1,4)
if __name__=='__main__':unittest.main()
