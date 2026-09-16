import unittest
from tests.test_planner_pool import PlannerPoolTests
from workflow.proposal_feedback import record
from workflow.planner_pool import review_pending
from workflow.handoff import digest, Rejected
from workflow.runner import write


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.f=PlannerPoolTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.reg=self.f.reg
        self.path=self.f.f.out/'proposals-rejected.json'
        write(self.path,dict(items=[self.f.f.make_spec('unpublished',905)]))
        self.helper=dict(review_inboxes=[str(self.f.f.out)])
        with self.reg.transaction() as s:
            s['lanes']['publication-review-test']=dict(generation=1,state='running',process={'health':'alive'})
        self.args=dict(lane='publication-review-test',generation=1,proposal=str(self.path),
            sha256=digest(self.path),outcome='repair',reason='Missing lane name',evidence=self.f.f.f.evidence)

    def pending(self):return review_pending(self.reg,self.f.settings,self.helper)

    def test_repair_suppresses_unchanged_and_new_bytes_wake(self):
        self.assertTrue(self.pending());record(self.reg,**self.args);self.assertFalse(self.pending())
        self.path.write_text('{"items":[{"id":"corrected"}]}')
        self.assertTrue(self.pending())

    def test_dependency_wakes_only_when_done(self):
        self.args.update(outcome='dependency',wait_for_lanes=['one'])
        with self.reg.transaction() as s:s['lanes']['one']['state']='handoff_ready'
        record(self.reg,**self.args);self.assertFalse(self.pending())
        with self.reg.transaction() as s:s['lanes']['one']['state']='done'
        self.assertTrue(self.pending())

    def test_repair_routes_discovery_instead_of_review(self):
        record(self.reg,**self.args)
        self.f.settings['planner_pool']['helpers'][0]['defer_for_review']=[str(self.f.f.out)]
        self.f.tick()
        with self.reg.transaction() as s:
            instruction=s['throughput_runtime']['autofill']['planner_pool']['scopes']['enemies']['spec']['instruction']
        self.assertIn('Missing lane name',instruction)
        self.assertIn('corrected uniquely named',instruction)

    def test_generation_hash_and_terminal_report_fences(self):
        for change in (dict(generation=2),dict(sha256='0'*64),dict(evidence={'path':'missing','sha256':'0'*64})):
            with self.assertRaises((Rejected, OSError)):record(self.reg,**(self.args|change))
        with self.reg.transaction() as s:s['lanes']['publication-review-test']['state']='done'
        with self.assertRaises(Rejected):record(self.reg,**self.args)
        with self.reg.transaction() as s:
            s['lanes']['publication-review-test']['review']={'evidence':{'review':self.args['evidence']}}
        record(self.reg,**self.args);self.assertFalse(self.pending())
