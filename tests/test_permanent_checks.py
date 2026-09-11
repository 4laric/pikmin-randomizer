import tempfile
import unittest
from collections import Counter
from randomizer.catalog import (COLLECTION_LOCATION_IDS, COLLECTION_NAMES, PERMANENT_LOCATION_IDS,
                               PERMANENT_NAMES, FINE_POPULATION, OBSTACLES, can_reach_manifest, progression_pool)
from randomizer.seed import generate, solo_rewards, spheres
from randomizer.session import Session
from randomizer.runner import NativeRun


class PermanentChecksTests(unittest.TestCase):
    def test_catalog_and_fills(self):
        self.assertGreater(len(PERMANENT_NAMES), 64)
        self.assertEqual(PERMANENT_NAMES[:58], COLLECTION_NAMES)
        self.assertEqual(len(FINE_POPULATION), 19)
        self.assertEqual(len(PERMANENT_LOCATION_IDS), len(set(PERMANENT_LOCATION_IDS.values())))
        for name, ident in COLLECTION_LOCATION_IDS.items():
            self.assertEqual(PERMANENT_LOCATION_IDS[name], ident)
        self.assertEqual(len(set(OBSTACLES.values())), len(OBSTACLES))
        for seed in range(50):
            m = generate(str(seed), permanent_checks=True, randomize_color_stats=True,
                         progressive_color_stats=True, starting_flarlic=1, starting_area='random', starting_color='random')
            spheres(solo_rewards(m), m)

    def test_high_indices_recover_once(self):
        m = generate('journal', permanent_checks=True)
        with tempfile.TemporaryDirectory() as d:
            session = Session(m, d); run = NativeRun(session)
            (run.directory / 'checks.txt').write_text('64\n64\n67\n')
            restored = Session(m, d)
            self.assertEqual(restored.data['checked'], [session.names[64], session.names[67]])
            self.assertIn('CHECKS 2 64 67', restored.native_state(run.token, True))

    def test_obstacles_require_colors_and_area(self):
        m = generate('gates', permanent_checks=True, starting_flarlic=10)
        full = Counter(progression_pool(m))
        for name in OBSTACLES:
            self.assertFalse(can_reach_manifest(name, {}, m))
            self.assertTrue(can_reach_manifest(name, full, m))
