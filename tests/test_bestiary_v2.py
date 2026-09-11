import unittest
from collections import Counter
from randomizer.seed import generate, validate
from randomizer.catalog import *

class BestiaryV2Tests(unittest.TestCase):
    def test_catalog_compatibility(self):
        for permanent in (False, True):
            old = generate('compat', collection_checks=True, permanent_checks=permanent, legacy_checks=True)
            new = generate('compat', collection_checks=True, permanent_checks=permanent)
            validate(old); validate(new)
            self.assertEqual(len(new['locations']), 158 if permanent else 77)
            self.assertEqual(len(NEW_BESTIARY), 11)
            for n, ident in new['locations'].items():
                self.assertFalse(n.startswith('Explore:'))
                if n in old['locations']: self.assertEqual(ident, old['locations'][n])
            self.assertEqual(len(new['locations']), len(set(new['locations'].values())))
            self.assertTrue(any(n.endswith(' - Scout') for n in old['locations']))
    def test_routes_and_pool(self):
        m = generate('logic', collection_checks=True, starting_flarlic=1)
        full = Counter(progression_pool(m))
        for name in NEW_BESTIARY:
            self.assertFalse(can_reach_manifest(name, {}, m))
            self.assertTrue(can_reach_manifest(name, full, m))
        full[FLARLIC] = 0
        self.assertFalse(can_reach_manifest('Bestiary: Deliver Armored Cannon Beetle', full, m))
        full[FLARLIC] = 2
        self.assertTrue(can_reach_manifest('Bestiary: Deliver Armored Cannon Beetle', full, m))
        self.assertFalse(can_reach_manifest('Explore: The Forest of Hope - Scout', full, m))
        self.assertGreaterEqual(item_pool(m).count(REPAIR), 25)

    def test_existing_landing_manifest(self):
        m = generate('previous', collection_checks=True)
        m.pop('benefit_items'); m['capabilities'].remove('benefit-items-v1')
        m.pop('color_population')
        m['capabilities'].remove('color-population-v1')
        m.pop('no_exploration')
        m['capabilities'][m['capabilities'].index('no-exploration-v1')] = 'landing-only-v1'
        m['locations'] = {n: MODERN_LOCATION_IDS[n] for n in modern_names(False)}
        validate(m)
        self.assertEqual(len(active_names(m)), 64)
        self.assertTrue(can_reach_manifest('Explore: The Forest of Hope - Land', {}, m))
