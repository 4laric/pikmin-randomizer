"""Compile the exported engine component, including existing consumer examples."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SourceClockTests(unittest.TestCase):
    def test_native_clock_and_existing_consumers(self):
        self.compile_probe("source")

    def test_native_display_adapter(self):
        self.compile_probe("display")

    def compile_probe(self, name):
        compiler = shutil.which("g++")
        if compiler is None:
            self.skipTest("g++ is required for the native source clock probe")
        with tempfile.TemporaryDirectory() as directory:
            exe = Path(directory) / ("clock.exe" if os.name == "nt" else "clock")
            built = subprocess.run(
                [compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror",
                 "-I", str(ROOT / "engine/pc_port"),
                 str(ROOT / f"engine/tools/test_p2_{name}_clock.cpp"), "-o", str(exe)],
                capture_output=True, text=True, timeout=90,
            )
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=15)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn(f"PASS {name} clock:", run.stdout)


if __name__ == "__main__":
    unittest.main()
