import copy
import json
import unittest
from unittest.mock import Mock
from tests import test_workflow_autofill as fixtures
from workflow.terminal_cleanup import tick, finished_loop, idle_tree, release_terminal_builds
from workflow.runner import write

class TerminalCleanupTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.AutofillTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.r=self.f.reg;self.c=self.f.controller
        self.c.config['terminal_cleanup']={'enabled':True}
        self.child={'health':'alive','pid':22};self.runner={'health':'alive','pid':11}
        self.out=self.c.launch_directory('test');self.out.mkdir(parents=True)
        write(self.out/'child.json',self.child)
        (self.out/'stderr.log').write_text('timestamp=1970-01-01T00:00:01Z message="exiting loop" session.id=ses_test\n')
        with self.r.transaction() as s:
            s['lanes']['one'].update(state='review_ready',process=self.runner,review={'evidence':{'review':self.f.f.evidence}})
            s.setdefault('control',{})['launches']={'test':dict(id='test',lane='one',status='running',bound_generation=s['lanes']['one']['generation'],process=self.runner,session='ses_test')}
        self.rows=[dict(ProcessId=11,ParentProcessId=1,Name='python.exe'),dict(ProcessId=22,ParentProcessId=11,Name='opencode.exe')]
        self.stop=Mock(return_value=True)
    def run_cleanup(self):tick(self.c,inventory=lambda:self.rows,terminate=self.stop)
    def test_finished_terminal_only(self):
        self.run_cleanup();self.stop.assert_called_once_with(self.child)
        self.assertTrue((self.out/'terminal-cleanup.json').exists())
    def test_short_grace_still_requires_terminal_quiet_period(self):
        self.c.config['terminal_cleanup']['grace_seconds'] = 30
        self.f.now = 30
        self.run_cleanup(); self.stop.assert_not_called()
        self.f.now = 32
        self.run_cleanup(); self.stop.assert_called_once_with(self.child)
    def test_active_child_prevents_stop(self):
        self.rows.append(dict(ProcessId=33,ParentProcessId=22,Name='ninja.exe'))
        self.run_cleanup();self.stop.assert_not_called()
    def test_live_lease_prevents_stop(self):
        with self.r.transaction() as s:s['leases']['build:test']={'lane':'one','process':{'health':'unknown'}}
        self.run_cleanup();self.stop.assert_not_called()
    def test_nonterminal_or_stale_generation_prevents_stop(self):
        with self.r.transaction() as s:s['lanes']['one']['state']='running'
        self.run_cleanup();self.stop.assert_not_called()
        with self.r.transaction() as s:
            s['lanes']['one']['state']='review_ready';s['lanes']['one']['generation']+=1
        self.run_cleanup();self.stop.assert_not_called()
    def test_wrong_session_or_new_activity_prevents_stop(self):
        line='timestamp=1970-01-01T00:00:01Z message="exiting loop" session.id=ses_test\n'
        self.assertFalse(finished_loop(line,'ses_other',1000,300))
        self.assertFalse(finished_loop(line+'message=stream\n','ses_test',1000,300))
        self.assertFalse(finished_loop(line,'ses_test',10,300))
        self.assertTrue(finished_loop(line+'message=cleanup prune=7.days\n','ses_test',1000,300))
    def test_dashboard_separates_reservations(self):
        from workflow.autofill import _state,autofill_status
        with self.r.transaction() as s:
            _state(s)['planner_pool']={'scopes':{'one':{'spec':{'lane':{'lane':'one'}}}}}
        self.assertEqual(autofill_status(self.r)['planner_pool']['report_ready'],1)

    def test_dead_terminal_build_released_before_expiry(self):
        resource=self.r.resource('build:output/private')
        with self.r.transaction() as s:
            generation=s['lanes']['one']['generation']
            s['leases'][resource]=dict(lane='one',generation=generation,token='test',
                process={'health':'dead'},expires_at=999999)
        release_terminal_builds(self.r);release_terminal_builds(self.r)
        with self.r.transaction() as s:self.assertNotIn(resource,s['leases'])

    def test_live_unknown_active_and_stale_generation_leases_preserved(self):
        for health,lane_state,offset in [('alive','done',0),('unknown','done',0),
                                         ('dead','running',0),('dead','done',1)]:
            with self.r.transaction() as s:
                s['lanes']['one']['state']=lane_state
                s['leases']['build:test']=dict(lane='one',generation=s['lanes']['one']['generation']+offset,
                    token='test',process={'health':health},expires_at=999999)
            release_terminal_builds(self.r)
            with self.r.transaction() as s:self.assertIn('build:test',s['leases'])
