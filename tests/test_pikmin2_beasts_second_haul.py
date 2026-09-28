import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from experimental import pikmin2_beasts_floor3_haul as haul


class SecondHaulTests(unittest.TestCase):
    def test_selected_source_slot_model_and_economy_are_bound(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            def write(path,value):
                path.parent.mkdir(parents=True,exist_ok=True)
                raw=json.dumps(value).encode();path.write_bytes(raw);return haul.sha(raw)
            catalog=root/'catalog.json';catalog_hash=write(catalog,{})
            units=root/'units';assembly=root/'assembly';package=root/'package'
            name='room_block1_3_hiba_tsuchi'
            local=dict(spawns=[{}, {},dict(type=2,position=[175,20.5,-55])])
            local_hash=write(units/'units'/name/'collision.json',local)
            imported=dict(catalog_sha256=catalog_hash,source_sha256={},
                units={name:dict(output_sha256={'collision.json':local_hash})})
            import_hash=write(units/'units.json',imported)
            room=dict(vertices=[],triangles=[],routes=[
                dict(id=6,position=[150,20.5,0],links=[0]),
                dict(id=0,position=[-85,0,-340],links=[])])
            room_hash=write(assembly/'collision.json',room)
            write(assembly/'assembly.json',dict(policy='P2_BEASTS_FLOOR3_ASSEMBLY_1',
                catalog_sha256=catalog_hash,import_sha256=import_hash,
                layout=[[name,0,[0,0,0]]],output_sha256={'collision.json':room_hash}))
            model=package/'treasures/donutswhite/treasure.mod'
            model.parent.mkdir(parents=True);model.write_bytes(b'model')
            config=dict(money='230',min='15',max='25')
            metadata=dict(catalog_sha256=catalog_hash,source_definition={},source_sha256={},
                treasures={'donutswhite':dict(instance_id='forest_1:floor3:treasure:donutswhite:0',
                    model_sha256=haul.sha(b'model'),source_config=config,value=230,weight=15,slots=25)})
            write(package/'floor3.json',metadata)
            iso=root/'disc';iso.write_bytes(b'config')
            with patch.object(haul,'source_floor',return_value={}), \
                 patch.object(haul,'ground_height',side_effect=lambda v,t,x,z:20.5 if x>0 else 0), \
                 patch.object(haul,'disc_files',return_value={'user/Abe/Pellet/us/otakara_config.txt':(0,6)}), \
                 patch.object(haul,'pellet_catalog',return_value={'donutswhite':config}):
                result=haul.prepare(iso,catalog,units,assembly,package,root/'result',treasure='donutswhite')
                self.assertEqual(result['cargo']['source_slot'],2)
                self.assertEqual(result['cargo']['source_row'],0)
                self.assertEqual(result['cargo']['position'],[175,20.5,-55])
                self.assertEqual(result['cargo']['value'],230)
                self.assertEqual(result['route']['waypoint_ids'],[6,0])
                self.assertFalse(result['campaign_reward_authorized'])
                model.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'model/identity'):
                    haul.prepare(iso,catalog,units,assembly,package,root/'bad',treasure='donutswhite')
                model.write_bytes(b'model');metadata['treasures']['donutswhite']['value']=150
                write(package/'floor3.json',metadata)
                with self.assertRaisesRegex(ValueError,'economy'):
                    haul.prepare(iso,catalog,units,assembly,package,root/'bad',treasure='donutswhite')
