from pathlib import Path
import tempfile
import unittest
from experimental.pikmin2_transitions import read_transitions
from experimental.pikmin2_campaign import content_identity


class TransitionConfigTests(unittest.TestCase):
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
