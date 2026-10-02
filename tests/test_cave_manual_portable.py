"""Launcher mechanics only; no native gameplay acceptance."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from scripts.play_pikmin2_cave import file_lock,linux_runtime_paths,stop_owned_child,verify_libraries

class ManualLauncherTests(unittest.TestCase):
    def test_library_change_missing_and_extra_refuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);lib=root/'lib';lib.mkdir();p=lib/'libexample.so';p.write_bytes(b'original')
            expected={'lib/libexample.so':hashlib.sha256(p.read_bytes()).hexdigest()}
            verify_libraries(root,expected)
            p.write_bytes(b'changed')
            with self.assertRaises(ValueError):verify_libraries(root,expected)
            p.unlink()
            with self.assertRaises(ValueError):verify_libraries(root,expected)
            p.write_bytes(b'original');(lib/'extra.so').write_bytes(b'extra')
            with self.assertRaises(ValueError):verify_libraries(root,expected)

    def test_owned_child_cleanup_leaves_unrelated_child_alive(self):
        owned=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
        other=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
        try:
            stop_owned_child(owned);self.assertIsNotNone(owned.returncode)
            self.assertIsNone(other.poll());stop_owned_child(owned)
        finally:stop_owned_child(owned);stop_owned_child(other)

    def test_process_lock_is_exclusive_then_released(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'launch.lock'
            code="from pathlib import Path;from scripts.play_pikmin2_cave import file_lock;\nwith file_lock(Path(__import__('sys').argv[1])): pass"
            with file_lock(p):
                child=subprocess.run([sys.executable,'-c',code,str(p)],capture_output=True,timeout=10)
                self.assertNotEqual(child.returncode,0)
            child=subprocess.run([sys.executable,'-c',code,str(p)],capture_output=True,timeout=10)
            self.assertEqual(child.returncode,0,child.stderr)

    @unittest.skipIf(os.name=='nt','actual Linux /proc control')
    def test_linux_owned_process_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            executable=Path(tmp)/'nectar.exe';shutil.copy2(Path(sys.executable).resolve(),executable)
            child=subprocess.Popen([str(executable),'-c','import time;time.sleep(30)'])
            try:self.assertIn(str(executable),linux_runtime_paths())
            finally:stop_owned_child(child)

if __name__=='__main__':unittest.main()
