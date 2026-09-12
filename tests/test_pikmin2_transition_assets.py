import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from experimental.pikmin2_transition_assets import bind_pose, extract, SOURCES


class TransitionAssetTests(unittest.TestCase):
    def test_bind_pose_bakes_scale_and_translation(self):
        joint=bytearray(96)
        struct.pack_into('>H',joint,8,1);struct.pack_into('>I',joint,12,32)
        struct.pack_into('>3f',joint,36,1,1.163055,1)
        struct.pack_into('>3f',joint,56,0,7,0)
        with patch('experimental.pikmin2_transition_assets.blocks',return_value={'JNT1':joint}):
            pose=bind_pose(b'')
            self.assertAlmostEqual(pose[0][1][1],1.163055,6)
            self.assertEqual(pose[0][1][3],7)
            joint[34]=1
            with self.assertRaises(ValueError):bind_pose(b'')
            joint[34]=0;struct.pack_into('>f',joint,36,0)
            with self.assertRaises(ValueError):bind_pose(b'')

    def test_import_contract_hashes_models_and_refuses_reuse(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);iso=root/'disc';iso.write_bytes(b'ab')
            paths=list(SOURCES);catalog={SOURCES[k][0]:(i,1) for i,k in enumerate(paths)}
            def archive(data):return {SOURCES[paths[data[0]-97]][1]:b'model'}
            def convert(source,target,kind):
                target.write_bytes(kind.encode());return {'bounds':[0]*6,'hidden_source_joints':['flag'] if kind=='hole' else []}
            with patch('experimental.pikmin2_transition_assets.disc_files',return_value=catalog),patch('experimental.pikmin2_transition_assets.archive_files',side_effect=archive),patch('experimental.pikmin2_transition_assets.convert_visible',side_effect=convert):
                a=extract(iso,root/'one');b=extract(iso,root/'two')
                self.assertEqual(a,b)
                self.assertEqual(a['models']['hole']['file'],'cave_hole.mod')
                self.assertEqual(a['models']['geyser']['placement'],dict(y_offset=0,scale=1,yaw_degrees=0))
                self.assertEqual(a['models']['hole']['hidden_source_joints'],['flag'])
                with self.assertRaises(FileExistsError):extract(iso,root/'one')
                catalog[SOURCES['hole'][0]]=(0,3)
                with self.assertRaisesRegex(ValueError,'Truncated'):extract(iso,root/'bad')
