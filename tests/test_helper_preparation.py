import threading
import unittest
from types import SimpleNamespace
from tests import test_planner_pool as fixtures
from workflow.helper_preparation import prepare_batch, refresh_reservations
from workflow.handoff import Rejected


class HelperPreparationTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.PlannerPoolTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.reg=self.f.reg;self.controller=self.f.controller
        self.work=[(str(i),dict(id=str(i),lane={'lane':'helper-'+str(i)})) for i in range(4)]
        with self.reg.transaction() as state:
            state.setdefault('throughput_runtime',{}).setdefault('autofill',{})['planner_pool']={
                'target':8,'updated_at':123,'scopes':{scope:dict(spec=spec) for scope,spec in self.work}}

    def test_four_preparations_overlap_and_failure_does_not_block_others(self):
        barrier=threading.Barrier(4,timeout=5)
        def prepare(controller,spec,reader):
            barrier.wait()
            if spec['id']=='0':raise Rejected('invalid proof')
            return True
        result=prepare_batch(self.controller,self.work,None,{},prepare)
        self.assertEqual(result,[False,True,True,True])
        rows=self.reg.snapshot()['throughput_runtime']['autofill']['planner_pool']['scopes']
        self.assertEqual(rows['0']['error'],'invalid proof')
        self.assertTrue(all('preparation' in row for row in rows.values()))

    def scopes(self):
        return self.reg.snapshot()['throughput_runtime']['autofill']['planner_pool']['scopes']

    def test_skipped_attempt_keeps_the_recorded_error(self):
        with self.reg.transaction() as state:
            state['throughput_runtime']['autofill']['planner_pool']['scopes']['0']['error']='No authorized stopped worker'
        from unittest.mock import patch
        with patch.object(self.controller,'capacity',return_value=False):
            self.assertEqual(prepare_batch(self.controller,self.work[:1],None,{},lambda *a:self.fail('ran')),[False])
        row=self.scopes()['0']
        self.assertEqual(row['error'],'No authorized stopped worker')
        self.assertNotIn('preparation',row)
        self.assertEqual(row['preparation_skipped']['reason'],'capacity')

    def test_unexpected_exception_is_recorded_and_not_replaced_by_bookkeeping(self):
        def prepare(controller,spec,reader):raise RuntimeError('boom')
        with self.assertRaises(RuntimeError):prepare_batch(self.controller,self.work[:1],None,{},prepare)
        self.assertEqual(self.scopes()['0']['error'],'RuntimeError: boom')
        import sqlite3
        from unittest.mock import patch
        with patch.object(self.reg,'transaction',side_effect=sqlite3.OperationalError('database is locked')):
            with self.assertRaises(RuntimeError):prepare_batch(self.controller,self.work[:1],None,{},prepare)
        self.assertIn('database is locked',(self.controller.base/'helper-preparation-record-error.json').read_text())

    def test_fresh_counts_include_pending_exclude_completed_preserve_target_time(self):
        with self.reg.transaction() as state:
            state['lanes']['helper-0']={'state':'running'}
            state['lanes']['helper-1']={'state':'review_ready'}
            state['lanes']['helper-2']={'state':'done'}
            state['throughput_runtime']['autofill']['planner_pool']['scopes']['0']['support_targets']=[{'lane':'producer'}]
        refresh_reservations(self.reg)
        pool=self.reg.snapshot()['throughput_runtime']['autofill']['planner_pool']
        self.assertEqual((pool['active'],pool['running'],pool['queued'],pool['prepared'],pool['report_ready']),(3,1,0,1,1))
        self.assertEqual(pool['integration_support_active'],1)
        self.assertEqual((pool['target'],pool['updated_at']),(8,123))
        self.assertIn('counts_updated_at',pool)

class PreparationFairnessTests(unittest.TestCase):
    def test_old_unassigned_work_precedes_fresh_discovery_without_bypassing_support_pressure(self):
        from workflow.planner_pool import preparation_priority
        records={'old':{'started_at':1},'fresh':{'started_at':990,'prerequisite_recovery':'new'}}
        helpers=[{'scope':'fresh'},{'scope':'old'},{'scope':'review','kind':'publication'}]
        ordered=sorted(helpers,key=lambda h:preparation_priority(h,records,{'publication':{'pressure':10}},1000))
        self.assertEqual([h['scope'] for h in ordered],['review','old','fresh'])
        records['old']['completed_at']=900
        ordered=sorted(helpers,key=lambda h:preparation_priority(h,records,{},1000))
        self.assertEqual(ordered[-1]['scope'],'old')
