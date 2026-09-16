import subprocess
import shutil
import os
import unittest
from pathlib import Path
from tests import test_pikmin2_workflow as baseline
from workflow.handoff import validate_handoff, digest, Rejected

class CaptainEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.f=baseline.WorkflowTests();self.f.setUp();self.addCleanup(self.f.doCleanups);self.f.running()
    def test_interrupted_pass_rejected_diagnostics_preserved(self):
        f=self.f;f.log.write_text('P2_MAMUTA_REVISIT_CAPTAIN_DOWN tick=20 health=0\nninja: no work to do.\n')
        f.evidence['sha256']=digest(f.log)
        data=f.handoff(runtime=True)
        with self.assertRaisesRegex(Rejected,'captain-down'):validate_handoff(f.root,data)
        for row in data['slice_acceptance']:row['status']='BLOCKED'
        for row in data['gates'].values():row['status']='BLOCKED'
        self.assertTrue(validate_handoff(f.root,data)['reviewable'])
    def test_good_pass_cannot_hide_interrupted_gate(self):
        f=self.f;data=f.handoff(runtime=True)
        p=f.root/'output/interrupted.log';p.write_text('P2_FIXTURE_CAPTAIN_DOWN tick=1 outcome=BLOCKED\n')
        data['evidence']['bad']={'path':str(p),'sha256':digest(p)}
        data['gates']['movement_animation'].update(status='PASS',method='natural',evidence=['bad'])
        with self.assertRaisesRegex(Rejected,'captain-down'):validate_handoff(f.root,data)
    def test_separate_failed_run_does_not_erase_good_evidence(self):
        f=self.f;data=f.handoff(runtime=True)
        p=f.root/'output/interrupted.log';p.write_text('P2_FIXTURE_CAPTAIN_DOWN outcome=BLOCKED\n')
        data['evidence']['diagnostic']={'path':str(p),'sha256':digest(p)}
        self.assertTrue(validate_handoff(f.root,data)['reviewable'])
    def test_cpp_guard_exits_before_observation_on_each_death_signal(self):
        compiler=shutil.which('g++') or 'C:/msys64/mingw64/bin/g++.exe'
        if not Path(compiler).is_file():self.skipTest('C++ compiler unavailable')
        header=(Path(__file__).resolve().parents[1]/'scripts/p2_fixture_captain_guard.h').as_posix()
        source=self.f.root/'output/guard.cpp';exe=self.f.root/'output/guard.exe'
        source.write_text('#include "'+header+'"\nint main(int argc,char**){p2_fixture_require_captain(argc==2,argc==3,argc==4?1.0f:100.0f,7);std::puts("OBSERVED");}\n')
        env=dict(os.environ,PATH=str(Path(compiler).parent)+os.pathsep+os.environ.get('PATH',''))
        built=subprocess.run([compiler,'-std=c++11',str(source),'-o',str(exe)],capture_output=True,text=True,env=env)
        self.assertEqual(built.returncode,0,built.stderr)
        for count in (0,1,2,3):
            result=subprocess.run([str(exe)]+['x']*count,capture_output=True,text=True,env=env)
            self.assertEqual(result.returncode,86 if count else 0)
            self.assertEqual('OBSERVED' in result.stdout,count==0)
            self.assertEqual('CAPTAIN_DOWN' in result.stdout,count!=0)

    def test_required_adoption_and_protected_damage_rejected(self):
        f=self.f;data=f.handoff(runtime=True)
        lane=dict(f.reg.status()['lanes']['one'],native=data['native'],fixture_captain_guard_required=True)
        with self.assertRaisesRegex(Rejected,'Captain safety adoption'):validate_handoff(f.root,data,lane)
        data['fixture_adoption']['captain_safety']={'policy':'unprotected','evidence':['log']}
        self.assertTrue(validate_handoff(f.root,data,lane)['reviewable'])
        data['fixture_adoption']['captain_safety']['policy']='protected_observation'
        data['gates']['attacks_receivers'].update(status='PASS',method='injected',evidence=['log'])
        with self.assertRaisesRegex(Rejected,'Protected observation'):validate_handoff(f.root,data,lane)
