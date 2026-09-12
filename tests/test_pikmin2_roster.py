import json
from pathlib import Path
import struct
import unittest

from experimental.pikmin2_roster import placements, _private


class RosterTests(unittest.TestCase):
    def test_source_group_offsets_are_deterministic_and_grounded(self):
        # Positive Y winding under imported collision convention.
        room=dict(vertices=[[-100,0,-100],[100,0,-100],[100,0,100],[-100,0,100]],
                  triangles=[[0,1,2],[0,2,3]],spawns=[dict(type=0,position=[0,10,0],angle=30,radius=40,min=2,max=3)])
        actors=[dict(instance_id='one'),dict(instance_id='two')]
        a=placements(room,actors,0)
        self.assertEqual(a,placements(room,actors,0))
        self.assertEqual(a[0]['position'],[20,0,0])
        self.assertEqual(a[0]['source_position'],[0,10,0])
        self.assertEqual(a[0]['ground_projection_delta'],-10)
        self.assertEqual(a[0]['angle'],30)
        with self.assertRaises(ValueError):placements(room,actors*2,0)
        with self.assertRaises(ValueError):placements(room,actors,2)
        room['triangles']=[]
        with self.assertRaises(ValueError):placements(room,actors,0)

    def test_private_guard_rejects_outside_and_hardlink(self):
        import tempfile,os
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);run=root/'run';run.mkdir()
            with self.assertRaises(ValueError):_private(root/'outside',run)
            source=root/'source';source.write_text('untouched');linked=run/'linked';os.link(source,linked)
            with self.assertRaises(ValueError):_private(linked,run)
            self.assertEqual(source.read_text(),'untouched')

    def test_audit_rejects_fixture_overlap_and_disconnected_return(self):
        from experimental.pikmin2_roster import audit
        room=dict(vertices=[[-1000,0,-1000],[1000,0,-1000],[1000,0,1000],[-1000,0,1000]],
                  triangles=[[0,1,2],[0,2,3]],routes=[dict(id=0,position=[0,0,-100],links=[1]),dict(id=1,position=[300,0,-300],links=[0])])
        actor=dict(position=[300,0,-300],category='enemy',catalog_id='YellowKochappy')
        audit(room,[actor],1)
        self.assertEqual(actor['terrain_route_probe']['destination_route'],0)
        room['routes'][1]['links']=[]
        with self.assertRaises(ValueError):audit(room,[actor],1)
        with self.assertRaises(ValueError):audit(room,[dict(actor,position=[0,0,-100])],1)
