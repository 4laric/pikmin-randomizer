import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experimental.pikmin2_beasts_floor4_violet import IDENTITY,GENERATOR,generation_context,prepare,sha
from experimental.pikmin2_beasts_floor2 import generation_context as floor2_context


class Floor4VioletTests(unittest.TestCase):
    def test_late_floor_does_not_reuse_floor2_suppression(self):
        for count in (0,19,20,21,2147483647):
            with self.subTest(count=count):
                result=generation_context(count)
                self.assertEqual(result['spawned_generators'],[GENERATOR])
                self.assertEqual(result['conversion_budgets'],{IDENTITY:5})
                self.assertFalse(result['suppression_applies'])
        self.assertEqual(floor2_context(20)['spawned_generators'],[])
        for value in (None,True,-1,20.0,'20',2147483648):
            with self.subTest(value=value),self.assertRaises(ValueError):generation_context(value)

    def fixture(self,root):
        unit=root/'units/units/room';unit.mkdir(parents=True)
        local=dict(spawns=[dict(type=8,position=[10,0,20],angle=175)])
        local_raw=json.dumps(local).encode();(unit/'collision.json').write_bytes(local_raw)
        catalog=root/'catalog.json';catalog.write_bytes(b'{}')
        imported=dict(cave_id='forest_1',catalog_sha256=sha(b'{}'),source_sha256={},
            units={'room':dict(output_sha256={'collision.json':sha(local_raw)})})
        imported_raw=json.dumps(imported).encode();(root/'units/units.json').write_bytes(imported_raw)
        assembly=root/'assembly';assembly.mkdir();(assembly/'collision.json').write_bytes(b'{"vertices":[],"triangles":[]}')
        report=dict(policy='P2_BEASTS_FLOOR4_ASSEMBLY_1',floor=4,catalog_sha256=sha(b'{}'),import_sha256=sha(imported_raw),
            layout=[['room',1,[100,0,200]]],output_sha256={'collision.json':sha((assembly/'collision.json').read_bytes())})
        (assembly/'assembly.json').write_text(json.dumps(report))
        (root/'iso').write_bytes(b'archive')
        return catalog,assembly

    def test_source_slot_transform_grounding_and_rejections(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);catalog,assembly=self.fixture(root)
            with patch('experimental.pikmin2_beasts_floor4_violet.source_manifest',return_value=[{}, {}, {}, {'source_definition':{}}]), \
                 patch('experimental.pikmin2_beasts_floor4_violet.disc_files',return_value={'enemy/parm/enemyParms.szs':(0,7)}), \
                 patch('experimental.pikmin2_beasts_floor4_violet.archive_files',return_value={'pom/enemyparm.txt':b'params'}), \
                 patch('experimental.pikmin2_beasts_floor4_violet.proper_slots',return_value=5), \
                 patch('experimental.pikmin2_beasts_floor4_violet.ground_height',return_value=2):
                # Catalog needs source hashes; production source parser is separately covered.
                raw=b'{"source_sha256":{}}';catalog.write_bytes(raw)
                imported=json.loads((root/'units/units.json').read_bytes());imported['catalog_sha256']=sha(raw)
                iraw=json.dumps(imported).encode();(root/'units/units.json').write_bytes(iraw)
                report=json.loads((assembly/'assembly.json').read_bytes());report.update(catalog_sha256=sha(raw),import_sha256=sha(iraw))
                (assembly/'assembly.json').write_text(json.dumps(report))
                result=prepare(root/'iso',catalog,root/'units',assembly,root/'out',20,(0,0))
                self.assertEqual(result['flower']['transformed_position'],[80,0,210])
                self.assertEqual(result['flower']['position'],[80,2,210])
                self.assertEqual(result['flower']['yaw'],265)
                for selected in ((1,0),(0,1),(True,0),(-1,0)):
                    with self.subTest(selected=selected),self.assertRaises(ValueError):
                        prepare(root/'iso',catalog,root/'units',assembly,root/'bad',20,selected)
                (assembly/'collision.json').write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'Assembly input changed'):
                    prepare(root/'iso',catalog,root/'units',assembly,root/'bad',20,(0,0))
