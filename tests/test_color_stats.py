import copy
import unittest
from randomizer.seed import generate, validate, fingerprint, solo_rewards, spheres
from randomizer.catalog import can_reach_manifest, FLARLIC, BLUE, YELLOW, route_strength
from randomizer.stats import bootstrap_stats, profile_lines


class ColorStatsTests(unittest.TestCase):
    def test_profiles_reveal_on_color_unlock(self):
        for starting in ('red', 'yellow', 'blue'):
            manifest = {'starting_color': starting, 'progressive_color_stats': True}
            inventory = {f'Progressive {color.title()} Damage': 1 for color in ('red', 'yellow', 'blue')}
            for color, line in zip(('red', 'yellow', 'blue'), profile_lines(manifest, inventory)):
                self.assertEqual('DMG 125%' in line, color == starting)
                self.assertEqual('undiscovered' in line, color != starting)
            inventory.update({'Red Onion': 1, 'Yellow Onion': 1, 'Blue Onion': 1})
            self.assertTrue(all('DMG 125%' in line for line in profile_lines(manifest, inventory)))
        self.assertEqual(profile_lines({}), [])

    def test_deterministic_profiles_and_legacy(self):
        old = generate('same', enemy_shuffle=True, starting_area='random', starting_color='random')
        new = generate('same', enemy_shuffle=True, starting_area='random', starting_color='random', randomize_color_stats=True)
        self.assertEqual(new, generate('same', enemy_shuffle=True, starting_area='random', starting_color='random', randomize_color_stats=True))
        self.assertNotIn('color_stats', old)
        for field in ('profile', 'starting_color', 'enemy_mask'):
            self.assertEqual(new[field], old[field])
        self.assertNotEqual(fingerprint(old), fingerprint(new))
        self.assertIn('COLOR_STATS_WIDE blue ', bootstrap_stats(new))
        self.assertEqual(len(profile_lines(new)), 3)

    def test_invalid_profiles_fail_closed(self):
        m = generate('stats', randomize_color_stats=True)
        for value in (0, 6, True, 1.5, '2'):
            bad = copy.deepcopy(m); bad['color_stats']['red']['carry'] = value
            with self.assertRaises(ValueError): validate(bad)

    def test_legacy_profile_version_stays_valid(self):
        m = generate('legacy', randomize_color_stats=True)
        m['capabilities'][m['capabilities'].index('color-stats-v2')] = 'color-stats-v1'
        m['color_stats'] = {c: dict(damage=100, movement=100, attack_rate=100, carry=1) for c in ('red', 'yellow', 'blue')}
        validate(m)
        self.assertIn('COLOR_STATS blue ', bootstrap_stats(m))
        m['color_stats']['red']['carry'] = 5
        with self.assertRaises(ValueError): validate(m)

    def test_profile_shape_and_capability(self):
        m = generate('invalid', randomize_color_stats=True)
        for change in ('missing', 'extra', 'capability'):
            bad = copy.deepcopy(m)
            if change == 'missing': del bad['color_stats']['blue']
            elif change == 'extra': bad['color_stats']['red']['throw_height'] = 2
            else: bad['capabilities'].remove('color-stats-v2')
            with self.assertRaises(ValueError): validate(bad)

    def test_strength_affects_weight_not_colors_or_population(self):
        m = generate('stats', randomize_color_stats=True, starting_flarlic=1)
        for color in m['color_stats']: m['color_stats'][color]['carry'] = 1
        part = 'Pikmin: Eternal Fuel Dynamo'  # 40 weight, audited red approach.
        self.assertFalse(can_reach_manifest(part, {FLARLIC: 1}, m))
        m['color_stats']['red']['carry'] = 2
        self.assertTrue(can_reach_manifest(part, {FLARLIC: 1}, m))
        self.assertFalse(can_reach_manifest(part, {}, m))
        self.assertFalse(can_reach_manifest('Population: 30 Pikmin in the field', {FLARLIC: 1}, m))
        # Strong red carriers do not bypass the other route colors.
        self.assertFalse(can_reach_manifest('Pikmin: Sagittarius', {FLARLIC: 9}, m))
        self.assertEqual(route_strength('Pikmin: Sagittarius', m), 1)
        for color in m['color_stats']: m['color_stats'][color]['carry'] = 3
        self.assertTrue(can_reach_manifest('Pikmin: Sagittarius', {BLUE: 1, YELLOW: 1}, m))

    def test_solo_generation_profiles(self):
        for seed in range(40):
            m = generate(str(seed), randomize_color_stats=True, collection_checks=bool(seed % 2),
                         starting_area='random', starting_color='random', starting_flarlic=1)
            spheres(solo_rewards(m), m)
