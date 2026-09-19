import copy
import unittest
from contextlib import contextmanager
from unittest.mock import Mock
from workflow.handoff import Rejected
from workflow.review_followup import pin, record, deferred, require_dispositions


class ReviewFollowupTests(unittest.TestCase):
    def setUp(self):
        self.lane = dict(lane='report',generation=2,state='review_ready',review={'evidence':'original'})
        self.state = dict(lanes={'report':self.lane,
            'owner':dict(generation=3,state='running',process={'pid':1}),
            'prerequisite':dict(generation=1,state='blocked')},
            throughput={'workstreams':{'s':dict(owner_lane='owner',lanes=['report'])}},
            control={'launches':{'l':dict(lane='owner',bound_generation=3,
                review_obligations=[dict(lane='report',pin=pin(self.lane))])}})
        self.reg = Mock()
        @contextmanager
        def transaction():
            yield self.state
        self.reg.transaction = transaction
        def lane(state,key,generation=None):
            value=state['lanes'][key]
            if generation is not None and generation != value['generation']:raise Rejected('generation')
            return value
        self.reg.lane.side_effect=lane
        self.reg.probe.return_value='alive'
        self.reg.archive_evidence.side_effect=lambda e:e
        self.args=dict(key='report',generation=2,review_pin=pin(self.lane),reviewer='owner',
            reviewer_generation=3,waiting_on='prerequisite',next_action='Land the maintained change after prerequisite receipt',
            reason='Exact prerequisite source is missing',evidence={'path':'report','sha256':'hash'})

    def test_standby_requires_disposition_and_deferral_is_not_acceptance(self):
        with self.assertRaises(Rejected):require_dispositions(self.state,'owner',3)
        record(self.reg,**self.args)
        require_dispositions(self.state,'owner',3)
        self.assertEqual(self.lane['state'],'review_ready')
        self.assertNotIn('integration',self.lane)

    def test_prerequisite_completion_or_source_change_reopens_demand(self):
        record(self.reg,**self.args)
        self.assertTrue(deferred(self.state,'report'))
        self.state['lanes']['prerequisite']['root']={'head':'new'}
        self.assertFalse(deferred(self.state,'report'))
        with self.assertRaises(Rejected):require_dispositions(self.state,'owner',3)
        self.state['lanes']['prerequisite']['state']='done'
        with self.assertRaises(Rejected):record(self.reg,**self.args)

    def test_stale_unknown_self_or_unauthorized_decisions_rejected(self):
        for mode in ('pins','generation','self','owner','dead','unknown'):
            with self.subTest(mode=mode):
                args=copy.deepcopy(self.args)
                if mode=='pins':args['review_pin']='stale'
                if mode=='generation':args['reviewer_generation']=1
                if mode=='self':args['waiting_on']='report'
                if mode=='owner':args['waiting_on']='owner'
                if mode in ('dead','unknown'):self.reg.probe.return_value=mode
                with self.assertRaises(Rejected):record(self.reg,**args)
                self.reg.probe.return_value='alive'

    def test_resumed_or_accepted_review_satisfies_obligation(self):
        for state in ('running','done'):
            self.lane['state']=state
            require_dispositions(self.state,'owner',3)


if __name__ == '__main__':unittest.main()
