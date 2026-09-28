"""Run one workflow CLI module from this checkout, whatever the caller's directory.

Usage: <python> <checkout>/scripts/workflow_module.py <module> [args...]
`python -m workflow.<module>` imports whichever workflow/ is in the current directory;
this entry pins the package to the checkout containing this script.
"""
from pathlib import Path
import re
import runpy
import sys

CHECKOUT = Path(__file__).resolve().parents[1]


def resolve(name):
    """Only real modules of this checkout's workflow package; None refuses."""
    name = name.removeprefix('workflow.')
    if not re.fullmatch(r'[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*', name):
        return None
    path = CHECKOUT / 'workflow' / (name.replace('.', '/') + '.py')
    return name if path.is_file() else None


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    name = resolve(argv[0]) if argv else None
    if name is None:
        print('Refused: expected a module of the workflow package, e.g. workflow_module.py review_decisions --root ...',
              file=sys.stderr)
        return 2
    sys.path.insert(0, str(CHECKOUT))
    import workflow
    if Path(workflow.__file__).resolve().parent != CHECKOUT / 'workflow':
        print('Refused: workflow package resolved outside ' + str(CHECKOUT), file=sys.stderr)
        return 2
    sys.argv = [str(CHECKOUT / 'workflow' / (name.replace('.', '/') + '.py'))] + argv[1:]
    runpy.run_module('workflow.' + name, run_name='__main__', alter_sys=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
