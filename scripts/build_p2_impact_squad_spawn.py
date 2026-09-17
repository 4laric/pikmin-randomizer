'''Leased build/run harness for the #745 squad-spawn repair (#745).

Builds native/tools/p2_challenge_guarded_boot_fixture.cpp (with the #745
gateDiag repair) against a private leased pikmin_pc build via the maintained
replacement-main builder, runs the headed chal0 boot, and classifies the
stall with the repair adapter. No shared edits, no ADMIT.'''

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

CANONICAL_ROOT = Path('C:/Users/alari/pikmin-randomizer')
FIXTURE_REL = Path('tools/p2_challenge_guarded_boot_fixture.cpp')

def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def phase_configure(native, build, ninja_dir, log_path):
    build = Path(build)
    build.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ' '))
    cmd = ['cmake', '-S', str(native), '-B', str(build), '-G', 'Ninja',
        '-DCMAKE_MAKE_PROGRAM=' + str(ninja_dir) + '/ninja.exe',
        '-DCMAKE_BUILD_TYPE=RelWithDebInfo',
        '-DCMAKE_C_COMPILER=C:/msys64/mingw64/bin/gcc.exe',
        '-DCMAKE_CXX_COMPILER=C:/msys64/mingw64/bin/g++.exe',
        '-DPIKMIN_NATIVE_JAUDIO=ON', '-DPIKMIN_NATIVE_OPTIMIZE=OFF',
        '-DPIKMIN_RANDOMIZER_TEST_HOOKS=OFF', '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON']
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', timeout=900, env=env)
    Path(log_path).write_text(proc.stdout, encoding='utf-8')
    return proc.returncode


def phase_build(build, log_path):
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ' '))
    proc = subprocess.run(['cmake', '--build', str(build), '--target', 'pikmin_pc', '-j', '6'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', timeout=3600, env=env)
    Path(log_path).write_text(proc.stdout, encoding='utf-8')
    return proc.returncode

def phase_ninja_dry(build, ninja_dir):
    ninja = str(Path(ninja_dir) / 'ninja.exe')
    proc = subprocess.run([ninja, '-n', '-d', 'explain', 'pikmin_pc'], cwd=str(build), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', timeout=300)
    return proc.returncode, proc.stdout


FIXTURE_BEGIN = '// MUSE-CHALLENGE-BOOT-INCLUDES-BEGIN'
FIXTURE_SPLIT = '// MUSE-CHALLENGE-BOOT-INCLUDES-END'
FIXTURE_APP = '// MUSE-CHALLENGE-BOOT-APP-BEGIN'
FIXTURE_END = '// MUSE-CHALLENGE-BOOT-APP-END'
ROOM_REQUIRE = 'require(pc_pikipelago_room_preview(),"requires --experimental-pikmin2-room");'
CHALLENGE_REQUIRE = ('require(pc_pikipelago_challenge_level()>=0 && !pc_pikipelago_room_preview(),'
                     '"requires --experimental-challenge-level 0-4");')
ROOM_ANCHOR = 'class RoomApp : public PlugPikiApp {'


def phase_fixture(native, build, output, expected_head, log_path):
    import glob
    import re
    native, build, output = Path(native), Path(build), Path(output)
    fixture = (native / FIXTURE_REL).resolve()
    if not fixture.is_file():
        raise ValueError('Missing fixture TU')
    head = subprocess.check_output(['git', '-C', str(native), 'rev-parse', 'HEAD'], text=True).strip()
    if head != expected_head:
        raise ValueError('Native HEAD %s differs from expected %s' % (head, expected_head))
    record = {'head': head, 'steps': {}}
    text = fixture.read_text(encoding='utf-8')
    includes = text.split(FIXTURE_BEGIN, 1)[1].split(FIXTURE_SPLIT, 1)[0]
    app = text.split(FIXTURE_APP, 1)[1].split(FIXTURE_END, 1)[0]
    assert ROOM_ANCHOR in app
    assert 'P2_CHALLENGE_GATE_DIAG' in app and 'P2_CHALLENGE_PARK_ALIVE' in app
    room_src = (native / 'tools' / 'preview_p2_room.cpp').read_text(encoding='utf-8')
    start = room_src.index(ROOM_ANCHOR)
    end = room_src.index('int main(', start)
    room = (room_src[:start] + includes + app + room_src[end:]).replace(ROOM_REQUIRE, CHALLENGE_REQUIRE, 1)
    assert CHALLENGE_REQUIRE in room and ROOM_REQUIRE not in room
    room_path = (build / 'p2_impact_squad_spawn_room.cpp').resolve()
    room_path.write_text(room, encoding='utf-8', newline='')
    for inc in glob.glob(str(native / 'tools' / 'preview_p2_*.inc')):
        (build / Path(inc).name).write_bytes(Path(inc).read_bytes())
    record['steps']['splice'] = {'room': str(room_path), 'sha256': sha256(room_path)}
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ' '))
    probe_src = str(native / 'tools' / 'p2_impact_squad_spawn_probe.cpp')
    probe_exe = str(build / 'p2_impact_squad_spawn_probe.exe')
    proc = subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                           '-o', probe_exe, probe_src],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding='utf-8', errors='replace', cwd=str(build), env=env)
    (output / 'probe-compile.log').write_text(proc.stdout, encoding='utf-8')
    if proc.returncode:
        raise RuntimeError('Probe compile failed')
    proc = subprocess.run([probe_exe], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding='utf-8', errors='replace', env=env)
    (output / 'probe-run.log').write_text('exit=%d\n%s' % (proc.returncode, proc.stdout), encoding='utf-8')
    if proc.returncode or 'PROBE_PASS' not in proc.stdout:
        raise RuntimeError('Probe contract failed')
    record['steps']['probe'] = {'exit': proc.returncode}
    commands = json.loads((build / 'compile_commands.json').read_text(encoding='utf-8'))
    ref_cmd = ref_file = None
    for end_name in ('tools/p2_kurage_runtime.cpp', 'pc_port/pc_main.cpp'):
        for entry in commands:
            if entry['file'].replace('\\', '/').endswith(end_name):
                ref_cmd, ref_file = entry['command'], entry['file']
                break
        if ref_cmd:
            break
    assert ref_cmd, 'no reference TU'
    room_obj = str(build / 'p2_impact_squad_spawn_room.obj')
    cmd = ref_cmd.replace(ref_file.replace('/', '\\'), str(room_path))
    cmd, n = re.subn(r'-o\s+\S+', lambda m: '-o ' + room_obj, cmd, count=1)
    assert n == 1
    proc = subprocess.run(['cmd', '/c', cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding='utf-8', errors='replace', cwd=str(build), env=env)
    (output / 'room-compile.log').write_text(proc.stdout, encoding='utf-8')
    if proc.returncode:
        raise RuntimeError('Spliced room compile failed')
    record['steps']['room_compile'] = {'exit': 0}
    ninja_text = (build / 'build.ninja').read_text(encoding='utf-8', errors='replace')
    edge = link_libs = None
    lines = ninja_text.splitlines()
    for i, line in enumerate(lines):
        if 'CXX_EXECUTABLE_LINKER__pikmin_pc' in line and line.startswith('build '):
            edge = line.replace('C$:/', 'C:/')
            for j in range(i + 1, min(i + 20, len(lines))):
                if lines[j].startswith('  LINK_LIBRARIES = '):
                    link_libs = lines[j].split('=', 1)[1].strip()
                    break
            break
    assert edge and link_libs
    objects = [t for t in edge.split()[2:] if t.endswith('.obj') and 'LINKER__' not in t]
    swapped = False
    for i, o in enumerate(objects):
        if o.replace('\\', '/').endswith('pc_port/pc_main.cpp.obj'):
            objects[i] = room_obj.replace('\\', '/')
            swapped = True
    assert swapped
    rsp = build / 'p2_impact_squad_spawn.rsp'
    rsp.write_text('\n'.join(objects), encoding='utf-8')
    exe = str(build / 'p2_impact_squad_spawn_fixture.exe')
    proc = subprocess.run(['g++', '@' + str(rsp), '-mconsole', '-o', exe] + link_libs.split(),
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding='utf-8', errors='replace', cwd=str(build), env=env)
    (output / 'fixture-link.log').write_text(proc.stdout, encoding='utf-8')
    if proc.returncode:
        raise RuntimeError('Fixture link failed')
    record['steps']['fixture_link'] = {'exe': exe, 'objects': len(objects), 'exe_sha256': sha256(exe)}
    (output / 'fixture-record.json').write_text(json.dumps(record, indent=1), encoding='utf-8')
    (output / 'fixture-exe.txt').write_text(exe, encoding='utf-8')

def phase_run(exe, staged, output, deadline=300):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    run = output / 'runs' / uuid.uuid4().hex
    run.mkdir(parents=True)
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ' '),
               SDL_AUDIODRIVER='dummy', PIKMIN_RANDOMIZER_TEST_BACKGROUND='1')
    try:
        proc = subprocess.run([str(Path(exe).resolve()), '--experimental-challenge-level', '0'],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, encoding='utf-8', errors='replace',
                              cwd=str(Path(staged).resolve()), env=env, timeout=deadline)
        code, text = proc.returncode, proc.stdout
    except subprocess.TimeoutExpired as exc:
        code, text = 1, (exc.stdout or '') + '\nRUN_TIMEOUT\n'
    (run / 'native.log').write_text(text, encoding='utf-8')
    return code, run


def main(argv=None):
    parser = argparse.ArgumentParser(description='Squad-spawn repair leased build and run')
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--expected-native-head', default=None)
    parser.add_argument('--ninja-dir', type=Path, required=True)
    parser.add_argument('--exe', type=Path, default=None)
    parser.add_argument('--deadline', type=int, default=300)
    parser.add_argument('phases', nargs='+', choices=('configure', 'build', 'fixture', 'run', 'classify', 'all'))
    args = parser.parse_args(argv)
    if 'C:/msys64/mingw64/bin' not in os.environ.get('PATH', ' '):
        os.environ['PATH'] = 'C:/msys64/mingw64/bin;' + os.environ.get('PATH', ' ')
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from experimental.pikmin2_impact_squad_spawn_repair import classify_log
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    order = ('configure', 'build', 'fixture', 'run', 'classify') if 'all' in args.phases else args.phases
    exe = args.exe
    run_dir = None
    code = 0
    for phase in order:
        if phase == 'configure':
            code = phase_configure(args.native, args.build, args.ninja_dir, out / 'configure.log')
        elif phase == 'build':
            code = phase_build(args.build, out / 'build.log')
            if code == 0:
                code, dry = phase_ninja_dry(args.build, args.ninja_dir)
                (out / 'ninja-dry.log').write_text(dry, encoding='utf-8')
                if dry.strip() != 'ninja: no work to do.':
                    code = 2
        elif phase == 'fixture':
            head = args.expected_native_head
            if head is None:
                head = subprocess.check_output(['git', '-C', str(args.native), 'rev-parse', 'HEAD'], text=True).strip()
            phase_fixture(args.native, args.build, out, head, out / 'fixture.log')
            code = 0
            exe = Path((out / 'fixture-exe.txt').read_text(encoding='utf-8').strip())
        elif phase == 'run':
            if exe is None:
                exe = Path((out / 'fixture-exe.txt').read_text(encoding='utf-8').strip())
            code, run_dir = phase_run(exe, args.assets, out, args.deadline)
            (out / 'run-meta.json').write_text(json.dumps({'run': str(run_dir), 'exit_code': code}), encoding='utf-8')
        elif phase == 'classify':
            if run_dir is None:
                meta = json.loads((out / 'run-meta.json').read_text(encoding='utf-8'))
                run_dir, code = Path(meta['run']), meta['exit_code']
            text = (Path(run_dir) / 'native.log').read_text(encoding='utf-8', errors='replace')
            verdict = classify_log(text, code)
            (out / 'verdict.json').write_text(json.dumps(verdict, indent=1), encoding='utf-8')
            print(json.dumps(verdict))
            code = 0 if verdict['verdict'] == 'spawned' else 1
        if code:
            raise SystemExit('Phase failed')
    print(json.dumps({'status': 'ok'}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
