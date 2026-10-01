import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import experimental.pikmin2_fuefuki_motion as motion

CLIPS = ('dead', 'landing', 'landfail', 'move', 'pivot',
         'wait', 'whisle', 'struggle', 'jump', 'carry')


def make_dir(root):
    rows = [{'file': name + '.bca', 'events': [[10, 2], [20, 3]]} for name in CLIPS]
    for clip in CLIPS:
        data = bytearray(72)
        data[40] = 2  # loop attribute
        (root / (clip + '.bca')).write_bytes(bytes(data))
    (root / 'enemyanimmgr.txt').write_bytes(b'stub')
    return rows


class FuefukiMotionTests(unittest.TestCase):
    def test_encode_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            rows = make_dir(directory)
            with patch.object(motion, 'parse_anim_mgr', return_value={'clips': rows}), \
                 patch.object(motion, 'bca_pose', return_value=(60, [])):
                out = motion.encode(directory)
            lines = out.decode().splitlines()
            header = lines[0].split()
            self.assertEqual(header[0], 'P2_RETAIL_EVENTS_1')
            self.assertEqual(header[2], '10')
            self.assertEqual(lines[1].split()[0], 'dead.bca')
            self.assertEqual(lines[1].split()[1], '60')  # duration
            self.assertEqual(lines[1].split()[2], '2')   # attribute
            self.assertEqual(lines[1].split()[4], '2')   # event count
            self.assertEqual(lines[2], '10 2')
            self.assertEqual(lines[3], '20 3')

    def test_reject_wrong_clip_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            rows = make_dir(directory)
            with patch.object(motion, 'parse_anim_mgr', return_value={'clips': rows[:9]}), \
                 patch.object(motion, 'bca_pose', return_value=(60, [])):
                with self.assertRaises(ValueError):
                    motion.encode(directory)

    def test_reject_missing_clip_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            rows = make_dir(directory)
            (directory / 'dead.bca').unlink()
            with patch.object(motion, 'parse_anim_mgr', return_value={'clips': rows}), \
                 patch.object(motion, 'bca_pose', return_value=(60, [])):
                with self.assertRaises(ValueError):
                    motion.encode(directory)


if __name__ == '__main__':
    unittest.main()
