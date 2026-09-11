import tempfile
import unittest
from randomizer.catalog import START_AREAS, ALL_LOCATION_IDS, ALL_AREA_LOCATION_IDS, POSITRON, IMPACT_ACCESS, ITEM_IDS, item_pool, can_reach_manifest, BLUE
from randomizer.seed import generate, solo_rewards, spheres
from randomizer.runner import NativeRun
from randomizer.session import Session


class AllAreaTests(unittest.TestCase):
    def test_all_fifteen_pairs(self):
        for area in ('impact', 'forest', 'navel', 'spring', 'trial'):
            for color in ('red', 'yellow', 'blue'):
                for seed in range(20):
                    m = generate(str(seed), starting_area=area, starting_color=color, all_areas=True)
                    self.assertEqual(len(m['locations']), 58)
                    self.assertEqual(len(item_pool(m)), 58)
                    self.assertEqual(sum(map(len, spheres(solo_rewards(m), m))), 58)
                    self.assertNotIn(START_AREAS[m['profile']][2], item_pool(m))
        self.assertTrue(all(ALL_AREA_LOCATION_IDS[n] == i for n, i in ALL_LOCATION_IDS.items()))

    def test_water_start_waits_for_blue(self):
        for color in ('red', 'yellow'):
            m = generate('water', 'ap', starting_area='spring', starting_color=color)
            self.assertFalse(can_reach_manifest('Bestiary: Water Dumple', {}, m))
            self.assertTrue(can_reach_manifest('Bestiary: Water Dumple', {BLUE: 1}, m))
            self.assertFalse(can_reach_manifest('Population: 30 Pikmin in the field', {}, m))
            self.assertIn(BLUE, item_pool(m))
            initial = {n for n in m['locations'] if can_reach_manifest(n, {}, m)}
            self.assertEqual(initial, {'Explore: The Distant Spring - Land', 'Population: 20 Pikmin in the field'})

    def test_impact_high_ids_recover(self):
        m = generate('impact-check', 'ap', starting_area='trial')
        with tempfile.TemporaryDirectory() as d:
            session = Session(m, d)
            session.bind_ap('test', 0, 1)
            session.receive(0, [ITEM_IDS[IMPACT_ACCESS]])
            run = NativeRun(session)
            self.assertIn(' 128 ', session.native_state(run.token, True))
            (run.directory / 'checks.txt').write_text('55\n56\n57\n')
            restored = Session(m, d)
            self.assertIn(POSITRON, restored.data['checked'])
            self.assertEqual(len(restored.data['checked']), 3)
