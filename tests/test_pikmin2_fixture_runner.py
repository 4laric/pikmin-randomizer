from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import run_pikmin2_fixture as runner
PYTHON = str(Path(sys.prefix) / 'python.exe') if sys.platform == 'win32' else sys.executable


class FixtureRunnerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.run = self.root / 'output/run'; self.run.mkdir(parents=True)
        self.dlls = self.root / 'dlls'; self.dlls.mkdir()
        for name in ['libstdc++-6.dll', 'libgcc_s_seh-1.dll', 'libwinpthread-1.dll']:
            (self.dlls / name).write_bytes(b'test')
        self.patch = patch.object(runner, 'ROOT', self.root)
        self.patch.start(); self.addCleanup(self.patch.stop)

    def assets(self):
        assets = self.run / 'assets/dataDir'; assets.mkdir(parents=True)
        for name in ['consFont.bti', 'bigFont.bti']:
            (assets / name).write_bytes(b'font' * 20)

    def test_empty_arena_fails_before_launch(self):
        with patch.object(runner, 'supervise') as launch:
            result = runner.launch(PYTHON,self.run,[],['PASS'],toolchain=self.dlls)
        launch.assert_not_called()
        self.assertFalse(result['launched'])

    def test_explicit_cwd_runtime_path_and_markers(self):
        self.assets()
        with patch.object(runner, 'supervise', return_value={'passed':True}) as launch:
            runner.launch(PYTHON,self.run,['--test'],['PASS HOST'],toolchain=self.dlls)
        args = launch.call_args.args
        self.assertEqual(args[1],self.run.resolve())
        self.assertEqual(args[2],60)
        self.assertTrue(args[3]['PATH'].startswith(str(self.dlls)))
        self.assertEqual(launch.call_args.kwargs['required_markers'],['PASS HOST'])

    def test_timeout_records_failure(self):
        self.assets()
        result = runner.launch(PYTHON,self.run,
            ['-c','import time; time.sleep(20)'],['PASS HOST'],timeout=.2,toolchain=self.dlls)
        self.assertTrue(result['timed_out'])
        self.assertFalse(result['passed'])

    def test_unrelated_success_marker_cannot_pass(self):
        self.assets()
        result = runner.launch(PYTHON,self.run,
            ['-c','print("PASS OTHER")'],['PASS HOST'],toolchain=self.dlls)
        self.assertFalse(result['passed'])
