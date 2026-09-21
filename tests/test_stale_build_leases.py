import unittest
from unittest.mock import patch
from tests import test_build_capacity as fixtures
from workflow.build_capacity import update

class StaleBuildLeaseTests(unittest.TestCase):
 def setUp(self):
  self.f=fixtures.BuildCapacityTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
  self.f.enable();self.r=self.f.reg;self.c=self.f.controller
 def lease(self,health='dead',generation=1):
  return dict(lane='owner',generation=generation,token='old',process={'health':health},expires_at=999999)
 def test_dead_running_and_old_generation_reclaimed_without_new_acquisition(self):
  with self.r.transaction() as s:
   s['lanes']['owner']['state']='running'
   s['leases']['build:output/private']=self.lease()
   s['leases']['maintained-build-export']=self.lease(generation=0)
  with patch.object(self.r,'probe',side_effect=lambda p:p['health']):update(self.c);update(self.c)
  s=self.r.snapshot();self.assertFalse(s['leases'])
  self.assertEqual(sum(e['kind']=='lease_reaped' for e in s['events']),2)
  self.assertEqual(s['lanes']['owner']['state'],'running')
  self.assertEqual(s['build_lease_recovery']['remaining'],0)
 def test_expired_live_unknown_and_nonbuild_owners_are_preserved(self):
  with self.r.transaction() as s:
   for key,health in [('build:output/live','alive'),('build:output/unknown','unknown'),('shared-runtime','dead')]:
    s['leases'][key]=dict(self.lease(health),expires_at=0)
  with patch.object(self.r,'probe',side_effect=lambda p:p['health']):update(self.c)
  self.assertEqual(len(self.r.snapshot()['leases']),3)
 def test_current_replacement_identity_is_probed_not_old_owner(self):
  with self.r.transaction() as s:s['leases']['build:output/private']=self.lease()
  with self.r.transaction() as s:s['leases']['build:output/private']=dict(self.lease('alive'),token='new')
  with patch.object(self.r,'probe',side_effect=lambda p:p['health']):update(self.c)
  self.assertEqual(self.r.snapshot()['leases']['build:output/private']['token'],'new')

if __name__=='__main__':unittest.main()
