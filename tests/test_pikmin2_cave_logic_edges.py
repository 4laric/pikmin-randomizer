"""Independent edge tests for the lane 39 cave logic (adapted to lane 34 tables).

Originally drafted by the delegated `general` subagent against a draft API; the
API was corrected to consume lane 34's real `p2-cave-floor-table-v1` shape, so
the cases below were carried over and re-pointed at that contract.  These tests
deliberately probe boundaries the focused file does not.
"""
import unittest

from randomizer.cave_logic import (CaveLogicError, hole_requirement, load_cave,
                                   requirement_satisfied, requirements_map, satisfied,
                                   segment_requirement, treasure_requirement, validate_tags)
from randomizer.catalog import can_reach_manifest

CAVE = 'edge_1'


def slot(floor, slot_class, index):
    return '%s:f%d:%s:%d' % (CAVE, floor, slot_class, index)


def segments(floor, count):
    return [{'slot_id': slot(floor, 'segment', i), 'index': i} for i in range(count)]


def choke(floor, index, after, hazard, hardness='hard'):
    return {'slot_id': slot(floor, 'choke', index), 'index': index,
            'after_segment': after, 'before_segment': after + 1, 'hazard': hazard,
            'kind': hardness, 'hardness': hardness, 'unit': 'way2_tsuchi'}


def leaf(floor, index, segment, hazard):
    return {'slot_id': slot(floor, 'leaf', index), 'index': index, 'segment': segment,
            'hazard': hazard, 'item_slots': 1}


def bud(floor, index, segment, species, count=5):
    return {'slot_id': slot(floor, 'bud', index), 'index': index, 'segment': segment,
            'species': species, 'count': count}


def treasure(floor, ident, leaf_index, segment, hazard, leaves):
    return {'treasure_id': ident, 'slot_id': leaves[leaf_index]['slot_id'],
            'segment': segment, 'leaf_hazard': hazard}


def table(floor, segment_count, chokes=(), leaves=(), buds=(), treasures=(), ambient=()):
    leaves = list(leaves)
    items = [treasure(floor, ident, li, seg, hazard, leaves)
             for (ident, li, seg, hazard) in treasures]
    return {'schema': 1, 'seed': 'edge', 'cave_id': CAVE, 'floor': floor,
            'unit_pool': 'pool.txt', 'segments': segments(floor, segment_count),
            'chokes': list(chokes), 'leaves': leaves, 'buds': list(buds),
            'treasures': items, 'hole': {'slot_id': slot(floor, 'segment', segment_count - 1),
                                         'segment': segment_count - 1},
            'generated': False, 'geometry_rerolls': True, 'ambient_hazards': list(ambient)}


def keys(requirement):
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


def side_leaf_table():
    leaves = [leaf(1, 0, 1, 'elec')]
    return table(1, 2, leaves=leaves, treasures=[('side_elec', 0, 1, 'elec')])


class NoChokeTests(unittest.TestCase):
    def test_hazard_without_a_choke_is_only_the_leaf(self):
        cave = load_cave(side_leaf_table())
        self.assertEqual(keys(hole_requirement(cave, 1)), ())
        self.assertEqual(keys(treasure_requirement(cave, 'side_elec')), (('Yellow Onion',),))
        self.assertFalse(satisfied(treasure_requirement(cave, 'side_elec'), {}))
        self.assertTrue(satisfied(treasure_requirement(cave, 'side_elec'), {'Yellow Onion': 1}))


class SegmentBoundaryTests(unittest.TestCase):
    def test_extra_segments_without_chokes_inherit_only_earlier_chokes(self):
        chokes = [choke(1, 0, 0, 'water'), choke(1, 1, 2, 'elec')]
        leaves = [leaf(1, 0, 3, 'water'), leaf(1, 1, 0, 'water')]
        cave = load_cave(table(1, 4, chokes=chokes, leaves=leaves, treasures=[
            ('deep', 0, 3, 'water'), ('shallow', 1, 0, 'water')]))
        self.assertEqual(keys(segment_requirement(cave, 1, 0)), ())
        self.assertEqual(keys(segment_requirement(cave, 1, 1)), (('Blue Onion',),))
        # Segment 2 is after choke0 only (choke1 is after segment2); segment3 both.
        self.assertEqual(keys(segment_requirement(cave, 1, 2)), (('Blue Onion',),))
        self.assertIn(('Yellow Onion',), keys(segment_requirement(cave, 1, 3)))
        self.assertEqual(keys(treasure_requirement(cave, 'shallow')), (('Blue Onion',),))


class MonotonicInheritanceTests(unittest.TestCase):
    def test_three_floor_hole_requirements_grow_with_depth(self):
        f1 = table(1, 2, chokes=[choke(1, 0, 0, 'water')],
                   leaves=[leaf(1, 0, 1, 'water')], treasures=[('t1', 0, 1, 'water')])
        f2 = table(2, 2, chokes=[choke(2, 0, 0, 'elec')],
                   leaves=[leaf(2, 0, 1, 'water')], treasures=[('t2', 0, 1, 'water')],
                   ambient=['poison'])
        f3 = table(3, 2, chokes=[choke(3, 0, 0, 'fire')],
                   leaves=[leaf(3, 0, 1, 'elec')], treasures=[('t3', 0, 1, 'elec')])
        cave = load_cave([f1, f2, f3])
        depth2 = set(keys(hole_requirement(cave, 2)))
        depth3 = set(keys(hole_requirement(cave, 3)))
        self.assertTrue(depth2.issubset(depth3))
        self.assertTrue(depth3 - depth2)
        self.assertIn(('White Onion',), depth3)
        self.assertNotIn(('White Onion',), set(keys(hole_requirement(cave, 1))))


class BudBoundaryTests(unittest.TestCase):
    def test_bud_at_the_choke_source_segment_satisfies_it(self):
        chokes = [choke(1, 0, 0, 'elec')]
        leaves = [leaf(1, 0, 1, 'water')]
        at_source = load_cave(table(1, 2, chokes=chokes, leaves=leaves,
                                    buds=[bud(1, 0, 0, 'yellow')],
                                    treasures=[('t', 0, 1, 'water')]))
        after_it = load_cave(table(1, 2, chokes=chokes, leaves=leaves,
                                   buds=[bud(1, 0, 1, 'yellow')],
                                   treasures=[('t', 0, 1, 'water')]))
        self.assertIn(('Yellow Onion', 'cap:yellow:5'),
                      keys(treasure_requirement(at_source, 't')))
        self.assertNotIn(('Yellow Onion', 'cap:yellow:5'),
                         keys(treasure_requirement(after_it, 't')))

    def test_bud_count_above_the_field_cap_never_satisfies(self):
        chokes = [choke(1, 0, 0, 'elec')]
        leaves = [leaf(1, 0, 1, 'water')]
        cave = load_cave(table(1, 2, chokes=chokes, leaves=leaves,
                               buds=[bud(1, 0, 0, 'yellow', count=150)],
                               treasures=[('t', 0, 1, 'water')]))
        self.assertFalse(satisfied(treasure_requirement(cave, 't'), {'Blue Onion': 1}, 10))


class DedupeTests(unittest.TestCase):
    def test_identical_keys_dedupe_but_distinct_elec_keys_do_not(self):
        # Two identical water chokes collapse to one key.
        same = load_cave(table(1, 3, chokes=[choke(1, 0, 0, 'water'), choke(1, 1, 1, 'water')],
                              leaves=[leaf(1, 0, 2, 'water')], treasures=[('t', 0, 2, 'water')]))
        self.assertEqual(keys(segment_requirement(same, 1, 2)), (('Blue Onion',),))
        # A bud-backed elec key and a bare elec key are both retained.
        leaves = [leaf(1, 0, 2, 'water')]
        deep = table(2, 2, chokes=[choke(2, 0, 0, 'elec')],
                     leaves=[leaf(2, 0, 1, 'water')], treasures=[('deep', 0, 1, 'water')])
        graph = load_cave([table(1, 3, chokes=[choke(1, 0, 0, 'elec')], leaves=leaves,
                                 buds=[bud(1, 0, 0, 'yellow')],
                                 treasures=[('t', 0, 2, 'water')]), deep])
        self.assertEqual(keys(treasure_requirement(graph, 'deep')),
                         (('Blue Onion',), ('Yellow Onion',),
                          ('Yellow Onion', 'cap:yellow:5')))

    def test_cross_floor_duplicate_id_is_rejected(self):
        f1 = table(1, 2, leaves=[leaf(1, 0, 1, 'water')], treasures=[('dup', 0, 1, 'water')])
        f2 = table(2, 2, leaves=[leaf(2, 0, 1, 'water')], treasures=[('dup', 0, 1, 'water')])
        with self.assertRaises(CaveLogicError):
            load_cave([f1, f2])


class TagTests(unittest.TestCase):
    def test_tags_accept_exact_mapping_and_reject_flips(self):
        cave = load_cave(side_leaf_table())
        self.assertEqual(validate_tags(cave, {'side_elec': 'elec'}), {'side_elec': 'elec'})
        with self.assertRaises(CaveLogicError):
            validate_tags(cave, {'side_elec': 'water'})
        with self.assertRaises(CaveLogicError):
            validate_tags(cave, {})


class SerialisedLiteralTests(unittest.TestCase):
    def test_unknown_and_empty_literals_raise(self):
        for literal in ({'mystery': True}, {}, {'captain': False},
                        {'item': ''}, {'capacity': 0, 'color': 'yellow'}):
            with self.subTest(literal=literal), self.assertRaises(CaveLogicError):
                requirement_satisfied([[literal]], {}, {})


class HookTests(unittest.TestCase):
    def test_hook_uses_cave_rule_then_falls_back_to_legacy(self):
        cave = load_cave(side_leaf_table())
        manifest = {'schema': 9, 'starting_flarlic': 2,
                    'cave_requirements': requirements_map(cave)}
        self.assertTrue(can_reach_manifest('side_elec', {'Yellow Onion': 1}, manifest))
        self.assertFalse(can_reach_manifest('side_elec', {'Blue Onion': 1}, manifest))
        # Empty cave_requirements must not change a legacy result.
        legacy = {'schema': 0, 'cave_requirements': {}}
        self.assertTrue(can_reach_manifest('Pikmin: Whimsical Radar',
                                           {'Yellow Onion': 1, 'Blue Onion': 1}, legacy))
        self.assertFalse(can_reach_manifest('Pikmin: Whimsical Radar', {}, legacy))


if __name__ == '__main__':
    unittest.main()
