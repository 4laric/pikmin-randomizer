import unittest

from experimental.pikmin2_cave_water import (
    WATER_SCHEMA,
    validate_water_sidecar,
    water_unit_sidecar,
)
from experimental.pikmin2_collision import ATTR_WATER, water_tagged_mapcodes


EMPTY_TREE = '0\n# type\n{\n 0\n}\n'
SINGLE_BOX = '0 { 1 -408 -102 -428 272 -2 372 }'
TWO_BOXES = '0 { 2 -10 -20 -30 10 5 30 40 -7 40 60 -2 80 }'


def room_with(minimum, maximum):
    return {'bounds': {'min': list(minimum), 'max': list(maximum)}}


class WaterUnitSidecarTests(unittest.TestCase):
    def test_empty_tree(self):
        sidecar = water_unit_sidecar(EMPTY_TREE)
        self.assertTrue(sidecar['empty'])
        self.assertEqual(sidecar['boxes'], [])
        self.assertEqual(sidecar['count'], 0)
        self.assertIsNone(sidecar['surface'])
        self.assertIsNone(sidecar['runtime_min_y'])

    def test_single_real_box(self):
        sidecar = water_unit_sidecar(SINGLE_BOX)
        self.assertEqual(sidecar['count'], 1)
        self.assertEqual(sidecar['boxes'][0]['min'], [-408.0, -102.0, -428.0])
        self.assertEqual(sidecar['boxes'][0]['max'], [272.0, -2.0, 372.0])
        self.assertEqual(sidecar['surface'], -2.0)
        self.assertEqual(sidecar['runtime_min_y'], -1102.0)

    def test_two_boxes_aggregate_extremes(self):
        sidecar = water_unit_sidecar(TWO_BOXES)
        self.assertEqual(sidecar['count'], 2)
        self.assertEqual(sidecar['surface'], max(5.0, -2.0))
        self.assertEqual(sidecar['runtime_min_y'], min(-20.0 - 1000.0, -7.0 - 1000.0))

    def test_comments_and_whitespace_tolerated(self):
        text = ('0 # version\n{\n  # open\n 1 # count\n'
                ' -408   -102   -428\n 272 -2 372 # box\n}\n')
        self.assertEqual(water_unit_sidecar(text), water_unit_sidecar(SINGLE_BOX))

    def test_malformed_inputs_raise(self):
        malformed = {
            'wrong version': '1 { 0 }',
            'non-numeric': '0 { 1 a 0 0 1 1 1 }',
            'count mismatch': '0 { 2 0 0 0 1 1 1 }',
            'non-finite': '0 { 1 0 0 0 1 nan 1 }',
            'inverted box': '0 { 1 1 0 0 0 1 1 }',
        }
        for label, text in malformed.items():
            with self.subTest(label=label), self.assertRaises(ValueError):
                water_unit_sidecar(text)

    def test_honest_native_flags(self):
        sidecar = water_unit_sidecar(SINGLE_BOX)
        self.assertEqual(sidecar['schema'], WATER_SCHEMA)
        self.assertFalse(sidecar['native_consumer_implemented'])
        self.assertFalse(sidecar['dynamic_lowering_supported'])

    def test_deterministic(self):
        self.assertEqual(water_unit_sidecar(SINGLE_BOX), water_unit_sidecar(SINGLE_BOX))
        self.assertEqual(water_unit_sidecar(TWO_BOXES), water_unit_sidecar(TWO_BOXES))


class ValidateWaterSidecarTests(unittest.TestCase):
    def setUp(self):
        self.sidecar = water_unit_sidecar(SINGLE_BOX)
        self.room = room_with([-500.0, -200.0, -500.0], [300.0, 100.0, 400.0])

    def test_inside_bounds_passes(self):
        self.assertTrue(validate_water_sidecar(self.sidecar, self.room))

    def test_y_is_unconstrained(self):
        deep = room_with([-500.0, 900.0, -500.0], [300.0, 2000.0, 400.0])
        self.assertTrue(validate_water_sidecar(self.sidecar, deep))

    def test_outside_x_raises(self):
        narrow = room_with([-100.0, -200.0, -500.0], [300.0, 100.0, 400.0])
        with self.assertRaises(ValueError) as caught:
            validate_water_sidecar(self.sidecar, narrow)
        self.assertIn('min X', str(caught.exception))

    def test_outside_z_raises(self):
        shallow = room_with([-500.0, -200.0, -100.0], [300.0, 100.0, 100.0])
        with self.assertRaises(ValueError) as caught:
            validate_water_sidecar(self.sidecar, shallow)
        self.assertIn('Z', str(caught.exception))

    def test_schema_mismatch_raises(self):
        bad = dict(self.sidecar, schema=WATER_SCHEMA + 1)
        with self.assertRaises(ValueError):
            validate_water_sidecar(bad, self.room)

    def test_count_mismatch_raises(self):
        bad = dict(self.sidecar, count=self.sidecar['count'] + 1)
        with self.assertRaises(ValueError):
            validate_water_sidecar(bad, self.room)


class WaterCollisionTaggingTests(unittest.TestCase):
    ROOM = {
        'vertices': [[-5.0, 0.0, -5.0], [5.0, 0.0, -5.0], [0.0, 0.0, 5.0]],
        'triangles': [[0, 1, 2]],
        'mapcodes': [1],
    }

    def sidecar(self, text):
        return water_unit_sidecar(text)

    def test_submerged_floor_is_tagged_water(self):
        boxes = self.sidecar('0 { 1 -20 -20 -20 20 -2 20 }')['boxes']
        tagged = water_tagged_mapcodes(self.ROOM, [0], boxes)
        self.assertEqual(tagged[0] >> 29, ATTR_WATER)
        self.assertNotEqual(tagged[0], 0)

    def test_outside_box_is_not_tagged(self):
        boxes = self.sidecar('0 { 1 100 -20 100 200 -2 200 }')['boxes']
        self.assertEqual(water_tagged_mapcodes(self.ROOM, [0], boxes), [0])

    def test_downward_face_is_not_tagged(self):
        room = {'vertices': self.ROOM['vertices'], 'triangles': [[0, 2, 1]]}
        boxes = self.sidecar('0 { 1 -20 -20 -20 20 -2 20 }')['boxes']
        self.assertEqual(water_tagged_mapcodes(room, [0], boxes), [0])

    def test_empty_boxes_leave_codes_unchanged(self):
        self.assertEqual(water_tagged_mapcodes(self.ROOM, [0], []), [0])


if __name__ == '__main__':
    unittest.main()
