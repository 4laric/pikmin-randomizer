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
    def test_unrouted_file_never_receives_invented_owner(self):
        self.c.config['shared_review_routing']['files']={};tick(self.c)
        self.assertFalse(self.inbox.exists())
