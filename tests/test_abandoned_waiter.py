import copy
import unittest
from tests.test_terminal_cleanup import TerminalCleanupTests
from workflow.abandoned_waiter import tick,sleep_only


class AbandonedWaiterTests(unittest.TestCase):
    def setUp(self):
        self.f=TerminalCleanupTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.r,self.c=self.f.r,self.f.c
        self.owner=dict(pid=33,health='alive')
        self.f.rows.append(dict(ProcessId=33,ParentProcessId=777,Name='python3.12.exe',
            CommandLine='C:/Python/python3.12.exe -c "import time; time.sleep(7200)"'))
        with self.r.transaction() as s:
            lane=s['lanes']['one'];lane.update(state='blocked',progress_at=100,outcome=dict(outcome='blocked',evidence=self.f.f.f.evidence))
            self.request=dict(id='wait',lane='one',generation=lane['generation'],resource='build:output/test',
                              requested_at=1,process=self.owner)
            s['queue']['wait']=copy.deepcopy(self.request)

    def run_tick(self,rows=None,identity=None):
        tick(self.c,inventory=rows or (lambda:self.f.rows),identity_reader=identity or (lambda _:self.owner))

    def test_cancels_only_queue_then_normal_cleanup_can_retire_terminal_cli(self):
        self.run_tick();self.run_tick()
        self.assertNotIn('wait',self.r.snapshot()['queue'])
        self.f.stop.assert_not_called()
        self.f.run_cleanup();self.f.stop.assert_called_once_with(self.f.child)

    def test_active_unknown_reused_leased_child_and_generation_protected(self):
        original=self.r.snapshot()
        for kind in ('active','unknown','lease','generation','new_request','no_outcome'):
            with self.r.transaction() as s:
                s.clear();s.update(copy.deepcopy(original))
                if kind=='active':s['lanes']['one']['state']='running'
                elif kind=='unknown':s['queue']['wait']['process']['health']='unknown'
                elif kind=='lease':s['leases']['build:other']=dict(lane='one',process=self.owner)
                elif kind=='generation':s['queue']['wait']['generation']+=1
                elif kind=='new_request':s['queue']['wait']['requested_at']=999999
                elif kind=='no_outcome':s['lanes']['one']['outcome']=None
            self.run_tick();self.assertIn('wait',self.r.snapshot()['queue'],kind)
        with self.r.transaction() as s:s.clear();s.update(original)
        self.run_tick(identity=lambda _:dict(pid=33,health='new'));self.assertIn('wait',self.r.snapshot()['queue'])
        self.f.rows.append(dict(ProcessId=44,ParentProcessId=33,Name='ninja.exe'))
        self.run_tick();self.assertIn('wait',self.r.snapshot()['queue'])

    def test_changed_log_or_additional_python_code_is_not_idle(self):
        def rows():
            with (self.f.out/'stderr.log').open('a') as p:p.write('message=new-tool\n')
            return self.f.rows
        self.run_tick(rows=rows);self.assertIn('wait',self.r.snapshot()['queue'])
        for command in ['C:/Python/python.exe other.py -c "import time; time.sleep(7200)"',
                        'C:/Python/python.exe -c "import time; time.sleep(7200); run_build()"']:
            self.f.rows[-1]['CommandLine']=command
            self.assertFalse(sleep_only(self.f.rows,self.owner))
