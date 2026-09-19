import unittest
from unittest.mock import patch
from tests import test_planner_pool as fixtures
from workflow.queue_pressure import update,dependents,integration_items
from workflow.autofill import validate_spec
from workflow.handoff import Rejected,digest
from workflow.runner import write

class PressureTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.PlannerPoolTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.r=self.f.reg;self.c=self.f.controller
        self.c.config['queue_pressure']={'enabled':True};self.c.base.mkdir(parents=True,exist_ok=True)
        self.now=10000;self.r.clock=lambda:self.now

    def test_growth_age_completions_and_issue_dependents(self):
        with self.r.transaction() as s:
            s['lanes']['a']={'state':'handoff_ready','issue':1,'handoff_at':9000}
            s['lanes']['b']={'state':'blocked','dependencies':['#1']}
        update(self.c)
        self.now+=120
        with self.r.transaction() as s:s['lanes']['c']={'state':'handoff_ready','issue':2,'handoff_at':self.now}
        update(self.c)
        with self.r.transaction() as s:
            m=s['queue_pressure']['stages']['integration'];self.assertEqual(m['depth'],2)
            self.assertEqual(m['downstream'],1);self.assertGreater(m['arrivals_per_hour'],0)
            self.assertGreater(m['oldest_seconds'],1000);s['lanes']['a']['state']='done'
        self.now+=120;update(self.c)
        with self.r.transaction() as s:self.assertGreater(s['queue_pressure']['stages']['integration']['completions_per_hour'],0)

    def test_integration_partitions_do_not_overlap(self):
        lanes={str(i):{'state':'handoff_ready','issue':i} for i in range(20)}
        a={x['lane'] for x in integration_items(lanes,0)};b={x['lane'] for x in integration_items(lanes,1)}
        self.assertFalse(a&b);self.assertEqual(a|b,set(lanes))

    def test_higher_pressure_support_stage_gets_next_worker(self):
        publication=self.f.settings['planner_pool']['helpers'][0]
        publication.update(kind='publication',review_inboxes=[str(self.f.f.out)])
        write(self.f.f.out/'proposals-new.json',{'items':[self.f.f.make_spec('candidate',906)]})
        spec=self.f.f.make_spec('integration-helper',907);path=self.f.f.out/'integration-template.json';write(path,spec)
        self.f.settings['planner_pool']['helpers'].append(dict(scope='integrate',kind='integration_support',
            bucket=0,buckets=1,template=str(path),sha256=digest(path)))
        with self.r.transaction() as s:
            s['lanes']['handoff']=dict(s['lanes']['one'],lane='handoff',state='handoff_ready',handoff_at=9000,worker_id='other')
            s['queue_pressure']={'stages':{'integration':{'pressure':20},'publication':{'pressure':2}}}
        with patch('workflow.autofill._workers',return_value=[{}]), patch('workflow.autofill._prepare',return_value=True) as prepare:
            self.f.tick()
        self.assertEqual(prepare.call_args.args[1]['id'],'integration-helper-cycle-1')

    def test_preflight_rejects_missing_lane_or_runtime_native(self):
        spec=self.f.f.spec
        spec['lane']['target_level']='runtime'
        with self.assertRaisesRegex(Rejected,'native'):validate_spec(self.r,spec,verified=True)
        spec['lane']['target_level']='tooling';del spec['lane']['lane']
        with self.assertRaisesRegex(Rejected,'lane name'):validate_spec(self.r,spec,verified=True)

    def test_support_precedes_discovery_and_same_snapshot_not_repeated(self):
        helper=self.f.settings['planner_pool']['helpers'][0]
        helper.update(kind='integration_support',bucket=0,buckets=1)
        with self.r.transaction() as s:s['lanes']['handoff']=dict(s['lanes']['one'],lane='handoff',state='handoff_ready',handoff_at=9000,issue=1,handoff=None,worker_id='other')
        with patch('workflow.autofill._workers',return_value=[{}]), patch('workflow.autofill._prepare',return_value=False):self.f.tick()
        with self.r.transaction() as s:
            record=s['throughput_runtime']['autofill']['planner_pool']['scopes']['enemies']
            self.assertIn('Integration review support',record['spec']['instruction'])
            record['completed_at']=0
        self.now+=1000
        with patch('workflow.autofill._workers',return_value=[{}]), patch('workflow.autofill._prepare',return_value=False):self.f.tick()
        with self.r.transaction() as s:self.assertEqual(s['throughput_runtime']['autofill']['planner_pool']['scopes']['enemies']['cycle'],1)

