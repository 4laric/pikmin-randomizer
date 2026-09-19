"""Focused boundary tests for the forest_4 import contract (lane p2-cave-forest_4, #157).

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
    'p2_cave_forest_4_adapter',
    ROOT / 'experimental' / 'content_lanes' / 'p2-cave-forest_4.py')
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
        self.assertIn('$1Kabuto_uji_jisyaku', closure['enemy_tokens'])
        self.assertIn('bird_hane', closure['treasure_tokens'])

    def test_classifier_structural_cases(self):
        self.assertEqual(classify_token('Sarai'), 'exact')
        self.assertEqual(classify_token('UjiB'), 'exact')
        self.assertEqual(classify_token('Hana'), 'exact')
        self.assertEqual(classify_token('$1Kabuto_uji_jisyaku'), 'generator_variant')
        self.assertEqual(classify_token('$2BlueKochappy_be_dama_blue_l'), 'generator_variant')
        self.assertEqual(classify_token('$1BlueKochappy'), 'generator_variant')
        self.assertEqual(classify_token('BlueChappy_be_dama_yellow_l'), 'suffixed_unresolved')
        self.assertEqual(classify_token('SnakeCrow_apple_blue'), 'suffixed_unresolved')
        self.assertEqual(classify_token('SnakeWhole_suit_powerup'), 'suffixed_unresolved')
        self.assertEqual(classify_token('Fuefuki_whistle'), 'suffixed_unresolved')
        for bad in ('', '   ', None, 42, ['Sarai'], '$'):
            with self.subTest(bad=bad):
                with self.assertRaises(ContractViolation):
                    classify_token(bad)

    def test_good_manifest_validates_complete(self):
        report = validate_manifest(good_manifest(), root=ROOT)
        self.assertTrue(report['complete'])
        self.assertEqual(len(report['floors']), 7)
        self.assertEqual([f['number'] for f in report['floors']], [1, 2, 3, 4, 5, 6, 7])


class MalformedManifestTests(unittest.TestCase):
    def _expect_violation(self, mutate):
        manifest = good_manifest()
        mutate(manifest)
        with self.assertRaises(ContractViolation):
            validate_manifest(manifest, root=ROOT)

    def test_not_a_mapping(self):
        with self.assertRaises(ContractViolation):
            validate_manifest(['not', 'a', 'mapping'], root=ROOT)

    def test_wrong_cave_id(self):
        self._expect_violation(lambda m: m.update(cave_id='forest_3'))

    def test_missing_floor(self):
        self._expect_violation(lambda m: m['floors'].pop())

    def test_extra_floor(self):
        self._expect_violation(lambda m: m['floors'].append(dict(m['floors'][0])))

    def test_wrong_floor_number(self):
        self._expect_violation(lambda m: m['floors'][3].update(number=99))

    def test_wrong_unit_pool(self):
        self._expect_violation(
            lambda m: m['floors'][0].update(unit_pool='nope.txt'))

    def test_missing_enemy_token(self):
        def mutate(manifest):
            manifest['floors'][5]['enemy_ids'].remove('Fuefuki')
        self._expect_violation(mutate)

    def test_extra_treasure_token(self):
        def mutate(manifest):
            manifest['floors'][1]['treasure_ids'].append('invented_loot')
        self._expect_violation(mutate)

    def test_non_string_token_rejected(self):
        def mutate(manifest):
            manifest['floors'][6]['enemy_ids'].append(42)
        self._expect_violation(mutate)

    def test_fabricated_placements_refused(self):
        for key in ('placements', 'actors', 'spawn_layout'):
            with self.subTest(key=key):
                def mutate(manifest, key=key):
                    manifest['floors'][2][key] = []
                self._expect_violation(mutate)


class SourceBoundaryTests(unittest.TestCase):
    def test_missing_source_fails_closed_with_prerequisite(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(MissingPrerequisite) as ctx:
                locate_source(tmp)
        message = str(ctx.exception)
        self.assertIn(SOURCE_PATH, message)
        self.assertIn(tmp, message)
        self.assertIn('157', message)

    def test_synthetic_presence_hashes_bytes(self):
        payload = b'synthetic forest_4 presence probe, not retail content\n'
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp, *SOURCE_PATH.split('/'))
            target.parent.mkdir(parents=True)
            target.write_bytes(payload)
            record = locate_source(tmp)
        self.assertEqual(record['sha256'], hashlib.sha256(payload).hexdigest())
        self.assertEqual(record['bytes'], len(payload))
        self.assertTrue(record['path'].endswith('forest_4.txt'))

    def test_summarize_reports_missing_prerequisite_not_playable(self):
        packet = summarize(root=ROOT, asset_root=ROOT / 'output' / 'definitely-absent-157')
        self.assertEqual(packet['lane'], LANE)
        self.assertEqual(packet['issue'], ISSUE)
        self.assertEqual(packet['floor_count'], 7)
        self.assertFalse(packet['playable'])
        self.assertIn('missing_prerequisite', packet['source'])
        self.assertIn(SOURCE_PATH, packet['source']['missing_prerequisite'])


if __name__ == '__main__':
    unittest.main()
