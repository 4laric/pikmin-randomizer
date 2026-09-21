"""Static import-contract guard for the workflow package.

A dropped hunk in an integration merge once removed a symbol from a workflow
module while another module still lazily imported it; the package kept
importing because the import sat inside a function, so the breakage only
surfaced when the affected integration path was exercised (#845).

This guard parses every ``workflow/*.py`` module without executing it and
verifies that each relative ``from .module import name`` (including imports
nested inside functions and methods) refers to a name the target module
actually defines or re-exports. It also verifies ``from . import submodule``
targets exist. Imports guarded by ``except ImportError``/``ModuleNotFoundError``
are treated as optional and skipped.
"""
import ast
import unittest
from pathlib import Path

import workflow

_PKG = Path(workflow.__file__).parent
_OPTIONAL = ('ImportError', 'ModuleNotFoundError')


def _bindings(tree):
    """Names bound at module level: defs, classes, assignments and import aliases."""
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


def _targets(node):
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, (ast.Tuple, ast.List)):
        found = set()
        for item in node.elts:
            found.update(_targets(item))
        return found
    return set()


def _optional_imports(tree):
    """Line numbers of relative imports inside try/except ImportError blocks."""
    lines = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        if not any(getattr(h.type, 'id', getattr(h.type, 'attr', None)) in _OPTIONAL
                   or (isinstance(h.type, ast.Tuple) and any(
                       getattr(e, 'id', getattr(e, 'attr', None)) in _OPTIONAL for e in h.type.elts))
                   for h in node.handlers):
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.ImportFrom):
                lines.add(child.lineno)
    return lines


def _module_names(path):
    tree = ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
    if any(isinstance(n, ast.FunctionDef) and n.name == '__getattr__' for n in tree.body):
        return None  # Module exposes dynamic attributes; skip strict name checking.
    return _bindings(tree)


def violations(package=_PKG):
    """List ``(module, lineno, imported, target)`` contract violations."""
    defined = {}
    optional = {}
    for path in sorted(package.glob('*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
        defined[path.stem] = _module_names(path)
        optional[path] = _optional_imports(tree)

    problems = []
    for path in sorted(package.glob('*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.level == 0:
                continue
            if node.lineno in optional.get(path, set()):
                continue
            if node.level != 1:
                problems.append((path.stem, node.lineno, '.'.join(a.name for a in node.names),
                                 'relative level %d unsupported' % node.level))
                continue
            target = node.module
            if not target:
                for alias in node.names:
                    if alias.name == '*':
                        continue
                    if (package / (alias.name + '.py')).exists() or (package / alias.name).is_dir():
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


class ImportContractTests(unittest.TestCase):
    def test_relative_imports_resolve(self):
        found = violations()
        detail = '\n'.join('%s.py:%d imports %r from .%s' % v for v in found)
        self.assertEqual([], found, 'Broken workflow import contracts (dropped symbol?):\n' + detail)

    def test_sole_disposition_contract_is_wired(self):
        from workflow import review_decisions
        from workflow.registry import Registry
        self.assertTrue(callable(review_decisions.apply_sole_disposition))
        self.assertTrue(callable(review_decisions.require_sole_authority))
        self.assertTrue(callable(Registry.dispose_sole_review))


if __name__ == '__main__':
    for item in violations():
        print('%s.py:%d imports %r from .%s' % item)
    unittest.main()
