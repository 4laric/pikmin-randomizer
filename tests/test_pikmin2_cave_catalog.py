import unittest
from experimental.pikmin2_cave_catalog import parse,enemy_token

ENEMIES={'KareOoinu_s','Chappy','Rkabuto'}
TREASURES={'gem_one','map01'}


def source(version=1):
    return ('{ {c000} 4 1 {_eof} } 1\n'
            '{ {f000} 4 0 {f001} 4 2 {f008} -1 units.txt {f015} 4 '+str(version)+' {_eof} }\n'
            '{ 2 $2Chappy_gem_one 21 1 KareOoinu_s 4 6 }\n'
            '{ 1 map01 12 }\n{ 1 gate 1200.5 3 }\n'+('{ 2 1 0 Chappy 10 1 }' if version else ''))


class CaveCatalogTests(unittest.TestCase):
    def test_ranges_weights_plants_and_optional_caps(self):
        result=parse(source(),ENEMIES,TREASURES)
        self.assertFalse(result['generated']);self.assertEqual(result['floor_count'],3)
        floor=result['floors'][0]
        self.assertEqual((floor['first_floor'],floor['last_floor']),(1,3))
        self.assertEqual(floor['enemies'][0]['minimum_count'],2)
        self.assertEqual(floor['enemies'][0]['selection_weight'],1)
        self.assertEqual(floor['enemies'][0]['carried_treasure'],'gem_one')
        self.assertEqual(floor['enemies'][1]['target_count'],4)
        self.assertNotIn('minimum_count',floor['enemies'][1])
        self.assertEqual(floor['gates'],[dict(gate_id='gate',life=1200.5,selection_weight=3)])
        self.assertTrue(floor['caps'][0]['empty']);self.assertEqual(floor['caps'][1]['enemy']['enemy_id'],'Chappy')
        self.assertEqual(parse(source(0),ENEMIES,TREASURES)['floors'][0]['caps'],[])
        self.assertEqual(result,parse(source(),ENEMIES,TREASURES))

    def test_native_case_lookup_but_exact_underscore_split(self):
        self.assertEqual(enemy_token('RKabuto',ENEMIES,TREASURES)['enemy_id'],'Rkabuto')
        self.assertEqual(enemy_token('KareOoinu_s',ENEMIES,TREASURES)['enemy_id'],'KareOoinu_s')
        self.assertEqual(enemy_token('$Chappy',ENEMIES,TREASURES)['drop_mode'],1)
        self.assertEqual(enemy_token('$9Chappy',ENEMIES,TREASURES)['drop_semantics'],'source_accepts_unmapped_mode')
        # Native split is strcmp, final ID lookup is stricmp: do not invent a
        # case-insensitive carried-treasure split the game does not perform.
        with self.assertRaises(ValueError):enemy_token('chappy_gem_one',ENEMIES,TREASURES)

    def test_malformed_records_fail_closed(self):
        changes=[('{c000} 4 1','{c000} 4 2'),('{f001} 4 2','{f001} 4 -1'),
                 ('{f008} -1 units.txt','{f008} 4 units.txt'),('units.txt','../units.txt'),
                 ('{ 2 $2','{ 3 $2'),('21 1','-1 1'),('21 1','21 9'),
                 ('1200.5','nan'),('gate 1200','unknown 1200'),('map01 12','missing 12'),
                 ('gem_one 21','missing 21'),('{ 2 1 0','{ 3 1 0'),('{ 2 1 0','{ 2 256 0')]
        for old,new in changes:
            with self.subTest(new=new),self.assertRaises(ValueError):parse(source().replace(old,new),ENEMIES,TREASURES)
        for text in (source()+' trailing',source()[:-1],source().replace('{f015} 4 1','{f099} 4 1')):
            with self.assertRaises(ValueError):parse(text,ENEMIES,TREASURES)
