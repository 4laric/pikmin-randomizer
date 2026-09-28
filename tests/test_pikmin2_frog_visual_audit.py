import struct,unittest
from experimental.pikmin2_convert import Writer
from experimental.pikmin2_frog_visual_audit import chunks,vertices,bounds,emitted_material

class AuditTests(unittest.TestCase):
 def model(self):
  w=Writer();w.begin(16,2);w.pad();w.put('6f',-1,2,3,4,5,6);w.end();w.begin(65535);w.end();return bytes(w.data)
 def test_vertices_and_footer_boundary(self):
  raw=self.model();self.assertEqual(bounds(vertices(raw)),[-1,2,3,4,5,6])
  with self.assertRaises(ValueError):vertices(raw+b'// source export footer')
  self.assertEqual(vertices(raw,True),vertices(raw+b'// source export footer',True))
  with self.assertRaises(ValueError):vertices(raw+b'garbage',True)
 def test_truncation_and_nan(self):
  raw=self.model()
  with self.assertRaises(ValueError):chunks(raw[:-1])
  changed=bytearray(raw);struct.pack_into('>f',changed,32,float('nan'))
  with self.assertRaises(ValueError):vertices(changed)
 def test_lighting_flag_is_not_vertex_material_source(self):
  w=Writer();w.begin(48,1,1);w.pad();w.data+=bytes(124+152);w.end();w.begin(65535);w.end();raw=w.data
  struct.pack_into('>I',raw,120,1);struct.pack_into('>I',raw,156,257);raw[164:168]=bytes([255]*4)
  struct.pack_into('>I',raw,192,0x1800)
  parsed=emitted_material(raw)[0];self.assertFalse(parsed['diffuse_enabled']);self.assertFalse(parsed['specular_enabled'])
  struct.pack_into('>I',raw,192,0x11);self.assertTrue(emitted_material(raw)[0]['diffuse_enabled'])
  struct.pack_into('>I',raw,120,2)
  with self.assertRaises(ValueError):emitted_material(raw)

if __name__=='__main__':unittest.main()
