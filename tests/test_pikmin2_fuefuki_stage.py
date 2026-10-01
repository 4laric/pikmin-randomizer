import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experimental.pikmin2_fuefuki_stage import HEADER, MOTION_FILE, build


def make_import(root):
    (root / 'Fuefuki').mkdir(parents=True)
    clips = []
    for name, duration, frames in (('wait', 30, [0, 10, 20]),
                                   ('whisle', 34, [0, 12, 24]),
                                   ('move', 20, [0, 10])):
        poses = []
        for index, frame in enumerate(frames):
            filename = f'fuefuki_Fuefuki_{name}_{index:02}.mod'
            data = bytes([index]) * 32
            (root / 'Fuefuki' / filename).write_bytes(data)
            poses.append({'file': filename, 'frame': frame,
                          'sha256': hashlib.sha256(data).hexdigest()})
        clips.append({'name': name, 'source_frames': duration, 'status': 'converted',
                      'poses': poses})
    clips.append({'name': 'landing', 'source_frames': 60, 'status': 'unsupported',
                  'poses': [{'frame': 0, 'unsupported_reason': 'singular scale'}]})
    (root / 'fuefuki.json').write_text(json.dumps(
        {'policy': 'P2_FUEFUKI_IMPORT_1', 'species': {'Fuefuki': {'clips': clips}}}))
    return root


class FuefukiStageTests(unittest.TestCase):
    def test_stage_writes_profile_and_poses(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = make_import(Path(tmp) / 'import')
            output = Path(tmp) / 'stage'
            events = b'P2_RETAIL_EVENTS_1 ' + b'a' * 64 + b' 10\n'
            with patch('experimental.pikmin2_fuefuki_stage.motion.encode',
                       return_value=events):
                manifest = build(imported, output)
            self.assertEqual(manifest['profile'], HEADER)
            self.assertEqual(manifest['motion_file'], MOTION_FILE)
            self.assertTrue((output / MOTION_FILE).is_file())
            self.assertEqual(manifest['clips'], 3)
            self.assertEqual(manifest['poses'], 8)
            self.assertEqual(manifest['unsupported_clips'], ['landing'])
            profile = (output / 'p2-fuefuki-visual.txt').read_text()
            lines = profile.splitlines()
            self.assertEqual(lines[0], HEADER)
            self.assertIn('clip wait 3 30 0 10 20', lines)
            self.assertIn('clip whisle 3 34 0 12 24', lines)
            self.assertNotIn('landing', profile)
            self.assertTrue((output / 'assets' / 'dataDir' / 'courses' / 'pikmin2room'
                             / 'fuefuki_Fuefuki_wait_00.mod').is_file())

    def test_reject_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = make_import(Path(tmp) / 'import')
            output = Path(tmp) / 'stage'
            output.mkdir()
            with self.assertRaises(ValueError):
                build(imported, output)

    def test_reject_wrong_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            imported = make_import(Path(tmp) / 'import')
            report = json.loads((imported / 'fuefuki.json').read_text())
            report['policy'] = 'SOMETHING_ELSE'
            (imported / 'fuefuki.json').write_text(json.dumps(report))
            with self.assertRaises(ValueError):
                build(imported, Path(tmp) / 'stage')


if __name__ == '__main__':
    unittest.main()
