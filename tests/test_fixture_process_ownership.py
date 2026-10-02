"""Harmless process controls; no game, broker or native executable is launched."""
from contextlib import ExitStack
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
spec = importlib.util.spec_from_file_location('owned_cave_runner', SCRIPTS / 'run_pikmin2_cave_fixture.py')
runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
platform = sys.modules['fixture_platform']  # The exact module used by runner.


class SourceOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(platform, 'is_windows', return_value=False))
        for name, value in [('SIGCHLD', 17), ('SIGKILL', 9)]:
            self.stack.enter_context(patch.object(platform.signal, name, value, create=True))
        for name, value in [('P_PID', 1), ('WNOWAIT', 0x1000000), ('WEXITED', 4), ('WNOHANG', 1),
                            ('CLD_EXITED', 1), ('CLD_KILLED', 2), ('CLD_DUMPED', 3)]:
            self.stack.enter_context(patch.object(platform.os, name, value, create=True))
        self.stack.enter_context(patch.object(platform.signal, 'getsignal', return_value=signal.SIG_DFL))
        self.proc = SimpleNamespace(pid=771234, returncode=None, args=['fake source control'])
        def wait(**kwargs):
            self.proc.returncode = 0; return 0
        self.proc.wait = Mock(side_effect=wait)
        event = SimpleNamespace(si_pid=self.proc.pid, si_code=1, si_status=0)
        self.waitid = self.stack.enter_context(patch.object(platform.os, 'waitid', return_value=event, create=True))
        self.stack.enter_context(patch.object(platform.os, 'getpgid', return_value=self.proc.pid, create=True))
        self.stack.enter_context(patch.object(platform.os, 'getsid', return_value=self.proc.pid, create=True))
        def killpg(pid, sig):
            if sig == 0: raise ProcessLookupError()
        self.killpg = self.stack.enter_context(patch.object(platform.os, 'killpg', side_effect=killpg, create=True))

    def test_exit_observation_retains_child_until_one_idempotent_group_retirement(self):
        self.assertEqual(0, platform.wait_owned_process(self.proc, 1))
        self.proc.wait.assert_not_called()
        receipt = platform.terminate_owned_process(self.proc)
        self.assertTrue(receipt['leader_retained_until_signal'])
        self.assertTrue(receipt['child_reaped']); self.assertTrue(receipt['group_absent'])
        self.assertIs(receipt, platform.terminate_owned_process(self.proc))
        self.assertEqual(1, len([c for c in self.killpg.call_args_list if c.args[1] == 9]))
        self.proc.wait.assert_called_once()
        self.assertTrue(self.waitid.call_args.args[2] & platform.os.WNOWAIT)

    def test_reaped_leader_refuses_all_group_signals(self):
        self.proc.returncode = 0
        for _ in range(2):
            with self.assertRaisesRegex(RuntimeError, 'already reaped'):
                platform.terminate_owned_process(self.proc)
        self.killpg.assert_not_called()

    def test_unknown_child_refuses_all_group_signals(self):
        self.waitid.side_effect = ChildProcessError('ECHILD')
        with self.assertRaisesRegex(RuntimeError, 'identity lost'):
            platform.terminate_owned_process(self.proc)
        self.killpg.assert_not_called()

    def test_changed_session_or_group_refuses_signal(self):
        for name in ('getpgid', 'getsid'):
            with self.subTest(name=name), patch.object(platform.os, name, return_value=2):
                proc = SimpleNamespace(pid=771234, returncode=None, args=['fake'])
                with self.assertRaisesRegex(RuntimeError, 'original private session'):
                    platform.terminate_owned_process(proc)
        self.killpg.assert_not_called()

    def test_changed_sigchld_policy_refuses_signal(self):
        with patch.object(platform.signal, 'getsignal', return_value=signal.SIG_IGN):
            with self.assertRaisesRegex(RuntimeError, 'default SIGCHLD'):
                platform.owned_process_options()
            with self.assertRaisesRegex(RuntimeError, 'policy changed'):
                platform.terminate_owned_process(self.proc)
        self.killpg.assert_not_called()

    def test_interrupted_observation_retries_without_reaping(self):
        event = self.waitid.return_value
        self.waitid.side_effect = [InterruptedError(), event]
        self.assertEqual(0, platform.wait_owned_process(self.proc, 1))
        self.proc.wait.assert_not_called(); self.killpg.assert_not_called()

    def test_interruptions_cannot_extend_observation_deadline(self):
        self.waitid.side_effect = InterruptedError()
        with patch.object(platform.time, 'monotonic', side_effect=[0, 0, 2]):
            with self.assertRaises(subprocess.TimeoutExpired):
                platform.wait_owned_process(self.proc, 1)
        self.killpg.assert_not_called()

    def test_exit_signal_and_nonzero_status_are_preserved(self):
        for code, status, expected in ((1, 23, 23), (2, 9, -9), (3, 11, -11)):
            with self.subTest(code=code):
                self.waitid.return_value = SimpleNamespace(si_pid=self.proc.pid, si_code=code, si_status=status)
                self.assertEqual(expected, platform.wait_owned_process(self.proc, 1))
        self.proc.wait.assert_not_called()

    def test_missing_group_witness_is_failure_without_another_kill(self):
        self.killpg.side_effect = None
        with patch.object(platform.time, 'monotonic', side_effect=[0, .1, 3]):
            with self.assertRaisesRegex(RuntimeError, 'absence not witnessed'):
                platform.terminate_owned_process(self.proc)
        with self.assertRaisesRegex(RuntimeError, 'absence not witnessed'):
            platform.terminate_owned_process(self.proc)
        self.assertEqual(1, len([c for c in self.killpg.call_args_list if c.args[1] == 9]))
        self.assertTrue(self.proc._fixture_cleanup['child_reaped'])
        self.assertFalse(self.proc._fixture_cleanup['group_absent'])

    def test_disappeared_original_group_is_not_success(self):
        self.killpg.side_effect = ProcessLookupError()
        with self.assertRaisesRegex(RuntimeError, 'disappeared before retirement'):
            platform.terminate_owned_process(self.proc)
        self.proc.wait.assert_not_called()
        self.assertFalse(self.proc._fixture_cleanup['group_absent'])


@unittest.skipUnless(sys.platform == 'linux', 'actual harmless Linux process controls')
class ActualLinuxOwnershipTests(unittest.TestCase):
    def setUp(self):
        evidence = os.environ.get('FIXTURE_OWNERSHIP_EVIDENCE_DIR')
        if evidence:
            self.directory = Path(evidence).resolve() / self._testMethodName
            self.directory.mkdir(parents=True, exist_ok=False)
        else:
            self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
            self.directory = Path(self.temp.name)

    def supervise(self, code, timeout=2):
        return runner.supervise([sys.executable, '-c', code], self.directory, timeout)

    def test_actual_normal_exit_and_cleanup_with_foreign_sentinel_untouched(self):
        sentinel = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(10)'], start_new_session=True)
        try:
            result = self.supervise('print(' + repr('\n'.join(runner.MARKERS)) + ')')
            self.assertTrue(result['passed']); self.assertTrue(result['cleanup']['group_absent'])
            self.assertEqual(1, result['cleanup']['signal_attempts'])
            self.assertIsNone(sentinel.poll())
            (self.directory / 'foreign-sentinel.json').write_text(json.dumps({'pid':sentinel.pid, 'still_alive_after_fixture_cleanup':sentinel.poll() is None})+'\n')
        finally:
            sentinel.kill(); sentinel.wait(timeout=2)

    def test_actual_early_exit_cleans_surviving_same_group_descendant(self):
        code = ('import subprocess,sys; p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(10)"]);'
                ' print("descendant="+str(p.pid),flush=True); print(' + repr('\n'.join(runner.MARKERS)) + ')')
        result = self.supervise(code)
        self.assertTrue(result['passed']); self.assertTrue(result['cleanup']['group_absent'])
        self.assertTrue(result['cleanup']['leader_retained_until_signal'])

    def test_actual_timeout_cleans_entire_group_and_reaps_leader(self):
        code = ('import subprocess,sys,time;p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(10)"]);'
                'print("started",flush=True);time.sleep(10)')
        result = self.supervise(code, .2)
        self.assertTrue(result['timed_out']); self.assertFalse(result['passed'])
        self.assertEqual(-signal.SIGKILL, result['exit_code'])
        self.assertTrue(result['cleanup']['child_reaped']); self.assertTrue(result['cleanup']['group_absent'])
        self.assertLess(result['elapsed_seconds'], 2.5)

    def test_actual_abnormal_exit_retains_code_and_still_cleans(self):
        result = self.supervise('raise SystemExit(23)')
        self.assertEqual(23, result['exit_code']); self.assertFalse(result['passed'])
        self.assertTrue(result['cleanup']['group_absent'])

    def test_actual_already_reaped_child_is_never_signalled(self):
        proc = subprocess.Popen([sys.executable, '-c', 'pass'], **platform.owned_process_options())
        proc.wait(timeout=2)
        with patch.object(platform.os, 'killpg', wraps=os.killpg) as signals:
            with self.assertRaisesRegex(RuntimeError, 'already reaped'):
                platform.terminate_owned_process(proc)
            signals.assert_not_called()
        (self.directory / 'already-reaped.json').write_text(json.dumps({'pid':proc.pid,'exit_code':proc.returncode,'killpg_calls':0})+'\n')

    def test_actual_ignored_sigchld_refuses_before_launch(self):
        code = ('import signal; signal.signal(signal.SIGCHLD,signal.SIG_IGN);'
                'from fixture_platform import owned_process_options; owned_process_options()')
        result = subprocess.run([sys.executable, '-c', code], cwd=SCRIPTS,
                                capture_output=True, text=True, timeout=2)
        (self.directory / 'ignored-sigchld.json').write_text(json.dumps({'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr},indent=2)+'\n')
        self.assertNotEqual(0, result.returncode); self.assertIn('default SIGCHLD', result.stderr)


if __name__ == '__main__': unittest.main()
