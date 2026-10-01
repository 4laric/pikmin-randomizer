"""Focused P1 boundary tests for the ch_MAT_yellow_purple_white import path
(lane p2-challenge-ch-mat-yellow-purple-white-p1, #552).

Expectations derive from the checked-in canonical baseline at runtime; no
retail values are hardcoded. The P1 module is loaded by path and reuses the P0
adapter by path, so the suite needs no package glue. No engine, assets or
display are required.
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

import importlib.util

_SPEC = importlib.util.spec_from_file_location(
    'ch_mat_yellow_purple_white_p1',
    ROOT / 'experimental' / 'content_lanes' / 'ch_mat_yellow_purple_white.py')
_P1 = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_P1)

CAVE_ID = _P1.p0(ROOT).CAVE_ID
P1_SCHEMA = _P1.P1_SCHEMA


def good_manifest():
    return _P1.default_manifest(ROOT)


class P1ManifestTests(unittest.TestCase):
    def test_default_manifest_is_valid(self):
        staging = _P1.validate_p1_manifest(good_manifest(), root=ROOT)
        self.assertEqual(staging['cave_id'], CAVE_ID)
        self.assertEqual(staging['floors'], 1)
        self.assertEqual(staging['floor_seconds'], [230.0])
        self.assertEqual(staging['squad_total'], 60)
        self.assertEqual(staging['sprays'], {'bitter': 0, 'spicy': 2})
        self.assertEqual(staging['ui_index'], 19)

    def test_default_manifest_matches_p0_closure(self):
        closure = _P1.p0(ROOT).resource_closure(root=ROOT)
        manifest = good_manifest()
        self.assertEqual(manifest['pikmin_by_native_color_and_maturity'],
                         closure['pikmin_by_native_color_and_maturity'])
        self.assertEqual(sum(sum(r) for r in manifest['pikmin_by_native_color_and_maturity']),
                         closure['pikmin_total'])
        self.assertEqual(manifest['floor_seconds'], closure['floor_seconds'])

    def test_wrong_identity_fields_fail(self):
        for key, value in (('cave_id', 'ch_MAT_x'), ('floors', 2), ('floors', '1'),
                           ('ui_index', 20), ('table_order', 17),
                           ('bitter_sprays', 1), ('spicy_sprays', 3),
                           ('treasure_count_field', 1)):
            bad = good_manifest()
            bad[key] = value
            with self.subTest(key=key, value=value):
                with self.assertRaises(ValueError):
                    _P1.validate_p1_manifest(bad, root=ROOT)

    def test_legacy_time_exactness(self):
        for value in (700, 699.9, 0.0):
            bad = good_manifest()
            bad['legacy_time'] = value
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    _P1.validate_p1_manifest(bad, root=ROOT)

    def test_timer_exactness(self):
        for value in ([230], [], [-5.0], [230.0, 230.0], 230.0):
            bad = good_manifest()
            bad['floor_seconds'] = value
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    _P1.validate_p1_manifest(bad, root=ROOT)

    def test_roster_exactness_and_empty_squad(self):
        bad = good_manifest()
        bad['pikmin_by_native_color_and_maturity'][2] = [29, 0, 0]
        with self.assertRaises(ValueError):
            _P1.validate_p1_manifest(bad, root=ROOT)
        empty = good_manifest()
        empty['pikmin_by_native_color_and_maturity'] = [[0, 0, 0]] * 7
        with self.assertRaises(ValueError):
            _P1.validate_p1_manifest(empty, root=ROOT)
        for matrix in ([[0, 0, 0]] * 6, 'roster', None,
                       [[0, 0, 0]] * 6 + [[0, 0, -1]],
                       [[0, 0, 0]] * 6 + [['30', 0, 0]]):
            bad = good_manifest()
            bad['pikmin_by_native_color_and_maturity'] = matrix
            with self.subTest(matrix=matrix):
                with self.assertRaises(ValueError):
                    _P1.validate_p1_manifest(bad, root=ROOT)

    def test_non_mapping_manifest_fails(self):
        for bad in (None, [], 'manifest'):
            with self.assertRaises(ValueError):
                _P1.validate_p1_manifest(bad, root=ROOT)

    def test_fabricated_runtime_keys_refused(self):
        for key in ('placements', 'actors', 'spawn_layout', 'scores', 'results'):
            bad = good_manifest()
            bad[key] = []
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    _P1.validate_p1_manifest(bad, root=ROOT)


class P1StagingTests(unittest.TestCase):
    def test_stage_layout_files_and_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            result = _P1.stage_run_layout(good_manifest(), directory, root=ROOT)
            for name in ('stage-manifest.json', 'p1-input-package.json', 'run-plan.json'):
                path = Path(directory) / name
                self.assertTrue(path.is_file(), name)
                self.assertRegex(result['files'][name], r'^[0-9a-f]{64}$')
            package = json.loads((Path(directory) / 'p1-input-package.json').read_text(encoding='utf-8'))
            self.assertEqual(package['schema'], P1_SCHEMA)
            self.assertEqual(package['cave_id'], CAVE_ID)
            self.assertEqual(package['squad_total'], 60)
            self.assertEqual(package['sprays'], {'bitter': 0, 'spicy': 2})
            plan = json.loads((Path(directory) / 'run-plan.json').read_text(encoding='utf-8'))
            self.assertEqual(plan['gates'], 'all six UNTESTED unless genuinely observed')
            self.assertIn('CAPTAIN_DOWN', ' '.join(plan['order']))

    def test_stage_rejects_bad_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            bad = good_manifest()
            bad['floors'] = 3
            with self.assertRaises(ValueError):
                _P1.stage_run_layout(bad, directory, root=ROOT)

    def test_host_mode_pins_missing_root(self):
        self.assertIsNone(_P1.host_mode_pins(None)['host_mode'])
        with tempfile.TemporaryDirectory() as directory:
            pins = _P1.host_mode_pins(directory)
        self.assertIsNone(pins['host_mode']['pc_port/pc_p2_challenge_mode.h'])

    def test_host_mode_pins_real_native(self):
        native = ROOT / 'native'
        header = native / 'pc_port' / 'pc_p2_challenge_mode.h'
        if not header.is_file():
            self.skipTest('shared native host-mode module not present in this tree')
        pins = _P1.host_mode_pins(native)
        self.assertRegex(pins['host_mode']['pc_port/pc_p2_challenge_mode.h'], r'^[0-9a-f]{64}$')

    def test_p1_main_end_to_end(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = Path(directory) / 'manifest.json'
            manifest_path.write_text(json.dumps(good_manifest()), encoding='utf-8')
            out = Path(directory) / 'run'
            result = _P1.p1_main(manifest_path, out, root=ROOT)
            self.assertEqual(result['cave_id'], CAVE_ID)
            self.assertTrue((out / 'run-plan.json').is_file())

    def test_p1_main_bad_manifest_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = Path(directory) / 'manifest.json'
            manifest_path.write_text(json.dumps({'cave_id': 'wrong'}), encoding='utf-8')
            with self.assertRaises(ValueError):
                _P1.p1_main(manifest_path, Path(directory) / 'run', root=ROOT)

    def test_p1_main_unreadable_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                _P1.p1_main(Path(directory) / 'absent.json', Path(directory) / 'run', root=ROOT)


if __name__ == '__main__':
    unittest.main()
