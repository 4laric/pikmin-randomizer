"""Opt-in J3D billboard (SHP1 shape matrix type 1) static fallback (#429).

Builds tiny synthetic J3D2bmd3 models (no disc assets) and checks that
``billboard='error'`` (the default) still rejects type 1, that
``billboard='static'`` is an explicitly recorded fallback that bakes the
authored geometry through the rigid joint draw matrix, and that stricter
defaults stay unchanged. Type 2 (Y-billboard) is deliberately out of scope.
"""
import struct
import tempfile
import unittest
from pathlib import Path

from experimental.pikmin2_convert import convert, decode, write_model
from pikmin2_synthetic_model import TRIANGLE, UVS, build_model, normal_model


def billboard_model():
    return build_model(TRIANGLE, [(0., 1., 0.)], UVS, matrix_type=1)


def native_billboard_model():
    # Axis-aligned rigid joint placed away from the model origin.
    return build_model(TRIANGLE, [(0., 1., 0.)], UVS, matrix_type=1,
                       joint_translation=(3.0, 5.0, -2.0))


def _chunk_offsets(data):
    offsets = {}
    at = 0
    while at + 8 <= len(data):
        tag, length = struct.unpack_from('>II', data, at)
        offsets[tag] = at
        if tag == 0xFFFF:
            break
        at = at + 8 + length
    return offsets


def _mesh_flags_and_joint_translation(path):
    data = Path(path).read_bytes()
    offsets = _chunk_offsets(data)
    # Chunk tag/len header (8) + one count (4), padded to a 32-byte boundary.
    mesh = offsets[0x50]
    flags = struct.unpack_from('>I', data, mesh + 32 + 4)[0]
    joint = offsets[0x60]
    scale = struct.unpack_from('>3f', data, joint + 32 + 36)
    translation = struct.unpack_from('>3f', data, joint + 32 + 60)
    return flags, scale, translation


def y_billboard_model():
    return build_model(TRIANGLE, [(0., 1., 0.)], UVS, matrix_type=2)


class BillboardFallbackTests(unittest.TestCase):
    def test_default_still_rejects_type_one(self):
        for bake in (False, True):
            with self.assertRaisesRegex(ValueError, 'Unsupported shape matrix type'):
                decode(billboard_model(), True, bake_rigid=bake)

    def test_invalid_mode_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported billboard mode'):
            decode(billboard_model(), True, bake_rigid=True, billboard='bogus')

    def test_static_requires_baking(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported shape matrix type'):
            decode(billboard_model(), True, bake_rigid=False, billboard='static')

    def test_y_billboard_stays_out_of_scope(self):
        for matrix_type in (2, 4):
            model = build_model(TRIANGLE, [(0., 1., 0.)], UVS, matrix_type=matrix_type)
            with self.assertRaisesRegex(ValueError, 'Unsupported shape matrix type'):
                decode(model, True, bake_rigid=True, billboard='static')

    def test_static_bakes_authored_geometry_unchanged(self):
        _, base_arrays, base_shapes, base_mats = decode(normal_model(), True, bake_rigid=True)
        _, arrays, shapes, mats = decode(billboard_model(), True, bake_rigid=True,
                                         billboard='static')
        # No vertices are moved or fabricated: the billboard shape is baked
        # through the same rigid joint draw matrix as a basic shape.
        self.assertEqual(arrays[9], base_arrays[9])
        self.assertEqual(arrays[10], base_arrays[10])
        self.assertEqual(len(shapes), len(base_shapes))
        self.assertEqual(mats, base_mats)

    def test_report_records_fallback_and_affected_shapes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'billboard.mod'
            report = write_model(decode(billboard_model(), True, bake_rigid=True,
                                        billboard='static'),
                                 path, 'synthetic.bmd')
            self.assertEqual(report['billboard_policy'], 'static')
            self.assertEqual(report['billboard_shapes'], [0])
            self.assertEqual(report['billboard_materials'], [0])
            self.assertIn('not reproduced', report['billboard_note'])
            self.assertTrue(path.exists())

    def test_strict_report_has_no_billboard_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'base.mod'
            report = write_model(decode(normal_model(), True, bake_rigid=True),
                                 path, 'synthetic.bmd')
            for key in ('billboard_policy', 'billboard_shapes', 'billboard_materials',
                        'billboard_note'):
                self.assertNotIn(key, report)

    def test_mode_with_no_billboard_shape_records_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            report = write_model(decode(normal_model(), True, bake_rigid=True,
                                        billboard='static'),
                                 Path(directory) / 'base.mod', 'synthetic.bmd')
            self.assertNotIn('billboard_policy', report)

    def test_convert_passes_billboard_policy_through(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'billboard.bmd'
            source.write_bytes(billboard_model())
            report = convert(source, Path(directory) / 'billboard.mod',
                             approximate_materials=True, bake_rigid=True,
                             billboard='static')
            self.assertEqual(report['billboard_policy'], 'static')
            with self.assertRaisesRegex(ValueError, 'Unsupported shape matrix type'):
                convert(source, Path(directory) / 'strict.mod',
                        approximate_materials=True, bake_rigid=True)


class NativeBillboardTests(unittest.TestCase):
    """Opt-in camera-facing billboard emit path (#429)."""

    def test_native_requires_baking(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported shape matrix type'):
            decode(billboard_model(), True, bake_rigid=False, billboard='native')

    def test_native_flag_and_joint_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native.mod'
            report = write_model(
                decode(native_billboard_model(), True, bake_rigid=True,
                       billboard='native'),
                path, 'synthetic.bmd')
            self.assertEqual(report['billboard_policy'], 'native')
            self.assertEqual(report['billboard_shapes'], [0])
            self.assertEqual(report['billboard_pivot'], [3.0, 5.0, -2.0])
            self.assertAlmostEqual(report['billboard_scale'], 1.0)
            self.assertIn('camera-facing', report['billboard_note'])
            flags, scale, translation = _mesh_flags_and_joint_translation(path)
            self.assertTrue(flags & (1 << 17), 'billboard feature flag set')
            self.assertEqual(scale, (1.0, 1.0, 1.0))
            self.assertEqual(translation, (3.0, 5.0, -2.0))

    def test_native_geometry_is_pivot_relative(self):
        _, base_arrays, _, _ = decode(native_billboard_model(), True, bake_rigid=True,
                                      billboard='static')
        _, arrays, _, _ = decode(native_billboard_model(), True, bake_rigid=True,
                                 billboard='native')
        expected = [(x - 3.0, y - 5.0, z + 2.0) for x, y, z in base_arrays[9]]
        for got, want in zip(arrays[9], expected):
            for a, b in zip(got, want):
                self.assertAlmostEqual(a, b)
        # Normals are unaffected by the pivot/scale change.
        self.assertEqual(arrays[10], base_arrays[10])

    def test_native_uniform_scale_divided_out(self):
        # A unit-scale model is the reference local geometry.
        _, reference, _, _ = decode(billboard_model(), True, bake_rigid=True,
                                    billboard='static')
        # The synthetic DRW1 has one draw entry; supply the scaled joint matrix
        # explicitly to bypass the scalar-shape bind-pose restriction.
        matrix = [[0.5, 0.0, 0.0, 3.0],
                  [0.0, 0.5, 0.0, 5.0],
                  [0.0, 0.0, 0.5, -2.0]]
        _, arrays, _, _ = decode(native_billboard_model(), True, bake_rigid=True,
                                 draw_matrices=[matrix], billboard='native')
        for got, want in zip(arrays[9], reference[9]):
            for a, b in zip(got, want):
                self.assertAlmostEqual(a, b)

    def test_native_rejects_rotated_joint(self):
        matrix = [[0.0, -1.0, 0.0, 0.0],
                  [1.0, 0.0, 0.0, 0.0],
                  [0.0, 0.0, 1.0, 0.0]]
        with self.assertRaisesRegex(ValueError, 'axis-aligned'):
            decode(native_billboard_model(), True, bake_rigid=True,
                   draw_matrices=[matrix], billboard='native')

    def test_native_rejects_non_uniform_scale(self):
        matrix = [[0.5, 0.0, 0.0, 0.0],
                  [0.0, 1.0, 0.0, 0.0],
                  [0.0, 0.0, 1.0, 0.0]]
        with self.assertRaisesRegex(ValueError, 'uniform positive'):
            decode(native_billboard_model(), True, bake_rigid=True,
                   draw_matrices=[matrix], billboard='native')

    def test_static_mode_never_sets_the_native_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'static.mod'
            write_model(decode(native_billboard_model(), True, bake_rigid=True,
                               billboard='static'),
                        path, 'synthetic.bmd')
            flags, _, _ = _mesh_flags_and_joint_translation(path)
            self.assertFalse(flags & (1 << 17))


if __name__ == '__main__':
    unittest.main()