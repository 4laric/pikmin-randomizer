"""Focused boundary tests for the forest_3 import contract (lane p2-cave-forest_3, #156).

All expectations derive from the checked-in canonical baseline at runtime;
no retail values are hardcoded here. Fixture bytes are explicitly synthetic
and only exercise presence/hashing, never retail decoding.
"""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# The reserved adapter is loaded by file path so this test needs no package
# glue outside the lane's three owned files; the integrator's tree provides
# experimental/content_lanes/__init__.py when it lands the first lane.
import importlib.util

_SPEC = importlib.util.spec_from_file_location(
    'p2_cave_forest_3_adapter',
    ROOT / 'experimental' / 'content_lanes' / 'p2-cave-forest_3.py')
_ADAPTER = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_ADAPTER)

CAVE_ID = _ADAPTER.CAVE_ID
ISSUE = _ADAPTER.ISSUE
LANE = _ADAPTER.LANE
SOURCE_PATH = _ADAPTER.SOURCE_PATH
ContractViolation = _ADAPTER.ContractViolation
MissingPrerequisite = _ADAPTER.MissingPrerequisite
baseline_floors = _ADAPTER.baseline_floors
classify_token = _ADAPTER.classify_token
inventory_cave = _ADAPTER.inventory_cave
locate_source = _ADAPTER.locate_source
plan_lane = _ADAPTER.plan_lane
resource_closure = _ADAPTER.resource_closure
summarize = _ADAPTER.summarize
validate_manifest = _ADAPTER.validate_manifest


def good_manifest():
    rows = baseline_floors(ROOT)
    return {'cave_id': CAVE_ID,
            'floors': [{'number': r['first'], 'unit_pool': r['unit_pool'],
                        'enemy_ids': list(r['enemy_ids']),
                        'treasure_ids': list(r['treasure_ids'])} for r in rows]}


class BaselineTests(unittest.TestCase):
    def test_lane_and_inventory_agree_on_seven_floors(self):
        lane = plan_lane(ROOT)
        self.assertEqual(lane['lane'], LANE)
        self.assertEqual(lane['issue'], ISSUE)
        self.assertEqual(lane['source'], SOURCE_PATH)
        self.assertIsNone(lane['source_sha256'])
        cave = inventory_cave(ROOT)
        self.assertEqual(cave['issue'], ISSUE)
        rows = baseline_floors(ROOT)
        self.assertEqual(len(rows), 7)
        self.assertEqual([r['first'] for r in rows], [1, 2, 3, 4, 5, 6, 7])

    def test_resource_closure_matches_baseline_sets(self):
        closure = resource_closure(root=ROOT)
        self.assertEqual(closure['cave_id'], CAVE_ID)
        self.assertEqual(closure['floor_count'], 7)
        self.assertEqual(len(closure['unit_pools']), 7)
        rows = baseline_floors(ROOT)
        expect_enemies, expect_treasures = set(), set()
        for row in rows:
            expect_enemies.update(row['enemy_ids'])
            expect_treasures.update(row['treasure_ids'])
        self.assertEqual(set(closure['enemy_tokens']), expect_enemies)
        self.assertEqual(set(closure['treasure_tokens']), expect_treasures)
        self.assertIn('$Egg', closure['enemy_tokens'])
        self.assertIn('haniwa', closure['treasure_tokens'])

    def test_classifier_structural_cases(self):
        self.assertEqual(classify_token('Hiba'), 'exact')
        self.assertEqual(classify_token('BlueKochappy'), 'exact')
        self.assertEqual(classify_token('$Egg'), 'generator_variant')
        self.assertEqual(classify_token('$MaroFrog_wadou_kaichin'), 'generator_variant')
        self.assertEqual(classify_token('BlueChappy_diamond_green_l'), 'suffixed_unresolved')
        self.assertEqual(classify_token('Wealthy_kouseki_suisyou'), 'suffixed_unresolved')
        self.assertEqual(classify_token('KingChappy_suit_fire'), 'suffixed_unresolved')
        for bad in ('', '   ', None, 42, ['Hiba'], '$'):
            with self.subTest(bad=bad):
                with self.assertRaises(ContractViolation):
                    classify_token(bad)

    def test_unresolved_list_is_explicit(self):
        closure = resource_closure(root=ROOT)
        self.assertIn('BlueChappy_diamond_green_l', closure['unresolved'])
        self.assertIn('$Bomb', closure['unresolved'])
        self.assertNotIn('Hiba', closure['unresolved'])


class ManifestTests(unittest.TestCase):
    def test_valid_manifest_passes_with_coverage(self):
        report = validate_manifest(good_manifest(), root=ROOT)
        self.assertTrue(report['complete'])
        self.assertEqual([f['number'] for f in report['floors']], [1, 2, 3, 4, 5, 6, 7])

    def test_wrong_cave_id_or_shape_fails(self):
        bad = good_manifest()
        bad['cave_id'] = 'forest_2'
        with self.assertRaises(ContractViolation):
            validate_manifest(bad, root=ROOT)
        with self.assertRaises(ContractViolation):
            validate_manifest([], root=ROOT)
        with self.assertRaises(ContractViolation):
            validate_manifest({'cave_id': CAVE_ID}, root=ROOT)

    def test_missing_floor_fails(self):
        bad = good_manifest()
        bad['floors'].pop(3)
        with self.assertRaises(ContractViolation):
            validate_manifest(bad, root=ROOT)

    def test_duplicate_and_reordered_floors_fail(self):
        bad = good_manifest()
        bad['floors'].append(copy.deepcopy(bad['floors'][0]))
        with self.assertRaises(ContractViolation):
            validate_manifest(bad, root=ROOT)
        bad = good_manifest()
        bad['floors'][0], bad['floors'][1] = bad['floors'][1], bad['floors'][0]
        with self.assertRaises(ContractViolation):
            validate_manifest(bad, root=ROOT)

    def test_wrong_unit_pool_fails(self):
        bad = good_manifest()
        bad['floors'][6]['unit_pool'] = '2_MAT_kingA_kingB_tsuchi.tx'
        with self.assertRaises(ContractViolation):
            validate_manifest(bad, root=ROOT)

    def test_missing_and_extra_tokens_fail(self):
        bad = good_manifest()
        bad['floors'][1]['enemy_ids'].remove('Hiba')
        with self.assertRaises(ContractViolation):
            validate_manifest(bad, root=ROOT)
        bad = good_manifest()
        bad['floors'][1]['enemy_ids'].append('HibaX')
        with self.assertRaises(ContractViolation):
            validate_manifest(bad, root=ROOT)
        bad = good_manifest()
        bad['floors'][6]['treasure_ids'] = []
        with self.assertRaises(ContractViolation):
            validate_manifest(bad, root=ROOT)

    def test_malformed_token_lists_fail(self):
        for key, value in (('enemy_ids', 'Hiba'), ('enemy_ids', ['Hiba', 7]),
                           ('treasure_ids', None), ('enemy_ids', [''])):
            bad = good_manifest()
            bad['floors'][0][key] = value
            with self.subTest(key=key, value=value):
                with self.assertRaises(ContractViolation):
                    validate_manifest(bad, root=ROOT)

    def test_fabricated_placements_refused(self):
        for key in ('placements', 'actors', 'spawn_layout'):
            bad = good_manifest()
            bad['floors'][0][key] = []
            with self.subTest(key=key):
                with self.assertRaises(ContractViolation):
                    validate_manifest(bad, root=ROOT)


class SourceBoundaryTests(unittest.TestCase):
    def test_missing_source_reports_exact_prerequisite(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(MissingPrerequisite) as ctx:
                locate_source(directory)
        message = str(ctx.exception)
        self.assertIn(SOURCE_PATH, message)
        self.assertIn(directory, message)
        self.assertIn(str(ISSUE), message)

    def test_present_source_hashes_bytes_without_interpreting(self):
        payload = b'SYNTHETIC-TEST-PLACEHOLDER; not retail caveinfo\n'
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / Path(*SOURCE_PATH.split('/'))
            target.parent.mkdir(parents=True)
            target.write_bytes(payload)
            record = locate_source(directory)
        self.assertEqual(record['sha256'], hashlib.sha256(payload).hexdigest())
        self.assertEqual(record['bytes'], len(payload))
        self.assertTrue(record['path'].endswith('forest_3.txt'))

    def test_summarize_reports_unavailable_source(self):
        with tempfile.TemporaryDirectory() as directory:
            packet = summarize(root=ROOT, asset_root=directory)
        self.assertEqual(packet['lane'], LANE)
        self.assertEqual(packet['floor_count'], 7)
        self.assertFalse(packet['playable'])
        self.assertIn('missing_prerequisite', packet['source'])
        self.assertIn(SOURCE_PATH, packet['source']['missing_prerequisite'])


if __name__ == '__main__':
    unittest.main()
