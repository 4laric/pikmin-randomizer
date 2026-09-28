import unittest
from experimental.pikmin2_surface_physics import water_boxes, in_water, surface_mapcode
from experimental.pikmin2_collision import translate_mapcode


class SurfacePhysicsTests(unittest.TestCase):
    def setUp(self): self.box=water_boxes('0 { 1 -140 -55 350 960 45 1150 }')[0]
    def test_source_bounds_preserved(self):
        self.assertEqual(self.box['min'],[-140,-55,350])
        self.assertEqual(self.box['max'],[960,45,1150])
        self.assertEqual(self.box['runtime_min_y'],-1055)
    def test_surface_threshold_and_bottom_semantics(self):
        self.assertTrue(in_water(self.box,[0,42,500]))
        self.assertFalse(in_water(self.box,[0,42.001,500]))
        self.assertTrue(in_water(self.box,[0,-5000,500]))
    def test_shore_sphere_overlap(self):
        self.assertFalse(in_water(self.box,[-141,40,500]))
        self.assertTrue(in_water(self.box,[-141,40,500],1))
        self.assertTrue(in_water(self.box,[-140,40,350]))
        self.assertFalse(in_water(self.box,[0,40,1151]))
    def test_entrance_and_landing_dry(self):
        self.assertFalse(in_water(self.box,[-190,80,1160]))
        self.assertFalse(in_water(self.box,[-137.643,0,3033.014]))
    def test_reject_unsupported_or_malformed(self):
        for text in ('1 { 0 }','0 { -1 }','0 { 1 0 0 0 1 1 }','0 { 1 0 0 0 1 nan 1 }','0 { 1 1 0 0 0 1 1 }','0 { 0 } extra'):
            with self.subTest(text=text),self.assertRaises(ValueError): water_boxes(text)
    def test_materials_not_water_and_default_unchanged(self):
        for attr in (3,9):
            self.assertEqual(surface_mapcode(attr)>>29,0)
            with self.assertRaises(ValueError): translate_mapcode(attr)
        self.assertEqual((surface_mapcode(99)>>27)&3,2)
        self.assertEqual((surface_mapcode(3)>>25)&1,1)
        self.assertEqual((surface_mapcode(67)>>25)&1,0)
    def test_reject_unaudited_materials_flags_and_probe(self):
        for code in (4,8,10,128,-1):
            with self.assertRaises(ValueError): surface_mapcode(code)
        with self.assertRaises(ValueError): in_water(self.box,[0,0,0],-1)


class TranslationInterfaceTests(unittest.TestCase):
    def test_legacy_bytes_and_explicit_default_match_prechange_golden(self):
        import struct,hashlib
        from experimental.pikmin2_collision import chunk,attach_collision
        room=dict(vertices=[[0,0,0],[0,0,10],[10,0,10]],triangles=[[0,2,1]],mapcodes=[18],routes=[])
        mod=chunk(0x10,struct.pack('>I',1)+bytes(20)+struct.pack('>fff',99,98,97))+chunk(0xffff,b'')
        old=attach_collision(mod,room)
        self.assertEqual(old,attach_collision(mod,room,mapcode_translator=translate_mapcode))
        self.assertEqual(hashlib.sha256(old).hexdigest(),'adf7cef80c22ee8a157b8e0898bae672d9edcc058c0a1a6130fc26ac025e897e')
        room['mapcodes']=[3]
        with self.assertRaises(ValueError): attach_collision(mod,room)
        self.assertTrue(attach_collision(mod,room,mapcode_translator=surface_mapcode))
    def test_decode_forwards_policy_and_default_rejects(self):
        import tempfile,struct
        from pathlib import Path
        from experimental.pikmin2_collision import decode_room,plane
        vertices=[[0,0,0],[0,0,10],[10,0,10]];tri=[0,2,1]
        grid=struct.pack('>I',3)+b''.join(struct.pack('>3f',*v) for v in vertices)+struct.pack('>I',1)
        grid+=struct.pack('>3I16f',*tri,*plane(vertices,tri),*([0]*12))
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            (path/'grid.bin').write_bytes(grid)
            (path/'mapcode.bin').write_bytes(struct.pack('>I',1)+bytes([9]))
            (path/'route.txt').write_text('0')
            with self.assertRaises(ValueError):decode_room(path)
            self.assertEqual(decode_room(path,mapcode_translator=surface_mapcode)['mapcodes'],[9])
    def test_nonmanifold_output_keeps_water_and_refuses_native_mod(self):
        import tempfile,json
        from pathlib import Path
        from unittest.mock import patch
        from experimental.pikmin2_surface_physics import convert_surface
        room=dict(vertices=[[0,0,0],[0,0,10],[10,0,10]],triangles=[[0,2,1]]*3,mapcodes=[3]*3,routes=[])
        with tempfile.TemporaryDirectory() as directory:
            src=Path(directory)/'source';(src/'texts').mkdir(parents=True)
            (src/'surface-pocket.json').write_text(json.dumps(dict(schema=1,source_region='tutorial',return_anchor=[1,0,1],landing_actors=[])))
            (src/'texts/waterbox.txt').write_text('0 { 3 20 -5 20 30 5 30 40 -5 40 50 5 50 60 -5 60 70 5 70 }')
            for name in ('grid.bin','mapcode.bin','route.txt'):(src/'texts'/name).write_bytes(b'source')
            (src/'surface-render.mod').write_bytes(b'source')
            out=Path(directory)/'out'
            with patch('experimental.pikmin2_surface_physics.decode_room',return_value=room):report=convert_surface(src,out)
            self.assertFalse(report['native_mod_written'])
            self.assertFalse(report['terrain_usable_alone'])
            self.assertEqual(report['mandatory_water_sidecar'],'surface-water.json')
            self.assertEqual(len(json.loads((out/'surface-water.json').read_text())['boxes']),3)
            self.assertFalse((out/'surface-terrain.mod').exists())
            self.assertEqual(json.loads((out/'surface-collision.json').read_text())['triangles'],room['triangles'])

if __name__ == '__main__': unittest.main()
