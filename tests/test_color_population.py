import copy
import unittest
from randomizer.catalog import (COLOR_POPULATION, MODERN_LOCATION_IDS, population_checks,
    modern_names, active_names, can_reach_manifest, FOREST_ACCESS)
from randomizer.seed import generate, validate


class ColorPopulationTests(unittest.TestCase):
    def test_catalog_and_old_seed(self):
        self.assertEqual(len(MODERN_LOCATION_IDS), len(set(MODERN_LOCATION_IDS.values())))
        for permanent in (False, True):
            m = generate('colors', collection_checks=True, permanent_checks=permanent)
            self.assertEqual(len(population_checks(m)), 57 if permanent else 27)
            self.assertTrue(all(name in COLOR_POPULATION for name in active_names(m) if name.startswith('Population:')))
            old = copy.deepcopy(m)
            old.pop('color_population'); old['capabilities'].remove('color-population-v1')
            old['locations'] = {n: MODERN_LOCATION_IDS[n] for n in modern_names(permanent, True)}
            validate(old)
            self.assertEqual(len(active_names(old)), 120 if permanent else 59)
            bad = copy.deepcopy(m); bad['locations'] = old['locations']
            with self.assertRaises(ValueError): validate(bad)

    def test_matching_onion_and_farming_required(self):
        for starting in ('red', 'yellow', 'blue'):
            m = generate('colors', collection_checks=True, starting_area='spring', starting_color=starting, starting_flarlic=1)
            for color in ('Red', 'Yellow', 'Blue'):
                low = f'Population: 20 total {color} Pikmin'
                high = f'Population: 500 total {color} Pikmin'
                self.assertEqual(can_reach_manifest(low, {}, m), color.lower() == starting)
                self.assertFalse(can_reach_manifest(high, {}, m))
                self.assertEqual(can_reach_manifest(high, {FOREST_ACCESS: 1}, m), color.lower() == starting)
                self.assertTrue(can_reach_manifest(high, {FOREST_ACCESS: 1, color + ' Onion': 1}, m))
