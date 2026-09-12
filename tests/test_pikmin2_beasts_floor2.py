import copy
import struct
import tempfile
from pathlib import Path
import unittest
from experimental.pikmin2_beasts_floor2 import source_floor, flower_plan, decode_no_cargo, CARGO_FREE_CONFIG, POLICY, prepare


def catalog():
    return {'caves':[{'cave_id':'forest_1','floors':[dict(definition_index=1, first_floor=2, last_floor=2,
        parameters={'f008':'1_units_cent2_tsuchi.txt','f007':'0','f010':'0'},
        enemies=[{'enemy_id':name,'minimum_count':count,'placement_type':kind} for name,count,kind in
                 [('BlackPom',2,8),('HikariKinoko',6,6),('KareOoinu_s',2,6)]],
        treasures=[], gates=[], caps=[{'empty':False,'enemy':{'enemy_id':'Egg','minimum_count':2,'placement_type':1}}])]}]}


class FloorTwoTests(unittest.TestCase):
    def test_pod_input_rejected_before_stage_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'pod.mod').write_bytes(b'')
            with self.assertRaises(ValueError):prepare(root,root,root/'absent',root,root/'runs',pod=root)
            self.assertFalse((root/'runs').exists())

    def test_explicit_cargo_free_contract_and_version(self):
        self.assertEqual(CARGO_FREE_CONFIG,b'P2_CARGO_FREE_1\n')
        self.assertEqual(POLICY,'P2_BEASTS_FLOOR2_PREPARE_2')

    def test_source_rejects_hidden_cargo_weighted_and_changed_counts(self):
        self.assertFalse(source_floor(catalog())['treasures'])
        for mutation in ('cargo','count','weighted','cap'):
            c=catalog();f=c['caves'][0]['floors'][0]
            if mutation=='cargo':f['treasures']=[{'treasure_id':'borrowed'}]
            elif mutation=='count':f['enemies'][0]['minimum_count']=3
            elif mutation=='weighted':f['enemies'][0]['selection_weight']=1
            else:f['caps'][0]['enemy']['enemy_id']='UjiA'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):source_floor(c)

    def test_source_transforms_preserved_and_unmatched_ground_rejected(self):
        room={'vertices':[[-10,0,-10],[10,0,-10],[10,0,10],[-10,0,10]],
              'triangles':[[0,1,2],[0,2,3]],
              'spawns':[{'type':8,'position':[x,0,0],'angle':45,'radius':0,'min':1,'max':1} for x in (-2,2)]}
        plan=flower_plan(room)
        self.assertEqual([p['generator_id'] for p in plan],[62000,62001])
        self.assertEqual(plan[0]['position'],[-2,0,0]);self.assertEqual(plan[0]['yaw'],45)
        bad=copy.deepcopy(room);bad['spawns'][0]['position'][1]=1
        with self.assertRaises(ValueError):flower_plan(bad)

    def test_decoded_generator_prohibits_cargo_and_bad_proxy(self):
        entries=[]
        for label in ['preview red onion','preview ship']+['preview red pikmin']*20+['preview violet 0','preview violet 1']:
            e=bytearray(100);e[:8]=b'    0.0v';e[16:48]=label.encode().ljust(32,b'\0')
            if label.startswith('preview violet'):
                struct.pack_into('<I',e,8,62000+int(label[-1]));e[72:80]=b'ssob\x02\x00\x00\x00';struct.pack_into('>I',e,80,69)
            entries.append(e)
        header=b'1.0v'+struct.pack('>4fI',0,0,0,0,24)
        self.assertEqual(decode_no_cargo(header+b''.join(entries))['allowed_receipts'],[])
        entries[0][84:88]=b'50rp'
        with self.assertRaises(ValueError):decode_no_cargo(header+b''.join(entries))


if __name__=='__main__':unittest.main()
