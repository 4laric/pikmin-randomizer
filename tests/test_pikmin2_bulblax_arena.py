import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experimental.pikmin2_bulblax_arena import (
    EXPECTED, SQUAD_BASE, placements, prepare, roster)
from experimental.pikmin2_bulblax_install import emit
from experimental.pikmin2_bulblax_visual import CONFIG, prepare as prepare_profile

COURSE_BYTES = b'original-practice-course'


def entry(kind=b'ikip', identity=1):
    row = bytearray(100)
    row[:8] = b'    0.0v'
    struct.pack_into('<I', row, 8, identity)
    row[72:76] = kind
    return bytes(row)


def bank_fixture(root):
    from experimental.pikmin2_bulblax_bank import HEADER, POLICIES
    from experimental.pikmin2_bulblax_assets import SPECIES
    motions = {species: {} for species in SPECIES}
    motions['Queen']['wait1'] = {'poses': 2, 'source_frames': 60, 'frames': [0, 59]}
    motions['Baby']['move'] = {'poses': 2, 'source_frames': 12, 'frames': [0, 11]}
    motions['KingChappy']['move1'] = {'poses': 2, 'source_frames': 80, 'frames': [0, 79]}
    root.mkdir(parents=True)
    files = {}
    for species, clips in motions.items():
        for name, info in clips.items():
            for index in range(info['poses']):
                rel = f'{species}/bulblax_{species}_{name}_{index:02}.mod'
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(f'{species}:{name}:{index}'.encode())
                files[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    report = {'schema': 1, 'bank': HEADER, 'reference_sha256': '0' * 64,
              'normal_policy': {s: dict(p) for s, p in POLICIES.items()},
              'motions': {s: {n: dict(m, mod_bytes=0) for n, m in clips.items()}
                          for s, clips in motions.items()},
              'unsupported': {s: [] for s in motions}, 'blocked': {s: [] for s in motions},
              'file_sha256': files, 'cost': {'poses': 6, 'mod_bytes': 0}, 'limitations': []}
    (root / 'bulblax-bank.json').write_text(json.dumps(report))
    (root / 'p2-bulblax-bank.txt').write_text(HEADER + '\n')
    return root


def profile_fixture(root):
    bank = bank_fixture(root / 'bank')
    manifest = emit(bank, [{'placement_id': i, 'species': s, 'clip': c, 'xyz': list(x)}
                           for i, s, c, x in EXPECTED])
    manifest_path = root / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest))
    profile = root / 'profile'
    prepare_profile(manifest_path, bank, profile)
    return profile


def fake_assets(root):
    (root / 'dataDir/stages/chal0').mkdir(parents=True)
    (root / 'dataDir/stages/practice').mkdir(parents=True)
    (root / 'dataDir/stages/practice.ini').write_bytes(b'practice-stage')
    (root / 'dataDir/stages/practice/default.gen').write_bytes(
        b'1.0v' + struct.pack('>4fI', 47, 30, 1919, 180, 1))
    course = root / 'dataDir/courses/practice'
    course.mkdir(parents=True)
    (course / 'keep.bin').write_bytes(COURSE_BYTES)
    return root


def fake_overlay(assets, destination, overrides):
    (destination / 'dataDir/stages/chal0').mkdir(parents=True)
    course = destination / 'dataDir/courses/practice'
    course.mkdir(parents=True)
    (course / 'keep.bin').write_bytes(COURSE_BYTES)
    (destination / 'dataDir/courses/pikmin2room').mkdir(parents=True)


class RosterTests(unittest.TestCase):
    def test_starting_squad_rows_and_colors(self):
        with tempfile.TemporaryDirectory() as d:
            assets = fake_assets(Path(d) / 'assets')
            with patch('experimental.pikmin2_bulblax_arena.records',
                       return_value=[entry(b'goal')]), \
                    patch('experimental.pikmin2_bulblax_arena.generator',
                          return_value=b'x' * 24 + entry()):
                data, ids = roster(assets)
            rows = [data[i:i + 100] for i in range(24, len(data), 100)]
            spawned = [r for r in rows if struct.unpack_from('<I', r, 8)[0] >= SQUAD_BASE]
            self.assertEqual(len(spawned), 10)
            self.assertEqual(len(set(ids)), 10)
            self.assertEqual([struct.unpack_from('>I', r, 92)[0] for r in spawned],
                             [1] * 5 + [0] * 5)
            self.assertFalse(any(r[72:76] in (b'iket', b'tlep') for r in rows))
            self.assertEqual(struct.unpack_from('>I', data, 20)[0], len(rows))

    def test_collision_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            assets = fake_assets(Path(d) / 'assets')
            with patch('experimental.pikmin2_bulblax_arena.records',
                       return_value=[entry(identity=SQUAD_BASE)]), \
                    patch('experimental.pikmin2_bulblax_arena.generator',
                          return_value=b'x' * 24 + entry()):
                with self.assertRaises(ValueError):
                    roster(assets)


class PlacementTests(unittest.TestCase):
    def test_recorded_display_placements_pass(self):
        with tempfile.TemporaryDirectory() as d:
            profile = profile_fixture(Path(d))
            result = placements(profile)
            self.assertEqual([r['placement_id'] for r in result],
                             [i for i, _, _, _ in EXPECTED])
            self.assertTrue(all(r['source_yaw'] is None for r in result))
            self.assertTrue(all(not r['source_yaw_applied'] for r in result))

    def test_tampered_profile_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            profile = profile_fixture(Path(d))
            meta = json.loads((profile / 'bulblax-visual.json').read_bytes())
            for mutate in (lambda m: m['placements'][0].__setitem__('species', 'Baby'),
                           lambda m: m['placements'][1].__setitem__('xyz', [0.0, 0.0, 0.0]),
                           lambda m: m['placements'].pop(),
                           lambda m: m.__setitem__('kind', 'other')):
                broken = json.loads(json.dumps(meta))
                mutate(broken)
                (profile / 'bulblax-visual.json').write_text(json.dumps(broken))
                with self.assertRaises(ValueError):
                    placements(profile)
                (profile / 'bulblax-visual.json').write_text(json.dumps(meta))


class PrepareTests(unittest.TestCase):
    def test_prepare_preserves_course_and_installs_display(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            assets = fake_assets(root / 'assets')
            profile = profile_fixture(root)
            with patch('experimental.pikmin2_bulblax_arena.overlay', fake_overlay), \
                    patch('experimental.pikmin2_bulblax_arena.records',
                          return_value=[entry(b'goal')]), \
                    patch('experimental.pikmin2_bulblax_arena.generator',
                          return_value=b'x' * 24 + entry()):
                run = prepare(assets, profile, root / 'output')
            result = json.loads((run / 'arena.json').read_bytes())
            self.assertEqual(result['schema'], 1)
            self.assertEqual(result['scene'], 'P1 Impact Site')
            self.assertEqual(len(result['actors']), 3)
            self.assertEqual(len(result['squad']['generators']), 10)
            self.assertEqual(len(result['placements']), 3)
            self.assertIn('display-only', result['gates']['native_identity'])
            self.assertEqual(result['gates']['combat'],
                             'blocked: source attacks/damage receivers are not registered')
            self.assertEqual(result['gates']['reload'], 'untested')
            self.assertTrue((run / CONFIG).is_file())
            room = run / 'assets/dataDir/courses/pikmin2room'
            self.assertEqual(len(list(room.glob('*.mod'))), 6)
            self.assertEqual((run / 'assets/dataDir/courses/practice/keep.bin').read_bytes(),
                             COURSE_BYTES)


if __name__ == '__main__':
    unittest.main()
