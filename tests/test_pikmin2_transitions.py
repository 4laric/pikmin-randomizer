from pathlib import Path
import tempfile
import unittest
import hashlib
import json
from experimental.pikmin2_transitions import read_transitions, read_visuals, install_visuals
from experimental.pikmin2_campaign import content_identity


class TransitionConfigTests(unittest.TestCase):
    def test_visual_bundle_is_frozen_verified_and_installed_privately(self):
        self.assertEqual(read_visuals(None), {})
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            models={}
            for kind in ('hole', 'geyser'):
                name=f'cave_{kind}.mod';data=kind.encode()
                (root/name).write_bytes(data)
                models[kind]=dict(file=name,sha256=hashlib.sha256(data).hexdigest(),
                                  placement=dict(y_offset=0,scale=1,yaw_degrees=0))
            manifest=dict(schema=1,models=models)
            path=root/'transition-assets.json'
            path.write_text(json.dumps(manifest))
            frozen=read_visuals(root)
            (root/'cave_hole.mod').write_bytes(b'changed')
            self.assertEqual(frozen['cave_hole.mod'],b'hole')
            with self.assertRaises(ValueError): read_visuals(root)
            run=root/'run';target=run/'assets/dataDir/courses/pikmin2room'
            target.mkdir(parents=True)
            install_visuals(frozen,run,1)
            self.assertEqual((target/'cave_hole.mod').read_bytes(),b'hole')
            self.assertEqual((run/'p2-cave-visual.txt').read_text(),'P2_CAVE_VISUAL_1 hole\n')
            with self.assertRaises(ValueError): install_visuals(frozen,run,1)
            with self.assertRaises(ValueError): install_visuals(frozen,run,3)
            (root/'cave_hole.mod').write_bytes(b'hole')
            for field,value in (('file','../cave_hole.mod'),('placement',dict(y_offset=1,scale=1,yaw_degrees=0))):
                changed=json.loads(json.dumps(manifest));changed['models']['hole'][field]=value
                path.write_text(json.dumps(changed))
                with self.assertRaises(ValueError): read_visuals(root)
            manifest['models'].pop('geyser');path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError): read_visuals(root)

    def test_coordinates_are_bound_to_save_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for unit in ('room_north_tutorial_1_snow', 'room_purple14x14_snow'):
                directory = root/'units'/unit
                directory.mkdir(parents=True)
                for name in ('render.mod', 'collision.json'): (directory/name).write_bytes(b'fixture')
            for name in ('manifest.json', 'pod.mod', 'treasure.mod', 'p2-pod.txt', 'p2-purple.txt'):
                (root/name).write_bytes(b'fixture')
            baseline = content_identity(root, [root,root], root)
            self.assertEqual(baseline, content_identity(root, [root,root], root, {}))
            marked = content_identity(root, [root,root], root, {1:b'hole at A'})
            moved = content_identity(root, [root,root], root, {1:b'hole at B'})
            self.assertNotEqual(baseline, marked)
            self.assertNotEqual(marked, moved)
            visual = content_identity(root, [root,root], root, visuals={'cave_hole.mod':b'first'})
            self.assertNotEqual(baseline, visual)
            self.assertNotEqual(visual, content_identity(root, [root,root], root, visuals={'cave_hole.mod':b'second'}))
            snow = root/'snow'
            snow.mkdir()
            for name in ('snow.json', 'p2-snow.txt', 'snow_wait_00.mod'):
                (snow/name).write_bytes(b'original')
            enabled = content_identity(root, [root,root], root, snow=snow)
            self.assertNotEqual(baseline, enabled)
            for name in ('snow.json', 'p2-snow.txt', 'snow_wait_00.mod'):
                with self.subTest(snow_asset=name):
                    (snow/name).write_bytes(b'changed')
                    self.assertNotEqual(enabled, content_identity(root, [root,root], root, snow=snow))
                    (snow/name).write_bytes(b'original')

    def test_absent_and_frozen_configuration(self):
        self.assertEqual(read_transitions(None), {})
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for floor, kind in ((1, 'hole'), (2, 'geyser')):
                (directory/f'floor{floor}.txt').write_bytes(f'P2_CAVE_TRANSITION_1 {kind} 1 2 3 50\n'.encode())
            frozen = read_transitions(directory)
            (directory/'floor1.txt').write_text('changed')
            self.assertEqual(frozen[1], b'P2_CAVE_TRANSITION_1 hole 1 2 3 50\n')

    def test_incomplete_or_invalid_layout_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            with self.assertRaises(FileNotFoundError): read_transitions(directory)
            (directory/'floor2.txt').write_text('P2_CAVE_TRANSITION_1 geyser 0 0 0 50')
            for value in ('P2_CAVE_TRANSITION_1 geyser 0 0 0 50',
                          'P2_CAVE_TRANSITION_1 hole nan 0 0 50',
                          'P2_CAVE_TRANSITION_1 hole 0 0 0 151',
                          'P2_CAVE_TRANSITION_1 hole 0 100001 0 50',
                          'P2_CAVE_TRANSITION_1 hole 0 0 0 50 junk'):
                (directory/'floor1.txt').write_text(value)
                with self.subTest(value=value), self.assertRaises(ValueError): read_transitions(directory)
