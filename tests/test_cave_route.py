"""Synthetic transfer tests validate recovery policy, never gameplay acceptance."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from randomizer import cave_route
from randomizer.cave_journey import create,zero_buds
from randomizer.cave_floor import fingerprint
from tests.test_pikmin2_cave_journey import placements


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.journey=create('1154');self.route=cave_route.Route(Path(self.temp.name),self.journey,placements(self.journey),'source-receipt')
        self.state=self.route.initialize(dict(position=[220.,96.,1000.],health=1.,squad=[[1,0]]*20))

    def stage_run(self,state,name):
        run=self.route.directory/'runs'/name/'run';run.mkdir(parents=True)
        (run/'input.txt').write_text('synthetic unit-test input')
        token='a'*32 if state['phase']=='surface' else fingerprint(self.route.manifests[int(state['phase'][-1])])[:32]
        self.route.begin(run,state,token,['input.txt'])
        if state['phase']=='surface':
            party=state['surface'] if state['visit'] else dict(health=.75,squad=[[1,2],[0,1],[2,0]])
            (run/'p2-cave-surface-transfer.txt').write_text('P2_CAVE_ROUTE_TRANSFER_1 '+token+' -210 80 1160 '+str(party['health'])+' '+str(len(party['squad']))+' '+ ' '.join(str(x) for p in party['squad'] for x in p))
        else:
            n=int(state['phase'][-1]);(run/'p2-cave-transfer.txt').write_text(f'P2_CAVE_TRANSFER_1 {token} {n} .5 2 1 2 0 1')
            (run/'p2-cave-bud-transfer.txt').write_text(zero_buds(self.route.manifests[n]))
        return run

    def test_route_descent_exit_and_reentry_keep_survivors(self):
        for name,phase in [('enter','floor1'),('descend','floor2'),('exit','surface'),('reenter','floor1')]:
            self.stage_run(self.state,name);self.state,changed=self.route.recover()
            self.assertTrue(changed);self.assertEqual(self.state['phase'],phase)
            if name in ('descend','reenter'):
                self.assertEqual(self.state['entry']['squad'],[[1,2],[0,1]])
                self.assertEqual(self.state['entry']['health'],.5)
            if name=='exit':
                self.assertEqual(self.state['surface']['squad'],[[1,2],[0,1]])
                self.assertEqual(self.state['surface']['health'],.5)
        self.assertEqual(self.state['visit'],2);self.assertEqual(self.state['revision'],4)
        self.assertEqual(self.route.ledger(1),'P2_RECEIPTS_1\n')

    def test_mixed_surface_floor_return_keeps_wire2_after_last_white_lost(self):
        state=self.state
        for name in ('mixed-enter','mixed-descend','mixed-exit','mixed-reenter'):
            run=self.route.directory/'runs'/name/'run';run.mkdir(parents=True)
            (run/'input.txt').write_text('synthetic versioned boundary policy input')
            if state['phase']=='surface':
                token='a'*32
                party=state['surface'] if state['visit'] else dict(health=.75,squad=[[3,2],[4,1],[1,0]],wire_schema=2)
                wire='P2_CAVE_ROUTE_TRANSFER_2 '+token+' -210 80 1160 '+str(party['health'])+' '+str(len(party['squad']))+' '+ ' '.join(str(x) for row in party['squad'] for x in row)
                boundary='p2-cave-surface-transfer.txt'
            else:
                n=int(state['phase'][-1]);token=fingerprint(self.route.manifests[n])[:32]
                party=dict(health=.625,squad=[[3,2],[4,1],[1,0]]) if n==1 else dict(health=.5,squad=[[1,2]])
                wire=f'P2_CAVE_TRANSFER_2 {token} {n} '+str(party['health'])+' '+str(len(party['squad']))+' '+ ' '.join(str(x) for row in party['squad'] for x in row)
                boundary='p2-cave-transfer.txt';(run/'p2-cave-bud-transfer.txt').write_text(zero_buds(self.route.manifests[n]))
            self.route.begin(run,state,token,['input.txt']);(run/boundary).write_text(wire)
            state,changed=self.route.recover();self.assertTrue(changed)
            current=state['surface'] if state['phase']=='surface' else state['entry']
            self.assertEqual(current['wire_schema'],2)
            self.assertEqual(current['squad'],party['squad']);self.assertEqual(current['health'],party['health'])
            self.assertEqual(self.route.recover(),(state,False))
        self.assertEqual((state['phase'],state['revision'],state['visit']),('floor1',4,2))

    def test_native_wire1_purple_promotes_custom_surface2_and_reentry(self):
        self.stage_run(self.state,'enter-purple-test');state,_=self.route.recover()
        for name in ('purple-descend','purple-exit'):
            n=int(state['phase'][-1]);run=self.stage_run(state,name)
            token=fingerprint(self.route.manifests[n])[:32]
            (run/'p2-cave-transfer.txt').write_text(f'P2_CAVE_TRANSFER_1 {token} {n} .5 2 3 2 1 1')
            state,changed=self.route.recover();self.assertTrue(changed)
        self.assertEqual(state['surface'],dict(position=[-210.,80.,1160.],health=.5,squad=[[3,2],[1,1]],wire_schema=2))
        run=self.stage_run(state,'purple-reenter')
        wire=(run/'p2-cave-surface-transfer.txt').read_text().replace('P2_CAVE_ROUTE_TRANSFER_1','P2_CAVE_ROUTE_TRANSFER_2')
        (run/'p2-cave-surface-transfer.txt').write_text(wire)
        state,changed=self.route.recover();self.assertTrue(changed)
        self.assertEqual(state['entry']['squad'],[[3,2],[1,1]])
        self.assertEqual(state['entry']['wire_schema'],2)

    def test_crash_after_commit_before_pending_unlink_recovers_once(self):
        self.stage_run(self.state,'enter');real=cave_route.atomic_write
        def crash(path,text):
            real(path,text)
            if path==self.route.state_path:raise OSError('synthetic commit interruption')
        with patch.object(cave_route,'atomic_write',side_effect=crash):
            with self.assertRaises(OSError):self.route.recover()
        state,changed=self.route.recover();self.assertFalse(changed);self.assertEqual(state['revision'],1)
        self.assertEqual(self.route.recover(),(state,False))

    def test_live_child_and_input_change_do_not_commit(self):
        run=self.stage_run(self.state,'enter')
        with self.assertRaisesRegex(ValueError,'still live'):self.route.recover([run/'nectar.exe'])
        (run/'input.txt').write_text('changed')
        with self.assertRaisesRegex(ValueError,'input changed'):self.route.recover()
        self.assertEqual(self.route.load(),self.state)

    def test_foreign_boundary_and_second_launch_refuse(self):
        run=self.stage_run(self.state,'enter')
        (run/'p2-cave-surface-transfer.txt').write_text('P2_CAVE_ROUTE_TRANSFER_1 '+'b'*32+' 0 0 0 1 1 1 0')
        with self.assertRaisesRegex(ValueError,'foreign surface'):self.route.recover()
        with self.assertRaisesRegex(ValueError,'unresolved'):self.route.begin(run,self.state,'c'*32,['input.txt'])

    def test_saved_entry_and_retained_boundary_tampering_refuse(self):
        run=self.stage_run(self.state,'enter');state,_=self.route.recover()
        state['entry']['squad'][0][0]=0;self.route.state_path.write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError,'differs'):self.route.load()

    def test_interrupted_unsaved_child_cannot_reset_party(self):
        run=self.stage_run(self.state,'enter');(run/'p2-cave-surface-transfer.txt').unlink()
        (run/'run-result.json').write_text(json.dumps(dict(exit_code=86,captain_down=True,timed_out=False)))
        with self.assertRaisesRegex(ValueError,'without automatic'):self.route.stop_unsaved()
        self.assertTrue(self.route.pending_path.exists())

    def test_missing_state_never_recreates_starter(self):
        self.route.state_path.unlink()
        with self.assertRaisesRegex(ValueError,'reset'):self.route.initialize(dict(position=[0,0,0],health=1,squad=[[1,0]]*20))

    def test_invalid_surface_wire(self):
        for text in ['P2_CAVE_ROUTE_TRANSFER_1 a 0 0 0 nan 1 1 0','P2_CAVE_ROUTE_TRANSFER_1 a 0 0 0 1 1 5 0','P2_CAVE_ROUTE_TRANSFER_1 a 0 0 0 1 101']:
            with self.assertRaises(ValueError):cave_route.surface_transfer(text,'a')

    def test_floor_launch_requires_actual_semantic_sidecars(self):
        from scripts.play_pikmin2_cave_route import floor_inputs
        run=self.route.directory/'floor-inputs';run.mkdir()
        with self.assertRaisesRegex(ValueError,'p2-cave-entry'):floor_inputs(run)
        names=['p2-cave-entry.txt','p2-cave-bud-entry.txt','p2-cave-item-receipts.txt',
               'p2-cave-transition.txt','p2-cave-items.txt','p2-cave-rooms.txt',
               'p2-cave-gates.txt','p2-cave-barriers.txt','p2-cave-floor.txt','p2-pod.txt','nectar.exe',
               'assets/dataDir/stages/chal0.ini','assets/dataDir/stages/chal0/default.gen',
               'assets/dataDir/courses/pikmin2room/room.ini','assets/dataDir/courses/pikmin2room/room.mod',
               'assets/dataDir/courses/pikmin2room/pod.mod','assets/dataDir/courses/pikmin2room/treasure.mod']
        for name in names:
            (run/name).parent.mkdir(parents=True,exist_ok=True);(run/name).write_text('synthetic input')
        self.assertEqual(set(floor_inputs(run)),set(names))
        (run/'p2-cave-transition.txt').unlink()
        with self.assertRaisesRegex(ValueError,'transition'):floor_inputs(run)

    def test_checkpoint_semantic_input_change_refuses_recovery(self):
        self.stage_run(self.state,'enter');state,_=self.route.recover()
        run=self.route.directory/'runs/descend';run.mkdir(parents=True)
        (run/'p2-cave-bud-entry.txt').write_text('synthetic pinned budget')
        self.route.begin(run,state,fingerprint(self.route.manifests[1])[:32],['p2-cave-bud-entry.txt'])
        (run/'p2-cave-bud-entry.txt').write_text('changed budget')
        with self.assertRaisesRegex(ValueError,'input changed'):self.route.recover()


class WfgRouteTests(unittest.TestCase):
    def setUp(self):
        from randomizer.cave_journey import create_wfg_route
        from experimental.pikmin2_cave_lane41_generator import _seed_uint64
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.journey=create_wfg_route('1161')
        self.placements={i:dict(cave=spec['descriptor']['table']['cave_id'],
            floor=spec['descriptor']['table']['floor'],seed=_seed_uint64(spec['descriptor']['table']['seed']),
            items=[dict(slot_id='item:'+t['slot_id']+':0',host=t['slot_id'],item=t['treasure_id'])
                   for t in spec['descriptor']['table']['treasures']]) for i,spec in enumerate(self.journey['floors'])}
        self.route=cave_route.Route(self.temp.name,self.journey,self.placements,'source')
        self.state=self.route.initialize(dict(position=[0.,0.,0.],health=1.,squad=[[1,0]]*20))

    def boundary(self,state,name,squad):
        run=self.route.directory/'runs'/name;run.mkdir(parents=True)
        (run/'input.txt').write_text('synthetic policy evidence only')
        if state['phase']=='surface':
            token='a'*32;name='p2-cave-surface-transfer.txt'
            text=f'P2_CAVE_ROUTE_TRANSFER_2 {token} 0 0 0 .75 {len(squad)} '
        else:
            index=self.route.phase_indices[state['phase']];manifest=self.route.manifests[index]
            token=fingerprint(manifest)[:32];name='p2-cave-transfer.txt'
            text=f"P2_CAVE_TRANSFER_2 {token} {manifest['table']['floor']} .5 {len(squad)} "
            (run/'p2-cave-bud-transfer.txt').write_text(zero_buds(manifest).replace('bud:1 0','bud:1 5'))
        self.route.begin(run,state,token,['input.txt'])
        (run/name).write_text(text+' '.join(str(v) for row in squad for v in row))
        return run

    def test_four_phase_cycle_keeps_actual_party_and_white_evidence(self):
        state=self.state;party=[[1,0]]*20;evidence=None
        for name,phase in [('enter','acquisition'),('acquire','floor1'),('descend','floor2'),('exit','surface')]:
            if name=='acquire':party=[[3,2],[4,1],[1,0]]
            if name=='exit':party=[[3,2],[1,0]]
            self.boundary(state,name,party);state,changed=self.route.recover()
            self.assertTrue(changed);self.assertEqual(state['phase'],phase)
            target=state['surface'] if phase=='surface' else state['entry']
            self.assertEqual(target['squad'],party);self.assertEqual(target['wire_schema'],2)
            if name=='acquire':evidence=state['wfg_white_boundary'];self.assertIsNotNone(evidence)
            if evidence:self.assertEqual(state['wfg_white_boundary'],evidence)
            self.assertEqual(self.route.recover(),(state,False))
        self.assertEqual((state['revision'],state['visit']),(4,1))
        self.boundary(state,'reenter',party);state,_=self.route.recover()
        self.assertEqual((state['phase'],state['revision'],state['visit']),('acquisition',5,2))
        self.assertEqual(state['entry']['squad'],party)
        run=self.boundary(state,'later-carry-only',party)
        (run/'p2-cave-bud-transfer.txt').write_text(zero_buds(self.route.manifests[0]))
        state,_=self.route.recover();self.assertEqual(state['wfg_white_boundary'],evidence)
        (Path(evidence['run'])/'p2-cave-bud-transfer.txt').write_text('tampered')
        with self.assertRaisesRegex(ValueError,'White boundary changed'):self.route.load()

    def test_no_white_is_valid_boundary_without_acquisition_evidence(self):
        self.boundary(self.state,'enter',[[1,0]]*20);state,_=self.route.recover()
        self.boundary(state,'leave',[[1,2]]*19);state,_=self.route.recover()
        self.assertIsNone(state['wfg_white_boundary'])
        self.assertEqual(state['entry']['squad'],[[1,2]]*19)

    def test_incoming_white_without_spent_white_bud_is_carry_only(self):
        self.boundary(self.state,'enter',[[4,1],[1,0]]);state,_=self.route.recover()
        run=self.boundary(state,'carry-through',[[4,1],[1,0]])
        (run/'p2-cave-bud-transfer.txt').write_text(zero_buds(self.route.manifests[0]))
        state,changed=self.route.recover()
        self.assertTrue(changed);self.assertIsNone(state['wfg_white_boundary'])
        self.assertEqual(state['entry']['squad'],[[4,1],[1,0]])
        import hashlib
        state['wfg_white_boundary']=dict(run=str(run),
            sha256=hashlib.sha256((run/'p2-cave-transfer.txt').read_bytes()).hexdigest(),
            buds_sha256=hashlib.sha256((run/'p2-cave-bud-transfer.txt').read_bytes()).hexdigest())
        self.route.state_path.write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError,'lacks White acquisition'):self.route.load()

    def test_acquisition_commit_recovers_once_and_uses_actual_floor(self):
        self.boundary(self.state,'enter',[[1,0]]*20);state,_=self.route.recover()
        self.boundary(state,'acquire',[[4,2],[3,1]])
        real=cave_route.atomic_write
        def crash(path,text):
            real(path,text)
            if path==self.route.state_path:raise OSError('after durable write')
        with patch.object(cave_route,'atomic_write',side_effect=crash):
            with self.assertRaises(OSError):self.route.recover()
        state,changed=self.route.recover();self.assertFalse(changed)
        self.assertEqual((state['phase'],state['revision']),('floor1',2))
        self.assertEqual(state['entry']['squad'],[[4,2],[3,1]])
        bad=dict(self.placements);bad[0]=dict(bad[0],floor=0)
        with self.assertRaisesRegex(ValueError,'placement identity'):
            cave_route.Route(self.temp.name,self.journey,bad,'source')


if __name__=='__main__':unittest.main()
