import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from experimental.pikmin2_beasts_exit_receiver import receive_exit,sha
from experimental.pikmin2_beasts_surface_ledger import BeastsSurfaceLedger
from experimental.pikmin2_beasts_checkpoint_reference import BeastsReferenceAdapter
from tests.test_pikmin2_beasts_checkpoint_reference import audit,party,context
from tests.test_pikmin2_beasts_generation import plan
from tests.test_pikmin2_beasts_witness_bridge import native_trace
from tests.test_pikmin2_beasts_boundary import bound


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.run=self.root/'run';self.run.mkdir()
        self.adapter=BeastsReferenceAdapter(audit(),'a'*64,{1:{},2:{},3:{}})
        ledger=self.reopen();ledger.create(dict(region='test',day=1,time=8,position=[0,0,0],squad=party(),health=1,receipts={}))
        first=ledger.enter_beasts(0,'c'*32)
        self.launch=ledger.apply_beasts_floor(1,first['trip']['token'],squad=party(),health=1,receipts={},conversions=[],destination_context=context(19))
        token=self.launch['trip']['token']
        readiness=plan(19);readiness['override_sha256']={}
        (self.run/'readiness.json').write_text(json.dumps(readiness))
        names=['readiness.json','p2-purple.txt','p2-pod.txt','p2-cargo-free.txt','p2-beasts-floor2-fixture.txt',
               'p2-beasts-boundary.txt','p2-cave-entry.txt','p2-cave-transition.txt','p2-beasts-exit-fixture.txt']
        for name in names[1:]:(self.run/name).write_text('test input')
        log=bound(native_trace(),token).replace('P2_BEASTS_PARTY health=',
            'P2_BEASTS_EXIT_REMOTE_REJECTED\nP2_BEASTS_EXIT_TRANSFER_WRITTEN\nP2_BEASTS_PARTY health=',1)
        (self.run/'native.log').write_text(log)
        (self.run/'p2-cave-transfer.txt').write_text(f'P2_BEASTS_TRANSFER_1\n{token}\n2 3 0.875 20\n'+''.join(f'{1 if i<10 else 3} {i%3}\n' for i in range(20)))
        exe=self.root/'fixture.exe';exe.write_bytes(b'test executable')
        self.evidence=dict(passed=True,returncode=42,exit_handoff_fixture=True,boundary_token=token,
            input_sha256={name:sha(self.run/name) for name in names},executable=str(exe),executable_sha256=sha(exe),
            log_sha256=sha(self.run/'native.log'),transfer_sha256=sha(self.run/'p2-cave-transfer.txt'))
        self.write_evidence()
    def reopen(self):return BeastsSurfaceLedger(self.root/'ledger','a'*64,'b'*32,self.adapter)
    def write_evidence(self):(self.run/'acceptance.json').write_text(json.dumps(self.evidence))
    def test_receive_and_retry_after_restart(self):
        third=receive_exit(self.reopen(),self.launch,self.run)
        self.assertEqual(third['trip']['checkpoint']['floor'],3)
        self.assertEqual(receive_exit(self.reopen(),self.launch,self.run),third)
    def test_wrong_exit_and_boundary_do_not_write(self):
        original=self.reopen().path.read_bytes()
        for key,value in [('returncode',0),('passed',False),('boundary_token','d'*64)]:
            old=self.evidence[key];self.evidence[key]=value;self.write_evidence()
            with self.subTest(key=key),self.assertRaises(ValueError):receive_exit(self.reopen(),self.launch,self.run)
            self.assertEqual(self.reopen().path.read_bytes(),original)
            self.evidence[key]=old
    def test_mutated_inputs_log_transfer_or_executable_do_not_write(self):
        original=self.reopen().path.read_bytes()
        for path in [self.run/'p2-cave-entry.txt',self.run/'native.log',self.run/'p2-cave-transfer.txt',Path(self.evidence['executable'])]:
            old=path.read_bytes();path.write_bytes(old+b'changed')
            with self.subTest(path=path),self.assertRaises(ValueError):receive_exit(self.reopen(),self.launch,self.run)
            self.assertEqual(self.reopen().path.read_bytes(),original);path.write_bytes(old)
    def test_missing_manifest_and_stale_launch(self):
        del self.evidence['input_sha256']['p2-cave-entry.txt'];self.write_evidence()
        with self.assertRaises(ValueError):receive_exit(self.reopen(),self.launch,self.run)
        with self.assertRaises(ValueError):receive_exit(self.reopen(),dict(self.launch,campaign='d'*32),self.run)
    def test_parser_uses_verified_bytes_if_log_changes_after_read(self):
        original=Path.read_bytes;log=self.run/'native.log'
        def read(path):
            raw=original(path)
            if path==log:path.write_bytes(b'changed after verified read')
            return raw
        with patch.object(Path,'read_bytes',read):
            result=receive_exit(self.reopen(),self.launch,self.run)
        self.assertEqual(result['trip']['checkpoint']['floor'],3)
        with self.assertRaises(ValueError):receive_exit(self.reopen(),self.launch,self.run)
