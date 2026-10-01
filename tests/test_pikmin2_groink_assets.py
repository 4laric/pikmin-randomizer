import unittest
from experimental.pikmin2_groink_assets import profile, muzzle


class GroinkAssetsTests(unittest.TestCase):
    def test_general_parameters_do_not_flatten_variant_blocks(self):
        raw = b'{ {fp00} 4 700 {fp14} 4 250 {fp22} 4 15 {fp23} 4 65 {fp24} 4 10 {_eof} }'
        parsed = profile(raw+b'{ {fp14} 4 999 {_eof} }')
        self.assertEqual(parsed['general']['search_distance'], 250)
        self.assertEqual(parsed['general']['health'], 700)
        for invalid in (raw+raw, raw.replace(b'250', b'0'), raw.replace(b'700', b'nan')):
            with self.assertRaises(ValueError):
                profile(invalid)

    def test_muzzle_uses_normalized_column_zero_and_25_offset(self):
        result = muzzle([[0, 1, 0, 4], [2, 0, 0, 5], [0, 0, 1, 6]])
        self.assertEqual(result['forward'], [0, 1, 0])
        self.assertEqual(result['position'], [4, 30, 6])
        for invalid in ([[0]*4]*3, [[1, 0, 0, float('inf')]]*3, [[1]]):
            with self.assertRaises(ValueError):
                muzzle(invalid)
