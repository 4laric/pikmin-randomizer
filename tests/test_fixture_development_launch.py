"""Development execution controls; fake inputs are never native runtime evidence."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fixture_platform as platform
import run_pikmin2_fixture as runner

MEMORY = 'MemTotal: 1000000 kB\nMemAvailable: 500000 kB\n'


class DevelopmentLaunchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.session = self.root / 'output/session'; self.run = self.session / 'run'
        assets = self.run / 'assets/dataDir'; assets.mkdir(parents=True)
        for name in ('consFont.bti', 'bigFont.bti'): (assets / name).write_bytes(b'fixture-font' * 8)
        self.exe = self.root / 'fake-ELF'; self.exe.write_bytes(b'not executable; prelaunch mock only')
        self.runtime = {'platform': 'linux', 'executable': {'path': str(self.exe), 'sha256': platform.digest(self.exe)},
                        'libraries': {'mock only': {'sha256': '0' * 64}}, 'scope': 'mocked prelaunch test'}
        self.root_patch = patch.object(runner, 'ROOT', self.root)
        self.root_patch.start(); self.addCleanup(self.root_patch.stop)

    def launch(self, **kwargs):
        return runner.launch(self.exe, self.run, ['unused'], ['PASS TEST'],
                             canonical_root=self.root, session_root=self.session, **kwargs)

    def fresh_run(self, name):
        self.run = self.session / name
        assets = self.run / 'assets/dataDir'; assets.mkdir(parents=True)
        for font in ('consFont.bti', 'bigFont.bti'): (assets / font).write_bytes(b'fixture-font' * 8)

    def test_explicit_development_launch_skips_missing_controller_and_records_real_context(self):
        with patch.object(runner, 'is_windows', return_value=False), \
                patch.object(runner, 'runtime_evidence', return_value=self.runtime), \
                patch.object(platform.Path, 'read_text', return_value=MEMORY), \
                patch.object(runner, 'linux_admission', side_effect=FileNotFoundError('controller absent')) as controller, \
                patch.object(runner, 'supervise', return_value={'passed': True}) as supervised:
            result = self.launch(development_launch=True)
        self.assertTrue(result['passed']); controller.assert_not_called(); supervised.assert_called_once()
        context = json.loads((self.run / 'development-execution.json').read_text())
        self.assertEqual('development', context['mode']); self.assertFalse(context['controller_proof_used'])
        self.assertEqual(50, context['capacity']['used_percent'])
        self.assertEqual(self.runtime['executable'], context['executable'])
        self.assertFalse((self.run / 'admission.json').exists())
        for key in ('admitted', 'pins', 'Main', 'Principal', 'unit', 'cgroup', 'job'):
            self.assertNotIn(key, context)
        inputs = json.loads((self.run / 'run-inputs.json').read_text())
        self.assertEqual('development', inputs['execution_mode'])
        self.assertEqual(self.runtime, inputs['runtime'])
        self.assertEqual('960x540', supervised.call_args.args[3]['PIKMIN_P2_ROOM_WINDOW'])

    def test_production_default_still_propagates_missing_controller(self):
        with patch.object(runner, 'is_windows', return_value=False), \
                patch.object(runner, 'runtime_evidence', return_value=self.runtime), \
                patch.object(runner, 'linux_admission', side_effect=FileNotFoundError('controller absent')) as controller, \
                patch.object(runner, 'supervise') as supervised:
            result = self.launch()
        self.assertFalse(result['launched']); self.assertIn('controller absent', result['error'])
        controller.assert_called_once(); supervised.assert_not_called()
        self.assertFalse((self.run / 'development-execution.json').exists())

    def test_production_controller_response_is_preserved(self):
        proof = {'admitted': True, 'exe_sha256': self.runtime['executable']['sha256'], 'pins': {'mock': 'production-only'}}
        with patch.object(runner, 'is_windows', return_value=False), \
                patch.object(runner, 'runtime_evidence', return_value=self.runtime), \
                patch.object(runner, 'linux_admission', return_value=proof), \
                patch.object(runner, 'supervise', return_value={'passed': True}):
            self.assertTrue(self.launch()['passed'])
        self.assertEqual(proof, json.loads((self.run / 'admission.json').read_text()))
        self.assertFalse((self.run / 'development-execution.json').exists())

    def test_bad_elf_dependency_and_loader_environment_fail_before_development_launch(self):
        for index, message in enumerate(('Expected an ELF executable', 'Unresolved ELF dependencies', 'Loader environment overrides forbidden')):
            self.fresh_run('dependency-refusal-' + str(index))
            with self.subTest(message=message), \
                    patch.object(runner, 'is_windows', return_value=False), \
                    patch.object(runner, 'runtime_evidence', side_effect=ValueError(message)), \
                    patch.object(runner, 'linux_development_context') as context, \
                    patch.object(runner, 'supervise') as supervised:
                result = self.launch(development_launch=True)
                self.assertFalse(result['launched']); self.assertEqual(message, result['error'])
                context.assert_not_called(); supervised.assert_not_called()

    def test_executable_drift_refuses_before_process_start(self):
        self.exe.write_bytes(b'changed after mock ELF inspection')
        with patch.object(runner, 'is_windows', return_value=False), \
                patch.object(runner, 'runtime_evidence', return_value=self.runtime), \
                patch.object(runner, 'supervise') as supervised:
            result = self.launch(development_launch=True)
        self.assertFalse(result['launched']); self.assertIn('Executable changed', result['error'])
        supervised.assert_not_called()

    def test_explicit_boolean_choice_required(self):
        for index, value in enumerate(('true', 1, None)):
            self.fresh_run('choice-refusal-' + str(index))
            with self.subTest(value=value), patch.object(runner, 'supervise') as supervised:
                result = self.launch(development_launch=value)
                self.assertFalse(result['launched']); self.assertIn('explicit boolean', result['error'])
                supervised.assert_not_called()

    def test_capacity_ceiling_and_unknown_memory_refuse(self):
        for memory in ('MemTotal: 1000 kB\nMemAvailable: 10 kB\n', 'MemTotal: 1000 kB\n',
                       'MemTotal: nope kB\nMemAvailable: 5 kB\n', 'MemTotal: 1000 kB\nMemAvailable: 1001 kB\n'):
            with self.subTest(memory=memory), patch.object(platform.Path, 'read_text', return_value=memory):
                with self.assertRaises(ValueError):
                    platform.linux_development_context(self.exe, self.root, self.session, self.run, self.runtime)

    def test_private_run_and_session_are_required(self):
        for session, run in ((self.root, self.run), (self.root / 'output', self.run), (self.session, self.root)):
            with self.subTest(session=session,run=run), self.assertRaisesRegex(ValueError, 'private output'):
                platform.linux_development_context(self.exe, self.root, session, run, self.runtime)

    def test_wrong_platform_or_inspected_executable_refuses(self):
        for runtime in ({'platform': 'windows'}, {'platform': 'linux', 'executable': {'path': 'wrong'}}):
            with self.subTest(runtime=runtime), self.assertRaisesRegex(ValueError, 'inspected Linux runtime'):
                platform.linux_development_context(self.exe, self.root, self.session, self.run, runtime)


@unittest.skipUnless(sys.platform == 'linux', 'actual harmless ELF development launch')
class ActualLinuxDevelopmentTests(unittest.TestCase):
    def test_actual_elf_exec_and_owned_cleanup_without_controller(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); run = root / 'output/session/run'
            assets = run / 'assets/dataDir'; assets.mkdir(parents=True)
            for name in ('consFont.bti', 'bigFont.bti'): (assets / name).write_bytes(b'fixture-font' * 8)
            with patch.object(runner, 'ROOT', root), \
                    patch.object(runner, 'linux_admission', side_effect=AssertionError('controller must not be called')) as controller:
                result = runner.launch(sys.executable, run, ['-c', 'print("PASS DEVELOPMENT ELF")'],
                                       ['PASS DEVELOPMENT ELF'], canonical_root=root,
                                       session_root=root / 'output/session', development_launch=True)
            controller.assert_not_called()
            self.assertTrue(result['passed']); self.assertTrue(result['cleanup']['group_absent'])
            context = json.loads((run / 'development-execution.json').read_text())
            self.assertEqual(hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest(), context['executable']['sha256'])
            self.assertFalse((run / 'admission.json').exists())


if __name__ == '__main__': unittest.main()
