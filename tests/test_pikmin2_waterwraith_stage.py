import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from experimental import pikmin2_waterwraith_stage as stage


def write_import(root, species_clips, policy='P2_WATERWRAITH_1'):
    """species_clips: {species: [(clip_name, [(frame, payload), ...]), ...]}"""
    species = {}
    for name, clips in species_clips.items():
        entry_clips = []
        for clip_name, poses in clips:
            converted = []
            for index, (frame, payload) in enumerate(poses):
                filename = f'ww_{name}_{clip_name}_{index:02d}.mod'
                (root / name).mkdir(parents=True, exist_ok=True)
                (root / name / filename).write_bytes(payload)
                converted.append({'file': filename, 'frame': frame,
                                  'sha256': hashlib.sha256(payload).hexdigest()})
            entry_clips.append({'name': clip_name, 'status': 'converted',
                                'source_frames': max(frame for frame, _ in poses) + 1,
                                'poses': converted})
        species[name] = {'enemy_id': {'BlackMan': 99, 'Tyre': 98}.get(name, 0),
                         'clips': entry_clips}
    (root / 'waterwraith.json').write_text(
        json.dumps({'policy': policy, 'species': species}) + '\n', encoding='utf-8')


def tiny_species():
    return {
        'BlackMan': [('kagebozu_walk', [(0, b'walk0'), (24, b'walk1')]),
                     ('kagebozu_dead', [(0, b'dead0')])],
        'Tyre': [('tyre_move', [(0, b'move0')])],
    }


class BuildTests(unittest.TestCase):
    def test_path_escape_is_rejected_before_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            imported = root / 'imported'
            imported.mkdir()
            write_import(imported, tiny_species())
            path = imported / 'waterwraith.json'
            report = json.loads(path.read_text())
            report['species']['BlackMan']['clips'][0]['poses'][0]['file'] = '../escape.mod'
            path.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, 'Unsafe pose filename'):
                stage.build(imported, root / 'stage', ['kagebozu_walk'])
            self.assertFalse((root / 'stage').exists())

    def test_profile_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            imported = root / 'imported'
            imported.mkdir()
            write_import(imported, tiny_species())
            out = root / 'stage'
            manifest = stage.build(imported, out,
                                   only_clips=['kagebozu_walk', 'tyre_move'])
            self.assertEqual(manifest['profile'], stage.HEADER)
            self.assertEqual(manifest['clips'], 2)
            self.assertEqual(manifest['poses'], 3)
            self.assertEqual(manifest['species']['BlackMan']['enemy_id'], 99)
            self.assertEqual(manifest['species']['BlackMan']['clips'], 1)
            self.assertEqual(manifest['species']['Tyre']['clips'], 1)
            profile = (out / 'p2-waterwraith-visual.txt').read_text(encoding='utf-8')
            self.assertTrue(profile.startswith(stage.HEADER + '\n'))
            self.assertIn('species BlackMan 99', profile)
            self.assertIn('clip BlackMan kagebozu_walk 2 25 0 24', profile)
            self.assertIn('species Tyre 98', profile)
            self.assertIn('clip Tyre tyre_move 1 1 0', profile)
            self.assertTrue((out / 'assets' / 'dataDir' / 'courses' / 'pikmin2room'
                             / 'ww_BlackMan_kagebozu_walk_00.mod').is_file())
            self.assertIn('p2-waterwraith-visual.txt', manifest['file_sha256'])

    def test_default_path_requires_all_clips(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            imported = root / 'imported'
            imported.mkdir()
            write_import(imported, tiny_species())
            with self.assertRaises(ValueError):
                stage.build(imported, root / 'stage')  # 3 != 16

    def test_unknown_clip_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            imported = root / 'imported'
            imported.mkdir()
            write_import(imported, tiny_species())
            with self.assertRaises(ValueError):
                stage.build(imported, root / 'stage', only_clips=['not_a_clip'])

    def test_hash_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            imported = root / 'imported'
            imported.mkdir()
            write_import(imported, tiny_species())
            (imported / 'BlackMan' / 'ww_BlackMan_kagebozu_walk_00.mod').write_bytes(b'tampered')
            with self.assertRaises(ValueError):
                stage.build(imported, root / 'stage', only_clips=['kagebozu_walk'])

    def test_wrong_policy_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            imported = root / 'imported'
            imported.mkdir()
            write_import(imported, tiny_species(), policy='P2_OTHER_1')
            with self.assertRaises(ValueError):
                stage.build(imported, root / 'stage', only_clips=['kagebozu_walk'])

    def test_output_exists_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            imported = root / 'imported'
            imported.mkdir()
            write_import(imported, tiny_species())
            out = root / 'stage'
            out.mkdir()
            with self.assertRaises(ValueError):
                stage.build(imported, out, only_clips=['kagebozu_walk'])

    def test_byte_budget_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            imported = root / 'imported'
            imported.mkdir()
            write_import(imported, tiny_species())
            previous = stage.MAX_STAGE_BYTES
            stage.MAX_STAGE_BYTES = 1
            try:
                with self.assertRaises(ValueError):
                    stage.build(imported, root / 'stage', only_clips=['kagebozu_walk'])
            finally:
                stage.MAX_STAGE_BYTES = previous

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            imported = root / 'imported'
            imported.mkdir()
            write_import(imported, tiny_species())
            self.assertEqual(stage.main(['--imported', str(imported),
                                         '--output', str(root / 'stage'),
                                         '--clips', 'tyre_move']), 0)
            self.assertTrue((root / 'stage' / 'stage.json').is_file())


if __name__ == '__main__':
    unittest.main()
