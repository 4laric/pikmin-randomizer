"""Lane 39 cave-logic tests over lane 34's `p2-cave-floor-table-v1` shape.

The example is the fan-out's mandatory first step: one water choke, a water leaf
and an electric leaf on `forest_1` floor 1, two hazard-tagged treasures, plus a
second floor to exercise cross-floor inheritance and bud OR-keys.  These are
logic tests written against the seeded pool, never against an observed layout.
"""
import unittest

from randomizer.cave_logic import (CaveLogicError, hole_requirement, hint, load_cave,
                                   requirement_fingerprint, requirement_satisfied,
                                   requirements_map, requirements_manifest, satisfied,
                                   segment_requirement, treasure_requirement, validate_tags)
from randomizer.catalog import can_reach_manifest

CAVE = 'forest_1'
WATER = 'juji_key_fc'
ELEC = 'example_elec_treasure'
DEEP = 'deep_water'
TAGS = {WATER: 'water', ELEC: 'elec', DEEP: 'water'}


def slot(floor, slot_class, index):
    return '%s:f%d:%s:%d' % (CAVE, floor, slot_class, index)


def floor_one():
    return {
        'schema': 1, 'seed': 'l39-demo', 'cave_id': CAVE, 'floor': 1,
        'unit_pool': '1_units_cent3_tsuchi.txt',
        'segments': [{'slot_id': slot(1, 'segment', i), 'index': i} for i in range(3)],
        'chokes': [
            {'slot_id': slot(1, 'choke', 0), 'index': 0, 'after_segment': 0,
             'before_segment': 1, 'hazard': 'water', 'kind': 'hard',
             'hardness': 'hard', 'unit': 'way2_tsuchi'},
            {'slot_id': slot(1, 'choke', 1), 'index': 1, 'after_segment': 1,
             'before_segment': 2, 'hazard': 'elec', 'kind': 'hard',
             'hardness': 'hard', 'unit': 'way3_tsuchi'},
        ],
        'leaves': [
            {'slot_id': slot(1, 'leaf', 0), 'index': 0, 'segment': 0,
             'hazard': 'water', 'item_slots': 1},
            {'slot_id': slot(1, 'leaf', 1), 'index': 1, 'segment': 1,
             'hazard': 'elec', 'item_slots': 1},
        ],
        'buds': [{'slot_id': slot(1, 'bud', 0), 'index': 0, 'segment': 0,
                  'species': 'yellow', 'count': 5}],
        'treasures': [
            {'treasure_id': WATER, 'slot_id': slot(1, 'leaf', 0), 'segment': 0,
             'leaf_hazard': 'water'},
            {'treasure_id': ELEC, 'slot_id': slot(1, 'leaf', 1), 'segment': 1,
             'leaf_hazard': 'elec'},
        ],
        'hole': {'slot_id': slot(1, 'segment', 2), 'segment': 2},
        'generated': False, 'geometry_rerolls': True,
    }


def floor_two(ambient=()):
    return {
        'schema': 1, 'seed': 'l39-demo', 'cave_id': CAVE, 'floor': 2,
        'unit_pool': '1_units_cent3_tsuchi.txt',
        'segments': [{'slot_id': slot(2, 'segment', i), 'index': i} for i in range(2)],
        'chokes': [
            {'slot_id': slot(2, 'choke', 0), 'index': 0, 'after_segment': 0,
             'before_segment': 1, 'hazard': 'elec', 'kind': 'hard',
             'hardness': 'hard', 'unit': 'way2_tsuchi'},
        ],
        'leaves': [
            {'slot_id': slot(2, 'leaf', 0), 'index': 0, 'segment': 1,
             'hazard': 'water', 'item_slots': 1},
        ],
        'buds': [],
        'treasures': [
            {'treasure_id': DEEP, 'slot_id': slot(2, 'leaf', 0), 'segment': 1,
             'leaf_hazard': 'water'},
        ],
        'hole': {'slot_id': slot(2, 'segment', 1), 'segment': 1},
        'generated': False, 'geometry_rerolls': True,
        'ambient_hazards': list(ambient),
    }


def demo_cave(ambient=()):
    return load_cave([floor_one(), floor_two(ambient)])


def keys(requirement):
    """Render a requirement as sorted string keys for readable assertions."""
    text = []
    for key in requirement:
        parts = []
        for literal in key:
            if literal[0] == 'item':
                parts.append(literal[1])
            elif literal[0] == 'capacity':
                parts.append('cap:%s:%d' % (literal[2], literal[1]))
            else:
                parts.append('captain')
        text.append(tuple(sorted(parts)))
    return tuple(sorted(text))


class LoadCaveTests(unittest.TestCase):
    def test_load_is_deterministic_and_ignores_geometry(self):
        self.assertEqual(demo_cave(), demo_cave())
        rolled = floor_one()
        rolled['geometry'] = {'seed': 99, 'shape': [3, 3]}
        self.assertNotIn('geometry', load_cave([rolled, floor_two()])['floors'][0])

    def test_malformed_tables_fail_closed(self):
        mixed = floor_two()
        mixed['cave_id'] = 'other_1'
        bad_hazard = floor_one()
        bad_hazard['chokes'][0]['hazard'] = 'lava'
        bad_hardness = floor_one()
        bad_hardness['chokes'][0]['hardness'] = 'medium'
        bad_bud = floor_one()
        bad_bud['buds'][0]['count'] = 0
        bad_index = floor_one()
        bad_index['segments'][1]['index'] = 5
        cases = [[floor_two()], [floor_one(), mixed], [bad_hazard, floor_two()],
                 [bad_hardness, floor_two()], [bad_bud, floor_two()],
                 [bad_index, floor_two()]]
        for tables in cases:
            with self.subTest(tables=tables), self.assertRaises(CaveLogicError):
                load_cave(tables)

    def test_duplicate_treasure_id_across_floors_is_rejected(self):
        second = floor_two()
        second['treasures'][0]['treasure_id'] = WATER
        with self.assertRaises(CaveLogicError):
            load_cave([floor_one(), second])

    def test_hazard_tag_config_matches_the_tables(self):
        cave = demo_cave()
        self.assertEqual(validate_tags(cave, TAGS), TAGS)
        with self.assertRaises(CaveLogicError):
            validate_tags(cave, {**TAGS, ELEC: 'water'})
        with self.assertRaises(CaveLogicError):
            validate_tags(cave, {**TAGS, 'missing': 'water'})
        with self.assertRaises(CaveLogicError):
            validate_tags(cave, {WATER: 'water', ELEC: 'elec'})
        with self.assertRaises(CaveLogicError):
            validate_tags(cave, {**TAGS, WATER: 'lava'})


class RequirementTests(unittest.TestCase):
    def test_segment_and_leaf_requirements(self):
        cave = demo_cave()
        self.assertEqual(keys(segment_requirement(cave, 1, 0)), ())
        self.assertEqual(keys(segment_requirement(cave, 1, 1)), (('Blue Onion',),))
        self.assertEqual(keys(treasure_requirement(cave, WATER)), (('Blue Onion',),))
        self.assertEqual(keys(treasure_requirement(cave, ELEC)),
                         (('Blue Onion',), ('Yellow Onion', 'cap:yellow:5')))

    def test_water_choke_gates_the_hole(self):
        cave = demo_cave()
        self.assertEqual(keys(hole_requirement(cave, 1)),
                         (('Blue Onion',), ('Yellow Onion', 'cap:yellow:5')))
        self.assertTrue(satisfied(hole_requirement(cave, 1), {'Blue Onion': 1,
                                                              'Yellow Onion': 1}))
        self.assertFalse(satisfied(hole_requirement(cave, 1), {'Red Onion': 1}))

    def test_leaf_hazards_do_not_gate_the_hole(self):
        solo = {
            'schema': 1, 'seed': 'x', 'cave_id': CAVE, 'floor': 1,
            'segments': [{'slot_id': slot(1, 'segment', i), 'index': i} for i in range(2)],
            'chokes': [], 'buds': [],
            'leaves': [{'slot_id': slot(1, 'leaf', 0), 'index': 0, 'segment': 1,
                        'hazard': 'elec', 'item_slots': 1}],
            'treasures': [{'treasure_id': ELEC, 'slot_id': slot(1, 'leaf', 0),
                           'segment': 1, 'leaf_hazard': 'elec'}],
            'hole': {'slot_id': slot(1, 'segment', 1), 'segment': 1},
            'generated': False, 'geometry_rerolls': True,
        }
        cave = load_cave(solo)
        self.assertEqual(keys(hole_requirement(cave, 1)), ())
        self.assertEqual(keys(treasure_requirement(cave, ELEC)), (('Yellow Onion',),))

    def test_bud_or_key_tracks_pikmin_count(self):
        cave = demo_cave()
        # Vanilla conversion count 5: 20 capacity suffices, 0 does not.
        self.assertTrue(satisfied(treasure_requirement(cave, ELEC), {'Blue Onion': 1}, 2))
        self.assertFalse(satisfied(treasure_requirement(cave, ELEC), {'Blue Onion': 1}, 0))
        heavy = load_cave([{**floor_one(), 'buds': [{'slot_id': slot(1, 'bud', 0),
                          'index': 0, 'segment': 0, 'species': 'yellow', 'count': 25}]},
                          floor_two()])
        self.assertFalse(satisfied(treasure_requirement(heavy, ELEC), {'Blue Onion': 1}, 2))
        self.assertTrue(satisfied(treasure_requirement(heavy, ELEC), {'Blue Onion': 1}, 3))

    def test_bud_count_never_beats_the_100_cap(self):
        huge = load_cave([{**floor_one(), 'buds': [{'slot_id': slot(1, 'bud', 0),
                         'index': 0, 'segment': 0, 'species': 'yellow', 'count': 150}]},
                         floor_two()])
        self.assertFalse(satisfied(treasure_requirement(huge, ELEC), {'Blue Onion': 1}, 10))

    def test_cross_floor_inheritance(self):
        cave = demo_cave()
        self.assertEqual(keys(treasure_requirement(cave, DEEP)),
                         (('Blue Onion',), ('Yellow Onion',), ('Yellow Onion', 'cap:yellow:5')))
        self.assertFalse(satisfied(treasure_requirement(cave, DEEP), {'Blue Onion': 1}))
        self.assertTrue(satisfied(treasure_requirement(cave, DEEP),
                                  {'Blue Onion': 1, 'Yellow Onion': 1}))

    def test_ambient_hazard_is_worst_case(self):
        cave = demo_cave(ambient=['poison'])
        self.assertIn(('White Onion',), keys(treasure_requirement(cave, DEEP)))
        self.assertFalse(satisfied(treasure_requirement(cave, DEEP),
                                   {'Blue Onion': 1, 'Yellow Onion': 1}))
        self.assertTrue(satisfied(treasure_requirement(cave, DEEP),
                                  {'Blue Onion': 1, 'Yellow Onion': 1, 'White Onion': 1}))

    def test_soft_geyser_passes_with_timing(self):
        soft = floor_one()
        soft['leaves'][1]['hazard'] = 'fire'
        soft['treasures'][1]['leaf_hazard'] = 'fire'  # fire is soft: timing passes it
        cave = load_cave([soft, floor_two()])
        self.assertTrue(any('captain' in key for key in keys(treasure_requirement(cave, ELEC))))
        self.assertTrue(satisfied(treasure_requirement(cave, ELEC), {'Blue Onion': 1}, 0))

    def test_unknown_treasure_and_segment_rejected(self):
        cave = demo_cave()
        with self.assertRaises(CaveLogicError):
            treasure_requirement(cave, 'nope')
        with self.assertRaises(CaveLogicError):
            segment_requirement(cave, 1, -1)
        with self.assertRaises(CaveLogicError):
            hole_requirement(cave, 9)


class HintStabilityTests(unittest.TestCase):
    def test_hint_and_fingerprint_are_stable_across_reroll(self):
        cave = demo_cave()
        rolled_one = floor_one()
        rolled_one['geometry'] = {'shape': [9, 9], 'seed': 7}
        rolled_two = floor_two()
        rolled_two['geometry'] = {'shape': [2, 2], 'seed': 8}
        rerolled = load_cave([rolled_one, rolled_two])
        self.assertEqual(hint(cave, ELEC), hint(rerolled, ELEC))
        self.assertEqual(requirement_fingerprint(cave), requirement_fingerprint(rerolled))
        self.assertIn('Floor 1', hint(cave, ELEC))
        self.assertIn('Blue Onion', hint(cave, WATER))

    def test_hint_changes_when_the_table_changes(self):
        cave = demo_cave()
        without_bud = load_cave([{**floor_one(), 'buds': []}, floor_two()])
        self.assertNotEqual(hint(cave, ELEC), hint(without_bud, ELEC))
        self.assertNotEqual(requirement_fingerprint(cave),
                            requirement_fingerprint(without_bud))

    def test_manifest_view_round_trips_through_the_consumer(self):
        cave = demo_cave()
        manifest = {**requirements_manifest(cave), 'starting_flarlic': 2}
        rows = requirements_map(cave)
        self.assertEqual(set(manifest['requirements']), set(rows))
        self.assertTrue(requirement_satisfied(rows[WATER], {'Blue Onion': 1}, manifest))
        self.assertFalse(requirement_satisfied(rows[WATER], {'Yellow Onion': 1}, manifest))

    def test_unknown_serialised_literal_fails_closed(self):
        with self.assertRaises(CaveLogicError):
            requirement_satisfied([[{'mystery': True}]], {}, {})
        with self.assertRaises(CaveLogicError):
            requirement_satisfied([[{'captain': False}]], {}, {})
        with self.assertRaises(CaveLogicError):
            requirement_satisfied([['Blue Onion']], {}, {})


class AccessRuleHookTests(unittest.TestCase):
    def test_seeded_requirements_flow_through_can_reach_manifest(self):
        manifest = {'schema': 9, 'starting_flarlic': 2,
                    'cave_requirements': requirements_map(demo_cave())}
        self.assertTrue(can_reach_manifest(WATER, {'Blue Onion': 1}, manifest))
        self.assertFalse(can_reach_manifest(WATER, {'Red Onion': 1}, manifest))
        self.assertFalse(can_reach_manifest(ELEC, {'Red Onion': 1}, manifest))

    def test_legacy_locations_are_untouched_without_the_hook(self):
        # No cave_requirements key -> the original legacy rule still applies.
        # Whimsical Radar is a Forest of Hope part: yellow + blue, no area access.
        self.assertTrue(can_reach_manifest('Pikmin: Whimsical Radar',
                                           {'Yellow Onion': 1, 'Blue Onion': 1},
                                           {'schema': 0}))
        self.assertFalse(can_reach_manifest('Pikmin: Whimsical Radar', {}, {'schema': 0}))


class Lane34AgreementTests(unittest.TestCase):
    def test_fixtures_satisfy_the_lane34_validator_when_present(self):
        try:
            from experimental.pikmin2_cave_schema import validate_floor_table
        except Exception:
            self.skipTest('lane 34 schema module not merged into this worktree')
        validate_floor_table(floor_one())
        validate_floor_table(floor_two())


if __name__ == '__main__':
    unittest.main()
