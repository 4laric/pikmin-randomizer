"""Read-only controller service status and immutable release preparation.

  <python> <checkout>/scripts/workflow_module.py service status --root <root> [--json]
  <python> <checkout>/scripts/workflow_module.py service prepare-release --root <root>
      --ref <commit-ish or clean worktree> --config <controller config> [--python <exe>]

Neither command stops, starts or signals a process. prepare-release builds a clean
worktree at <root>/output/workflow/release/<short-sha>, runs the workflow tests inside
it and prints the restart commands for the operator to run.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from .handoff import Rejected, local_path, require
from .provenance import CHECKOUT, claimed, git, revision, warnings

WRAPPER = 'Start-Pikmin2Controller.ps1'
TESTS = 'tests/workflow_release_tests.txt'  # Whitespace-separated pytest arguments, versioned with the release.


def parent_check(identity, inventory=None, identify=None):
    """Is the controller's parent the restart wrapper? 'unknown' when it cannot be told."""
    from .processes import identify as current
    from .terminal_cleanup import process_inventory
    identify, inventory = identify or current, inventory or process_inventory
    unknown = lambda reason: dict(parent='unknown', reason=reason)
    try:
        if identify(identity['pid']) != identity:
            return unknown('Controller PID no longer has its recorded identity')
        rows = inventory()
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        return unknown('Cannot inspect processes: ' + (str(exc) or type(exc).__name__))
    rows = [rows] if isinstance(rows, dict) else rows
    if not isinstance(rows, list):
        return unknown('Process inventory unavailable on this host')
    child, started = identity['pid'], identity['started']
    for _ in range(3):  # py.exe and Store python aliases may sit between wrapper and controller.
        row = next((r for r in rows if r.get('ProcessId') == child), None)
        if row is None:
            return unknown(f'Process {child} missing from inventory')
        ppid = row.get('ParentProcessId')
        parent = next((r for r in rows if r.get('ProcessId') == ppid), None)
        try:
            parent_started = identify(ppid)['started'] if parent is not None else None
            reused = parent_started is not None and int(parent_started) > int(started)
        except ProcessLookupError:
            parent = None
        except (OSError, ValueError, KeyError, TypeError):
            return unknown(f'Cannot identify parent process {ppid}')
        if parent is None or reused:
            return dict(parent='not_wrapper', ppid=ppid,
                        reason=f'Parent process {ppid} has exited; nothing restarts a crashed controller')
        command = parent.get('CommandLine')
        if not command:
            return unknown(f'Command line of parent process {ppid} is not readable')
        if WRAPPER.lower() in command.lower():
            return dict(parent='wrapper', ppid=ppid, command=command)
        if not re.fullmatch(r'(py|pyw|python(\d+(\.\d+)*)?)\.exe', parent.get('Name') or '', re.I):
            return dict(parent='not_wrapper', ppid=ppid, command=command,
                        reason='Controller parent is not the ' + WRAPPER + ' wrapper')
        child, started = ppid, parent_started
    return unknown('Launcher chain too deep to attribute')


def started_at(identity):
    """Windows FILETIME creation stamps become UTC ISO; other hosts keep their raw value."""
    try:
        value = int(identity['started'])
    except (KeyError, TypeError, ValueError):
        return None
    if value < 10 ** 17:
        return None
    seconds = value / 10 ** 7 - 11644473600
    return datetime.datetime.fromtimestamp(seconds, datetime.timezone.utc).isoformat(timespec='seconds')


def controller_checkout(identity, inventory=None, identify=None):
    """(checkout, None) from the live controller's absolute pikmin2_controller.py argument, else (None, reason)."""
    from .processes import identify as current
    from .terminal_cleanup import process_inventory
    identify, inventory = identify or current, inventory or process_inventory
    if not identity:
        return None, 'No controller has claimed this registry'
    try:
        if identify(identity['pid']) != identity:
            return None, 'Controller PID no longer has its recorded identity'
        rows = inventory()
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        return None, 'Cannot inspect processes: ' + (str(exc) or type(exc).__name__)
    rows = [rows] if isinstance(rows, dict) else rows
    row = next((r for r in rows if r.get('ProcessId') == identity['pid']), None) if isinstance(rows, list) else None
    command = (row or {}).get('CommandLine')
    if not command:
        return None, 'Command line of controller process is not readable'
    match = re.search(r'"([^"]*pikmin2_controller\.py)"|(\S*pikmin2_controller\.py)', command, re.I)
    script = Path(match.group(1) or match.group(2)) if match else None
    if script is None or not script.is_absolute() or not script.is_file():
        return None, 'Controller command line names no absolute, existing pikmin2_controller.py'
    return script.resolve().parents[1], None


def code_status(control, on_disk=None, inventory=None, identify=None):
    """Running provenance of the current claim versus the checkout that controller runs from.

    Never substitutes the caller's checkout: an undeterminable controller checkout is
    reported as unknown."""
    running = claimed(control)
    notes = []
    if on_disk is None:
        path = Path(running['path']) if running and running.get('path') else None
        if path is None or not path.is_dir():
            path, reason = controller_checkout(control.get('controller'), inventory, identify)
            if path is None:
                notes.append('Controller checkout unknown (' + reason + '); on-disk comparison skipped')
        on_disk = revision(path) if path else None
    return dict(running=running, on_disk=on_disk, warnings=warnings(running, on_disk) + notes)


def status(reg, inventory=None, identify=None):
    """Controller identity, liveness, parent and code provenance; strictly read-only."""
    from .terminal_cleanup import process_inventory
    rows = []
    def listing():  # One process inventory serves both the checkout and the parent lookups.
        if not rows:
            rows.append((inventory or process_inventory)())
        return rows[0]
    control = reg.control_status()
    identity = control.get('controller')
    result = dict(controller=identity, started_at=started_at(identity or {}), **code_status(control, None, listing, identify))
    if not result['on_disk'] or CHECKOUT != Path(result['on_disk']['path']):
        result['this_checkout'] = revision(CHECKOUT)
    notes = result['warnings']
    if not identity:
        result.update(liveness=None, parent=None)
        notes.insert(0, 'No controller has claimed this registry')
        return result
    result['liveness'] = reg.probe(identity)
    if result['liveness'] != 'alive':
        result['parent'] = None
        notes.insert(0, f"Controller {identity.get('pid')} is {result['liveness']}")
        return result
    result['parent'] = parent_check(identity, listing, identify)
    if result['parent']['parent'] == 'not_wrapper':
        notes.append('Controller is not supervised by ' + WRAPPER + ': ' + result['parent']['reason'])
    elif result['parent']['parent'] == 'unknown':
        notes.append('Controller parent unknown: ' + result['parent']['reason'])
    return result


def _clean_worktree(path, sha):
    """A worktree of its own at exactly sha with no tracked or untracked changes."""
    top = (git(path, 'rev-parse', '--show-toplevel') or '').strip()
    head = (git(path, 'rev-parse', 'HEAD') or '').strip()
    changes = git(path, 'status', '--porcelain')
    return bool(top) and Path(top).resolve() == Path(path).resolve() and head == sha and changes == ''


def resolve_ref(root, ref):
    """Full commit sha of a ref, or of a clean worktree's HEAD; uncommitted trees refuse."""
    require(isinstance(ref, str) and ref.strip() and not ref.startswith('-'), 'Release ref required')
    if Path(ref).is_dir():
        changes = git(ref, 'status', '--porcelain')
        require(changes is not None, 'Release worktree is not readable by git: ' + ref)
        require(changes == '', 'Refusing release from a worktree with uncommitted changes: ' + ref)
        sha = (git(ref, 'rev-parse', 'HEAD') or '').strip()
    else:
        sha = (git(root, 'rev-parse', '--verify', '--end-of-options', ref + '^{commit}') or '').strip()
    require(re.fullmatch(r'[0-9a-f]{40}', sha), 'Unknown release ref: ' + ref)
    require(git(root, 'cat-file', '-e', sha + '^{commit}') is not None, 'Release commit not in canonical repository')
    return sha


def restart_commands(root, config, python, release, out, identity=None, parent=None):
    """PowerShell operator commands; printed, never executed here.

    A wrapper whose controller exits nonzero sleeps and relaunches unless STOP still
    exists, so STOP is removed only once the old wrapper is gone too. Start-Process
    joins -ArgumentList unquoted, so each path carries its own double quotes."""
    q = lambda s: "'" + str(s).replace("'", "''") + "'"
    arg = lambda path: q('"' + Path(path).as_posix() + '"')
    stop = (out / 'STOP').as_posix()
    wrapper = (release / 'scripts' / WRAPPER).as_posix()
    commands = [f'New-Item -ItemType File -Force -Path {q(stop)} | Out-Null']
    if identity and (parent or {}).get('parent') == 'wrapper':
        commands.append(f"Wait-Process -Id {identity['pid']},{parent['ppid']} -ErrorAction SilentlyContinue"
                        f"  # controller {identity['pid']} and its {WRAPPER} wrapper {parent['ppid']}")
    else:
        commands += ([f"Wait-Process -Id {identity['pid']} -ErrorAction SilentlyContinue  # controller {identity['pid']}"]
                     if identity else ['# Wait until service status reports the controller dead'])
        commands.append(f"# Wrapper not identified: before removing STOP, this must print nothing: Get-CimInstance Win32_Process"
                        f" | Where-Object CommandLine -like '*{WRAPPER}*' | Select-Object ProcessId,CommandLine")
    return commands + [f'Remove-Item -LiteralPath {q(stop)}',
            "Start-Process -WindowStyle Hidden -FilePath powershell.exe -ArgumentList "
            f"'-NoProfile','-ExecutionPolicy','Bypass','-File',{arg(wrapper)},"
            f"'-WorkspaceRoot',{arg(root)},'-Config',{arg(config)},'-Python',{arg(python)}",
            f"& {q(Path(python).as_posix())} {q((release / 'scripts/workflow_module.py').as_posix())} service status"
            f" --root {q(Path(root).as_posix())}"]


def call(run, command, what, **kwargs):
    """One subprocess; failure to start or finish refuses instead of raising a traceback."""
    try:
        return run(command, capture_output=True, text=True, **kwargs)
    except (OSError, subprocess.SubprocessError) as exc:
        raise Rejected(f"{what} could not run ({' '.join(map(str, command))}): {str(exc) or type(exc).__name__}")


def prepare_release(root, ref, config, python=None, tests=None, run=subprocess.run, identity=None, parent=None):
    """Create or reuse a clean release worktree, test it, return the restart plan."""
    root = Path(root).resolve()
    python = python or sys.executable
    config = local_path(root, str(config))
    require(config.is_file(), 'Controller config not found: ' + str(config))
    try:
        settings = json.loads(config.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as exc:
        raise Rejected('Controller config unreadable: ' + str(exc))
    output = settings.get('output') if isinstance(settings, dict) else None
    require(isinstance(output, str) and output.strip(), 'Controller config lacks output; the wrapper requires it')
    out = local_path(root, output)
    sha = resolve_ref(root, ref)
    release = root / 'output/workflow/release' / sha[:12]
    if release.exists():
        require(_clean_worktree(release, sha), 'Release directory exists with different content: ' + str(release))
        created = False
    else:
        release.parent.mkdir(parents=True, exist_ok=True)
        partial = lambda: (f'; partial release {release} remains: clear it with git -C {root} worktree remove --force'
                           f' {release} (or delete it and run git worktree prune)' if release.exists() else '')
        try:
            p = call(run, ['git', '-C', str(root), 'worktree', 'add', '--detach', str(release), sha], 'git worktree add',
                     timeout=600)
        except Rejected as exc:
            raise Rejected(str(exc) + partial())
        require(p.returncode == 0, 'git worktree add failed: ' + (p.stderr or '').strip() + partial())
        require(_clean_worktree(release, sha), 'New release worktree is not a clean checkout of ' + sha)
        created = True
    listing = release / (tests or TESTS)
    require(listing.is_file(), 'Release test list missing: ' + str(listing))
    names = listing.read_text(encoding='utf-8-sig').split()
    require(names, 'Release test list is empty')
    env = dict(os.environ, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1')
    for key in ('PYTHONPATH', 'GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE'):
        env.pop(key, None)
    try:
        p = call(run, [python, '-m', 'pytest', *names, '-q', '-p', 'no:cacheprovider'], 'Release tests',
                 cwd=release, env=env, timeout=3600)
    except Rejected as exc:
        raise Rejected(f'{exc}; release worktree {release} remains and a rerun reuses it')
    summary = ((p.stdout or '') + (p.stderr or '')).strip().splitlines()[-1:] or ['']
    require(p.returncode == 0, 'Release tests failed in ' + str(release) + ': ' + summary[0])
    require(_clean_worktree(release, sha), 'Release tests modified the release worktree')
    code = revision(release)
    require(code['sha'] == sha and not code['dirty'], 'Release provenance is not clean')
    return dict(release=str(release), sha=sha, created=created, tests=summary[0], code_revision=code,
                commands=restart_commands(root, config, python, release, out, identity, parent))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    s = sub.add_parser('status', help='Read-only controller, parent and code provenance status')
    s.add_argument('--root', type=Path, required=True)
    s.add_argument('--json', action='store_true')
    r = sub.add_parser('prepare-release', help='Build and test a release worktree; print restart commands')
    r.add_argument('--root', type=Path, required=True)
    r.add_argument('--ref', required=True)
    r.add_argument('--config', type=Path, required=True)
    r.add_argument('--python', default=sys.executable)
    r.add_argument('--tests', help='Test list inside the release (default ' + TESTS + ')')
    args = parser.parse_args(argv)
    from .registry import Registry
    root = args.root.resolve()
    reg = Registry(root / 'output/workflow/registry.sqlite3', root)
    try:
        if args.command == 'status':
            data = status(reg)
            if args.json:
                print(json.dumps(data, indent=2))
                return 0
            c, run = data['controller'] or {}, data['running'] or {}
            print(f"Controller: pid {c.get('pid')} on {c.get('host')} started {data['started_at'] or c.get('started')} "
                  f"({data['liveness']}); parent: {(data['parent'] or {}).get('parent')}")
            print(f"Running code: {run.get('sha')} dirty={run.get('dirty')} tree={run.get('tree')} at {run.get('path')}")
            d = data['on_disk']
            print(f"On disk:      {d['sha']} dirty={d['dirty']} tree={d['tree']} at {d['path']}" if d else
                  'On disk:      unknown (controller checkout not determined)')
            if data.get('this_checkout'):
                t = data['this_checkout']
                print(f"This checkout: {t['sha']} dirty={t['dirty']} tree={t['tree']} at {t['path']} (not the controller's)")
            for note in data['warnings']:
                print('WARNING: ' + note)
            return 1 if data['warnings'] else 0
        try:
            identity = reg.control_status().get('controller')
        except Rejected:
            identity = None  # A release can be prepared before any controller exists.
        identity = identity if identity and reg.probe(identity) == 'alive' else None
        parent = parent_check(identity) if identity else None
        data = prepare_release(root, args.ref, args.config, args.python, args.tests, identity=identity, parent=parent)
    except Rejected as exc:
        print('Refused: ' + str(exc), file=sys.stderr)
        return 2
    print(f"Release {data['sha']} ready at {data['release']} ({'created' if data['created'] else 'reused'}); "
          f"tests: {data['tests']}")
    print('Run these yourself to switch the controller (workers keep running):')
    for line in data['commands']:
        print('  ' + line)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
