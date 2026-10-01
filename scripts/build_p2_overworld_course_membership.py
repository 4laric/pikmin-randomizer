'''Leased build/run harness for the #802 overworld-course membership lane.

Builds pikmin_pc in a private leased build dir, compiles the module TU
(pc_port/pc_p2_overworld_course.cpp) plus the membership probe and the #738
smoke fixture with reference flags, links both fixture exes against the
private pikmin_pc graph plus the module object, runs the probe and the
headed smoke boot, and classifies. Never edits native/CMakeLists.txt
(serialized behind #755); the maintained one-line landing is specified in
docs/PIKMIN2_OVERWORLD_COURSE_CMAKELISTS_MEMBERSHIP.md. No ADMIT.
'''

import argparse
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

MODULE_REL = Path('pc_port/pc_p2_overworld_course.cpp')
SMOKE_REL = Path('tools/p2_overworld_boot_smoke_fixture.cpp')
PROBE_REL = Path('tools/p2_overworld_course_membership_fixture.cpp')


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
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding='utf-8', errors='replace',
                          timeout=900, env=env)
    Path(log_path).write_text(proc.stdout, encoding='utf-8')
    return proc.returncode


def phase_build(build, log_path):
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ' '))
    proc = subprocess.run(['cmake', '--build', str(build), '--target', 'pikmin_pc', '-j', '6'],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding='utf-8', errors='replace',
                          timeout=3600, env=env)
    Path(log_path).write_text(proc.stdout, encoding='utf-8')
    return proc.returncode


def phase_ninja_dry(build, ninja_dir):
    ninja = str(Path(ninja_dir) / 'ninja.exe')
    proc = subprocess.run([ninja, '-n', '-d', 'explain', 'pikmin_pc'], cwd=str(build),
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding='utf-8', errors='replace', timeout=300)
    return proc.returncode, proc.stdout


def ref_command(build):
    commands = json.loads((Path(build) / 'compile_commands.json').read_text(encoding='utf-8'))
    for end_name in ('tools/p2_kurage_runtime.cpp', 'pc_port/pc_main.cpp'):
        for entry in commands:
            if entry['file'].replace('\\', '/').endswith(end_name):
                return entry['command'], entry['file']
    raise RuntimeError('no reference TU')


def compile_tu(cmd, ref_file, src, obj, build, env, log_path):
    text = cmd.replace(ref_file.replace('/', '\\'), str(src))
    text, n = re.subn(r'-o\s+\S+', lambda m: '-o ' + str(obj), text, count=1)
    assert n == 1
    proc = subprocess.run(['cmd', '/c', text], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding='utf-8', errors='replace',
                          cwd=str(build), env=env)
    Path(log_path).write_text(proc.stdout, encoding='utf-8')
    if proc.returncode:
        raise RuntimeError('compile failed: ' + str(src))


def link_objects(build):
    ninja_text = (Path(build) / 'build.ninja').read_text(encoding='utf-8', errors='replace')
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
    return ([t for t in edge.split()[2:] if t.endswith('.obj') and 'LINKER__' not in t],
            link_libs)


def phase_fixtures(native, build, output, expected_head):
    native, build, output = Path(native), Path(build), Path(output)
    head = subprocess.check_output(['git', '-C', str(native), 'rev-parse', 'HEAD'],
                                   text=True).strip()
    if head != expected_head:
        raise ValueError('Native HEAD %s differs from expected %s' % (head, expected_head))
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ' '))
    cmd, ref_file = ref_command(build)
    module_src = (native / MODULE_REL).resolve()
    smoke_src = (native / SMOKE_REL).resolve()
    probe_src = (native / PROBE_REL).resolve()
    for path in (module_src, smoke_src, probe_src):
        if not path.is_file():
            raise ValueError('Missing TU ' + str(path))
    module_obj = str((build / 'p2_overworld_course_module.obj').resolve())
    smoke_obj = str((build / 'p2_overworld_boot_smoke.obj').resolve())
    probe_obj = str((build / 'p2_overworld_course_membership.obj').resolve())
    compile_tu(cmd, ref_file, module_src, module_obj, build, env, output / 'module-compile.log')
    compile_tu(cmd, ref_file, smoke_src, smoke_obj, build, env, output / 'smoke-compile.log')
    compile_tu(cmd, ref_file, probe_src, probe_obj, build, env, output / 'probe-compile.log')
    objects, link_libs = link_objects(build)
    fixed = []
    for o in objects:
        if o.replace('\\', '/').endswith('pc_port/pc_main.cpp.obj'):
            continue
        fixed.append(o)
    for name, obj in (('smoke', smoke_obj), ('probe', probe_obj)):
        rsp = build / ('p2_overworld_course_%s.rsp' % name)
        rsp.write_text('\n'.join(fixed + [obj.replace('\\', '/'), module_obj.replace('\\', '/')]),
                       encoding='utf-8')
        exe = str((build / ('p2_overworld_course_%s_fixture.exe' % name)).resolve())
        proc = subprocess.run(['g++', '@' + str(rsp), '-mconsole', '-o', exe] + link_libs.split(),
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, encoding='utf-8', errors='replace',
                              cwd=str(build), env=env)
        (output / ('%s-link.log' % name)).write_text(proc.stdout, encoding='utf-8')
        if proc.returncode:
            raise RuntimeError('link failed: ' + name)
    record = {'head': head, 'module_sha256': sha256(module_obj),
              'smoke_exe_sha256': sha256(build / 'p2_overworld_course_smoke_fixture.exe'),
              'probe_exe_sha256': sha256(build / 'p2_overworld_course_probe_fixture.exe')}
    (output / 'fixture-record.json').write_text(json.dumps(record, indent=1), encoding='utf-8')
    (output / 'smoke-exe.txt').write_text(
        str((build / 'p2_overworld_course_smoke_fixture.exe').resolve()), encoding='utf-8')
    (output / 'probe-exe.txt').write_text(
        str((build / 'p2_overworld_course_probe_fixture.exe').resolve()), encoding='utf-8')


def phase_probe_run(exe, output):
    output = Path(output)
    proc = subprocess.run([str(Path(exe).resolve()), '--experimental-overworld-course', 'forest'],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding='utf-8', errors='replace', timeout=120)
    (output / 'probe-run.log').write_text(
        'exit=%d\n%s' % (proc.returncode, proc.stdout), encoding='utf-8')
    return proc.returncode


def phase_smoke_run(exe, staged, output, deadline=300):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    run = output / 'runs' / uuid.uuid4().hex
    run.mkdir(parents=True)
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ' '),
               SDL_AUDIODRIVER='dummy', PIKMIN_RANDOMIZER_TEST_BACKGROUND='1')
    try:
        proc = subprocess.run(
            [str(Path(exe).resolve()), '--experimental-overworld-course', 'forest',
             '--experimental-pikmin2-room'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace',
            cwd=str(Path(staged).resolve()), env=env, timeout=deadline)
        code, text = proc.returncode, proc.stdout
    except subprocess.TimeoutExpired as exc:
        code, text = 1, (exc.stdout or '') + '\nRUN_TIMEOUT\n'
    (run / 'native.log').write_text(text, encoding='utf-8')
    return code, run


def main(argv=None):
    parser = argparse.ArgumentParser(description='Overworld-course membership leased build and run')
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--expected-native-head', default=None)
    parser.add_argument('--ninja-dir', type=Path, required=True)
    parser.add_argument('--deadline', type=int, default=300)
    parser.add_argument('phases', nargs='+',
                        choices=('configure', 'build', 'fixtures', 'probe', 'smoke', 'classify', 'all'))
    args = parser.parse_args(argv)
    if 'C:/msys64/mingw64/bin' not in os.environ.get('PATH', ' '):
        os.environ['PATH'] = 'C:/msys64/mingw64/bin;' + os.environ.get('PATH', ' ')
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from experimental.pikmin2_overworld_course_membership import classify_log
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    order = ('configure', 'build', 'fixtures', 'probe', 'smoke', 'classify') \
        if 'all' in args.phases else args.phases
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
        elif phase == 'fixtures':
            head = args.expected_native_head
            if head is None:
                head = subprocess.check_output(['git', '-C', str(args.native), 'rev-parse', 'HEAD'],
                                               text=True).strip()
            phase_fixtures(args.native, args.build, out, head)
            code = 0
        elif phase == 'probe':
            exe = Path((out / 'probe-exe.txt').read_text(encoding='utf-8').strip())
            code = phase_probe_run(exe, out)
        elif phase == 'smoke':
            exe = Path((out / 'smoke-exe.txt').read_text(encoding='utf-8').strip())
            code, _ = phase_smoke_run(exe, args.assets, out, args.deadline)
            (out / 'run-meta.json').write_text(
                json.dumps({'exit_code': code,
                            'run': str(sorted((out / 'runs').iterdir(),
                                              key=lambda p: p.stat().st_mtime_ns)[-1])}),
                encoding='utf-8')
        elif phase == 'classify':
            texts, codes = [], []
            probe_log = out / 'probe-run.log'
            texts.append(probe_log.read_text(encoding='utf-8', errors='replace'))
            codes.append(int(probe_log.read_text(encoding='utf-8').splitlines()[0].split('=')[1]))
            meta = json.loads((out / 'run-meta.json').read_text(encoding='utf-8'))
            run_log = Path(meta['run']) / 'native.log'
            texts.append(run_log.read_text(encoding='utf-8', errors='replace'))
            codes.append(meta['exit_code'])
            verdicts = [classify_log(t, c) for t, c in zip(texts, codes)]
            (out / 'verdict.json').write_text(json.dumps(verdicts, indent=1), encoding='utf-8')
            print(json.dumps(verdicts))
            code = 0 if (verdicts[0]['verdict'] == 'linked'
                         and verdicts[1]['verdict'] == 'boot-pass') else 1
        if code:
            raise SystemExit('Phase failed')
    print(json.dumps({'status': 'ok'}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
