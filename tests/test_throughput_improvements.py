import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from workflow.handoff import Rejected
from workflow.integration_repair import review_rejections, repair_pin
from workflow.stage_timing import observe, metrics
from workflow.producer_contract import validate
from workflow.recurring_failures import groups
from workflow.input_cache import read


class ReviewRepairTests(unittest.TestCase):
    def setUp(self):
        from tests.test_workflow_delivery import DeliveryTests
        self.f=DeliveryTests();self.f.setUp();self.addCleanup(self.f.doCleanups)

    def test_rejected_handoff_routes_and_pin_drift_refuses(self):
        f=self.f;lane=f.ready(reviews=True);f.running('two')
        from tests.approval_auth import reviewer
        reviewer(self,f.reg,'two',owns=['one'],fake_diff=True)
        f.reg.dispose_review('one',1,lane['revision'],'reject',lane['handoff']['sha256'],
                             'shared.cpp','rejected','two',f.evidence,reviewer_generation=1)
        review_rejections(f.reg)
        state=f.reg.snapshot();lane=state['lanes']['one']
        from workflow.control import fingerprint
        pin=lane['review_repair']['pin'];reason='integration-repair:'+fingerprint(pin)
        self.assertEqual(repair_pin(state,lane,reason),pin)
        review_rejections(f.reg)
        self.assertEqual(len(f.reg.snapshot()['events']),len(state['events']))
        lane['revision']+=1
        with self.assertRaises(Rejected):repair_pin(state,lane,reason)

    def test_requested_review_does_not_infer_rejection(self):
        self.f.ready(reviews=True);review_rejections(self.f.reg)
        self.assertNotIn('review_repair',self.f.reg.snapshot()['lanes']['one'])


class StageTimingTests(unittest.TestCase):
    def test_transitions_and_reason_changes_do_not_reset_age(self):
        from tests.test_pikmin2_controller import ControllerTests
        f=ControllerTests();f.setUp();self.addCleanup(f.doCleanups)
        with f.reg.transaction() as s:
            s['lanes']['provider']['state']='done'
            s['lanes']['consumer']['state']='ready'
        observe(f.reg);f.now+=60
        with f.reg.transaction() as s:s['lanes']['consumer']['next_action']='new detail'
        observe(f.reg)
        self.assertEqual(metrics(f.reg.snapshot(),f.now)['current'][0]['age_seconds'],60)
        with f.reg.transaction() as s:s['lanes']['consumer']['state']='running'
        f.now+=30;observe(f.reg)
        observed=metrics(f.reg.snapshot(),f.now)
        self.assertEqual(observed['current'][0]['age_seconds'],0)
        self.assertEqual(sum(v['count'] for v in observed['completed_last_hour'].values()),1)
        with f.reg.transaction() as s:s['lanes']['consumer']['state']='done'
        self.assertEqual(metrics(f.reg.snapshot(),f.now)['current'],[])


class ContractTests(unittest.TestCase):
    def spec(self):
        return dict(role='repair',lane=dict(native={'head':'x'},owned_files=['native/a.cpp','native/CMakeLists.txt']),
                    producer_contract=dict(kind='engine_change',deliverable='Wire hook',
                        callsites=[dict(file='native/a.cpp',symbol='birth')],build_membership=['native/CMakeLists.txt'],
                        consumers=[dict(lane='consumer',command='real-run --birth',expected='natural birth hook')]))

    def test_engine_contract_requires_owned_callsites_build_and_checks(self):
        spec=self.spec();validate(spec,required=True)
        spec['lane']['owned_files'].remove('native/a.cpp')
        with self.assertRaises(Rejected):validate(spec,required=True)
        spec=self.spec();spec['producer_contract']['consumers'][0]['command']=''
        with self.assertRaises(Rejected):validate(spec,required=True)

    def test_old_specs_readable_new_native_requires_contract(self):
        spec=self.spec();del spec['producer_contract'];validate(spec)
        with self.assertRaises(Rejected):validate(spec,required=True)


class ChangedInputsTests(unittest.TestCase):
    def test_file_changes_and_full_audit_invalidate(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'p.json';p.write_text('{"v":1}')
            value,sha=read(p,now=1)
            with patch.object(Path,'read_bytes',side_effect=AssertionError('unchanged input reread')):
                self.assertEqual(read(p,now=2),(value,sha))
            p.write_text('{"v":2}')
            self.assertEqual(read(p,now=3)[0]['v'],2)
            with patch.object(Path,'read_bytes',return_value=b'{"v":3}'):
                self.assertEqual(read(p,now=304)[0]['v'],3)


class RecurringFailureTests(unittest.TestCase):
    def test_exact_pattern_groups_once_and_progress_invalidates(self):
        state=dict(lanes={},events=[])
        for key in ('a','b'):
            state['lanes'][key]=dict(state='blocked',generation=1,progress_at=1,failure_fingerprint='missing entry X',failure_streak=1)
            state['events'].append(dict(kind='failure',lane=key,at=2,fingerprint='missing entry X',evidence={'path':key}))
        self.assertEqual(len(groups(state)),1)
        self.assertEqual(len(groups(state)[0]['consumers']),2)
        state['lanes']['b']['progress_at']=3
        self.assertEqual(groups(state),[])


class NativePreflightTests(unittest.TestCase):
    def test_waiting_for_capacity_does_not_start_build(self):
        from workflow.native_build import execute
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'output/source';build=root/'output/build'
            record=dict(source=str(source),build=str(build))
            reg=Mock(root=root)
            reg.snapshot.return_value={'lanes':{'a':dict(generation=1,state='running',native={'worktree':str(source)})}}
            reg.acquire.return_value=dict(acquired=False,request={'id':'wait'})
            with patch('workflow.native_build.preflight',return_value=record),patch('workflow.native_build.subprocess.run') as run:
                result=execute(reg,'a',1,source,build,'abc',build/'game.exe',root/'output/evidence',wait_seconds=0)
                self.assertFalse(result['launched']);run.assert_not_called()
                reg.cancel_request.assert_called_once_with('a',1,'wait')

    def test_resolves_configured_tools_and_refuses_shared_or_wrong_source(self):
        from workflow.native_build import preflight
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'output/source';build=root/'output/build'
            source.mkdir(parents=True);build.mkdir()
            for name in ('ninja.exe','compiler.exe'):(root/name).write_bytes(b'tool')
            cache=build/'CMakeCache.txt'
            cache.write_text('CMAKE_GENERATOR:INTERNAL=Ninja\nCMAKE_HOME_DIRECTORY:INTERNAL='+str(source)+
                '\nCMAKE_CXX_COMPILER:FILEPATH='+str(root/'compiler.exe')+'\nCMAKE_MAKE_PROGRAM:FILEPATH='+str(root/'ninja.exe'))
            with patch('workflow.native_build.subprocess.run',return_value=SimpleNamespace(stdout='abc')):
                self.assertEqual(preflight(root,source,build,'abc')['tools']['ninja']['path'],str(root/'ninja.exe'))
                with self.assertRaises(Rejected):preflight(root,root/'native',build,'abc')
                with self.assertRaises(Rejected):preflight(root,source,build,'changed')
