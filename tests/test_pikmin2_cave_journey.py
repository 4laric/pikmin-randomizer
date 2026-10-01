"""Synthetic boundary bytes test policy only, not compiled gameplay acceptance."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from randomizer.cave_floor import create as legacy, fingerprint, atomic_write
from randomizer.cave_journey import create, identity, encoded, Session, zero_buds, POLICY
from experimental.pikmin2_cave_lane41_generator import _seed_uint64


def placements(journey):
    return {n: dict(cave='forest_1',floor=n,seed=_seed_uint64(spec['descriptor']['table']['seed']),
                   items=[dict(slot_id='item:'+t['slot_id']+':0',host=t['slot_id'],item=t['treasure_id'])
                          for t in spec['descriptor']['table']['treasures']])
            for n,spec in enumerate(journey['floors'],1)}


class JourneyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.journey = create('1127')
        self.session = Session(Path(self.tmp.name)/'session',self.journey,placements(self.journey))
        self.state = self.session.initialize()

    def run_dir(self, state=None, name='source'):
        state = state or self.state
        run = self.session.directory/'runs'/name; run.mkdir(parents=True)
        entry = state['entry']
        (run/'cave.json').write_text(encoded(self.session.manifests[state['floor']]))
        (run/'layout.json').write_text('synthetic unit-test layout')
        (run/'nectar.exe').write_bytes(b'synthetic unit-test executable')
        (run/'p2-cave-entry.txt').write_text(f"P2_CAVE_ENTRY_1 {entry['fingerprint'][:32]} {state['floor']} {entry['health']} {len(entry['squad'])}\n"
            + ''.join(f'{s} {m}\n' for s,m in entry['squad']))
        self.session.begin(run,state)
        return run

    def transfer(self, run):
        # Smaller mixed/mature squad and damaged captain prevent starter-reset
        # assertions from passing merely because a default squad looks similar.
        manifest = self.session.manifests[1]
        (run/'p2-cave-transfer.txt').write_text(f'P2_CAVE_TRANSFER_1\n{fingerprint(manifest)[:32]}\n1 0.5 3\n1 2\n0 1\n2 0\n')
        (run/'p2-cave-bud-transfer.txt').write_text(zero_buds(manifest).replace('bud:0 0','bud:0 5'))
        p = self.session.placements[1]; item = p['items'][0]
        atomic_write(self.session.ledger_path(1),f"P2_RECEIPTS_1\n{p['seed']} treasure:forest_1:f1:{item['slot_id']} {item['host']} cave_treasure\n")

    def test_legacy_identity_and_new_floor_namespaces(self):
        self.assertEqual(fingerprint(legacy('930')), 'f4ac3b78b6ff81adbe0aad75398e35af9f89a49ad326a4bfaef646bf7078f54c')
        self.assertEqual(create('1127'),self.journey)
        self.assertNotEqual(identity(create('1127','Other')),identity(self.journey))
        one,two = self.session.manifests.values()
        self.assertNotEqual(one['table']['seed'],two['table']['seed'])
        self.assertNotEqual(fingerprint(one),fingerprint(two))
        self.assertTrue(all(':f2:' in b['slot_id'] for b in two['table']['buds']))

    def test_actual_protocol_transition_and_restart(self):
        run = self.run_dir(); self.transfer(run)
        state, changed = self.session.recover()
        self.assertTrue(changed)
        self.assertEqual((state['floor'],state['revision']),(2,1))
        self.assertEqual(state['entry']['squad'],[[1,2],[0,1],[2,0]])
        self.assertEqual(state['entry']['health'],0.5)
        self.assertIn('bud:0 5',state['boundary']['buds'])
        self.assertEqual(state['entry']['buds'],zero_buds(self.session.manifests[2]))
        self.assertIn('cave_treasure',self.session.ledger(1))
        self.assertEqual(self.session.ledger(2),'P2_RECEIPTS_1\n')
        restart = Session(self.session.directory,self.journey,self.session.placements)
        self.assertEqual(restart.initialize(),state)
        run2 = self.run_dir(state,'destination')
        self.assertEqual(self.session.recover(),(state,False))
        self.assertEqual(self.session.load()['floor'],2)

    def test_crash_before_and_after_atomic_commit_recovers_once(self):
        run = self.run_dir(); self.transfer(run)
        real = atomic_write
        def crash(path,text):
            if path == self.session.state_path:
                raise OSError('simulated before atomic commit')
            real(path,text)
        with patch('randomizer.cave_journey.atomic_write',side_effect=crash):
            with self.assertRaises(OSError): self.session.recover()
        self.assertEqual(self.session.load()['floor'],1)
        pending = self.session.pending_path.read_text()
        state,_ = self.session.recover()
        # Reproduce the crash between successful atomic replace and unlink.
        atomic_write(self.session.pending_path,pending)
        again, changed = self.session.recover()
        self.assertTrue(changed); self.assertEqual(again,state)
        self.assertFalse(self.session.pending_path.exists())

    def test_live_child_and_duplicate_begin_refused(self):
        run = self.run_dir(); self.transfer(run)
        with self.assertRaisesRegex(RuntimeError,'still running'):
            self.session.recover([run/'nectar.exe'])
        with self.assertRaisesRegex(RuntimeError,'pending'):
            self.session.begin(run,self.state)
        self.assertEqual(self.session.load()['floor'],1)

    def test_foreign_bad_and_failed_transfers_never_reset(self):
        run = self.run_dir(); self.transfer(run)
        original = (run/'p2-cave-transfer.txt').read_text()
        for text in (original.replace('1 0.5 3','2 0.5 3'),original.replace('0.5','nan'),
                     original.replace('0.5','0'),original.replace('0.5 3','0.5 0'),
                     original.replace('1 2\n','4 2\n'),original.replace(fingerprint(self.session.manifests[1])[:32],'0'*32),
                     original+'0 0\n'):
            (run/'p2-cave-transfer.txt').write_text(text)
            with self.assertRaises(ValueError): self.session.recover()
            self.assertEqual(self.session.load()['floor'],1)
        (run/'p2-cave-transfer.txt').write_text(original)

    def test_missing_ledger_and_cross_floor_alias_refused(self):
        run = self.run_dir(); self.transfer(run)
        self.session.ledger_path(2).unlink()
        with self.assertRaisesRegex(ValueError,'missing durable'):
            self.session.recover()
        self.assertFalse(self.session.ledger_path(2).exists())
        aliased = copy.deepcopy(self.session.placements); aliased[2] = aliased[1]
        with self.assertRaisesRegex(ValueError,'placement identity'):
            Session(self.session.directory,self.journey,aliased)

    def test_state_pending_input_and_incomplete_boundary_refused(self):
        run = self.run_dir()
        pending = self.session.pending_path.read_text()
        (run/'p2-cave-entry.txt').write_text('tampered')
        with self.assertRaisesRegex(ValueError,'input changed'): self.session.recover()
        p = json.loads(pending); p['revision'] = True
        atomic_write(self.session.pending_path,encoded(p))
        with self.assertRaisesRegex(ValueError,'foreign pending'): self.session.recover()
        atomic_write(self.session.pending_path,pending)
        self.session.state_path.write_text('{"schema":1,"schema":1}')
        with self.assertRaisesRegex(ValueError,'duplicate JSON'): self.session.load()

    def test_committed_boundary_tampering_refused(self):
        run = self.run_dir(); self.transfer(run); self.session.recover()
        state = self.session.state_path.read_text()
        value = json.loads(state); value['entry']['squad'] = [[1,0]]*20
        atomic_write(self.session.state_path,encoded(value))
        with self.assertRaisesRegex(ValueError,'incoming squad'): self.session.load()
        atomic_write(self.session.state_path,state)
        (run/'p2-cave-transfer.txt').write_text('changed source')
        with self.assertRaises(ValueError): self.session.load()

    def test_incomplete_native_boundary_refused(self):
        run = self.run_dir()
        (run/'p2-cave-bud-transfer.txt').write_text(zero_buds(self.session.manifests[1]))
        with self.assertRaisesRegex(ValueError,'incomplete native boundary'):
            self.session.recover()
        self.assertTrue(self.session.pending_path.exists())
        self.assertEqual(self.session.load()['floor'],1)

    def test_package_hash_descriptor_and_duplicate_json_refused(self):
        from scripts.play_pikmin2_cave_journey import package_inputs
        package = Path(self.tmp.name)/'package'; package.mkdir()
        (package/'journey.json').write_text(encoded(self.journey))
        for name in ('nectar.exe','cave-generator.exe'):
            (package/name).write_bytes(b'synthetic unit-test input')
        blueprints, files = {}, {}
        names = ('cave.json','layout.json','render.mod','collision.json',
                 'assets/dataDir/courses/pikmin2room/room.mod')
        for n in (1,2):
            floor = package/f'floor-{n}'
            for name in (*names,'p2-cave-items.txt'):
                p = floor/name; p.parent.mkdir(parents=True,exist_ok=True)
                p.write_text(encoded(self.session.manifests[n]) if name=='cave.json' else 'synthetic unit-test input')
                files[p.relative_to(package).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
            blueprints[str(n)] = {name:files[(floor/name).relative_to(package).as_posix()] for name in names}
        for name in ('journey.json','nectar.exe','cave-generator.exe'):
            files[name] = hashlib.sha256((package/name).read_bytes()).hexdigest()
        meta = dict(schema=3,policy=POLICY,files=files,blueprints=blueprints,fingerprint=identity(self.journey))
        path = package/'package.json'; path.write_text(encoded(meta))
        package_inputs(package)
        (package/'nectar.exe').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'input changed'): package_inputs(package)
        (package/'nectar.exe').write_bytes(b'synthetic unit-test input')
        bad = copy.deepcopy(meta); bad['files']['../escape'] = '0'*64
        path.write_text(encoded(bad))
        with self.assertRaises(ValueError): package_inputs(package)
        path.write_text('{"schema":3,"schema":3}')
        with self.assertRaisesRegex(ValueError,'duplicate JSON'): package_inputs(package)


if __name__ == '__main__':
    unittest.main()
