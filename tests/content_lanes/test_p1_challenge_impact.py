"""Focused P0 tests for the P1 Challenge Impact import contract (issue #565).

Synthetic asset trees only; malformed/missing-input boundaries plus identity
sync against experimental.levels and the checked-in lane plan. No user assets,
no native build, no runtime.
"""
import hashlib
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import importlib.util
_spec = importlib.util.spec_from_file_location(
    'p1_challenge_impact', ROOT / 'experimental/content_lanes/p1-challenge-impact.py')
_adapter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_adapter)
GENERATOR_FILES = _adapter.GENERATOR_FILES
LEVEL_KEY = _adapter.LEVEL_KEY
NATIVE_AREA_ID = _adapter.NATIVE_AREA_ID
SOURCE_STAGE_FILE = _adapter.SOURCE_STAGE_FILE
STAGE_INFO_INDEX = _adapter.STAGE_INFO_INDEX
MissingPrerequisite = _adapter.MissingPrerequisite
audit = _adapter.audit
decode_stage_ini = _adapter.decode_stage_ini
resource_closure = _adapter.resource_closure
summarize_generator = _adapter.summarize_generator
from experimental.levels import BY_KEY

INI = ('\nnavi_start\t\t0.0 0.0\nmap_file\t\tcourses/practice/practice.mod\n\n'
       'day_multiply\t0.8\n\ndayMgr {\nnumsettings 2\n\ntimesetting 0 {\n}\n'
       'timesetting 1 {\n}\n}\n\nnew_room {\n\tindex\t\t0\n\t}\n')


def gen_blob(tags):
    parts = [b'1.0v' + b'\0' * 16 + struct.pack('>I', len(tags))]
    for tag in tags:
        rec = bytearray(96)
        rec[0:8] = b'    0.0v'
        rec[16:48] = b'test-record'.ljust(32, b'\0')
        rec[72:76] = tag.encode('ascii')
        parts.append(bytes(rec))
    return b''.join(parts)


class ImpactContractTests(unittest.TestCase):
    def make_assets(self, directory, ini=INI, gens=('default.gen', 'plants.gen'),
                    geometry=True, tags=('ikip', 'iket')):
        root = Path(directory)
        (root / 'dataDir/stages/chal0').mkdir(parents=True)
        (root / 'dataDir' / SOURCE_STAGE_FILE).write_text(ini, encoding='shift_jis')
        for name in gens:
            (root / 'dataDir/stages/chal0' / name).write_bytes(gen_blob(tags))
        if geometry:
            geo = root / 'dataDir/courses/practice'
            geo.mkdir(parents=True)
            (geo / 'practice.mod').write_bytes(b'\x00mod-bytes')
        return root

    def test_happy_path_decodes_definitions_and_closure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_assets(directory)
            packet = audit(root)
            self.assertEqual(packet['level_key'], LEVEL_KEY)
            self.assertEqual(packet['native_area_id'], NATIVE_AREA_ID)
            self.assertEqual(packet['stage_info_index'], STAGE_INFO_INDEX)
            self.assertEqual(packet['source'], SOURCE_STAGE_FILE)
            self.assertEqual(packet['definitions'],
                             {'navi_start': (0.0, 0.0), 'map_file': 'courses/practice/practice.mod',
                              'day_multiply': 0.8, 'timesettings': 2, 'rooms': 1})
            self.assertEqual([e['rel'] for e in packet['closure']],
                             ['dataDir/' + SOURCE_STAGE_FILE, 'dataDir/stages/chal0/default.gen',
                              'dataDir/stages/chal0/plants.gen', 'dataDir/courses/practice/practice.mod'])
            for entry in packet['closure']:
                self.assertRegex(entry['sha256'], r'^[0-9a-f]{64}$')
                self.assertGreater(entry['bytes'], 0)
            self.assertEqual(packet['generators']['default.gen']['records'], 2)
            self.assertEqual(packet['generators']['default.gen']['tags'], {'ikip': 1, 'iket': 1})
            self.assertEqual(packet['floors'],
                             [{'course': 'challenge:impact',
                               'generator_files': ['default.gen', 'plants.gen']}])

    def test_missing_map_file_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_assets(directory, ini=INI.replace('map_file', 'no_map'))
            with self.assertRaisesRegex(ValueError, 'Missing map file'):
                decode_stage_ini(root / 'dataDir' / SOURCE_STAGE_FILE)

    def test_malformed_day_multiply_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_assets(directory, ini=INI.replace('0.8', 'fast'))
            with self.assertRaisesRegex(ValueError, 'Malformed day_multiply'):
                decode_stage_ini(root / 'dataDir' / SOURCE_STAGE_FILE)

    def test_timesetting_coverage_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_assets(directory, ini=INI.replace('numsettings 2', 'numsettings 5'))
            with self.assertRaisesRegex(ValueError, 'timesetting coverage mismatch'):
                decode_stage_ini(root / 'dataDir' / SOURCE_STAGE_FILE)

    def test_missing_generator_names_exact_prerequisite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_assets(directory, gens=('default.gen',))
            with self.assertRaises(MissingPrerequisite) as ctx:
                resource_closure(root)
            self.assertIn('dataDir/stages/chal0/plants.gen', str(ctx.exception))

    def test_missing_geometry_names_exact_prerequisite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_assets(directory, geometry=False)
            with self.assertRaises(MissingPrerequisite) as ctx:
                resource_closure(root)
            self.assertIn('dataDir/courses/practice/practice.mod', str(ctx.exception))

    def test_missing_assets_root_names_expected_files(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / 'no-such-assets'
            with self.assertRaises(MissingPrerequisite) as ctx:
                audit(missing)
            self.assertIn(str(missing), str(ctx.exception))

    def test_missing_ini_names_exact_prerequisite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'dataDir/stages/chal0').mkdir(parents=True)
            with self.assertRaises(MissingPrerequisite):
                decode_stage_ini(root / 'dataDir' / SOURCE_STAGE_FILE)

    def test_corrupt_generator_framing_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_assets(directory)
            (root / 'dataDir/stages/chal0/default.gen').write_bytes(b'garbage-bytes')
            with self.assertRaises(ValueError):
                summarize_generator(root / 'dataDir/stages/chal0/default.gen')

    def test_identity_matches_level_registry(self):
        level = BY_KEY[LEVEL_KEY]
        self.assertEqual((level.area_id, level.stage_file), (NATIVE_AREA_ID, SOURCE_STAGE_FILE))

    def test_identity_matches_checked_in_lane_plan(self):
        plan = json.loads((ROOT / 'docs/PIKMIN_CONTENT_IMPORT_LANES.json').read_text(encoding='utf-8-sig'))
        lane = next(x for x in plan['lanes'] if x['lane'] == 'p1-challenge-impact')
        self.assertEqual(lane['source'], SOURCE_STAGE_FILE)
        self.assertEqual(lane['issue'], 565)
        self.assertEqual(lane['details']['level_key'], LEVEL_KEY)
        self.assertEqual(lane['details']['native_area_id'], NATIVE_AREA_ID)
        self.assertEqual(lane['details']['stage_info_index'], STAGE_INFO_INDEX)
        self.assertEqual(lane['owned_files'],
                         ['experimental/content_lanes/p1-challenge-impact.py',
                          'tests/content_lanes/test_p1_challenge_impact.py',
                          'docs/content_lanes/p1-challenge-impact.md'])

    def test_no_fabricated_placements(self):
        with tempfile.TemporaryDirectory() as directory:
            packet = audit(self.make_assets(directory))
            blob = json.dumps(packet)
            for word in ('actors', 'placements', 'spawn_count', 'enemy_count'):
                self.assertNotIn(word, blob)
            self.assertEqual(set(packet['generators']['default.gen']),
                             {'records', 'bytes', 'tags', 'rel', 'sha256'})
            self.assertEqual(tuple(GENERATOR_FILES), ('default.gen', 'plants.gen'))

    def test_closure_hashes_match_file_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_assets(directory)
            for entry in resource_closure(root):
                digest = hashlib.sha256((root / entry['rel']).read_bytes()).hexdigest()
                self.assertEqual(entry['sha256'], digest)


if __name__ == '__main__':
    unittest.main()
