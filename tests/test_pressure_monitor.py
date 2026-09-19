import threading
import unittest
from unittest.mock import patch
from tests.test_queue_pressure import PressureTests
from workflow.queue_pressure import start_monitor, update

class PressureMonitorTests(unittest.TestCase):
 def setUp(self):
  self.f=PressureTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
 def test_single_monitor_refreshes_without_main_tick(self):
  seen=threading.Event()
  with patch('workflow.queue_pressure.update',side_effect=lambda c:seen.set()):
   stop=start_monitor(self.f.c)
   try:
    self.assertIs(stop,start_monitor(self.f.c));self.assertTrue(seen.wait(3))
   finally:stop.set()
 def test_proposal_scan_reuses_single_registry_snapshot(self):
  from workflow.runner import write
  root=self.f.r.root/'output/workflow/autofill/planning-shards/test';root.mkdir(parents=True)
  for i in range(3):write(root/('proposals-'+str(i)+'.json'),{'items':[]})
  with patch.object(self.f.r,'snapshot',wraps=self.f.r.snapshot) as snapshot:
   update(self.f.c)
   self.assertEqual(snapshot.call_count,1)

if __name__=='__main__':unittest.main()
