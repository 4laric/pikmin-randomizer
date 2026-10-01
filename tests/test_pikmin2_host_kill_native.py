import json
from pathlib import Path
import tempfile
import unittest
from scripts.test_pikmin2_host_kill_native import kill_at_marker

class OwnedProcess:
    pid=12345
    returncode=None
    killed=False
    def poll(self):return self.returncode
    def kill(self):self.killed=True;self.returncode=1
    def wait(self,timeout):return self.returncode

class HostKillTests(unittest.TestCase):
    def test_only_matching_owned_pid_is_terminated(self):
        with tempfile.TemporaryDirectory() as d:
            marker=Path(d)/'marker.json';p=OwnedProcess()
            marker.write_text(json.dumps(dict(pid=54321,boundary='handoff')))
            with self.assertRaises(RuntimeError):kill_at_marker(p,marker,'handoff',1)
            self.assertFalse(p.killed)
            marker.write_text(json.dumps(dict(pid=p.pid,boundary='handoff')))
            result=kill_at_marker(p,marker,'handoff',1)
            self.assertTrue(p.killed);self.assertEqual(result['pid'],p.pid)
    def test_wrong_boundary_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            marker=Path(d)/'marker.json';p=OwnedProcess()
            marker.write_text(json.dumps(dict(pid=p.pid,boundary='commit')))
            with self.assertRaises(RuntimeError):kill_at_marker(p,marker,'handoff',1)
            self.assertFalse(p.killed)
    def test_completed_host_not_killed(self):
        p=OwnedProcess();p.returncode=0
        with self.assertRaises(RuntimeError):kill_at_marker(p,Path('unused'),'handoff',1)
        self.assertFalse(p.killed)
