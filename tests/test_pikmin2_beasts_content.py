import copy
import unittest
from experimental.pikmin2_beasts_content import floor_roster


def catalog():
    rows=[]
    for name,count in [('UjiB',4),('UjiA',2),('UjiA',2),('UjiA',2),('Clover',4),('Tukushi',2),('KareOoinu_s',2)]:
        rows.append({'enemy_id':name,'target_count' if name in ('Clover','Tukushi','KareOoinu_s') else 'minimum_count':count})
    return {'caves':[{'cave':'forest_1','floors':[{'definition_index':0,'first_floor':1,'last_floor':1,'parameters':{'f007':'0','f010':'0'},'enemies':rows,'treasures':[{'treasure_id':'juji_key_fc','source_weight':10,'minimum_count':1,'selection_weight':0}],'gates':[],'caps':[]}]}]}


class ContentTests(unittest.TestCase):
    def test_duplicate_species_rows_keep_distinct_ids(self):
        result=floor_roster(catalog());rows=result['enemies']
        self.assertEqual(len(set(r['definition_id'] for r in rows)),7)
        self.assertEqual(sum(r['source'].get('minimum_count',0) for r in rows),10)
        self.assertTrue(all(r['runtime_status']=='unsupported' for r in rows))

    def test_wrong_treasure_rejected(self):
        c=catalog();c['caves'][0]['floors'][0]['treasures'][0]['treasure_id']='dia_a_red'
        with self.assertRaises(ValueError):floor_roster(c)

    def test_changed_population_rejected(self):
        c=catalog();c['caves'][0]['floors'][0]['enemies'][0]['minimum_count']=5
        with self.assertRaises(ValueError):floor_roster(c)

    def test_exit_flags_distinct(self):
        c=catalog();c['caves'][0]['floors'][0]['parameters']['f010']='1'
        result=floor_roster(c);self.assertTrue(result['exit']['clogged_hole']);self.assertFalse(result['exit']['has_geyser'])


if __name__=='__main__':unittest.main()
