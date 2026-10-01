"""Compile production receiver logic against observable engine doubles."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class ReceiverOwnershipTests(unittest.TestCase):
    def test_receiver_authority_and_digestion(self):
        engine = Path(__file__).resolve().parents[1] / 'engine'
        compiler = shutil.which('g++')
        if not compiler and Path('C:/msys64/mingw64/bin/g++.exe').exists():
            compiler = 'C:/msys64/mingw64/bin/g++.exe'
        if not compiler:
            self.skipTest('C++ compiler unavailable')
        env = dict(os.environ, PATH=str(Path(compiler).parent) + os.pathsep + os.environ.get('PATH', ''))
        with tempfile.TemporaryDirectory() as temp:
            build = Path(temp)
            shutil.copyfile(engine / 'tools/kurage_receiver_stubs/engine.h', build / 'engine.h')
            for header in ('Creature.h', 'NaviMgr.h', 'Piki.h', 'PikiMgr.h', 'PikiState.h', 'system.h'):
                (build / header).write_text('#include "engine.h"\n')
            for name in ('receiver', 'digestion'):
                with self.subTest(target=name):
                    output = build / (name + '.exe')
                    sources = [engine / f'tools/test_p2_kurage_{name}.cpp']
                    if name == 'receiver':
                        sources.append(engine / 'pc_port/pc_p2_kurage_receiver.cpp')
                    subprocess.run([compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror',
                                    '-I', str(build), '-I', str(engine / 'pc_port'),
                                    *map(str, sources), '-o', str(output)],
                                   check=True, capture_output=True, env=env, timeout=60)
                    result = subprocess.run([str(output)], check=True, capture_output=True,
                                            text=True, env=env, timeout=15)
                    self.assertIn('PASS', result.stdout)
