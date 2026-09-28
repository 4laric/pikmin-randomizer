"""Focused boundary tests for the challenge-20 import contract
(lane p2-challenge-ch_mat_yellow_purple_white, #552).

All expectations derive from the checked-in canonical baseline at runtime;
no retail values are hardcoded here. Fixture bytes are explicitly synthetic
and only exercise presence/hashing, never retail decoding. A present file
can never match the recorded pin with synthetic bytes, so the hash-mismatch
guard itself is tested; the match branch requires the real disc.
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
    'ch_mat_yellow_purple_white_adapter',
    ROOT / 'experimental' / 'content_lanes' / 'p2-challenge-ch_mat_yellow_purple_white.py')
_ADAPTER = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_ADAPTER)

CAVE_ID = _ADAPTER.CAVE_ID
ISSUE = _ADAPTER.ISSUE
LANE = _ADAPTER.LANE
SOURCE_PATH = _ADAPTER.SOURCE_PATH
RECORDED_SHA256 = _ADAPTER.RECORDED_SHA256
ContractViolation = _ADAPTER.ContractViolation
MissingPrerequisite = _ADAPTER.MissingPrerequisite
baseline_details = _ADAPTER.baseline_details
inventory_stage = _ADAPTER.inventory_stage
locate_source = _ADAPTER.locate_source
plan_details = _ADAPTER.plan_details
resource_closure = _ADAPTER.resource_closure
summarize = _ADAPTER.summarize
validate_manifest = _ADAPTER.validate_manifest

EXPECTED_MATRIX = [[0, 0, 0], [0, 0, 0], [30, 0, 0], [15, 0, 0],
                   [15, 0, 0], [0, 0, 0], [0, 0, 0]]


def good_manifest():
    return {'cave_id': CAVE_ID,
            'table_order': 16,
            'ui_index': 19,
            'floors': 1,
            'pikmin_by_native_color_and_maturity': copy.deepcopy(EXPECTED_MATRIX),
            'legacy_time': 700.0,
            'bitter_sprays': 0,
            'spicy_sprays': 2,
            'treasure_count_field': 0,
            'floor_seconds': [230.0]}


class BaselineTests(unittest.TestCase):
    def test_plan_and_inventory_agree(self):
        details = baseline_details(ROOT)
        self.assertEqual(details['cave_id'], CAVE_ID)
        self.assertEqual(details['table_order'], 16)
        self.assertEqual(details['ui_index'], 19)
        self.assertEqual(details['floors'], 1)
        self.assertEqual(plan_details(ROOT)['cave_path'], SOURCE_PATH)
        self.assertEqual(inventory_stage(ROOT)['cave_path'], SOURCE_PATH)

    def test_recorded_pin_format(self):
        self.assertRegex(RECORDED_SHA256, r'^[0-9a-f]{64}$')
        self.assertEqual(len(RECORDED_SHA256), 64)

    def test_resource_closure_preserves_roster(self):
        closure = resource_closure(root=ROOT)
        self.assertEqual(closure['cave_id'], CAVE_ID)
        self.assertEqual(closure['floors'], 1)
        self.assertEqual(closure['pikmin_by_native_color_and_maturity'],
                         EXPECTED_MATRIX)
        self.assertEqual(closure['pikmin_total'], 60)
        self.assertEqual(closure['floor_seconds'], [230.0])
        self.assertEqual((closure['bitter_sprays'], closure['spicy_sprays']), (0, 2))
        self.assertEqual(closure['legacy_time'], 700.0)
        self.assertEqual(closure['treasure_count_field'], 0)
        self.assertNotIn('actors', closure)
        self.assertNotIn('placements', closure)


class ManifestTests(unittest.TestCase):
    def test_valid_manifest_passes(self):
        report = validate_manifest(good_manifest(), root=ROOT)
        self.assertTrue(report['complete'])
        self.assertEqual(report['pikmin_total'], 60)
        self.assertEqual((report['table_order'], report['ui_index']), (16, 19))

    def test_wrong_identity_fields_fail(self):
        for key, value in (('cave_id', 'ch_MAT_yellow_purple_whit'),
                           ('table_order', 17), ('table_order', '16'),
                           ('ui_index', 20), ('floors', 2),
                           ('floors', '1')):
            bad = good_manifest()
            bad[key] = value
            with self.subTest(key=key, value=value):
                with self.assertRaises(ContractViolation):
                    validate_manifest(bad, root=ROOT)

    def test_wrong_economy_fields_fail(self):
        for key, value in (('legacy_time', 700), ('legacy_time', 699.9),
                           ('bitter_sprays', 1), ('spicy_sprays', 3),
                           ('spicy_sprays', '2'), ('treasure_count_field', 1),
                           ('floor_seconds', [230]), ('floor_seconds', [230.0, 230.0]),
                           ('floor_seconds', []), ('floor_seconds', [-5.0])):
            bad = good_manifest()
            bad[key] = value
            with self.subTest(key=key, value=value):
                with self.assertRaises(ContractViolation):
                    validate_manifest(bad, root=ROOT)

    def test_roster_matrix_exactness(self):
        bad = good_manifest()
        bad['pikmin_by_native_color_and_maturity'][2] = [29, 0, 0]
        with self.assertRaises(ContractViolation):
            validate_manifest(bad, root=ROOT)
        for matrix in ([[0, 0, 0]] * 6, 'roster', None,
                       [[0, 0, 0]] * 6 + [[0, 0, -1]],
                       [[0, 0, 0]] * 6 + [['30', 0, 0]]):
            bad = good_manifest()
            bad['pikmin_by_native_color_and_maturity'] = matrix
            with self.subTest(matrix=matrix):
                with self.assertRaises(ContractViolation):
                    validate_manifest(bad, root=ROOT)

    def test_non_mapping_manifest_fails(self):
        for bad in (None, [], 'manifest'):
            with self.assertRaises(ContractViolation):
                validate_manifest(bad, root=ROOT)

    def test_fabricated_runtime_keys_refused(self):
        for key in ('placements', 'actors', 'spawn_layout', 'scores', 'results'):
            bad = good_manifest()
            bad[key] = []
            with self.subTest(key=key):
                with self.assertRaises(ContractViolation):
                    validate_manifest(bad, root=ROOT)


class SourceBoundaryTests(unittest.TestCase):
    def test_missing_source_reports_exact_prerequisite(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(MissingPrerequisite) as ctx:
                locate_source(directory)
        message = str(ctx.exception)
        self.assertIn(SOURCE_PATH, message)
        self.assertIn(directory, message)
        self.assertIn(RECORDED_SHA256, message)
        self.assertIn(str(ISSUE), message)

    def test_present_wrong_revision_rejected(self):
        import tempfile
        payload = b'SYNTHETIC-TEST-PLACEHOLDER; not retail caveinfo\n'
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / Path(*SOURCE_PATH.split('/'))
            target.parent.mkdir(parents=True)
            target.write_bytes(payload)
            with self.assertRaises(ContractViolation) as ctx:
                locate_source(directory)
        self.assertIn(RECORDED_SHA256, str(ctx.exception))

    def test_summarize_reports_unavailable_source(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            packet = summarize(root=ROOT, asset_root=directory)
        self.assertEqual(packet['lane'], LANE)
        self.assertEqual(packet['cave_id'], CAVE_ID)
        self.assertEqual(packet['source_sha256'], RECORDED_SHA256)
        self.assertFalse(packet['playable'])
        self.assertIn('unavailable', packet['source'])
        self.assertIn(SOURCE_PATH, packet['source']['unavailable'])
        self.assertEqual(packet['closure']['pikmin_total'], 60)


if __name__ == '__main__':
    unittest.main()