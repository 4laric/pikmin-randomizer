import unittest
from unittest.mock import Mock
from tests import test_planner_pool as fixtures
from workflow.setup_healing import dispose_claims,recover_setup
from workflow.runner import write
from workflow.handoff import digest


class HealingTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.PlannerPoolTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.reg=self.f.reg;self.c=self.f.controller
        self.lane='planning-shard-test-cycle-1'
        self.path=self.reg.root/'output/workflow/autofill/planning-shards/test/proposals-one.json'
        self.path.parent.mkdir(parents=True)
        write(self.path,dict(items=[self.f.f.make_spec('unpublished',908)]))
        with self.reg.transaction() as s:
            s.setdefault('control',{})['controller']={'health':'alive'}
            s['lanes'][self.lane]=dict(lane=self.lane,generation=2,state='done',process={'health':'dead'})
            s['planning_claims']={'topic:shard-test':dict(lane=self.lane,generation=1,process={'health':'dead'})}

    def decide(self):
        with self.reg.transaction() as s:
            s['proposal_feedback']={str(self.path):dict(sha256=digest(self.path),evidence=self.f.f.f.evidence,outcome='repair')}

    def count(self):
        with self.reg.transaction() as s:return len(s['planning_claims'])

    def test_disposition_releases_only_reviewed_stopped_claims(self):
        dispose_claims(self.c);self.assertEqual(self.count(),1)
        self.decide()
        with self.reg.transaction() as s:s['lanes'][self.lane]['process']['health']='alive'
        dispose_claims(self.c);self.assertEqual(self.count(),1)
        with self.reg.transaction() as s:s['lanes'][self.lane]['process']['health']='dead'
        dispose_claims(self.c);self.assertEqual(self.count(),0)
        dispose_claims(self.c);self.assertEqual(self.count(),0)

    def test_other_unresolved_proposal_prevents_release(self):
        self.decide();write(self.path.with_name('proposals-other.json'),dict(items=[{'id':'other'}]))
        dispose_claims(self.c);self.assertEqual(self.count(),1)

    def test_setup_resume_is_bounded_and_preserves_existing_sources(self):
        key='runtime-worker'
        with self.reg.transaction() as s:
            s['lanes'][key]=dict(lane=key,state='blocked',target_level='runtime',root={'head':'root'},
                native={'head':'already-created'},outcome={'summary':'provisioned native:null'},process={'health':'dead'})
        self.c.config['lanes']={key:{}};self.c.config['models']=['model'];self.c.available=Mock(return_value=True)
        self.reg.recovery_safe=Mock(return_value=False);self.reg.plan_launch=Mock(return_value={'id':'launch'})
        recover_setup(self.c);self.reg.plan_launch.assert_not_called()
        self.reg.recovery_safe.return_value=True
        recover_setup(self.c);recover_setup(self.c)
        self.assertEqual(self.reg.plan_launch.call_count,1)
        self.assertIn('CURRENT registry',self.reg.plan_launch.call_args.args[2])
        with self.reg.transaction() as s:self.assertEqual(s['lanes'][key]['native'],{'head':'already-created'})

