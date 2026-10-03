import importlib.util,unittest
from pathlib import Path
_spec=importlib.util.spec_from_file_location("white_deposit_driver",Path(__file__).resolve().parents[1]/"scripts/run_p2_white_campaign.py")
r=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(r)
class Backend:
 def __init__(self):self.calls=[]
 def verify(self):self.calls.append(('verify',))
 def key(self,key,pressed):self.calls.append((key,pressed))
class Controls(unittest.TestCase):
 def setUp(self):self.b=Backend();self.time=0;self.p=r.ShipKeyProtocol(self.b,lambda:self.time,phase_budget=240)
 def request(self,seq=1,key='SHIFT_F10'):self.p.line(f'P2_WHITE_NATIVE_KEY_REQUEST seq={seq} key={key} actual_SDL_keyboard_required=1')
 def deposit(self,stock):self.p.line(f'P2_SHIP_DEPOSIT species=4 maturity=0 stored={stock}')
 def test_partial14_then_eligible_retry_last1(self):
  self.request()
  for stock in range(1,15):self.deposit(stock)
  self.assertEqual(self.p.deposit_stock,14);self.assertIsNone(self.p.pending)
  self.request(2);self.deposit(15);self.assertEqual(self.p.deposit_stock,15)
  self.assertEqual([e['sequence'] for e in self.p.effects],[1,2])
  self.assertEqual(self.b.calls[-3:],[('F10',False),('CTRL',False),('SHIFT',False)])
 def test_onebulk15_and_no_extra_press(self):
  self.request()
  for stock in range(1,16):self.deposit(stock)
  with self.assertRaises(ValueError):self.request(2)
 def test_no_effect_overlap_refuses(self):
  self.request()
  with self.assertRaises(ValueError):self.request(2)
 def test_sequence_skip_refuses(self):
  self.request();self.deposit(1)
  with self.assertRaises(ValueError):self.request(3)
 def test_duplicate_native_effect_refuses(self):
  self.request();self.deposit(1)
  with self.assertRaises(ValueError):self.deposit(1)
 def test_jump_native_effect_refuses(self):
  self.request()
  with self.assertRaises(ValueError):self.deposit(2)
 def test_unrequested_native_effect_refuses(self):
  with self.assertRaises(ValueError):self.deposit(1)
 def test_timeout_remains_two_seconds(self):
  self.request();self.time=2.01
  with self.assertRaises(ValueError):self.p.tick()
 def test_selected240_fence_preserved(self):
  self.request();self.deposit(1);self.time=240
  with self.assertRaises(ValueError):self.request(2)
 def test_resume_key_protocol_unchanged(self):
  self.p=r.ShipKeyProtocol(self.b,lambda:self.time,resume=True,phase_budget=60)
  self.request(1,'CTRL_F10');self.p.line('P2_SHIP_CHOICE captain=0 species=4')
  self.request(2,'F10');self.p.line('P2_SHIP_WITHDRAW species=4 maturity=0 stored=14')
  self.assertIsNone(self.p.pending)
  with self.assertRaises(ValueError):self.request(3,'SHIFT_F10')
if __name__=='__main__':unittest.main()
