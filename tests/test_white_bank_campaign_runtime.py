import importlib.util,sys,unittest,tempfile,struct,hashlib
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import run_p2_white_bank_campaign as runner
class FakeKeys:
    def __init__(self):self.calls=[];self.valid=True;self.release_error=False
    def verify(self):
        if not self.valid:raise ValueError('foreign/missing window')
        self.calls.append(('verify',))
    def key(self,key,pressed):
        self.calls.append((key,pressed))
        if self.release_error and key=='F10' and not pressed:raise ValueError('release error')

class ServiceContainmentControls(unittest.TestCase):
    def test_finite_manager_duration_formats(self):
        self.assertEqual(runner.manager_duration_seconds('6min'),360)
        self.assertEqual(runner.manager_duration_seconds('1min'),60)
        self.assertEqual(runner.manager_duration_seconds('1min 500ms'),60.5)
        for value in ('infinity','6min garbage','-60s','','60'):
            with self.assertRaises(ValueError):runner.manager_duration_seconds(value)

    def service(self,mode='resume',**changes):
        import os,types
        values={'MainPID':str(os.getpid()),'InvocationID':'a'*32,
            'ControlGroup':'/user.slice/user-1000.slice/user@1000.service/app.slice/white-bank-test.service',
            'KillMode':'control-group','KillSignal':'9','RuntimeMaxUSec':'1min'}
        values.update(changes)
        response=types.SimpleNamespace(stdout='\n'.join(k+'='+v for k,v in values.items()))
        actual='/user.slice/user-1000.slice/user@1000.service/app.slice/white-bank-test.service'
        with patch.object(runner.sys,'platform','linux'),patch.dict(os.environ,
            {'WHITE_BANK_UNIT':'white-bank-test.service','INVOCATION_ID':'a'*32}),\
            patch('subprocess.run',return_value=response),patch.object(Path,'read_text',return_value='0::'+actual+'\n'):
            return runner.require_owned_service(mode)

    def test_actual_own_unit_and_profile_required(self):
        self.assertEqual(self.service()['KillMode'],'control-group')
        self.assertEqual(self.service('positive',RuntimeMaxUSec='6min')['RuntimeMaxUSec'],'6min')
        for changes in ({'MainPID':'0'},{'MainPID':'1'},{'InvocationID':'b'*32},
            {'ControlGroup':'/user.slice/foreign.service'},{'KillMode':'process'},
            {'KillSignal':'15'},{'RuntimeMaxUSec':'infinity'},{'RuntimeMaxUSec':'6min'}):
            with self.assertRaises(ValueError):self.service(**changes)

    def test_profile_and_mode_fail_closed(self):
        self.assertEqual(runner.phase_limit('positive'),360)
        for mode in ('ready','forced-down','paused-down','resume'):
            self.assertEqual(runner.phase_limit(mode),60)
        with self.assertRaises(ValueError):runner.phase_limit('human')

    def test_inner_cleanup_and_guard_exit_remain_strict(self):
        clean={'mode':'forced-down','exit_code':86,'error':None,'cleanup_errors':[],
            'timed_out':False,'launched':True,'elapsed':5}
        self.assertIsNone(runner.phase_failure(clean,'forced-down'))
        for changes in ({'exit_code':0},{'timed_out':True},{'cleanup_errors':['unreaped']},
                        {'error':'helper died'},{'elapsed':60},{'launched':False}):
            self.assertIsNotNone(runner.phase_failure(dict(clean,**changes),'forced-down'))

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
        self.config='P2_WHITE_TREASURE_CAMPAIGN_1 1 1465143809 178195544 '+' '.join([str(i)*64 for i in (1,2,3)])
        (self.directory/'p2-white-treasure-campaign.txt').write_text(self.config)
        self.identity=hashlib.sha256(' '.join(self.config.split()[1:]).encode()).hexdigest()
        self.fields=['PIKMIN_CAMPAIGN_WHITE_TREASURE_1','a'*64,'1','0','0','0',
                     '0','0','0','15','0','0','3','1','1464357891','5','1','1464357892','5','1','1464357893','5',self.identity,'1']
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





if __name__=="__main__":unittest.main(verbosity=2)
