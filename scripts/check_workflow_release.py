#!/usr/bin/env python3
"""Fail-closed preflight for a workflow release directory.

A release is a clean git worktree of the integration line that is about to
replace the live controller. Packaging only proves the worktree is clean, not
that its ``workflow`` package still satisfies the import contract. A dropped
hunk in a "snapshot the live tooling" merge once removed a symbol from a module
while another module lazily imported it inside a function, so the package kept
importing and the break surfaced only when the integration path ran (#845).

This preflight validates the release *before* the live controller is stopped:

* every relative ``from .module import name`` / ``from . import submodule`` in
  ``workflow/*.py`` resolves (including imports nested in functions), skipping
  optional imports guarded by ``except ImportError``/``ModuleNotFoundError``;
* the deployment entrypoints and integration modules exist;
* required integration symbols are defined;
* the package and controller entrypoint import cleanly in a fresh interpreter.

Exit status is nonzero when any finding is reported, so a caller can abort a
deployment without touching the running controller. This is a packaging/import
guard only; it never asserts gameplay or integration acceptance.
"""
import argparse
import ast
import subprocess
import sys
from pathlib import Path

REQUIRED_ENTRYPOINTS = (
    'scripts/workflow_module.py',
    'scripts/pikmin2_controller.py',
    'workflow/review_decisions.py',
)
# Modules whose named symbols the controller/reduced path imports lazily.
REQUIRED_SYMBOLS = {
    'workflow/review_decisions.py': ('apply_sole_disposition', 'require_sole_authority'),
}
OPTIONAL = ('ImportError', 'ModuleNotFoundError')
IMPORT_SMOKE = (
    'import workflow\n'
    'from workflow import review_decisions, delivery\n'
    'from workflow.registry import Registry\n'
    'assert callable(review_decisions.apply_sole_disposition), "apply_sole_disposition not callable"\n'
    'assert callable(review_decisions.require_sole_authority), "require_sole_authority not callable"\n'
    'assert hasattr(Registry, "dispose_sole_review"), "Registry.dispose_sole_review missing"\n'
)


def _targets(node):
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, (ast.Tuple, ast.List)):
        found = set()
        for item in node.elts:
            found.update(_targets(item))
        return found
    return set()


def _bindings(tree):
    """Names bound at module level: defs, classes, assignments and imports."""
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                names.update(_targets(target))
        elif isinstance(node, ast.AnnAssign):
            names.update(_targets(node.target))
        elif isinstance(node, ast.Import):
            names.update(a.asname or a.name.split('.')[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.update(a.asname or a.name for a in node.names if a.name != '*')
        elif (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
              and getattr(node.value.func, 'id', None) == '__all__'):
            for arg in node.value.args:
                if isinstance(arg, (ast.List, ast.Tuple)):
                    names.update(e.value for e in arg.elts if isinstance(e, ast.Constant))
    return names


def _optional_imports(tree):
    lines = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        optional = False
        for handler in node.handlers:
            names = []
            if handler.type is not None:
                names = [getattr(handler.type, 'id', getattr(handler.type, 'attr', None))]
                if isinstance(handler.type, ast.Tuple):
                    names = [getattr(e, 'id', getattr(e, 'attr', None)) for e in handler.type.elts]
            if any(name in OPTIONAL for name in names):
                optional = True
        if not optional:
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.ImportFrom):
                lines.add(child.lineno)
    return lines


def _module_names(path):
    tree = ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
    if any(isinstance(n, ast.FunctionDef) and n.name == '__getattr__' for n in tree.body):
        return None  # Dynamic attributes; skip strict name checking.
    return _bindings(tree)


def import_contract_violations(workflow_dir):
    """List ``(module, lineno, imported, target)`` contract violations."""
    workflow_dir = Path(workflow_dir)
    defined = {}
    optional = {}
    for path in sorted(workflow_dir.glob('*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
        defined[path.stem] = _module_names(path)
        optional[path] = _optional_imports(tree)

    problems = []
    for path in sorted(workflow_dir.glob('*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.level == 0:
                continue
            if node.lineno in optional.get(path, set()):
                continue
            if node.level != 1:
                problems.append((path.stem, node.lineno,
                                 '.'.join(a.name for a in node.names),
                                 'relative level %d unsupported' % node.level))
                continue
            target = node.module
            if not target:
                for alias in node.names:
                    if alias.name == '*':
                        continue
                    if (workflow_dir / (alias.name + '.py')).exists() or (workflow_dir / alias.name).is_dir():
                        continue
                    package_names = defined.get('__init__')
                    if package_names is None or alias.name in package_names:
                        continue
                    problems.append((path.stem, node.lineno, alias.name, '<package submodule>'))
                continue
            if target not in defined:
                problems.append((path.stem, node.lineno, target, '<missing module>'))
                continue
            target_names = defined[target]
            if target_names is None:
                continue
            for alias in node.names:
                if alias.name == '*':
                    continue
                if alias.name not in target_names:
                    problems.append((path.stem, node.lineno, alias.name, target))
    return problems


def check_release(release_dir, run_import_smoke=True):
    """Return a list of human-readable problems for a candidate release.

    An empty list means the release passed every preflight check.
    """
    release_dir = Path(release_dir)
    problems = []

    if not release_dir.is_dir():
        return ['Release directory does not exist: %s' % release_dir]

    workflow_dir = release_dir / 'workflow'
    if not workflow_dir.is_dir():
        problems.append('Missing workflow package: %s' % workflow_dir)
    else:
        for module, lineno, imported, target in import_contract_violations(workflow_dir):
            problems.append(
                'workflow/%s.py:%d imports %r from .%s (broken import contract)'
                % (module, lineno, imported, target))

    for rel in REQUIRED_ENTRYPOINTS:
        if not (release_dir / rel).is_file():
            problems.append('Missing required entrypoint: %s' % rel)

    for rel, symbols in REQUIRED_SYMBOLS.items():
        path = release_dir / rel
        if not path.is_file():
            continue
        names = _module_names(path)
        if names is None:
            continue
        for symbol in symbols:
            if symbol not in names:
                problems.append('%s does not define required symbol %r' % (rel, symbol))

    if run_import_smoke and not problems:
        try:
            result = subprocess.run(
                [sys.executable, '-c', IMPORT_SMOKE],
                cwd=str(release_dir), capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.SubprocessError) as exc:
            problems.append('Import smoke could not run: %s' % exc)
        else:
            if result.returncode != 0:
                detail = (result.stderr or result.stdout or '').strip().splitlines()
                problems.append('Import smoke failed (exit %d): %s'
                                % (result.returncode, detail[-1] if detail else 'no output'))

    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', type=Path, default=Path(__file__).resolve().parent.parent,
                        help='release directory to check (default: parent of this script)')
    parser.add_argument('--no-import-smoke', action='store_true',
                        help='skip executing the package in a fresh interpreter')
    args = parser.parse_args(argv)

    problems = check_release(args.release, run_import_smoke=not args.no_import_smoke)
    if problems:
        print('Release preflight FAILED for %s' % args.release)
        for problem in problems:
            print('  - %s' % problem)
        return 1
    print('Release preflight passed for %s' % args.release)
    return 0


if __name__ == '__main__':
    sys.exit(main())
