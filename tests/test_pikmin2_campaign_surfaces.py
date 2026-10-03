import copy
import unittest
import hashlib
import json
from pathlib import Path
import tempfile

from scripts.stage_pikmin2_campaign_surfaces import native_geometry, stage_table, mapcode, landing
from scripts.play_pikmin2_campaign_surfaces import launch


class CampaignSurfaceTests(unittest.TestCase):
    def test_distinct_story_destinations(self):
        table = stage_table().decode()
        self.assertEqual(table.count('new_map visible'),4)
        for i,c in enumerate(('tutorial','forest','yakushima','last')):
            self.assertIn(f'id {i}\n file stages/p2_{c}.ini',table)
        self.assertNotIn('stages/stage',table)

    def test_zero_area_face_has_explicit_native_source_mapping(self):
        room=dict(vertices=[[0,0,0],[0,0,10],[10,0,0]],
                  triangles=[[0,1,2],[0,0,0]],mapcodes=[65,65],degenerate_triangles=[1])
        original=copy.deepcopy(room)
        native,retained,omitted=native_geometry(room)
        self.assertEqual((retained,omitted),([0],[1]))
        self.assertEqual(native['triangles'],[[0,1,2]])
        self.assertEqual(room,original)
        room['degenerate_triangles']=[]
        with self.assertRaisesRegex(ValueError,'Degenerate'):native_geometry(room)
        room['triangles'][1]=[0,1,9]
        with self.assertRaisesRegex(ValueError,'index'):native_geometry(room)

    def test_mapcodes_do_not_invent_water_from_walk_sound(self):
        self.assertEqual(mapcode(65),mapcode(73))
        self.assertEqual(mapcode(98),2<<27)
        for invalid in (-1,128,15,True):
            with self.assertRaises(ValueError):mapcode(invalid)

    def test_landing_uses_nearest_red_onion_and_refuses_wet_floor(self):
        def actor(index,p):return dict(item='onyn',onion_index=index,effective_position=p)
        generators={'defaultgen.txt':{'actors':[actor(4,[2,0,2]),actor(1,[2,0,2]),actor(1,[100,0,100])]}}
        room=dict(vertices=[[0,0,0],[10,0,0],[0,0,10]],triangles=[[0,1,2]])
        self.assertEqual(landing(generators,room,[]),[2,40,2])
        with self.assertRaisesRegex(ValueError,'water'):
            landing(generators,room,[dict(min=[0,-100,0],max=[10,5,10],surface=5)])

    def test_launcher_refuses_changed_inputs_and_preserves_saved_campaign(self):
        with tempfile.TemporaryDirectory() as temp:
            run=Path(temp)
            (run/'assets').mkdir()
            (run/'assets/terrain').write_bytes(b'original')
            (run/'native.exe').write_bytes(b'fixture executable placeholder')
            record=dict(schema=1,courses={c:{} for c in ('tutorial','forest','yakushima','last')},
                        files={'terrain':hashlib.sha256(b'original').hexdigest()})
            (run/'campaign-surface-inputs.json').write_text(json.dumps(record))
            calls=[]
            class Result:returncode=0
            def process(*args,**kwargs):calls.append((args,kwargs));return Result()
            self.assertEqual(launch(run,run/'native.exe','forest',process),0)
            self.assertEqual(calls[0][1]['cwd'],run.resolve())
            (run/'assets/terrain').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'changed'):launch(run,run/'native.exe',process=process)
            (run/'assets/terrain').write_bytes(b'original')
            (run/'save/p2-campaign').mkdir(parents=True)
            save=run/'save/p2-campaign/card'
            save.write_bytes(b'preserve')
            with self.assertRaisesRegex(ValueError,'Native saves exist'):launch(run,run/'native.exe',process=process)
            self.assertEqual(save.read_bytes(),b'preserve')
            self.assertEqual(len(calls),1)


if __name__=='__main__':unittest.main()
