"""Hairy Bulborb (YellowChappy) static hair shape (owner report: no hair)."""
import unittest

from experimental import pikmin2_chappy_hair as hair


def _decoded():
    positions = [(0., 0., 0.), (1., 0., 0.), (0., 1., 0.), (0., 0., 1.)] * 3
    normals = [(0., 1., 0.), (1., 0., 0.), (0., 0., 1.), (0., -1., 0.)] * 3
    tris = [[{9: i, 10: i}, {9: i + 1, 10: i + 1}, {9: i + 2, 10: i + 2}] for i in range(0, 9, 3)]
    b = {'_render_states': [(0x101, 1, 0, 0, 0)], '_source_lighting': [dict(lit=True, color_vertex=False, alpha_vertex=False, rgba=(255,) * 4)],
         '_alpha_stages': [None], '_draw_order': [0]}
    return b, {9: positions, 10: normals}, [tris], [0]


class ChapppyHairTest(unittest.TestCase):
    def test_only_the_hairy_bulborb_gets_hair(self):
        self.assertEqual(hair.HAIR_SPECIES, ('YellowChappy',))

    def test_adds_one_untextured_lit_shape_with_spikes(self):
        b, arrays, shapes, mats = hair.add_hair(_decoded())
        self.assertEqual(len(shapes), 2)
        self.assertEqual(mats, [0, -1])
        self.assertEqual(len(b['_render_states']), 2)
        self.assertEqual(b['_source_lighting'][1]['rgba'], hair.HAIR_RGBA)
        self.assertEqual(b['_draw_order'], [0, 1])
        self.assertEqual(len(shapes[1]) % 2, 0)  # two crossed triangles per strand
        for tri in shapes[1]:
            for v in tri:
                self.assertLess(v[9], len(arrays[9]))
                self.assertLess(v[10], len(arrays[10]))

    def test_deterministic(self):
        self.assertEqual(hair.add_hair(_decoded())[1], hair.add_hair(_decoded())[1])


if __name__ == '__main__':
    unittest.main()
