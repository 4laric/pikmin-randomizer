import copy,unittest
from unittest.mock import patch
from experimental.pikmin2_beasts_uji import roster
class RosterTests(unittest.TestCase):
 def fixture(self):
  content={'enemies':[{'definition_id':f'd{i}','source':{'enemy_id':s,'minimum_count':n}} for i,(s,n) in enumerate([('UjiB',4),('UjiA',2),('UjiA',2),('UjiA',2)])]}
  room={'vertices':[],'triangles':[],'spawns':[{'instance':2,'type':t,'position':[i*100,0,0],'angle':30,'min':1,'max':3,'radius':75} for t,count in [(1,6),(0,5)] for i in range(count)]}
  return content,room
 def test_counts_ids_offsets(self):
  c,r=self.fixture()
  with patch('experimental.pikmin2_beasts_uji.ground_height',return_value=0):a=roster(c,r)
  self.assertEqual(sum(x['species']=='UjiA' for x in a),6);self.assertEqual(len({x['instance_id'] for x in a}),10);self.assertEqual(len({x['generator'] for x in a}),10);self.assertEqual(sum(x['corpse_value'] for x in a),14)
  self.assertTrue(all(x['source_slot']['position']!=x['position'] for x in a if x['species']=='UjiA'))
 def test_wrong_counts(self):
  c,r=self.fixture();c['enemies'][0]['source']['minimum_count']=3
  with self.assertRaises(ValueError):roster(c,r)
 def test_missing_ground(self):
  c,r=self.fixture()
  with patch('experimental.pikmin2_beasts_uji.ground_height',return_value=None),self.assertRaises(ValueError):roster(c,r)
if __name__=='__main__':unittest.main()
