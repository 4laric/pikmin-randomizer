import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('cave_runner', Path(__file__).parents[1] / 'scripts/run_pikmin2_cave_fixture.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class CaveRunnerTests(unittest.TestCase):
    def test_timeout_writes_failure_and_reaps_child(self):
        with tempfile.TemporaryDirectory() as temp:
            result = runner.supervise([sys.executable, '-c', 'import time; print("starting", flush=True); time.sleep(30)'], temp, .5)
            self.assertTrue(result['timed_out'])
            self.assertFalse(result['passed'])
            self.assertIsNotNone(result['exit_code'])
            self.assertIn('starting', (Path(temp) / 'native.log').read_text())
            self.assertEqual(json.loads((Path(temp) / 'run-result.json').read_text()), result)

    def test_success_requires_real_markers_and_zero_exit(self):
        with tempfile.TemporaryDirectory() as temp:
            for code, passed in [('', False), ('print(' + repr('\n'.join(runner.MARKERS)) + ')', True),
                                 ('print(' + repr('\n'.join(runner.MARKERS)) + '); raise SystemExit(86)', False),
                                 ('print(' + repr('\n'.join(runner.MARKERS) + '\nP2_FIXTURE_CAPTAIN_DOWN') + ')', False)]:
                result = runner.supervise([sys.executable, '-c', code], temp, 5)
                self.assertEqual(result['passed'], passed)

    def test_launch_error_still_records_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(OSError):
                runner.supervise([str(Path(temp) / 'missing.exe')], temp, 1)
            result = json.loads((Path(temp) / 'run-result.json').read_text())
            self.assertFalse(result['passed'])
            self.assertIn('error', result)

    @unittest.skipUnless(os.name == 'nt', 'Windows junction regression')
    def test_file_junction_becomes_readable_private_file(self):
        import _winapi
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source'; source.mkdir()
            font = root / 'font.bti'; font.write_bytes(b'original-font')
            _winapi.CreateJunction(str(font), str(source / 'consFont.bti'))
            assets = root / 'assets'; assets.mkdir()
            (assets / 'sequence').write_bytes(b'audio')
            _winapi.CreateJunction(str(assets), str(source / 'SndData'))
            output = root / 'output'
            runner.clone_assets(source, output)
            copied = output / 'consFont.bti'
            self.assertTrue(copied.is_file())
            self.assertFalse(copied.is_junction())
            self.assertEqual(copied.read_bytes(), font.read_bytes())
            copied.write_bytes(b'private')
            self.assertEqual(font.read_bytes(), b'original-font')
            self.assertEqual((output / 'SndData/sequence').read_bytes(), b'audio')


if __name__ == '__main__':
    unittest.main()
