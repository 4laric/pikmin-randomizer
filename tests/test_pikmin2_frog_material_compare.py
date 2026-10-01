import unittest
from experimental.pikmin2_frog_material_compare import matched_evidence,instrument

class ComparisonTests(unittest.TestCase):
 def log(self):return '\n'.join(f'P2_FROG_MATERIAL_COMPARE kind={k} corrected={c} pose=wait1_0 scale=1 yaw=0 eye=0,80,500 target=0,20,0 x={-75+100*k+50*c} ambient=70,60,70 fov=23 aspect=1.6' for k in range(2) for c in range(2))
 def test_matched_cases(self):self.assertTrue(matched_evidence(self.log())['shared_ambient'])
 def test_reject_changed_scale_light_or_missing_case(self):
  for text in (self.log().replace('scale=1','scale=2',1),self.log().replace('ambient=70,60,70','ambient=1,2,3',1),self.log().split('\n',1)[1]):
   with self.assertRaises(ValueError):matched_evidence(text)
 def test_native_anchor_changed(self):
  with self.assertRaises(ValueError):instrument('not the copied family source')

if __name__=='__main__':unittest.main()
