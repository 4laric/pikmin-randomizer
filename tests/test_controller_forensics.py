"""A crashed controller leaves its traceback, saved logs and a restart event behind."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from tests import test_pikmin2_controller as fixtures
from workflow.controller import record_restart

REPO = Path(__file__).resolve().parents[1]


def entry():
    spec = importlib.util.spec_from_file_location('pikmin2_controller_entry', REPO / 'scripts/pikmin2_controller.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


class RestartRecordTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ControllerTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)

    def test_wrapper_note_becomes_one_event(self):
        base = self.f.controller.base
        note = dict(previous_pid=321, exit_code=1, stderr_log=str(base / 'controller.20260919T062940Z.exit1.stderr.log'),
                    stdout_log=None, stamp='20260919T062940Z', at=1789799380)
        (base / 'controller-exit.json').write_text('\ufeff' + json.dumps(note), encoding='utf-8')  # PowerShell writes a BOM.
        detail = dict(note, exited_at=note.pop('at'))
        self.assertEqual(record_restart(self.f.reg, base), detail)
        self.assertIsNone(record_restart(self.f.reg, base))
        events = [e for e in self.f.reg.snapshot()['events'] if e['kind'] == 'controller_restarted_after_exit']
        self.assertEqual(len(events), 1)
        self.assertEqual((events[0]['previous_pid'], events[0]['exit_code']), (321, 1))
        self.assertTrue((base / 'controller-exit.recorded.json').is_file())

    def test_damaged_note_never_blocks_startup(self):
        base = self.f.controller.base
        (base / 'controller-exit.json').write_bytes(b'\0' * 16)
        self.assertIsNone(record_restart(self.f.reg, base))
        self.assertTrue((base / 'controller-exit.json').is_file())


class FatalTracebackTests(unittest.TestCase):
    def test_unhandled_startup_exception_writes_error_json_and_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            config = root / 'config.json'
            config.write_text(json.dumps(dict(output='output/workflow/controller', lanes={}, models=['a/b'])))
            self.assertEqual(entry().run(['--root', str(root), '--config', str(config), '--once']), 1)
            error = json.loads((root / 'output/workflow/controller/error.json').read_text())
            self.assertEqual(error['stage'], 'fatal')
            self.assertIn('Registry missing', error['traceback'])

    def test_output_outside_private_root_is_not_written(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            config = root / 'config.json'
            config.write_text(json.dumps(dict(output='../escape', lanes={})))
            self.assertEqual(entry().run(['--root', str(root / 'ws'), '--config', str(config), '--once']), 1)
            self.assertFalse((root / 'escape' / 'error.json').exists())


@unittest.skipUnless(os.name == 'nt' and shutil.which('powershell.exe'), 'Restart wrapper is Windows PowerShell')
class WrapperTests(unittest.TestCase):
    STUB = '''
import sys
from pathlib import Path
root = Path(sys.argv[sys.argv.index('--root') + 1])
count = root / 'runs'
n = int(count.read_text()) if count.exists() else 0
count.write_text(str(n + 1))
print('controller stdout run %d' % n)
print('Traceback (most recent call last): crash in run %d' % n, file=sys.stderr)
sys.exit(3 if n == 0 else 0)
'''

    def test_failed_run_logs_are_preserved_pruned_and_noted(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            scripts = root / 'scripts'; scripts.mkdir()
            shutil.copy(REPO / 'scripts/Start-Pikmin2Controller.ps1', scripts)
            (scripts / 'pikmin2_controller.py').write_text(self.STUB, encoding='utf-8')
            config = root / 'config.json'
            config.write_text(json.dumps(dict(output='output/controller')))
            output = root / 'output/controller'; output.mkdir(parents=True)
            for i in range(3):  # Older saved crashes beyond the retention count are pruned.
                (output / ('controller.2020010%dT000000Z.exit1.stderr.log' % i)).write_text('old')
            result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                str(scripts / 'Start-Pikmin2Controller.ps1'), '-WorkspaceRoot', str(root), '-Config', str(config),
                '-Python', sys.executable, '-RestartDelaySeconds', '0', '-KeepCrashLogs', '2'],
                capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / 'runs').read_text(), '2')
            saved = sorted(p.name for p in output.glob('controller.*.exit*.stderr.log'))
            self.assertEqual(len(saved), 2)
            self.assertEqual(saved[0], 'controller.20200102T000000Z.exit1.stderr.log')
            crash = output / saved[-1]
            self.assertIn('.exit3.', crash.name)
            self.assertIn('crash in run 0', crash.read_text())
            self.assertIn('crash in run 1', (output / 'controller.stderr.log').read_text())
            note = json.loads((output / 'controller-exit.json').read_text(encoding='utf-8-sig'))
            self.assertEqual(note['exit_code'], 3)
            self.assertEqual(Path(note['stderr_log']), crash)
            self.assertIsInstance(note['previous_pid'], int)


if __name__ == '__main__':
    unittest.main()
