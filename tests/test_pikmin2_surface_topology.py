import copy
import unittest
from experimental.pikmin2_surface_topology import audit


class TopologyTests(unittest.TestCase):
    def room(self,triangles,codes=None):
        return dict(vertices=[[0,0,0],[10,0,0],[0,0,10],[0,10,0],[0,0,-10]],
                    triangles=triangles,mapcodes=codes or [65]*len(triangles))
    def test_manifold_preserves_source(self):
        room=self.room([[0,1,2],[1,0,4]])
        old=copy.deepcopy(room);report=audit(room)
        self.assertEqual(room,old)
        self.assertTrue(report['native_conversion_approved'])
        self.assertFalse(report['terrain_usable_alone'])
    def test_junction_is_not_arbitrarily_paired(self):
        report=audit(self.room([[0,1,2],[1,0,4],[0,1,3]]))
        self.assertEqual(len(report['nonmanifold_edges']),1)
        self.assertFalse(report['native_conversion_approved'])
        self.assertTrue(report['topology_unchanged'])
    def test_same_winding_different_slip_not_deleted(self):
        room=self.room([[0,1,2],[1,2,0],[0,1,3]],[103,65,65])
        old=copy.deepcopy(room);report=audit(room)
        group=report['duplicate_faces'][0]
        self.assertTrue(group['same_winding'])
        self.assertFalse(group['identical_physics_codes'])
        self.assertEqual(report['safe_smooth_pairs'],0)
        self.assertEqual(room,old)
    def test_reverse_winding_is_reported_as_distinct(self):
        report=audit(self.room([[0,1,2],[0,2,1],[0,1,3]]))
        self.assertFalse(report['duplicate_faces'][0]['same_winding'])
        self.assertEqual(report['safe_smooth_pairs'],0)
    def test_invalid_geometry_refused(self):
        for triangles in ([[0,1,8]],[[0,0,1]]):
            with self.assertRaises(ValueError):audit(self.room(triangles))
    def test_overfull_even_with_smooth_pair_not_approved(self):
        # Upward coplanar pair plus a wall, all original faces preserved.
        report=audit(self.room([[0,1,2],[1,0,4],[0,1,3]]))
        self.assertEqual(report['safe_smooth_pairs'],1)
        self.assertFalse(report['native_conversion_approved'])

if __name__=='__main__':unittest.main()

