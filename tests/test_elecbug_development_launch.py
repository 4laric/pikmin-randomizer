"""Exercise the maintained Linux preflight without assets or a native child."""
import ast
import hashlib
from pathlib import Path
import re
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

RUNNER = Path(__file__).resolve().parents[1] / 'scripts/run_elecbug_contact_runtime.py'


class DevelopmentLaunch(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        scripts = self.root / 'scripts'
        scripts.mkdir()
        self.session = self.root / 'output' / 'anode'
        self.run = self.session / 'run'
        self.run.mkdir(parents=True)
        self.exe = self.root / 'fixture'
        self.exe.write_bytes(b'fixture identity')
        self.sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
        self.platform = ModuleType('fixture_platform')
        self.launcher = ModuleType('run_pikmin2_cave_fixture')
        for module in (self.platform, self.launcher):
            path = scripts / (module.__name__ + '.py')
            path.write_text(module.__name__)
            module.__file__ = str(path)
        (scripts / 'p2_fixture_captain_guard.h').write_text('guard')
        self.platform.owned_process_options = object()
        self.platform.terminate_owned_process = object()
        namespace = dict(owned_process_options=self.platform.owned_process_options,
                         terminate_owned_process=self.platform.terminate_owned_process)
        exec('def supervise(): pass', namespace)
        self.launcher.supervise = namespace['supervise']
        self.args = SimpleNamespace(output=self.session, exe_sha256=self.sha(self.exe),
                                    root_commit='a' * 40, native_commit='b' * 40,
                                    fixture_source_sha256='c' * 64,
                                    platform_helper_sha256=self.sha(self.platform.__file__),
                                    supervisor_sha256=self.sha(self.launcher.__file__))
        self.runtime = dict(platform='linux', executable=dict(path=str(self.exe), sha256=self.sha(self.exe)))
        self.proof = dict(target='pikmin_ci_fixture_elecbug_contact',
                          source='tools/p2_elecbug_contact_runtime.cpp',
                          exe_sha256=self.sha(self.exe), guard_sha256=self.sha(scripts / 'p2_fixture_captain_guard.h'),
                          pins=dict(PIKMIN_SHA=self.args.root_commit, NATIVE_SHA=self.args.native_commit,
                                    FIXTURE_SOURCE_SHA256=self.args.fixture_source_sha256))
        self.platform.runtime_evidence = Mock(return_value=self.runtime)
        self.platform.linux_admission = Mock(return_value=self.proof)
        self.platform.linux_development_context = Mock(return_value=dict(mode='development', controller_proof_used=False))
        tree = ast.parse(RUNNER.read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'linux_preflight')
        globals_ = dict(Path=Path, ROOT=self.root, sha=self.sha, re=re, sys=SimpleNamespace(platform='linux'))
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(RUNNER), 'exec'), globals_)
        self.preflight = globals_['linux_preflight']

    def call(self):
        with patch.dict(sys.modules, fixture_platform=self.platform, run_pikmin2_cave_fixture=self.launcher):
            return self.preflight(self.exe, self.run, self.args, {})

    def test_default_retains_controller_proof_and_pin_validation(self):
        self.assertEqual(self.call()['admission'], self.proof)
        self.platform.linux_admission.assert_called_once()
        self.platform.linux_development_context.assert_not_called()
        self.proof['pins']['NATIVE_SHA'] = 'd' * 40
        with self.assertRaisesRegex(ValueError, 'source pin mismatch'):
            self.call()

    def test_explicit_development_inspects_runtime_and_private_capacity_context(self):
        self.args.development_launch = True
        result = self.call()
        self.platform.linux_admission.assert_not_called()
        self.platform.runtime_evidence.assert_called_once_with(self.exe, env={}, cwd=self.run)
        self.platform.linux_development_context.assert_called_once_with(self.exe, self.root, self.session, self.run, self.runtime)
        self.assertFalse(result['development']['controller_proof_used'])
        self.assertNotIn('admission', result)
        self.assertIn('separate build provenance', result['source_binding'])

    def test_development_context_refusal_propagates_before_launch(self):
        self.args.development_launch = True
        self.platform.linux_development_context.side_effect = ValueError('private capacity refused')
        with self.assertRaisesRegex(ValueError, 'private capacity refused'):
            self.call()

    def test_bad_runtime_identity_and_metadata_refuse(self):
        self.args.development_launch = True
        self.runtime['executable']['sha256'] = 'd' * 64
        with self.assertRaisesRegex(ValueError, 'library/executable'):
            self.call()
        self.platform.linux_development_context.assert_not_called()
        self.runtime['executable']['sha256'] = self.args.exe_sha256
        self.args.fixture_source_sha256 = 'unknown'
        with self.assertRaisesRegex(ValueError, 'source metadata'):
            self.call()

    def test_non_boolean_opt_in_and_unadopted_helpers_refuse(self):
        for value in (1, 'true', None):
            self.args.development_launch = value
            with self.assertRaisesRegex(ValueError, 'explicit boolean'):
                self.call()
        self.args.development_launch = True
        self.args.supervisor_sha256 = 'd' * 64
        with self.assertRaisesRegex(ValueError, 'helper identity'):
            self.call()
        self.platform.runtime_evidence.assert_not_called()


if __name__ == '__main__':
    unittest.main()
