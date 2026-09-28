import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experimental.pikmin2_sarai_assets import frames_for, extract

ISO = Path('C:/Users/alari/pikmin-randomizer/assets/disc/PIKMIN2 for GAMECUBE.iso')
MOUTH_JOINTS = ('rkamujnt', 'lkamujnt')
CLIP_FILES = {'wait1.bca', 'move1.bca', 'attack1.bca', 'waitact2.bca', 'waitact1.bca',
              'flick.bca', 'type1.bca', 'type2.bca', 'type3.bca', 'type4.bca',
              'dead.bca', 'type5.bca'}


class SaraiAssetUnitTests(unittest.TestCase):
    def test_capture_and_event_frames(self):
        self.assertEqual(frames_for(50, [[13, 2], [50, 1000]]), [0, 10, 13, 16, 17, 30, 49])
        self.assertEqual(frames_for(1, []), [0])

    def test_invalid_and_budget(self):
        for duration, events in [(0, []), (5, [[6, 2]]), (100, [[i, 2] for i in range(40)])]:
            with self.assertRaises(ValueError):
                frames_for(duration, events)

    def test_existing_output_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root/'marker'
            marker.write_bytes(b'preserve')
            with patch('experimental.pikmin2_sarai_assets.disc_files', return_value={}):
                with self.assertRaises(FileExistsError):
                    extract(Path('unused.iso'), root)
            self.assertEqual(marker.read_bytes(), b'preserve')


@unittest.skipUnless(ISO.exists(), 'Requires the local retail disc image')
class SaraiRetailExtractionTests(unittest.TestCase):
    def test_schema_mouths_hashes_and_pose_bank(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'sarai'
            result = extract(ISO, output)
            document = json.loads((output/'sarai.json').read_text(encoding='utf-8'))
            self.assertEqual(document, result)
            self.assertEqual(document['schema'], 1)
            self.assertEqual(document['species'], 'Sarai')
            self.assertEqual(document['enemy_id'], 23)
            self.assertFalse(document['native_ready'])

            self.assertRegex(document['model_sha256'], r'^[0-9a-f]{64}$')
            self.assertEqual(hashlib.sha256((output/'enemy.bmd').read_bytes()).hexdigest(),
                             document['model_sha256'])
            for source in ('enemy/data/Sarai/model.szs', 'enemy/data/Sarai/anim.szs', 'enemy/parm/enemyParms.szs'):
                self.assertRegex(document['source_sha256'][source], r'^[0-9a-f]{64}$')

            self.assertEqual([name for name in MOUTH_JOINTS if document['joints'].count(name) == 1],
                             list(MOUTH_JOINTS))
            self.assertEqual({clip['file'] for clip in document['clips']}, CLIP_FILES)
            self.assertTrue(document['parameters'])

            for clip in document['clips']:
                self.assertEqual(clip['status'], 'converted', clip.get('reason'))
                self.assertTrue(clip['poses'])
                self.assertLessEqual(len(clip['poses']), 32)
                for pose in clip['poses']:
                    self.assertEqual([mouth['joint'] for mouth in pose['mouths']], list(MOUTH_JOINTS))
                    self.assertTrue((output/pose['file']).exists())
                    self.assertTrue((output/pose['file'].replace('.mod', '.json')).exists())
                    for mouth in pose['mouths']:
                        self.assertEqual(mouth['radius'], 15)
                        matrix = mouth['matrix']
                        self.assertEqual(len(matrix), 3)
                        for row in matrix:
                            self.assertEqual(len(row), 4)
                            self.assertTrue(all(math.isfinite(v) for v in row))


if __name__ == '__main__':
    unittest.main()
