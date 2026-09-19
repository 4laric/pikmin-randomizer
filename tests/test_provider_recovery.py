"""Fault injection for recovery after tools, including restart during shutdown."""
import json
import os
import subprocess
import sys
import unittest

from tests import test_pikmin2_controller as controller_tests
from workflow.processes import identify
from workflow.runner import write
from workflow.provider_recovery import recover, safe_descendants, stop_exact


class ProviderRecoveryTests(unittest.TestCase):
    setUp = controller_tests.ControllerTests.setUp
    add_lane = controller_tests.ControllerTests.add_lane

    def prepare(self):
        self.now = 2000
        self.worker = dict(pid=123, started='worker', host='test')
        self.supervisor = dict(pid=124, started='supervisor', host='test')
        self.alive = [self.worker, self.supervisor]
        self.reg.probe = lambda p: 'alive' if p in self.alive else 'dead'
        self.controller.config['lanes']['consumer']['legacy_supervisors'] = [self.supervisor]
        self.controller.config['provider_stall_recovery'] = dict(enabled=True, quiet_seconds=180, models=['paid/muse'])
        with self.reg.transaction() as state:
            state['lanes']['consumer']['process'] = self.worker
        self.events = self.out/'run-0.jsonl'
        self.errors = self.out/'run-0.err'
        self.events.write_text(json.dumps(dict(type='tool_use',timestamp=1000000,
            part=dict(id='tool1',state=dict(status='completed'))))+'\n'+
            json.dumps(dict(type='step_finish',timestamp=1001000))+'\n')
        os.utime(self.events, (1001,1001))
        self.errors.write_text('timestamp=1970-01-01T00:16:42Z level=ERROR Rate limit exceeded\n')
        self.stopped = []

    def rows(self):
        return [dict(ProcessId=p['pid'], ParentProcessId=0 if p==self.supervisor else 124, Name='python.exe' if p==self.supervisor else 'opencode.exe') for p in self.alive]

    def stop(self,p):
        self.stopped.append(p); self.alive.remove(p)

    def run_recovery(self,**kw):
        recover(self.controller,table=kw.get('table',self.rows),stop=kw.get('stop',self.stop))

    def test_stops_supervisor_before_worker_then_replays_once(self):
        self.prepare(); self.run_recovery()
        self.assertEqual(self.stopped,[self.supervisor,self.worker])
        self.assertEqual(self.reg.control_status()['launches'],{})
        self.run_recovery(); self.run_recovery()
        launches=list(self.reg.control_status()['launches'].values())
        self.assertEqual(len(launches),1)
        self.assertEqual(launches[0]['models'],['paid/muse'])
        self.assertEqual(launches[0]['session'],'session-consumer')

    def test_active_descendant_blocks_stop(self):
        self.prepare()
        self.run_recovery(table=lambda:self.rows()+[dict(ProcessId=999,ParentProcessId=123,Name='cc1plus.exe')])
        self.assertEqual(self.stopped,[])

    def test_unknown_descendant_inventory_blocks_stop(self):
        self.prepare()
        def fail(): raise OSError('access denied')
        self.run_recovery(table=fail); self.assertEqual(self.stopped,[])

    def test_active_or_unknown_lease_blocks_stop(self):
        self.prepare()
        with self.reg.transaction() as state:
            state['leases']['build'] = dict(lane='consumer',process=self.worker)
        self.run_recovery(); self.assertEqual(self.stopped,[])
        self.reg.probe=lambda p:'unknown'
        self.run_recovery(); self.assertEqual(self.stopped,[])

    def test_incomplete_tool_and_partial_json_block_stop(self):
        self.prepare()
        self.events.write_text(self.events.read_text().replace('completed','running'))
        os.utime(self.events,(1001,1001))
        self.run_recovery(); self.assertEqual(self.stopped,[])
        self.events.write_text('{partial'); os.utime(self.events,(1001,1001))
        self.run_recovery(); self.assertEqual(self.stopped,[])

    def test_fresh_activity_and_obsolete_error_block_stop(self):
        self.prepare(); os.utime(self.events,(1999,1999))
        self.run_recovery(); self.assertEqual(self.stopped,[])
        os.utime(self.events,(1001,1001)); self.errors.write_text('timestamp=1970-01-01T00:16:00Z Rate limit exceeded')
        self.run_recovery(); self.assertEqual(self.stopped,[])

    def test_terminal_handoff_is_never_restarted(self):
        self.prepare()
        with self.reg.transaction() as state:
            state['lanes']['consumer'].update(state='handoff_ready',handoff_at=self.now)
        self.run_recovery(); self.assertEqual(self.stopped,[])

    def test_restart_after_supervisor_stop(self):
        self.prepare()
        def interrupted(p):
            if p==self.worker: raise OSError('interrupted')
            self.stop(p)
        self.run_recovery(stop=interrupted)
        self.assertEqual(self.stopped,[self.supervisor])
        self.run_recovery(); self.run_recovery()
        self.assertEqual(len(self.reg.control_status()['launches']),1)

    def test_identity_disappeared_does_not_authorize_fresh_stop(self):
        self.prepare(); self.alive.remove(self.worker)
        self.run_recovery(); self.assertEqual(self.stopped,[])

    def test_recovery_budget_is_bounded(self):
        self.prepare(); self.controller.config['provider_stall_recovery']['max_attempts_per_head']=0
        self.run_recovery(); self.assertEqual(self.stopped,[])

    def test_managed_runner_is_replaced_in_same_session(self):
        self.prepare()
        directory=self.controller.launch_directory('old'); directory.mkdir(parents=True)
        write(directory/'child.json',self.worker)
        (directory/'events.jsonl').write_text(self.events.read_text())
        os.utime(directory/'events.jsonl',(1001,1001))
        (directory/'stderr.log').write_text(self.errors.read_text())
        with self.reg.transaction() as state:
            state['lanes']['consumer']['process']=self.supervisor
            self.reg.control(state)['launches']['old']=dict(id='old',lane='consumer',status='running')
        self.run_recovery(); self.run_recovery(); self.run_recovery()
        launches=self.reg.control_status()['launches']
        self.assertEqual(launches['old']['status'],'exited')
        self.assertEqual(len(launches),2)
        self.assertEqual(next(x for k,x in launches.items() if k!='old')['session'],'session-consumer')

    def test_terminal_state_after_shutdown_prevents_relaunch(self):
        self.prepare(); self.run_recovery()
        with self.reg.transaction() as state: state['lanes']['consumer']['state']='done'
        self.run_recovery(); self.assertEqual(self.reg.control_status()['launches'],{})

    def test_new_child_between_checks_prevents_worker_stop(self):
        self.prepare()
        def table():
            return self.rows()+([dict(ProcessId=999,ParentProcessId=123,Name='ninja.exe')] if self.stopped else [])
        self.run_recovery(table=table)
        self.assertEqual(self.stopped,[self.supervisor])

    def test_console_hosts_allowed_but_nested_build_is_not(self):
        owners=[dict(pid=1)]
        rows=[dict(ProcessId=1,ParentProcessId=0,Name='opencode.exe'),dict(ProcessId=2,ParentProcessId=1,Name='conhost.exe')]
        self.assertTrue(safe_descendants(owners,rows))
        self.assertFalse(safe_descendants(owners,rows+[dict(ProcessId=3,ParentProcessId=2,Name='gcc.exe')]))

    @unittest.skipUnless(os.name=='nt','Windows handle identity test')
    def test_real_stop_rejects_stale_identity_and_stops_exact_process(self):
        proc=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            identity=identify(proc.pid)
            stop_exact(dict(identity,started='wrong'))  # The old identity is already dead.
            self.assertIsNone(proc.poll())
            stop_exact(identity)
            self.assertEqual(proc.wait(timeout=5),1)
        finally:
            if proc.poll() is None: proc.terminate(); proc.wait(timeout=5)


if __name__=='__main__': unittest.main()
