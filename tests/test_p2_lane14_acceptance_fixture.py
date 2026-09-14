import importlib
import json
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO / 'docs' / 'p2_lane14_acceptance_fixture.json'
ROSTER_PATH = REPO / 'docs' / 'PIKMIN2_ENEMY_ROSTER.json'


class Lane14AcceptanceFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = json.loads(FIXTURE_PATH.read_text())
        cls.roster = {row['enum_name']: row['source_id']
                      for row in json.loads(ROSTER_PATH.read_text())['entries']}

    def test_schema_and_lane(self):
        self.assertEqual(self.plan['schema'], 'p2-lane14-acceptance-fixture-v1')
        self.assertEqual(self.plan['lane'], 14)
        self.assertEqual(self.plan['tracking_issue'], 165)

    def test_every_run_module_imports_and_exposes_run(self):
        for run in self.plan['runs']:
            with self.subTest(run=run['id']):
                module = importlib.import_module(run['module'])
                self.assertTrue(callable(getattr(module, 'run', None)),
                                f"{run['module']} has no callable run()")
                self.assertGreater(run['seconds'], 0)

    def test_identities_match_roster(self):
        for run in self.plan['runs']:
            with self.subTest(run=run['id']):
                identity = run['identity']
                expected = run['source_id']
                if isinstance(identity, str) and ',' in identity:
                    pairs = list(zip(identity.split(','), str(expected).split(',')))
                    for name, sid in pairs:
                        self.assertEqual(self.roster[name], int(sid))
                else:
                    self.assertEqual(self.roster[identity], int(expected))

    def test_injected_runs_are_labelled(self):
        injected = [run for run in self.plan['runs'] if run['kind'] == 'injected']
        self.assertTrue(injected, 'expected at least one injected diagnostic run')
        for run in injected:
            with self.subTest(run=run['id']):
                self.assertIn('not_natural_combat=1', run['injection_marker'])
                self.assertIn('injected', run['kind'])

    def test_natural_death_gap_is_recorded(self):
        gap = self.plan['open_gap']
        self.assertIn('natural_death', gap)
        self.assertIn('reward_delivery', gap)
        self.assertIn('follow_on', gap)

    def test_fixture_build_runs_declare_a_builder(self):
        for run in self.plan['runs']:
            if not run['requires_fixture_build']:
                continue
            with self.subTest(run=run['id']):
                module = importlib.import_module(run['module'])
                self.assertTrue(callable(getattr(module, 'build', None)),
                                f"{run['module']} requires a fixture build but has no build()")


if __name__ == '__main__':
    unittest.main()
