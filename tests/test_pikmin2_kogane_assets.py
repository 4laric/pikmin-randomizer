import unittest
from pathlib import Path
from experimental.pikmin2_kogane_assets import (SPECIES, DROP_TABLES, MAX_FLIPS, FART_GAS_DURATION,
                                                FART_STATE_GATE, animation_rows, parse_parms, drop_for, extract)

PARM_FIXTURE = """# Creature::Property
{
	{s000} 4 0.500000 	# friction(not used)
	{_eof}
}
# EnemyParmsBase
{
	{fp00} 4 1000.000000 	# life
	{fp22} 4 20.000000 	# attack hit range
	{_eof}
}
# EnemyParmsBase
{
	{fp01} 4 15.000000 	# appear min
	{fp40} 4 0.800000 	# scale
	{_eof}
}
"""


class SpawnRegistryTests(unittest.TestCase):
    """Spawn identity: IDs 9/10/11 map to distinct Obj/Mgr classes sharing one model bank."""

    def test_registered_ids(self):
        self.assertEqual({s: v['enemy_id'] for s, v in SPECIES.items()},
                         {'kogane': 9, 'wealthy': 10, 'fart': 11})

    def test_distinct_classes_and_textures(self):
        classes = {(v['obj_class'], v['mgr_class']) for v in SPECIES.values()}
        textures = {v['change_texture'] for v in SPECIES.values()}
        self.assertEqual(len(classes), 3)
        self.assertEqual(len(textures), 3)
        self.assertEqual(SPECIES['kogane']['obj_class'], 'Game::Koganemushi::Obj')

    def test_distinct_karada_kcolors(self):
        self.assertEqual(len({tuple(v['karada_kcolor']) for v in SPECIES.values()}), 3)


class DropTableTests(unittest.TestCase):
    """Defeat/drop behavior per flip count, surface vs cave, demo-flag branches."""

    def test_table_shape(self):
        for table in DROP_TABLES.values():
            self.assertEqual(len(table), MAX_FLIPS)
            for entry in table:
                self.assertEqual(set(entry), {'surface', 'cave'})

    def test_kogane_drops(self):
        self.assertEqual(drop_for('kogane', 0, False), ('pellet', 'PELLET_NUMBER_ONE', 1))
        self.assertEqual(drop_for('kogane', 0, True), ('doping', 'HONEY_Y', 1))
        self.assertEqual(drop_for('kogane', 1, False), ('doping', 'HONEY_Y', 2))
        self.assertEqual(drop_for('kogane', 2, False), ('doping', 'HONEY_Y', 3))
        self.assertEqual(drop_for('kogane', 2, False, demo_flag=True), ('doping', 'HONEY_R', 1))

    def test_wealthy_drops(self):
        self.assertEqual(drop_for('wealthy', 0, False), ('pellet', 'PELLET_NUMBER_FIVE', 3))
        self.assertEqual(drop_for('wealthy', 0, True), ('doping', 'HONEY_Y', 3))
        self.assertEqual(drop_for('wealthy', 1, False), ('doping', 'HONEY_Y', 3))
        self.assertEqual(drop_for('wealthy', 1, True, demo_flag=True), ('doping', 'HONEY_R', 1))

    def test_fart_drops(self):
        self.assertEqual(drop_for('fart', 0, False), ('doping', 'HONEY_Y', 3))
        self.assertEqual(drop_for('fart', 1, False), ('doping', 'HONEY_Y', 3))
        self.assertEqual(drop_for('fart', 1, False, demo_flag=True), ('doping', 'HONEY_B', 1))
        self.assertEqual(drop_for('fart', 2, True, demo_flag=True), ('doping', 'HONEY_B', 1))

    def test_drop_bounds(self):
        for bad in [('unknown', 0, False), ('kogane', -1, False), ('kogane', 3, False), ('kogane', True, False)]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                drop_for(*bad)


class BehaviorConstantTests(unittest.TestCase):
    """Representative behavior: Doodlebug gas and shared flip/escape contract."""

    def test_gas_contract(self):
        self.assertEqual(FART_GAS_DURATION, 2.5)
        self.assertEqual(FART_STATE_GATE, 2)

    def test_animation_events(self):
        rows = animation_rows('3 { a move.bca 2 0 11 1 -1 } { a wait.bca 0 0 14 1 -1 } { a damage.bca 5 2 7 3 29 4 -1 }')
        self.assertEqual([r['file'] for r in rows], ['move.bca', 'wait.bca', 'damage.bca'])
        self.assertEqual(rows[2]['events'], [[5, 2], [7, 3], [29, 4]])

    def test_invalid_registry(self):
        for text in ['2 { a a.bca -1 }', '1 { a a.bca 15 -1 }', '1 { a ../a.bca -1 }',
                     '2 { a a.bca -1 } { a a.bca -1 }']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                animation_rows(text)


class ParmParseTests(unittest.TestCase):
    def test_sections_preserved(self):
        sections = parse_parms(PARM_FIXTURE)
        self.assertEqual([s['section'] for s in sections],
                         ['Creature::Property', 'EnemyParmsBase', 'EnemyParmsBase'])
        self.assertEqual(sections[1]['parms']['fp22'], 20.0)
        self.assertEqual(sections[2]['parms']['fp40'], 0.8)

    def test_duplicate_key_rejected(self):
        text = '# EnemyParmsBase\n{\n\t{fp00} 4 1.0\n\t{fp00} 4 2.0\n}\n'
        with self.assertRaises(ValueError):
            parse_parms(text)

    def test_malformed_rejected(self):
        with self.assertRaises(ValueError):
            parse_parms('# EnemyParmsBase\n{\n}\n')


class BudgetTests(unittest.TestCase):
    def test_budget_rejected_before_io(self):
        for count in [1, 9, True]:
            with self.subTest(count=count), self.assertRaises(ValueError):
                extract(Path('missing'), Path('unused'), count)


if __name__ == '__main__':
    unittest.main()
