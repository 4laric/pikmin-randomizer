import tempfile
import unittest
from collections import Counter
from pathlib import Path
from randomizer.seed import generate, solo_rewards, spheres, validate
from randomizer.catalog import ITEM_IDS, item_pool, can_reach_manifest, FLARLIC
from randomizer.stats import current_profiles, upgrade_pool
from randomizer.session import Session
from randomizer.runner import NativeRun


class ProgressiveStatsTests(unittest.TestCase):
    def test_pool_and_fills(self):
        for seed in range(60):
            m = generate(str(seed), progressive_color_stats=True, starting_area='random', starting_color='random', starting_flarlic=1)
            pool = Counter(item_pool(m))
            self.assertEqual(pool['Ship Repair'], 25)
            self.assertEqual(len(upgrade_pool()), 18)
            self.assertEqual(sum(pool.values()), 77)
            spheres(solo_rewards(m), m)

    def test_only_owned_carry_affects_logic(self):
        m = generate('carry', progressive_color_stats=True, starting_flarlic=1)
        part = 'Pikmin: Eternal Fuel Dynamo'
        owned = Counter({FLARLIC: 1})
        self.assertFalse(can_reach_manifest(part, owned, m))
        owned['Progressive Blue Carry Strength'] = 2
        self.assertFalse(can_reach_manifest(part, owned, m))
        owned['Progressive Red Carry Strength'] = 1
        self.assertTrue(can_reach_manifest(part, owned, m))
        self.assertEqual(current_profiles(m, owned)['red']['damage'], 100)
        owned['Progressive Red Damage'] = 100
        self.assertEqual(current_profiles(m, owned)['red']['damage'], 150)

    def test_receipts_reconnect_and_journal(self):
        for options in ({'progressive_color_stats': True}, {'randomize_color_stats': True}, {'randomize_color_stats': True, 'progressive_color_stats': True}):
            m = generate('resume', 'ap', starting_flarlic=1, **options)
            with tempfile.TemporaryDirectory() as d:
                session = Session(m, d); session.bind_ap('room', 0, 1)
                if m.get('progressive_color_stats'):
                    ids = [ITEM_IDS['Progressive Red Carry Strength']] * 2
                    session.receive(0, ids); session.receive(0, ids)
                    self.assertEqual(session.inventory['Progressive Red Carry Strength'], 2)
                run = NativeRun(session)
                (run.directory / 'checks.txt').write_text('0\n')
                restored = Session(m, d)
                self.assertEqual(restored.inventory, session.inventory)
                self.assertEqual(restored.data['checked'], [session.names[0]])

    def test_modes_fail_closed(self):
        m = generate('bad', progressive_color_stats=True)
        m['capabilities'].remove('progressive-color-stats-v1')
        with self.assertRaises(ValueError): validate(m)

    def test_combined_base_plus_capped_upgrades(self):
        for seed in range(60):
            m = generate(str(seed), progressive_color_stats=True, randomize_color_stats=True,
                         starting_area='random', starting_color='random', starting_flarlic=1)
            self.assertEqual(current_profiles(m), m['color_stats'])
            inv = Counter(upgrade_pool())
            upgraded = current_profiles(m, inv)
            for color, base in m['color_stats'].items():
                self.assertEqual(upgraded[color]['carry'], base['carry'] + 2)
                self.assertEqual(upgraded[color]['damage'], base['damage'] + 50)
                self.assertEqual(upgraded[color]['movement'], base['movement'] + 25)
                self.assertEqual(upgraded[color]['attack_rate'], base['attack_rate'] + 25)
            self.assertEqual(upgraded, current_profiles(m, Counter({n: 99 for n in inv})))
            spheres(solo_rewards(m), m)
