"""Developer cave only: no released manifest, fill, campaign session, or AP imports."""
import copy
import json
import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch
from randomizer.cave_floor import create, validate, fingerprint, resolve, NAMES


def fixture_layout():
    """Synthetic graph for geometry unit tests; not native-generation evidence."""
    table = create('930')['table']
    nodes = [dict(id=row['slot_id'], kind='segment', segment_index=row['index'])
             for row in table['segments']]
    first, last = [row['id'] for row in nodes]
    choke = table['chokes'][0]['slot_id']
    nodes.append(dict(id=choke, kind='choke', hazard='water', segment_index=1))
    edges = [[first, choke], [choke, last]]
    for row in table['leaves']:
        nodes.append(dict(id=row['slot_id'], kind='leaf', hazard=row['hazard'],
                          segment_index=row['segment']))
        edges.append([[first, last][row['segment']], row['slot_id']])
    for row in table['buds']:
        nodes.append(dict(id=row['slot_id'], kind='bud',
                          hazard={'blue': 'water', 'yellow': 'elec'}[row['species']],
                          segment_index=row['segment']))
        edges.append([[first, last][row['segment']], row['slot_id']])
    return dict(schema='p2-cave-observed-layout/1', source='fixture', cave='forest_1',
                floor=1, seed=930, nodes=nodes, edges=edges, entrance=first, hole=last)


class BoundedCaveTests(unittest.TestCase):
    def test_deterministic_standalone_contract(self):
        for seed in range(30):
            descriptor = create(str(seed))
            self.assertEqual(descriptor['table'], resolve(str(seed), 'Player1')['table'])
            self.assertEqual(descriptor, validate(json.loads(json.dumps(descriptor))))
            self.assertEqual(fingerprint(descriptor), fingerprint(create(str(seed))))
            self.assertNotEqual(fingerprint(descriptor), fingerprint(create(str(seed), 'Other')))
        self.assertEqual(create('930')['required_colors'],
                         {'treasure_water': ['blue'], 'treasure_elec': ['yellow', 'blue']})

    def test_rejects_campaign_ap_and_tampered_descriptors(self):
        for mutation in (lambda d: d.update(mode='ap'),
                         lambda d: d.update(schema=9),
                         lambda d: d['table']['buds'].clear(),
                         lambda d: d['table'].update(floor=True),
                         lambda d: d['required_colors'].clear(),
                         lambda d: d['table'].update(seed='42')):
            descriptor = create('930')
            mutation(descriptor)
            with self.assertRaises(ValueError): validate(descriptor)
        for seed, slot in ((None, 'Player1'), ('', 'Player1'), ('930', ''), (930, 'Player1')):
            with self.assertRaises(ValueError): create(seed, slot)

    def test_real_geometry_and_route_water_cut(self):
        from scripts.stage_pikmin2_playable_cave import mesh
        from experimental.pikmin2_collision import ground_height
        tiles={(x,z) for x in range(-1,9) for z in range(-1,2)}
        with tempfile.TemporaryDirectory() as tmp:
            binary,routes=mesh(tiles,{(4,0)},Path(tmp))
            room=json.loads((Path(tmp)/'collision.json').read_text())
        self.assertTrue(binary)
        self.assertIn(b'point {',routes)
        self.assertTrue(any(code>>29==5 for code in room['mapcodes']))
        self.assertEqual(ground_height(room['vertices'],room['triangles'],400,0),0)
        self.assertIsNone(ground_height(room['vertices'],room['triangles'],400,200))

    def test_fresh_staging_is_required(self):
        from scripts.stage_pikmin2_playable_cave import stage
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            with self.assertRaisesRegex(ValueError, 'fresh private'):
                stage(create('930'), directory, directory, directory, directory, directory)

    def test_layout_water_is_an_unavoidable_route_cut(self):
        from scripts.stage_pikmin2_playable_cave import physical_layout
        from experimental.pikmin2_cave_rooms import logical_projection
        previous = None
        for salt in (0, 1, 2, 100000):
            rooms, tiles, water = physical_layout(fixture_layout(), salt)
            end = max(x for x,z in tiles)-1
            # Flood-fill all dry tiles from spawn: neither water treasure nor
            # far segment/electric treasure may be reached via a side route.
            reached, todo = set(), [(0,0)]
            while todo:
                p = todo.pop()
                if p in reached or p not in tiles or p in water: continue
                reached.add(p)
                x,z = p
                todo.extend(((x-1,z),(x+1,z),(x,z-1),(x,z+1)))
            self.assertIn((-1,1), reached)  # Blue conversion available before water.
            self.assertNotIn((0,-5), reached)
            self.assertNotIn((end,0), reached)
            self.assertNotIn((end,-5), reached)
            self.assertEqual(physical_layout(fixture_layout(), salt), (rooms,tiles,water))
            projection = logical_projection(rooms)
            if previous is not None: self.assertEqual(previous,projection)
            previous = projection

    def test_barrier_sidecar_covers_corridor_and_excludes_buds(self):
        from scripts.stage_pikmin2_playable_cave import barriers_text, physical_layout
        from experimental.pikmin2_cave_gates import build_gates
        rooms, _, _ = physical_layout(fixture_layout(), 0)
        lines = barriers_text(rooms).splitlines()
        self.assertEqual(lines[:4], ['P2_CAVE_BARRIERS_1', 'cave forest_1', 'floor 1', 'seed 930'])
        rows = {words[0]: list(map(float,words[1:])) for words in map(str.split,lines[5:])}
        expected = {door['id'] for door in build_gates(rooms)['doors'] if door['carry_block'] != 'none'}
        self.assertEqual(set(rows),expected)
        self.assertEqual(lines[4], 'barriers '+str(len(expected)))
        for unit in rooms['units']:
            if unit['id'] not in rows: continue
            xmin,ymin,zmin,xmax,ymax,zmax = rows[unit['id']]
            self.assertLess(ymin,0); self.assertGreaterEqual(ymax,130)
            if unit['kind']=='choke':
                self.assertLess(zmin,-50); self.assertGreater(zmax,50)
            else:
                self.assertLess(xmin,unit['gx']-50)
                self.assertGreater(xmax,unit['gx']+50)
            self.assertLess(xmin,xmax); self.assertLess(zmin,zmax)

    def test_capacity_uses_canonical_policy(self):
        from scripts.play_pikmin2_cave import runtime_capacity
        with patch('scripts.capacity_gate.measure',return_value=object()), \
             patch('scripts.capacity_gate.admit',return_value=(False,'occupied')):
            with self.assertRaisesRegex(RuntimeError,'CAPACITY_GATE: occupied'): runtime_capacity()

    def test_receipt_and_checkpoint_recovery(self):
        from scripts.play_pikmin2_cave import checkpoint,receipts,recover_pending
        from experimental.pikmin2_cave_lane41_generator import _seed_uint64
        m=create('930')
        seed=_seed_uint64(m['table']['seed'])
        placement={'seed':seed,'items':[{'slot_id':'item:forest_1:f1:leaf:0:0',
                    'host':'forest_1:f1:leaf:0','item':'treasure_water'}]}
        ledger=f'P2_RECEIPTS_1\n{seed} treasure:forest_1:f1:item:forest_1:f1:leaf:0:0 forest_1:f1:leaf:0 cave_treasure\n'
        buds=f'P2_CAVE_BUD_STATE_1\n{seed} forest_1 1 2\nforest_1:f1:bud:0 5\nforest_1:f1:bud:1 1\n'
        transfer=f'P2_CAVE_TRANSFER_1\n{fingerprint(m)[:32]}\n1 0.5 2\n0 2\n2 1\n'
        saved=checkpoint(transfer,buds,ledger,m,placement)
        self.assertEqual(saved['squad'],[[0,2],[2,1]])
        self.assertEqual(receipts(ledger,placement),[NAMES[0]])
        with self.assertRaises(ValueError): receipts(ledger+ledger.splitlines()[1]+'\n',placement)
        with self.assertRaises(ValueError): checkpoint(transfer,buds.replace('bud:0 5','bud:0 6'),ledger,m,placement)
        for corrupt in (transfer.replace('0.5','nan'), transfer.replace('0.5','0'),
                        transfer.replace('0 2\n','3 2\n'), transfer+'0 0\n',
                        transfer.replace(fingerprint(m)[:32], '0'*32)):
            with self.assertRaises(ValueError): checkpoint(corrupt,buds,ledger,m,placement)
        for corrupt in (ledger.replace('cave_treasure','enemy'),ledger.replace(str(seed),'1'),
                        ledger.replace('leaf:0:0','leaf:999:0')):
            with self.assertRaises(ValueError): receipts(corrupt,placement)
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp); run=session/'runs'/'abc';run.mkdir(parents=True)
            (run/'p2-cave-transfer.txt').write_text(transfer)
            (run/'p2-cave-bud-transfer.txt').write_text(buds)
            (session/'pending.json').write_text(json.dumps({'run':str(run),'fingerprint':fingerprint(m)}))
            with self.assertRaises(RuntimeError): recover_pending(session,m,placement,ledger,[run/'nectar.exe'])
            recover_pending(session,m,placement,ledger)
            self.assertEqual(json.loads((session/'checkpoint.json').read_text()),saved)
