from pathlib import Path
import hashlib
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import contextlib
import io
import json

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from run_pikmin2_captain_combined_sdl import runtime_dependencies
import run_pikmin2_captain_combined_sdl as captain


class PackagedCaptainRuntimeTests(unittest.TestCase):
    def setUp(self):
        windows = patch('fixture_platform.is_windows', return_value=True)
        windows.start()
        self.addCleanup(windows.stop)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.package = self.root / 'package'
        self.package.mkdir()
        self.exe = self.package / 'fixture.exe'
        self.exe.write_bytes(b'not executed')
        self.names = ('libstdc++-6.dll', 'libgcc_s_seh-1.dll',
                      'libwinpthread-1.dll', 'SDL2.dll')
        for name in self.names:
            (self.package / name).write_bytes(name.encode())

    def test_complete_artifact_uses_its_own_runtime(self):
        directory, hashes = runtime_dependencies(self.exe, self.package)
        self.assertEqual(directory, self.package.resolve())
        self.assertEqual(hashes, {name: hashlib.sha256(name.encode()).hexdigest()
                                  for name in self.names})

    def test_executable_local_conflicts_fail_for_every_dependency(self):
        other = self.root / 'other'
        other.mkdir()
        for name in self.names:
            (other / name).write_bytes(name.encode())
        for name in self.names:
            with self.subTest(name=name):
                (other / name).write_bytes(b'different build')
                with self.assertRaisesRegex(ValueError, 'Conflicting executable-local'):
                    runtime_dependencies(self.exe, other)
                (other / name).write_bytes(name.encode())

    def test_incomplete_artifact_never_falls_back_to_local_installation(self):
        for name in self.names:
            with self.subTest(name=name):
                (self.package / name).unlink()
                with self.assertRaises(FileNotFoundError):
                    runtime_dependencies(self.exe, self.package)
                (self.package / name).write_bytes(name.encode())


class PortableCaptainWiringTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / 'output').mkdir()
        self.session = self.root / 'output' / 'captain'
        self.assets = self.root / 'assets'
        stage = self.assets / 'dataDir/stages/practice'
        stage.mkdir(parents=True)
        (stage / 'default.gen').write_bytes(b'original default generator')
        (stage / '1.gen').write_bytes(b'original daily generator')
        self.exe = self.root / 'fixture'
        self.exe.write_bytes(b'not executed')
        self.probes = []
        self.launches = []

    def invoke(self, prepare_only, development_launch=False):
        class Run:
            def __init__(self, session):
                self.directory = session.directory / 'runs' / 'token'
                self.directory.mkdir(parents=True)
                self.bootstrap = self.directory / 'bootstrap.txt'
                self.bootstrap.write_text('CAPTAINS 2\n')
            def write_state(self, ready): pass
            def poll(self): pass
        def overlay(source, target, overrides):
            stage = target / 'dataDir/stages/practice'
            stage.mkdir(parents=True)
            for name in ('default.gen', '1.gen'):
                (stage / name).write_bytes((source / 'dataDir/stages/practice' / name).read_bytes())
        def runtime(exe, runtime_directory, env, *, cwd):
            self.assertTrue((cwd / 'assets/dataDir/stages/practice/1.gen').is_file())
            self.probes.append(cwd)
            return dict(platform='linux', runtime_directory=None, cwd=str(cwd), libraries={},
                        executable=dict(path=str(exe), sha256=captain.digest(exe)))
        def launch(exe, directory, args, markers, timeout, **kwargs):
            self.launches.append((directory, timeout, kwargs))
            return dict(passed=False, launched=False, error='mock controller admission denial')
        def spec(name, path):
            self.assertEqual(path, captain.ROOT / 'scripts/run_pikmin2_fixture.py')
            return SimpleNamespace(loader=SimpleNamespace(exec_module=lambda module: setattr(module, 'launch', launch)))
        def git_only(argv, **kwargs):
            self.assertEqual(argv[0], 'git', 'Thin runner must not invoke platform admission directly')
            return '' if 'status' in argv else 'a' * 40
        args = ['captain', '--canonical-root', str(self.root), '--session-root', str(self.session),
                '--assets', str(self.assets), '--exe', str(self.exe), '--phase', 'save']
        if prepare_only: args.append('--prepare-only')
        if development_launch: args.append('--development-launch')
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(sys, 'argv', args))
            stack.enter_context(patch.dict(captain.os.environ, {}, clear=False))
            for name, value in [('is_windows', lambda: False), ('runtime_evidence', runtime),
                                ('generate', lambda *a, **k: {'p2_second_captain': True}), ('validate', lambda m: None),
                                ('Session', lambda m, d: SimpleNamespace(directory=d)), ('NativeRun', Run), ('overlay', overlay)]:
                stack.enter_context(patch.object(captain, name, value))
            early_probe = stack.enter_context(patch.object(captain, 'runtime_dependencies', side_effect=AssertionError('early Linux probe')))
            stack.enter_context(patch.object(captain.subprocess, 'check_output', side_effect=git_only))
            stack.enter_context(patch('importlib.util.spec_from_file_location', side_effect=spec))
            stack.enter_context(patch('importlib.util.module_from_spec', return_value=SimpleNamespace()))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            if prepare_only:
                captain.main()
            else:
                with self.assertRaisesRegex(AssertionError, 'mock controller admission denial'):
                    captain.main()
            early_probe.assert_not_called()
        return self.session / 'runs/token'

    def test_linux_prepare_resolves_runtime_in_staged_cwd_without_admission(self):
        directory = self.invoke(True)
        self.assertEqual(self.probes, [directory])
        self.assertEqual(self.launches, [])
        self.assertFalse((directory / 'admission.json').exists())
        data = json.loads((directory / 'adoption-inputs.json').read_text())
        self.assertEqual(data['runtime_platform'], 'linux')
        self.assertIsNone(data['runtime_directory'])
        self.assertIn('runtime_libraries', data)
        self.assertNotIn('runtime_dlls_sha256', data)

    def test_launch_uses_pinned_helper_and_context_rejects_before_log_read(self):
        directory = self.invoke(False)
        self.assertEqual(self.launches, [(directory, 60, dict(toolchain=None, canonical_root=self.root, session_root=self.session, development_launch=False))])
        self.assertFalse((directory / 'native.log').exists())
        self.assertFalse((directory / 'phase-verified.json').exists())

    def test_development_launch_preserves_context_bound_and_refusal(self):
        directory = self.invoke(False, development_launch=True)
        self.assertEqual(self.launches, [(directory, 60, dict(toolchain=None, canonical_root=self.root,
                                                            session_root=self.session, development_launch=True))])
        self.assertFalse((directory / 'native.log').exists())
        self.assertFalse((directory / 'phase-verified.json').exists())

    def test_development_prepare_only_still_does_not_launch(self):
        self.invoke(True, development_launch=True)
        self.assertEqual(self.launches, [])


if __name__ == '__main__':
    unittest.main()
