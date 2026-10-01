"""Gate-F process-restart driver for the lane-13 Dwarf Orange Bulborb candidate.

Closes the "persistence across process restart" leg at identity/content level:
the SAME instrumented fixture executable is launched as two independent,
strictly sequential processes inside a private copy of the two-actor arena. Both
runs must publish the same BlueKochappy 44 identity, the same 64-pose bank marker
and the same ``P2_DWARF_ORANGE_ARENA_BIRTH`` health/XYZ for generators 211001 and
211002.

Scope: this slice has no P2 Pod/reward binding, so reward duplication or loss
across restart is not applicable (P2 reward once-credit is lane 06). The driver
also records whether any save file content changed between the two runs.

The two launches are one serialized session (an advisory GL lock), and at most
``MAX_RUNS`` processes are started. Never run this while another P2 game run is
active.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

ID_SOURCE = 211001
ID_CONTROL = 211002
MAX_RUNS = 2
ENEMY_READY = 'P2_ENEMY_READY '
BANK = 'P2_DWARF_ORANGE_BANK '
BIRTH = 'P2_DWARF_ORANGE_ARENA_BIRTH '
SAVE_ROOTS = ('save', 'assets/dataDir/savedata')
VOLATILE = {BANK: ('load_seconds',)}
EXPECTED = {
    ID_SOURCE: {'health': '250.0', 'x': '-150.000', 'y': '30.000', 'z': '1850.000'},
    ID_CONTROL: {'health': '130.0', 'x': '150.000', 'y': '30.000', 'z': '1550.000'},
}
GL_LOCK = Path(os.environ.get('PIKMIN_P2_GL_LOCK',
                              Path(tempfile.gettempdir()) / 'pikmin2-gl.lock'))
RUNTIME_BIN = Path(os.environ.get('PIKMIN2_RUNTIME_BIN', r'C:\msys64\mingw64\bin'))


class SessionBusy(RuntimeError):
    """Raised when another serialized P2 game run holds the GL lock."""


def fields(line):
    return dict(re.findall(r'([A-Za-z_]+)=([^\s]+)', line))


def stable(line):
    """Drop run-to-run volatile fields (never identity/content)."""
    for prefix, keys in VOLATILE.items():
        if line.startswith(prefix):
            for key in keys:
                line = re.sub(rf'\s{key}=[^\s]+', '', line)
    return line


def markers(log):
    ready, bank, births = [], [], {}
    for line in log.splitlines():
        if line.startswith(ENEMY_READY):
            ready.append(line)
        elif line.startswith(BANK):
            bank.append(line)
        elif line.startswith(BIRTH):
            ident = fields(line).get('id')
            if ident is not None:
                births[int(ident)] = line
    return {'enemy_ready': ready, 'bank': bank, 'births': births}


def _compare_lines(run1, run2):
    return {'run1': list(run1), 'run2': list(run2),
            'identical': len(run1) == len(run2)
            and all(stable(a) == stable(b) for a, b in zip(run1, run2))}


def _compare_birth(births1, births2, ident):
    first, second = births1.get(ident), births2.get(ident)
    return {'id': ident, 'run1': first, 'run2': second,
            'identical': first is not None and second is not None
            and stable(first) == stable(second)}


def compare(one, two):
    groups = {
        'enemy_ready': _compare_lines(one['enemy_ready'], two['enemy_ready']),
        'bank': _compare_lines(one['bank'], two['bank']),
    }
    for ident in (ID_SOURCE, ID_CONTROL):
        groups[f'birth_{ident}'] = _compare_birth(one['births'], two['births'], ident)
    groups['identical'] = all(group['identical'] for key, group in groups.items()
                              if key != 'identical')
    return groups


def _birth_matches(line, expected):
    if line is None:
        return False
    parsed = fields(line)
    return all(parsed.get(key) == value for key, value in expected.items())


def content_checks(one):
    ready, bank, births = one['enemy_ready'], one['bank'], one['births']
    ready_fields = fields(ready[0]) if len(ready) == 1 else {}
    bank_fields = fields(bank[0]) if len(bank) == 1 else {}
    return {
        'enemy_ready_once': len(ready) == 1,
        'enemy_identity': len(ready) == 1 and ready_fields.get('species') == 'BlueKochappy'
                          and ready_fields.get('source_id') == '44',
        'enemy_health': len(ready) == 1 and ready_fields.get('health') == '250.0'
                        and ready_fields.get('max_health') == '250.0',
        'bank_once': len(bank) == 1,
        'bank_poses': len(bank) == 1 and bank_fields.get('poses') == '64',
        'birth_source': _birth_matches(births.get(ID_SOURCE), EXPECTED[ID_SOURCE]),
        'birth_control': _birth_matches(births.get(ID_CONTROL), EXPECTED[ID_CONTROL]),
    }


def run_checks(log, exit_code):
    return {
        'exit_zero': exit_code == 0,
        'completion': 'DONE P2_DWARF_ORANGE_COMBAT' in log,
        'window': '960x540' in log,
        'no_extinction': 'Extinction' not in log,
    }


def evaluate(log1, code1, log2, code2):
    one, two = markers(log1), markers(log2)
    comparison = compare(one, two)
    checks = {
        'run1': {**run_checks(log1, code1), **content_checks(one)},
        'run2': {**run_checks(log2, code2), **content_checks(two)},
    }
    return {'markers_run1': one, 'markers_run2': two, 'comparison': comparison,
            'checks': checks, 'identical': comparison['identical'],
            'passed': comparison['identical']
            and all(checks['run1'].values()) and all(checks['run2'].values())}


def copy_arena(source, dest):
    source, dest = Path(source).resolve(), Path(dest).resolve()
    if source == dest or source in dest.parents or dest in source.parents:
        raise ValueError('Refusing to copy the arena onto or under itself')
    shutil.copytree(source, dest)
    return dest


def snapshot(root):
    root = Path(root)
    state = {}
    for rel in SAVE_ROOTS:
        base = root / rel
        if not base.is_dir():
            continue
        for path in base.rglob('*'):
            if path.is_file():
                state[path.relative_to(root).as_posix()] = hashlib.sha256(
                    path.read_bytes()).hexdigest()
    return state


def save_delta(before, after):
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(key for key in set(before) & set(after) if before[key] != after[key])
    return {'added': added, 'removed': removed, 'changed': changed,
            'any': bool(added or removed or changed)}


def session_dirs(root):
    base = Path(root) / 'save' / 'bbft_sessions'
    if not base.is_dir():
        return []
    return sorted(path.name for path in base.iterdir() if path.is_dir())


def ensure_runtime_path(runtime=RUNTIME_BIN):
    """Prepend the MinGW runtime dir (libgcc/libstdc++/SDL2) for the fixture."""
    runtime = Path(runtime)
    if runtime.is_dir():
        current = os.environ.get('PATH', '')
        if str(runtime) not in current.split(os.pathsep):
            os.environ['PATH'] = str(runtime) + os.pathsep + current
    return os.environ.get('PATH', '')


@contextmanager
def serialized(lock=GL_LOCK):
    """Advisory single-game lock: refuse to start while another run holds it."""
    lock = Path(lock)
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise SessionBusy(f'another P2 game run holds {lock}') from exc
    try:
        os.write(handle, str(os.getpid()).encode())
        yield
    finally:
        os.close(handle)
        try:
            lock.unlink()
        except OSError:
            pass


def run_restart(arena, exe, output, seconds=180, window='960x540'):
    from experimental.pikmin2_animation_profile import capture_command
    from experimental.pikmin2_dwarf_orange_runtime import positions
    arena, exe, output = (Path(p).resolve() for p in (arena, exe, output))
    if seconds <= 0:
        raise ValueError('Seconds must be positive')
    output.mkdir(parents=True, exist_ok=False)
    stage = copy_arena(arena, output / 'arena')
    positions(stage)
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = window
    ensure_runtime_path()
    files_before, dirs_before = snapshot(stage), session_dirs(stage)
    with serialized():
        run1 = capture_command([str(exe), '--experimental-pikmin2-room'],
                               stage, output / 'run1', seconds)
        files_after1, dirs_after1 = snapshot(stage), session_dirs(stage)
        run2 = capture_command([str(exe), '--experimental-pikmin2-room'],
                               stage, output / 'run2', seconds)
        files_after2, dirs_after2 = snapshot(stage), session_dirs(stage)
    log1 = (output / 'run1' / 'native.log').read_text(errors='replace')
    log2 = (output / 'run2' / 'native.log').read_text(errors='replace')
    result = evaluate(log1, run1['exit_code'], log2, run2['exit_code'])
    result.update({
        'gate': 'F persistence: identity/content across process restart',
        'arena_source': str(arena), 'arena_copy': str(stage), 'exe': str(exe),
        'exe_sha256': run1.get('executable_sha256'), 'window': window,
        'serialized': True, 'run_count': MAX_RUNS, 'runs': [run1, run2],
        'log_run1': str(output / 'run1' / 'native.log'),
        'log_run2': str(output / 'run2' / 'native.log'),
        'reward_scope': {'applicable': False, 'detail':
                         'no P2 Pod/reward in this slice; P2 once-credit is lane 06'},
        'save': {
            'files_before_run1': files_before,
            'files_after_run1': files_after1,
            'files_after_run2': files_after2,
            'delta_run1': save_delta(files_before, files_after1),
            'delta_run2': save_delta(files_after1, files_after2),
            'session_dirs_before': dirs_before,
            'session_dirs_after_run1': dirs_after1,
            'session_dirs_after_run2': dirs_after2,
        },
    })
    (output / 'restart.json').write_text(json.dumps(result, indent=2))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    run = sub.add_parser('run')
    for name in ('arena', 'exe', 'output'):
        run.add_argument('--' + name, type=Path, required=True)
    run.add_argument('--seconds', type=int, default=180)
    args = parser.parse_args(argv)
    result = run_restart(args.arena, args.exe, args.output, args.seconds)
    print(json.dumps({k: v for k, v in result.items() if k != 'markers_run1'
                      and k != 'markers_run2'}, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
