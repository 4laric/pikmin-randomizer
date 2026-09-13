from copy import deepcopy
import json
import unittest

from experimental.pikmin2_beasts_failure import apply_failure,failure_reason,receive_failure
from experimental.pikmin2_beasts_checkpoint_reference import digest
from experimental.pikmin2_beasts_exit_receiver import sha
from experimental.pikmin2_beasts_exit_receiver import receive_exit
from tests import test_pikmin2_beasts_exit_receiver as receiver_tests


class FailureTests(unittest.TestCase):
    reopen=receiver_tests.ReceiverTests.reopen
    write_evidence=receiver_tests.ReceiverTests.write_evidence

    def setUp(self):
        receiver_tests.ReceiverTests.setUp(self)
        self.third=receive_exit(self.reopen(),self.launch,self.run)
        self.token=self.third['trip']['token']

    def transfer(self,reason='extinction'):
        return f'P2_BEASTS_FAILURE_1\n{self.token}\n3 0 0 0\n{reason}\n'

    def test_failure_reopens_and_replays_without_surface_or_rewards_change(self):
        result=apply_failure(self.reopen(),self.third,self.transfer())
        cp=result['trip']['checkpoint'];before=self.third['trip']['checkpoint']
        self.assertEqual((result['phase'],result['revision'],result['trip']['token']),('failed',4,None))
        self.assertEqual((cp['floor'],cp['revision'],cp['health'],cp['squad']),(3,3,0,[]))
        self.assertEqual(result['surface'],self.third['surface'])
        for key in ('receipts','conversions','context','budgets'):self.assertEqual(cp[key],before[key])
        raw=self.reopen().path.read_bytes()
        self.assertEqual(apply_failure(self.reopen(),self.third,self.transfer()),result)
        self.assertEqual(self.reopen().path.read_bytes(),raw)
        with self.assertRaises(ValueError):self.reopen().launch_requirement()
        with self.assertRaises(ValueError):self.reopen().return_to_surface()
        with self.assertRaises(ValueError):apply_failure(self.reopen(),self.third,self.transfer('knockout'))
        self.assertEqual(self.reopen().path.read_bytes(),raw)

    def test_knockout_and_conflicting_reference_replay(self):
        before=self.third['trip']['checkpoint']
        failed=self.adapter.fail_floor3(before,self.token,'knockout')
        self.assertEqual(self.adapter.fail_floor3(failed,self.token,'knockout'),failed)
        for reason in ('extinction','unknown'):
            with self.subTest(reason=reason),self.assertRaises(ValueError):self.adapter.fail_floor3(failed,self.token,reason)
        for state in (self.launch['trip']['checkpoint'],failed):
            with self.subTest(state=state['status']),self.assertRaises(ValueError):
                self.adapter.fail_floor3(state,self.adapter.token(state),'knockout')

    def test_wrong_transfer_cannot_write(self):
        text=self.transfer();raw=self.reopen().path.read_bytes()
        for bad in [text+'1 0\n',text.replace(self.token,'f'*64),text.replace('3 0 0 0','3 4 0 0'),
                    text.replace('3 0 0 0','3 0 1 0'),text.replace('3 0 0 0','3 0 0 1'),
                    text.replace('extinction','retreat'),text.replace('FAILURE','TRANSFER'),
                    text+'\n',text.replace('3 0 0 0','3 0 nan 0')]:
            with self.subTest(bad=bad),self.assertRaises(ValueError):apply_failure(self.reopen(),self.third,bad)
            self.assertEqual(self.reopen().path.read_bytes(),raw)
        with self.assertRaises(ValueError):apply_failure(self.reopen(),self.launch,text)
        with self.assertRaises(ValueError):apply_failure(self.reopen(),dict(self.third,campaign='f'*32),text)

    def test_successful_floor4_remains_forbidden(self):
        cp=self.third['trip']['checkpoint']
        with self.assertRaisesRegex(ValueError,'Unsupported floor3'):
            self.adapter.apply(cp,self.token,cp['squad'],cp['health'],cp['receipts'],[],{})
        self.assertEqual(self.adapter.validate(json.loads(json.dumps(cp))),cp)
        failed=self.adapter.fail_floor3(cp,self.token,'extinction')
        for field,value in [('health',1),('revision',2),('floor',4),('squad',cp['squad'])]:
            bad=deepcopy(failed);bad[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.adapter.validate(bad)

    def test_strict_token_and_reason_parser(self):
        self.assertEqual(failure_reason(self.transfer('knockout'),self.token),'knockout')
        for token in ('',self.token.upper(),None,'f'*63):
            with self.subTest(token=token),self.assertRaises(ValueError):failure_reason(self.transfer(),token)

    def stage_failure(self,reason='extinction'):
        stage=self.root/'failure';stage.mkdir()
        cp=self.third['trip']['checkpoint'];entry=['P2_BEASTS_FLOOR3_ENTRY_1',self.token,f'3 {cp["health"]:.9g} 20']
        entry += [f'{1 if p["species"]=="red" else 3} {p["maturity"]}' for p in cp['squad']]
        files={'checkpoint.json':json.dumps(cp),'p2-floor3-boundary.txt':self.token+'\n','p2-cave-entry.txt':'\n'.join(entry)+'\n',
               'p2-floor3-failure-fixture.txt':f'P2_FLOOR3_FAILURE_FIXTURE_1\n{reason}\n',
               'p2-cargo-free.txt':'test','p2-pod.txt':'test','p2-purple.txt':'test'}
        for name,raw in files.items():(stage/name).write_text(raw)
        hashes={name:sha(stage/name) for name in files}
        survey=dict(policy='P2_BEASTS_FLOOR3_ENTRY_SURVEY_1',floor=3,native_profile='forest_1',boundary_token=self.token,
            checkpoint_identity=digest(cp),checkpoint_profile=self.adapter.identity,party_restore_protocol_floor=3,
            party=dict(health=cp['health'],squad=cp['squad']),input_sha256=dict(hashes))
        (stage/'survey.json').write_text(json.dumps(survey));hashes['survey.json']=sha(stage/'survey.json')
        (stage/'native.log').write_text('\n'.join([f'P2_BEASTS_ENTRY_READY floor=3 token={self.token} descent=disabled',
            f'P2_FLOOR3_FAILURE_ARMED token={self.token} reason={reason} active_descent_rejected=1',
            f'P2_FLOOR3_FAILURE_INJECTED reason={reason} repairs_unchanged=1 pokos=0',
            f'P2_BEASTS_FAILURE floor=3 destination=0 reason={reason} survivors=0 health=0'])+'\n')
        (stage/'p2-cave-transfer.txt').write_text(self.transfer(reason))
        exe=self.root/'fixture.exe'
        evidence=dict(policy='P2_BEASTS_FAILURE_1',passed=True,returncode=42,token=self.token,reason=reason,
            input_sha256=hashes,exe=str(exe),executable_sha256=sha(exe),log_sha256=sha(stage/'native.log'),
            transfer_sha256=sha(stage/'p2-cave-transfer.txt'))
        (stage/'acceptance.json').write_text(json.dumps(evidence))
        return stage,evidence

    def test_receiver_hash_checks_and_exact_replay(self):
        stage,evidence=self.stage_failure('knockout')
        raw=self.reopen().path.read_bytes()
        for name in ('checkpoint.json','p2-cave-entry.txt','native.log','p2-cave-transfer.txt'):
            path=stage/name;before=path.read_bytes();path.write_bytes(before+b'changed')
            with self.subTest(name=name),self.assertRaises(ValueError):receive_failure(self.reopen(),self.third,stage)
            self.assertEqual(self.reopen().path.read_bytes(),raw);path.write_bytes(before)
        result=receive_failure(self.reopen(),self.third,stage)
        self.assertEqual(receive_failure(self.reopen(),self.third,stage),result)

    def test_receiver_rejects_wrong_process_and_unbound_stage(self):
        stage,evidence=self.stage_failure()
        raw=self.reopen().path.read_bytes()
        for key,value in [('returncode',0),('passed',False),('reason','knockout'),('token','f'*64)]:
            bad=deepcopy(evidence);bad[key]=value;(stage/'acceptance.json').write_text(json.dumps(bad))
            with self.subTest(key=key),self.assertRaises(ValueError):receive_failure(self.reopen(),self.third,stage)
            self.assertEqual(self.reopen().path.read_bytes(),raw)

    def test_valid_hashes_cannot_hide_wrong_party(self):
        stage,evidence=self.stage_failure();raw=self.reopen().path.read_bytes()
        path=stage/'p2-cave-entry.txt';path.write_text(path.read_text().replace('3 0.875 20','3 1 20'))
        survey=json.loads((stage/'survey.json').read_text())
        survey['input_sha256']['p2-cave-entry.txt']=sha(path)
        (stage/'survey.json').write_text(json.dumps(survey))
        evidence['input_sha256'].update(survey['input_sha256'])
        evidence['input_sha256']['survey.json']=sha(stage/'survey.json')
        (stage/'acceptance.json').write_text(json.dumps(evidence))
        with self.assertRaisesRegex(ValueError,'entry party'):receive_failure(self.reopen(),self.third,stage)
        self.assertEqual(self.reopen().path.read_bytes(),raw)
