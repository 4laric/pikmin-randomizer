import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from experimental.pikmin2_breadbug_visual import placements_text,read_verified,install,sha,prepare
class BreadbugVisualTests(unittest.TestCase):
    def test_prepared_config_exact_bytes_match_recorded_hash(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'source';(source/'PanModoki').mkdir(parents=True);(source/'PanHouse').mkdir()
            (source/'PanModoki/enemy.bmd').write_bytes(b'model');(source/'PanHouse/nest.mod').write_bytes(b'nest')
            clips=[]
            for name in ('wait1.bca','move1.bca'):
                (source/'PanModoki'/name).write_bytes(b'motion');clips.append(dict(file=name,sha256=sha(b'motion')))
            data=dict(schema=1,species=dict(PanModoki=dict(model_sha256=sha(b'model'),joints=['joint'],clips=clips),PanHouse=dict(static_pose=dict(file='nest.mod',sha256=sha(b'nest')))))
            (source/'breadbugs.json').write_text(json.dumps(data))
            def fake_convert(model,target,*args,**kwargs):target.write_bytes(b'pose')
            with patch('experimental.pikmin2_breadbug_visual.bca_pose',return_value=(2,None)),patch('experimental.pikmin2_breadbug_visual.convert',side_effect=fake_convert):
                result=prepare(source,root/'profile',[dict(display_id=1,kind='wait',position=[0,0,0],yaw_degrees=0)],2)
            raw=(root/'profile/p2-breadbug-visual.txt').read_bytes()
            self.assertNotIn(b'\r',raw);self.assertEqual(sha(raw),result['config_sha256'])
            self.assertEqual(raw,b'P2_BREADBUG_VISUAL_1\nwait 2 2 0 1\nmove 2 2 0 1\n1\n1 wait 0 0 0 0\n')
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
