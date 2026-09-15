import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experimental.pikmin2_beasts_floor3 import POOL, ROOMS, TREASURES, checked_rooms, economy, prepare, sha, source_floor


def catalog():
    return dict(caves=[dict(cave_id='forest_1', floors=[dict(definition_index=2, first_floor=3, last_floor=3,
        parameters=dict(f008=POOL, f007='0', f010='0'),
        enemies=[dict(enemy_id=n, minimum_count=c, placement_type=t) for n,c,t in [('Hiba',7,1),('Hiba',7,8),('HikariKinoko',8,6)]],
        treasures=[dict(treasure_id=t, source_weight=10, minimum_count=1, selection_weight=0) for t in TREASURES], gates=[], caps=[])])],
        unit_pools={POOL: dict(units=[dict(name=n, kind=1) for n in ROOMS])})


class FloorThreeTests(unittest.TestCase):
    def test_source_preserves_distinct_hazard_rows(self):
        floor = source_floor(catalog())
        self.assertEqual([r['placement_type'] for r in floor['enemies']], [1,8,6])
        for mutation in ('count','kind','cargo','weight','carried','geyser','pool','duplicate','rooms','gate','cap'):
            c=catalog(); f=c['caves'][0]['floors'][0]
            if mutation=='count': f['enemies'][0]['minimum_count']=6
            elif mutation=='kind': f['enemies'][1]['placement_type']=1
            elif mutation=='cargo': f['treasures'].pop()
            elif mutation=='weight': f['enemies'][0]['selection_weight']=1
            elif mutation=='carried': f['enemies'][0]['carried_treasure']='x'
            elif mutation=='geyser': f['parameters']['f007']='1'
            elif mutation=='pool': f['parameters']['f008']='other'
            elif mutation=='duplicate': c['caves'].append(copy.deepcopy(c['caves'][0]))
            elif mutation=='rooms': c['unit_pools'][POOL]['units'].pop()
            elif mutation=='gate': f['gates'].append({})
            else: f['caps'].append({})
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): source_floor(c)

    def test_economy_rejects_impossible_carry_settings(self):
        self.assertEqual(economy(dict(money='100',min='5',max='10')), dict(value=100,weight=5,slots=10))
        for money,minimum,maximum in [('0','5','10'),('10','0','10'),('10','11','10'),('10','1','101'),('x','1','10')]:
            with self.subTest(values=(money,minimum,maximum)), self.assertRaises(ValueError):
                economy(dict(money=money,min=minimum,max=maximum))

    def test_checked_room_hashes_and_source_graph_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); raw=json.dumps(catalog()).encode()
            room=dict(vertices=[[-10,0,-10],[10,0,-10],[10,0,10]],triangles=[[0,1,2]],routes=[],
                      spawns=[dict(type=8,position=[0,0,0]),dict(type=1,position=[100,0,100])])
            files={'render.mod':b'model','room.mod':b'collision','room.ini':b'routes','collision.json':json.dumps(room).encode()}
            metadata=dict(cave_id='forest_1',catalog_sha256=sha(raw),units={})
            for name in ROOMS:
                directory=root/'units'/name;directory.mkdir(parents=True)
                for name_file,data in files.items(): (directory/name_file).write_bytes(data)
                metadata['units'][name]=dict(definition=dict(name=name,kind=1),assembly_ready=True,
                    route_audit=[dict(destination=1,unreachable_sources=[0])],output_sha256={n:sha(d) for n,d in files.items()})
            manifest=root/'units.json'; manifest.write_text(json.dumps(metadata))
            with patch('experimental.pikmin2_beasts_floor3.attach_collision',return_value=b'capped'):
                imported, checked=checked_rooms(root,raw)
                self.assertEqual(imported['units'][ROOMS[0]]['route_audit'][0]['unreachable_sources'],[0])
                self.assertTrue(checked[ROOMS[0]]['probes'][0]['grounded'])
                self.assertIsNone(checked[ROOMS[0]]['probes'][1]['ground'])
            for field,value in [('assembly_ready',False),('definition',{})]:
                bad=copy.deepcopy(metadata);bad['units'][ROOMS[0]][field]=value;manifest.write_text(json.dumps(bad))
                with self.subTest(field=field),self.assertRaises(ValueError): checked_rooms(root,raw)
            manifest.write_text(json.dumps(metadata))
            (root/'units'/ROOMS[0]/'render.mod').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'hash mismatch'): checked_rooms(root,raw)

    def test_invalid_source_fails_before_output_or_disc_access(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); c=catalog();c['caves']=[]
            path=root/'catalog.json';path.write_text(json.dumps(c))
            with self.assertRaises(ValueError):prepare(root/'missing.iso',path,root,root/'out')
            self.assertFalse((root/'out').exists())

    def test_changed_disc_and_conflicting_source_hashes_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);c=catalog();c['source_sha256']={'source':sha(b'original')}
            path=root/'catalog.json';path.write_text(json.dumps(c));disc=root/'disc';disc.write_bytes(b'changed')
            for unit_hash in (sha(b'original'),sha(b'other')):
                with self.subTest(unit_hash=unit_hash), \
                     patch('experimental.pikmin2_beasts_floor3.checked_rooms',return_value=({'source_sha256':{'source':unit_hash}},{})), \
                     patch('experimental.pikmin2_beasts_floor3.disc_files',return_value={'source':(0,7)}), \
                     self.assertRaisesRegex(ValueError,'provenance'):
                    prepare(disc,path,root,root/'out')
                self.assertFalse((root/'out').exists())


if __name__ == '__main__': unittest.main()
