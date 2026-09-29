import copy
import json
import unittest
from collections import Counter
from randomizer.seed import generate, validate, solo_rewards, spheres, fingerprint
from randomizer.catalog import active_names, can_reach_manifest, BLUE, YELLOW, FLARLIC, FOREST_ACCESS
from randomizer.cave_floor import NAMES, LOCATION_IDS, resolve
from pathlib import Path
import tempfile


class BoundedCaveTests(unittest.TestCase):
    def test_default_unchanged(self):
        self.assertEqual(generate('930'), generate('930', p2_cave_floor=False))
        self.assertNotIn('cave_requirements', generate('930'))

    def test_fill_and_stable_ids(self):
        for seed in range(30):
            m = generate(str(seed), p2_cave_floor=True)
            rewards = solo_rewards(m)
            self.assertEqual(len(rewards), len(active_names(m)))
            self.assertEqual(sum(map(len, spheres(rewards, m))), len(rewards))
            self.assertEqual({n: m['locations'][n] for n in NAMES}, LOCATION_IDS)
            self.assertEqual(m['p2_cave_floor'], resolve(str(seed), 'Player1'))

    def test_capacity_is_not_a_population_source(self):
        m = generate('930', p2_cave_floor=True)
        self.assertFalse(can_reach_manifest(NAMES[0], Counter({FLARLIC: 100}), m))
        self.assertTrue(can_reach_manifest(NAMES[0], Counter({BLUE: 1}), m))
        self.assertFalse(can_reach_manifest(NAMES[1], Counter({YELLOW: 1}), m))
        self.assertTrue(can_reach_manifest(NAMES[1], Counter({BLUE: 1, YELLOW: 1}), m))

    def test_area_gate(self):
        m = generate('930', p2_cave_floor=True, starting_area='navel')
        self.assertFalse(can_reach_manifest(NAMES[0], Counter({BLUE: 1}), m))
        self.assertTrue(can_reach_manifest(NAMES[0], Counter({BLUE: 1, FOREST_ACCESS: 1}), m))

    def test_incompatible_content_rejected(self):
        m = generate('930', p2_cave_floor=True)
        for mutate in (lambda m: m['p2_cave_floor']['table']['buds'].clear(),
                       lambda m: m['cave_requirements'].clear(),
                       lambda m: m['p2_cave_floor']['table'].update(seed='42'),
                       lambda m: m['locations'].update({NAMES[0]: 1})):
            bad = copy.deepcopy(m)
            mutate(bad)
            with self.assertRaises(ValueError):
                validate(bad)
        with self.assertRaises(ValueError):
            generate('x', p2_cave_floor=True, legacy_checks=True)

    def test_ap_unimplemented_delivery_rejected(self):
        with self.assertRaises(ValueError): generate('930', mode='ap', p2_cave_floor=True)
        m = generate('930', p2_cave_floor=True)
        restored = json.loads(json.dumps(m))
        validate(restored)
        self.assertEqual(fingerprint(m), fingerprint(restored))
        self.assertEqual(m['cave_requirements'], restored['cave_requirements'])

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

    def test_receipt_and_checkpoint_recovery(self):
        from scripts.play_pikmin2_cave import checkpoint,receipts,recover_pending
        from experimental.pikmin2_cave_lane41_generator import _seed_uint64
        m=generate('930',p2_cave_floor=True)
        seed=_seed_uint64(m['p2_cave_floor']['table']['seed'])
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
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp); run=session/'runs'/'abc';run.mkdir(parents=True)
            (run/'p2-cave-transfer.txt').write_text(transfer)
            (run/'p2-cave-bud-transfer.txt').write_text(buds)
            (session/'pending.json').write_text(json.dumps({'run':str(run),'fingerprint':fingerprint(m)}))
            with self.assertRaises(RuntimeError): recover_pending(session,m,placement,ledger,[run/'nectar.exe'])
            recover_pending(session,m,placement,ledger)
            self.assertEqual(json.loads((session/'checkpoint.json').read_text()),saved)
