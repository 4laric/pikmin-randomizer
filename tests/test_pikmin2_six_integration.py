"""Compiled policy checks for the six-family integration candidate."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class SixIntegrationTests(unittest.TestCase):
    def test_compiled_family_policies(self):
        engine = Path(__file__).resolve().parents[1] / 'engine'
        compiler = shutil.which('g++') or ('C:/msys64/mingw64/bin/g++.exe'
            if Path('C:/msys64/mingw64/bin/g++.exe').exists() else None)
        if not compiler:
            self.skipTest('C++ compiler unavailable')
        env = dict(os.environ, PATH=str(Path(compiler).parent) + os.pathsep + os.environ.get('PATH', ''))
        with tempfile.TemporaryDirectory() as temp:
            for name in ('p2_actor_slots_test', 'p2_queen_policy_test', 'p2_king_policy_test',
                         'p2_bigtreasure_test', 'p2_fuefuki_interference_policy_test'):
                with self.subTest(target=name):
                    output = Path(temp) / (name + '.exe')
                    sources = [engine / 'tools' / (name + '.cpp')]
                    if name == 'p2_bigtreasure_test':
                        sources.append(engine / 'pc_port/pc_p2_bigtreasure.cpp')
                    subprocess.run([compiler, '-std=c++17', '-I', str(engine / 'pc_port'),
                                    *map(str, sources), '-o', str(output)],
                                   check=True, capture_output=True, env=env, timeout=60)
                    subprocess.run([str(output)], check=True, capture_output=True, env=env, timeout=15)
