import math
import unittest
from experimental.pikmin2_groink_arena import profile_text


class GroinkArenaTests(unittest.TestCase):
    def test_profile_keeps_row_major_source_muzzle_and_explicit_target(self):
        matrix = [[1,0,0,7],[0,1,0,8],[0,0,1,9]]
        text = profile_text([10,20,30], [200,0,0], 0.5, matrix, 250, 15)
        self.assertIn('owner 10 20 30 0.5\ntarget 200 0 0\n', text)
        self.assertTrue(text.endswith('muzzle 1 0 0 7 0 1 0 8 0 0 1 9\n'))

    def test_profile_rejects_bad_coordinates_and_yaw(self):
        matrix = [[1,0,0,7],[0,1,0,8],[0,0,1,9]]
        for owner, yaw in (([math.nan,0,0],0), ([100001,0,0],0), ([0,0,0],7)):
            with self.assertRaises(ValueError):
                profile_text(owner,[1,2,3],yaw,matrix,250,15)
