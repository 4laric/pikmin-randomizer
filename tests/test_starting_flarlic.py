import unittest
from collections import Counter
from randomizer.seed import generate, validate, solo_rewards, spheres
from randomizer.catalog import FLARLIC, field_capacity, progression_pool, can_reach_manifest
from randomizer.overlay import snapshot
from randomizer.session import Session
from randomizer.runner import NativeRun
from tempfile import TemporaryDirectory


class StartingFlarlicTests(unittest.TestCase):
    def test_capacity_pool_and_fill(self):
        for initial in (1, 2, 5, 10):
            for collection in (False, True):
                m = generate('flarlic', starting_flarlic=initial, collection_checks=collection)
                self.assertEqual(progression_pool(m).count(FLARLIC), 10 - initial)
                self.assertEqual(field_capacity({}, True, initial), 10 * initial)
                self.assertEqual(field_capacity({FLARLIC: 20}, True, initial), 100)
                spheres(solo_rewards(m), m)
                self.assertTrue(can_reach_manifest('Explore: The Forest of Hope - Land', {}, m))
                with TemporaryDirectory() as d:
                    session = Session(m, d)
                    self.assertEqual(snapshot(m, session.data)[1], initial * 10)
                    run = NativeRun(session)
                    self.assertIn(f'STARTING_FLARLIC {initial}', run.bootstrap.read_text())

    def test_invalid_and_legacy(self):
        for initial in (0, 11, True, 1.5, '1'):
            with self.assertRaises(ValueError):
                generate('bad', starting_flarlic=initial)
        old = generate('legacy', expanded=True)
        self.assertNotIn('starting_flarlic', old)
        self.assertNotIn('starting-flarlic-v1', old['capabilities'])
        self.assertEqual(progression_pool(old).count(FLARLIC), 8)
        bad = generate('bad', starting_flarlic=1)
        bad['capabilities'].remove('starting-flarlic-v1')
        with self.assertRaises(ValueError):
            validate(bad)
