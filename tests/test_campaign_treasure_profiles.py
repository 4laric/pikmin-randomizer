import hashlib
import unittest
from unittest.mock import patch

from experimental.pikmin2_campaign_treasures import source_profiles


class TreasureSourceProfiles(unittest.TestCase):
    def setUp(self):
        self.item = (b'1 { name fixture dictionary 184 money 200 min 101 max 101 '
                     b'radius 52 p_radius 53 height 50 inertiascaling 750 friction 0.1 dynamics lod end }')
        self.raw = {'item': self.item, 'otakara': b'0'}
        self.entries = {'fixture': dict(kind='item', dictionary=184, value=200, minimum=101, maximum=101)}
        self.pins = {kind: hashlib.sha256(data).hexdigest() for kind, data in self.raw.items()}

    def verify(self, raw=None, entries=None):
        with patch('experimental.pikmin2_campaign_treasures.CONFIG_SHA256', self.pins):
            return source_profiles(raw or self.raw, entries or self.entries, ['fixture'])

    def test_loose_profile_preserves_original_101_strength_and_dimensions(self):
        result = self.verify()['fixture']
        self.assertEqual(result['source']['min'], '101')
        self.assertEqual(result['source']['max'], '101')
        self.assertEqual(result['physics'], dict(radius=52., p_radius=53., height=50.,
                                                inertiascaling=750., friction=.1, dynamics='lod'))

    def test_changed_source_bytes_and_catalog_dictionary_refuse(self):
        with self.assertRaisesRegex(ValueError, 'source hash'):
            self.verify(dict(self.raw, item=self.item + b' '))
        with self.assertRaisesRegex(ValueError, 'pinned catalog'):
            self.verify(entries={'fixture': dict(self.entries['fixture'], dictionary=185)})

    def test_nonfinite_and_negative_source_physics_refuse_even_when_hash_matches(self):
        for replacement in (b'radius nan', b'radius -1', b'radius 0'):
            raw = dict(self.raw, item=self.item.replace(b'radius 52', replacement))
            self.pins['item'] = hashlib.sha256(raw['item']).hexdigest()
            with self.subTest(replacement=replacement), self.assertRaisesRegex(ValueError, 'physics'):
                self.verify(raw)


if __name__ == '__main__':
    unittest.main()
