"""Isolated development_streams contract; no builds, launches or consumer wakeups."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from workflow.development_streams import (bind_owner, canonical_receipt, configure, dispatch,
                                          manifest, observe_maintained_sources, receipt_references,
                                          retire_ready, status, submit_candidate, validate_sources)
from workflow.handoff import Rejected, digest
from workflow.registry import Registry

ROOT = 'a' * 40
NATIVE = 'b' * 40
ROOT2 = 'c' * 40
NATIVE2 = 'd' * 40
BASE = dict(root=ROOT, native=NATIVE)
MOVED = dict(root=ROOT2, native=NATIVE2)
BRANCH = 'codex/stream-actors-assets'


class DevelopmentStreamTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.db = self.root / 'output/workflow/registry.sqlite3'
        self.reg = Registry(self.db, self.root, clock=lambda: 1000.0, process_probe=lambda _: 'alive')
        self.reg.init()
        self.probe = {101: 'alive', 102: 'alive'}
        self.reg.probe = lambda process: self.probe.get(process.get('pid'), 'unknown')
        self.log = self.root / 'output/stream-evidence.md'
        self.log.write_text('stream-local candidate evidence\n')
        self.evidence = {'path': str(self.log), 'sha256': digest(self.log)}
        self.register_lane('stream-owner', issue=9001, level='implementation', pid=101)
        self.register_lane('integration-owner', issue=9002, level='integration ownership', pid=102)
        self.definition = dict(id='actors-assets', name='Actors and assets', scope='Actor/asset slices',
                               shared_hooks=['native/pc_port/pc_p2_actor_slots.h'],
                               maintained_base=BASE,
                               worktrees=dict(root=dict(path='output/development-streams/actors-assets/root',
                                                        branch=BRANCH),
                                              native=dict(path='output/development-streams/actors-assets/native',
                                                          branch=BRANCH)))

    def register_lane(self, lane, issue, level, pid):
        record = dict(lane=lane, owner='Codex through 4laric', worker_id='worker-' + lane,
                      task_id='task-' + lane, issue=issue, scope='Bounded tool slice',
                      target_level=level, state='ready', generation=1, revision=1,
                      process={'host': 'test', 'pid': pid, 'started': '1'},
                      next_action='Run checks', milestone='dev-streams',
                      owned_files=['output/' + lane + '.py'], acceptance=['Bounded'],
                      dependencies=[], created_at=1000.0, started_at=None, heartbeat_at=1000.0,
                      progress_at=1000.0, failure_streak=0, recovery_count=0)
        with self.reg.transaction() as state:
            state['lanes'][lane] = record
        return record

    def observe(self, base=None, dirty=' M file.cpp'):
        base = base or BASE
        return {kind: dict(repo='output/maintained-' + kind, ref='main', commit=base[kind], dirty=dirty)
                for kind in ('root', 'native')}

    def worktrees(self, exists=True, branch_ok=True, ancestor=True):
        return {kind: dict(exists=exists, is_git=exists, path='output/development-streams/actors-assets/' + kind,
                           branch=BRANCH if branch_ok else 'wrong', head='e' * 40,
                           ancestor_of_base=ancestor) for kind in ('root', 'native')}

    def bind(self, lane='stream-owner', generation=1, stream='actors-assets', **kwargs):
        return bind_owner(self.reg, stream, lane, generation, **kwargs)

    def candidate(self, cid='c1', base=None, state='ready', evidence=None):
        return dict(id=cid, title='Slice ' + cid, summary='Stream-local work',
                    references=['#859', 'existing-lane'], base=base or BASE,
                    commits=dict(root=['e' * 40], native=['f' * 40]),
                    state=state, evidence=evidence or self.evidence)

    def submit(self, cid='c1', base=None, state='ready', evidence=None, observed=None, worktrees=None,
               lane='stream-owner', generation=1, stream='actors-assets'):
        return submit_candidate(self.reg, stream, lane, generation, self.candidate(cid, base, state, evidence),
                               observed=observed or self.observe(), worktrees=worktrees or self.worktrees())

    def test_configure_reports_unstaffed_roles_without_fabricating_owners(self):
        entry = configure(self.reg, [self.definition])[0]
        self.assertEqual(entry['status'], 'awaiting-owner')
        report = status(self.reg)[0]
        self.assertIsNone(report['owner'])
        self.assertEqual(report['owner_state'], 'awaiting-controller-assignment')
        self.assertEqual(report['maintained_base'], BASE)
        self.assertEqual(report['worktrees']['native']['branch'], BRANCH)

    def test_configure_refuses_silent_maintained_base_move(self):
        configure(self.reg, [self.definition])
        moved = dict(self.definition, maintained_base=MOVED)
        with self.assertRaises(Rejected):
            configure(self.reg, [moved])
        entry = configure(self.reg, [moved], supersede=True)[0]
        self.assertEqual(entry['maintained_base'], MOVED)

    def test_stale_candidate_pins_fail_closed(self):
        configure(self.reg, [self.definition])
        self.bind()
        self.submit()
        with self.assertRaises(Rejected):
            self.submit('stale', base=MOVED)
        configure(self.reg, [dict(self.definition, maintained_base=MOVED)], supersede=True)
        report = status(self.reg)[0]
        self.assertIsNone(report['ready_batch'])
        self.assertEqual(report['stale_candidates'], ['c1'])

    def test_external_maintained_head_movement_fails_closed(self):
        configure(self.reg, [self.definition])
        self.bind()
        self.submit(observed=self.observe())
        with self.assertRaises(Rejected):
            self.submit('c2', observed=self.observe(MOVED))
        with self.assertRaises(Rejected):
            validate_sources(self.reg, 'actors-assets', observed=self.observe(MOVED),
                             worktrees=self.worktrees())
        validate_sources(self.reg, 'actors-assets', observed=self.observe(BASE), worktrees=self.worktrees())
        configure(self.reg, [dict(self.definition, maintained_base=MOVED)], supersede=True)
        validate_sources(self.reg, 'actors-assets', observed=self.observe(MOVED), worktrees=self.worktrees())
        self.submit('c3', base=MOVED, observed=self.observe(MOVED))

    def test_second_ready_batch_is_rejected_but_draft_allowed(self):
        configure(self.reg, [self.definition])
        self.bind()
        self.submit('c1')
        self.assertEqual(status(self.reg)[0]['ready_batch'], 'c1')
        with self.assertRaises(Rejected):
            self.submit('c2')
        self.submit('c2', state='draft')
        self.assertEqual(status(self.reg)[0]['ready_batch'], 'c1')

    def test_candidate_id_is_immutable(self):
        configure(self.reg, [self.definition])
        self.bind()
        self.submit('c1')
        with self.assertRaises(Rejected):
            self.submit('c1', state='draft')
        self.assertEqual(status(self.reg)[0]['ready_batch'], 'c1')
        retire_ready(self.reg, 'actors-assets', 'c1', 'stream-owner', 1, reason='Abandoned for a smaller slice')
        with self.assertRaises(Rejected):
            self.submit('c1')
        self.assertEqual(status(self.reg)[0]['closed_candidates'], ['c1'])

    def test_old_generation_submission_is_rejected_after_rebind(self):
        configure(self.reg, [self.definition])
        self.bind()
        with self.reg.transaction() as state:
            state['lanes']['stream-owner']['generation'] = 2
        self.bind(generation=2, replace=True)
        with self.assertRaises(Rejected):
            self.submit('old', generation=1)
        self.submit('new', generation=2)
        self.assertEqual(status(self.reg)[0]['ready_batch'], 'new')

    def test_submission_requires_live_owner_at_binding_generation(self):
        configure(self.reg, [self.definition])
        self.bind()
        with self.reg.transaction() as state:
            state['lanes']['stream-owner']['generation'] = 2
        with self.assertRaises(Rejected):
            self.submit()
        with self.reg.transaction() as state:
            state['lanes']['stream-owner']['generation'] = 1
        self.probe[101] = 'dead'
        with self.assertRaises(Rejected):
            self.submit()
        self.probe[101] = 'unknown'
        with self.assertRaises(Rejected):
            self.submit()
        self.probe[101] = 'alive'
        with self.reg.transaction() as state:
            state['lanes']['stream-owner']['state'] = 'done'
        with self.assertRaises(Rejected):
            self.submit()

    def test_stream_worktrees_are_required_and_validated(self):
        configure(self.reg, [self.definition])
        self.bind()
        with self.assertRaises(Rejected):
            self.submit(worktrees=self.worktrees(exists=False))
        with self.assertRaises(Rejected):
            self.submit(worktrees=self.worktrees(branch_ok=False))
        with self.assertRaises(Rejected):
            self.submit(worktrees=self.worktrees(ancestor=False))
        with self.assertRaises(Rejected):
            validate_sources(self.reg, 'actors-assets', observed=self.observe(), worktrees=self.worktrees(exists=False))
        self.submit()

    def test_maintained_wrong_checkout_is_rejected(self):
        config = self.root / 'output/workflow/controller/config.json'
        config.parent.mkdir(parents=True, exist_ok=True)
        root_repo = self.root / 'output/mr'
        native_repo = self.root / 'output/mn'
        self.make_repo(root_repo, 'main', 'other')
        self.make_repo(native_repo, 'main', 'extra')
        config.write_text(json.dumps({'integration_lines': {
            'root': {'repo': 'output/mr', 'ref': 'other'},
            'native': {'repo': 'output/mn', 'ref': 'main'}}}))
        with self.assertRaises(Rejected):
            observe_maintained_sources(self.reg)
        config.write_text(json.dumps({'integration_lines': {
            'root': {'repo': 'output/mr', 'ref': 'main'},
            'native': {'repo': 'output/mn', 'ref': 'main'}}}))
        result = observe_maintained_sources(self.reg)
        self.assertEqual(result['root']['commit'], result['root']['ref_commit'])
        self.assertIsInstance(result['root']['dirty'], str)

    def make_repo(self, path, head_branch, other_branch):
        path.mkdir(parents=True)
        subprocess.run(['git', 'init', '-q', '-b', head_branch, str(path)], check=True)
        (path / 'file.txt').write_text('one\n')
        subprocess.run(['git', '-C', str(path), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(path), '-c', 'user.email=t@t', '-c', 'user.name=t',
                        'commit', '-qm', 'one'], check=True)
        subprocess.run(['git', '-C', str(path), 'branch', other_branch], check=True)
        (path / 'file.txt').write_text('two\n')
        subprocess.run(['git', '-C', str(path), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(path), '-c', 'user.email=t@t', '-c', 'user.name=t',
                        'commit', '-qm', 'two'], check=True)

    def test_owner_binding_is_exclusive_and_generation_is_mandatory(self):
        configure(self.reg, [self.definition,
                             dict(self.definition, id='world-content', name='World content',
                                  scope='World slices')])
        self.bind()
        with self.assertRaises(Rejected):
            self.bind(stream='world-content')
        with self.assertRaises(Rejected):
            self.bind(lane='integration-owner')
        self.bind(lane='integration-owner', replace=True)
        with self.assertRaises(Rejected):
            self.bind(lane='ghost-lane', replace=True)
        with self.assertRaises(Rejected):
            self.bind(generation=99, replace=True)
        with self.assertRaises(Rejected):
            bind_owner(self.reg, 'actors-assets', 'stream-owner', None, replace=True)

    def test_binding_rejects_dead_unknown_and_terminal_owners(self):
        configure(self.reg, [self.definition])
        for health in ('dead', 'unknown'):
            self.probe[101] = health
            with self.assertRaises(Rejected):
                self.bind()
        self.probe[101] = 'alive'
        with self.reg.transaction() as state:
            state['lanes']['stream-owner']['state'] = 'done'
        with self.assertRaises(Rejected):
            self.bind()

    def test_status_reports_owner_liveness(self):
        configure(self.reg, [self.definition])
        self.bind()
        self.assertEqual(status(self.reg)[0]['owner_state'], 'assigned-live')
        self.probe[101] = 'dead'
        self.assertEqual(status(self.reg)[0]['owner_state'], 'assigned-not-live')
        self.probe[101] = 'alive'
        with self.reg.transaction() as state:
            state['lanes']['stream-owner']['generation'] = 2
        self.assertEqual(status(self.reg)[0]['owner_state'], 'assigned-stale-generation')

    def test_retire_ready_abandon_frees_slot_and_is_idempotent(self):
        configure(self.reg, [self.definition])
        self.bind()
        self.submit('c1')
        closed = retire_ready(self.reg, 'actors-assets', 'c1', 'stream-owner', 1, reason='Superseded')
        self.assertEqual(closed['state'], 'abandoned')
        self.assertFalse(closed['accepted'])
        self.assertFalse(closed['delivery_claimed'])
        self.assertIsNone(status(self.reg)[0]['ready_batch'])
        self.submit('c2')
        replayed = retire_ready(self.reg, 'actors-assets', 'c1', 'stream-owner', 1, reason='Superseded')
        self.assertEqual(replayed['closed_at'], closed['closed_at'])
        with self.assertRaises(Rejected):
            retire_ready(self.reg, 'actors-assets', 'c1', 'stream-owner', 1, reason='Different reason')
        with self.assertRaises(Rejected):
            retire_ready(self.reg, 'actors-assets', 'c1', 'stream-owner', 2, reason='Superseded')
        with self.assertRaises(Rejected):
            retire_ready(self.reg, 'actors-assets', 'c1', 'stream-owner', 1, reason='')

    def test_maintained_disposition_is_removed_and_receipts_are_read_only(self):
        configure(self.reg, [self.definition])
        self.bind()
        self.submit('c1')
        receipt = dict(root_commit='1' * 40, validation_path=str(self.log), validation_sha256=digest(self.log))
        with self.reg.transaction() as state:
            state['lanes']['integration-owner']['integration'] = receipt
        with self.assertRaises(Rejected):
            dispatch(self.reg, dict(operation='retire-ready', stream='actors-assets', candidate='c1',
                                    lane='stream-owner', generation=1, disposition='maintained'))
        self.assertIsNotNone(canonical_receipt(self.reg, 'integration-owner'))
        retire_ready(self.reg, 'actors-assets', 'c1', 'stream-owner', 1, reason='No maintained delivery claimed')
        self.assertEqual(receipt_references(self.reg, 'actors-assets'), [])
        self.assertNotEqual(self.reg.snapshot()['lanes']['integration-owner']['state'], 'done')

    def test_no_canonical_integration_or_consumer_wakeups(self):
        before = self.reg.snapshot()
        configure(self.reg, [self.definition])
        self.bind()
        self.submit()
        after = self.reg.snapshot()
        self.assertEqual(after['lanes'], before['lanes'])
        self.assertEqual(after.get('events'), before.get('events'))
        self.assertEqual(after.get('wake_revision'), before.get('wake_revision'))
        self.assertFalse((after.get('control') or {}).get('launches'))
        self.assertFalse((after.get('control') or {}).get('notices'))
        self.assertNotIn('integration', after['lanes']['stream-owner'])
        self.assertNotEqual(after['lanes']['stream-owner']['state'], 'done')
        self.assertTrue(after['development_streams']['streams']['actors-assets']['candidates'])

    def test_candidate_requires_owner_and_hashed_evidence(self):
        configure(self.reg, [self.definition])
        with self.assertRaises(Rejected):
            self.submit()
        self.bind()
        with self.assertRaises(Rejected):
            self.submit(evidence={'path': str(self.log), 'sha256': '0' * 64})

    def test_dispatch_and_manifest_are_read_only_routing(self):
        configure(self.reg, [self.definition])
        result = dispatch(self.reg, dict(operation='status', stream='actors-assets'))
        self.assertEqual(result['streams'][0]['id'], 'actors-assets')
        self.assertEqual(manifest(self.reg)['maintained_base']['actors-assets'], BASE)
        with self.assertRaises(Rejected):
            dispatch(self.reg, dict(operation='record-receipt'))
        self.assertEqual(self.reg.snapshot()['lanes'], self.reg.snapshot()['lanes'])


if __name__ == '__main__':
    unittest.main()
