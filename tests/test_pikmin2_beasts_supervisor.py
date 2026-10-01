import json
import unittest
from unittest.mock import patch

from experimental.pikmin2_beasts_supervisor import supervise
from randomizer.session import SessionLock
from tests import test_pikmin2_beasts_exit_receiver as receiver_tests


class SupervisorTests(unittest.TestCase):
    setUp = receiver_tests.ReceiverTests.setUp
    reopen = receiver_tests.ReceiverTests.reopen
    write_evidence = receiver_tests.ReceiverTests.write_evidence

    @property
    def request(self):return self.root/'ledger/beasts-supervisor/request.json'

    def start(self):
        return supervise(self.reopen(), root=self.root, assets=self.root,
                         exe=self.root/'fixture.exe', output=self.root/'runs')

    def complete(self, args, *, prepared):
        request = json.loads(self.request.read_text())
        self.assertEqual(request['launch_state'], self.launch)
        self.assertIsNone(request['stage'])
        self.assertEqual(args.boundary_token, self.launch['trip']['token'])
        self.assertEqual(args.global_purple_count, 19)
        self.assertTrue(args.exit_handoff)
        prepared(self.run)
        self.assertEqual(json.loads(self.request.read_text())['stage'], str(self.run))
        return True

    def test_start_and_reopen_never_launches_floor3(self):
        with patch('experimental.pikmin2_beasts_supervisor.run', side_effect=self.complete) as run:
            result = self.start()
            raw = self.reopen().path.read_bytes()
            recovered = supervise(self.reopen())
        self.assertEqual(run.call_count, 1)
        self.assertEqual(recovered, result)
        self.assertEqual(result['status'], 'floor3_stopped')
        self.assertEqual(result['state']['surface'], self.launch['surface'])
        self.assertEqual(self.reopen().path.read_bytes(), raw)

    def test_crash_before_stage_never_relaunches(self):
        with patch('experimental.pikmin2_beasts_supervisor.run', side_effect=RuntimeError('crash')) as run:
            with self.assertRaises(RuntimeError):self.start()
            result = supervise(self.reopen())
        self.assertEqual(run.call_count, 1)
        self.assertEqual(result['status'], 'pending_or_uncertain')
        self.assertEqual(result['state'], self.launch)

    def test_crash_after_stage_recovers_completed_evidence(self):
        def crash(args, *, prepared):
            self.complete(args, prepared=prepared)
            raise RuntimeError('lost result')
        with patch('experimental.pikmin2_beasts_supervisor.run', side_effect=crash) as run:
            with self.assertRaises(RuntimeError):self.start()
            self.assertEqual(supervise(self.reopen())['status'], 'floor3_stopped')
        self.assertEqual(run.call_count, 1)

    def test_incomplete_and_failed_evidence_do_not_advance(self):
        raw = self.reopen().path.read_bytes()
        (self.run/'acceptance.json').unlink()
        with patch('experimental.pikmin2_beasts_supervisor.run', side_effect=self.complete):
            self.assertEqual(self.start()['status'], 'pending_or_uncertain')
        self.evidence['passed'] = False
        self.write_evidence()
        with self.assertRaises(ValueError):supervise(self.reopen())
        self.assertEqual(self.reopen().path.read_bytes(), raw)

    def test_uncertain_commit_replays(self):
        from experimental.pikmin2_beasts_exit_receiver import receive_exit
        def lost(ledger, state, stage):
            receive_exit(ledger, state, stage)
            raise RuntimeError('response lost after commit')
        with patch('experimental.pikmin2_beasts_supervisor.run', side_effect=self.complete), \
             patch('experimental.pikmin2_beasts_supervisor.receive_exit', side_effect=lost):
            with self.assertRaises(RuntimeError):self.start()
        raw = self.reopen().path.read_bytes()
        self.assertEqual(supervise(self.reopen())['status'], 'floor3_stopped')
        self.assertEqual(self.reopen().path.read_bytes(), raw)

    def test_concurrent_start_is_rejected(self):
        with SessionLock(self.root/'ledger/beasts-supervisor'), \
             patch('experimental.pikmin2_beasts_supervisor.run') as run:
            with self.assertRaisesRegex(ValueError, 'another runner'):self.start()
        run.assert_not_called()
        self.assertFalse(self.request.exists())

    def test_unsupported_party_is_rejected_before_intent(self):
        state = json.loads(json.dumps(self.launch))
        state['trip']['checkpoint']['squad'][0]['maturity'] = 1
        with patch('experimental.pikmin2_beasts_surface_ledger.BeastsSurfaceLedger.read', return_value=state), \
             patch('experimental.pikmin2_beasts_supervisor.run') as run:
            with self.assertRaisesRegex(ValueError, 'twenty leaf Reds'):self.start()
        run.assert_not_called()
        self.assertFalse(self.request.exists())
