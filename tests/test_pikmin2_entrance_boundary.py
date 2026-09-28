import copy
import math
import unittest
from experimental.pikmin2_collision import plane,adjacency
from scripts.stage_pikmin2_entrance import boundary_room


class BoundaryTests(unittest.TestCase):
    def room(self):
        return dict(vertices=[[-220,80,1130],[-220,80,1190],[-160,80,1190]],
                    triangles=[[0,2,1]],mapcodes=[103],routes=[])
    def test_only_wall_geometry_added_source_unchanged(self):
        source=self.room();old=copy.deepcopy(source);result=boundary_room(source)
        self.assertEqual(source,old)
        self.assertEqual(result['vertices'][:3],old['vertices'])
        self.assertEqual(result['triangles'][:1],old['triangles'])
        self.assertEqual(result['mapcodes'][:1],[103])
        self.assertEqual(len(result['triangles']),65)
        adjacency(result['triangles'])
    def test_walls_inward_vertical_and_high(self):
        result=boundary_room(self.room())
        for tri in result['triangles'][1:]:
            nx,ny,nz,d=plane(result['vertices'],tri)
            self.assertAlmostEqual(ny,0)
            self.assertGreater(nx*-190+nz*1160-d,59)
        added=result['vertices'][3:]
        self.assertEqual(min(v[1] for v in added),-1920)
        self.assertEqual(max(v[1] for v in added),4176)
        self.assertTrue(all(abs(math.hypot(v[0]+190,v[2]-1160)-60)<1e-8 for v in added))
    def test_polygon_stays_within_declared_disk_with_body_margin(self):
        result=boundary_room(self.room())
        for radius in (6,10,20):
            for i in range(360):
                angle=i*math.pi/180
                point=[-190+(60-radius-1)*math.cos(angle),80,1160+(60-radius-1)*math.sin(angle)]
                for tri in result['triangles'][1:]:
                    nx,ny,nz,d=plane(result['vertices'],tri)
                    self.assertGreaterEqual(nx*point[0]+ny*point[1]+nz*point[2]-d,radius)

if __name__=='__main__':unittest.main()
