import json
import tempfile
import unittest
from pathlib import Path

from experimental.pikmin2_cave_growth import (CHOKE, EXCLUDED, LEAF, SEGMENT, build_table,
                                              format_log, grow_floor, load_pool, partition_pool,
                                              reroll_differs, run)


def unit(name,kind,directions):
    return dict(name=name,cells=[1,1],kind=kind,flags=[0,0],
                doors=[dict(id=index,direction=direction,offset=0,waypoint=0,links=[])
                       for index,direction in enumerate(directions)])


def pool():
    return [unit('way2',2,[0,2]),unit('wayl',2,[2,3]),unit('room_a',1,[0,1,2,3]),
            unit('room_b',1,[0,2]),unit('cap',0,[2]),unit('boss',1,[])]


def catalog():
    floor=dict(first_floor=1,last_floor=1,parameters={'f008':'pool'})
    return dict(schema=1,caves=[dict(cave_id='test',floor_count=1,floors=[floor])],
                unit_pools={'pool':dict(units=pool())})


class PartitionTests(unittest.TestCase):
    def test_partition_classes(self):
        result=partition_pool(pool(),{'wayl':'water'})
        self.assertEqual(result['segments'],['room_a','room_b','way2'])
        self.assertEqual(result['chokes'],['wayl'])
        self.assertEqual(result['leaves'],['cap'])
        self.assertEqual(result['excluded'],['boss'])
        self.assertEqual(result['choke_hazards'],['water'])
        self.assertEqual(result['slot']['way2'],SEGMENT)
        self.assertEqual(result['slot']['wayl'],CHOKE)
        self.assertEqual(result['slot']['cap'],LEAF)
        self.assertEqual(result['slot']['boss'],EXCLUDED)

    def test_hazard_does_not_promote_a_leaf(self):
        result=partition_pool(pool(),{'cap':'water'})
        self.assertEqual(result['slot']['cap'],LEAF)
        self.assertEqual(result['chokes'],[])
        self.assertEqual(result['hazard']['cap'],'water')

    def test_zero_doors_is_never_a_segment(self):
        result=partition_pool(pool())
        self.assertNotIn('boss',result['segments'])


class TableTests(unittest.TestCase):
    def test_explicit_chokes_are_the_provider_table(self):
        result=partition_pool(pool(),{'wayl':'water','way2':'elec'})
        table=build_table(7,'test',1,result,['elec'])
        self.assertEqual(table['chokes'],['elec'])
        self.assertEqual(build_table(7,'test',1,result,['elec']),table)

    def test_same_seed_same_table_and_seed_changes_it(self):
        result=partition_pool(pool(),{'wayl':'water','way2':'elec'})
        self.assertEqual(build_table(3,'test',1,result),build_table(3,'test',1,result))
        tables={tuple(build_table(seed,'test',1,result)['chokes']) for seed in range(24)}
        self.assertGreater(len(tables),1)
        with self.assertRaises(ValueError):build_table(3,'test',1,result,['poison'])


class GrowthTests(unittest.TestCase):
    def test_forced_choke_is_on_every_path(self):
        units=pool();result=partition_pool(units,{'wayl':'water'})
        table=build_table(11,'test',1,result,['water'])
        layout=grow_floor(table,units,result)
        self.assertEqual(layout['status'],'ok')
        self.assertEqual(layout['path_check']['choke_count'],1)
        self.assertTrue(all(row['on_every_path'] for row in layout['path_check']['details']))
        self.assertEqual(layout['path_check']['details'][0]['unit'],'wayl')

    def test_multi_choke_chain_has_each_choke_as_a_cut(self):
        units=pool()+[unit('wayx',2,[0,2])]
        result=partition_pool(units,{'wayl':'water','wayx':'elec'})
        table=build_table(5,'test',1,result,['water','elec'])
        layout=grow_floor(table,units,result)
        self.assertEqual(layout['status'],'ok')
        self.assertEqual(layout['path_check']['choke_count'],2)
        self.assertTrue(all(row['on_every_path'] for row in layout['path_check']['details']))

    def test_retry_reports_failure_when_no_room_can_host_the_hole(self):
        units=[unit('way2',2,[0,2]),unit('wayl',2,[2,3])]
        result=partition_pool(units,{'wayl':'water'})
        table=build_table(1,'test',1,result,['water'])
        layout=grow_floor(table,units,result,max_attempts=8)
        self.assertEqual(layout['status'],'failed')
        self.assertEqual(layout['attempts'],8)

    def test_geometry_rerolls_but_table_is_fixed(self):
        units=pool();result=partition_pool(units,{'wayl':'water'})
        table=build_table(9,'test',1,result,['water'])
        signatures=set()
        for salt in range(6):
            layout=grow_floor(table,units,result,salt=salt)
            signatures.add(tuple((node['id'],node['unit'],node['rotation']) for node in layout['nodes']))
        self.assertGreater(len(signatures),1)
        self.assertEqual(grow_floor(table,units,result,salt=2)['table'],table)
        self.assertTrue(reroll_differs(table,units,result,0,6))

    def test_log_carries_the_generation_markers(self):
        units=pool();result=partition_pool(units,{'wayl':'water'})
        layout=grow_floor(build_table(2,'test',1,result,['water']),units,result)
        log=format_log(layout)
        self.assertIn('P2_CAVE_GROWTH',log)
        self.assertIn('P2_CAVE_GROWTH PASS',log)
        self.assertIn('on_every_path=true',log)


class RunTests(unittest.TestCase):
    def test_run_writes_model_growth_and_is_not_native_validated(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'catalog.json';path.write_text(json.dumps(catalog()))
            result,log=run(path,'test',1,42,salt=0,hazards={'wayl':'water'},chokes=['water'],
                           output=root/'out',verify_salts=4)
            self.assertEqual(result['generated'],'model');self.assertFalse(result['native_validated'])
            self.assertEqual(result['layout']['status'],'ok')
            self.assertTrue((root/'out/growth.json').exists());self.assertTrue((root/'out/growth.log').exists())
            self.assertIn('P2_CAVE_GROWTH PASS',log)
            with self.assertRaises(ValueError):load_pool(path,'test',2)


if __name__=='__main__':
    unittest.main()
