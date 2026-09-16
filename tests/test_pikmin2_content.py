import copy
import unittest
from experimental.pikmin2_content import roster, candidates, manifest


def definitions():
    return [dict(number=1,parameters={},enemies=[dict(id='YellowKochappy',packed_weight=40,placement_type=0)],
                 treasures=[dict(id='tape_yellow',packed_weight=10),dict(id='dia_a_red',packed_weight=10)]),
            dict(number=2,parameters={},enemies=[dict(id='BlackPom',packed_weight=20,placement_type=1),
                 dict(id='YellowKochappy',packed_weight=70,placement_type=0),dict(id='Clover',packed_weight=2,placement_type=6)],
                 treasures=[dict(id='map01',packed_weight=10)])]


class ContentTests(unittest.TestCase):
    def test_packed_population_and_plant_counts(self):
        floors=roster(definitions())
        self.assertEqual(sum(a['catalog_id']=='YellowKochappy' for a in floors[0]['actors']),4)
        self.assertEqual(sum(a['catalog_id']=='YellowKochappy' for a in floors[1]['actors']),7)
        self.assertEqual(sum(a['category']=='plant' for a in floors[1]['actors']),2)
        ids=[a['instance_id'] for f in floors for a in f['actors']]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertNotEqual(floors[0]['actors'][0]['instance_id'],floors[1]['actors'][2]['instance_id'])
        self.assertIsNone(floors[0]['actors'][0]['placement'])

    def test_reject_unimplemented_weighted_population(self):
        for value in (-1,41):
            f=definitions();f[0]['enemies'][0]['packed_weight']=value
            with self.assertRaises(ValueError): roster(f)

    def test_transforms_preserve_source_height_radius_and_heading(self):
        slot=dict(type=0,position=[10,25,20],angle=135,radius=85,min=2,max=2)
        imported=dict(floors=[dict(unit_candidates=['room'])],units={'room':dict(spawn_candidates=[slot])})
        before=copy.deepcopy(imported)
        result=candidates(imported,1,[('room',1,[0,0,100])])[0]
        self.assertEqual(result['position'],[-20,25,110])
        self.assertEqual(result['angle'],45)
        self.assertEqual(result['source'],slot)
        self.assertEqual(imported,before)
        with self.assertRaises(ValueError): candidates(imported,1,[('other',0,[0,0,0])])

    def test_only_unique_source_item_slot_resolves(self):
        slot=dict(type=2,position=[0,10,640],angle=240,radius=0,min=1,max=1)
        imported=dict(floors=[dict(unit_candidates=['room']),dict(unit_candidates=['room'])],
                      units={'room':dict(spawn_candidates=[slot])})
        layouts=[[('room',0,[0,0,0]),('room',2,[0,0,1020])],[('room',0,[0,0,0])]]
        result=manifest(definitions(),imported,layouts,{})
        self.assertFalse(result['native_ready'])
        self.assertTrue(all(a['placement'] is None for a in result['floors'][0]['actors']))
        item=next(a for a in result['floors'][1]['actors'] if a['category']=='treasure')
        self.assertEqual(item['placement']['position'],[0,10,640])
        self.assertEqual(item['catalog_id'],'map01')
        self.assertEqual(item['instance_id'],'tutorial_1:floor2:treasure:map01:0')
        self.assertEqual(result,manifest(definitions(),imported,layouts,{}))
