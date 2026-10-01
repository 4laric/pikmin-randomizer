"""Real process/filesystem tests; POSIX cases run through the fixed Linux test recipe."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fixture_platform as platform
import run_pikmin2_cave_fixture as cave
import run_pikmin2_fixture as runner


class WindowsDependencies(unittest.TestCase):
    def test_four_dll_missing_and_conflicting_never_fall_back(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); package = root / 'package'; package.mkdir()
            exe = package / 'fixture.exe'; exe.write_bytes(b'not executed')
            other = root / 'other'; other.mkdir()
            names = platform.WINDOWS_DLLS + ('SDL2.dll',)
            for name in names:
                (package / name).write_bytes(name.encode())
                (other / name).write_bytes(name.encode())
            directory, hashes = platform.windows_dependencies(exe, package)
            self.assertEqual(directory, package.resolve())
            self.assertEqual(set(hashes), set(names))
            for name in names:
                with self.subTest(name=name):
                    (other / name).write_bytes(b'wrong')
                    with self.assertRaises(ValueError):
                        platform.windows_dependencies(exe, other)
                    (other / name).unlink()
                    with self.assertRaises(FileNotFoundError):
                        platform.windows_dependencies(exe, other)
                    (other / name).write_bytes(name.encode())
            (other / 'SDL2.dll').unlink()
            self.assertEqual(set(platform.windows_dependencies(exe, other, include_sdl=False)[1]), set(platform.WINDOWS_DLLS))


class PrivateOverlay(unittest.TestCase):
    def test_materialized_files_are_independent_and_overrides_are_exact(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / 'source'; source.mkdir()
            (source / 'nested').mkdir()
            original = source / 'nested/original'; original.write_bytes(b'original')
            stable = source / 'stable'; stable.write_bytes(b'stable')
            before = {p: (platform.digest(p), p.stat().st_mode) for p in (original, stable)}
            target = root / 'copy'
            platform.copy_private_tree(source, target, {'nested/original': b'override', 'new/deep/file': b'new'})
            self.assertEqual((target / 'nested/original').read_bytes(), b'override')
            (target / 'stable').write_bytes(b'changed privately')
            self.assertEqual(before, {p: (platform.digest(p), p.stat().st_mode) for p in before})
            with self.assertRaises(ValueError):
                platform.copy_private_tree(source, target)
            with self.assertRaises(ValueError):
                platform.copy_private_tree(source, source / 'child')
            for overrides in ({'../escape': b'x'}, {'a': b'x', 'a/b': b'y'}, {'/absolute': b'x'}):
                with self.assertRaises(ValueError):
                    platform.copy_private_tree(source, root / 'invalid', overrides)
                self.assertFalse((root / 'invalid').exists())

    @unittest.skipIf(sys.platform == 'win32', 'POSIX symlinks and read-only modes')
    def test_readonly_relative_links_cycles_dangling_and_alias_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / 'source'; source.mkdir()
            (source / 'real').mkdir(); original = source / 'real/data'; original.write_bytes(b'original')
            (source / 'file-link').symlink_to('real/data')
            (source / 'dir-link').symlink_to('real', target_is_directory=True)
            original.chmod(0o444); source.chmod(0o555)
            try:
                platform.copy_private_tree(source, root / 'copy')
                for relative in ('real/data', 'file-link', 'dir-link/data'):
                    target = root / 'copy' / relative
                    self.assertFalse(target.is_symlink())
                    self.assertNotEqual(target.stat().st_ino, original.stat().st_ino)
                    target.write_bytes(b'private')
                self.assertEqual(original.read_bytes(), b'original')
                self.assertEqual(original.stat().st_mode & 0o777, 0o444)
            finally:
                source.chmod(0o755); original.chmod(0o644)
            alias = root / 'alias'; alias.symlink_to(source, target_is_directory=True)
            with self.assertRaises(ValueError):
                platform.copy_private_tree(source, alias / 'inside')
            (source / 'cycle').symlink_to('.', target_is_directory=True)
            with self.assertRaises(ValueError):
                platform.copy_private_tree(source, root / 'cyclic')
            (source / 'cycle').unlink(); (source / 'broken').symlink_to('missing')
            with self.assertRaises(FileNotFoundError):
                platform.copy_private_tree(source, root / 'dangling')


class Supervision(unittest.TestCase):
    def test_real_exit_and_marker_oracles(self):
        cases = [('print("PASS")', True), ('print("OTHER")', False),
                 ('print("PASS");raise SystemExit(86)', False),
                 ('print("PASS\\nP2_FIXTURE_CAPTAIN_DOWN");raise SystemExit(86)', False),
                 ('print("PASS",flush=True);import time;time.sleep(10)', False)]
        for code, passed in cases:
            with self.subTest(code=code), tempfile.TemporaryDirectory() as temp:
                result = cave.supervise([sys.executable, '-c', code], temp, .5, required_markers=['PASS'])
                self.assertEqual(result['passed'], passed)
                self.assertEqual(json.loads((Path(temp) / 'run-result.json').read_text()), result)

    @unittest.skipIf(sys.platform == 'win32', 'POSIX owned process groups')
    def test_children_die_on_timeout_and_after_leader_exit_unrelated_survives(self):
        def running(pid):
            try:
                return Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0] != 'Z'
            except FileNotFoundError:
                return False
        sentinel = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(30)'])
        try:
            for early_exit in (False, True):
                with self.subTest(early_exit=early_exit), tempfile.TemporaryDirectory() as temp:
                    pidfile = str(Path(temp) / 'descendants.json')
                    child = f'import os,subprocess,sys,time,json;g=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"]);open({pidfile!r},"w").write(json.dumps([os.getpid(),g.pid]));time.sleep(30)'
                    parent = f'import subprocess,sys,time,pathlib;subprocess.Popen([sys.executable,"-c",{child!r}]);p=pathlib.Path({pidfile!r})\nwhile not p.exists():time.sleep(.01)\nprint("PASS",flush=True)\n' + ('' if early_exit else 'time.sleep(30)')
                    result = cave.supervise([sys.executable, '-c', parent], temp, 1, required_markers=['PASS'])
                    self.assertEqual(result['timed_out'], not early_exit)
                    self.assertEqual(result['passed'], early_exit)
                    descendants = json.loads(Path(pidfile).read_text())
                    deadline = time.monotonic() + 2
                    while any(running(pid) for pid in descendants) and time.monotonic() < deadline:
                        time.sleep(.02)
                    self.assertFalse(any(running(pid) for pid in descendants))
                    self.assertIsNone(sentinel.poll())
        finally:
            sentinel.kill(); sentinel.wait(timeout=5)

    def test_exception_retires_real_child_and_records_failure(self):
        original = subprocess.Popen; children = []
        def launch(*args, **kwargs):
            proc = original(*args, **kwargs); children.append(proc)
            original_wait = proc.wait
            first = True
            def wait(*args, **kwargs):
                nonlocal first
                if first:
                    first = False
                    raise RuntimeError('injected supervisor failure')
                return original_wait(*args, **kwargs)
            proc.wait = wait
            return proc
        with tempfile.TemporaryDirectory() as temp, patch.object(cave.subprocess, 'Popen', side_effect=launch):
            with self.assertRaisesRegex(RuntimeError, 'injected'):
                cave.supervise([sys.executable, '-c', 'import time;time.sleep(30)'], temp, 1)
            self.assertIsNotNone(children[0].poll())
            self.assertFalse(json.loads((Path(temp) / 'run-result.json').read_text())['passed'])


@unittest.skipUnless(sys.platform.startswith('linux'), 'Real ELF and Linux controller boundary')
class LinuxDependencies(unittest.TestCase):
    def test_actual_python_link_closure_and_loader_override_rejection(self):
        evidence = platform.linux_dependencies(sys.executable, env={}, cwd='/tmp')
        self.assertEqual(evidence['executable']['sha256'], platform.digest(sys.executable))
        self.assertEqual(evidence['loader']['sha256'], platform.digest(evidence['loader']['resolved_path']))
        self.assertTrue(evidence['libraries'])
        for item in evidence['libraries'].values():
            self.assertEqual(item['sha256'], platform.digest(item['resolved_path']))
        for name in ('LD_PRELOAD', 'LD_AUDIT', 'LD_LIBRARY_PATH', 'GLIBC_TUNABLES'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                platform.linux_dependencies(sys.executable, {name: '/not/trusted'})
        with tempfile.TemporaryDirectory() as temp:
            invalid = Path(temp) / 'invalid'; invalid.write_bytes(b'not ELF'); invalid.chmod(0o755)
            with self.assertRaises(ValueError):
                platform.linux_dependencies(invalid, {})

    @unittest.skipUnless(shutil.which('cc'), 'Small ELF dependency fixture needs host C compiler')
    def test_relative_runpath_uses_actual_run_directory_and_missing_rejects(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'one/lib').mkdir(parents=True); (root / 'two/lib').mkdir(parents=True)
            for folder, value in [('one', 1), ('two', 2)]:
                subprocess.run(['cc', '-shared', '-fPIC', '-x', 'c', '-', '-o', str(root / folder / 'lib/libprivate1174.so')],
                               input=f'int value(void){{return {value};}}', text=True, check=True, capture_output=True)
            exe = root / 'probe'
            subprocess.run(['cc', '-x', 'c', '-', '-L' + str(root / 'one/lib'), '-Wl,-rpath,./lib', '-lprivate1174', '-o', str(exe)],
                           input='extern int value(void);int main(void){return value();}', text=True, check=True, capture_output=True)
            a = platform.linux_dependencies(exe, {}, root / 'one')
            b = platform.linux_dependencies(exe, {}, root / 'two')
            self.assertNotEqual(a['libraries']['libprivate1174.so']['sha256'], b['libraries']['libprivate1174.so']['sha256'])
            (root / 'two/lib/libprivate1174.so').unlink()
            with self.assertRaises(ValueError):
                platform.linux_dependencies(exe, {}, root / 'two')


class LaunchAdmission(unittest.TestCase):
    """Unit checks isolate the admission boundary; no native gameplay is implied."""
    def test_linux_denial_or_changed_binary_never_launches(self):
        for fault in ('denied', 'changed', 'timeout'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); run = root / 'output/session/run'; run.mkdir(parents=True)
                assets = run / 'assets/dataDir'; assets.mkdir(parents=True)
                for name in ('consFont.bti', 'bigFont.bti'):
                    (assets / name).write_bytes(b'font' * 20)
                exe = root / 'candidate'; exe.write_bytes(b'unit fixture; never executed')
                runtime = {'platform': 'linux', 'executable': {'sha256': platform.digest(exe)}}
                error = (ValueError('fixed broker denied') if fault == 'denied' else
                         subprocess.TimeoutExpired('fixed helper', 10) if fault == 'timeout' else None)
                with patch.object(runner, 'ROOT', root), patch.object(runner, 'is_windows', return_value=False), \
                     patch.object(runner, 'runtime_evidence', return_value=runtime), \
                     patch.object(runner, 'linux_admission', side_effect=error, return_value={'exe_sha256': '0' * 64}), \
                     patch.object(runner, 'supervise') as native:
                    result = runner.launch(exe, run, [], ['PASS'], canonical_root=root,
                                           session_root=root / 'output/session')
                native.assert_not_called()
                self.assertFalse(result['launched'])
                self.assertFalse(result['passed'])
                self.assertFalse((run / 'native.log').exists())
                self.assertEqual(json.loads((run / 'run-result.json').read_text()), result)

    def test_invalid_windows_capacity_never_launches(self):
        for admission in ({'ram': float('nan'), 'games': 0}, {'ram': 91, 'games': 0},
                          {'ram': 10, 'games': 6}, {'ram': 10, 'games': -1},
                          {'ram': 10, 'games': 1.5}, {}):
            with self.subTest(admission=admission), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); run = root / 'output/session/run'; run.mkdir(parents=True)
                assets = run / 'assets/dataDir'; assets.mkdir(parents=True)
                for name in ('consFont.bti', 'bigFont.bti'):
                    (assets / name).write_bytes(b'font' * 20)
                exe = root / 'candidate'; exe.write_bytes(b'unit fixture; never executed')
                runtime = {'platform': 'windows', 'runtime_directory': str(root), 'dlls': {},
                           'executable': {'sha256': platform.digest(exe)}}
                with patch.object(runner, 'ROOT', root), patch.object(runner, 'is_windows', return_value=True), \
                     patch.object(runner, 'runtime_evidence', return_value=runtime), \
                     patch.object(runner.subprocess, 'check_output', return_value=json.dumps(admission)), \
                     patch.object(runner, 'supervise') as native:
                    result = runner.launch(exe, run, [], ['PASS'], canonical_root=root,
                                           session_root=root / 'output/session')
                native.assert_not_called()
                self.assertFalse(result['launched'])
                self.assertFalse(result['passed'])


if __name__ == '__main__':
    unittest.main()
