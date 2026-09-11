import unittest
from collections import Counter
from randomizer.catalog import (TOTAL_POPULATION, DELIVERY_BESTIARY, ALL_AREA_LOCATION_IDS,
    COLLECTION_LOCATION_IDS, BLUE, RED, YELLOW, FOREST_ACCESS, can_reach_manifest, active_names)
from randomizer.seed import generate, validate, solo_rewards, spheres


class CollectionChecksTest(unittest.TestCase):
    def test_version_and_unique_ids(self):
        old = generate('old', enemy_shuffle=True)
        new = generate('new', collection_checks=True)
        validate(old); validate(new)
        self.assertEqual((old['schema'], new['schema']), (6, 9))
        combined = {**ALL_AREA_LOCATION_IDS, **COLLECTION_LOCATION_IDS}
        self.assertEqual(len(combined), len(set(combined.values())))
        self.assertEqual(len(active_names(new)), 64)
        self.assertIn('Population: 100 Pikmin in the field', old['locations'])
        self.assertNotIn('Population: 100 Pikmin in the field', new['locations'])

    def test_total_population_does_not_need_flarlic(self):
        m = generate('farm', collection_checks=True)
        for name in TOTAL_POPULATION:
            self.assertTrue(can_reach_manifest(name, Counter(), m))
        water = generate('water', starting_area='spring', collection_checks=True)
        self.assertFalse(can_reach_manifest('Population: 500 total Pikmin', Counter(), water))
        self.assertTrue(can_reach_manifest('Population: 500 total Pikmin', Counter({FOREST_ACCESS: 1}), water))

    def test_corpse_return_routes(self):
        m = generate('return', collection_checks=True)
        name = 'Bestiary: Deliver Dwarf Bulborb'
        self.assertFalse(can_reach_manifest(name, Counter(), m))
        self.assertTrue(can_reach_manifest(name, Counter({BLUE: 1, YELLOW: 1}), m))

    def test_solo_fills(self):
        for shuffle in (False, True):
            for seed in range(100):
                m = generate(str(seed), starting_area='random', starting_color='random',
                             enemy_shuffle=shuffle, collection_checks=True)
                self.assertEqual(sum(map(len, spheres(solo_rewards(m), m))), 64)
