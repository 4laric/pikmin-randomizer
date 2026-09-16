import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.test_pikmin2_surface_native import FixtureProcess, expected_receipts, run_test


class DriverTests(unittest.TestCase):
    def test_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileExistsError): run_test(SimpleNamespace(output=Path(directory)))
    def test_timeout_limits(self):
        for value in (0, 301):
            with self.assertRaises(ValueError): FixtureProcess(value)
    def test_fixture_exec_receives_timeout_and_dummy_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            (run/'p2-cave-entry.txt').write_text('P2_CAVE_ENTRY_1\ntoken\n1 1 1\n1 0\n')
            process = FixtureProcess(45, 'extinction')
            with patch('scripts.test_pikmin2_surface_native.subprocess.run', return_value=SimpleNamespace(returncode=42)) as launch:
                self.assertEqual(process(['fixture'], cwd=run).returncode, 42)
            self.assertEqual(launch.call_args.kwargs['timeout'], 45)
            self.assertEqual(launch.call_args.kwargs['env']['SDL_AUDIODRIVER'], 'dummy')
            self.assertTrue((run/'p2-cave-extinction.txt').exists())
    def test_restore_requires_native_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            (run/'p2-cave-entry.txt').write_text('P2_CAVE_ENTRY_1\ntoken\n2 1 1\n1 0\n')
            (run/'native.log').write_text('not a pass')
            with patch('scripts.test_pikmin2_surface_native.subprocess.run', return_value=SimpleNamespace(returncode=0)):
                with self.assertRaises(AssertionError): FixtureProcess(30,'restore_floor2')(['fixture'],cwd=run)
    def test_default_expected_receipts(self):
        self.assertEqual(sum(expected_receipts(None).values()), 380)

if __name__ == '__main__': unittest.main()
