import json
import unittest
from unittest.mock import patch

from experimental.pikmin2_beasts_floor3_supervisor import supervise
from experimental.pikmin2_beasts_exit_receiver import sha
from randomizer.session import SessionLock
from tests import test_pikmin2_beasts_failure as failures


class Floor3SupervisorTests(unittest.TestCase):
    reopen=failures.FailureTests.reopen
    write_evidence=failures.FailureTests.write_evidence
    transfer=failures.FailureTests.transfer
    stage_failure=failures.FailureTests.stage_failure

    def setUp(self):
        failures.FailureTests.setUp(self)
        self.stage,self.evidence=self.stage_failure()
        report=json.loads((self.stage/'survey.json').read_text());report['terminal_fixture_reason']='extinction'
        (self.stage/'survey.json').write_text(json.dumps(report))
        self.evidence['input_sha256']['survey.json']=sha(self.stage/'survey.json')
        (self.stage/'acceptance.json').write_text(json.dumps(self.evidence))
        self.outputs={name:(self.stage/name).read_bytes() for name in ('native.log','acceptance.json','p2-cave-transfer.txt')}
        for name in self.outputs:(self.stage/name).unlink()

    def start(self):return supervise(self.reopen(),stage=self.stage,exe=self.root/'fixture.exe')

    def complete(self,*args):
        request=json.loads((self.root/'ledger/beasts-supervisor/floor3-request.json').read_text())
        self.assertEqual(request['launch_state'],self.third)
        for name,raw in self.outputs.items():(self.stage/name).write_bytes(raw)

    def test_launch_once_reopen_and_conflicting_arguments_cannot_relaunch(self):
        with patch('experimental.pikmin2_beasts_floor3_supervisor.run',side_effect=self.complete) as run:
            result=self.start();raw=self.reopen().path.read_bytes()
            self.assertEqual(supervise(self.reopen(),stage=self.root/'other',exe=self.root/'other.exe'),result)
            self.assertEqual(self.reopen().path.read_bytes(),raw)
        self.assertEqual(run.call_count,1)
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['state']['surface'],self.third['surface'])

    def test_interrupted_process_stays_pending(self):
        with patch('experimental.pikmin2_beasts_floor3_supervisor.run',side_effect=RuntimeError('crash')) as run:
            with self.assertRaises(RuntimeError):self.start()
            self.assertEqual(supervise(self.reopen())['status'],'pending_or_uncertain')
        self.assertEqual(run.call_count,1)
        self.assertEqual(self.reopen().read(),self.third)

    def test_uncertain_commit_replays(self):
        from experimental.pikmin2_beasts_failure import receive_failure
        def lost(*args):receive_failure(*args);raise RuntimeError('lost response')
        with patch('experimental.pikmin2_beasts_floor3_supervisor.run',side_effect=self.complete), \
             patch('experimental.pikmin2_beasts_floor3_supervisor.receive_failure',side_effect=lost):
            with self.assertRaises(RuntimeError):self.start()
        raw=self.reopen().path.read_bytes()
        self.assertEqual(supervise(self.reopen())['status'],'failed')
        self.assertEqual(self.reopen().path.read_bytes(),raw)

    def test_stage_mismatch_or_lock_blocks_launch(self):
        with SessionLock(self.root/'ledger/beasts-supervisor'),patch('experimental.pikmin2_beasts_floor3_supervisor.run') as run:
            with self.assertRaises(ValueError):self.start()
        run.assert_not_called()
        (self.stage/'checkpoint.json').write_text('{}')
        with patch('experimental.pikmin2_beasts_floor3_supervisor.run') as run:
            with self.assertRaises(ValueError):self.start()
        run.assert_not_called()
        self.assertFalse((self.root/'ledger/beasts-supervisor/floor3-request.json').exists())

    def test_floor2_replay_reports_downstream_failure(self):
        from experimental.pikmin2_beasts_supervisor import _receive
        self.reopen().fail_beasts_floor3(self.third['revision'],self.token,'knockout')
        result=_receive(self.reopen(),dict(launch_state=self.launch,stage=str(self.run)))
        self.assertEqual(result['status'],'failed')
