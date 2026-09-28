import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPILER = Path('C:/msys64/mingw64/bin/g++.exe')
PRIVATE_BTK = Path(r'C:/Users/alari/pikmin-randomizer/output/p2-kimi-bulblax/output/p234-import/Queen/queenchappy_model.btk')


def include_dir():
    candidates = []
    if os.environ.get('P2_NATIVE_PC_PORT'):
        candidates.append(Path(os.environ['P2_NATIVE_PC_PORT']))
    candidates += [ROOT / 'engine' / 'pc_port', ROOT / 'native' / 'pc_port',
                   ROOT.parent / 'p2-kimi-bulblax-native' / 'pc_port']
    return next((c for c in candidates if (c / 'pc_p2_btk.h').is_file()), None)


@unittest.skipUnless(COMPILER.is_file(), 'MinGW g++ required')
class BtkPolicyTests(unittest.TestCase):
    def compile_and_run(self, btk_file=None):
        include = include_dir()
        self.assertIsNotNone(include, 'pc_p2_btk.h not found')
        with tempfile.TemporaryDirectory(prefix='p2-btk-policy-') as tmp:
            exe = Path(tmp) / 'btk_policy.exe'
            env = dict(os.environ, PATH=str(COMPILER.parent) + os.pathsep + os.environ.get('PATH', ''))
            subprocess.run([str(COMPILER), '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', str(include),
                            str(ROOT / 'tests' / 'pikmin2_btk_policy.cpp'), '-o', str(exe)],
                           check=True, capture_output=True, env=env)
            if btk_file is not None:
                env['P2_BTK_FILE'] = str(btk_file)
            return subprocess.run([str(exe)], capture_output=True, text=True, env=env)

    def test_synthetic_parse_and_reject(self):
        result = self.compile_and_run()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('P2_BTK_POLICY_PASS', result.stdout)

    def test_real_queen_btk_samples(self):
        if not PRIVATE_BTK.is_file():
            self.skipTest('private Bulblax import BTK not present')
        result = self.compile_and_run(PRIVATE_BTK)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('P2_BTK_POLICY_PASS', result.stdout)
        self.assertIn('P2_BTK_POLICY file=', result.stdout)
        self.assertIn('duration=30', result.stdout)


if __name__ == '__main__':
    unittest.main()
