"""Validate the asset decoder against native field offsets and malformed input."""
import struct
import unittest

from audit_wollywog_cohort import parameters


class WollywogParameterTests(unittest.TestCase):
    def fixture(self):
        data = bytearray(368)
        struct.pack_into('>i', data, 0, 11)
        struct.pack_into('>i', data, 36, 1)
        struct.pack_into('>i', data, 116, 3)
        struct.pack_into('>f', data, 120, 1800)
        struct.pack_into('>f', data, 296, 24)
        struct.pack_into('>f', data, 348, 50)
        return data

    def test_native_offsets(self):
        result = parameters(self.fixture())
        self.assertEqual(result['corpse_type'], 1)
        self.assertEqual(result['jump_ready_loops'], 3)
        self.assertEqual(result['health'], 1800)
        self.assertEqual(result['collision_radius'], 24)
        self.assertEqual(result['impassable_distance'], 50)

    def test_reject_bad_layouts(self):
        data = self.fixture()
        for bad in (b'', data[:-1], data + b'\0', b'\0\0\0\x0a' + data[4:]):
            with self.subTest(size=len(bad)), self.assertRaises(ValueError):
                parameters(bad)

    def test_reject_nonfinite_even_in_unreported_field(self):
        for value in (float('nan'), float('inf'), -float('inf')):
            data = self.fixture()
            struct.pack_into('>f', data, 364, value)
            with self.assertRaises(ValueError): parameters(data)


if __name__ == '__main__':
    unittest.main()
