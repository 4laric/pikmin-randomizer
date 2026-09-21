"""Deployment preflight guard for a workflow release directory (#868).

The preflight must fail closed on the exact defect that reached the live
controller: a lazy in-function import of a symbol the target module no longer
defines. It must also flag missing entrypoints/symbols and pass on this tree.
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

_SPEC = importlib.util.spec_from_file_location(
    'check_workflow_release', _ROOT / 'scripts' / 'check_workflow_release.py')
preflight = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(preflight)


def _write_release(base, review_decisions_body, delivery_body=''):
    (base / 'scripts').mkdir(parents=True, exist_ok=True)
    (base / 'workflow').mkdir(parents=True, exist_ok=True)
    for rel in preflight.REQUIRED_ENTRYPOINTS:
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('', encoding='utf-8')
    (base / 'workflow' / '__init__.py').write_text('', encoding='utf-8')
    (base / 'workflow' / 'review_decisions.py').write_text(review_decisions_body, encoding='utf-8')
    (base / 'workflow' / 'delivery.py').write_text(delivery_body, encoding='utf-8')
    return base


class ReleasePreflightTests(unittest.TestCase):
    def test_detects_dropped_symbol_in_lazy_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = _write_release(
                Path(tmp),
                review_decisions_body='def dispose_review(*a, **k):\n    return None\n',
                delivery_body=('def dispose_sole_review(self, *a, **k):\n'
                               '    from .review_decisions import apply_sole_disposition\n'
                               '    return apply_sole_disposition(self, *a, **k)\n'))
            problems = preflight.check_release(base, run_import_smoke=False)
            self.assertTrue(any('apply_sole_disposition' in p for p in problems),
                            problems)

    def test_missing_required_symbol_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = _write_release(
                Path(tmp),
                review_decisions_body='def apply_sole_disposition(*a, **k):\n    return None\n')
            problems = preflight.check_release(base, run_import_smoke=False)
            self.assertTrue(any('require_sole_authority' in p for p in problems), problems)

    def test_missing_entrypoint_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = _write_release(
                Path(tmp),
                review_decisions_body=(
                    'def apply_sole_disposition(*a, **k):\n    return None\n'
                    'def require_sole_authority(*a, **k):\n    return None\n'))
            (base / 'workflow' / 'review_decisions.py').write_text('', encoding='utf-8')
            (base / 'workflow' / 'review_decisions.py').unlink()
            problems = preflight.check_release(base, run_import_smoke=False)
            self.assertTrue(any('workflow/review_decisions.py' in p for p in problems), problems)

    def test_detects_unwired_required_monitor(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = _write_release(
                Path(tmp),
                review_decisions_body=(
                    'def apply_sole_disposition(*a, **k):\n    return None\n'
                    'def require_sole_authority(*a, **k):\n    return None\n'))
            problems = preflight.check_release(base, run_import_smoke=False)
            self.assertTrue(any('registry_wal' in p and 'unwired' in p for p in problems),
                            problems)

    def test_reports_monitor_imported_but_never_called(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = _write_release(
                Path(tmp),
                review_decisions_body=(
                    'def apply_sole_disposition(*a, **k):\n    return None\n'
                    'def require_sole_authority(*a, **k):\n    return None\n'))
            (base / 'workflow' / 'registry_wal.py').write_text(
                'def maintain(*a, **k):\n    return None\n'
                'def start_monitor(*a, **k):\n    return None\n', encoding='utf-8')
            (base / 'scripts' / 'pikmin2_controller.py').write_text(
                'from workflow.registry_wal import start_monitor\n', encoding='utf-8')
            problems = preflight.check_release(base, run_import_smoke=False)
            self.assertTrue(any('never calls it' in p for p in problems), problems)

    def test_accepts_wired_required_monitor(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = _write_release(
                Path(tmp),
                review_decisions_body=(
                    'def apply_sole_disposition(*a, **k):\n    return None\n'
                    'def require_sole_authority(*a, **k):\n    return None\n'))
            (base / 'workflow' / 'registry_wal.py').write_text(
                'def maintain(*a, **k):\n    return None\n'
                'def start_monitor(*a, **k):\n    return None\n', encoding='utf-8')
            (base / 'scripts' / 'pikmin2_controller.py').write_text(
                'from workflow.registry_wal import start_monitor as start_wal\n'
                'stop = start_wal(controller)\n', encoding='utf-8')
            problems = preflight.check_release(base, run_import_smoke=False)
            self.assertFalse(any('registry_wal' in p for p in problems), problems)

    def test_current_tree_passes_full_preflight(self):
        problems = preflight.check_release(_ROOT, run_import_smoke=True)
        self.assertEqual([], problems)


if __name__ == '__main__':
    unittest.main()
