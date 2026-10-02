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

    def stage_run(self,state,name,receipt_copy=False):
        run=self.route.directory/'runs'/name/'run';run.mkdir(parents=True)
        (run/'input.txt').write_text('synthetic unit-test input')
        token='a'*32 if state['phase']=='surface' else fingerprint(self.route.manifests[int(state['phase'][-1])])[:32]
        inputs=['input.txt']
        if receipt_copy:
            (run/'p2-cave-item-receipts.txt').write_text(self.route.ledger(int(state['phase'][-1])))
            inputs.append('p2-cave-item-receipts.txt')
        self.route.begin(run,state,token,inputs)
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

    def test_controller_floor_inventory_duplicates_pin_once_and_recover(self):
        import hashlib
        from scripts.play_pikmin2_cave_route import floor_inputs,verify_copied_inputs
        self.stage_run(self.state,'inventory-enter');state,_=self.route.recover()
        run=self.route.directory/'runs'/'inventory-floor'/'run';run.mkdir(parents=True)
        required=['p2-cave-entry.txt','p2-cave-bud-entry.txt','p2-cave-item-receipts.txt',
                  'p2-cave-transition.txt','p2-cave-items.txt','p2-cave-rooms.txt',
                  'p2-cave-gates.txt','p2-cave-barriers.txt','p2-cave-floor.txt','p2-pod.txt','nectar.exe',
                  'assets/dataDir/stages/chal0.ini','assets/dataDir/stages/chal0/default.gen',
                  'assets/dataDir/courses/pikmin2room/room.ini','assets/dataDir/courses/pikmin2room/room.mod',
                  'assets/dataDir/courses/pikmin2room/pod.mod','assets/dataDir/courses/pikmin2room/treasure.mod',
                  'cave-generator.exe','synthetic.dll']
        for name in required:
            path=run/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(('synthetic policy input '+name).encode())
        digest=lambda name:hashlib.sha256((run/name).read_bytes()).hexdigest()
        pins={name:digest(name) for name in ('nectar.exe','cave-generator.exe','synthetic.dll')}
        pins.update({'floor-1/'+name:digest(name) for name in required if name.startswith('p2-')})
        # Exercise the actual controller inventory functions and concatenation.
        blueprints=['assets/dataDir/courses/pikmin2room/room.mod']
        inputs=floor_inputs(run)+blueprints+verify_copied_inputs(run,pins,'floor1',1)
        self.assertGreater(len(inputs),len(set(inputs)))
        self.assertGreater(inputs.count('nectar.exe'),1)
        self.assertGreater(inputs.count(blueprints[0]),1)
        self.assertGreater(inputs.count('p2-cave-floor.txt'),1)
        token=fingerprint(self.route.manifests[1])[:32]
        self.route.begin(run,state,token,inputs)
        pending=json.loads(self.route.pending_path.read_text())
        self.assertEqual(pending['inputs'],{name:digest(name) for name in set(inputs)})
        (run/'p2-cave-transfer.txt').write_text(f'P2_CAVE_TRANSFER_1 {token} 1 .5 2 1 2 0 1')
        (run/'p2-cave-bud-transfer.txt').write_text(zero_buds(self.route.manifests[1]))
        state,changed=self.route.recover();self.assertTrue(changed)
        self.assertEqual(state['boundary_proofs'][-1]['inputs'],pending['inputs'])
        self.assertEqual(self.route.recover(),(state,False))

    def test_controller_surface_duplicate_inputs_pin_once(self):
        import hashlib
        from scripts.play_pikmin2_cave_route import verify_copied_inputs
        run=self.route.directory/'runs'/'inventory-surface'/'run';run.mkdir(parents=True)
        (run/'nectar.exe').write_bytes(b'synthetic surface input')
        digest=hashlib.sha256((run/'nectar.exe').read_bytes()).hexdigest()
        inputs=['nectar.exe']+verify_copied_inputs(run,{'nectar.exe':digest},'surface')
        self.assertEqual(inputs,['nectar.exe','nectar.exe'])
        self.route.begin(run,self.state,'a'*32,inputs)
        self.assertEqual(json.loads(self.route.pending_path.read_text())['inputs'],{'nectar.exe':digest})

    def test_broken_pending_link_blocks_recover_begin_and_stop_without_publication(self):
        run=self.stage_run(self.state,'broken-pending')
        journal=self.route.pending_path.read_bytes()
        self.route.pending_path.unlink()
        target=Path(self.temp.name)/'missing-pending-target.json'
        try:self.route.pending_path.symlink_to(target)
        except OSError:self.skipTest('symlink creation unavailable')
        fresh=self.route.directory/'runs'/'blocked-relaunch'/'run';fresh.mkdir(parents=True)
        (fresh/'input.txt').write_text('synthetic replacement launch')
        before=self.route.state_path.read_bytes()
        ledgers={n:self.route.ledger_path(n).read_bytes() for n in self.route.manifests}
        import os
        link=os.readlink(self.route.pending_path)
        for action in (self.route.recover,
                       lambda:self.route.begin(fresh,self.state,'b'*32,['input.txt']),
                       self.route.stop_unsaved):
            with self.subTest(action=action),patch.object(cave_route,'atomic_write') as publish:
                with self.assertRaisesRegex(ValueError,'member link'):action()
                publish.assert_not_called()
            self.assertTrue(self.route.pending_path.is_symlink())
            self.assertEqual(os.readlink(self.route.pending_path),link)
            self.assertFalse(target.exists())
            self.assertEqual(self.route.state_path.read_bytes(),before)
            self.assertEqual({n:self.route.ledger_path(n).read_bytes() for n in self.route.manifests},ledgers)
            self.assertEqual(self.route.load(),self.state)
        # Removing the test link and restoring the original journal recovers the
        # original boundary once, proving refusal did not replace its run.
        self.route.pending_path.unlink();self.route.pending_path.write_bytes(journal)
        state,changed=self.route.recover();self.assertTrue(changed)
        self.assertEqual(state['last_boundary']['run'],str(run))
        self.assertEqual(self.route.recover(),(state,False))

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

    def test_original_input_is_retained_after_cleanup_and_later_commit(self):
        original=self.stage_run(self.state,'original-surface');state,_=self.route.recover()
        self.stage_run(state,'later-floor');state,_=self.route.recover()
        self.assertFalse(self.route.pending_path.exists())
        self.assertEqual(len(state['boundary_proofs']),2)
        (original/'input.txt').write_text('post-commit original input mutation')
        with patch('scripts.play_pikmin2_cave.checkpoint') as parser:
            with self.assertRaisesRegex(ValueError,'input changed'):self.route.load()
            parser.assert_not_called()
        with self.assertRaises(ValueError):self.route.recover()

    def test_missing_original_input_cannot_be_repaired_by_cleanup(self):
        run=self.stage_run(self.state,'original');state,_=self.route.recover()
        original_state=self.route.state_path.read_bytes()
        (run/'input.txt').unlink()
        with self.assertRaisesRegex(ValueError,'missing'):self.route.load()
        self.assertEqual(self.route.state_path.read_bytes(),original_state)
        self.assertFalse(self.route.pending_path.exists())

    def test_valid_changed_bud_budget_after_cleanup_refuses_before_parser(self):
        self.stage_run(self.state,'surface');state,_=self.route.recover()
        run=self.stage_run(state,'floor');state,_=self.route.recover()
        unchanged={path:path.read_bytes() for path in (self.route.state_path,self.route.ledger_path(1),self.route.ledger_path(2))}
        budget=run/'p2-cave-bud-transfer.txt'
        original=budget.read_text();self.assertIn('bud:0 0',original)
        budget.write_text(original.replace('bud:0 0','bud:0 5'))
        with patch('scripts.play_pikmin2_cave.checkpoint') as parser,patch.object(cave_route,'atomic_write') as publish:
            with self.assertRaisesRegex(ValueError,'boundary changed'):self.route.load()
            parser.assert_not_called();publish.assert_not_called()
        self.assertEqual({path:path.read_bytes() for path in unchanged},unchanged)

    def test_late_proof_tamper_precedes_all_earlier_floor_parsers(self):
        state=self.state
        for name in ('surface','floor1','floor2'):
            run=self.stage_run(state,name);state,_=self.route.recover()
        (run/'input.txt').write_text('late proof changed after all commits')
        with patch('scripts.play_pikmin2_cave.checkpoint') as parser:
            with self.assertRaisesRegex(ValueError,'input changed'):self.route.load()
            parser.assert_not_called()

    def test_original_bud_output_symlink_refuses_even_with_identical_bytes(self):
        self.stage_run(self.state,'surface');state,_=self.route.recover()
        run=self.stage_run(state,'floor');state,_=self.route.recover()
        budget=run/'p2-cave-bud-transfer.txt';outside=self.route.directory/'same-budget.txt'
        outside.write_bytes(budget.read_bytes());budget.unlink()
        try:budget.symlink_to(outside)
        except OSError as error:self.skipTest('symlink creation unavailable: '+str(error))
        with patch('scripts.play_pikmin2_cave.checkpoint') as parser:
            with self.assertRaisesRegex(ValueError,'link'):self.route.load()
            parser.assert_not_called()

    def test_foreign_proof_paths_and_symlinked_member_refuse(self):
        import copy
        run=self.stage_run(self.state,'surface');state,_=self.route.recover()
        for name in ('../input.txt','/input.txt','nested/../input.txt','nested\\input.txt','C:/input.txt'):
            bad=copy.deepcopy(state);bad['boundary_proofs'][0]['inputs']={name:'0'*64}
            self.route.state_path.write_text(json.dumps(bad))
            with self.assertRaisesRegex(ValueError,'foreign'):self.route.load()
        bad=copy.deepcopy(state);bad['boundary_proofs'][0]['run']=str(self.route.directory/'outside')
        self.route.state_path.write_text(json.dumps(bad))
        with self.assertRaisesRegex(ValueError,'foreign'):self.route.load()
        self.route.state_path.write_text(json.dumps(state))
        original=run/'input.txt';copy_file=self.route.directory/'same-input.txt';copy_file.write_bytes(original.read_bytes());original.unlink()
        try:original.symlink_to(copy_file)
        except OSError as error:self.skipTest('symlink creation unavailable: '+str(error))
        with self.assertRaisesRegex(ValueError,'link'):self.route.load()

    def test_run_directory_link_is_not_an_original_input_identity(self):
        run=self.stage_run(self.state,'surface');state,_=self.route.recover()
        container=run.parent;retained=self.route.directory/'retained';container.rename(retained)
        try:container.symlink_to(retained,target_is_directory=True)
        except OSError as error:self.skipTest('symlink creation unavailable: '+str(error))
        with self.assertRaisesRegex(ValueError,'link'):self.route.load()

    def test_invalid_new_budget_does_not_partially_publish_state_or_ledgers(self):
        self.stage_run(self.state,'surface');state,_=self.route.recover()
        run=self.stage_run(state,'floor')
        budget=run/'p2-cave-bud-transfer.txt';budget.write_text(budget.read_text().replace('bud:0 0','bud:0 6'))
        paths=(self.route.state_path,self.route.pending_path,self.route.ledger_path(1),self.route.ledger_path(2))
        before={path:path.read_bytes() for path in paths}
        with patch.object(cave_route,'atomic_write') as publish:
            with self.assertRaisesRegex(ValueError,'invalid bud budget'):self.route.recover()
            publish.assert_not_called()
        self.assertEqual({path:path.read_bytes() for path in paths},before)

    def test_history_without_proofs_is_immutable_and_not_promoted(self):
        state=dict(self.state);del state['boundary_proofs']
        self.route.state_path.write_text(json.dumps(state));before=self.route.state_path.read_bytes()
        with self.assertRaisesRegex(ValueError,'historical route lacks durable'):self.route.load()
        with self.assertRaisesRegex(ValueError,'historical route lacks durable'):self.route.initialize(self.state['surface'])
        self.assertEqual(self.route.state_path.read_bytes(),before)

    def test_proof_chain_survives_state_write_fault_and_reentry_once(self):
        run=self.stage_run(self.state,'surface');real=cave_route.atomic_write
        def crash(path,text):
            real(path,text)
            if path==self.route.state_path:raise OSError('after durable proof publication')
        with patch.object(cave_route,'atomic_write',side_effect=crash):
            with self.assertRaises(OSError):self.route.recover()
        state=self.route.load();self.assertEqual(state['boundary_proofs'][0]['inputs'],json.loads(self.route.pending_path.read_text())['inputs'])
        with patch.object(cave_route,'atomic_write') as publish:
            self.assertEqual(self.route.recover(),(state,False));self.assertEqual(self.route.recover(),(state,False));publish.assert_not_called()
        for name in ('floor1','floor2','reentry'):
            self.stage_run(state,name);state,changed=self.route.recover();self.assertTrue(changed)
        self.assertEqual(len(state['boundary_proofs']),4)
        with self.assertRaisesRegex(ValueError,'already consumed'):self.route.begin(run,state,'a'*32,['input.txt'])

    def test_live_receipt_ledger_can_advance_without_repinning_old_proof(self):
        self.stage_run(self.state,'surface');state,_=self.route.recover()
        run=self.stage_run(state,'floor',receipt_copy=True);state,_=self.route.recover()
        snapshot=state['boundary_proofs'][-1]['receipts'];placement=self.route.placements[1];item=placement['items'][0]
        reward='treasure:forest_1:f1:'+item['slot_id']
        self.route.ledger_path(1).write_text(snapshot+f"{placement['seed']} {reward} {item['host']} cave_treasure\n")
        self.assertEqual(self.route.load(),state)
        self.assertEqual(state['boundary_proofs'][-1]['receipts'],snapshot)
        (run/'p2-cave-item-receipts.txt').write_text(self.route.ledger(1))
        with self.assertRaisesRegex(ValueError,'input changed'):self.route.load()


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
        with self.assertRaisesRegex(ValueError,'boundary changed'):self.route.load()

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

    def test_original_acquisition_input_proof_survives_floor_exit_and_reentry(self):
        state=self.state
        self.boundary(state,'enter',[[1,0]]*20);state,_=self.route.recover()
        original=self.boundary(state,'acquire',[[4,1],[3,2],[1,0]]);state,_=self.route.recover()
        evidence=state['wfg_white_boundary']
        for name in ('descend','exit','reenter'):
            self.boundary(state,name,[[4,1],[3,2],[1,0]]);state,_=self.route.recover()
        self.assertEqual(state['wfg_white_boundary'],evidence)
        self.assertEqual(state['boundary_proofs'][1]['run'],str(original))
        (original/'input.txt').write_text('altered original WFG bank/profile proof input')
        with patch('scripts.play_pikmin2_cave.checkpoint') as parser:
            with self.assertRaisesRegex(ValueError,'input changed'):self.route.load()
            parser.assert_not_called()


if __name__=='__main__':unittest.main()
