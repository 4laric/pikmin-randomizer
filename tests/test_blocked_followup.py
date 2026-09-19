import unittest
from tests import test_pikmin2_controller as fixtures
from workflow.blocked_followup import tick, link
from workflow.handoff import Rejected


class BlockedFollowupTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ControllerTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.reg,self.c=self.f.reg,self.f.controller
        self.c.config['throughput']={'autofill':{'enabled':True,'planner_lane':'consumer'}}
        self.reg.finish('consumer',1,'blocked','Awaiting proposals',self.f.ev,['#581'])
        self.reg.finish('provider',1,'blocked','Needs engine implementation, not missing raw assets',self.f.ev,['#186'])
        self.f.now += 301

    def test_without_no_work_report_and_bounded_after_no_progress(self):
        tick(self.c);tick(self.c)
        self.assertEqual(len(self.reg.control_status()['launches']),1)
        for _ in range(3):
            with self.reg.transaction() as s:
                for x in s['control']['launches'].values():x['status']='exited'
            tick(self.c)
        self.assertEqual(len(self.reg.control_status()['launches']),2)
        self.assertEqual(self.reg.status()['lanes']['provider']['state'],'blocked')

    def test_new_evidence_per_generation_keeps_the_attempt_cap(self):
        from workflow.handoff import digest
        for n in range(4):
            path=self.f.out/('evidence-%d.txt'%n);path.write_text('Gap unchanged, generation %d'%n)
            self.reg.finish('provider',1,'blocked','Needs engine implementation, not missing raw assets',
                            dict(path=str(path),sha256=digest(path)),['#186'])
            self.f.now+=301;tick(self.c)
            with self.reg.transaction() as s:
                for x in s['control']['launches'].values():x['status']='exited'
        self.assertEqual(len(self.reg.control_status()['launches']),2)

    def test_live_consumer_and_explicit_active_producer_are_not_duplicated(self):
        self.reg.probe=lambda p:'unknown'
        tick(self.c);self.assertFalse(self.reg.control_status()['launches'])

        self.reg.probe=lambda p:'dead'
        with self.reg.transaction() as s:
            s['lanes']['provider']['dependencies']=['producer']
            s['lanes']['producer']={'state':'running'}
        tick(self.c);self.assertFalse(self.reg.control_status()['launches'])

    def test_attach_to_unstarted_coordinator_without_duplicate_launch(self):
        launch=self.reg.plan_launch('consumer','ordinary-planning','Original task',self.c.config['models'])
        tick(self.c);tick(self.c)
        launches=self.reg.control_status()['launches']
        self.assertEqual(len(launches),1)
        self.assertTrue(launches[launch['id']]['instruction'].startswith('Original task'))
        self.assertEqual(len(launches[launch['id']]['blocked_followup_ids']),1)

    def test_failed_consumer_verification_routes_bounded_producer_repair(self):
        with self.reg.transaction() as s:
            lane=s['lanes']['provider']
            s['consumer_verifications']={'check':dict(id='check',consumer='provider',
                consumer_generation=1,created_at=1000,status='unverified',
                producers=[dict(lane='integrated-producer',root_commit='b'*40,native_commit=None)],
                source_pins={k:(lane.get(k) or {}).get('head') for k in ('root','native')},
                acceptance_check='Compile the consumer fixture',result='same source-path error',evidence=self.f.ev)}
        tick(self.c)
        launch=next(iter(self.reg.control_status()['launches'].values()))
        self.assertEqual(len(launch['blocked_followup_ids']),1)
        self.assertTrue(launch['blocked_followup_ids'][0].startswith('consumer-repair:'))
        self.assertIn('Compile the consumer fixture',launch['instruction'])
        for _ in range(3):
            with self.reg.transaction() as s:
                for item in s['control']['launches'].values():item['status']='exited'
            tick(self.c)
        self.assertEqual(len(self.reg.control_status()['launches']),2)

    def prepare_link(self):
        self.f.add_lane('implementation',3)
        with self.reg.transaction() as s:
            s.setdefault('throughput_runtime',{})['autofill']={'prerequisite_coordinator':'consumer'}
            s['lanes']['consumer'].update(state='running',process=self.f.identity)

    def test_links_real_producer_without_clearing_consumer(self):
        self.prepare_link()
        result=link(self.reg,'consumer',1,'provider',1,['implementation'],'Owned missing input',self.f.ev)
        self.assertEqual(result['producers'],['implementation'])
        self.assertEqual(self.reg.status()['lanes']['provider']['state'],'blocked')

    def test_rejects_blocked_provider_stale_generation_and_cycle(self):
        self.prepare_link()
        with self.assertRaises(Rejected):link(self.reg,'consumer',1,'provider',2,['implementation'],'reason',self.f.ev)
        with self.reg.transaction() as s:s['lanes']['implementation']['state']='blocked'
        with self.assertRaises(Rejected):link(self.reg,'consumer',1,'provider',1,['implementation'],'reason',self.f.ev)
        with self.reg.transaction() as s:
            s['lanes']['implementation']['state']='running'
            s['lanes']['implementation']['dependencies']=['provider']
        with self.assertRaises(Rejected):link(self.reg,'consumer',1,'provider',1,['implementation'],'reason',self.f.ev)

