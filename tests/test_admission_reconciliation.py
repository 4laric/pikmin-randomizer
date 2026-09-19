import unittest
from tests import test_integration_wakeup as fixtures
from workflow.admission_reconciliation import audit, resolve
from workflow.handoff import Rejected
from workflow.integration_wakeup import tick


class AdmissionReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.IntegrationWakeupTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.r = self.f.reg
        self.admission = dict(status='observed', ids=[57], source='maintained')
        self.settings = dict(lane_families={'provider':57})
        with self.r.transaction() as s:
            s['throughput_runtime']['autofill']['items'] = {}
            s['throughput']['workstreams']['content']['lanes'] = ['provider']
            s['lanes']['provider'].update(state='blocked', handoff=None)

    def request(self, decision='retain'):
        row = audit(self.r, self.admission, self.settings)[0]
        with self.r.transaction() as s:
            owner=s['lanes']['consumer']; owner['state']='running'
            identity=owner['process']; generation=owner['generation']
        self.r.probe=lambda p:'alive' if p==identity else 'dead'
        return dict(lane='provider',token=row['token'],reviewer='consumer',reviewer_generation=generation,
                    decision=decision,reason='Evidence reviewed',evidence=self.f.f.ev,
                    next_action='Complete native export',no_remaining_delivery=True,
                    covered_criteria='All original family gates covered by canonical admission evidence')

    def test_audit_is_idempotent_and_wakes_owner(self):
        first=audit(self.r,self.admission,self.settings)
        self.assertEqual(first,audit(self.r,self.admission,self.settings))
        tick(self.f.controller)
        launches=list(self.r.control_status()['launches'].values())
        self.assertEqual(len(launches),1)
        self.assertIn('admission_audit',launches[0]['instruction'])

    def test_retained_work_stays_blocked_and_changed_pins_reaudit(self):
        resolve(self.r,self.request(),self.admission)
        self.assertEqual(self.r.snapshot()['lanes']['provider']['state'],'blocked')
        self.assertEqual(audit(self.r,self.admission,self.settings)[0]['status'],'retain')
        with self.r.transaction() as s:s['lanes']['provider']['revision']+=1
        self.assertEqual(audit(self.r,self.admission,self.settings)[0]['status'],'pending')

    def test_reviewed_supersession_is_not_integration(self):
        resolve(self.r,self.request('superseded'),self.admission)
        lane=self.r.snapshot()['lanes']['provider']
        self.assertEqual(lane['state'],'done')
        self.assertFalse(lane.get('integration'))
        self.assertTrue(lane['review_disposition']['superseded'])

    def test_stale_pins_and_missing_delivery_attestation_rejected(self):
        request=self.request('superseded');request.pop('no_remaining_delivery')
        with self.assertRaises(Rejected):resolve(self.r,request,self.admission)
        request['no_remaining_delivery']=True
        with self.r.transaction() as s:s['lanes']['provider']['revision']+=1
        with self.assertRaises(Rejected):resolve(self.r,request,self.admission)

    def test_unmapped_unadmitted_and_unavailable_are_not_closed(self):
        self.assertEqual(audit(self.r,self.admission,{}),[])
        self.assertEqual(audit(self.r,dict(status='unavailable'),self.settings),[])
        self.assertEqual(audit(self.r,dict(status='observed',ids=[]),self.settings),[])
        self.assertEqual(self.r.snapshot()['lanes']['provider']['state'],'blocked')

    def test_discovery_nominates_only_and_dashboard_shows_reason(self):
        from workflow.dashboard import render_dashboard
        with self.r.transaction() as s:s['lanes']['provider']['scope']='Kurage57 death observer'
        admission=dict(self.admission,families=[dict(id=57,enum='Kurage',name='Lesser Spotted Jellyfloat')])
        rows=audit(self.r,admission,{})
        self.assertEqual(rows[0]['status'],'pending')
        self.assertEqual(self.r.snapshot()['lanes']['provider']['state'],'blocked')
        self.assertIn('Admitted families with outstanding lane work (1)',
                      render_dashboard({'admission_reconciliation':rows}))

    def test_live_or_unknown_target_and_claimed_delivery_are_protected(self):
        request=self.request('superseded')
        owner=self.r.snapshot()['lanes']['consumer']['process']
        for health in ('alive','unknown'):
            self.r.probe=lambda p:'alive' if p==owner else health
            with self.assertRaises(Rejected):resolve(self.r,request,self.admission)
        self.r.probe=lambda p:'alive' if p==owner else 'dead'
        with self.r.transaction() as s:
            s['throughput']['batches']['active']=dict(state='claimed',candidates={'provider':{}})
        with self.assertRaises(Rejected):resolve(self.r,request,self.admission)

    def test_non_owner_cannot_decide(self):
        request=self.request();request['reviewer']='provider'
        with self.assertRaises(Rejected):resolve(self.r,request,self.admission)
