from collections import Counter
import tempfile
import unittest
from randomizer.catalog import RED, BLUE, YELLOW, ITEM_IDS, item_pool, color_inventory, can_reach_manifest
from randomizer.seed import generate, solo_rewards, spheres, validate
from randomizer.session import Session
from randomizer.runner import NativeRun
from randomizer.overlay import snapshot


class StartingColorTests(unittest.TestCase):
    def test_all_combinations_fill(self):
        seen = set()
        for seed in range(300):
            m = generate(str(seed), starting_area='random', starting_color='random')
            seen.add((m['profile'], m['starting_color']))
            self.assertEqual(m, generate(str(seed), starting_area='random', starting_color='random'))
            rewards = solo_rewards(m)
            self.assertEqual(Counter(rewards.values()), Counter(item_pool(m)))
            self.assertEqual(sum(map(len, spheres(rewards, m))), 55)
            start = {'red': RED, 'yellow': YELLOW, 'blue': BLUE}[m['starting_color']]
            self.assertNotIn(start, item_pool(m))
        self.assertEqual(len(seen), 6)

    def test_red_requirements_and_overlay(self):
        m = generate('blue', starting_area='navel', starting_color='blue')
        owned = color_inventory({}, m)
        self.assertIn(BLUE, owned)
        self.assertNotIn(RED, owned)
        self.assertFalse(can_reach_manifest('Population: 30 Pikmin in the field', {}, m))
        self.assertFalse(can_reach_manifest('Bestiary: Fiery Blowhog', {}, m))
        self.assertFalse(can_reach_manifest('Bestiary: Wollywog', {}, m))
        self.assertTrue(can_reach_manifest('Bestiary: Fiery Blowhog', {RED: 1}, m))
        with tempfile.TemporaryDirectory() as d:
            session = Session(m, d)
            self.assertEqual(snapshot(m, session.data), ([], 20, 0))

    def test_red_protocol_and_recovery(self):
        m = generate('yellow', 'ap', starting_color='yellow')
        with tempfile.TemporaryDirectory() as d:
            session = Session(m, d)
            session.bind_ap('test', 0, 1)
            session.receive(0, [ITEM_IDS[RED]])
            run = NativeRun(session)
            self.assertIn('COLOR yellow', run.bootstrap.read_text())
            self.assertIn(' 64 ', session.native_state(run.token, True))
            (run.directory / 'checks.txt').write_text('30\n')
            restored = Session(m, d)
            self.assertIn('Population: 20 Pikmin in the field', restored.data['checked'])
        m['starting_color'] = 'purple'
        with self.assertRaises(ValueError): validate(m)
