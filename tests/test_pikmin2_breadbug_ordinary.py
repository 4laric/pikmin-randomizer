"""Lane 18 ordinary Onion endpoint slice — root-side wiring tests (#220).

These tests pin the family/endpoint wiring the ordinary-RESTART runtime relies
on: the Breadbug bestiary check maps to native TEKI_Collec (type 8) in the
Forest Navel, the generated session exposes the check, and the fixture/driver
target the Collec and the exact check name. The real-GL run itself is invoked by
``scripts/p2_breadbug_ordinary_runtime.py`` against a privately built fixture.
"""
import unittest
from pathlib import Path

from randomizer.seed import generate
from randomizer.catalog import NEW_BESTIARY

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'scripts' / 'p2_breadbug_ordinary_fixture.cpp'
DRIVER = ROOT / 'scripts' / 'p2_breadbug_ordinary_runtime.py'

TARGET = 'Bestiary: Deliver Breadbug'


class BreadbugOrdinaryWiringTests(unittest.TestCase):
    def test_bestiary_check_maps_to_collec_in_the_forest_navel(self):
        # The ordinary endpoint (pc_randomizer_corpse_delivered) matches this
        # catalog entry by native type; the Breadbug proxy is TEKI_Collec = 8.
        self.assertEqual(NEW_BESTIARY[TARGET], (8, 'The Forest Navel', 3))

    def test_seed_exposes_the_breadbug_check_in_the_navel(self):
        m = generate('lane18-wiring', 'ap', expanded=True, all_areas=True,
                     collection_checks=True, starting_flarlic=10, starting_area='navel')
        self.assertEqual(m['schema'], 9)
        self.assertEqual(m['profile'], 'navel-day2')
        from randomizer.session import Session
        session = Session(m, ROOT / 'output' / 'lane18-wiring-check')
        self.assertIn(TARGET, session.names)

    def test_fixture_targets_collec_and_the_breadbug_check(self):
        text = FIXTURE.read_text(encoding='utf-8')
        self.assertIn('TEKI_Collec', text)
        self.assertIn(TARGET, text)
        self.assertIn('GoalItem', text)
        self.assertIn('pc_randomizer', text)

    def test_driver_targets_the_breadbug_check_and_boots_the_navel(self):
        text = DRIVER.read_text(encoding='utf-8')
        self.assertIn("TARGET = 'Bestiary: Deliver Breadbug'", text)
        self.assertIn("starting_area='navel'", text)


if __name__ == '__main__':
    unittest.main()
