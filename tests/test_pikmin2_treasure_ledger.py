import unittest

from experimental.pikmin2_treasure_ledger import (cave_placements, classify, course_table, generator_placements,
                                                  reconcile)

OTAKARA = ['ahiru', 'apple', 'elec', 'fire', 'gas', 'water', 'loozy']
ITEMS = ['fue_a', 'map01', 'key']
ENEMIES = {7: 'Chappy', 73: 'BigTreasure', 0: 'Pelplant'}
ENEMY_IDS = set(ENEMIES.values()) | {'KareOoinu_s'}
CARGO = set(OTAKARA) | set(ITEMS)


def block(payload, version='v0.3', label='x'):
    name = list(label.encode()) + [0] * (32 - len(label))
    head = '{%s} -1 %s%s 1.0 2.0 3.0 0.5 0.0 0.0 ' % (version, '' if version == 'v0.0' else '4 ', ' '.join(map(str, name)))
    return '{ ' + head + payload + ' { {_eof} } }'


PELT = '{pelt} {0000} { 3 0.0 90.0 0.0 {0000} 1 }'
ITEM_PELT = '{pelt} {0000} { 4 0.0 0.0 0.0 {0000} 1 }'
TEKI5 = '{teki} {0005} 7 0 2 90.0 1 100.0 0.0 %d 3 1 1 8 0.0 {0001} 1 1 2'
TEKI4 = '{teki} {0004} 7 2 90.0 1 100.0 0.0 %d 3 1 1 8 0.0 {0001} 1'
TEKI2 = '{teki} {0002} 7 1 0.0 1 100.0 0.0 {0001} 1'


def generator_text(blocks, count=None, version='v0.1'):
    count = len(blocks) if count is None else count
    return '# generatorMgr\n{%s} 0.0 0.0 0.0 %s%d # count\n' % (version, '0.0 ' if version == 'v0.1' else '', count) + '\n'.join(blocks)


STAGES = '''#
2 # courses
{
	name tutorial
	folder user/Kando/map/tutorial
	abe_folder user/Abe/map/tutorial
	start -1 0 2
	startangle 150
	end
	2
		0-1.txt 0 1 1
		30-39.txt 30 39 39
	0
	2
		{t_01} 3 tutorial_1.txt
		{test} 0 caveinfo.txt
	7
}
{
	name forest
	abe_folder user/Abe/map/forest
	end
	0
	0
	0
	5
}
'''

CAVE = ('{ {c000} 4 2 {_eof} }\n2\n'
        '{ {f000} 4 0 {f001} 4 0 {f008} -1 units.txt {f015} 4 1 {_eof} }\n'
        '{ 2 $2Chappy_apple 21 1 KareOoinu_s 4 6 }\n{ 1 map01 12 }\n{ 0 }\n{ 2 1 0 $1Chappy_key 10 1 }\n'
        '{ {f000} 4 1 {f001} 4 1 {f008} -1 units.txt {f015} 4 0 {_eof} }\n'
        '{ 1 BigTreasure 10 1 }\n{ 0 }\n{ 0 }\n')


class CourseTableTests(unittest.TestCase):
    def test_windows_caves_and_declared_counts(self):
        courses = course_table(STAGES)
        self.assertEqual([c['name'] for c in courses], ['tutorial', 'forest'])
        self.assertEqual(courses[0]['nonloop'], [dict(file='0-1.txt', minimum_day=0, maximum_day=1, day_limit=1),
                                                 dict(file='30-39.txt', minimum_day=30, maximum_day=39, day_limit=39)])
        self.assertEqual(courses[0]['caves'][0], dict(tag='t_01', declared_treasures=3, caveinfo='tutorial_1.txt'))
        self.assertEqual((courses[0]['declared_ground_treasures'], courses[1]['declared_ground_treasures']), (7, 5))

    def test_malformed_tables_fail_closed(self):
        for bad in (STAGES.replace('2 # courses', '3 # courses'), STAGES.replace('\t7\n}', '\t7 9\n}'),
                    STAGES.replace('{t_01} 3', '{t_01} x'), STAGES.replace('\tend\n\t2', '\t2')):
            with self.assertRaises(ValueError):
                course_table(bad)


class GeneratorTests(unittest.TestCase):
    def test_pellets_and_held_codes(self):
        text = generator_text([block(PELT, label='otakara'), block(TEKI5 % 0x301, version='v0.1'),
                               block(TEKI4 % 0x401), block(TEKI2), block(ITEM_PELT, version='v0.0')])
        found = generator_placements(text, OTAKARA, ITEMS, ENEMIES)
        self.assertEqual([(p['kind'], p['treasure_id'], p['generator_index'], p['engine_loaded']) for p in found],
                         [('loose', 'apple', 0, True), ('held', 'apple', 1, True), ('held', 'map01', 2, True),
                          ('loose', 'map01', 4, True)])
        self.assertEqual(found[0]['position'], [1.5, 2.0, 3.0])
        self.assertEqual(found[0]['generator_label'], 'otakara')
        self.assertEqual((found[1]['enemy_id'], found[1]['enemy_count'], found[1]['pellet_kind']), ('Chappy', 2, 'otakara'))
        self.assertEqual(found[2]['config_index'], 1)

    def test_blocks_after_declared_count_are_not_loaded(self):
        text = generator_text([block(TEKI5 % 0), block(PELT)], count=1)
        found = generator_placements(text, OTAKARA, ITEMS, ENEMIES)
        self.assertEqual([(p['treasure_id'], p['engine_loaded']) for p in found], [('apple', False)])
        self.assertEqual(classify(CARGO, [dict(p, scope='campaign_surface') for p in found])['apple']['classification'], 'unused')

    def test_malformed_generators_fail_closed(self):
        for bad in (generator_text([block(PELT)], count=2), generator_text([block(PELT.replace('{ 3 ', '{ 1 '))]),
                    generator_text([block(PELT.replace('{0000} 1 }', '{0000} 9 }'))]),
                    generator_text([block(TEKI5 % 0x501)]), generator_text([block(TEKI5 % 0x309)]),
                    generator_text([block(TEKI5.replace('{0005} 7', '{0005} 99') % 0)]),
                    generator_text([block(PELT, version='v0.x')]), generator_text([block(PELT)], version='v0.2')):
            with self.assertRaises(ValueError):
                generator_placements(bad, OTAKARA, ITEMS, ENEMIES)


class CaveTests(unittest.TestCase):
    def test_loose_held_cap_and_boss_drops(self):
        found = cave_placements(CAVE, ENEMY_IDS, CARGO)
        self.assertEqual([(p['kind'], p['treasure_id'], p['first_floor']) for p in found],
                         [('held', 'apple', 1), ('loose', 'map01', 1), ('cap_held', 'key', 1)]
                         + [('boss_drop', t, 2) for t in ('elec', 'fire', 'gas', 'water', 'loozy')])
        self.assertEqual((found[0]['enemy_id'], found[0]['minimum_count'], found[0]['drop_mode']), ('Chappy', 2, 2))
        self.assertEqual((found[1]['minimum_count'], found[1]['selection_weight']), (1, 2))
        self.assertEqual(found[3]['enemy_id'], 'BigTreasure')

    def test_unknown_references_fail_closed(self):
        with self.assertRaises(ValueError):
            cave_placements(CAVE.replace('map01 12', 'map99 12'), ENEMY_IDS, CARGO)
        with self.assertRaises(ValueError):
            cave_placements(CAVE.replace('$2Chappy_apple', '$2Chappy_pear'), ENEMY_IDS, CARGO)
        with self.assertRaises(ValueError):
            cave_placements(CAVE, ENEMY_IDS, CARGO - {'loozy'})
        with self.assertRaises(ValueError):
            cave_placements(CAVE.replace('{ 2 1 0 $1Chappy_key 10 1 }', '{ 2 1 0 $1Chappy_key 10 }'), ENEMY_IDS, CARGO)


class ClassificationTests(unittest.TestCase):
    def test_classification_and_reconciliation(self):
        placements = [dict(treasure_id='ahiru', scope='campaign_surface', file='initgen.txt', engine_loaded=True),
                      dict(treasure_id='apple', scope='campaign_cave'), dict(treasure_id='apple', scope='challenge'),
                      dict(treasure_id='key', scope='challenge'), dict(treasure_id='fire', scope='battle'),
                      dict(treasure_id='fire', scope='challenge')]
        classes = classify({'ahiru', 'apple', 'key', 'fire', 'gas'}, placements)
        self.assertEqual(classes['ahiru'], dict(classification='campaign', campaign_scopes=['campaign_surface'], mode_scopes=[]))
        self.assertEqual(classes['apple']['mode_scopes'], ['challenge'])
        self.assertEqual(classes['key']['classification'], 'mode_only')
        self.assertEqual(classes['fire']['mode_scopes'], ['battle', 'challenge'])
        self.assertEqual(classes['gas']['classification'], 'unused')
        with self.assertRaises(ValueError):
            classify({'ahiru'}, [dict(treasure_id='nope', scope='battle')])
        courses = course_table(STAGES)
        surface = dict(tutorial=[placements[0], dict(treasure_id='apple', scope='campaign_surface', file='nonloop/0-1.txt', engine_loaded=False)])
        caves = dict(tutorial_1=[dict(treasure_id='apple'), dict(treasure_id='apple'), dict(treasure_id='key')])
        result = reconcile(courses, surface, caves, 4, [1, 2, 3, 4])
        self.assertFalse(result['reconciled'])
        self.assertEqual(result['courses'][0]['observed'], 1)
        self.assertEqual(result['courses'][0]['unloaded_block_treasure_ids'], ['apple'])
        self.assertEqual(result['caves'][0]['repeated_definitions'], ['apple'])
        self.assertEqual((result['caves'][0]['observed'], result['caves'][0]['reconciled']), (2, False))
        self.assertEqual(result['declared_total'], 15)
        self.assertTrue(result['dictionary']['contiguous_from_one'])
        self.assertFalse(reconcile(courses, surface, caves, 4, [1, 2, 2, 4])['dictionary']['contiguous_from_one'])


if __name__ == '__main__':
    unittest.main()
