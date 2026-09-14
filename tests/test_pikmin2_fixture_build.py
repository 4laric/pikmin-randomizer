"""Synthetic build-identity tests; never touch a production build or execute game code."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import build_pikmin2_fixture as tool


class CommandTests(unittest.TestCase):
    def test_ninja_owns_response_expansion_and_link_order(self):
        raw = dict(file='a.obj', output='x.exe', command='g++.exe @x.rsp -o x.exe')
        expanded = dict(raw, command='g++.exe z.obj a.obj libz.a liba.a -o x.exe')
        with patch.object(tool, 'run', side_effect=[(0, json.dumps([raw])), (0, json.dumps([expanded]))]):
            self.assertEqual(tool.expand_response_files(raw['command'], 'ninja', Path('.')), expanded['command'])
        changed = dict(expanded, output='different.exe')
        with patch.object(tool, 'run', side_effect=[(0, json.dumps([raw])), (0, json.dumps([changed]))]):
            with self.assertRaises(tool.BuildRejected):
                tool.expand_response_files(raw['command'], 'ninja', Path('.'))

    def test_windows_paths_spaces_and_backslashes_roundtrip(self):
        args = [r'C:\Program Files\toolchain\g++.exe', '-I' + r'C:\source folder\include',
                '-DNAME="example"', 'C:\\trailing\\', '', '-flto=4']
        self.assertEqual(tool.windows_args(subprocess.list2cmdline(args)), args)

    def test_known_cmake_wrapper_only_and_no_shell_execution(self):
        command = r'C:\Windows\system32\cmd.exe /C "cd . && "C:\Program Files\g++.exe" -o fixture.exe main.obj && cd ."'
        self.assertEqual(tool.compiler_args(command)[0], r'C:\Program Files\g++.exe')
        for text in ('g++.exe @args.rsp', 'g++.exe -o x a.obj && erase x', '"g++.exe -o x',
                     'cmd.exe /C "cd . && g++.exe a.obj && unexpected && cd ."'):
            with self.subTest(text=text), self.assertRaises(tool.BuildRejected):
                tool.compiler_args(text)

    def test_keep_lto_and_other_build_flags_change_only_private_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = ['g++.exe', '-flto=4', '-O3', '-DTEST=1', '-MD', '-MF', 'old.d', '-MT', 'old.obj',
                    '-o', 'old.obj', '-c', 'old.cpp']
            changed = tool.fixture_compile(args, root / 'fixture.cpp', root / 'out', root / 'native')
            for flag in ('-flto=4', '-O3', '-DTEST=1'):
                self.assertIn(flag, changed)
            self.assertNotIn('old.obj', changed)
            self.assertNotIn('old.d', changed)
            self.assertEqual(changed[changed.index('-o') + 1], str(root / 'out/fixture.obj'))
            with self.assertRaises(tool.BuildRejected): tool.option_index(['-o', 'a', '-o', 'b'], '-o')

    def test_missing_or_stale_ninja_dependencies_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            obj = root / 'main.obj'
            for text in ('', 'main.obj: #deps 1, deps mtime 123 (STALE)\n    a.h\n'):
                with self.subTest(text=text), self.assertRaises(tool.BuildRejected):
                    tool.ninja_dependencies(text, {obj}, root)

    def test_make_dependency_escaped_spaces(self):
        root = Path.cwd()
        result = tool.make_dependencies('fixture: source\\ file.cpp \\\n include\\ file.h\n', root)
        self.assertEqual(result, {root / 'source file.cpp', root / 'include file.h'})

    def test_make_dependencies_preserve_windows_separators_and_dollar(self):
        root = Path.cwd()
        result = tool.make_dependencies(r'fixture: folder\native\header.h money$$\file.h', root)
        self.assertEqual(result, {root / 'folder/native/header.h', root / 'money$/file.h'})

    def test_library_directory_order_precedes_import_library_suffix(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first, second = root / 'first', root / 'second'
            first.mkdir()
            second.mkdir()
            (first / 'libfoo.a').write_bytes(b'first')
            (second / 'libfoo.dll.a').write_bytes(b'second')
            with patch.object(tool, 'run', return_value=(0, 'libraries: =' + str(first) + ';' + str(second))):
                result = tool.resolve_libraries(['g++', '-lfoo'], root / 'g++', root, {})
            self.assertEqual(result['-lfoo'], first / 'libfoo.a')


class BuildHarness:
    """Fake compiler/Ninja responses and files for exercising the whole workflow."""
    def __init__(self, root):
        self.root = root
        self.source, self.build = root / 'native source', root / 'native build'
        self.fixture, self.output = root / 'probe.cpp', root / 'private output'
        self.compiler, self.ninja = root / 'g++.exe', root / 'ninja.exe'
        self.main = self.source / 'pc_port/pc_main.cpp'
        self.obj, self.library, self.import_lib = self.build / 'main.obj', self.build / 'legacy.a', root / 'libfoo.a'
        self.executable = self.build / 'bin/nectar.exe'
        self.pending, self.change_during_link = False, False
        self.calls = []
        for path in (self.compiler, self.ninja, self.fixture, self.main, self.obj, self.library, self.import_lib,
                     self.executable, self.build / 'build.ninja', self.build / 'CMakeFiles/rules.ninja',
                     self.build / '.ninja_log', self.build / '.ninja_deps'):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'synthetic input\n')
        (self.build / 'CMakeCache.txt').write_text('\n'.join([
            'CMAKE_GENERATOR:INTERNAL=Ninja', 'CMAKE_HOME_DIRECTORY:INTERNAL=' + str(self.source),
            'CMAKE_CXX_COMPILER:FILEPATH=' + str(self.compiler), 'CMAKE_MAKE_PROGRAM:FILEPATH=' + str(self.ninja),
            'CMAKE_BUILD_TYPE:STRING=Release']), encoding='utf-8')
        self.compile = [str(self.compiler), '-DPIKI_PC_PORT=1', '-flto=4', '-O3', '-MD', '-o', str(self.obj), '-c', str(self.main)]
        self.link = [str(self.compiler), '-flto=4', str(self.obj), str(self.library), '-lfoo',
                     '-o', str(self.executable), '-Wl,--out-implib,old.dll.a']

    def run(self, args, cwd, env=None):
        self.calls.append(args)
        if '-n' in args:
            return 0, '[1/1] Re-running CMake...\n' if self.pending else 'ninja: no work to do.\n'
        if '--version' in args:
            return 0, 'synthetic version\n'
        if '-print-search-dirs' in args:
            return 0, 'libraries: =' + str(self.root) + '\n'
        if '-t' in args:
            which = args[args.index('-t') + 1]
            if which == 'commands':
                # Link need not be last. Ignore an unrelated archive shell step.
                return 0, '\n'.join([subprocess.list2cmdline(self.link), 'cmd.exe /C "ar qc legacy.a && ranlib legacy.a"',
                                     subprocess.list2cmdline(self.compile)]) + '\n'
            if which == 'deps':
                return 0, str(self.obj) + ': #deps 1, deps mtime 123 (VALID)\n    ' + str(self.main) + '\n'
            if which == 'inputs':
                return 0, str(self.main) + '\n'
        if any(a.startswith('-print-file-name=') for a in args):
            if args[-1].endswith('.dll.a'):
                return 0, 'libfoo.dll.a\n'
            return 0, str(self.import_lib) + '\n'
        if any(a.startswith('-print-prog-name=') for a in args):
            return 0, str(self.compiler) + '\n'
        if '-M' in args or '-c' in args:
            deps = Path(args[args.index('-MF') + 1])
            deps.write_text('fixture: ' + self.fixture.as_posix().replace(' ', '\\ ') + '\n', encoding='utf-8')
            if '-c' in args:
                Path(args[args.index('-o') + 1]).write_bytes(b'synthetic fixture object')
            return 0, ''
        if '-o' in args:
            Path(args[args.index('-o') + 1]).write_bytes(b'synthetic linked fixture')
            if self.change_during_link:
                self.library.write_bytes(b'concurrent replacement')
            return 0, ''
        raise AssertionError(args)

    def execute(self, check_only=False, expected='a' * 40):
        with patch.object(tool, 'run', side_effect=self.run), patch.object(tool, 'git_state', return_value={'head': 'a' * 40, 'status': '', 'tracked_diff_sha256': 'synthetic'}):
            return tool.build_fixture(self.build, self.source, self.fixture, self.output, expected, check_only)


class WorkflowTests(unittest.TestCase):
    def test_synthetic_build_snapshots_link_inputs_and_preserves_flags(self):
        with tempfile.TemporaryDirectory(prefix='fixture QA ') as temp:
            h = BuildHarness(Path(temp))
            result = h.execute()
            self.assertEqual(result['status'], 'built')
            self.assertFalse(result['historical_build_certified'])
            self.assertEqual(h.obj.read_bytes(), b'synthetic input\n')
            link = result['commands'][-1]
            self.assertIn('-flto=4', link)
            self.assertNotIn(str(h.library), link)
            self.assertNotIn('-lfoo', link)
            self.assertTrue(any('link-inputs' in a for a in link))
            self.assertIn(str(h.import_lib), result['inputs'])
            self.assertTrue((h.output / 'provenance.json').exists())

    def test_pending_build_rejected_before_compiler(self):
        with tempfile.TemporaryDirectory() as temp:
            h = BuildHarness(Path(temp))
            h.pending = True
            with self.assertRaises(tool.BuildRejected): h.execute()
            result = json.loads((h.output / 'provenance.json').read_text())
            self.assertEqual(result['status'], 'rejected')
            self.assertEqual(result['commands'], [])
            self.assertFalse(any('-c' in args for args in h.calls))

    def test_changed_link_input_invalidates_successful_compiler_exit(self):
        with tempfile.TemporaryDirectory() as temp:
            h = BuildHarness(Path(temp))
            h.change_during_link = True
            with self.assertRaisesRegex(tool.BuildRejected, 'Inputs changed'): h.execute()
            self.assertEqual(json.loads((h.output / 'provenance.json').read_text())['status'], 'rejected')

    def test_wrong_head_missing_input_and_source_mismatch_are_rejected(self):
        for mode in ('head', 'missing', 'source'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                h = BuildHarness(Path(temp))
                if mode == 'missing': h.library.unlink()
                if mode == 'source':
                    p = h.build / 'CMakeCache.txt'
                    p.write_text(p.read_text().replace(str(h.source), str(h.root / 'wrong')))
                with self.assertRaises(tool.BuildRejected): h.execute(expected='b' * 40 if mode == 'head' else 'a' * 40)

    def test_check_only_never_compiles_and_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            h = BuildHarness(Path(temp))
            self.assertEqual(h.execute(check_only=True)['status'], 'checked_not_built')
            self.assertFalse((h.output / 'fixture.exe').exists())
            before = (h.output / 'provenance.json').read_bytes()
            with self.assertRaises(FileExistsError): h.execute()
            self.assertEqual((h.output / 'provenance.json').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()


class ResponseCommandTests(unittest.TestCase):
    def test_short_command_preserves_argv(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = ['g++', '-c', 'path with spaces/source.cpp']
            with patch.object(tool, 'run', return_value=(0, 'ok')) as execute:
                self.assertEqual(tool.run_command(args, root, {}, root, 'compile'), (0, 'ok'))
                execute.assert_called_once_with(args, root, {})
            self.assertFalse((root / 'compile.rsp').exists())

    def test_long_command_preserves_escaped_arguments(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = ['g++', 'C:\\source folder\\a.cpp', '-DNAME="quoted value"', 'x' * 7100]
            with patch.object(tool, 'run', return_value=(0, 'ok')) as execute:
                tool.run_command(args, root, {}, root, 'link')
                execute.assert_called_once_with(['g++', '@' + str((root / 'link.rsp').resolve())], root, {})
            text = (root / 'link.rsp').read_text()
            self.assertIn('source folder', text)
            self.assertIn('\\"quoted value\\"', text)
            self.assertEqual(len(text.splitlines()), len(args) - 1)
