import tempfile
import unittest
from collections import Counter
from randomizer.catalog import can_reach_manifest, item_pool, FOREST_ACCESS, NAVEL_ACCESS, ITEM_IDS
from randomizer.seed import generate, validate, solo_rewards, spheres
from randomizer.session import Session
from randomizer.runner import NativeRun


class RandomStartTests(unittest.TestCase):
    def test_fill_and_both_starts(self):
        profiles = set()
        for seed in range(200):
            m = generate(str(seed), starting_area='random')
            self.assertEqual(m, generate(str(seed), starting_area='random'))
            profiles.add(m['profile'])
            rewards = solo_rewards(m)
            self.assertEqual(Counter(rewards.values()), Counter(item_pool(m)))
            self.assertEqual(sum(map(len, spheres(rewards, m))), 55)
        self.assertEqual(profiles, {'foh-day2', 'navel-day2'})

    def test_navel_gates(self):
        m = generate('navel', starting_area='navel')
        self.assertIn(FOREST_ACCESS, item_pool(m))
        self.assertNotIn(NAVEL_ACCESS, item_pool(m))
        self.assertTrue(can_reach_manifest('Explore: The Forest Navel - Land', {}, m))
        self.assertTrue(can_reach_manifest('Population: 20 Pikmin in the field', {}, m))
        self.assertFalse(can_reach_manifest('Pikmin: Yellow Onion Discovery', {}, m))
        self.assertFalse(can_reach_manifest('Bestiary: Spotty Bulborb', {}, m))
        self.assertTrue(can_reach_manifest('Pikmin: Yellow Onion Discovery', {FOREST_ACCESS: 1}, m))

    def test_protocol_and_compatibility(self):
        m = generate('native', 'ap', starting_area='navel')
        with tempfile.TemporaryDirectory() as directory:
            session = Session(m, directory)
            session.bind_ap('test', 0, 1)
            session.receive(0, [ITEM_IDS[FOREST_ACCESS]])
            run = NativeRun(session)
            self.assertIn('PROFILE navel-day2', run.bootstrap.read_text())
            self.assertIn(' 32 ', session.native_state(run.token, True))
        self.assertEqual(generate('old')['schema'], 1)
        self.assertEqual(generate('old', expanded=True)['schema'], 2)
        m['profile'] = 'trial-day2'
        with self.assertRaises(ValueError): validate(m)
