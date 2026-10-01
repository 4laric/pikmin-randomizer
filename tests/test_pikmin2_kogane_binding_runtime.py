import unittest
from pathlib import Path
from experimental.pikmin2_kogane_binding_runtime import validate,instrument
class BindingTests(unittest.TestCase):
 def test_missing_is_not_success(self):self.assertFalse(validate('',0)['passed'])
 def test_typed_control_gate(self):
  rows='\n'.join(f'P2_KOGANE_ID id={219001+i} source_id={s} control={int(s<0)}' for i,s in enumerate((9,10,11,-1)))
  text=rows+'\nP2_KOGANE_DRAW corpse=0\nPASS P2_KOGANE_RUNTIME'
  self.assertTrue(validate(text,0)['passed']);self.assertFalse(validate(text.replace('source_id=10','source_id=9'),0)['passed']);self.assertFalse(validate(text,1)['passed'])
 def test_instrument_real_source(self):
  root=Path(__file__).resolve().parents[1];s=instrument((root/'engine/tools/preview_p2_room.cpp').read_text());self.assertIn('pc_p2_kogane_source_id(actor)==expected',s);self.assertIn('kogane-binding.ppm',s)
if __name__=='__main__':unittest.main()
