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
               'p2-cave-gates.txt','p2-cave-barriers.txt','p2-cave-floor.txt','p2-pod.txt','nectar.exe']
        for name in names:(run/name).write_text('synthetic input')
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


if __name__=='__main__':unittest.main()
