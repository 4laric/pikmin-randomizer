import unittest
from tests import test_pikmin2_controller as fixtures
from workflow.resource_wakeup import tick


class ResourceWakeupTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ControllerTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.reg,self.c = self.f.reg,self.f.controller
        self.reg.finish('consumer',1,'blocked','Private build lease queued; both slots held',self.f.ev,['#186'])
        with self.reg.transaction() as s:
            self.reg.event(s,'lease_released','provider',resource='build:private')
            s['events'][-1]['at'] = self.reg.clock()+1
        self.f.now += 2

    def test_reassesses_once_preserving_other_gates(self):
        tick(self.c);tick(self.c)
        launches=list(self.reg.control_status()['launches'].values())
        self.assertEqual(len(launches),1)
        self.assertEqual(launches[0]['session'],'session-consumer')
        self.assertIn('not a reserved slot',launches[0]['instruction'])
        self.assertEqual(self.reg.status()['lanes']['consumer']['dependencies'],['#186'])
        with self.reg.transaction() as s:
            for x in s['control']['launches'].values():x['status']='exited'
        tick(self.c);self.assertEqual(len(self.reg.control_status()['launches']),1)

    def test_full_paused_stale_capacity_and_live_unknown_are_protected(self):
        for health in ['alive','unknown']:
            self.reg.probe=lambda p:health
            tick(self.c);self.assertFalse(self.reg.control_status()['launches'])
        self.reg.probe=lambda p:'dead'
        for policy in [dict(enabled=True,paused=True),dict(enabled=True,paused=False,observed_at=-10000)]:
            with self.reg.transaction() as s:s['build_capacity']=policy
            tick(self.c);self.assertFalse(self.reg.control_status()['launches'])
        with self.reg.transaction() as s:
            s['build_capacity']={};s['settings']['max_heavy_builds']=0
        tick(self.c);self.assertFalse(self.reg.control_status()['launches'])

    def test_old_event_and_unrelated_blocker_do_not_wake(self):
        with self.reg.transaction() as s:
            s['events'][-1]['at']=0
        tick(self.c);self.assertFalse(self.reg.control_status()['launches'])

        with self.reg.transaction() as s:
            s['events'][-1]['at']=self.reg.clock()
            s['lanes']['consumer']['next_action']='Missing legal assets; source review needed'
        tick(self.c);self.assertFalse(self.reg.control_status()['launches'])

    def test_reaped_build_waiter_is_new_availability(self):
        with self.reg.transaction() as s:s['events'][-1]['kind']='request_reaped'
        tick(self.c)
        self.assertEqual(len(self.reg.control_status()['launches']),1)

    def test_fifo_head_blocker_reassessed_without_build_lease_word_order(self):
        with self.reg.transaction() as s:
            s['lanes']['consumer']['next_action'] = ('Lease retried 10x: 0 leases, capacity free '
                '(max=4) but FIFO head is BLOCKED lane forest (live pid) wedging the heavy pool.')
        tick(self.c)
        self.assertEqual(len(self.reg.control_status()['launches']),1)
