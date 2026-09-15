import unittest
from experimental.pikmin2_qurione_material_compare import evidence
class CompareTests(unittest.TestCase):
 def log(self):
  return '\n'.join('P2_QURIONE_MATERIAL_COMPARE corrected='+str(i)+' pose=waitl_0 x='+str(-35 if i==0 else 35)+' y=0 z=0 scale=1 yaw=0 eye=0,80,300 target=0,20,0 ambient=50,50,50 fov=45 aspect=1.6' for i in (0,1))
 def test_pair(self):self.assertTrue(evidence(self.log())['fixed_pose_equal_depth'])
 def test_reject_unmatched(self):
  for log in ('',self.log().splitlines()[0],self.log().replace('x=35','x=36'),self.log().replace('corrected=1','corrected=0')):
   with self.assertRaises(ValueError):evidence(log)
if __name__=='__main__':unittest.main()
