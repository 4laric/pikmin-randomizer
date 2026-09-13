"""Opt-in J3D billboard (SHP1 shape matrix type 1) static fallback (#429).

Builds tiny synthetic J3D2bmd3 models (no disc assets) and checks that
``billboard='error'`` (the default) still rejects type 1, that
``billboard='static'`` is an explicitly recorded fallback that bakes the
authored geometry through the rigid joint draw matrix, and that stricter
defaults stay unchanged. Type 2 (Y-billboard) is deliberately out of scope.
"""
import tempfile
import unittest
from pathlib import Path

from experimental.pikmin2_convert import convert, decode, write_model
from test_pikmin2_convert_normals import TRIANGLE, UVS, build_model, normal_model


def billboard_model():
    return build_model(TRIANGLE, [(0., 1., 0.)], UVS, matrix_type=1)


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


if __name__ == '__main__':
    unittest.main()
