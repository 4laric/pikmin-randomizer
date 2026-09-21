"""Isolated development_streams contract; no builds, launches or consumer wakeups."""
import tempfile
import unittest
from pathlib import Path

from workflow.development_streams import (bind_owner, configure, dispatch, manifest,
                                          record_maintained_receipt, status, submit_candidate,
                                          validate_sources)
from workflow.handoff import Rejected, digest
from workflow.registry import Registry

BASE = dict(root='a' * 40, native='b' * 40)
MOVED = dict(root='c' * 40, native='d' * 40)


class DevelopmentStreamTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.db = self.root / 'output/workflow/registry.sqlite3'
        self.reg = Registry(self.db, self.root, clock=lambda: 1000.0, process_probe=lambda _: 'alive')
        self.reg.init()
        self.log = self.root / 'output/stream-evidence.md'
        self.log.write_text('stream-local candidate evidence\n')
        self.evidence = {'path': str(self.log), 'sha256': digest(self.log)}
        self.register_lane('stream-owner', issue=9001, level='implementation')
        self.register_lane('integration-owner', issue=9002, level='integration ownership')
        self.definition = dict(id='actors-assets', name='Actors and assets', scope='Actor/asset slices',
                               shared_hooks=['native/pc_port/pc_p2_actor_slots.h'],
                               maintained_base=BASE,
                               worktrees=dict(root='output/development-streams/actors-assets/root',
                                              native='output/development-streams/actors-assets/native'))

    def register_lane(self, lane, issue, level):
        record = dict(lane=lane, owner='Codex through 4laric', worker_id='worker-' + lane,
                      task_id='task-' + lane, issue=issue, scope='Bounded tool slice',
                      target_level=level, state='ready', generation=1, revision=1,
                      next_action='Run checks', milestone='dev-streams',
                      owned_files=['output/' + lane + '.py'], acceptance=['Bounded'],
                      dependencies=[], created_at=1000.0, started_at=None, heartbeat_at=1000.0,
                      progress_at=1000.0, failure_streak=0, recovery_count=0)
        with self.reg.transaction() as state:
            state['lanes'][lane] = record
        return record

    def candidate(self, cid='c1', base=None, state='ready', evidence=None):
        return dict(id=cid, title='Slice ' + cid, summary='Stream-local work',
                    references=['#859', 'existing-lane'], base=base or BASE,
                    commits=dict(root=['e' * 40], native=['f' * 40]),
                    state=state, evidence=evidence or self.evidence)

    def test_configure_reports_unstaffed_roles_without_fabricating_owners(self):
        entry = configure(self.reg, [self.definition])[0]
        self.assertEqual(entry['status'], 'awaiting-owner')
        report = status(self.reg)[0]
        self.assertIsNone(report['owner'])
        self.assertEqual(report['owner_state'], 'awaiting-controller-assignment')
        self.assertEqual(report['maintained_base'], BASE)
        self.assertEqual(report['worktrees']['native'],
                         'output/development-streams/actors-assets/native')

    def test_configure_refuses_silent_maintained_base_move(self):
        configure(self.reg, [self.definition])
        moved = dict(self.definition, maintained_base=MOVED)
        with self.assertRaises(Rejected):
            configure(self.reg, [moved])
        entry = configure(self.reg, [moved], supersede=True)[0]
        self.assertEqual(entry['maintained_base'], MOVED)

    def test_stale_pins_fail_closed(self):
        configure(self.reg, [self.definition])
        bind_owner(self.reg, 'actors-assets', 'stream-owner')
        submit_candidate(self.reg, 'actors-assets', self.candidate())
        with self.assertRaises(Rejected):
            submit_candidate(self.reg, 'actors-assets', self.candidate('stale', base=MOVED))
        configure(self.reg, [dict(self.definition, maintained_base=MOVED)], supersede=True)
        report = status(self.reg)[0]
        self.assertIsNone(report['ready_batch'])
        self.assertEqual(report['stale_candidates'], ['c1'])
        with self.assertRaises(Rejected):
            validate_sources(self.reg, 'actors-assets', BASE)
        validate_sources(self.reg, 'actors-assets', MOVED)

    def test_second_ready_batch_is_rejected_but_draft_allowed(self):
        configure(self.reg, [self.definition])
        bind_owner(self.reg, 'actors-assets', 'stream-owner')
        submit_candidate(self.reg, 'actors-assets', self.candidate('c1'))
        self.assertEqual(status(self.reg)[0]['ready_batch'], 'c1')
        with self.assertRaises(Rejected):
            submit_candidate(self.reg, 'actors-assets', self.candidate('c2'))
        submit_candidate(self.reg, 'actors-assets', self.candidate('c2', state='draft'))
        self.assertEqual(status(self.reg)[0]['ready_batch'], 'c1')

    def test_owner_binding_is_exclusive_and_requires_live_lane(self):
        configure(self.reg, [self.definition,
                             dict(self.definition, id='world-content', name='World content',
                                  scope='World slices')])
        bind_owner(self.reg, 'actors-assets', 'stream-owner')
        with self.assertRaises(Rejected):
            bind_owner(self.reg, 'world-content', 'stream-owner')
        with self.assertRaises(Rejected):
            bind_owner(self.reg, 'actors-assets', 'integration-owner')
        bind_owner(self.reg, 'actors-assets', 'integration-owner', replace=True)
        with self.assertRaises(Rejected):
            bind_owner(self.reg, 'actors-assets', 'ghost-lane')
        with self.assertRaises(Rejected):
            bind_owner(self.reg, 'actors-assets', 'stream-owner', generation=99, replace=True)
        with self.reg.transaction() as state:
            state['lanes']['stream-owner']['state'] = 'done'
        with self.assertRaises(Rejected):
            bind_owner(self.reg, 'actors-assets', 'stream-owner', replace=True)

    def test_no_canonical_integration_or_consumer_wakeups(self):
        before = self.reg.snapshot()
        configure(self.reg, [self.definition])
        bind_owner(self.reg, 'actors-assets', 'stream-owner')
        submit_candidate(self.reg, 'actors-assets', self.candidate())
        after = self.reg.snapshot()
        self.assertEqual(after['lanes'], before['lanes'])
        self.assertEqual(after.get('events'), before.get('events'))
        self.assertEqual(after.get('wake_revision'), before.get('wake_revision'))
        self.assertFalse((after.get('control') or {}).get('launches'))
        self.assertFalse((after.get('control') or {}).get('notices'))
        self.assertNotIn('integration', after['lanes']['stream-owner'])
        self.assertNotEqual(after['lanes']['stream-owner']['state'], 'done')
        self.assertTrue(after['development_streams']['streams']['actors-assets']['candidates'])

    def test_maintained_receipt_reference_requires_integration_owner(self):
        configure(self.reg, [self.definition])
        bind_owner(self.reg, 'actors-assets', 'stream-owner')
        receipt = dict(id='r1', candidate=None, recorded_by='stream-owner', root_commit='1' * 40,
                       native_commit='2' * 40, export_evidence=self.evidence)
        with self.assertRaises(Rejected):
            record_maintained_receipt(self.reg, 'actors-assets', receipt)
        receipt['recorded_by'] = 'integration-owner'
        stored = record_maintained_receipt(self.reg, 'actors-assets', receipt)
        self.assertTrue(stored['reference_only'])
        self.assertEqual(stored['root_commit'], '1' * 40)
        entry = status(self.reg)[0]
        self.assertEqual(entry['maintained_receipts'], ['r1'])
        self.assertNotEqual(self.reg.snapshot()['lanes']['integration-owner']['state'], 'done')

    def test_candidate_requires_owner_and_hashed_evidence(self):
        configure(self.reg, [self.definition])
        with self.assertRaises(Rejected):
            submit_candidate(self.reg, 'actors-assets', self.candidate())
        bind_owner(self.reg, 'actors-assets', 'stream-owner')
        with self.assertRaises(Rejected):
            submit_candidate(self.reg, 'actors-assets',
                             self.candidate(evidence={'path': str(self.log), 'sha256': '0' * 64}))

    def test_dispatch_and_manifest_are_read_only_routing(self):
        configure(self.reg, [self.definition])
        result = dispatch(self.reg, dict(operation='status', stream='actors-assets'))
        self.assertEqual(result['streams'][0]['id'], 'actors-assets')
        self.assertEqual(manifest(self.reg)['maintained_base']['actors-assets'], BASE)
        with self.assertRaises(Rejected):
            dispatch(self.reg, dict(operation='integrate'))
        self.assertEqual(self.reg.snapshot()['lanes'], self.reg.snapshot()['lanes'])


if __name__ == '__main__':
    unittest.main()
