import json
from pathlib import Path
import tempfile
import unittest
from experimental.pikmin2_beasts_fixture import placements, prepare, WALK


class FixtureTests(unittest.TestCase):
    def test_missing_ground_rejected(self):
        with self.assertRaises(ValueError): placements({'vertices': [], 'triangles': []})

    def test_walk_crosses_both_seams_in_order(self):
        self.assertEqual([x for x,z in WALK], sorted(x for x,z in WALK))
        self.assertTrue(WALK[0][0] < 425 < 595 < WALK[-1][0])

    def test_wrong_provenance_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'assembly.json').write_text(json.dumps({'schema':1,'cave':'tutorial_1','assembled':True}))
            with self.assertRaises(ValueError): prepare(root,root,root,root/'run')

    def test_changed_geometry_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'assembly.json').write_text(json.dumps({'schema':1,'cave':'forest_1','assembled':True,'output_sha256':{'room.mod':'bad'}}))
            (root/'room.mod').write_bytes(b'changed')
            with self.assertRaises(ValueError): prepare(root,root,root,root/'run')


if __name__ == '__main__': unittest.main()
