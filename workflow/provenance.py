"""Which workflow code revision this process runs: git HEAD, dirty flag and a source tree hash.

Records stamp the compact form so any launch, decision or receipt can be tied to the
rules that produced it. Computing a revision never raises: an unreadable checkout is
reported as sha None and dirty True, never as clean.
"""
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import threading

CHECKOUT = Path(__file__).resolve().parents[1]
ENTRY = CHECKOUT / 'scripts' / 'workflow_module.py'
SCRIPTS = ('scripts/pikmin2_workflow.py', 'scripts/pikmin2_controller.py')
_lock = threading.Lock()
_cached = None


def git(path, *args, timeout=10):
    """Stdout of one bounded git call, or None when git is missing, slow or fails."""
    env = {k: v for k, v in os.environ.items() if k not in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE')}
    env['GIT_OPTIONAL_LOCKS'] = '0'  # Status must not refresh or lock a shared index.
    try:
        p = subprocess.run(['git', '-C', str(path), *args], capture_output=True, text=True, timeout=timeout,
                           env=env, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    return p.stdout if p.returncode == 0 else None


def tree(path):
    """sha256 over sorted (relative path, sha256 of bytes) of the workflow sources."""
    path = Path(path)
    files = sorted({p.relative_to(path).as_posix() for p in (path / 'workflow').rglob('*.py')} |
                   {s for s in SCRIPTS if (path / s).is_file()})
    total = hashlib.sha256()
    for name in files:
        total.update(f'{name}\0{hashlib.sha256((path / name).read_bytes()).hexdigest()}\n'.encode())
    return total.hexdigest()


def revision(path=CHECKOUT):
    """Uncached {sha, dirty, tree, path} of one checkout; never raises."""
    path = Path(path).resolve()
    head = (git(path, 'rev-parse', 'HEAD') or '').strip()
    sha = head if re.fullmatch(r'[0-9a-f]{40}', head) else None
    status = git(path, 'status', '--porcelain', '--', 'workflow', 'scripts') if sha else None
    try:
        digest = tree(path)
    except (OSError, ValueError):
        digest = None
    return dict(sha=sha, dirty=status is None or bool(status.strip()), tree=digest, path=str(path))


def code_revision():
    """This process's checkout, computed once and cached for the process lifetime."""
    global _cached
    with _lock:
        if _cached is None:
            _cached = revision()
        return dict(_cached)


def stamp():
    """Compact additive record field; the tree prefix is enough to tell revisions apart."""
    value = code_revision()
    return dict(sha=value['sha'], dirty=value['dirty'], tree=(value['tree'] or '')[:16] or None)


def unspaced(path):
    """Forward-slash path with no whitespace (Windows 8.3 form if needed); refuses otherwise.

    A quoted first word is an expression, not a command, in PowerShell, so no quoting
    renders one command line that PowerShell, cmd and bash all run.
    """
    text = Path(path).as_posix()
    if not re.search(r'\s', text):
        return text
    if os.name == 'nt':
        import ctypes
        buffer = ctypes.create_unicode_buffer(32768)
        if ctypes.windll.kernel32.GetShortPathNameW(str(path), buffer, len(buffer)) and not re.search(r'\s', buffer.value):
            return Path(buffer.value).as_posix()
    raise ValueError('Worker CLI path contains whitespace and has no short form: ' + text +
                     '; run the controller from a python and checkout without spaces')


def cli(module):
    """Absolute worker command for workflow.<module>, pinned to this interpreter and checkout.

    `python -m workflow.X` puts the caller's directory first on sys.path, so a worker
    standing in a lane worktree with an older workflow/ would run stale gate code.
    """
    return ' '.join((unspaced(sys.executable), unspaced(ENTRY), module))


def claimed(control):
    """Revision recorded by the current controller's own claim, else None.

    A claim by pre-provenance code replaces control.controller but not the revision
    field, so a revision recorded for another process must not describe this one.
    """
    code = (control or {}).get('controller_code_revision')
    if not isinstance(code, dict) or not control.get('controller') or code.get('process') != control['controller']:
        return None
    return {k: v for k, v in code.items() if k != 'process'}


def warnings(running, on_disk):
    """Loud, specific differences between the recorded running code and the checkout."""
    result = []
    if not running:
        result.append('Controller provenance unknown: its claim recorded no revision (pre-provenance code)')
        running = dict(sha=on_disk and on_disk.get('sha'))  # Only on-disk findings remain meaningful.
    elif running.get('sha') is None:
        result.append('Controller code revision unknown (git unavailable when it started)')
    if running.get('dirty'):
        result.append('Controller runs DIRTY code: uncommitted workflow/ or scripts/ changes')
    if on_disk:
        if on_disk.get('dirty'):
            result.append('Checkout ' + str(on_disk.get('path')) + ' has uncommitted workflow/ or scripts/ changes')
        if running.get('sha') != on_disk.get('sha'):
            result.append(f"Running sha {running.get('sha')} != on-disk sha {on_disk.get('sha')}: restart needed")
        elif running.get('tree') and on_disk.get('tree') and not on_disk['tree'].startswith(running['tree'][:16]):
            result.append('Checkout sources changed since the controller started: lazily imported modules may mix versions')
    return result
