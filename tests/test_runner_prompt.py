import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from workflow.runner import prompt_arguments,legacy_spawn_failure,main

class RunnerPromptTests(unittest.TestCase):
    def test_large_unicode_prompt_is_exact_and_command_is_short(self):
        with tempfile.TemporaryDirectory() as d:
            prompt='long instructions \u03bb\n'*10000
            args=prompt_arguments(d,prompt)
            self.assertLess(len(subprocess.list2cmdline(args)),2000)
            self.assertEqual(Path(d,'prompt.txt').read_bytes(),prompt.encode('utf-8'))
            self.assertEqual(args[-2],'--file')

    def test_spawn_error_is_durable_without_child(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)
            (out/'start.json').write_text(json.dumps(dict(executable='missing',config='config',worktree=d,model='allowed',action_id='test',prompt='hello')))
            with patch('workflow.runner.identify',return_value={'pid':1}),patch('workflow.runner.subprocess.Popen',side_effect=OSError('cannot spawn')):
                main(d)
            result=json.loads((out/'result.json').read_text())
            self.assertEqual(result['kind'],'spawn_error')
            self.assertFalse(result['child_created'])
            self.assertFalse((out/'child.json').exists())

    def test_legacy_recovery_requires_exact_creation_failure_and_no_child(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d);p=out/'runner.stderr'
            p.write_text('WinError 206')
            self.assertFalse(legacy_spawn_failure(d))
            p.write_text('Traceback (most recent call last)\nsubprocess.Popen(command\n_winapi.CreateProcess\nFileNotFoundError: [WinError 206] The filename or extension is too long')
            self.assertTrue(legacy_spawn_failure(d))
            (out/'child.json').write_text('{}')
            self.assertFalse(legacy_spawn_failure(d))

    def test_controller_recovers_legacy_and_structured_spawn_failure_once(self):
        from tests import test_pikmin2_controller as fixtures
        from workflow.runner import write
        for legacy in (True,False):
            with self.subTest(legacy=legacy):
                f=fixtures.ControllerTests();f.setUp()
                try:
                    item=f.plan();f.controller.dispatch(item)
                    directory=f.controller.launch_directory(item['id'])
                    if legacy:
                        (directory/'runner.stderr').write_text('Traceback (most recent call last)\nsubprocess.Popen(command\n_winapi.CreateProcess\nFileNotFoundError: [WinError 206] The filename or extension is too long')
                    else:write(directory/'result.json',dict(kind='spawn_error',exit_code=None,child_created=False))
                    f.reg.probe=lambda p:'dead'
                    f.controller.complete_runs();f.controller.complete_runs()
                    launches=list(f.reg.control_status()['launches'].values())
                    self.assertEqual(len(launches),2)
                    self.assertEqual(launches[-1]['dead_runner_retries'],1)
                    self.assertEqual(launches[-1]['session'],item['session'])
                finally:f.doCleanups()
