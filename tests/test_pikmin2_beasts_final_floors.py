from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experimental.pikmin2_beasts_final_floors import EXPECTED,POOLS,ROOMS,cargo_catalog,prepare,sha,source_manifest


def actor(key):
    name,count,placement,cargo=key
    return dict(enemy_id=name,minimum_count=count,placement_type=placement,carried_treasure=cargo,selection_weight=0,drop_mode=0)


def catalog():
    floors=[]
    for number in range(1,6):
        floors.append(dict(definition_index=number-1,first_floor=number,last_floor=number,
            parameters=dict(f007='1' if number==5 else '0',f010='1' if number==5 else '0',f008=POOLS.get(number,'earlier')),
            enemies=[actor(k) for k in EXPECTED.get(number,[])],
            treasures=[dict(treasure_id='dia_b_blue',source_weight=10,minimum_count=1,selection_weight=0)] if number==4 else [],
            gates=[],caps=[dict(empty=False,enemy=actor(k)) for k in [('TamagoMushi',1,1,None),('Egg',2,1,None)]] if number==4 else []))
    return dict(caves=[dict(cave_id='forest_1',floors=floors)],
        unit_pools={pool:dict(units=[dict(name=n,kind=1) for n in ROOMS[number]]) for number,pool in POOLS.items()},source_sha256={'source':sha(b'original')})


class FinalFloorsTests(unittest.TestCase):
    def test_equipment_catalog_is_separate_and_collision_rejected(self):
        merged=cargo_catalog({'dia_b_blue':{}},{'radar_a':{}})
        self.assertEqual(merged['radar_a'][1],'equipment')
        self.assertEqual(merged['dia_b_blue'][1],'treasure')
        with self.assertRaisesRegex(ValueError,'Ambiguous'):cargo_catalog({'radar_a':{}},{'radar_a':{}})

    def test_cargo_ownership_and_final_exit_preserved(self):
        result=source_manifest(catalog());four,five=result[3:]
        self.assertEqual([(c['treasure_id'],c['delivery']) for c in four['cargo']],
                         [('donutsichigo_s','enemy_carried'),('dia_b_blue','loose')])
        self.assertEqual(four['cargo'][0]['owner_definition_id'],'forest_1:definition3:enemy:0')
        self.assertIsNone(four['cargo'][1]['owner_definition_id'])
        self.assertEqual(five['cargo'][0]['owner_definition_id'],'forest_1:definition4:enemy:0')
        self.assertEqual(five['exit'],dict(destination_floor=None,geyser=True,clogged=True,placement=None,native_supported=False))
        self.assertEqual([a['definition_id'] for a in four['actors'][-2:]],
            ['forest_1:definition3:cap:0','forest_1:definition3:cap:1'])

    def test_source_drift_rejected(self):
        for mutation in ('owner','cap','weight','pool','room','geyser','clog','cargo','gate','duplicate','missing','order'):
            c=catalog();f=c['caves'][0]['floors'][3]
            if mutation=='owner':f['enemies'][0]['carried_treasure']=None
            elif mutation=='cap':f['caps'].pop()
            elif mutation=='weight':f['enemies'][1]['selection_weight']=1
            elif mutation=='pool':f['parameters']['f008']='wrong'
            elif mutation=='room':c['unit_pools'][POOLS[4]]['units'].pop()
            elif mutation=='geyser':f['parameters']['f007']='1'
            elif mutation=='clog':c['caves'][0]['floors'][4]['parameters']['f010']='0'
            elif mutation=='cargo':f['treasures'].pop()
            elif mutation=='gate':f['gates'].append({})
            elif mutation=='duplicate':c['caves'].append(deepcopy(c['caves'][0]))
            elif mutation=='missing':c['caves'][0]['floors'].pop()
            else:f['enemies'].reverse()
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):source_manifest(c)

    def test_coverage_does_not_collapse_repeated_source_rows(self):
        c=catalog();row=actor(('UjiA',2,0,None));c['caves'][0]['floors'][0]['enemies']=[row,row,row]
        result=source_manifest(c)
        self.assertEqual(len({a['definition_id'] for a in result[0]['actors']}),3)
        result[0]['actors'][0]['source']['minimum_count']=999
        self.assertEqual(c['caves'][0]['floors'][0]['enemies'][0]['minimum_count'],2)

    def test_bad_provenance_fails_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);raw=json.dumps(catalog()).encode();(root/'catalog.json').write_bytes(raw)
            (root/'disc').write_bytes(b'changed!')
            for mode in ('catalog','conflict','disc'):
                imported=dict(cave_id='forest_1',catalog_sha256=sha(raw),source_sha256={'source':sha(b'original')})
                if mode=='catalog':imported['catalog_sha256']='0'*64
                if mode=='conflict':imported['source_sha256']['source']='0'*64
                (root/'units.json').write_text(json.dumps(imported))
                with self.subTest(mode=mode),patch('experimental.pikmin2_beasts_final_floors.disc_files',return_value={'source':(0,8)}),self.assertRaisesRegex(ValueError,'provenance'):
                    prepare(root/'disc',root/'catalog.json',root,root/'out')
                self.assertFalse((root/'out').exists())
