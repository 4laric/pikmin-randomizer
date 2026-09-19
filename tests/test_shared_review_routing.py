import unittest,json
from tests import test_pikmin2_controller as fixtures
from workflow.shared_review_routing import tick
from workflow.runner import write
from workflow.handoff import digest

class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ControllerTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.c=self.f.controller;self.r=self.f.reg
        self.inbox=self.f.root/'output/inbox';self.c.config['integrator_inbox']=str(self.inbox)
        self.c.config['shared_review_routing']={'enabled':True,'files':{'native/shared.cpp':'provider'}}
        with self.r.transaction() as s:  # Routing sends packets only to an owner that can record the decision.
            s.setdefault('throughput',{}).setdefault('workstreams',{})['routed']=dict(owner_lane='provider',lanes=['consumer'])
        self.path=self.f.out/'handoff.json';self.data={'shared_reviews':[{'file':'native/shared.cpp','status':'requested'}]}
        self.save()
    def save(self):
        write(self.path,self.data)
        with self.r.transaction() as s:s['lanes']['consumer'].update(state='handoff_ready',handoff={'path':str(self.path),'sha256':digest(self.path)})
    def test_delivered_once_consumption_does_not_resolve_then_resend(self):
        tick(self.c);tick(self.c);self.assertEqual(len(list(self.inbox.glob('*.md'))),1)
        with self.r.transaction() as s:self.assertEqual(next(iter(s['shared_review_routes'].values()))['attempts'],1)
        next(self.inbox.glob('*.md')).unlink();tick(self.c);self.assertFalse(list(self.inbox.glob('*.md')))
        self.f.now+=601;tick(self.c);self.assertEqual(len(list(self.inbox.glob('*.md'))),1)
        with self.r.transaction() as s:self.assertEqual(next(iter(s['shared_review_routes'].values()))['status'],'awaiting_owner_decision')
        self.data['shared_reviews'][0]['status']='approved';self.save();tick(self.c)  # A handoff status resolves nothing.
        with self.r.transaction() as s:self.assertEqual(next(iter(s['shared_review_routes'].values()))['status'],'awaiting_owner_decision')
        from workflow.approvals import pins
        with self.r.transaction() as s:
            s['approvals']={'row':dict(id='row',kind='handoff_review',lane='consumer',file='native/shared.cpp',at=1,
                pins=pins(s['lanes']['consumer']),status='approved',reviewer=dict(lane='provider'))}
        tick(self.c)
        with self.r.transaction() as s:self.assertEqual(next(iter(s['shared_review_routes'].values()))['status'],'resolved_or_superseded')
    def test_owner_without_decision_authority_gets_no_packet(self):
        with self.r.transaction() as s:s['throughput']['workstreams']['routed']['owner_lane']='other-owner'
        tick(self.c);tick(self.c)
        self.assertFalse(list(self.inbox.glob('*.md')) if self.inbox.exists() else [])
        state=self.r.snapshot();route=next(iter(state['shared_review_routes'].values()))
        self.assertEqual((route['status'],route['owner']),('owner_cannot_decide','provider'))
        notices=[n for n in state['control']['notices'].values() if n['kind']=='shared_review_owner_cannot_decide']
        self.assertEqual(len(notices),1);self.assertIn('own producer workstream',notices[0]['detail']['error'])
        with self.r.transaction() as s:s['throughput']['workstreams']['routed']['owner_lane']='provider'
        tick(self.c);self.assertEqual(len(list(self.inbox.glob('*.md'))),1)
    def test_unrouted_file_never_receives_invented_owner(self):
        self.c.config['shared_review_routing']['files']={};tick(self.c)
        self.assertFalse(self.inbox.exists())
