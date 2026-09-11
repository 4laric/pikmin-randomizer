from collections import Counter
import tempfile
import unittest
from randomizer.catalog import item_pool, can_reach_manifest, RED, BLUE, YELLOW, SPRING_ACCESS
from randomizer.seed import generate, solo_rewards, spheres, validate
from randomizer.session import Session
from randomizer.runner import NativeRun


class EnemyShuffleTests(unittest.TestCase):
    def test_all_masks_solvable(self):
        seen = set()
        for seed in range(200):
            m = generate(str(seed), enemy_shuffle=True, starting_area='random', starting_color='random')
            seen.add(m['enemy_mask'])
            self.assertEqual(m, generate(str(seed), enemy_shuffle=True, starting_area='random', starting_color='random'))
            rewards = solo_rewards(m)
            self.assertEqual(Counter(rewards.values()), Counter(item_pool(m)))
            self.assertEqual(sum(map(len, spheres(rewards, m))), 58)
        self.assertEqual(seen, set(range(1, 8)))

    def test_species_rules_and_recovery(self):
        m = generate('swaps', enemy_shuffle=True)
        m['enemy_mask'] = 7
        owned = {RED: 1, BLUE: 1, YELLOW: 1}
        for species in ('Spotty Bulborb',):
            self.assertFalse(can_reach_manifest('Bestiary: ' + species, owned, m))
            self.assertTrue(can_reach_manifest('Bestiary: ' + species, {**owned, SPRING_ACCESS: 1}, m))
        self.assertTrue(can_reach_manifest('Bestiary: Dwarf Bulborb', {}, m))
        with tempfile.TemporaryDirectory() as directory:
            session = Session(m, directory)
            run = NativeRun(session)
            self.assertIn('ENEMIES 7', run.bootstrap.read_text())
            (run.directory / 'checks.txt').write_text('30\n')
            self.assertEqual(len(Session(m, directory).data['checked']), 1)
        m['enemy_mask'] = 8
        with self.assertRaises(ValueError): validate(m)
