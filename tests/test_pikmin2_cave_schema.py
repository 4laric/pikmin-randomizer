# Lane 34 (#473) host-side cave-table schema validator tests.
# These tests target experimental/pikmin2_cave_schema.py, the four-slot schema
# and per-floor seeded table contract consumed by lanes 35-39.
import copy
import json
import unittest
from pathlib import Path

from experimental.pikmin2_cave_schema import (
    HAZARD_SPECIES,
    HAZARDS,
    SCHEMA_VERSION,
    SLOT_CLASSES,
    SPECIES_HAZARD,
    SchemaError,
    derive_floor_table,
    requirements,
    slot_id,
    table_digest,
    validate_floor_table,
    worked_example,
)

CID = 'forest_1'
FLOOR = 1
FIXTURE = Path(__file__).resolve().parent / 'data' / 'forest_1_floor1.json'


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


def valid_table():
    seg = lambda i: slot_id(CID, FLOOR, 'segment', i)
    ck = lambda i: slot_id(CID, FLOOR, 'choke', i)
    lf = lambda i: slot_id(CID, FLOOR, 'leaf', i)
    bd = lambda i: slot_id(CID, FLOOR, 'bud', i)
    return {
        'schema': SCHEMA_VERSION,
        'seed': 'unit-seed',
        'cave_id': CID,
        'floor': FLOOR,
        'segments': [
            {'slot_id': seg(0), 'index': 0},
            {'slot_id': seg(1), 'index': 1},
            {'slot_id': seg(2), 'index': 2},
        ],
        'chokes': [
            {'slot_id': ck(0), 'index': 0, 'after_segment': 0, 'before_segment': 1,
             'hazard': 'water', 'kind': 'hard', 'hardness': 'hard', 'unit': 'way2_tsuchi'},
            {'slot_id': ck(1), 'index': 1, 'after_segment': 1, 'before_segment': 2,
             'hazard': 'elec', 'kind': 'soft', 'hardness': 'soft', 'unit': 'way3_tsuchi'},
        ],
        'leaves': [
            {'slot_id': lf(0), 'index': 0, 'segment': 0, 'hazard': 'fire', 'item_slots': 1},
            {'slot_id': lf(1), 'index': 1, 'segment': 1, 'hazard': 'poison', 'item_slots': 1},
        ],
        'buds': [
            {'slot_id': bd(0), 'index': 0, 'segment': 2, 'species': 'red', 'count': 3},
        ],
        'treasures': [
            {'treasure_id': 'juji_key_fc', 'slot_id': lf(0), 'segment': 0, 'leaf_hazard': 'fire'},
        ],
        'hole': {'slot_id': seg(2), 'segment': 2},
        'generated': True,
        'geometry_rerolls': True,
    }


def mutate(**changes):
    table = copy.deepcopy(valid_table())
    table.update(changes)
    return table


class CaveSchemaTests(unittest.TestCase):
    def test_constants_and_slot_id_format(self):
        self.assertEqual(SCHEMA_VERSION, 1)
        self.assertEqual(SLOT_CLASSES, ('segment', 'choke', 'leaf', 'bud'))
        self.assertEqual(set(HAZARDS), {'water', 'elec', 'fire', 'poison'})
        for hazard, spec in HAZARDS.items():
            self.assertIn(spec['kind'], ('hard', 'soft'), hazard)
        self.assertEqual(HAZARD_SPECIES, {'water': 'blue', 'elec': 'yellow', 'fire': 'red', 'poison': 'white'})
        self.assertEqual(SPECIES_HAZARD, {'blue': 'water', 'yellow': 'elec', 'red': 'fire', 'white': 'poison'})
        self.assertEqual(slot_id('forest_1', 3, 'leaf', 7), 'forest_1:f3:leaf:7')

    def test_validate_accepts_valid_table_and_returns_it(self):
        table = valid_table()
        self.assertIs(validate_floor_table(table), table)
        digest = table_digest(table)
        self.assertEqual(len(digest), 64)
        int(digest, 16)

    def test_derive_is_deterministic_for_same_seed(self):
        first = self._derive('seed-same')
        second = self._derive('seed-same')
        self.assertEqual(first, second)
        self.assertEqual(table_digest(first), table_digest(second))

    def test_different_seed_changes_digest(self):
        first = table_digest(self._derive('seed-a'))
        second = table_digest(self._derive('seed-b'))
        self.assertNotEqual(first, second)

    def test_rejects_wrong_schema_unknown_class_and_hazard(self):
        with self.assertRaises(SchemaError):
            validate_floor_table(mutate(schema=SCHEMA_VERSION + 1))
        bad_class = copy.deepcopy(valid_table())
        bad_class['segments'][0]['slot_id'] = f'{CID}:f{FLOOR}:bogus:0'
        with self.assertRaises(SchemaError):
            validate_floor_table(bad_class)
        bad_hazard = copy.deepcopy(valid_table())
        bad_hazard['leaves'][0]['hazard'] = 'lava'
        with self.assertRaises(SchemaError):
            validate_floor_table(bad_hazard)

    def test_rejects_duplicate_slot_ids(self):
        table = copy.deepcopy(valid_table())
        table['buds'][0]['slot_id'] = table['leaves'][0]['slot_id']
        with self.assertRaises(SchemaError):
            validate_floor_table(table)

    def test_rejects_non_contiguous_segment_indices(self):
        table = copy.deepcopy(valid_table())
        table['segments'][2]['index'] = 3
        with self.assertRaises(SchemaError):
            validate_floor_table(table)

    def test_rejects_choke_not_joining_adjacent_segments(self):
        table = copy.deepcopy(valid_table())
        table['chokes'][0]['before_segment'] = 2
        with self.assertRaises(SchemaError):
            validate_floor_table(table)

    def test_rejects_leaf_with_wrong_item_slot_count(self):
        table = copy.deepcopy(valid_table())
        table['leaves'][0]['item_slots'] = 2
        with self.assertRaises(SchemaError):
            validate_floor_table(table)

    def test_rejects_treasure_leaf_binding_violations(self):
        mismatch = copy.deepcopy(valid_table())
        mismatch['treasures'][0]['leaf_hazard'] = 'water'
        with self.assertRaises(SchemaError):
            validate_floor_table(mismatch)
        missing = copy.deepcopy(valid_table())
        missing['treasures'][0]['slot_id'] = slot_id(CID, FLOOR, 'leaf', 99)
        with self.assertRaises(SchemaError):
            validate_floor_table(missing)

    def test_rejects_bud_hazard_already_gated_by_path_choke(self):
        table = copy.deepcopy(valid_table())
        table['chokes'][1]['hazard'] = 'fire'
        with self.assertRaises(SchemaError):
            validate_floor_table(table)

    def test_rejects_hole_not_last_and_treasure_beyond_hole(self):
        not_last = copy.deepcopy(valid_table())
        not_last['hole']['segment'] = 0
        with self.assertRaises(SchemaError):
            validate_floor_table(not_last)
        beyond = copy.deepcopy(valid_table())
        beyond['hole']['segment'] = 1
        beyond['leaves'].append({'slot_id': slot_id(CID, FLOOR, 'leaf', 2), 'index': 2,
                                 'segment': 2, 'hazard': 'fire', 'item_slots': 1})
        beyond['treasures'].append({'treasure_id': 'beyond', 'slot_id': slot_id(CID, FLOOR, 'leaf', 2),
                                    'segment': 2, 'leaf_hazard': 'fire'})
        with self.assertRaises(SchemaError):
            validate_floor_table(beyond)

    def test_requirements_report_segments_paths_and_hole(self):
        table = valid_table()
        report = requirements(table)
        self.assertEqual(set(report), {'treasures', 'hole'})
        entry = report['treasures']['juji_key_fc']
        self.assertEqual(entry['segment'], 0)
        self.assertEqual(entry['leaf_hazard'], 'fire')
        self.assertIsInstance(entry['chokes'], list)
        hole = report['hole']
        self.assertEqual(hole['segment'], 2)
        self.assertEqual(set(hole['chokes']),
                         {slot_id(CID, FLOOR, 'choke', 0), slot_id(CID, FLOOR, 'choke', 1)})

    def test_worked_example_is_water_elec_forest_1(self):
        table = worked_example()
        self.assertEqual(table['cave_id'], 'forest_1')
        self.assertEqual(table['generated'], False)
        self.assertEqual([leaf['hazard'] for leaf in table['leaves']], ['water', 'elec'])
        self.assertEqual([choke['hazard'] for choke in table['chokes']], ['water'])
        self.assertEqual({t['leaf_hazard'] for t in table['treasures']}, {'water', 'elec'})
        self.assertEqual(table['hole']['segment'], 2)
        validate_floor_table(table)

    def test_worked_example_requirements_project_paths(self):
        report = requirements(worked_example())
        self.assertEqual(set(report['treasures']), {'juji_key_fc', 'example_elec_treasure'})
        self.assertEqual(report['treasures']['juji_key_fc']['chokes'], [])
        self.assertEqual(report['treasures']['example_elec_treasure']['chokes'],
                         [slot_id(CID, FLOOR, 'choke', 0)])
        self.assertEqual(report['hole']['chokes'], [slot_id(CID, FLOOR, 'choke', 0)])

    def test_reentry_same_seed_reproduces_table_and_requirements(self):
        first = self._derive('reentry-seed')
        second = self._derive('reentry-seed')
        self.assertEqual(table_digest(first), table_digest(second))
        self.assertEqual(requirements(first), requirements(second))

    def test_derive_from_fixture_validates(self):
        fixture = load_fixture()
        table = self._derive('fixture-seed')
        self.assertEqual(table['schema'], SCHEMA_VERSION)
        self.assertEqual(table['cave_id'], fixture['cave_id'])
        self.assertEqual(table['floor'], fixture['floor'])
        self.assertEqual(table['seed'], 'fixture-seed')
        known = set(fixture['loose_treasures'])
        validate_floor_table(table, known_treasures=known)

    def _derive(self, seed):
        fixture = load_fixture()
        tagged = [{'treasure_id': treasure, 'hazard': 'water'}
                  for treasure in fixture['loose_treasures']]
        return derive_floor_table(
            seed,
            fixture['cave_id'],
            fixture['floor'],
            unit_pool=fixture['unit_pool'],
            unit_candidates=fixture['unit_candidates'],
            tagged_treasures=tagged,
            gates=fixture['gate_types'],
        )


if __name__ == '__main__':
    unittest.main()
