import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
from experimental.pikmin2_breadbug_actor import actor_rows,plan,install
from experimental.pikmin2_breadbug_visual import sha

def actor(identity=77,kind=8):
    row=bytearray(81);struct.pack_into('<I',row,8,identity);row[72:76]=b'iket';row[80]=kind;return bytes(row)

class BreadbugActorTests(unittest.TestCase):
    def test_private_install_preserves_generator_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);profile=root/'profile';profile.mkdir();self.profile(profile)
            run=root/'run';room=run/'assets/dataDir/courses/pikmin2room';room.mkdir(parents=True)
            generator=run/'assets/dataDir/stages/chal0/default.gen';generator.parent.mkdir(parents=True);generator.write_bytes(b'original')
            with patch('experimental.pikmin2_breadbug_actor.records',return_value=[actor()]):
                result=install(profile,run,[77]);self.assertFalse(result['native_validated'])
                with self.assertRaises(ValueError):install(profile,run,[77])
            self.assertEqual(generator.read_bytes(),b'original')
    def test_only_existing_unique_collec_generators(self):
        self.assertEqual(actor_rows([actor()],[77]),['77 8'])
        for rows,ids in (([actor(kind=3)],[77]),([actor(),actor()],[77]),([actor()],[77,77]),([],[77])):
            with self.subTest(rows=rows,ids=ids),self.assertRaises(ValueError):actor_rows(rows,ids)
    def profile(self,root):
        (root/'models').mkdir();files={};clips=[]
        for name in ('wait','move'):
            clips.append(dict(name=name,source_duration=2,frames=[0,1]))
            for i in range(2):
                f=f'breadbug_{name}_{i:02}.mod';(root/'models'/f).write_bytes(b'pose');files[f]=sha(b'pose')
        data=dict(schema=1,family='PanModoki',behavior='visual_only_no_gameplay_actor',clips=clips,files=files)
        (root/'breadbug-visual.json').write_text(json.dumps(data));return data
    def test_config_exact_bytes_source_hashes_and_proxy_names(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.profile(root);config,files=plan(root,[actor()],[77])
            self.assertEqual(config,b'P2_BREADBUG_ACTOR_PROXY_1\nwait 2 2 0 1\nmove 2 2 0 1\n1\n77 8\n')
            self.assertEqual(len(files),4);self.assertTrue(all(k.startswith('breadbug_actor_') for k in files))
            (root/'models/breadbug_wait_00.mod').write_bytes(b'wrong')
            with self.assertRaises(ValueError):plan(root,[actor()],[77])
    def test_rejects_giant_and_incomplete_frame_endpoints(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);data=self.profile(root);data['family']='OoPanModoki';(root/'breadbug-visual.json').write_text(json.dumps(data))
            with self.assertRaises(ValueError):plan(root,[actor()],[77])
            data['family']='PanModoki';data['clips'][0]['frames']=[0,2];(root/'breadbug-visual.json').write_text(json.dumps(data))
            with self.assertRaises(ValueError):plan(root,[actor()],[77])
