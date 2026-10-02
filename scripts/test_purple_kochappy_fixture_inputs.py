"""Prelaunch refusal tests only; fake bytes never stand in for a game runtime."""
import hashlib,tempfile,unittest
from pathlib import Path
from scripts.run_pikmin2_purple_kochappy import DLLS,runtime_dependencies,controlled_environment

class Inputs(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);self.source=self.base/'package';self.local=self.base/'consumer'
        self.source.mkdir();self.local.mkdir();self.exe=self.local/'fixture.exe';self.exe.write_bytes(b'not executable, test only')
        self.pin='e'*40;rows=[]
        for name in DLLS:
            payload=('test only '+name).encode();digest=hashlib.sha256(payload).hexdigest()
            (self.source/name).write_bytes(payload);(self.local/name).write_bytes(payload);rows.append(digest+' *./'+name)
        (self.source/'sha256.txt').write_text('\n'.join(rows)+'\n')
        (self.source/'BUILD_INFO.txt').write_text('commit '+self.pin+'\n')
    def test_matching_all_four(self):
        r=runtime_dependencies(self.exe,self.source,self.pin);self.assertEqual(set(r['dlls']),set(DLLS))
    def test_source_missing(self):
        (self.source/'SDL2.dll').unlink()
        with self.assertRaisesRegex(ValueError,'CI runtime DLL'):runtime_dependencies(self.exe,self.source,self.pin)
    def test_source_conflict(self):
        (self.source/'libgcc_s_seh-1.dll').write_bytes(b'wrong')
        with self.assertRaisesRegex(ValueError,'CI runtime DLL'):runtime_dependencies(self.exe,self.source,self.pin)
    def test_exe_local_missing(self):
        (self.local/'SDL2.dll').unlink()
        with self.assertRaisesRegex(ValueError,'executable-local DLL'):runtime_dependencies(self.exe,self.source,self.pin)
    def test_exe_local_conflict(self):
        (self.local/'libstdc++-6.dll').write_bytes(b'wrong')
        with self.assertRaisesRegex(ValueError,'executable-local DLL'):runtime_dependencies(self.exe,self.source,self.pin)
    def test_manifest_omits_dll(self):
        p=self.source/'sha256.txt';p.write_text('\n'.join(p.read_text().splitlines()[:-1]))
        with self.assertRaisesRegex(ValueError,'manifest missing'):runtime_dependencies(self.exe,self.source,self.pin)
    def test_pin_mismatch(self):
        with self.assertRaisesRegex(ValueError,'source pin'):runtime_dependencies(self.exe,self.source,'0'*40)
    def test_poison_environment(self):
        ambient={'PIKMIN_OTHER':'poison','P2_OTHER':'poison','COOP_FAKE':'poison','p2_lowercase':'poison','NECTAR_SAVE_DIR':'shared','NECTAR_SETTINGS_PATH':'shared','PATH':'system','SystemRoot':'windows'}
        env=controlled_environment(ambient,self.exe,self.source,self.base/'private-save','positive')
        self.assertFalse(any(k in env for k in ('PIKMIN_OTHER','P2_OTHER','COOP_FAKE','p2_lowercase','NECTAR_SETTINGS_PATH')))
        self.assertEqual(env['PIKMIN_P2_TEST_START_DAY'],'5');self.assertEqual(env['PIKMIN_P2_ROOM_WINDOW'],'960x540')
        self.assertEqual(env['SystemRoot'],'windows');self.assertEqual(env['NECTAR_SAVE_DIR'],str((self.base/'private-save').resolve()))
        self.assertNotIn('P2_PURPLE_KOCHAPPY_FORCE_DOWN',env)
    def test_only_selected_negative_flag(self):
        e=controlled_environment({'P2_PURPLE_KOCHAPPY_FORCE_DOWN':'ambient'},self.exe,self.source,self.base/'save','paused-down')
        self.assertNotIn('P2_PURPLE_KOCHAPPY_FORCE_DOWN',e);self.assertEqual(e['P2_PURPLE_KOCHAPPY_PAUSED_DOWN'],'1')

class LinuxInputs(unittest.TestCase):
    """Mocked refusal boundaries only; these responses are never broker evidence."""
    def setUp(self):
        import copy
        from unittest.mock import patch
        import scripts.run_pikmin2_purple_kochappy as runner
        self.runner=runner;self.patch=patch;self.copy=copy
        self.proof={'exe_sha256':'a'*64,'target':'pikmin_ci_fixture_purple_kochappy','source':'tools/p2_purple_kochappy_runtime.cpp','pins':{'PIKMIN_SHA':'b'*40,'NATIVE_SHA':'c'*40,'FIXTURE_SOURCE_SHA256':'d'*64,'FIXTURE_SUITE':'purple-kochappy-runtime'}}
        self.dependencies={'executable':{'sha256':'a'*64}}
    def inputs(self):
        return self.runner.linux_runtime_inputs('unused exe','unused root','unused session','unused run',{},'b'*40,'c'*40,'d'*64)
    def test_compile_proof_cannot_authorize_runtime(self):
        self.proof['pins']['FIXTURE_SUITE']='purple-kochappy-build'
        with self.patch.object(self.runner,'runtime_evidence',return_value=self.dependencies),self.patch.object(self.runner,'linux_admission',return_value=self.proof):
            with self.assertRaisesRegex(ValueError,'runtime recipe'):self.inputs()
    def test_actual_broker_refusal_propagates(self):
        with self.patch.object(self.runner,'runtime_evidence',return_value=self.dependencies),self.patch.object(self.runner,'linux_admission',side_effect=ValueError('actual broker refusal')):
            with self.assertRaisesRegex(ValueError,'actual broker refusal'):self.inputs()
    def test_dependency_refusal_precedes_admission(self):
        with self.patch.object(self.runner,'runtime_evidence',side_effect=ValueError('ELF dependency refusal')),self.patch.object(self.runner,'linux_admission') as admission:
            with self.assertRaisesRegex(ValueError,'ELF dependency refusal'):self.inputs()
            admission.assert_not_called()
    def test_source_target_and_executable_drift_rejected(self):
        for field in ('exe_sha256','target','source'):
            with self.subTest(field=field):
                p=self.copy.deepcopy(self.proof);p[field]='wrong'
                with self.patch.object(self.runner,'runtime_evidence',return_value=self.dependencies),self.patch.object(self.runner,'linux_admission',return_value=p):
                    with self.assertRaises(ValueError):self.inputs()
        for field in ('PIKMIN_SHA','NATIVE_SHA','FIXTURE_SOURCE_SHA256'):
            with self.subTest(pin=field):
                p=self.copy.deepcopy(self.proof);p['pins'][field]='e'*len(p['pins'][field])
                with self.patch.object(self.runner,'runtime_evidence',return_value=self.dependencies),self.patch.object(self.runner,'linux_admission',return_value=p):
                    with self.assertRaisesRegex(ValueError,'source pins'):self.inputs()
    def test_posix_environment_path_and_all_prefix_filtering(self):
        with self.patch.object(self.runner.os,'pathsep',':'):
            e=self.runner.controlled_environment({'Path':'/usr/bin:/bin','p2_other':'poison','NECTAR_SETTINGS_PATH':'poison'},Path('fixture'),None,Path('private-save'),'positive')
        self.assertTrue(e['PATH'].endswith(':/usr/bin:/bin'));self.assertNotIn('None',e['PATH'])
        self.assertNotIn('p2_other',e);self.assertNotIn('NECTAR_SETTINGS_PATH',e)
        self.assertEqual(e['PIKMIN_P2_TEST_START_DAY'],'5');self.assertEqual(e['PIKMIN_P2_ROOM_WINDOW'],'960x540')

class DevelopmentInputs(unittest.TestCase):
    def setUp(self):
        from unittest.mock import patch
        import scripts.run_pikmin2_purple_kochappy as runner
        self.runner=runner;self.patch=patch
        self.dependencies={'platform':'linux','executable':{'path':'unused exe','sha256':'a'*64}}
        self.context={'mode':'development','controller_proof_used':False,'capacity':{'used_percent':10}}
    def inputs(self,flag=True):
        return self.runner.linux_runtime_inputs('unused exe','unused root','unused session','unused run',{},'b'*40,'c'*40,'d'*64,development_launch=flag)
    def test_explicit_development_checks_runtime_and_capacity_without_controller(self):
        with self.patch.object(self.runner,'runtime_evidence',return_value=self.dependencies) as elf,self.patch.object(self.runner,'linux_development_context',return_value=self.context) as context,self.patch.object(self.runner,'linux_admission') as admission:
            self.assertEqual(self.inputs(),(self.dependencies,self.context))
            elf.assert_called_once();context.assert_called_once_with('unused exe','unused root','unused session','unused run',self.dependencies);admission.assert_not_called()
    def test_dependency_failure_precedes_development_context(self):
        with self.patch.object(self.runner,'runtime_evidence',side_effect=ValueError('ELF failed')),self.patch.object(self.runner,'linux_development_context') as context,self.patch.object(self.runner,'linux_admission') as admission:
            with self.assertRaisesRegex(ValueError,'ELF failed'):self.inputs()
            context.assert_not_called();admission.assert_not_called()
    def test_capacity_and_private_context_refusals_propagate(self):
        for reason in ('95% physical RAM ceiling','private output session/run','Executable changed'):
            with self.subTest(reason=reason),self.patch.object(self.runner,'runtime_evidence',return_value=self.dependencies),self.patch.object(self.runner,'linux_development_context',side_effect=ValueError(reason)),self.patch.object(self.runner,'linux_admission') as admission:
                with self.assertRaises(ValueError):self.inputs()
                admission.assert_not_called()
    def test_non_boolean_opt_in_refused_before_inspection(self):
        with self.patch.object(self.runner,'runtime_evidence') as elf:
            for flag in (1,0,'true',None,[]):
                with self.subTest(flag=flag),self.assertRaises(TypeError):self.inputs(flag)
            elf.assert_not_called()
    def test_plan_records_development_without_launching(self):
        import json,sys
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);exe=base/'fixture';exe.write_bytes(b'non executable fixture bytes')
            native=base/'native';(native/'tools').mkdir(parents=True);(native/'tools/p2_purple_kochappy_runtime.cpp').write_text('test source')
            output=base/'output';run=output/'private';run.mkdir(parents=True);(run/'purple-kochappy-inputs.json').write_text('{}')
            argv=['runner']
            for name in ('assets','bundle','red-bank','purple-bank','motion','pod'):argv+=['--'+name,str(base)]
            argv+=['--exe',str(exe),'--output',str(output),'--native',str(native),'--exe-sha256',self.runner.sha(exe),'--root-sha','b'*40,'--native-sha','b'*40,'--mode','positive','--plan','--development-launch']
            def git(args,**kw):return 'b'*40+'\n' if 'rev-parse' in args else ''
            with self.patch.object(sys,'argv',argv),self.patch.object(self.runner.subprocess,'check_output',side_effect=git),self.patch.object(self.runner,'is_windows',return_value=False),self.patch.object(self.runner,'prepare',return_value=run),self.patch.object(self.runner,'runtime_evidence',return_value=self.dependencies),self.patch.object(self.runner,'linux_development_context',return_value=self.context),self.patch.object(self.runner,'linux_admission') as admission,self.patch.object(self.runner,'supervise') as launch:
                self.assertEqual(self.runner.main(),0);launch.assert_not_called();admission.assert_not_called()
            inputs=json.loads((run/'acceptance-inputs.json').read_text());self.assertIsNone(inputs['broker_admission']);self.assertEqual(inputs['development_runtime'],self.context)
            self.assertFalse((run/'admission.json').exists());self.assertTrue((run/'development-runtime.json').is_file())

if __name__=='__main__':unittest.main()
