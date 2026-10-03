import struct
import unittest
from experimental.pikmin2_bridge_geometry import collision_prism


class BridgeCollisionLayout(unittest.TestCase):
    def test_native_reads_contiguous_room_indices_then_aligns_once(self):
        vertices = [(0, 0, 0), (1, 0, 0), (0, 0, 1)]
        for count in (1, 2, 13, 31):
            with self.subTest(rooms=count):
                rooms = [2*i for i in range(count)]
                data = collision_prism(vertices, [(count-1, (0, 1, 2))], rooms, 7)
                self.assertEqual(struct.unpack_from('>II', data, 8), (1, count))
                self.assertEqual(list(struct.unpack_from('>'+('i'*count), data, 32)), rooms)
                cursor = (32+4*count+31)//32*32
                row = struct.unpack_from('>IIIIhhhhffff', data, cursor)
                self.assertEqual(row[1:4], (7, 8, 9))
                self.assertEqual(row[4:8], (count-1, -1, -1, -1))
                self.assertEqual(len(data)%32, 0)

    def test_invalid_platform_room_or_vertex_is_refused(self):
        vertices = [(0, 0, 0), (1, 0, 0), (0, 0, 1)]
        for room, face in ((1, (0, 1, 2)), (0, (0, 1, 3))):
            with self.assertRaises(ValueError):
                collision_prism(vertices, [(room, face)], [2])


if __name__ == '__main__':
    unittest.main()
