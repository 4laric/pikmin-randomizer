"""Pure policy checks; no SDL process, OS input, or gameplay acceptance."""
import copy
import ctypes
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import pikmin2_cave_linux_runtime as runtime


TOKEN = 'a' * 32


def begin():
    return dict(event='begin', sequence=1, pid=1234, phase='floor',
                token=TOKEN, action='leave', title='White Flower Garden',
                cave='forest_2', floor=1, video_driver='x11', parent_x11_window=11,
                button_disabled_state_supported=False, buttons=[
                    dict(id=0, flags=2, text='Stay', return_default=False, escape_default=True),
                    dict(id=1, flags=1, text='Leave cave', return_default=True, escape_default=False)])


def windows():
    return [dict(window=11, pid=1234, owner_pid=1234, mapped=True, transient_for=0, title='Game', dialog=False, modal=False),
            dict(window=22, pid=None, owner_pid=1235, mapped=True, transient_for=11,
                 title='White Flower Garden', dialog=True, modal=True)]


class Backend:
    library_hashes = {}

    def __init__(self):
        self.items = []
        self.keys = []

    def windows(self):
        return copy.deepcopy(self.items)

    def press_return(self, window):
        self.keys.append(window)


class TitlePropertyTests(unittest.TestCase):
    def backend(self,properties):
        backend=object.__new__(runtime.X11Input);backend.display=1
        atoms={name:i+1 for i,name in enumerate(('_NET_WM_NAME','WM_NAME','UTF8_STRING','UTF-8','STRING','OTHER'))}
        backend.atom=lambda name:atoms[name]
        class X:
            def __init__(self):self.buffers=[];self.queries=[];self.freed=0
            def XGetWindowProperty(self,display,window,prop,start,length,delete,requested,actual,fmt,count,after,data):
                self.queries.append(prop)
                self.limit=length
                p=properties.get(prop,{})
                raw=p.get('raw',b'')
                actual._obj.value=atoms[p['type']] if p.get('type') else 0
                fmt._obj.value=p.get('format',8 if p.get('type') else 0)
                count._obj.value=p.get('count',len(raw));after._obj.value=p.get('after',0)
                if p.get('allocate',True):
                    buffer=ctypes.create_string_buffer(raw);self.buffers.append(buffer);data._obj.value=ctypes.addressof(buffer)
                return p.get('rc',0)
            def XFree(self,data):self.freed+=1
        backend.x=X();return backend,atoms

    def test_standard_utf8_title_preferred_with_bounded_complete_read(self):
        b,a=self.backend({1:dict(type='UTF8_STRING',raw='Emergence Cave é'.encode()),2:dict(type='OTHER',raw=b'ignored')})
        self.assertEqual(b.window_title(22),('Emergence Cave é','_NET_WM_NAME','UTF8_STRING'))
        self.assertEqual(b.x.queries,[a['_NET_WM_NAME']]);self.assertEqual(b.x.limit,1024);self.assertEqual(b.x.freed,1)
        b,a=self.backend({1:dict(type='UTF8_STRING',raw=b'x'*4096)})
        self.assertEqual(len(b.window_title(22)[0]),4096)

    def test_only_explicit_legacy_encodings_used_when_modern_absent(self):
        for encoding,raw,text in [('UTF-8',b'Emergence Cave','Emergence Cave'),('UTF8_STRING','é'.encode(),'é'),('STRING',b'caf\xe9','café')]:
            with self.subTest(encoding=encoding):
                b,a=self.backend({2:dict(type=encoding,raw=raw)})
                self.assertEqual(b.window_title(22),(text,'WM_NAME',encoding));self.assertEqual(b.x.freed,2)
        b,a=self.backend({});self.assertEqual(b.window_title(22),('','absent','absent'))

    def test_malformed_modern_title_refuses_without_fallback(self):
        bad=[dict(type='STRING',raw=b'Emergence Cave'),dict(type='UTF8_STRING',raw=b'\xff'),
             dict(type='UTF8_STRING',raw=b'A\0B'),dict(type='UTF8_STRING',raw=b'A',after=1),
             dict(type='UTF8_STRING',raw=b'A',format=16),dict(type='UTF8_STRING',raw=b'A',count=4097),
             dict(type='UTF8_STRING',raw=b'A',allocate=False),dict(count=1),dict(rc=1)]
        for prop in bad:
            with self.subTest(prop=prop):
                b,a=self.backend({1:prop,2:dict(type='STRING',raw=b'Emergence Cave')})
                with self.assertRaises(ValueError):b.window_title(22)
                self.assertEqual(b.x.queries,[a['_NET_WM_NAME']]);self.assertEqual(b.x.freed,0 if prop.get('allocate') is False else 1)

    def test_wrong_or_empty_decoded_title_still_refuses_exact_modal_match(self):
        for text in ('Other cave',''):
            b,a=self.backend({1:dict(type='UTF8_STRING',raw=text.encode())})
            items=windows();items[1]['title']=b.window_title(22)[0]
            with self.assertRaises(ValueError):runtime.matching_modal(items,begin(),set())
        b,a=self.backend({2:dict(type='OTHER',raw=b'Emergence Cave')})
        with self.assertRaises(ValueError):b.window_title(22)


class CaveLinuxRuntimePolicyTests(unittest.TestCase):
    def test_each_phase_clears_all_presence_based_switches(self):
        inherited = dict(zip(runtime.ENV_KEYS, ['', '1', 'false'])) | {'KEEP': 'yes'}
        for phase in runtime.PHASES:
            env = runtime.phase_environment(inherited, phase, guard_negative=phase == 'guard')
            self.assertEqual(env['KEEP'], 'yes')
            self.assertNotIn('P2_CAVE_ROUTE_ACQUIRE', env)
            self.assertEqual(set(env) - {'KEEP'},
                             {'P2_CAVE_ROUTE_FORCE_CAPTAIN_DOWN'} if phase == 'guard' else {'P2_CAVE_ROUTE_FULL_PARTY'})
        self.assertEqual(runtime.phase_environment(inherited, 'acquisition', fresh_acquisition=True)['P2_CAVE_ROUTE_ACQUIRE'], '1')
        with self.assertRaises(ValueError):
            runtime.phase_environment(inherited, 'surface', fresh_acquisition=True)

    def test_begin_requires_ready_token_actual_parent_and_default(self):
        checks = [('token', 'b' * 32), ('parent_x11_window', 0),
                  ('video_driver', 'dummy'), ('button_disabled_state_supported', True)]
        for key, value in checks:
            record = begin(); record[key] = value
            with self.assertRaises(ValueError):
                runtime.validate_begin(record, phase='acquisition', token=TOKEN, action='leave', title='White Flower Garden', ready=True)
        record = begin(); record['buttons'][1]['return_default'] = False
        with self.assertRaises(ValueError):
            runtime.validate_begin(record, phase='acquisition', token=TOKEN, action='leave', title='White Flower Garden', ready=True)
        with self.assertRaises(ValueError):
            runtime.validate_begin(begin(), phase='acquisition', token=TOKEN, action='leave', title='White Flower Garden', ready=False)

    def test_wrong_cave_floor_action_phase_and_launch_switches_refuse(self):
        for key,value in [('cave','forest_1'),('floor',2)]:
            record=dict(begin(),**{key:value})
            with self.assertRaises(ValueError):
                runtime.validate_begin(record,phase='acquisition',token=TOKEN,action='leave',title='White Flower Garden',ready=True)
        for env in ({}, {'P2_CAVE_ROUTE_FULL_PARTY':'0'}, {'P2_CAVE_ROUTE_FULL_PARTY':'1','P2_CAVE_ROUTE_FORCE_CAPTAIN_DOWN':''},
                    {'P2_CAVE_ROUTE_FULL_PARTY':'1','P2_CAVE_ROUTE_ACQUIRE':'1'}):
            with self.assertRaises(ValueError):runtime.validate_launch_environment(env,'floor1',Path('/unused'),TOKEN)
        runtime.validate_launch_environment({'P2_CAVE_ROUTE_FULL_PARTY':'1'},'floor1',Path('/unused'),TOKEN)
        with self.assertRaises(ValueError):runtime.validate_launch_environment({'P2_CAVE_ROUTE_FORCE_CAPTAIN_DOWN':'1','P2_CAVE_ROUTE_FULL_PARTY':''},'guard',Path('/unused'),TOKEN)

    def test_modal_requires_actual_parent_pid_and_unique_fresh_window(self):
        self.assertEqual(runtime.matching_modal(windows(), begin(), set())['window'], 22)
        for changed in ('pid', 'title', 'duplicate', 'stale', 'parent-owner', 'missing-owner'):
            items = windows(); baseline = set()
            if changed == 'pid': items[0]['pid'] = 5555
            if changed == 'title': items[1]['title'] = 'Other cave'
            if changed == 'duplicate': items.append(dict(items[1], window=23))
            if changed == 'stale': baseline.add(22)
            if changed == 'parent-owner': items[0]['owner_pid']=5555
            if changed == 'missing-owner': items[1]['owner_pid']=None
            with self.assertRaises(ValueError):
                runtime.matching_modal(items, begin(), baseline)
        items = windows(); items[1]['mapped'] = False
        self.assertIsNone(runtime.matching_modal(items, begin(), set()))

    def test_fresh_acquisition_switch_is_required_and_reentry_switch_forbidden(self):
        with tempfile.TemporaryDirectory() as directory:
            session=Path(directory);run=session/'runs'/'fresh';run.mkdir(parents=True)
            state=dict(phase='acquisition',visit=1,revision=1,wfg_white_boundary=None,entry=dict(health=1,squad=[[1,0]]*20))
            pending=dict(phase='acquisition',revision=1,run=str(run),token=TOKEN)
            (session/'route-state.json').write_text(json.dumps(state));(session/'route-pending.json').write_text(json.dumps(pending))
            env={'P2_CAVE_ROUTE_FULL_PARTY':'1'}
            with self.assertRaises(ValueError):runtime.validate_launch_environment(env,'acquisition',run,TOKEN)
            acquired=dict(env,P2_CAVE_ROUTE_ACQUIRE='1')
            runtime.validate_launch_environment(acquired,'acquisition',run,TOKEN)
            state['visit']=2;(session/'route-state.json').write_text(json.dumps(state))
            runtime.validate_launch_environment(env,'acquisition',run,TOKEN)
            with self.assertRaises(ValueError):runtime.validate_launch_environment(acquired,'acquisition',run,TOKEN)

    def test_end_requires_pressed_correlated_actual_native_selection(self):
        record = dict(begin(), event='end', rc=0, choice=1, known_button_selected=True, selected_label='Leave cave')
        runtime.validate_end(record, begin(), True)
        with self.assertRaises(ValueError): runtime.validate_end(record, begin(), False)
        for key, value in [('pid', 9999), ('sequence', 2), ('choice', 0), ('rc', -1), ('selected_label', 'Stay')]:
            with self.assertRaises(ValueError): runtime.validate_end(dict(record, **{key: value}), begin(), True)

    def test_observer_refuses_pid_reuse_and_duplicate_without_key(self):
        backend = Backend()
        observer = runtime.DialogObserver(backend, {}, Path('/exe'), Path('/run'), 'acquisition', TOKEN, 'leave', 'White Flower Garden')
        observer.line('P2_CAVE_ROUTE_FLOOR_READY token=' + TOKEN)
        with patch.object(runtime, 'native_context', return_value=(1234, '1')), patch.object(runtime,'modal_owner_context',return_value=(1235,'2')):
            observer.line(runtime.PREFIX + json.dumps(begin()))
        backend.items = windows()
        with patch.object(runtime, 'native_context', return_value=(1234, '2')):
            with self.assertRaises(ValueError): observer.tick()
        self.assertEqual(backend.keys, [])
        with self.assertRaises(ValueError): observer.line(runtime.PREFIX + json.dumps(begin()))

    def test_observer_performs_only_one_fixed_return_after_two_observations(self):
        backend = Backend()
        observer = runtime.DialogObserver(backend, {}, Path('/exe'), Path('/run'), 'acquisition', TOKEN, 'leave', 'White Flower Garden')
        observer.line('P2_CAVE_ROUTE_FLOOR_READY token=' + TOKEN)
        with patch.object(runtime, 'native_context', return_value=(1234, '1')), patch.object(runtime,'modal_owner_context',return_value=(1235,'2')):
            observer.line(runtime.PREFIX + json.dumps(begin()))
            backend.items = windows()
            observer.tick(); observer.tick()
        self.assertEqual(backend.keys, [22])

    def test_foreign_resource_owner_refuses_before_return(self):
        backend=Backend()
        observer=runtime.DialogObserver(backend,{},Path('/exe'),Path('/run'),'acquisition',TOKEN,'leave','White Flower Garden')
        observer.line('P2_CAVE_ROUTE_FLOOR_READY token='+TOKEN)
        with patch.object(runtime,'native_context',return_value=(1234,'1')):
            observer.line(runtime.PREFIX+json.dumps(begin()));backend.items=windows()
            with patch.object(runtime,'modal_owner_context',side_effect=ValueError('foreign owner')):
                with self.assertRaises(ValueError):observer.tick()
        self.assertEqual(backend.keys,[])

    def test_raw_provider_pid_and_group_must_match_observed_native(self):
        runtime.validate_provider_lineage({'pid':1234,'owned_process_group':1234},(1234,'1'))
        for record in ({'pid':5555,'owned_process_group':5555},{'pid':1234}, {'pid':1234,'owned_process_group':5555}):
            with self.assertRaises(ValueError):runtime.validate_provider_lineage(record,(1234,'1'))

    def test_guard_receipt_is_separate_and_preserves_common_false(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory); exe = run / 'nectar.exe'; exe.write_bytes(b'policy-only')
            (run/'pikmin_settings.conf').write_bytes(runtime.SETTINGS)
            raw = dict(exit_code=86, passed=False, timed_out=False, elapsed_seconds=1, captain_down=True)
            raw_bytes = (json.dumps(raw) + '\n').encode()
            (run / 'native.log').write_text('P2_CAVE_ROUTE_NEGATIVE_INITIALIZED captain=1\n')
            (run / 'run-result.json').write_bytes(raw_bytes)
            proof = dict(pins={'FIXTURE_SOURCE_SHA256': 'c' * 64})
            with patch.dict(runtime.os.environ,dict(runtime.MAPPED_ENV,P2_CAVE_ROUTE_FORCE_CAPTAIN_DOWN='1'),clear=True), patch.object(runtime, 'recipe_admission', return_value=proof), patch.object(runtime, '_provider_launch', return_value=raw):
                result = runtime.launch_linux_fixture(exe, run, ['--experimental-pikmin2-surface', 'tutorial'], 'guard', run, run, 'guard', TOKEN, None, None)
            self.assertFalse(result['passed'])
            self.assertEqual((run / 'run-result.json').read_bytes(), raw_bytes)
            receipt = json.loads((run / 'cave-linux-runtime-result.json').read_text())
            self.assertTrue(receipt['linux_route_phase_accepted'])
            self.assertFalse(receipt['gameplay_accepted'])

    def test_guard_rejects_boundary_and_writes_failure_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory); exe = run / 'nectar.exe'; exe.write_bytes(b'policy-only')
            (run/'pikmin_settings.conf').write_bytes(runtime.SETTINGS)
            (run / 'native.log').write_text('P2_CAVE_ROUTE_NEGATIVE_INITIALIZED captain=1\n')
            (run / 'p2-cave-transfer.txt').write_text('unexpected boundary')
            raw = dict(exit_code=86, timed_out=False, elapsed_seconds=1, captain_down=True)
            with patch.dict(runtime.os.environ,dict(runtime.MAPPED_ENV,P2_CAVE_ROUTE_FORCE_CAPTAIN_DOWN='1'),clear=True), patch.object(runtime, 'recipe_admission', return_value=dict(pins={'FIXTURE_SOURCE_SHA256': 'c' * 64})), patch.object(runtime, '_provider_launch', return_value=raw):
                with self.assertRaises(ValueError):
                    runtime.launch_linux_fixture(exe, run, ['--experimental-pikmin2-surface', 'tutorial'], 'guard', run, run, 'guard', TOKEN, None, None)
            self.assertFalse(json.loads((run / 'cave-linux-runtime-result.json').read_text())['linux_route_phase_accepted'])

    def test_xres_zero_success_and_server_pid_are_used(self):
        backend=runtime.X11Input.__new__(runtime.X11Input);backend.display=1
        values=(runtime.ClientIdValue*1)();values[0].spec.mask=2;values[0].length=4
        class ResourceServer:
            destroyed=False
            def XResQueryClientIds(self,display,num,spec,count,result):
                ctypes.cast(count,ctypes.POINTER(ctypes.c_long))[0]=1
                ctypes.cast(result,ctypes.POINTER(ctypes.POINTER(runtime.ClientIdValue)))[0]=ctypes.cast(values,ctypes.POINTER(runtime.ClientIdValue))
                return 0
            def XResGetClientPid(self,value):return 1235
            def XResClientIdsDestroy(self,count,result):self.destroyed=True
        backend.xr=ResourceServer()
        self.assertEqual(backend.owner_pid(22),1235)
        self.assertTrue(backend.xr.destroyed)

    def test_hidden_window_and_inherited_native_settings_refuse_before_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            run=Path(directory);settings=run/'pikmin_settings.conf';settings.write_bytes(runtime.SETTINGS)
            runtime.validate_mapped_runtime(runtime.MAPPED_ENV,run)
            hidden=dict(runtime.MAPPED_ENV);hidden.pop('PIKMIN_RANDOMIZER_TEST_VISIBLE')
            with self.assertRaises(ValueError):runtime.validate_mapped_runtime(hidden,run)
            settings.write_bytes(runtime.SETTINGS.replace(b'debugKeys=0',b'debugKeys=1'))
            with self.assertRaises(ValueError):runtime.validate_mapped_runtime(runtime.MAPPED_ENV,run)
            settings.unlink()
            with self.assertRaises(ValueError):runtime.validate_mapped_runtime(runtime.MAPPED_ENV,run)


if __name__ == '__main__':
    unittest.main()
