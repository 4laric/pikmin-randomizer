import json
from pathlib import Path
import tempfile
import unittest
from experimental.pikmin2_breadbug_visual import placements_text,read_verified,install,sha
class BreadbugVisualTests(unittest.TestCase):
    def test_placements_strict_and_separate_from_generator(self):
        row=dict(display_id=1,kind='wait',position=[1,2,3],yaw_degrees=90)
        self.assertEqual(placements_text([row]),['1 wait 1 2 3 90'])
        for rows in ([row,row],[dict(row,kind='OoPanModoki')],[dict(row,position=[0,float('nan'),0])],[dict(row,yaw_degrees=400)]):
            with self.assertRaises(ValueError):placements_text(rows)
    def test_hash_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'data';p.write_bytes(b'a')
            self.assertEqual(read_verified(p,sha(b'a')),b'a')
            with self.assertRaises(ValueError):read_verified(p,sha(b'b'))
    def test_install_validates_all_before_writes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);profile=root/'profile';(profile/'models').mkdir(parents=True)
            run=root/'run';room=run/'assets/dataDir/courses/pikmin2room';room.mkdir(parents=True)
            config=b'example';(profile/'p2-breadbug-visual.txt').write_bytes(config)
            metadata=dict(schema=1,behavior='visual_only_no_gameplay_actor',config_sha256=sha(config),files={'breadbug_wait_00.mod':sha(b'pose')})
            (profile/'breadbug-visual.json').write_text(json.dumps(metadata));(profile/'models/breadbug_wait_00.mod').write_bytes(b'wrong')
            with self.assertRaises(ValueError):install(profile,run)
            self.assertEqual(list(room.iterdir()),[]);self.assertFalse((run/'p2-breadbug-visual.txt').exists())
            (profile/'models/breadbug_wait_00.mod').write_bytes(b'pose');install(profile,run)
            with self.assertRaises(ValueError):install(profile,run)
