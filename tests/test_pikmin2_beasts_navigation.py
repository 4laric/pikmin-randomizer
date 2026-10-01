import copy
import unittest

from experimental.pikmin2_beasts_navigation import interpret


def example():
    return dict(vertices=[[-10,2,-10],[10,2,-10],[10,2,10],[-10,2,10]], triangles=[[0,1,2],[0,2,3]],
        routes=[dict(id=0,links=[1],position=[-5,0,0],radius=1),
                dict(id=1,links=[0],position=[0,0,0],radius=1),
                dict(id=2,links=[1],position=[5,0,0],radius=1)],
        spawns=[dict(type=1,position=[0,0,0]),dict(type=2,position=[100,0,0])])


class NavigationTests(unittest.TestCase):
    def test_one_way_leaf_can_return_without_reverse_link(self):
        room=example(); original=copy.deepcopy(room)
        staged,audit=interpret(room,dict(doors=[dict(waypoint=0)]))
        self.assertEqual(room,original)
        self.assertFalse(audit['all_pairs_connected'])
        self.assertTrue(audit['all_sources_reach_every_door'])
        self.assertFalse(audit['inverse_links_added'])
        self.assertEqual([p['links'] for p in staged['routes']],[[1],[0],[1]])
        self.assertEqual([p['position'][1] for p in staged['routes']],[0,2,2])
        self.assertEqual(staged['spawns'],original['spawns'])

    def test_height_mismatch_is_not_missing_ground(self):
        _,audit=interpret(example(),dict(doors=[dict(waypoint=0)]))
        supported,missing=audit['spawn_height_audit']
        self.assertTrue(supported['has_floor_support'])
        self.assertFalse(supported['exact_height_match'])
        self.assertEqual(supported['delta_y'],2)
        self.assertFalse(missing['has_floor_support'])
        self.assertIsNone(missing['delta_y'])

    def test_invalid_graphs_and_unsupported_coordinates_rejected(self):
        for change in ('missing','duplicate','unsupported','nan','door','empty'):
            room=example();definition=dict(doors=[dict(waypoint=0)])
            if change=='missing':room['routes'][0]['links']=[99]
            elif change=='duplicate':room['routes'][1]['id']=0
            elif change=='unsupported':room['routes'][1]['position'][0]=100
            elif change=='nan':room['routes'][1]['position'][1]=float('nan')
            elif change=='door':definition['doors'][0]['waypoint']=99
            else:definition['doors']=[]
            with self.subTest(change=change),self.assertRaises(ValueError):interpret(room,definition)

    def test_door_reachability_not_assumed(self):
        room=example();room['routes'][2]['links']=[]
        _,audit=interpret(room,dict(doors=[dict(waypoint=0)]))
        self.assertFalse(audit['all_sources_reach_every_door'])
        self.assertEqual(audit['door_route_audit'][0]['unreachable_sources'],[2])


if __name__ == '__main__':unittest.main()
