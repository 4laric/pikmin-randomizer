import copy
import unittest
from collections import Counter
from randomizer.seed import generate, validate, solo_rewards, spheres
from randomizer.stats import UPGRADE_LIMITS, current_profiles, upgrade_pool
from randomizer.catalog import item_pool


class BalanceOptionsTests(unittest.TestCase):
    def test_default_options_match_implicit_rolls(self):
        for seed in range(10):
            args = dict(randomize_color_stats=True, progressive_color_stats=True, starting_area='random')
            old = generate(str(seed), **args)
            explicit = generate(str(seed), **args, initial_stat_bounds={s: [25, 100] for s in ('damage', 'movement', 'attack_rate')}, stat_upgrade_counts=UPGRADE_LIMITS, random_start_areas=['impact', 'forest', 'navel', 'spring'])
            self.assertEqual(old['profile'], explicit['profile'])
            self.assertEqual(old['color_stats'], explicit['color_stats'])
            self.assertEqual(item_pool(old), item_pool(explicit))

    def test_custom_counts_bounds_and_fill(self):
        for carry in (0, 1, 4):
            counts = dict(damage=1, movement=0, attack_rate=2, carry=carry)
            m = generate('custom' + str(carry), randomize_color_stats=True, progressive_color_stats=True,
                         stat_upgrade_counts=counts, initial_stat_bounds=dict(damage=[50, 50], movement=[25, 25], attack_rate=[75, 100]),
                         starting_area='random', random_start_areas=['spring'], starting_flarlic=1)
            self.assertEqual(m['profile'], 'spring-day2')
            self.assertEqual(len(upgrade_pool(m)), 3 * sum(counts.values()))
            self.assertEqual(len(item_pool(m)), 113)
            for p in current_profiles(m, Counter({n: 99 for n in upgrade_pool(m)})).values():
                self.assertEqual(p['damage'], 75)
                self.assertEqual(p['movement'], 25)
                self.assertEqual(p['carry'], 1 + carry)
            self.assertEqual(sum(map(len, spheres(solo_rewards(m), m))), 113)

    def test_reject_invalid_configuration(self):
        for areas in ([], ['trial'], ['forest', 'typo']):
            with self.assertRaises(ValueError): generate('bad', random_start_areas=areas)
        for pair in ([100, 25], [26, 100], [True, 100], [25, 125]):
            with self.assertRaises(ValueError): generate('bad', initial_stat_bounds=dict(damage=pair, movement=[25, 100], attack_rate=[25, 100]))
        m = generate('valid', progressive_color_stats=True, stat_upgrade_counts=UPGRADE_LIMITS)
        for value in (-1, 5, True):
            bad = copy.deepcopy(m); bad['stat_upgrade_counts']['carry'] = value
            with self.assertRaises(ValueError): validate(bad)
        bad = copy.deepcopy(m); bad['capabilities'].remove('progressive-color-stats-v2')
        with self.assertRaises(ValueError): validate(bad)

    def test_area_pool_is_order_independent(self):
        for seed in range(10):
            self.assertEqual(generate(str(seed), starting_area='random', random_start_areas=['spring', 'impact']),
                             generate(str(seed), starting_area='random', random_start_areas=['impact', 'spring']))
