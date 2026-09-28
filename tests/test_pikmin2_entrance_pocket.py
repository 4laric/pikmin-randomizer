import copy
import unittest
from experimental.pikmin2_entrance_pocket import subset,validate_probes,CENTER


def room():
    x,y,z=CENTER
    return dict(vertices=[[x-100,y,z-100],[x-100,y,z+100],[x+100,y,z+100],[x+100,y,z-100],
                          [x+500,y,z],[x+510,y,z],[x+500,y,z+10]],
                triangles=[[0,2,1],[0,3,2],[4,6,5]],mapcodes=[103,65,9],routes=[])


class EntrancePocketTests(unittest.TestCase):
    def test_preserves_source_vertices_triangles_and_slips(self):
        source=room();before=copy.deepcopy(source);pocket=subset(source)
        self.assertEqual(pocket['source_triangle_ids'],[0,1])
        self.assertEqual(pocket['mapcodes'],[103,65])
        for i,tri in enumerate(pocket['triangles']):
            self.assertEqual([pocket['source_vertex_ids'][v] for v in tri],source['triangles'][pocket['source_triangle_ids'][i]])
        self.assertEqual(source,before)
        self.assertEqual(pocket['routes'],[])
    def test_all_travel_probes_match_exact_original_ground(self):
        source=room();probes=validate_probes(source,subset(source),[])
        self.assertGreaterEqual(len(probes),180)
        self.assertTrue(all(p['source_height']==p['subset_height']==80 for p in probes))
    def test_refuses_water_overlap(self):
        source=room();box=dict(min=[-300,0,1000],max=[0,100,1300],surface=100)
        with self.assertRaisesRegex(ValueError,'water'):validate_probes(source,subset(source),[box])
    def test_refuses_nonmanifold_source_even_if_geometry_coincident(self):
        source=room();source['triangles'].append([0,2,1]);source['mapcodes'].append(65)
        with self.assertRaisesRegex(ValueError,'nonmanifold'):subset(source)
    def test_missing_ground_refused(self):
        source=room();pocket=subset(source);pocket['triangles']=[]
        with self.assertRaisesRegex(ValueError,'ground'):validate_probes(source,pocket,[])
    def test_empty_and_invalid_selection_refused(self):
        with self.assertRaises(ValueError):subset(room(),center=[5000,0,5000])
        with self.assertRaises(ValueError):subset(room(),half_width=-1)

if __name__=='__main__':unittest.main()
