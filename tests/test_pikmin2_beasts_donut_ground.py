import unittest
from experimental.pikmin2_beasts_donut_ground import validate_queries

class GroundQueryTests(unittest.TestCase):
    def log(self):
        rows=[(1,20.5),(0,-98765),(1,20.5),(1,12.7537),(0,-98765),(0,-98765),(1,0),(0,-98765)]
        return '\n'.join(f'P2_DONUT_GROUND_CASE id={i} found={f} height={h}' for i,(f,h) in enumerate(rows))+'\nP2_DONUT_WALL x=185.53261 y=44.99944 z=34.57631 front=5.00001\nP2_DONUT_GROUND_QUERY bounded=8 overhead_rejected=1 wall_blocked=1\n'
    def test_matched_queries_and_wall(self):
        self.assertEqual(validate_queries(self.log())['cases'],8)
    def test_rejects_wrong_contact_height_and_wall(self):
        for old,new in [('id=0 found=1 height=20.5','id=0 found=1 height=119.781'),('id=5 found=0','id=5 found=1'),('height=-98765','height=0'),('front=5.00001','front=4'),('front=5.00001','front=nan'),('wall_blocked=1','wall_blocked=0'),('id=7','id=6')]:
            with self.subTest(old=old,new=new):
                with self.assertRaises(ValueError):validate_queries(self.log().replace(old,new))
