import copy
import unittest
from unittest.mock import patch
from tests import test_pikmin2_controller as fixtures
from workflow.throughput_controller import complete_pool_assignments


class CompletionLatencyTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ControllerTests();self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.reg,self.c=self.f.reg,self.f.controller

    def test_pool_completion_never_runs_global_status_diagnostics(self):
        with patch.object(self.reg,'status',side_effect=AssertionError('global diagnostic scan')):
            complete_pool_assignments(self.c)

    def test_live_heartbeats_share_one_write(self):
        item=self.f.plan();self.c.dispatch(item)
        self.reg.bind_launch(item['id'],self.f.identity)
        item=self.reg.control_status()['launches'][item['id']]
        self.f.now+=10
        from workflow.storage import selected
        with patch('workflow.storage.selected',wraps=selected) as tx:
            self.c.heartbeat_runs([item,item])
        self.assertEqual(tx.call_count,1)
        self.assertEqual(self.reg.snapshot()['lanes']['consumer']['heartbeat_at'],self.f.now)

    def test_normalized_heartbeat_keeps_generation_and_process_fences(self):
        from workflow.storage import migrate
        migrate(self.reg)
        self.test_stale_or_dead_heartbeat_observation_cannot_refresh_lane()

    def test_stale_or_dead_heartbeat_observation_cannot_refresh_lane(self):
        item=self.f.plan();self.c.dispatch(item)
        self.reg.bind_launch(item['id'],self.f.identity)
        item=self.reg.control_status()['launches'][item['id']]
        before=self.reg.snapshot()['lanes']['consumer']['heartbeat_at'];self.f.now+=10
        for mode in ('generation','identity','exit','unknown','dead'):
            original=self.reg.snapshot()
            with self.reg.transaction() as s:
                lane=s['lanes']['consumer']
                if mode=='generation':lane['generation']+=1
                if mode=='identity':lane['process']={'pid':99}
                if mode=='exit':s['control']['launches'][item['id']]['status']='exited'
            with patch.object(self.reg,'probe',return_value=mode if mode in ('dead','unknown') else 'alive'):
                self.c.heartbeat_runs([item])
            self.assertEqual(self.reg.snapshot()['lanes']['consumer']['heartbeat_at'],before)
            with self.reg.transaction() as s:s.clear();s.update(copy.deepcopy(original))
