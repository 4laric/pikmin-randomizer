import json
import unittest
from pathlib import Path

from randomizer import p2_placement as placement
from randomizer import p2_placement_catalog as catalog

REPO = Path(__file__).resolve().parents[1]
FACTS_PATH = REPO / 'docs' / 'p2_ground_placement_facts.json'
ROSTER_PATH = REPO / 'docs' / 'PIKMIN2_ENEMY_ROSTER.json'

# Source root-collision footprint (asset audit section 4) and helper budget
# (manager group cap) expected for each lane-14 identity.
EXPECTED = {
    'Armor': {'footprint_radius': 40, 'helper_budget': 0, 'requires_burrow_ground': True,
              'terrains': ['ground']},
    'ElecBug': {'footprint_radius': 32.5, 'helper_budget': 0, 'requires_burrow_ground': False,
                'terrains': ['ground']},
    'Imomushi': {'footprint_radius': 17.5, 'helper_budget': 0, 'requires_burrow_ground': True,
                 'terrains': ['ground']},
    'TamagoMushi': {'footprint_radius': 18, 'helper_budget': 10, 'requires_burrow_ground': True,
                    'terrains': ['ground', 'underground']},
    'Sokkuri': {'footprint_radius': 25, 'helper_budget': 0, 'requires_burrow_ground': False,
                'terrains': ['ground', 'mixed', 'water']},
    'Hana': {'footprint_radius': 75, 'helper_budget': 0, 'requires_burrow_ground': True,
             'terrains': ['ground']},
}


def ground_slot(**overrides):
    base = {
        'uid': 1, 'label': 'ground_01', 'stage': 1, 'terrain': 'ground', 'radius': 100,
        'water_depth': 0, 'flight_space': False, 'burrow_ground': True, 'home': False,
        'helper_capacity': 0, 'projectile_corridor': False, 'corpse_route': True,
        'protected': False, 'boss_slot': False, 'first_day': 1, 'respawn_days': 0,
        'evidence': {'xyz': False, 'terrain': False, 'route': False},
    }
    base.update(overrides)
    return base


class GroundPlacementFactsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts = json.loads(FACTS_PATH.read_text())
        cls.roster = {row['enum_name']: row for row in json.loads(ROSTER_PATH.read_text())['entries']}

    def test_schema_and_lane(self):
        self.assertEqual(self.facts['schema'], 'p2-placement-facts-v1')
        self.assertEqual(self.facts['lane'], 14)
        self.assertEqual(self.facts['evidence_level'], 'source-contract')

    def test_identity_set_matches_lane_14_candidates(self):
        lane14 = {identity for _, identity, lane, *_ in catalog.CANDIDATE_SPECS if lane == 14}
        self.assertEqual(set(self.facts['identities']), lane14)
        self.assertEqual(lane14, set(EXPECTED))

    def test_profiles_normalize_as_placement_v1(self):
        for identity, record in self.facts['identities'].items():
            with self.subTest(identity=identity):
                normalized = placement.normalize_profile({
                    'identity': identity, **record['profile'],
                })
                self.assertEqual(normalized['identity'], identity)
                self.assertTrue(normalized['terrains'])
                self.assertTrue(normalized['requires_corpse_route'])
                self.assertFalse(normalized['requires_home'])
                self.assertEqual(normalized['min_water_depth'], 0)
                self.assertEqual(normalized['helper_budget'], EXPECTED[identity]['helper_budget'])
                self.assertEqual(normalized['footprint_radius'], EXPECTED[identity]['footprint_radius'])
                self.assertEqual(normalized['requires_burrow_ground'],
                                 EXPECTED[identity]['requires_burrow_ground'])
                self.assertEqual(normalized['terrains'], EXPECTED[identity]['terrains'])

    def test_source_ids_match_roster_and_catalog(self):
        catalog_ids = catalog.candidate_source_ids()
        for identity, record in self.facts['identities'].items():
            with self.subTest(identity=identity):
                self.assertEqual(record['source_id'], catalog_ids[identity])
                self.assertEqual(self.roster[identity]['source_id'], record['source_id'])
                self.assertEqual(self.roster[identity]['common_name'], record['common_name'])
                self.assertIsNone(self.roster[identity]['child_name'])
                self.assertEqual(record['facts']['home_anchor'],
                                 self.roster[identity]['child_name'])
                self.assertEqual(record['facts']['drop_type'], self.roster[identity]['drop_type'])

    def test_facts_carry_source_anchors(self):
        for identity, record in self.facts['identities'].items():
            with self.subTest(identity=identity):
                self.assertTrue(record['source_anchors'])
                self.assertTrue(record['placement_note'])

    def test_constraints_change_placement(self):
        profiles = {
            identity: placement.normalize_profile({'identity': identity, **record['profile']})
            for identity, record in self.facts['identities'].items()
        }
        # Sokkuri accepts water; Armor does not.
        water = ground_slot(terrain='water', burrow_ground=False)
        self.assertEqual(placement.compatibility(water, profiles['Sokkuri']), [])
        self.assertTrue(placement.compatibility(water, profiles['Armor']))
        # Armor needs burrow ground; a non-burrow slot rejects it.
        no_burrow = ground_slot(burrow_ground=False)
        self.assertTrue(placement.compatibility(no_burrow, profiles['Armor']))
        # Hana's 75 footprint rejects a 50-radius slot but fits the default 100.
        small = ground_slot(radius=50)
        self.assertTrue(placement.compatibility(small, profiles['Hana']))
        self.assertEqual(placement.compatibility(ground_slot(), profiles['Hana']), [])
        # TamagoMushi's group budget exceeds a slot with no helper capacity.
        self.assertTrue(placement.compatibility(ground_slot(), profiles['TamagoMushi']))
        self.assertEqual(
            placement.compatibility(ground_slot(helper_capacity=10), profiles['TamagoMushi']), [])


if __name__ == '__main__':
    unittest.main()
