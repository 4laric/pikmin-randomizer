"""Engine-free staging controls; these do not establish native gameplay."""
import importlib.util
from pathlib import Path
import struct
import hashlib
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('white_campaign_stage', ROOT / 'scripts/stage_p2_white_campaign.py')
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


def row(name, kind=b'ikip', model=b'50rp'):
    result = bytearray(96)
    result[:8] = b'    0.0v'
    result[16:48] = name.ljust(32, b'\0')
    result[72:76] = kind
    result[80:84] = model
    return bytes(result)


class StageControls(unittest.TestCase):
    def source(self, count=20):
        rows = [row(('red%d' % i).encode()) for i in range(count)]
        rows += [row(b'preview dwarf bulborb', b'iket'), row(b'preview red onion', b'meti'),
                 row(b'preview ship', b'meti'), row(b'preview treasure bolt', b'tlle')]
        return b'1.0v' + struct.pack('>4f', 0, 0, 0, 0) + struct.pack('>I', len(rows)) + b''.join(rows)

    def rewrite(self, source, retail=False):
        boss = bytearray(row(b'original Pom', b'ssob'))
        boss[76:80] = b'\x02\0\0\0'
        with patch.object(stage, 'generator', return_value=source), patch.object(stage, 'records', return_value=[bytes(boss)]):
            return stage.rewrite_generators(Path('mock-assets'), retail)

    def test_original_twenty_bodies_preserved(self):
        source = self.source()
        result = self.rewrite(source, True)
        for index in range(20):
            before = source[24+96*index:24+96*(index+1)]
            after = result[24+96*index:24+96*(index+1)]
            self.assertEqual(before[:8] + before[12:], after[:8] + after[12:])
            self.assertEqual(struct.unpack_from('<I', after, 8)[0], index+1)

    def test_three_natural_ivory_and_one_violet(self):
        result = self.rewrite(self.source(), True)
        self.assertEqual(struct.unpack_from('>I', result, 20)[0], 27)
        rows = [result[i:i+96] for i in range(24, len(result), 96)]
        ids = [struct.unpack_from('<I', r, 8)[0] for r in rows]
        self.assertEqual(len(set(ids)), 27)
        self.assertTrue({25, 28, 29, 27}.issubset(ids))
        self.assertNotIn(b'preview dwarf bulborb', result)

    def test_p1_baseline_one_ivory(self):
        result = self.rewrite(self.source())
        self.assertEqual(struct.unpack_from('>I', result, 20)[0], 25)

    def test_underfilled_and_overfilled_refuse(self):
        for count in (0, 19, 21):
            with self.subTest(count=count), self.assertRaisesRegex(ValueError, '20 original'):
                self.rewrite(self.source(count), True)

    def test_changed_native_host_refuses(self):
        with self.assertRaisesRegex(ValueError, 'Red5 model'):
            self.rewrite(self.source().replace(b'50rp', b'10rp'))

    def test_unknown_generator_refuses(self):
        with self.assertRaisesRegex(ValueError, 'Unexpected'):
            self.rewrite(self.source().replace(b'preview ship', b'unknown ship'))

    def test_missing_legal_directories_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'Explicit existing'):
                stage.prepare(Path(tmp)/'absent', tmp, tmp, tmp, Path(tmp)/'fresh')

    def test_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp)/'marker';marker.write_bytes(b'preserve')
            with self.assertRaisesRegex(ValueError, 'Fresh private'):
                stage.prepare(tmp, tmp, tmp, tmp, tmp)
            self.assertEqual(marker.read_bytes(), b'preserve')


if __name__ == '__main__':
    unittest.main()

# No X server or engine is launched by these protocol/card refusal controls.
sys.path.insert(0,str(ROOT))
from scripts import run_p2_white_campaign as runner

class FakeKeys:
    def __init__(self):self.calls=[];self.valid=True;self.release_error=False
    def verify(self):
        if not self.valid:raise ValueError('foreign/missing window')
        self.calls.append(('verify',))
    def key(self,key,pressed):
        self.calls.append((key,pressed))
        if self.release_error and key=='F10' and not pressed:raise ValueError('release error')

class KeyProtocolControls(unittest.TestCase):
    def setUp(self):
        self.now=10.;self.backend=FakeKeys()
        self.p=runner.ShipKeyProtocol(self.backend,lambda:self.now)
    def request(self,key='SHIFT_F10',seq=1):
        self.p.line(f'P2_WHITE_NATIVE_KEY_REQUEST seq={seq} key={key} actual_SDL_keyboard_required=1')
    def test_actual_deposit_effect_releases_all_keys(self):
        self.request();self.assertIsNotNone(self.p.pending)
        self.p.line('P2_SHIP_DEPOSIT species=4 maturity=0 stored=1')
        self.assertIsNone(self.p.pending)
        self.assertEqual(self.backend.calls[-3:],[('F10',False),('CTRL',False),('SHIFT',False)])
    def test_wrong_species_does_not_acknowledge(self):
        self.request();self.p.line('P2_SHIP_DEPOSIT species=3 maturity=0 stored=1')
        self.assertIsNotNone(self.p.pending);self.now=12.01
        with self.assertRaises(ValueError):self.p.tick()
        self.assertTrue(self.p.closed)
    def test_wrong_maturity_does_not_acknowledge(self):
        self.request();self.p.line('P2_SHIP_DEPOSIT species=4 maturity=1 stored=1')
        self.assertIsNotNone(self.p.pending)
    def test_unexpected_key_refuses(self):
        with self.assertRaises(ValueError):self.request('F10')
    def test_duplicate_overlapping_request_refuses(self):
        self.request()
        with self.assertRaises(ValueError):self.request()
    def test_malformed_request_refuses(self):
        with self.assertRaises(ValueError):self.p.line('P2_WHITE_NATIVE_KEY_REQUEST seq=1 key=A actual_SDL_keyboard_required=1')
    def test_window_verification_precedes_press(self):
        self.backend.valid=False
        with self.assertRaises(ValueError):self.request()
        self.assertFalse(any(len(c)==2 and c[1] is True for c in self.backend.calls))
    def test_absolute_deadline_is_native_start_not_first_request(self):
        self.p=runner.ShipKeyProtocol(self.backend,lambda:self.now,started=-49.9)
        self.now=10.1
        with self.assertRaises(ValueError):self.request()
    def test_all_releases_attempted_after_one_failure(self):
        self.request();self.backend.release_error=True
        with self.assertRaises(RuntimeError):self.p.close()
        self.assertEqual(self.backend.calls[-3:],[('F10',False),('CTRL',False),('SHIFT',False)])
        self.assertTrue(self.p.closed)
    def test_resume_choice_then_fifteen_withdrawals(self):
        self.p=runner.ShipKeyProtocol(self.backend,lambda:self.now,resume=True)
        self.request('CTRL_F10');self.p.line('P2_SHIP_CHOICE captain=0 species=4')
        for index in range(15):
            self.request('F10',2+index)
            self.p.line(f'P2_SHIP_WITHDRAW species=4 maturity=0 stored={14-index}')
        self.assertEqual(len(self.p.effects),16)
    def test_resume_shift_deposit_refuses(self):
        self.p=runner.ShipKeyProtocol(self.backend,lambda:self.now,resume=True)
        with self.assertRaises(ValueError):self.request()

class PublicationDeadlineControls(unittest.TestCase):
    setUp=KeyProtocolControls.setUp
    request=KeyProtocolControls.request
    def test_slow_verification_never_publishes_late_keys(self):
        def slow_verify():self.now=71.
        self.backend.verify=slow_verify
        with self.assertRaises(ValueError):self.request()
        self.assertTrue(self.p.closed)
        self.assertFalse(any(len(c)==2 and c[1] is True for c in self.backend.calls))
    def test_clock_expires_between_modifier_and_f10(self):
        original=self.backend.key
        def slow_key(key,pressed):
            original(key,pressed)
            if key=='SHIFT' and pressed:self.now=71.
        self.backend.key=slow_key
        with self.assertRaises(ValueError):self.request()
        self.assertNotIn(('F10',True),self.backend.calls)
        self.assertIn(('SHIFT',False),self.backend.calls)

class CardControls(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.directory=Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.config='P2_WHITE_TREASURE_CAMPAIGN_1 0 26 23 '+' '.join([str(i)*64 for i in (1,2,3)])
        (self.directory/'p2-white-treasure-campaign.txt').write_text(self.config)
        self.identity=hashlib.sha256(' '.join(self.config.split()[1:]).encode()).hexdigest()
        self.fields=['PIKMIN_CAMPAIGN_WHITE_TREASURE_1','a'*64,'1','0','0','0',
                     '0','0','0','15','0','0','3','0','25','5','0','28','5','0','29','5',self.identity,'1']
        self.path=self.directory/'00000000000000000001.sav'
        self.guard=patch.object(runner,'validate_inputs',return_value={});self.guard.start();self.addCleanup(self.guard.stop)
    def write(self,fields=None,block=None):
        prefix=' '.join(fields or self.fields).encode()
        if block is None:
            data=bytearray(32768);data[0]=2;data[2]=2
            struct.pack_into('>3i',data,4,5,-1,-1);data[20:24]=b'cont'
            struct.pack_into('>9i',data,24,0,0,0,5,0,0,0,0,0);data[60:64]=b'cach'
            value=0x32546532
            for i,(word,) in enumerate(struct.iter_unpack('>I',data[:0x7ff8])):
                j=i&255;mix=(j<<24)|(((j+1)&255)<<16)|(((j-1)&255)<<8)|((j+2)&255)
                value=(value+mix+word)&0xffffffff
            struct.pack_into('>2I',data,0x7ff8,0,(0x32546532-value)&0xffffffff)
            block=bytes(data)
        value=14695981039346656037
        for byte in prefix+b'\n'+block:value=((value^byte)*1099511628211)&((1<<64)-1)
        self.path.write_bytes(prefix+b' '+str(value).encode()+b'\n'+block)
    def verify(self):
        return runner.verify_native_card(self.path,fingerprint='a'*64,generation=1,stage=self.directory,check_count=100,expected_day=2,expected_p1_stock=[0,0,0,5,0,0,0,0,0])
    def test_atomic_stock_budget_ledger_and_full_block(self):
        self.write();result=self.verify()
        self.assertEqual(result['native_block_size'],32768)
        self.assertEqual(result['stock_white_leaf'],15)
        self.assertEqual(result['ivory_budget_spent'],15)
        self.assertEqual(result['retail_pokos'],180)
    def test_checksum_damaged_native_block_refuses(self):
        self.write();data=bytearray(self.path.read_bytes());data[-1]=1;self.path.write_bytes(data)
        with self.assertRaises(ValueError):self.verify()
    def test_short_or_extra_block_refuses(self):
        for size in (32767,32769):
            self.write(block=bytes(size))
            with self.assertRaises(ValueError):self.verify()
    def test_stale_version_fingerprint_generation_refuse(self):
        for index,value in ((0,'PIKMIN_CAMPAIGN_WHITE_1'),(1,'b'*64),(2,'2')):
            fields=self.fields.copy();fields[index]=value;self.write(fields)
            with self.assertRaises(ValueError):self.verify()
    def test_stock_maturity_budget_ledger_descriptor_refuse(self):
        for index,value in ((9,'14'),(10,'1'),(15,'4'),(18,'6'),(22,'b'*64),(23,'0')):
            fields=self.fields.copy();fields[index]=value;self.write(fields)
            with self.assertRaises(ValueError):self.verify()
    def test_consumed_benefit_outside_manifest_refuses(self):
        fields=self.fields.copy();fields[3]='101';self.write(fields)
        with self.assertRaises(ValueError):self.verify()
    def test_extra_header_field_refuses(self):
        self.write(self.fields+['1'])
        with self.assertRaises(ValueError):self.verify()
    def test_wrong_generation_filename_refuses(self):
        self.write();self.path=self.path.rename(self.directory/'00000000000000000002.sav')
        with self.assertRaises(ValueError):self.verify()

class NativeCardLayoutControls(unittest.TestCase):
    setUp=CardControls.setUp
    write=CardControls.write
    verify=CardControls.verify
    def test_recomputed_metadata_hash_does_not_hide_native_card_checksum_damage(self):
        self.write();block=bytearray(self.path.read_bytes().split(b'\n',1)[1]);block[100]=1
        self.write(block=block)
        with self.assertRaisesRegex(ValueError,'native card checksum'):self.verify()
    def test_duplicate_original_red_native_stock_refuses(self):
        self.write();block=bytearray(self.path.read_bytes().split(b'\n',1)[1]);struct.pack_into('>i',block,36,20)
        self.write(block=block)
        with self.assertRaisesRegex(ValueError,'all-color maturity'):self.verify()
    def test_actual_native_day_and_save_status_refuse(self):
        for offset,value in ((0,0),(2,3)):
            self.write();block=bytearray(self.path.read_bytes().split(b'\n',1)[1]);block[offset]=value;self.write(block=block)
            with self.assertRaisesRegex(ValueError,'PlayState day'):self.verify()
    def test_actual_native_container_boundary_refuses(self):
        self.write();block=bytearray(self.path.read_bytes().split(b'\n',1)[1]);block[20:24]=b'xxxx';self.write(block=block)
        with self.assertRaisesRegex(ValueError,'serialization boundary'):self.verify()

class HelperGrammarControls(unittest.TestCase):
    def test_duplicate_helper_response_field_refuses(self):
        with self.assertRaisesRegex(ValueError,'Duplicate IPC field'):
            runner.strict_json('{"seq":1,"seq":1,"ok":true,"error":null}')
    def test_duplicate_phase_request_field_refuses(self):
        with self.assertRaisesRegex(ValueError,'Duplicate IPC field'):
            runner.strict_json('{"mode":"positive","mode":"resume"}')




class PhaseOutcome28Controls(unittest.TestCase):
    def result(self,mode='positive',**changes):
        result={'mode':mode,'error':None,'cleanup_errors':[],'timed_out':False,'launched':True,
                'exit_code':86 if mode in ('forced-down','paused-down') else 0,'elapsed':10.0}
        result.update(changes);return result
    def test_selected_negative86_is_valid(self):
        from scripts.run_p2_white_campaign import phase_failure
        for mode in ('forced-down','paused-down'):self.assertIsNone(phase_failure(self.result(mode),mode))
    def test_nested_runtime_error_propagates(self):
        from scripts.run_p2_white_campaign import phase_failure
        self.assertIn('Inner phase error',phase_failure(self.result(error='helper died'),'positive'))
    def test_nested_cleanup_error_propagates(self):
        from scripts.run_p2_white_campaign import phase_failure
        self.assertIn('cleanup failed',phase_failure(self.result(cleanup_errors=['key unconfirmed']),'positive'))
    def test_nested_timeout_propagates(self):
        from scripts.run_p2_white_campaign import phase_failure
        self.assertIn('timed out',phase_failure(self.result(timed_out=True),'positive'))
    def test_missing_timeout_not_assumed_false(self):
        from scripts.run_p2_white_campaign import phase_failure
        result=self.result();del result['timed_out'];self.assertIsNotNone(phase_failure(result,'positive'))
    def test_negative86_in_positive_refused(self):
        from scripts.run_p2_white_campaign import phase_failure
        self.assertIn('raw native exit',phase_failure(self.result(exit_code=86),'positive'))
    def test_negative_exit0_in_guard_refused(self):
        from scripts.run_p2_white_campaign import phase_failure
        self.assertIsNotNone(phase_failure(self.result('forced-down',exit_code=0),'forced-down'))
    def test_mismatched_mode_false_launch_and_late_elapsed_refuse(self):
        from scripts.run_p2_white_campaign import phase_failure
        for changes in ({'mode':'ready'},{'launched':False},{'elapsed':240.1},{'elapsed':float('nan')}):
            self.assertIsNotNone(phase_failure(self.result(**changes),'positive'))


class UnitIdentity28Controls(unittest.TestCase):
    """Synthetic systemctl/kernel snapshots; no Linux unit or process launched."""
    def context(self):
        argv=['/usr/bin/python3','-I','-B','/home/gamebuild/white1191/source/linux-controls28.py']
        expected={'argv':argv,'executable':'/usr/bin/python3.11','executable_sha256':'a'*64,
                  'cgroup':'/user.slice/user-1000.slice/user@1000.service/app.slice/white1191-28-'+('b'*32)+'.service'}
        process={'pid':4321,'birth':'9981','uid':1000,'argv':argv,'executable':expected['executable'],
                 'executable_sha256':expected['executable_sha256'],'cgroup':expected['cgroup']}
        facts={'ExecStart':'{ path=/usr/bin/python3 ; argv[]='+(' '.join(argv))+' ; ignore_errors=no ; start_time=[now] ; stop_time=[n/a] ; pid=4321 ; code=(null) ; status=0 }',
               'InvocationID':'c'*32,'ControlGroup':expected['cgroup'],'MainPID':'4321','ExecMainPID':'4321'}
        return facts,expected,process
    def test_normal_exit_mutable_execstart_fields_do_not_change_identity(self):
        from scripts.run_p2_white_campaign import bind_unit_identity
        facts,expected,process=self.context();prior=bind_unit_identity(facts,expected,process,live=process)
        facts.update(MainPID='0',ControlGroup='')
        facts['ExecStart']=facts['ExecStart'].replace('stop_time=[n/a]','stop_time=[later]').replace('code=(null)','code=exited')
        after=bind_unit_identity(facts,expected,process,prior=prior)
        self.assertEqual(after['command'],prior['command']);self.assertNotEqual(after['mutable_observation'],prior['mutable_observation'])
    def test_exit23_and_sigkill_observations_preserve_stable_fields(self):
        from scripts.run_p2_white_campaign import bind_unit_identity
        for code,status in [('exited','23'),('killed','9')]:
            facts,expected,process=self.context();prior=bind_unit_identity(facts,expected,process,live=process)
            facts.update(MainPID='0');facts['ExecStart']=facts['ExecStart'].replace('code=(null)','code='+code).replace('status=0','status='+status)
            self.assertEqual(bind_unit_identity(facts,expected,process,prior=prior)['process'],process)
    def test_mainpid_zero_without_actual_history_refuses(self):
        from scripts.run_p2_white_campaign import bind_unit_identity
        facts,expected,process=self.context();facts['MainPID']='0'
        with self.assertRaisesRegex(ValueError,'Genuine process snapshot'):bind_unit_identity(facts,expected,None)
    def test_early_completed_genuine_startup_receipt_binds_nonzero_execmainpid(self):
        from scripts.run_p2_white_campaign import bind_unit_identity
        facts,expected,process=self.context();facts.update(MainPID='0',ControlGroup='')
        self.assertEqual(bind_unit_identity(facts,expected,process)['process']['birth'],'9981')
    def test_zero_execmainpid_cannot_invent_history(self):
        from scripts.run_p2_white_campaign import bind_unit_identity
        facts,expected,process=self.context();facts.update(MainPID='0',ExecMainPID='0')
        with self.assertRaisesRegex(ValueError,'nonzero ExecMainPID'):bind_unit_identity(facts,expected,process)
    def test_source_substring_or_extra_argument_refuses(self):
        from scripts.run_p2_white_campaign import bind_unit_identity
        for suffix in ['.foreign',' --repair']:
            facts,expected,process=self.context();facts['ExecStart']=facts['ExecStart'].replace('linux-controls28.py ;','linux-controls28.py'+suffix+' ;')
            with self.assertRaisesRegex(ValueError,'full argv changed'):bind_unit_identity(facts,expected,process,live=process)
    def test_changed_invocation_cgroup_and_pid_birth_refuse(self):
        from scripts.run_p2_white_campaign import bind_unit_identity
        facts,expected,process=self.context();prior=bind_unit_identity(facts,expected,process,live=process)
        for key,value in [('InvocationID','d'*32),('ControlGroup','/foreign')]:
            bad=dict(facts,**{key:value})
            with self.assertRaises(ValueError):bind_unit_identity(bad,expected,process,prior=prior,live=process)
        with self.assertRaisesRegex(ValueError,'identity changed'):bind_unit_identity(facts,expected,process,prior=prior,live=dict(process,birth='9999'))
    def test_actual_process_foreign_argv_or_membership_refuses(self):
        from scripts.run_p2_white_campaign import bind_unit_identity
        facts,expected,process=self.context()
        for bad in [dict(process,cgroup='/foreign'),dict(process,argv=['/usr/bin/python3','-c','print(1)']),dict(process,executable_sha256='f'*64)]:
            with self.assertRaisesRegex(ValueError,'binding mismatch'):bind_unit_identity(facts,expected,None,live=bad)
    def test_current_mainpid_requires_actual_live_kernel_snapshot(self):
        from scripts.run_p2_white_campaign import bind_unit_identity
        facts,expected,process=self.context()
        with self.assertRaisesRegex(ValueError,'live kernel'):bind_unit_identity(facts,expected,process)
    def test_malformed_execstart_and_multiple_commands_refuse(self):
        from scripts.run_p2_white_campaign import parse_execstart
        facts,expected,process=self.context()
        for text in ('{ path=/usr/bin/python3 }',facts['ExecStart']+' '+facts['ExecStart']):
            with self.assertRaises(ValueError):parse_execstart(text)



class DirectBudget42Controls(unittest.TestCase):
    def result(self,*args,**kwargs):return PhaseOutcome28Controls.result(self,*args,**kwargs)
    def test_fixed_modes(self):
        self.assertEqual(runner.phase_limit('positive'),240)
        for mode in ('ready','forced-down','paused-down','resume'):self.assertEqual(runner.phase_limit(mode),60)
        with self.assertRaises(ValueError):runner.phase_limit('human-unbounded')
    def test_positive_boundary_and_other_modes(self):
        self.assertIsNone(runner.phase_failure(self.result(elapsed=239.9),'positive'))
        self.assertIsNotNone(runner.phase_failure(self.result(elapsed=240.0),'positive'))
        for mode in ('ready','forced-down','paused-down','resume'):
            self.assertIsNone(runner.phase_failure(self.result(mode,elapsed=59.9),mode))
            self.assertIsNotNone(runner.phase_failure(self.result(mode,elapsed=60.0),mode))
    def test_arbitrary_key_budgets_and_resume240_refuse(self):
        for value in (0,59,61,180,181,241,float('inf')):
            with self.assertRaises(ValueError):runner.ShipKeyProtocol(None,lambda:0,phase_budget=value)
        with self.assertRaises(ValueError):runner.ShipKeyProtocol(None,lambda:0,resume=True,phase_budget=240)
    def test_positive_key_deadline_after_verify_no_publication(self):
        now=[239.9];events=[]
        class SlowVerify:
            def verify(self):now[0]=240.1
            def key(self,k,value):events.append((k,value))
        protocol=runner.ShipKeyProtocol(SlowVerify(),lambda:now[0],started=0,phase_budget=240)
        with self.assertRaises(ValueError):protocol.line('P2_WHITE_NATIVE_KEY_REQUEST seq=1 key=SHIFT_F10 actual_SDL_keyboard_required=1')
        self.assertFalse(any(value for _,value in events));self.assertTrue(protocol.closed)
    def test_legacy_key60_deadline_remains(self):
        events=[]
        class Backend:
            def verify(self):pass
            def key(self,k,value):events.append((k,value))
        protocol=runner.ShipKeyProtocol(Backend(),lambda:60,started=0)
        with self.assertRaises(ValueError):protocol.tick()
        self.assertFalse(any(value for _,value in events))
