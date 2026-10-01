import os
from pathlib import Path
import unittest

from experimental.pikmin2_equipment import (EXPLORATION_KIT_COUNT, ITEM_COUNT, ITEMS, KEY_INDEX, MENU_ROWS, OlimarData,
                                            by_config_name, course_unlocks, deliver_upgrade, detector_map_type,
                                            find_item_cutscene, item, specification)

# item_config.txt order from docs/PIKMIN2_CONTENT_INVENTORY.json; index == OlimarData::ItemIndex.
CONFIG_ORDER = ['fue_a', 'fue_b', 'fue_wide', 'fue_pullout', 'light_a', 'suit_powerup', 'suit_fire', 'dashboots',
                'radar_a', 'radar_b', 'map01', 'map02', 'key']
DICTIONARY = [188, 192, 194, 195, 190, 193, 191, 189, 186, 187, 184, 185, 196]


class TableTests(unittest.TestCase):
    def test_indices_names_and_dictionary_numbers(self):
        self.assertEqual(len(ITEMS), ITEM_COUNT)
        self.assertEqual([i['index'] for i in ITEMS], list(range(ITEM_COUNT)))
        self.assertEqual([i['config_name'] for i in ITEMS], CONFIG_ORDER)
        self.assertEqual([i['dictionary'] for i in ITEMS], DICTIONARY)
        self.assertEqual([i['exploration_kit'] for i in ITEMS], [True] * EXPLORATION_KIT_COUNT + [False])
        self.assertEqual(sorted(sum(map(list, MENU_ROWS), [])), list(range(EXPLORATION_KIT_COUNT)))
        self.assertTrue(all(i['triggers'] for i in ITEMS))
        self.assertEqual(by_config_name('key')['symbol'], 'ODII_TheKey')
        with self.assertRaises(ValueError):
            item(13)
        with self.assertRaises(ValueError):
            by_config_name('fue_c')

    def test_source_anchors_exist_when_native_is_available(self):
        root = Path(os.environ.get('PIKMIN2_SOURCE', Path(__file__).resolve().parents[1] / 'native' / 'pikmin2-research'))
        if not (root / 'include' / 'Game' / 'gamePlayData.h').exists():
            self.skipTest('native/pikmin2-research is not available in this checkout')
        for record in ITEMS:
            for trigger in record['triggers']:
                text = (root / trigger['file']).read_text(encoding='utf-8', errors='replace')
                self.assertIn(trigger['symbol'], text, trigger)
        header = (root / 'include' / 'Game' / 'gamePlayData.h').read_text(encoding='utf-8', errors='replace')
        for record in ITEMS:
            self.assertIn(record['symbol'], header)


class StateTests(unittest.TestCase):
    def test_bit_layout_matches_source(self):
        state = OlimarData()
        self.assertEqual(state.get_item(0), [])
        self.assertEqual(state.flags, [0, 1])          # index < 8 lands in mFlags[1]
        self.assertEqual(state.get_item(10), [('open_course', 1)])
        self.assertEqual(state.flags, [4, 1])          # setDevelopSetting's mFlags[0] |= 4 is the Spherical Atlas
        self.assertEqual(state.get_item(11), [('open_course', 2)])
        self.assertEqual(state.to_bytes(), bytes([12, 1]))
        self.assertEqual(OlimarData.from_bytes(bytes([12, 1])).inventory(), state.inventory())
        self.assertEqual([i for i, has in enumerate(state.inventory()) if has], [0, 10, 11])
        self.assertEqual(state.get_item(0), [])         # duplicate receipts are idempotent
        self.assertEqual(state.flags, [12, 1])
        state.clear()
        self.assertEqual(state.flags, [0, 0])
        for bad in (-1, KEY_INDEX, 12, 13, '0'):
            with self.assertRaises(ValueError):
                state.has_item(bad)
            with self.assertRaises(ValueError):
                state.get_item(bad)
        with self.assertRaises(ValueError):
            OlimarData((256, 0))
        with self.assertRaises(ValueError):
            OlimarData.from_bytes(b'\0')

    def test_delivery_semantics_by_mode(self):
        state = OlimarData()
        self.assertEqual(deliver_upgrade(state, 'map01'), [('side_effect', 'open_course', 1), ('flag_set', 'ODII_SphericalAtlas', 'first')])
        self.assertEqual(deliver_upgrade(state, 'map01'), [('side_effect', 'open_course', 1), ('flag_set', 'ODII_SphericalAtlas', 'repeat')])
        self.assertEqual(deliver_upgrade(state, 'fue_a', 'challenge'), [])
        self.assertFalse(state.has_item(0))
        self.assertEqual(deliver_upgrade(state, 'key'), [('enable_challenge_game', 'PlayCommonData::enableChallengeGame')])
        self.assertEqual(deliver_upgrade(state, 'key', 'challenge'), [('interact_got_key', 'ItemBigFountain+ItemHole')])
        self.assertEqual(deliver_upgrade(state, 'key', 'versus'), [])
        self.assertEqual(state.to_bytes(), bytes([4, 0]))   # the Key never touches OlimarData
        with self.assertRaises(ValueError):
            deliver_upgrade(state, 'fue_a', 'story2')

    def test_map_types_cutscenes_and_course_unlocks(self):
        self.assertEqual([detector_map_type(d, n) for d, n in ((False, False), (True, False), (False, True), (True, True))], [0, 1, 2, 3])
        self.assertEqual(find_item_cutscene(10), dict(movie='s16_find_item_10', skip_distance_check=True, item='ODII_SphericalAtlas'))
        self.assertFalse(find_item_cutscene(7)['skip_distance_check'])
        state = OlimarData()
        self.assertEqual(course_unlocks(state, debt_paid=True), {0})
        state.get_item(11)
        self.assertEqual(course_unlocks(state, debt_paid=False), {0, 2})
        self.assertEqual(course_unlocks(state, debt_paid=True), {0, 2, 3})
        state.get_item(10)
        self.assertEqual(course_unlocks(state, debt_paid=True), {0, 1, 2, 3})
        self.assertEqual(specification()['items'][12]['config_name'], 'key')


if __name__ == '__main__':
    unittest.main()
