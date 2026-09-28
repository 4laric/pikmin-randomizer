from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BlendTests(unittest.TestCase):
    def test_compiled_coordinator(self):
        compiler = shutil.which("g++")
        if not compiler:
            self.skipTest("g++ required")
        with tempfile.TemporaryDirectory() as directory:
            exe = Path(directory) / "blend.exe"
            built = subprocess.run(
                [compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror",
                 "-I", str(ROOT / "engine/pc_port"),
                 str(ROOT / "engine/tools/test_p2_blend_player.cpp"), "-o", str(exe)],
                capture_output=True, text=True, timeout=90)
            self.assertEqual(built.returncode, 0, built.stderr)
            run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=15)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn("PASS blend player", run.stdout)
            print(run.stdout.strip())


if __name__ == "__main__":
    unittest.main()
