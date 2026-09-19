'''Private leased build/run harness for the #672 P2 challenge boot fixture.

Builds native/tools/p2_challenge_boot_fixture.cpp (stage-selectable boot TU,
module TU ridden along via include, no CMake edit) against a private leased
pikmin_pc build using the maintained replacement-main builder
(scripts/build_pikmin2_fixture.py), then runs the guarded chain.

Phases: configure (leased cmake), build (leased pikmin_pc plus ninja -n),
fixture (provenance-checked link, exe SHA-256), guardcheck (live self-test
plus compiled header-only negative path), run (headed chain run with
ordered-marker validation), all. The fixture consumes the captain guard
header-only (p2_fixture_captain_guard.h) from the canonical checkout scripts
via CPLUS_INCLUDE_PATH; the harness records its SHA-256 and never copies it.

Captain safety #632: guard before every observed tick; captain-down exits 86
(BLOCKED) with P2_FIXTURE_CAPTAIN_DOWN and can never be a live tick.
'''


import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ROOT = Path('C:/Users/alari/pikmin-randomizer')
sys.path.insert(0, str(CANONICAL_ROOT))

FIXTURE_REL = Path('tools/p2_challenge_boot_fixture.cpp')
GUARD_NAME = 'p2_fixture_captain_guard.h'
NEGATIVE_EXIT = 86

def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def resolve_guard(guard_dir=None):
    if guard_dir is not None:
        candidate = Path(guard_dir) / GUARD_NAME
    else:
        candidate = CANONICAL_ROOT / 'scripts' / GUARD_NAME
    if not candidate.is_file():
        raise ValueError('Missing captain guard header: ' + str(candidate))
    return candidate.resolve()


def guard_record(guard_dir=None):
    path = resolve_guard(guard_dir)
    return {'path': str(path), 'sha256': sha256(path)}


def parse_markers(text):
    rows = []
    for line in text.splitlines():
        if line.startswith('P2_CHALLENGE_BOOT_'):
            head = line.partition(' ')[0]
            rows.append((head[len('P2_CHALLENGE_BOOT_'):], line))
        elif line.startswith('P2_CHALLENGE_MODE_'):
            head = line.partition(' ')[0]
            rows.append((head[len('P2_CHALLENGE_MODE_'):], line))
        elif line.startswith('P2_FIXTURE_CAPTAIN_DOWN'):
            rows.append(('CAPTAIN_DOWN', line))
    return rows


def check_chain(rows):
    kinds = [kind for kind, _ in rows]
    if 'CAPTAIN_DOWN' in kinds:
        return False, 'captain-down during chain run'
    required = ['BOOT', 'TICK', 'DONE']
    positions = {}
    for want in required:
        try:
            positions[want] = kinds.index(want)
        except ValueError:
            return False, 'missing marker: ' + want
    if not (positions['BOOT'] < positions['TICK'] < positions['DONE']):
        return False, 'markers out of order'
    ticks = kinds.count('TICK')
    if ticks < 3:
        return False, 'expected at least 3 TICK markers'
    return True, 'chain BOOT..TICK..DONE in order'


def interpret_exit(code, text):
    rows = parse_markers(text)
    if code == NEGATIVE_EXIT and any(k == 'CAPTAIN_DOWN' for k, _ in rows):
        return {'verdict': 'blocked', 'detail': 'guard CAPTAIN_DOWN exit 86'}
    if code == 0:
        ok, detail = check_chain(rows)
        return {'verdict': 'pass' if ok else 'fail', 'detail': detail}
    return {'verdict': 'fail', 'detail': 'exit ' + str(code)}

def negative_source():
    return ('#include ' + chr(34) + GUARD_NAME + chr(34) + chr(10)
        + 'int main()' + chr(10) + '{' + chr(10)
        + '    p2_fixture_require_captain(true, false, 0.0f, 7);' + chr(10)
        + '    return 0;' + chr(10) + '}' + chr(10))


def build_negative(compiler, guard_dir, workdir):
    workdir = Path(workdir)
    src = workdir / 'guard_negative.cpp'
    src.write_text(negative_source(), encoding='utf-8')
    exe = workdir / 'guard_negative.exe'
    env = dict(os.environ, PATH=str(Path(compiler).parent) + os.pathsep + os.environ.get('PATH', ''))
    proc = subprocess.run([str(compiler), '-std=c++17', '-I', str(guard_dir), str(src), '-o', str(exe)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', timeout=120, env=env)
    if proc.returncode or not exe.is_file():
        raise RuntimeError('Negative guard TU failed to compile')
    return exe


def run_exe(exe, timeout=300):
    proc = subprocess.run([str(exe)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', timeout=timeout, env=dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', '')), creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    return proc.returncode, proc.stdout


def evidence_record(**fields):
    record = {'schema': 1, 'kind': 'p2-challenge-boot-build'}
    record.update(fields)
    return record


def validate_evidence(record):
    if not isinstance(record, dict) or record.get('schema') != 1:
        raise ValueError('Evidence schema must be 1')
    for key in ('native_head', 'exe_sha256', 'guard_sha256', 'ninja_dry_run', 'chain', 'exit'):
        if key not in record:
            raise ValueError('Evidence missing: ' + key)
    if record['chain'] != 'pass':
        raise ValueError('Chain run did not pass')
    if record['exit'] != 0:
        raise ValueError('Fixture exit was not 0')
    return record


def toolchain(ninja_dir=None):
    if ninja_dir is None:
        import ninja
        ninja_dir = str(Path(ninja.BIN_DIR))
    return ninja_dir


def lease_key():
    return 'challenge-boot-native-fixture'


def lease_generation(reg=None):
    if reg is None:
        from workflow.registry import Registry
        reg = Registry(CANONICAL_ROOT / 'output/workflow/registry.sqlite3', CANONICAL_ROOT)
    return reg.status()['lanes'][lease_key()]['generation']


def acquire(resource, pid, ttl=300):
    from workflow.registry import Registry
    reg = Registry(CANONICAL_ROOT / 'output/workflow/registry.sqlite3', CANONICAL_ROOT)
    return reg, reg.acquire(lease_key(), lease_generation(), resource, pid, ttl=ttl)


def renew(reg, resource, token, ttl=300):
    return reg.renew(lease_key(), lease_generation(), resource, token, ttl=ttl)


def release(reg, resource, token):
    return reg.release(lease_key(), lease_generation(), resource, token)

def phase_configure(native, build, ninja_dir, log_path):
    build = Path(build)
    build.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''))
    cmd = ['cmake', '-S', str(native), '-B', str(build), '-G', 'Ninja',
        '-DCMAKE_MAKE_PROGRAM=' + ninja_dir + '/ninja.exe',
        '-DCMAKE_BUILD_TYPE=RelWithDebInfo',
        '-DCMAKE_C_COMPILER=gcc', '-DCMAKE_CXX_COMPILER=g++',
        '-DPIKMIN_NATIVE_JAUDIO=ON', '-DPIKMIN_NATIVE_OPTIMIZE=OFF',
        '-DPIKMIN_RANDOMIZER_TEST_HOOKS=OFF']
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', timeout=900, env=env)
    Path(log_path).write_text(proc.stdout, encoding='utf-8')
    return proc.returncode


def phase_build(build, log_path, ninja_dir):
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''))
    proc = subprocess.run(['cmake', '--build', str(build), '--target', 'pikmin_pc', '-j', '6'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', timeout=3600, env=env)
    Path(log_path).write_text(proc.stdout, encoding='utf-8')
    return proc.returncode


def phase_ninja_dry(build, ninja_dir):
    ninja = str(Path(ninja_dir) / 'ninja.exe')
    proc = subprocess.run([ninja, '-n', '-d', 'explain', 'pikmin_pc'], cwd=str(build), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', timeout=300)
    return proc.returncode, proc.stdout

def phase_fixture(native, build, output, expected_head, guard_dir, log_path):
    from scripts import build_pikmin2_fixture as builder
    native, build, output = Path(native), Path(build), Path(output)
    fixture = (native / FIXTURE_REL).resolve()
    if not fixture.is_file():
        raise ValueError('Missing fixture TU: ' + str(fixture))
    guard = resolve_guard(guard_dir)
    env = dict(os.environ)
    env['PATH'] = 'C:/msys64/mingw64/bin;' + env.get('PATH', '')
    env['CPLUS_INCLUDE_PATH'] = str(guard.parent) + os.pathsep + env.get('CPLUS_INCLUDE_PATH', '')
    old = dict(os.environ)
    try:
        os.environ.clear()
        os.environ.update(env)
        stamp = 'fixture-' + str(time.time_ns())
        record = builder.build_fixture(build, native, fixture, output / stamp, expected_head)
    finally:
        os.environ.clear()
        os.environ.update(old)
    if record.get('status') != 'built':
        raise RuntimeError('Fixture build rejected: ' + str(record.get('error')))
    exe = output / stamp / 'fixture.exe'
    Path(log_path).write_text(json.dumps({'status': record['status'], 'exe_sha256': sha256(exe), 'provenance': str(output / stamp / 'provenance.json')}, indent=2) + chr(10), encoding='utf-8')
    return 0


def phase_guardcheck(exe, compiler, guard_dir, log_path):
    code, text = run_exe(exe)
    verdict = interpret_exit(code, text)
    if verdict['verdict'] != 'pass':
        raise RuntimeError('Live self-test failed')

    with tempfile.TemporaryDirectory(prefix='p2guardneg') as tmp:
        negative = build_negative(compiler, guard_dir, tmp)
        ncode, ntext = run_exe(negative)
    nverdict = interpret_exit(ncode, ntext)
    if nverdict['verdict'] != 'blocked':
        raise RuntimeError('Negative guard path failed')

    if 'PASS' in ntext:
        raise RuntimeError('Negative path emitted PASS')
    Path(log_path).write_text('self_test: exit=' + str(code) + ' ' + verdict['detail'] + ' / negative: exit=' + str(ncode) + ' ' + nverdict['detail'] + chr(10), encoding='utf-8')
    return 0


def phase_run(exe, log_path):
    code, text = run_exe(exe)
    verdict = interpret_exit(code, text)
    Path(log_path).write_text(text, encoding='utf-8')
    if verdict['verdict'] != 'pass':
        raise RuntimeError('Chain run failed: ' + verdict['detail'])
    return 0, text

def main(argv=None):
    parser = argparse.ArgumentParser(description='P2 challenge boot fixture leased build and run')
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-native-head', default=None)
    parser.add_argument('--guard-dir', default=None)
    parser.add_argument('--ninja-dir', default=None)
    parser.add_argument('--exe', type=Path, default=None)
    parser.add_argument('phases', nargs='+', choices=('configure', 'build', 'fixture', 'guardcheck', 'run', 'all'))
    args = parser.parse_args(argv)
    ninja_dir = args.ninja_dir or toolchain()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    order = ('configure', 'build', 'fixture', 'guardcheck', 'run') if 'all' in args.phases else args.phases
    exe = args.exe
    for phase in order:
        if phase == 'configure':
            code = phase_configure(args.native, args.build, ninja_dir, out / 'configure.log')
        elif phase == 'build':
            code = phase_build(args.build, out / 'build.log', ninja_dir)
            if code == 0:
                code, dry = phase_ninja_dry(args.build, ninja_dir)
                (out / 'ninja-dry.log').write_text(dry, encoding='utf-8')
                if dry.strip() != 'ninja: no work to do.':
                    code = 1

        elif phase == 'fixture':
            head = args.expected_native_head
            if head is None:
                head = subprocess.check_output(['git', '-C', str(args.native), 'rev-parse', 'HEAD'], text=True).strip()
            code = phase_fixture(args.native, args.build, out, head, args.guard_dir, out / 'fixture.json')
            if code == 0 and exe is None:
                rec = json.loads((out / 'fixture.json').read_text(encoding='utf-8'))
                out2 = Path(rec['provenance']).parent
                exe = out2 / 'fixture.exe'
        elif phase == 'guardcheck':
            if exe is None:
                raise SystemExit('guardcheck needs --exe or a prior fixture phase')
            compiler = Path('C:/msys64/mingw64/bin/g++.exe')
            guard = resolve_guard(args.guard_dir)
            code = phase_guardcheck(exe, compiler, guard.parent, out / 'guardcheck.log')
        elif phase == 'run':
            if exe is None:
                raise SystemExit('run needs --exe or a prior fixture phase')
            code, _ = phase_run(exe, out / 'run.log')
        if code:
            raise SystemExit('Phase failed')

    print(json.dumps({'status': 'ok', 'output': str(out.resolve()), 'exe': str(exe) if exe else None}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
