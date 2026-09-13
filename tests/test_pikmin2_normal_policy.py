import copy,unittest,math
from experimental.pikmin2_rigid import bake,apply
from experimental.pikmin2_convert import decode
I=[[1,0,0,0],[0,1,0,0],[0,0,1,0]]
class NormalTests(unittest.TestCase):
 def data(self):return {9:[(0,0,0),(2,0,0),(0,2,0)],10:[]},[[[{0:0,9:i} for i in range(3)]]]
 def test_strict_default(self):
  a,s=self.data()
  with self.assertRaisesRegex(ValueError,'Missing'):bake(a,s,[I])
 def test_compute_and_default(self):
  for policy,normal in [('compute',(0,0,1)),('default',(0,1,0))]:
   a,s=self.data();bake(a,s,[I],missing_normals=policy);self.assertEqual(a[10],[normal]*3)
 def test_area_weighting_shared_corner(self):
  a={9:[(0,0,0),(2,0,0),(0,2,0),(0,0,1)],10:[]};origin={0:0,9:0};s=[[[origin,{0:0,9:1},{0:0,9:2}],[origin,{0:0,9:3},{0:0,9:1}]]]
  bake(a,s,[I],missing_normals='compute');n=a[10][s[0][0][0][10]];self.assertAlmostEqual(n[1],2/math.sqrt(20));self.assertAlmostEqual(n[2],4/math.sqrt(20));self.assertNotIn(0,origin)
 def test_uv_seam_separates(self):
  a={9:[(0,0,0),(1,0,0),(0,1,0),(0,0,1)],10:[]};s=[[[{0:0,9:i,13:0} for i in (0,1,2)],[{0:0,9:i,13:1} for i in (0,3,1)]]];bake(a,s,[I],missing_normals='compute');self.assertNotEqual(s[0][0][0][10],s[0][1][0][10])
 def test_degenerate_fails(self):
  a,s=self.data();a[9]=[(0,0,0)]*3
  with self.assertRaisesRegex(ValueError,'degenerate'):bake(a,s,[I],missing_normals='compute')
 def test_rank_two_cofactor(self):
  m=[[1,0,0,0],[0,1,0,0],[0,0,0,0]]
  with self.assertRaises(ValueError):apply(m,(0,0,1),True)
  self.assertEqual(apply(m,(0,0,1),True,singular_normal='transpose-adjugate'),(0,0,1))
  with self.assertRaisesRegex(ValueError,'annihilates'):apply(m,(1,0,0),True,singular_normal='transpose-adjugate')
 def test_explicit_collapsed_normal_policy(self):
  collapsed=[[0,0,0,0],[0,0,0,0],[0,0,0,0]]
  with self.assertRaisesRegex(ValueError,'annihilates'):
   apply(collapsed,(0,1,0),True,singular_normal='transpose-adjugate')
  self.assertEqual(apply(collapsed,(0,1,0),True,singular_normal='transpose-adjugate-zero'),(0,0,0))
  self.assertEqual(apply(I,(0,1,0),True,singular_normal='transpose-adjugate-zero'),(0,1,0))
  a={9:[(0,0,0),(1,0,0),(0,1,0)],10:[(0,1,0)]}
  s=[[[{0:0,9:i,10:0} for i in range(3)]]]
  bake(a,s,[collapsed],singular_normal='transpose-adjugate-zero')
  self.assertEqual(a[10],[(0,0,0)])
 def test_policy_validation(self):
  with self.assertRaises(ValueError):decode(b'',missing_normals='compute')
  with self.assertRaises(ValueError):decode(b'',bake_rigid=True,missing_normals='guess')
if __name__=='__main__':unittest.main()
