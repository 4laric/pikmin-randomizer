"""Output-only candidate policy tests. Do not execute outside reviewed Linux recipe."""
import importlib.util
import json
import tempfile
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch,Mock
from contextlib import nullcontext

# Recipe test installation must provide the full root modules at this candidate root.
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('controller_candidate',ROOT/'scripts/play_pikmin2_cave_route.py')
controller=importlib.util.module_from_spec(spec);spec.loader.exec_module(controller)

class ControllerPolicy(unittest.TestCase):
    def state(self):
        return dict(phase='acquisition',visit=1,wfg_white_boundary=None,
                    entry=dict(health=1,squad=[[1,0]]*20))

    def test_fresh_requires_actual_baseline(self):
        self.assertTrue(controller.fresh_acquisition(self.state()))
        for change in (dict(visit=2),dict(phase='surface'),dict(wfg_white_boundary={'run':'proof'}),
                       dict(entry=dict(health=.5,squad=[[1,0]]*20)),
                       dict(entry=dict(health=1,squad=[[1,0]]*19)),
                       dict(entry=dict(health=1,squad=[[1,0]]*19+[[4,0]])),
                       dict(entry=dict(health=1,squad=[[1,0]]*19+[[1,1]]))):
            value=self.state();value.update(change)
            self.assertFalse(controller.fresh_acquisition(value))

    def test_linux_admission_cannot_be_env_only(self):
        with patch.object(controller,'is_windows',return_value=False):
            with self.assertRaises(RuntimeError):controller.require_controller_recipe(controller.ROOT)
            with self.assertRaises(RuntimeError):controller.runtime_capacity()
            with self.assertRaises(RuntimeError):controller.require_controller_recipe(controller.ROOT/'foreign','exe','session','run')

    def test_admission_uses_actual_copy_and_refusal_propagates(self):
        helper=types.ModuleType('scripts.pikmin2_cave_linux_runtime')
        calls=[]
        def refuse(*args):calls.append(args);raise ValueError('proof does not match actual copied ELF')
        helper.recipe_admission=refuse
        with patch.dict(sys.modules,{'scripts.pikmin2_cave_linux_runtime':helper}),patch.object(controller,'is_windows',return_value=False):
            with self.assertRaises(ValueError):controller.runtime_capacity('actual-copy','owned-session','owned-run')
        self.assertEqual(calls,[('actual-copy',controller.ROOT,'owned-session','owned-run')])

    def test_child_requires_admission_before_dialog_or_launch(self):
        helper=types.ModuleType('scripts.pikmin2_cave_linux_runtime')
        helper.recipe_admission=lambda *args:(_ for _ in ()).throw(ValueError('compile proof forbidden'))
        helper.launch_linux_fixture=lambda *args,**kwargs:self.fail('launch before proof')
        with patch.dict(sys.modules,{'scripts.pikmin2_cave_linux_runtime':helper}),patch.object(controller,'is_windows',return_value=False):
            with self.assertRaises(ValueError):controller.fixture_child('copy','run',[], 'marker',controller.ROOT,'session','surface','token','Enter cave','White Flower Garden')

    def test_windows_admission_remains_capacity_provider(self):
        with patch.object(controller,'is_windows',return_value=True),patch.object(controller,'windows_runtime_capacity',return_value='windows-proof') as provider:
            self.assertIsNone(controller.require_controller_recipe('workspace'))
            self.assertEqual(controller.runtime_capacity(),'windows-proof');provider.assert_called_once_with()

    def test_dialog_contract_requires_new_native_candidate(self):
        self.assertEqual(controller.linux_dialog('acquisition'),('leave','White Flower Garden'))
        self.assertEqual(controller.linux_dialog('floor1'),('descend','Emergence Cave'))
        self.assertEqual(controller.linux_dialog('floor2'),('leave','Emergence Cave'))
        with self.assertRaises(ValueError):controller.linux_dialog('arbitrary')

    def test_recovery_fault_is_linux_only(self):
        with patch.object(controller,'is_windows',return_value=True):
            with self.assertRaises(RuntimeError):controller.recover_boundary_child('not-opened')

    def test_recovery_fault_follows_real_state_write_only(self):
        import randomizer.cave_route as route_module
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);run=root/'runs'/'one';run.mkdir(parents=True)
            pending=root/'route-pending.json';pending.write_text(json.dumps(dict(run=str(run),revision=0,phase='surface',token='t')))
            (run/'run-result.json').write_text(json.dumps(dict(exit_code=42)))
            transfer=run/'p2-cave-surface-transfer.txt';transfer.write_text('actual unchanged native boundary')
            state=root/'route-state.json';state.write_text('old durable state')
            class FakeRoute:
                directory=root;pending_path=pending;state_path=state
                def load(self):return dict(revision=0,boundary_proofs=[])
                def recover(self,paths):
                    route_module.atomic_write(self.state_path,'new durable state')
                    self.pending_path.unlink()  # Must remain unreachable at the fixed fault.
            with patch.object(controller,'is_windows',return_value=False),patch.object(controller,'recovery_route',return_value=FakeRoute()),patch.object(controller,'require_controller_recipe') as admission,patch.object(controller,'live_runtime_paths',return_value=[]),patch.object(controller,'require_linux_phase_acceptance') as receipt_check,patch.object(controller.os,'_exit',side_effect=RuntimeError('fault87')) as exit_call:
                with self.assertRaisesRegex(RuntimeError,'fault87'):controller.recover_boundary_child(root)
                admission.assert_called_once_with(controller.ROOT,run/'nectar.exe',root,run)
                exit_call.assert_called_once_with(87)
                receipt_check.assert_called_once_with(run,'surface','t',controller.ROOT,root)
            self.assertEqual(state.read_text(),'new durable state')
            self.assertTrue(pending.exists())
            self.assertEqual(transfer.read_text(),'actual unchanged native boundary')

    def test_fault_rejects_non42_before_any_state_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);run=root/'run';run.mkdir()
            pending=root/'route-pending.json';pending.write_text(json.dumps(dict(run=str(run),revision=0,phase='surface',token='t')))
            (run/'run-result.json').write_text(json.dumps(dict(exit_code=0)))
            fake=types.SimpleNamespace(directory=root,pending_path=pending)
            with patch.object(controller,'is_windows',return_value=False),patch.object(controller,'recovery_route',return_value=fake),patch.object(controller,'require_controller_recipe'),patch.object(controller.os,'_exit') as exit_call:
                with self.assertRaises(ValueError):controller.recover_boundary_child(root)
                exit_call.assert_not_called()
            self.assertTrue(pending.exists())

    def test_fault_attempt_cannot_spawn_twice(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);run=root/'run';run.mkdir()
            pending=root/'route-pending.json';pending.write_text(json.dumps(dict(run=str(run),phase='surface',token='t')))
            (root/'recovery-once.json').write_text('{"status":"started"}')
            fake=types.SimpleNamespace(directory=root,pending_path=pending)
            with patch.object(controller,'require_controller_recipe'),patch.object(controller,'require_linux_phase_acceptance'),patch.object(controller.subprocess,'Popen') as spawn:
                with self.assertRaises(ValueError):controller.recover_fault_once(root,fake)
                spawn.assert_not_called()

    def test_raw42_does_not_override_modal_or_wrapper_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            run=Path(temporary).resolve();raw=run/'run-result.json';modal=run/'cave-linux-runtime-result.json'
            (run/'admission.json').write_text('fixed actual admission')
            proof=dict(pins=dict(FIXTURE_SOURCE_SHA256='fixed-source'),cgroup='/fixed')
            def record(flag):
                return dict(schema=1,phase='surface',token='t',run=str(run),exe=str(run/'nectar.exe'),
                    source_sha256='fixed-source',dialogs=[dict(event='os-return',pid=301,native_start='101')],raw_result_sha256=controller.sha(raw),
                    admission_sha256=controller.sha(run/'admission.json'),linux_route_phase_accepted=flag,gameplay_accepted=False)
            (run/'route-wrapper-cleanup.json').write_text(json.dumps(dict(schema=1,run=str(run),exe=str(run/'nectar.exe'),source_sha256='fixed-source',wrapper_exit=0,cleanup_complete=True,error=None,cleanup_errors=[],
                wrapper=dict(pid=300,pgid=300,sid=300,start='100',exe=str(Path(sys.executable).resolve()),cwd=str(controller.ROOT.resolve()),cgroup='/fixed'),
                native=dict(pid=301,ppid=300,pgid=301,sid=301,start='101',exe=str(run/'nectar.exe'),cwd=str(run),cgroup='/fixed'))))
            with patch.object(controller,'require_controller_recipe',return_value=proof):
                for wrapper,flag,code,timeout in ((1,True,42,False),(0,False,42,False),(0,True,86,False),(0,True,42,True)):
                    raw.write_text(json.dumps(dict(exit_code=code,passed=False,timed_out=timeout,pid=301,owned_process_group=301)))
                    modal.write_text(json.dumps(record(flag)));before=raw.read_bytes()
                    with self.assertRaises(RuntimeError):controller.require_linux_phase_acceptance(run,'surface','t',controller.ROOT,run,wrapper)
                    self.assertEqual(raw.read_bytes(),before)
                raw.write_text(json.dumps(dict(exit_code=42,passed=False,timed_out=False,pid=301,owned_process_group=301)))
                for key,value in (('token','other'),('phase','floor1'),('source_sha256','foreign'),('raw_result_sha256','tampered'),('admission_sha256','tampered'),('run','foreign'),('exe','foreign')):
                    changed=record(True);changed[key]=value;modal.write_text(json.dumps(changed))
                    with self.assertRaises(RuntimeError):controller.require_linux_phase_acceptance(run,'surface','t',controller.ROOT,run,0)
                modal.write_text(json.dumps(record(False)))
                pending=run/'route-pending.json';pending.write_text(json.dumps(dict(run=str(run),phase='surface',token='t')))
                transfer=run/'p2-cave-surface-transfer.txt';transfer.write_text('actual preserved native42 boundary')
                fake=types.SimpleNamespace(directory=run,pending_path=pending)
                before_pending=pending.read_bytes();before_transfer=transfer.read_bytes()
                with self.assertRaises(RuntimeError):controller.require_linux_pending_boundary(fake)
                self.assertEqual(pending.read_bytes(),before_pending);self.assertEqual(transfer.read_bytes(),before_transfer)
                modal.write_text(json.dumps(record(True)))
                cleanup_path=run/'route-wrapper-cleanup.json';original=cleanup_path.read_bytes();data=json.loads(original)
                for key,value in (('wrapper_exit',1),('cleanup_complete',False),('source_sha256','foreign')):
                    changed=dict(data,**{key:value});cleanup_path.write_text(json.dumps(changed))
                    with self.assertRaises(RuntimeError):controller.require_linux_phase_acceptance(run,'surface','t',controller.ROOT,run)
                changed=dict(data,native=dict(data['native'],start='999'));cleanup_path.write_text(json.dumps(changed))
                with self.assertRaises(RuntimeError):controller.require_linux_phase_acceptance(run,'surface','t',controller.ROOT,run)
                cleanup_path.write_bytes(original);before=raw.read_bytes()
                self.assertIs(controller.require_linux_phase_acceptance(run,'surface','t',controller.ROOT,run,0)['passed'],False)
                self.assertEqual(raw.read_bytes(),before)

    def test_recovery_requires_new_durable_history_api(self):
        for value in (dict(revision=0),dict(revision=1,boundary_proofs=[]),dict(revision=0,boundary_proofs={})):
            fake=types.SimpleNamespace(load=lambda:value)
            with self.assertRaises(ValueError):controller.durable_route_state(fake)
        state=dict(revision=1,boundary_proofs=[{'actual':'verified by Route.load'}])
        fake=types.SimpleNamespace(load=lambda:state)
        self.assertIs(controller.durable_route_state(fake),state)
        fake=types.SimpleNamespace(load=lambda:(_ for _ in ()).throw(ValueError('changed full bud transfer')))
        with self.assertRaisesRegex(ValueError,'changed full bud transfer'):controller.durable_route_state(fake)

    def test_wrapper_timeout_retires_owned_native_then_wrapper_before_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();run=root/'run';run.mkdir();(run/'native.log').write_text('native started')
            child=Mock(pid=300,returncode=-9);child.poll.return_value=None
            child.wait.side_effect=[controller.subprocess.TimeoutExpired('fixed-wrapper',75),0]
            wrapper=dict(pid=300,start='100',cgroup='/fixed');native=dict(pid=301,start='101',cgroup='/fixed')
            retired=[]
            with patch.object(controller,'exclusive',return_value=nullcontext()),patch.object(controller,'runtime_capacity',return_value=dict(cgroup='/fixed',pins=dict(FIXTURE_SOURCE_SHA256='fixed-source'))),patch.object(controller.subprocess,'Popen',return_value=child) as spawn,patch.object(controller,'owned_identity',return_value=wrapper),patch.object(controller,'discover_owned_native',return_value=native),patch.object(controller,'cleanup_owned_group',side_effect=lambda value:retired.append(value['pid']) or True):
                with self.assertRaises(controller.subprocess.TimeoutExpired):controller.launch_route_wrapper(['fixed'],root,{},None,run,root)
                self.assertIs(spawn.call_args.kwargs['start_new_session'],True)
            self.assertEqual(retired,[301,300])
            receipt=json.loads((run/'route-wrapper-cleanup.json').read_text())
            self.assertTrue(receipt['cleanup_complete']);self.assertTrue(receipt['error'])

    def test_native_cleanup_refusal_still_retires_wrapper_without_guessed_kill(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();run=root/'run';run.mkdir();(run/'native.log').write_text('native started')
            child=Mock(pid=300,returncode=-9);child.poll.return_value=None;child.wait.side_effect=[controller.subprocess.TimeoutExpired('fixed',75),0]
            wrapper=dict(pid=300,start='100',cgroup='/fixed');native=dict(pid=301,start='101',cgroup='/fixed')
            retired=[]
            def retire(value):
                retired.append(value['pid'])
                if value['pid']==301:raise ValueError('PID start changed')
                return True
            with patch.object(controller,'exclusive',return_value=nullcontext()),patch.object(controller,'runtime_capacity',return_value=dict(cgroup='/fixed',pins=dict(FIXTURE_SOURCE_SHA256='fixed-source'))),patch.object(controller.subprocess,'Popen',return_value=child),patch.object(controller,'owned_identity',return_value=wrapper),patch.object(controller,'discover_owned_native',return_value=native),patch.object(controller,'cleanup_owned_group',side_effect=retire),patch.object(controller.os,'killpg') as signal:
                with self.assertRaisesRegex(RuntimeError,'cleanup failed'):controller.launch_route_wrapper(['fixed'],root,{},None,run,root)
                signal.assert_not_called()
            self.assertEqual(retired,[301,300]);self.assertFalse(json.loads((run/'route-wrapper-cleanup.json').read_text())['cleanup_complete'])

    def test_leaderless_or_reused_group_is_never_signalled(self):
        owner=dict(pid=300,start='100',pgid=300,sid=300,cgroup='/fixed',exe='/copy',cwd='/run')
        fields=['S','1','300','300']+['0']*15+['200']
        root=types.SimpleNamespace(iterdir=lambda:[Path('/proc/301')])
        descendant=dict(owner,pid=301,start='200',ppid=1,state='S')
        with patch.object(controller,'Path',return_value=root),patch.object(controller,'proc_fields',return_value=fields),patch.object(controller,'proc_identity',return_value=descendant),patch.object(controller.os,'killpg') as signal:
            with self.assertRaisesRegex(ValueError,'original PID/start leader'):controller.cleanup_owned_group(owner)
            signal.assert_not_called()
        root=types.SimpleNamespace(iterdir=lambda:[Path('/proc/300')])
        reused=dict(owner,start='200',ppid=1,state='S')
        with patch.object(controller,'Path',return_value=root),patch.object(controller,'proc_fields',return_value=fields),patch.object(controller,'proc_identity',return_value=reused),patch.object(controller.os,'killpg') as signal:
            with self.assertRaisesRegex(ValueError,'PID reused'):controller.cleanup_owned_group(owner)
            signal.assert_not_called()

    def test_linux_budget_is_global_first_reentry_milestone(self):
        phases=('surface','acquisition','floor1','floor2','surface','acquisition')
        visits=(0,1,1,1,1,2)
        for revision in range(6):
            self.assertEqual(controller.linux_phase_budget(5,dict(revision=revision,phase=phases[revision],visit=visits[revision])),5-revision)
        for maximum in (4,6,8):
            with self.assertRaises(ValueError):controller.linux_phase_budget(maximum,dict(revision=0,phase='surface',visit=0))
        with self.assertRaises(ValueError):controller.linux_phase_budget(5,dict(revision=6,phase='floor1',visit=2))
        with self.assertRaises(ValueError):controller.linux_phase_budget(5,dict(revision=5,phase='surface',visit=1))

    def test_committed_rejected_receipt_refuses_before_next_phase(self):
        state=dict(revision=1,boundary_proofs=[dict(run='/original/run',phase='surface',token='original')])
        fake=types.SimpleNamespace(directory=Path('/session'),load=lambda:state)
        with patch.object(controller,'require_linux_phase_acceptance',side_effect=RuntimeError('committed helper refused')) as accept:
            with self.assertRaisesRegex(RuntimeError,'committed helper refused'):controller.require_linux_committed_boundaries(fake)
            accept.assert_called_once_with(Path('/original/run'),'surface','original',controller.ROOT,fake.directory)

    def test_proc_scan_skips_foreign_uid_and_cgroup_before_exe_probe(self):
        root=types.SimpleNamespace(iterdir=lambda:[Path('/proc/1'),Path('/proc/2'),Path('/proc/3')])
        calls=[]
        def group(pid):return '/owned' if pid in ('self',3) else '/foreign'
        def exe(pid):calls.append(pid);return '/owned/native'
        with patch.object(controller,'is_windows',return_value=False),patch.object(controller.os,'getuid',return_value=1001,create=True),patch.object(controller,'Path',return_value=root),patch.object(controller,'process_uid',side_effect=lambda pid:0 if pid==1 else 1001),patch.object(controller,'process_cgroup',side_effect=group),patch.object(controller,'process_executable',side_effect=exe):
            self.assertEqual(controller.live_runtime_paths(),['/owned/native'])
        self.assertEqual(calls,[3])

    def test_owned_proc_unreadability_refuses_instead_of_ignoring_pid(self):
        root=types.SimpleNamespace(iterdir=lambda:[Path('/proc/3')])
        with patch.object(controller,'is_windows',return_value=False),patch.object(controller.os,'getuid',return_value=1001,create=True),patch.object(controller,'Path',return_value=root),patch.object(controller,'process_uid',return_value=1001),patch.object(controller,'process_cgroup',return_value='/owned'),patch.object(controller,'process_executable',side_effect=PermissionError('owned exe unreadable')):
            with self.assertRaisesRegex(RuntimeError,'owned Linux runtime'):controller.live_runtime_paths()

    def test_private_xvfb_mapping_override_follows_agent_preferences(self):
        env=dict(PIKMIN_RANDOMIZER_TEST_VISIBLE='1',SDL_VIDEODRIVER='dummy')
        helper=types.ModuleType('scripts.pikmin2_cave_linux_runtime');helper.phase_environment=lambda values,*args,**kwargs:dict(values)
        with patch('randomizer.test_run.watch_enabled',return_value=False):controller.apply_test_run_env(env,controller.ROOT)
        self.assertNotIn('PIKMIN_RANDOMIZER_TEST_VISIBLE',env)
        with patch.dict(sys.modules,{'scripts.pikmin2_cave_linux_runtime':helper}):mapped=controller.linux_phase_environment(env,'surface')
        self.assertEqual(mapped['PIKMIN_RANDOMIZER_TEST_VISIBLE'],'1')
        self.assertEqual(mapped['PIKMIN_RANDOMIZER_TEST_BACKGROUND'],'1')
        self.assertEqual(mapped['SDL_VIDEODRIVER'],'x11')

    def test_linux_settings_are_exact_fresh_pending_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            run=Path(temporary);name=controller.stage_linux_settings(run)
            self.assertEqual(name,'pikmin_settings.conf')
            expected=b'debugKeys=0\nwindowWidth=960\nwindowHeight=540\ndisplayMode=0\n'
            self.assertEqual((run/name).read_bytes(),expected)
            with self.assertRaises(FileExistsError):controller.stage_linux_settings(run)
            self.assertEqual((run/name).read_bytes(),expected)

    def test_linux_settings_refuse_link_without_touching_original(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);run=root/'run';run.mkdir();original=root/'original.conf';original.write_bytes(b'original preserved')
            linked=run/'pikmin_settings.conf';linked.symlink_to(original)
            with self.assertRaises(FileExistsError):controller.stage_linux_settings(run)
            self.assertTrue(linked.is_symlink());self.assertEqual(original.read_bytes(),b'original preserved')

if __name__=='__main__':unittest.main()
