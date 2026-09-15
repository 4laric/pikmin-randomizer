import json
import tempfile
from pathlib import Path
import unittest

from experimental.pikmin2_assembly import transform
from experimental.pikmin2_beasts_assembly import cell_audit
from experimental.pikmin2_beasts_floor3_assembly import layout
from experimental.pikmin2_beasts_floor3_runtime import validate
from experimental.pikmin2_beasts_floor4 import ROOMS,GOALS,build
from tests.test_pikmin2_beasts_floor3_runtime import evidence,party


class FloorFourTests(unittest.TestCase):
    def test_source_offset_door_and_five_caps_pair_without_overlap(self):
        mid,north=ROOMS;way='way2_tsuchi';cap='item_cap_tsuchi'
        specs={mid:([5,7],[(0,0,[0,0,-595]),(1,1,[425,0,-340]),(2,1,[425,0,340]),(3,2,[0,0,595]),(4,3,[-425,0,340]),(5,3,[-425,0,-340])]),
               north:([3,3],[(0,2,[-170,0,255])]),way:([1,1],[(0,0,[0,0,-85]),(1,2,[0,0,85])]),cap:([1,1],[(0,2,[0,0,85])])}
        units={n:dict(cells=c,doors=[dict(id=i,direction=d,waypoint=i) for i,d,p in rows]) for n,(c,rows) in specs.items()}
        rooms={n:dict(routes=[dict(id=i,position=p) for i,d,p in rows]) for n,(_,rows) in specs.items()}
        instances,seams=layout(units,rooms,block=mid,north=north,cap=cap)
        self.assertEqual(instances[2],(north,0,[170,0,-1020]))
        self.assertEqual(len(instances),8);self.assertEqual(len(seams),7)
        self.assertEqual(len(cell_audit(instances,units)),8)
        for a,b in seams:
            def endpoint(pair):
                i,d=pair;n,t,o=instances[i];door=next(x for x in units[n]['doors'] if x['id']==d)
                p=next(x for x in rooms[n]['routes'] if x['id']==door['waypoint'])
                return transform(p['position'],t,o),(door['direction']+t)%4
            pa,da=endpoint(a);pb,db=endpoint(b)
            self.assertEqual(pa,pb);self.assertEqual((da-db)%4,2)

    def test_floor4_goals_cannot_use_floor3_traversal_evidence(self):
        log=evidence()
        with self.assertRaises(ValueError):validate(log,party(),goals=GOALS)
        lines=log.splitlines();lines=[line for line in lines if not line.startswith('P2_FLOOR3_POINT')]
        points=[f'P2_FLOOR3_POINT index={i} x={x} y=0 z={z} ground=0' for i,(x,z) in enumerate(GOALS)]
        lines[2:2]=points
        self.assertEqual(validate('\n'.join(lines)+'\n',party(),goals=GOALS)['points'],12)

    def test_final_package_provenance_rejected_before_disc_access(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'catalog.json').write_text('{}')
            (root/'final-floors.json').write_text(json.dumps(dict(policy='wrong',catalog_sha256='a'*64)))
            with self.assertRaises(ValueError):build(root/'absent.iso',root/'catalog.json',root,root,root/'output')
            self.assertFalse((root/'output').exists())


if __name__=='__main__':unittest.main()
