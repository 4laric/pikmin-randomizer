import unittest
from unittest.mock import patch
from tests.test_consumer_wakeup import ConsumerWakeupTests
from workflow.action_routing import routes, tick, integration_work
from workflow.dependency_classification import signature

class ActionRoutingTests(unittest.TestCase):
 def setUp(self):
  self.f=ConsumerWakeupTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
  self.r,self.c=self.f.r,self.f.c
  with self.r.transaction() as s:
   s['dependency_classifications']={'finding':dict(id='finding',at=1,consumer='consumer',snapshot=signature(s['lanes']['consumer']),evidence=self.f.f.ev,
    dispositions=[dict(requirement='owned runtime check',check='run guarded original consumer',reason='source inspected',internal_blocker=dict(kind='owner_blocked',owner_lane='consumer',inspected_lanes=['consumer'],missing='owner runtime proof',next_action='run existing consumer'))])}
 def test_resume_once_without_clearing_dependencies(self):
  tick(self.c);tick(self.c)
  launches=list(self.r.control_status()['launches'].values());self.assertEqual(len(launches),1)
  self.assertTrue(launches[0]['reason'].startswith('internal-owner-resume:'))
  self.assertEqual(self.r.snapshot()['lanes']['consumer']['state'],'blocked')
  with self.r.transaction() as s:
   for v in s['control']['launches'].values():v['status']='exited'
   s['lanes']['consumer']['generation']+=1
  tick(self.c);self.assertEqual(len(self.r.control_status()['launches']),1)
 def test_live_owner_protected(self):
  with patch.object(self.r,'recovery_safe',return_value=False):tick(self.c)
  self.assertFalse(self.r.control_status()['launches'])
 def test_landing_routes_to_registered_integrator_not_planner(self):
  s=self.r.snapshot();s['throughput']={'workstreams':{'x':{'owner_lane':'integrator','lanes':['consumer']}}}
  s['lanes']['provider']['native']={'head':'a'*40}
  request=dict(consumer='consumer',findings=[dict(kind='missing_producer',missing='source landing',next_action='land pinned source',inspected_lanes=['provider'])])
  result=routes(s,request);self.assertEqual([(x['kind'],x['owner']) for x in result],[('integration','integrator')])
 def test_non_landing_missing_producer_stays_planning(self):
  request=dict(consumer='consumer',findings=[dict(kind='missing_producer',missing='engine behavior',next_action='implement callsite',inspected_lanes=[])])
  self.assertEqual(routes(self.r.snapshot(),request)[0]['kind'],'planning')

if __name__=='__main__':unittest.main()
