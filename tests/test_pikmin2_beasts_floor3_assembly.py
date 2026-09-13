import copy
import unittest

from experimental.pikmin2_assembly import transform
from experimental.pikmin2_beasts_assembly import cell_audit, seam_audit
from experimental.pikmin2_beasts_floor3_assembly import BLOCK, NORTH, WAY, CAP, layout, return_audit


def data():
    specs={BLOCK:([4,4],[(0,0,[-85,0,-340]),(1,2,[85,0,340]),(2,3,[-340,0,85])]),
           NORTH:([5,5],[(0,2,[0,0,425])]), WAY:([1,1],[(0,0,[0,0,-85]),(1,2,[0,0,85])]),
           CAP:([1,1],[(0,2,[0,0,85])])}
    units={n:dict(cells=cells,doors=[dict(id=i,direction=d,waypoint=i) for i,d,p in rows]) for n,(cells,rows) in specs.items()}
    rooms={n:dict(routes=[dict(id=i,position=p) for i,d,p in rows]) for n,(_,rows) in specs.items()}
    return units,rooms


class FloorThreeAssemblyTests(unittest.TestCase):
    def test_source_doors_determine_nonoverlapping_layout(self):
        units,rooms=data();instances,seams=layout(units,rooms)
        self.assertEqual(len(instances),5);self.assertEqual(len(seams),4)
        self.assertEqual(instances[1],(WAY,0,[-85,0,-425]))
        self.assertEqual(instances[2],(NORTH,0,[-85,0,-935]))
        self.assertEqual(len(cell_audit(instances,units)),5)
        seen=set()
        def endpoint(pair):
            i,d=pair;name,turn,offset=instances[i]
            door=next(x for x in units[name]['doors'] if x['id']==d)
            point=next(x for x in rooms[name]['routes'] if x['id']==door['waypoint'])
            return transform(point['position'],turn,offset),(door['direction']+turn)%4
        for a,b in seams:
            self.assertNotIn(a,seen);self.assertNotIn(b,seen);seen.update((a,b))
            pa,da=endpoint(a);pb,db=endpoint(b)
            self.assertEqual(pa,pb);self.assertEqual((da-db)%4,2)
        self.assertEqual(len(seen),sum(len(units[n]['doors']) for n,_,_ in instances))
        bad=copy.deepcopy(instances);bad[2]=(NORTH,0,[0,0,0])
        with self.assertRaises(ValueError):cell_audit(bad,units)

    def test_return_target_preserves_one_way_leaf_and_rejects_cut(self):
        room=dict(routes=[dict(id=0,links=[1],position=[0,0,0]),
                          dict(id=1,links=[0],position=[1,0,0]),
                          dict(id=2,links=[1],position=[2,0,0])])
        original=copy.deepcopy(room)
        result=return_audit(room,[0,0,0])
        self.assertTrue(result['all_sources_reach_target']);self.assertFalse(result['all_pairs_connected'])
        self.assertEqual(room,original)
        room['routes'][2]['links']=[]
        with self.assertRaisesRegex(ValueError,'cannot reach'):return_audit(room,[0,0,0])
        with self.assertRaisesRegex(ValueError,'Ambiguous'):return_audit(original,[99,0,0])
        original['routes'][2]['position']=[0,0,0]
        with self.assertRaisesRegex(ValueError,'Ambiguous'):return_audit(original,[0,0,0])

    def test_full_seam_strip_requires_floor(self):
        units,rooms=data();instances,seams=layout(units,rooms)
        room=dict(vertices=[[-2000,0,-2000],[2000,0,-2000],[2000,0,2000],[-2000,0,2000]],triangles=[[0,1,2],[0,2,3]])
        result=seam_audit(room,instances,seams,units,rooms)
        self.assertEqual(sum(len(s['samples']) for s in result),156)
        room['triangles']=[]
        with self.assertRaises(ValueError):seam_audit(room,instances,seams,units,rooms)


if __name__ == '__main__':unittest.main()
