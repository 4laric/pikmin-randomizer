import copy
import unittest
from collections import Counter

from randomizer.seed import generate, validate, solo_rewards, spheres
from randomizer.catalog import population_checks, item_pool
from randomizer.enemy_slots import resolve_spawn_layout
from randomizer.spawn_data import ADULT_SLOTS


class MinibossPoolTests(unittest.TestCase):
    def test_layout_sources_and_complete_solo(self):
        for seed in range(100):
            m = generate(str(seed), miniboss_enemies=True, group_spawn_enemies=True,
                         permanent_checks=True, starting_area='random', starting_color='random',
                         starting_flarlic=1, randomize_color_stats=True, progressive_color_stats=True)
            assignments = m['spawn_layout']['assignments']
            counts = Counter(a['actual'] for a in assignments)
            self.assertEqual([counts[t] for t in (9, 17, 24)], [1, 1, 1])
            for stage in (1, 3):
                early = {a['actual'] for r, a in zip(ADULT_SLOTS, assignments)
                         if r['stage'] == stage and r['first_day'] == 2 and 0 < r['respawn_days'] <= 5
                         and (r['expires_after_day'] is None or r['expires_after_day'] >= 29)}
                self.assertTrue({4, 32} <= early)
            self.assertEqual(len(population_checks(m)), 12)
            self.assertEqual({n for _, n in population_checks(m).values()}, {10, 25, 50, 100})
            self.assertNotIn('Captain Heal', item_pool(m))
            self.assertEqual(sum(map(len, spheres(solo_rewards(m), m))), 113)

    def test_tampering_and_old_manifest(self):
        m = generate('identity', miniboss_enemies=True)
        bad = copy.deepcopy(m)
        bad['spawn_layout']['assignments'][0]['actual'] = 22  # Progg is not allowed.
        with self.assertRaises(ValueError): validate(bad)
        bad = copy.deepcopy(m); bad.pop('miniboss_enemies')
        with self.assertRaises(ValueError): validate(bad)
        self.assertEqual(resolve_spawn_layout('identity', 'Player1')['version'], 'adult-slots-v1')
        self.assertTrue(all(a['actual'] in (4, 32) for a in resolve_spawn_layout('identity', 'Player1')['assignments']))


if __name__ == '__main__':
    unittest.main()
