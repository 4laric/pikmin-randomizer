import unittest
from experimental.pikmin2_beasts_assembly import ROOM,WAY,CAP,layout,cell_audit,seam_audit
from experimental.pikmin2_assembly import transform


def data():
    units={ROOM:dict(cells=[5,5],doors=[dict(id=i,direction=i,waypoint=i) for i in range(4)]),
           WAY:dict(cells=[1,1],doors=[dict(id=0,direction=0,waypoint=0),dict(id=1,direction=2,waypoint=1)]),
           CAP:dict(cells=[1,1],doors=[dict(id=0,direction=2,waypoint=0)])}
    rooms={ROOM:dict(routes=[dict(id=i,position=p) for i,p in enumerate(([0,0,-425],[425,0,0],[0,0,425],[-425,0,0]))]),
           WAY:dict(routes=[dict(id=0,position=[0,0,-85]),dict(id=1,position=[0,0,85])]),
           CAP:dict(routes=[dict(id=0,position=[0,0,85])])}
    return units,rooms


class BeastsAssemblyTests(unittest.TestCase):
    def test_every_door_paired_opposite_and_coincident(self):
        units,rooms=data();instances,seams=layout(units,rooms)
        self.assertEqual(len(instances),9);self.assertEqual(len(seams),8)
        self.assertEqual((instances,seams),layout(units,rooms))
        seen=set()
        def endpoint(pair):
            i,d=pair;name,turn,offset=instances[i];door=units[name]['doors'][d]
            return transform(rooms[name]['routes'][door['waypoint']]['position'],turn,offset),(door['direction']+turn)%4
        for a,b in seams:
            self.assertNotIn(a,seen);self.assertNotIn(b,seen);seen.update((a,b))
            pa,da=endpoint(a);pb,db=endpoint(b)
            self.assertEqual(pa,pb);self.assertEqual((da-db)%4,2)
        self.assertEqual(len(seen),sum(len(units[n]['doors']) for n,_,_ in instances))
        self.assertEqual(len(cell_audit(instances,units)),9)
        with self.assertRaises(ValueError):cell_audit(instances+instances[:1],units)

    def test_seam_ground_probe_rejects_gap(self):
        units,rooms=data();instances,seams=layout(units,rooms)
        room=dict(vertices=[[-1000,0,-1000],[2000,0,-1000],[2000,0,1000],[-1000,0,1000]],triangles=[[0,1,2],[0,2,3]])
        report=seam_audit(room,instances,seams,units,rooms)
        self.assertEqual(sum(len(s['samples']) for s in report),312)
        room['triangles']=[]
        with self.assertRaises(ValueError):seam_audit(room,instances,seams,units,rooms)
