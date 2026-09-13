import unittest
from unittest.mock import patch
from experimental.pikmin2_beasts_floor3_haul import directed_route,support


class HaulRouteTests(unittest.TestCase):
    def test_route_preserves_direction_and_uses_shorter_source_path(self):
        routes=[dict(id=9,position=[0,0,0],links=[8,10]),
                dict(id=8,position=[0,0,10],links=[7]),
                dict(id=10,position=[100,0,0],links=[7]),
                dict(id=7,position=[0,0,20],links=[0]),
                dict(id=0,position=[0,0,30],links=[])]
        self.assertEqual(directed_route(routes,9,0),[9,8,7,0])
        with self.assertRaisesRegex(ValueError,'No directed'):directed_route(routes,0,9)
        self.assertEqual(routes[-1]['links'],[])

    def test_invalid_route_ids_rejected(self):
        node=dict(id=1,position=[0,0,0],links=[])
        for routes,start,end in [([node,node],1,1),([node],0,1),([dict(node,links=[9])],1,1)]:
            with self.subTest(routes=routes),self.assertRaises(ValueError):directed_route(routes,start,end)

    def test_strip_probes_include_edges_and_endpoints(self):
        room=dict(vertices=[],triangles=[])
        with patch('experimental.pikmin2_beasts_floor3_haul.ground_height',return_value=2):
            probes=support(room,[[0,0,0],[0,0,20]])
        self.assertEqual(len(probes),9)
        self.assertEqual({p['position'][0] for p in probes},{-25,0,25})
        self.assertEqual({p['position'][2] for p in probes},{0,10,20})
        self.assertTrue(all(p['position'][1]==2 for p in probes))

    def test_centerline_support_is_not_enough(self):
        def ground(vertices,triangles,x,z):return None if x==25 else 0
        with patch('experimental.pikmin2_beasts_floor3_haul.ground_height',side_effect=ground),self.assertRaisesRegex(ValueError,'strip'):
            support(dict(vertices=[],triangles=[]),[[0,0,0],[0,0,20]])
