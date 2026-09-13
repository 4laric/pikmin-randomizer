import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from experimental.pikmin2_motion_events import registry, encode, write

ROOT = Path(__file__).resolve().parents[1]
LOCAL = Path("C:/Users/alari/pikmin-randomizer/output/p2-kimi-bulblax/output/p234-import")


class RegistryTests(unittest.TestCase):
    def test_order_and_editor_path_not_used(self):
        self.assertEqual(registry(b"1 { Z:\\outside\\a.bca a.bca 0 0 3 2 3 3 9 1 -1 }"),
                         [("a.bca", [(0,0),(3,2),(3,3),(9,1)])])

    def test_refusals(self):
        cases = [b"", b"257", b"1 { x ../a.bca -1 }", b"1 { x a.bca 2 -1 }",
                 b"1 { x a.bca 0 1 -1 }", b"1 { x a.bca 0 0 0 1 -1 }",
                 b"1 { x a.bca 2 2 1 2 -1 }", b"1 { x a.bca 1 1000 -1 }",
                 b"1 { x a.bca -1 } trailing", b"1 { x a.bca -1",
                 b"2 { x a.bca -1 } { x a.bca -1 }"]
        for raw in cases:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                registry(raw)

    def test_bca_failure_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "enemyanimmgr.txt").write_bytes(b"1 { x a.bca -1 }")
            (root / "a.bca").write_bytes(b"bad")
            with self.assertRaises(ValueError): write(root, root / "result")
            self.assertFalse((root / "result").exists())


class NativeTests(unittest.TestCase):
    def test_compiled_parser_and_real_sources(self):
        compiler = shutil.which("g++")
        if not compiler: self.skipTest("g++ required")
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            exe = temp / "probe.exe"
            built = subprocess.run([compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror",
                                    "-I", str(ROOT / "engine/pc_port"),
                                    str(ROOT / "engine/tools/test_p2_motion_events.cpp"), "-o", str(exe)],
                                   capture_output=True, text=True, timeout=90)
            self.assertEqual(built.returncode, 0, built.stderr)
            paths = []
            for species in ("Queen", "Baby", "KingChappy"):
                directory = LOCAL / species
                if not directory.exists(): continue
                data = encode(directory)
                self.assertEqual(data, encode(directory))
                self.assertIn(hashlib.sha256((directory/"enemyanimmgr.txt").read_bytes()).hexdigest().encode(), data)
                dest = temp / (species + ".txt")
                write(directory, dest)
                self.assertEqual(data, dest.read_bytes())
                with self.assertRaises(FileExistsError): write(directory, dest)
                self.assertEqual(data, dest.read_bytes())
                paths.append(str(dest))
            run = subprocess.run([str(exe), *paths], capture_output=True, text=True, timeout=15)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn("PASS retail event tables", run.stdout)
            print(run.stdout.strip())


if __name__ == "__main__": unittest.main()
