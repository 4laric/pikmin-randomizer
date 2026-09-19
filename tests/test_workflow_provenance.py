"""Code provenance, pinned worker CLIs and release preparation, in temporary repos only."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from workflow import provenance, service
from workflow.handoff import Rejected, digest
from workflow.operator import code_line, report
from tests import test_consumer_verification as verification_fixtures
from tests import test_pikmin2_controller as controller_fixtures
from tests import test_pikmin2_workflow as workflow_fixtures
from tests import test_review_decisions as review_fixtures
from tests import test_shared_decisions as shared_fixtures
from tests import test_workflow_delivery as delivery_fixtures

ENTRY = Path(__file__).resolve().parents[1] / 'scripts/workflow_module.py'
_spec = importlib.util.spec_from_file_location('workflow_module', ENTRY)
workflow_module = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(workflow_module)


def git(path, *args):
    return subprocess.run(['git', '-C', str(path), '-c', 'user.email=t@example.invalid', '-c', 'user.name=Test',
                           '-c', 'core.autocrlf=false', *args], check=True, capture_output=True, text=True).stdout


def fixture(cls, test):
    item = cls(test); item.setUp()
    return item


class RevisionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name).resolve()
        (self.repo / 'workflow/sub').mkdir(parents=True); (self.repo / 'scripts').mkdir()
        (self.repo / 'workflow/__init__.py').write_text('')
        (self.repo / 'workflow/sub/gate.py').write_text('RULE = 1\n')
        (self.repo / 'scripts/pikmin2_workflow.py').write_text('print(1)\n')
        (self.repo / 'scripts/other.py').write_text('ignored by the tree hash\n')

    def commit(self):
        git(self.repo, 'init', '-q'); git(self.repo, 'add', '-A'); git(self.repo, 'commit', '-qm', 'base')
        return git(self.repo, 'rev-parse', 'HEAD').strip()

    def test_tree_hashes_sorted_relative_paths_and_bytes(self):
        expected = hashlib.sha256()
        for name in ('scripts/pikmin2_workflow.py', 'workflow/__init__.py', 'workflow/sub/gate.py'):
            expected.update(f'{name}\0{digest(self.repo / name)}\n'.encode())
        self.assertEqual(provenance.tree(self.repo), expected.hexdigest())

    def test_clean_then_dirty_temp_repo(self):
        sha = self.commit()
        clean = provenance.revision(self.repo)
        self.assertEqual((clean['sha'], clean['dirty'], clean['path']), (sha, False, str(self.repo)))
        (self.repo / 'workflow/sub/gate.py').write_text('RULE = 2\n')
        dirty = provenance.revision(self.repo)
        self.assertEqual((dirty['sha'], dirty['dirty']), (sha, True))
        self.assertNotEqual(dirty['tree'], clean['tree'])
        git(self.repo, 'checkout', '--', '.')
        (self.repo / 'workflow/untracked.py').write_text('')
        self.assertTrue(provenance.revision(self.repo)['dirty'])

    def test_missing_git_or_repo_is_unknown_and_dirty_never_raises(self):
        with patch.object(provenance.subprocess, 'run', side_effect=FileNotFoundError('git')):
            value = provenance.revision(self.repo)
        self.assertEqual((value['sha'], value['dirty']), (None, True))
        self.assertEqual(value['tree'], provenance.tree(self.repo))
        self.assertEqual(provenance.revision(self.repo)['sha'], None)  # Not a repository at all.
        with patch.object(provenance, 'tree', side_effect=PermissionError('locked')):
            self.assertIsNone(provenance.revision(self.repo)['tree'])

    def test_process_cache_and_compact_stamp(self):
        saved = provenance._cached; self.addCleanup(setattr, provenance, '_cached', saved)
        provenance._cached = None
        full = dict(sha='a' * 40, dirty=False, tree='b' * 64, path='x')
        with patch.object(provenance, 'revision', return_value=full) as computed:
            first = provenance.code_revision(); first['sha'] = 'mutated'
            self.assertEqual(provenance.code_revision()['sha'], 'a' * 40)
            self.assertEqual(provenance.stamp(), dict(sha='a' * 40, dirty=False, tree='b' * 16))
        self.assertEqual(computed.call_count, 1)

    def test_warnings(self):
        run = dict(sha='a' * 40, dirty=False, tree='c' * 64)
        self.assertEqual(provenance.warnings(run, dict(run, path='p')), [])
        self.assertTrue(any('DIRTY' in w for w in provenance.warnings(dict(run, dirty=True), dict(run))))
        self.assertTrue(any('restart' in w for w in provenance.warnings(run, dict(run, sha='b' * 40))))
        self.assertTrue(any('changed' in w for w in provenance.warnings(run, dict(run, tree='d' * 64))))
        self.assertTrue(any('unknown' in w for w in provenance.warnings(None, dict(run))))
        self.assertTrue(any('uncommitted' in w for w in provenance.warnings(None, dict(run, dirty=True, path='p'))))


class EntryScriptTests(unittest.TestCase):
    def test_allowlist(self):
        self.assertEqual(workflow_module.resolve('review_decisions'), 'review_decisions')
        self.assertEqual(workflow_module.resolve('workflow.service'), 'service')
        for name in ('os', '../scripts/x', '__init__', '-c', 'nonexistent_module', 'service.py', 'Service', ''):
            self.assertIsNone(workflow_module.resolve(name), name)
        p = subprocess.run([sys.executable, str(ENTRY), 'os'], capture_output=True, text=True)
        self.assertEqual(p.returncode, 2); self.assertIn('Refused', p.stderr)

    def test_entry_pins_this_checkout_over_a_stale_cwd_package(self):
        with tempfile.TemporaryDirectory() as temp:
            stale = Path(temp) / 'workflow'; stale.mkdir()
            (stale / '__init__.py').write_text('')
            (stale / 'service.py').write_text("print('STALE CODE')\n")
            env = dict(os.environ, PYTHONPATH=temp)
            p = subprocess.run([sys.executable, str(ENTRY), 'service', '--help'], cwd=temp, env=env,
                               capture_output=True, text=True, timeout=60)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn('prepare-release', p.stdout); self.assertNotIn('STALE', p.stdout)
            p = subprocess.run([sys.executable, '-m', 'workflow.service', '--help'], cwd=temp,
                               capture_output=True, text=True, timeout=60)
            self.assertIn('STALE', p.stdout)  # The hazard the entry script removes.

    def test_worker_instructions_render_absolute_pinned_commands(self):
        from workflow import (delivery_contracts, dependency_classification, review_decisions, support_actions)
        command = provenance.cli('review_decisions')
        self.assertTrue(Path(command.split()[1]).is_absolute())
        self.assertEqual(Path(command.split()[1]).resolve(), ENTRY)
        self.assertEqual(Path(command.split()[0]).resolve(), Path(sys.executable).resolve())
        self.assertIn(command, review_decisions.INSTRUCTION)
        self.assertIn(provenance.cli('shared_decisions'), support_actions.INSTRUCTION)
        self.assertIn(provenance.cli('support_actions'), support_actions.INSTRUCTION)
        self.assertIn(provenance.cli('dependency_classification'), dependency_classification.INSTRUCTION)
        self.assertIn(provenance.cli('delivery_contracts'), delivery_contracts.INSTRUCTION)
        human = {'operator.py', 'planner_claims.py', 'provenance.py'}  # Docstrings for humans only.
        for path in (ENTRY.parents[1] / 'workflow').glob('*.py'):
            if path.name not in human:
                self.assertIsNone(re.search(r'(python|py -3\.12) -m workflow\.', path.read_text(encoding='utf-8')), path)


class StampTests(unittest.TestCase):
    def test_controller_claim_keeps_exact_identity_and_records_start(self):
        f = fixture(controller_fixtures.ControllerTests, 'test_runner_publication_read_races_retry_without_duplicate_spawn')
        self.addCleanup(f.doCleanups)
        f.reg.controller_claim(f.identity); f.reg.controller_claim(f.identity)
        control = f.reg.control_status()
        self.assertEqual(control['controller'], f.identity)
        self.assertEqual(control['controller_code_revision'], provenance.code_revision())
        started = [e for e in f.reg.snapshot()['events'] if e['kind'] == 'controller_started']
        self.assertEqual(len(started), 1)
        self.assertEqual(started[0]['code_revision'], provenance.code_revision())
        self.assertEqual(started[0]['process'], f.identity)
        launch = f.plan()
        self.assertEqual(launch['code_revision'], provenance.stamp())
        self.assertEqual(f.reg.control_status()['launches'][launch['id']]['code_revision'], provenance.stamp())

    def test_old_launch_records_without_provenance_still_replay(self):
        f = fixture(controller_fixtures.ControllerTests, 'test_runner_publication_read_races_retry_without_duplicate_spawn')
        self.addCleanup(f.doCleanups)
        launch = f.plan()
        with f.reg.transaction() as state:
            del state['control']['launches'][launch['id']]['code_revision']
        again = f.plan()
        self.assertEqual(again['id'], launch['id']); self.assertNotIn('code_revision', again)

    def test_review_decision_record(self):
        f = fixture(review_fixtures.QueuedReviewTests, 'test_wait_apply_and_replay'); self.addCleanup(f.doCleanups)
        receipt = review_fixtures.record(f.r, **f.args)
        self.assertEqual(receipt['code_revision'], provenance.stamp())
        self.assertEqual(receipt, review_fixtures.record(f.r, **f.args))

    def test_shared_decision_record_identity_excludes_stamp(self):
        f = fixture(shared_fixtures.SharedDecisionTests, 'test_decision_replay_wakes_once_preserving_unrelated_dependencies')
        self.addCleanup(f.doCleanups)
        first = shared_fixtures.record(f.r, **f.args)
        self.assertEqual(first['code_revision'], provenance.stamp())
        stored = f.r.snapshot()['shared_preflight_decisions'][first['id']]
        self.assertEqual(stored['code_revision'], provenance.stamp())
        with f.r.transaction() as state:
            del state['shared_preflight_decisions'][first['id']]['code_revision']  # A pre-provenance record.
        replay = shared_fixtures.record(f.r, **f.args)
        self.assertEqual(replay['id'], first['id']); self.assertIsNone(replay['code_revision'])

    def test_consumer_verification_report(self):
        f = fixture(verification_fixtures.VerificationTests, 'test_integration_and_dispatch_are_not_success')
        self.addCleanup(f.doCleanups)
        f.r.probe = lambda _: 'alive'
        self.assertEqual(f.submit()['code_revision'], provenance.stamp())

    def test_dispose_review_record(self):
        f = fixture(delivery_fixtures.DeliveryTests, 'test_null_build_tooling_snapshot_and_review')
        self.addCleanup(f.doCleanups)
        lane = f.ready(reviews=True)
        record = f.reg.dispose_review('one', 1, lane['revision'], 'approved-1', lane['handoff']['sha256'],
                                      'shared.cpp', 'approved', 'reviewer', f.evidence)
        self.assertEqual(record['code_revision'], provenance.stamp())

    def test_submit_handoff_and_integrate_keep_receipts_exact(self):
        f = fixture(workflow_fixtures.WorkflowTests, 'test_handoff_review_and_integration_metrics')
        self.addCleanup(f.doCleanups)
        lane = f.running()
        lane = f.reg.submit_handoff('one', 1, 2, f.save_handoff(f.handoff(lane)))
        self.assertEqual(lane['handoff_code_revision'], provenance.stamp())
        self.assertEqual(set(lane['handoff']), {'path', 'sha256', 'result'})
        f.reg.checkpoint('one', 1, 3, {'state': 'integrating'})
        record = {'root_commit': 'b' * 40, 'validation_path': str(f.log), 'validation_sha256': digest(f.log)}
        done = f.reg.integrate('one', 1, 4, copy.deepcopy(record))
        self.assertEqual(done['integration'], record)
        self.assertEqual(done['integration_code_revision'], provenance.stamp())


class ServiceStatusTests(unittest.TestCase):
    identity = dict(host='h', pid=10, started='200')

    def registry(self, control, liveness='alive'):
        return SimpleNamespace(control_status=lambda: copy.deepcopy(control), probe=lambda _: liveness)

    def identify(self, table):
        def lookup(pid):
            if pid not in table:
                raise ProcessLookupError(pid)
            return dict(host='h', pid=pid, started=table[pid])
        return lookup

    def rows(self, parent_name, command, extra=()):
        return lambda: [dict(ProcessId=10, ParentProcessId=5, Name='python.exe', CommandLine='python pikmin2_controller.py'),
                        dict(ProcessId=5, ParentProcessId=1, Name=parent_name, CommandLine=command), *extra]

    def control(self, code=None):
        return dict(controller=self.identity, controller_code_revision=code or provenance.code_revision())

    def test_wrapper_parent_and_matching_code(self):
        wrapper = 'powershell.exe -File C:/x/scripts/Start-Pikmin2Controller.ps1 -WorkspaceRoot C:/x'
        data = service.status(self.registry(self.control()), self.rows('powershell.exe', wrapper),
                              self.identify({10: '200', 5: '100'}))
        self.assertEqual(data['parent']['parent'], 'wrapper')
        self.assertEqual(data['running'], provenance.code_revision())
        self.assertFalse(any('wrapper' in w or 'restart' in w for w in data['warnings']))

    def test_launcher_chain_is_followed(self):
        wrapper = 'powershell.exe -File Start-Pikmin2Controller.ps1'
        rows = self.rows('py.exe', 'py -3.12 pikmin2_controller.py',
                         [dict(ProcessId=1, ParentProcessId=0, Name='powershell.exe', CommandLine=wrapper)])
        data = service.status(self.registry(self.control()), rows, self.identify({10: '200', 5: '150', 1: '100'}))
        self.assertEqual(data['parent']['parent'], 'wrapper')

    def test_orphaned_reused_and_unreadable_parents(self):
        rows = lambda: [dict(ProcessId=10, ParentProcessId=5, Name='python.exe', CommandLine='x')]
        data = service.status(self.registry(self.control()), rows, self.identify({10: '200'}))
        self.assertEqual(data['parent']['parent'], 'not_wrapper')
        self.assertTrue(any('not supervised' in w for w in data['warnings']))
        reused = self.rows('powershell.exe', 'powershell.exe -File Start-Pikmin2Controller.ps1')
        self.assertEqual(service.status(self.registry(self.control()), reused,
                                        self.identify({10: '200', 5: '300'}))['parent']['parent'], 'not_wrapper')
        data = service.status(self.registry(self.control()), self.rows('powershell.exe', None),
                              self.identify({10: '200', 5: '100'}))
        self.assertEqual(data['parent']['parent'], 'unknown')
        self.assertTrue(any('parent unknown' in w for w in data['warnings']))
        other = service.status(self.registry(self.control()), self.rows('cmd.exe', 'cmd /c python x'),
                               self.identify({10: '200', 5: '100'}))
        self.assertEqual(other['parent']['parent'], 'not_wrapper')
        broken = service.status(self.registry(self.control()), lambda: None, self.identify({10: '200'}))
        self.assertEqual(broken['parent']['parent'], 'unknown')

    def test_dirty_mismatch_missing_and_dead_controllers_warn(self):
        running = dict(provenance.code_revision(), sha='f' * 40, dirty=True)
        data = service.status(self.registry(self.control(running), 'dead'))
        self.assertIsNone(data['parent'])
        text = ' '.join(data['warnings'])
        for fragment in ('is dead', 'DIRTY', 'restart needed'):
            self.assertIn(fragment, text)
        data = service.status(self.registry(dict(controller=None)))
        self.assertIn('No controller', data['warnings'][0])
        legacy = service.status(self.registry(dict(controller=self.identity), 'unknown'))
        self.assertTrue(any('provenance unknown' in w for w in legacy['warnings']))

    def test_operator_report_surfaces_loud_provenance(self):
        running = dict(sha='a' * 40, dirty=True, tree='b' * 64, path='p')
        data = report(dict(lanes={}, control=dict(controller_code_revision=running)), 5,
                      on_disk=dict(running, sha='c' * 40, dirty=False))
        line = code_line(data['code'])
        self.assertTrue(line.startswith('Code: running aaaaaaaaaaaa dirty=True | on disk cccccccccccc'))
        self.assertIn('!!! WARNING: Controller runs DIRTY code', line)
        self.assertIn('restart needed', line)
        self.assertIn('provenance unknown', code_line(report(dict(lanes={}), 5)['code']))


class PrepareReleaseTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = root = Path(temp.name).resolve()
        for name, text in {'.gitignore': '/output/\n__pycache__/\n', 'workflow/__init__.py': '',
                           'workflow/gate.py': 'RULE = 1\n', 'scripts/Start-Pikmin2Controller.ps1': 'param()\n',
                           'tests/__init__.py': '', 'tests/test_ok.py': 'def test_ok():\n    assert True\n',
                           'tests/workflow_release_tests.txt': 'tests/test_ok.py\n'}.items():
            (root / name).parent.mkdir(parents=True, exist_ok=True); (root / name).write_text(text)
        git(root, 'init', '-q'); git(root, 'add', '-A'); git(root, 'commit', '-qm', 'base')
        self.sha = git(root, 'rev-parse', 'HEAD').strip()
        self.config = root / 'output/workflow/controller.json'; self.config.parent.mkdir(parents=True)
        self.config.write_text(json.dumps(dict(output='output/workflow/controller')))
        self.calls = []

    def run_recorded(self, command, **kwargs):
        self.calls.append(command)
        return subprocess.run(command, **kwargs)

    def prepare(self, ref='HEAD', **kwargs):
        return service.prepare_release(self.root, ref, str(self.config), sys.executable, run=self.run_recorded, **kwargs)

    def test_creates_tests_and_prints_restart_without_touching_processes(self):
        data = self.prepare(identity=dict(host='h', pid=4242, started='1'))
        release = self.root / 'output/workflow/release' / self.sha[:12]
        self.assertEqual((Path(data['release']), data['sha'], data['created']), (release, self.sha, True))
        self.assertEqual((data['code_revision']['sha'], data['code_revision']['dirty']), (self.sha, False))
        self.assertIn('1 passed', data['tests'])
        self.assertEqual([c[3] if c[0] == 'git' else c[1:3] for c in self.calls], ['worktree', ['-m', 'pytest']])
        commands = '\n'.join(data['commands'])
        stop = (self.root / 'output/workflow/controller/STOP').as_posix()
        self.assertIn(f"New-Item -ItemType File -Force -Path '{stop}'", data['commands'][0])
        self.assertIn('Wait-Process -Id 4242', data['commands'][1])
        self.assertIn(f"Remove-Item -LiteralPath '{stop}'", data['commands'][2])
        self.assertIn((release / 'scripts/Start-Pikmin2Controller.ps1').as_posix(), data['commands'][3])
        self.assertIn(f"'-WorkspaceRoot','{self.root.as_posix()}'", commands)
        self.assertIn(f"'-Config','{self.config.as_posix()}'", commands)
        self.assertFalse((self.root / 'output/workflow/controller/STOP').exists())
        again = self.prepare()
        self.assertFalse(again['created']); self.assertEqual(again['release'], data['release'])

    def test_refuses_changed_release_dirty_worktree_unknown_ref_and_failing_tests(self):
        self.prepare()
        release = self.root / 'output/workflow/release' / self.sha[:12]
        (release / 'workflow/gate.py').write_text('RULE = 2\n')
        with self.assertRaisesRegex(Rejected, 'different content'):
            self.prepare()
        (self.root / 'workflow/gate.py').write_text('RULE = 3\n')
        with self.assertRaisesRegex(Rejected, 'uncommitted'):
            self.prepare(str(self.root))
        with self.assertRaisesRegex(Rejected, 'Unknown release ref'):
            self.prepare('no-such-ref')
        with self.assertRaisesRegex(Rejected, 'ref required'):
            self.prepare('--output=x')
        git(self.root, 'checkout', '--', '.')
        (self.root / 'tests/test_ok.py').write_text('def test_ok():\n    assert False\n')
        git(self.root, 'commit', '-qam', 'break'); broken = git(self.root, 'rev-parse', 'HEAD').strip()
        with self.assertRaisesRegex(Rejected, 'Release tests failed'):
            self.prepare(broken)

    def test_clean_worktree_path_ref_resolves_to_its_commit(self):
        self.assertEqual(self.prepare(str(self.root))['sha'], self.sha)


if __name__ == '__main__':
    unittest.main()
