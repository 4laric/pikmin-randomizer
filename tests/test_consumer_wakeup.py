import unittest
from tests import test_pikmin2_controller as fixtures
from workflow.consumer_wakeup import tick


class ConsumerWakeupTests(unittest.TestCase):
    def test_typed_delivery_runs_and_verifies_exact_consumer_contract(self):
        from workflow.delivery_contracts import record,status
        from workflow.consumer_verification import reconcile,report
        from workflow.handoff import digest
        self.f.add_lane('owner',3)
        with self.r.transaction() as s:
            s['throughput']={'workstreams':{'s':dict(owner_lane='owner',lanes=['consumer'])}}
        contract=record(self.r,'consumer',1,'provider','consumer_behavior','Required source',
                        'Run original consumer command; expect resolved behavior','owner',self.f.ev)
        tick(self.c)
        launch=next(iter(self.r.control_status()['launches'].values()))
        self.assertEqual(launch['delivery_contracts'],[contract['id']])
        self.c.dispatch(launch);self.r.bind_launch(launch['id'],self.f.identity)
        reconcile(self.c)
        path=self.f.out/'independent.txt';path.write_text('Original failure absent')
        report(self.r,launch['id'],'consumer',2,True,
            dict(command='consumer-check',expected='resolved',observed='resolved'),
            dict(path=str(path),sha256=digest(path)),prerequisite_resolved=True)
        self.assertEqual(status(self.r.snapshot(),contract),'verified')

    def setUp(self):
        self.f=fixtures.ControllerTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.r,self.c=self.f.reg,self.f.controller
        self.r.finish('consumer',1,'blocked','Missing source and approval',self.f.ev,['#1','#186'])
        with self.r.transaction() as s:
            s['lanes']['provider'].update(state='done',integrated_at=1001,
                integration=dict(root_commit='b'*40,native_commit=None,
                    validation_path=self.f.ev['path'],validation_sha256=self.f.ev['sha256']))
        self.f.now+=1000  # Past the integration quiet window.

    def test_issue_dependency_reassessed_once_without_clearing_other_gates(self):
        tick(self.c);tick(self.c)
        launches=list(self.r.control_status()['launches'].values())
        self.assertEqual(len(launches),1)
        self.assertEqual(launches[0]['session'],'session-consumer')
        self.assertIn('do not create duplicate work',launches[0]['instruction'])
        self.assertEqual(self.r.status()['lanes']['consumer']['dependencies'],['#1','#186'])

    def test_changed_receipt_can_reassess_but_unchanged_blocker_cannot_loop(self):
        tick(self.c)
        with self.r.transaction() as s:
            for launch in s['control']['launches'].values():launch['status']='exited'
        tick(self.c)
        self.assertEqual(len(self.r.control_status()['launches']),1)
        with self.r.transaction() as s:s['lanes']['provider']['integration']['root_commit']='c'*40
        tick(self.c)
        self.assertEqual(len(self.r.control_status()['launches']),1)  # Inside the debounce window.
        self.f.now+=900
        tick(self.c)
        self.assertEqual(len(self.r.control_status()['launches']),2)

    def test_review_only_and_corrupt_receipt_do_not_claim_source_available(self):
        with self.r.transaction() as s:s['lanes']['provider']['integration']['validation_sha256']='bad'
        tick(self.c);self.assertFalse(self.r.control_status()['launches'])
        with self.r.transaction() as s:s['lanes']['provider']['integration']=None
        tick(self.c);self.assertFalse(self.r.control_status()['launches'])

    def test_verified_coordinator_link_covers_issue_alias(self):
        with self.r.transaction() as s:
            s['lanes']['consumer']['dependencies']=['#999']
            s['throughput_runtime']={'autofill':{'prerequisite_requests':{'one':dict(status='linked',
                report=self.f.ev,lanes=['consumer'],disposition=dict(lanes=['provider'],evidence=self.f.ev))}}}
        tick(self.c);self.assertEqual(len(self.r.control_status()['launches']),1)

    def test_live_unknown_and_handoff_owners_are_not_restarted(self):
        for health in ['alive','unknown']:
            self.r.probe=lambda p:health
            tick(self.c);self.assertFalse(self.r.control_status()['launches'])
        self.r.probe=lambda p:'dead'
        with self.r.transaction() as s:s['lanes']['consumer']['handoff']={'path':'preserve'}
        tick(self.c);self.assertFalse(self.r.control_status()['launches'])

    def test_blocker_link_requires_pinned_consumer_and_verified_integration(self):
        with self.r.transaction() as s:
            s['lanes']['consumer']['dependencies']=['#999']
            s['blocked_producer_links']={'consumer':dict(producers=['provider'],evidence=self.f.ev,
                source_pins={'root':'wrong','native':None})}
        tick(self.c);self.assertFalse(self.r.control_status()['launches'])
        with self.r.transaction() as s:
            s['blocked_producer_links']['consumer']['source_pins']['root']='a'*40
        tick(self.c);self.assertEqual(len(self.r.control_status()['launches']),1)
