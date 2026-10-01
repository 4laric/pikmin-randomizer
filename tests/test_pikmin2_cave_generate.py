"""Focused unit tests for the cave generation provider contract
(lane cave-generate-provider, issue #129).

Hermetic: no binary, no ISO, no assets required. The normative sidecar
rules, rotation math, room bounds, and anchor derivation are tested here;
the native mirror is proven at runtime by the fresh-arena harness, which
recomputes every marker and fails on drift.
"""
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import importlib.util

_SPEC = importlib.util.spec_from_file_location(
    'cave_generate_proving',
    ROOT / 'experimental' / 'pikmin2_cave_generate_proving.py')
_PROVING = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_PROVING)


def good_manifest():
    return {'pool': 'pool_a.txt',
            'units': [{'name': 'room_a', 'w': 100.0, 'd': 80.0, 'kind': 0},
                      {'name': 'room_b', 'w': 60.0, 'd': 60.0, 'kind': 1}],
            'rooms': [{'unit': 0, 'turn': 0, 'offset': [0.0, 0.0, 0.0],
                       'w': 100.0, 'd': 80.0},
                      {'unit': 1, 'turn': 1, 'offset': [600.0, 0.0, 0.0],
                       'w': 60.0, 'd': 60.0}],
            'doors': [{'unit': 0, 'id': 0, 'dir': 1},
                      {'unit': 1, 'id': 0, 'dir': 3}],
            'links': [{'unit': 0, 'door': 0, 'peer': 1, 'pdoor': 0, 'dist': 12.5}],
            'spawns': [{'id': 'Chappy', 'count': 2}],
            'anchor_kind': 'hole'}


class RotationTests(unittest.TestCase):
    def test_quarter_turns(self):
        self.assertEqual(_PROVING.rotate([1.0, 0.0, 0.0], 0), [1.0, 0.0, 0.0])
        self.assertEqual(_PROVING.rotate([1.0, 0.0, 0.0], 1), [0.0, 0.0, 1.0])
        self.assertEqual(_PROVING.rotate([1.0, 0.0, 0.0], 2), [-1.0, 0.0, 0.0])
        self.assertEqual(_PROVING.rotate([1.0, 0.0, 0.0], 3), [0.0, 0.0, -1.0])
        self.assertEqual(_PROVING.rotate([1.0, 0.0, 0.0], 4 % 4), [1.0, 0.0, 0.0])

    def test_rotation_rejects_bad_input(self):
        for point, turn in (([1.0, 0.0], 0), ([1.0, 0.0, 0.0], 4),
                            ([1.0, 0.0, 0.0], -1),
                            ([float('inf'), 0.0, 0.0], 0)):
            with self.subTest(point=point, turn=turn):
                with self.assertRaises(_PROVING.ContractViolation):
                    _PROVING.rotate(point, turn)

    def test_room_bounds_axis_aligned(self):
        lo, hi = _PROVING.room_bounds(100.0, 80.0, 0, [10.0, 0.0, 20.0])
        self.assertEqual((lo, hi), ([-40.0, 0.0, -20.0], [60.0, 0.0, 60.0]))

    def test_room_bounds_rotated_swaps_extents(self):
        lo, hi = _PROVING.room_bounds(100.0, 80.0, 1, [0.0, 0.0, 0.0])
        self.assertEqual((lo, hi), ([-40.0, 0.0, -50.0], [40.0, 0.0, 50.0]))

    def test_anchor_derivation_and_clamp(self):
        rooms = [{'offset': [5.0, 1.0, 6.0], 'w': 100.0, 'd': 80.0}]
        anchor = _PROVING.derive_anchor(rooms, 'hole')
        self.assertEqual((anchor['x'], anchor['y'], anchor['z']), (5.0, 1.0, 6.0))
        self.assertAlmostEqual(anchor['radius'], math.hypot(100.0, 80.0) / 2)
        tiny = _PROVING.derive_anchor([{'offset': [0.0, 0.0, 0.0], 'w': 2.0, 'd': 2.0}], 'geyser')
        self.assertEqual(tiny['radius'], 20.0)
        huge = _PROVING.derive_anchor([{'offset': [0.0, 0.0, 0.0], 'w': 1000.0, 'd': 1000.0}], 'hole')
        self.assertEqual(huge['radius'], 150.0)
        with self.assertRaises(_PROVING.ContractViolation):
            _PROVING.derive_anchor([], 'hole')
        with self.assertRaises(_PROVING.ContractViolation):
            _PROVING.derive_anchor(rooms, 'cave')


class SidecarTests(unittest.TestCase):
    def test_roundtrip(self):
        text = _PROVING.render_sidecar(good_manifest())
        manifest = _PROVING.validate_sidecar(text)
        self.assertEqual(manifest['pool'], 'pool_a.txt')
        self.assertEqual(len(manifest['rooms']), 2)
        self.assertEqual(manifest['anchor_kind'], 'hole')

    def test_malformed_battery(self):
        good = _PROVING.render_sidecar(good_manifest())
        cases = [
            good.replace('P2_CAVE_GENERATE_1', 'P2_CAVE_GENERATE_0'),
            good.replace('pool pool_a.txt 2', 'pool pool_a.txt 3'),
            good.replace('unit 0 room_a', 'unit 1 room_a'),
            good.replace('room 1 1 1 ', 'room 1 1 7 '),
            good.replace('room 1 1 1 600', 'room 1 9 1 600'),
            good.replace('door 1 0 3', 'door 1 0 9'),
            good.replace('link 0 0 1 0 12.5', 'link 0 0 9 0 12.5'),
            good.replace('link 0 0 1 0 12.5', 'link 0 0 1 0 -1'),
            good.replace('spawn Chappy 2', 'spawn Chappy 0'),
            good.replace('spawn Chappy 2', 'spawn  2'),
            good.replace('anchor hole', 'anchor cave'),
            good + 'trailing garbage\n',
            good.replace('rooms 2', 'rooms 1'),
            '',
            '   \n',
        ]
        for text in cases:
            with self.subTest(text=text[:48]):
                with self.assertRaises(_PROVING.ContractViolation):
                    _PROVING.validate_sidecar(text)

    def test_token_shapes(self):
        for bad in ('../pool.txt', 'a b', '', 'x' * 129):
            with self.subTest(bad=bad[:12]):
                with self.assertRaises(_PROVING.ContractViolation):
                    _PROVING.check_token(bad)
        self.assertEqual(_PROVING.check_token('$Egg', dollar=True), '$Egg')
        with self.assertRaises(_PROVING.ContractViolation):
            _PROVING.check_token('$Egg')


class VerifyTests(unittest.TestCase):
    def test_verify_recomputes_markers(self):
        text = '\n'.join([
            'P2_CAVE_READY floor=1 survivors=20 health=1',
            'P2_CAVE_GENERATE_POOL pool=pool_a.txt units=2',
            'P2_CAVE_GENERATE_ROOM idx=0 unit=0 turn=0 x0=-50.000 y0=0.000 z0=-40.000 x1=50.000 y1=0.000 z1=40.000',
            'P2_CAVE_GENERATE_ROOM idx=1 unit=1 turn=1 x0=570.000 y0=0.000 z0=-30.000 x1=630.000 y1=0.000 z1=30.000',
            'P2_CAVE_GENERATE_SPAWN id=Chappy count=2',
            'P2_CAVE_GENERATE_LINKS total=1 symmetric=0',
            'P2_CAVE_GENERATE_ANCHOR kind=hole x=0.000 y=0.000 z=0.000 radius=64.031',
            'P2_CAVE_GENERATE_PASS rooms=2 spawns=1 links=1 anchor=hole',
        ]) + '\n'
        result = _PROVING.verify_run(text, good_manifest())
        self.assertEqual(result['rooms'], 2)
        self.assertEqual(result['anchor']['kind'], 'hole')

    def test_verify_rejects_refusal_and_missing_ready(self):
        with self.assertRaises(_PROVING.ContractViolation):
            _PROVING.verify_run('P2_CAVE_READY floor=1\nP2_CAVE_GENERATE_REFUSED reason=bad-manifest\n',
                                good_manifest())
        with self.assertRaises(_PROVING.ContractViolation):
            _PROVING.verify_run('P2_CAVE_GENERATE_PASS rooms=2 spawns=1 links=1 anchor=hole\n',
                                good_manifest())

    def test_verify_rejects_drift(self):
        text = ('P2_CAVE_READY floor=1\n'
                'P2_CAVE_GENERATE_POOL pool=pool_a.txt units=2\n'
                'P2_CAVE_GENERATE_ROOM idx=0 unit=0 turn=0 x0=0.000 y0=0.000 z0=0.000 x1=1.000 y1=0.000 z1=1.000\n')
        with self.assertRaises(_PROVING.ContractViolation):
            _PROVING.verify_run(text, good_manifest())


if __name__ == '__main__':
    unittest.main()