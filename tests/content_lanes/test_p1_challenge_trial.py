"""Focused boundary tests for the trial import contract
(lane p1-challenge-trial, #567).

All expectations derive from the checked-in canonical baseline at runtime;
no retail values are hardcoded except in the single clearly-marked
characterization test, whose values were read from the local asset copy
(not canonical pins). Fixture bytes are explicitly synthetic and only
exercise presence/parsing, never retail decoding.
"""
import copy
import hashlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# The reserved adapter is loaded by file path so this test needs no package
# glue outside the lane's three owned files; the integrator's tree provides
# experimental/content_lanes/__init__.py when it lands the first lane.
import importlib.util

_SPEC = importlib.util.spec_from_file_location(
    'p1_challenge_trial_adapter',
    ROOT / 'experimental' / 'content_lanes' / 'p1-challenge-trial.py')
_ADAPTER = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_ADAPTER)

LEVEL_KEY = _ADAPTER.LEVEL_KEY
ISSUE = _ADAPTER.ISSUE
LANE = _ADAPTER.LANE
SOURCE_PATH = _ADAPTER.SOURCE_PATH
ContractViolation = _ADAPTER.ContractViolation
MissingPrerequisite = _ADAPTER.MissingPrerequisite
baseline_details = _ADAPTER.baseline_details
decode_stage = _ADAPTER.decode_stage
locate_source = _ADAPTER.locate_source
native_level = _ADAPTER.native_level
resource_closure = _ADAPTER.resource_closure
summarize = _ADAPTER.summarize
validate_manifest = _ADAPTER.validate_manifest

# Explicit asset path used only by the characterization test below.
ASSETS = Path('C:/Users/alari/bbft/dist/cohesion/pikmin/assets')

SYNTHETIC_INI = (
    '// SYNTHETIC-TEST-PLACEHOLDER; not retail stage data\n'
    'navi_start 1.5 -2.5\n'
    'map_file courses/test/room.mod\n'
    'day_multiply 2\n'
    'dayMgr {\n'
    'numsettings 2\n'
    'timesetting 0 {\n'
    '  }\n'
    'timesetting 1 {\n'
    '  }\n'
    '}\n'
    'new_room {\n'
    'index 3\n'
    'radius 4.0\n'
    'centre 1.0 2.0\n'
    '}\n'
)


def good_manifest(sha='0' * 64):
    return {'level_key': LEVEL_KEY,
            'native_area_id': 4,
            'stage_info_index': 20,
            'tracks': ['Optional story destination #100',
                       'Separate timed/scored AP campaign #52'],
            'source_sha256': sha,
            'navi_start': [0.0, 0.0],
            'map_model': 'courses/laststage/garden.mod',
            'day_multiply': 1.0,
            'timesettings': [0, 1, 2, 3, 4],
            'new_room': {'index': ['0'], 'radius': ['4.0'],
                         'centre': ['0.0', '0.0']}}


def good_decoded():
    return {'directives': {}, 'blocks': ['dayMgr', 'new_room'],
            'timesettings': [0, 1, 2, 3, 4],
            'new_room': {'index': ['0'], 'radius': ['4.0'],
                         'centre': ['0.0', '0.0']},
            'unsupported': [],
            'navi_start': [0.0, 0.0],
            'map_model': 'courses/laststage/garden.mod',
            'day_multiply': 1.0}


class BaselineTests(unittest.TestCase):
    def test_plan_and_native_table_agree(self):
        details = baseline_details(ROOT)
        self.assertEqual(details['level_key'], LEVEL_KEY)
        self.assertEqual(details['native_area_id'], 4)
        self.assertEqual(details['stage_info_index'], 20)
        self.assertEqual(details['tracks'],
                         ['Optional story destination #100',
                          'Separate timed/scored AP campaign #52'])
        level = native_level(ROOT)
        self.assertEqual((level.key, level.area_id, level.stage_file),
                         (LEVEL_KEY, 4, SOURCE_PATH))

    def test_closure_from_synthetic_decode(self):
        decoded = decode_stage(SYNTHETIC_INI)
        self.assertEqual(decoded['timesettings'], [0, 1])
        self.assertEqual(decoded['blocks'], ['dayMgr', 'new_room'])
        self.assertEqual(decoded['unsupported'], [])
        closure = resource_closure(decoded)
        self.assertEqual(closure['navi_start'], [1.5, -2.5])
        self.assertEqual(closure['map_model'], 'courses/test/room.mod')
        self.assertIsNone(closure['map_model_checked'])
        self.assertIsNone(closure['map_model_resolved'])
        self.assertEqual(closure['day_multiply'], 2.0)
        self.assertEqual(closure['new_room']['index'], ['3'])

    def test_decoder_rejects_imbalance_and_duplicates(self):
        with self.assertRaises(ContractViolation):
            decode_stage('navi_start 0 0\n}\n')
        with self.assertRaises(ContractViolation):
            decode_stage('dayMgr {\n')
        with self.assertRaises(ContractViolation):
            decode_stage('navi_start 0 0\nnavi_start 1 1\n')
        with self.assertRaises(ContractViolation):
            decode_stage('timesetting x {\n')

    def test_decoder_lists_unknown_names(self):
        decoded = decode_stage('mystery_flag 1\nnew_room {\nindex 0\n}\n'
                               'dayMgr {\nnumsettings 0\n}\n')
        self.assertIn('mystery_flag', decoded['unsupported'])
        with self.assertRaises(ContractViolation):
            resource_closure({'directives': {}, 'blocks': [],
                              'timesettings': [], 'new_room': None,
                              'unsupported': []})


class ManifestTests(unittest.TestCase):
    def test_valid_manifest_passes(self):
        report = validate_manifest(good_manifest(), good_decoded(),
                                   '0' * 64, root=ROOT)
        self.assertTrue(report['complete'])
        self.assertEqual(report['stage_info_index'], 20)

    def test_wrong_identity_fields_fail(self):
        for key, value in (('level_key', 'challenge:tria'),
                           ('native_area_id', 5), ('native_area_id', '4'),
                           ('stage_info_index', 21),
                           ('tracks', ['Optional story destination #100']),
                           ('tracks', 'tracks'), ('source_sha256', '1' * 64)):
            bad = good_manifest()
            bad[key] = value
            with self.subTest(key=key, value=value):
                with self.assertRaises(ContractViolation):
                    validate_manifest(bad, good_decoded(), '0' * 64, root=ROOT)

    def test_wrong_decoded_fields_fail(self):
        for key, value in (('navi_start', [0.0, 1.0]),
                           ('map_model', 'courses/other.mod'),
                           ('day_multiply', 2.0),
                           ('timesettings', [0, 1, 2, 3]),
                           ('new_room', {})):
            bad = good_manifest()
            bad[key] = value
            with self.subTest(key=key, value=value):
                with self.assertRaises(ContractViolation):
                    validate_manifest(bad, good_decoded(), '0' * 64, root=ROOT)

    def test_non_mapping_inputs_fail(self):
        for bad in (None, [], 'manifest'):
            with self.assertRaises(ContractViolation):
                validate_manifest(bad, good_decoded(), '0' * 64, root=ROOT)
        with self.assertRaises(ContractViolation):
            validate_manifest(good_manifest(), [], '0' * 64, root=ROOT)

    def test_unsupported_decoded_refs_fail(self):
        decoded = dict(good_decoded(), unsupported=['mystery_flag'])
        with self.assertRaises(ContractViolation):
            validate_manifest(good_manifest(), decoded, '0' * 64, root=ROOT)

    def test_fabricated_runtime_keys_refused(self):
        for key in ('placements', 'actors', 'spawn_layout', 'scores',
                    'results', 'checks', 'receipts'):
            bad = good_manifest()
            bad[key] = []
            with self.subTest(key=key):
                with self.assertRaises(ContractViolation):
                    validate_manifest(bad, good_decoded(), '0' * 64, root=ROOT)


class SourceBoundaryTests(unittest.TestCase):
    def test_missing_source_reports_exact_prerequisite(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(MissingPrerequisite) as ctx:
                locate_source(directory)
        message = str(ctx.exception)
        self.assertIn('stages/chal4.ini', message)
        self.assertIn(directory, message)
        self.assertIn(str(ISSUE), message)

    def test_characterization_of_local_asset_copy(self):
        # Values below were read from the local asset copy, not pinned by
        # any canonical file; a mismatch means local asset drift, which is
        # itself the honest signal (re-record, do not relax the check).
        record = locate_source(ASSETS)
        self.assertEqual(record['bytes'], 2484)
        text = Path(record['path']).read_text(encoding='utf-8')
        decoded = decode_stage(text)
        self.assertEqual(decoded['timesettings'], [0, 1, 2, 3, 4])
        self.assertEqual(decoded['unsupported'], [])
        closure = resource_closure(decoded, ASSETS)
        self.assertEqual(closure['navi_start'], [0.0, 0.0])
        self.assertEqual(closure['map_model'], 'courses/laststage/garden.mod')
        self.assertTrue(closure['map_model_resolved'])
        manifest = dict(good_manifest(record['sha256']),
                        navi_start=closure['navi_start'],
                        map_model=closure['map_model'],
                        day_multiply=closure['day_multiply'],
                        timesettings=closure['timesettings'],
                        new_room=closure['new_room'])
        report = validate_manifest(manifest, closure, record['sha256'], root=ROOT)
        self.assertTrue(report['complete'])

    def test_summarize_without_asset_root(self):
        packet = summarize(root=ROOT)
        self.assertEqual(packet['lane'], LANE)
        self.assertEqual(packet['level_key'], LEVEL_KEY)
        self.assertFalse(packet['playable'])
        self.assertIn('unavailable', packet['source'])


if __name__ == '__main__':
    unittest.main()