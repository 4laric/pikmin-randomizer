"""Private leased build/run helper for the #711 ch_NARI_02tile stage-boot fixture.

Lane challenge-stage-boot-02tile-record-native (#711). Owns ONLY this file in
the root tree; the fixture TU it builds is native/tools/p2_challenge_stage_boot_fixture.cpp.

Steps: acquire/renew the private build lease through the canonical registry,
configure + build pikmin_pc (Ninja, C:/msys64/mingw64/bin on PATH), compile
and link the fixture through a rewritten Ninja response file (the maintained
pikmin2 fixture builder rejects @response files), then run the guarded fixture
for ch_NARI_01kusachi (expects PASS) and ch_NARI_02tile (expects the record
accepted with P2_CHALLENGE_STAGE_RESOLVED and a BLOCKED engine-table-row-pending
stop, never bad-record, never PASS). Stdlib only.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path('C:/Users/alari/pikmin-randomizer')
DEFAULT_BUILD = REPO / 'output/challenge-stage-boot-02tile-record-build'
GUARD = REPO / 'scripts/p2_fixture_captain_guard.h'


def sha256(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(args, cwd, env=None, timeout=3600):
    done = subprocess.run(args, cwd=cwd, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, encoding='utf-8',
                          errors='replace', timeout=timeout)
    return done.returncode, done.stdout


def parse_cache(build):
    cache = {}
    for line in (build / 'CMakeCache.txt').read_text(encoding='utf-8').splitlines():
        if line and not line.startswith(('#', '//')) and '=' in line:
            key, value = line.split('=', 1)
            cache[key.split(':')[0]] = value
    return cache


def configure(source, build, ninja):
    if (build / 'CMakeCache.txt').is_file():
        return 0, 'cache-present'
    build.mkdir(parents=True, exist_ok=True)
    return run(['cmake', '-S', str(source), '-B', str(build), '-G', 'Ninja',
                '-DCMAKE_MAKE_PROGRAM=' + str(ninja),
                '-DCMAKE_CXX_COMPILER=C:/msys64/mingw64/bin/g++.exe',
                '-DCMAKE_C_COMPILER=C:/msys64/mingw64/bin/gcc.exe',
                '-DCMAKE_BUILD_TYPE=Release'], REPO)


def build_fixture(source, build, output, scripts_root):
    sys.path.insert(0, str(scripts_root))
    import build_pikmin2_fixture as bf
    output.mkdir(parents=True, exist_ok=True)
    cache = parse_cache(build)
    ninja = bf.absolute(cache['CMAKE_MAKE_PROGRAM'], build)
    env = dict(os.environ)
    code, fresh = run([str(ninja), '-n', 'pikmin_pc'], build, env)
    if fresh.strip() != 'ninja: no work to do.':
        raise RuntimeError('pikmin_pc not fresh: ' + fresh.strip()[:120])
    code, text = run([str(ninja), '-t', 'commands', 'pikmin_pc'], build, env)
    (output / 'native-commands.txt').write_text(text, encoding='utf-8')
    fixture = source / 'tools/p2_challenge_stage_boot_fixture.cpp'
    main = (source / 'pc_port/pc_main.cpp').resolve()
    compile_args = None
    for line in text.splitlines():
        if ' -c ' not in line and ' -o ' not in line:
            continue
        try:
            parsed = bf.compiler_args(line)
        except bf.BuildRejected:
            continue
        if '-c' in parsed and bf.absolute(parsed[bf.option_index(parsed, '-c')], build) == main:
            compile_args = parsed
            break
    if compile_args is None:
        raise RuntimeError('pc_main compile line not found')
    compiler = Path(compile_args[0]).resolve()
    env['PATH'] = str(compiler.parent) + os.pathsep + os.environ.get('PATH', '')
    link_line = next((l for l in text.splitlines()
                      if ' -o ' in l and ' -c ' not in l and '.rsp' in l), None)
    if link_line is None:
        raise RuntimeError('response-file link line not found')
    wrapper = re.fullmatch(
        r'(?:"[^"]*[/\\]cmd\.exe"|\S*[/\\]cmd\.exe|cmd\.exe) /C "cd \. && (.*) && cd \."',
        link_line, re.IGNORECASE)
    core = wrapper.group(1) if wrapper else link_line
    link_tokens = core.split()
    rsp_token = next((t for t in link_tokens if t.startswith('@')), None)
    rsp_path = build / rsp_token[1:]
    if rsp_path.is_file():
        rsp_content = rsp_path.read_text(encoding='utf-8', errors='replace')
    else:
        rsp_rel = rsp_token[1:]
        ninja_lines = (build / 'build.ninja').read_text(encoding='utf-8', errors='replace').splitlines()
        anchor = next(i for i, l in enumerate(ninja_lines) if l.strip() == 'RSP_FILE = ' + rsp_rel)
        header = next(ninja_lines[i] for i in range(anchor, -1, -1) if ninja_lines[i].startswith('build '))
        objects = [t for t in header.split() if t.endswith('.obj')]
        begin = anchor
        while begin > 0 and ninja_lines[begin - 1].strip():
            begin -= 1
        end = anchor
        while end + 1 < len(ninja_lines) and ninja_lines[end + 1].strip():
            end += 1
        libs = ''
        for l in ninja_lines[begin:end + 1]:
            if l.strip().startswith('LINK_LIBRARIES = '):
                libs = l.strip().split('=', 1)[1].strip()
        rsp_content = '\n'.join(objects + ([libs] if libs else [])) + '\n'
    main_rel = 'CMakeFiles/pikmin_pc.dir/pc_port/pc_main.cpp.obj'
    if main_rel not in rsp_content:
        raise RuntimeError('pc_main object missing from response file')
    fixture_obj = output / 'fixture.obj'
    rsp_content = rsp_content.replace(main_rel, fixture_obj.as_posix())
    (output / 'fixture.rsp').write_text(rsp_content, encoding='utf-8')
    code, compile_log = run(bf.fixture_compile(compile_args, fixture, output, source), build, env)
    (output / 'compile.log').write_text(compile_log, encoding='utf-8')
    if code:
        raise RuntimeError('fixture compile failed; see compile.log')
    link = [token if token != rsp_token else '@' + str(output / 'fixture.rsp') for token in link_tokens]
    link[bf.option_index(link, '-o')] = str(output / 'fixture.exe')
    if '-Wl,--out-implib,' in ' '.join(link):
        link = [('-Wl,--out-implib,' + str(output / 'fixture.dll.a')) if t.startswith('-Wl,--out-implib,')
                else t for t in link]
    code, link_log = run(link, build, env)
    (output / 'link.log').write_text(link_log, encoding='utf-8')
    if code:
        raise RuntimeError('fixture link failed; see link.log')
    return {'exe': str(output / 'fixture.exe'), 'sha256': sha256(output / 'fixture.exe'),
            'size': (output / 'fixture.exe').stat().st_size}


def run_stage(source, exe, stage, baseline, run_dir, selector_root, landing_root, timeout=90):
    sys.path.insert(0, str(REPO / 'scripts'))
    sys.path.insert(0, str(selector_root))
    sys.path.insert(0, str(landing_root))
    import run_pikmin2_cave_fixture as cave
    import pikmin2_challenge_stage_select_boot as selector
    import pikmin2_challenge_02tile_stage_select_landing as landing
    directory = cave.prepare(baseline, run_dir)
    for name in ('p2-cave-entry.txt', 'p2-cave-generate.txt', 'p2-cave-runtime-inputs.json'):
        (directory / name).unlink(missing_ok=True)
    if stage == 'ch_NARI_02tile':
        record, _ = landing.select_stage_extended(stage, str(REPO))
        text = landing.render_boot_request_extended(record)
    else:
        record = selector.select_stage(stage, root=str(selector_root))
        text = selector.render_boot_request(record)
    sidecar = directory / 'p2-challenge-stage-select.txt'
    sidecar.write_text(text, encoding='utf-8')
    env = dict(os.environ)
    env['SDL_AUDIODRIVER'] = 'dummy'
    env['PATH'] = r'C:\msys64\mingw64\bin' + os.pathsep + env.get('PATH', '')
    argv = [str(exe), '--experimental-pikmin2-room', '--experimental-challenge-stage', stage]
    log = directory / 'native.log'
    proc = subprocess.Popen(argv, cwd=directory, env=env, stdout=log.open('wb'), stderr=subprocess.STDOUT)
    try:
        code = proc.wait(timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.kill()
        code = proc.wait(timeout=10)
    text = log.read_text(errors='replace')
    return {'stage': stage, 'exit_code': code, 'timed_out': timed_out,
            'sidecar_sha256': hashlib.sha256(sidecar.read_bytes()).hexdigest(),
            'log_sha256': hashlib.sha256(text.encode()).hexdigest(),
            'markers': {m: (m in text) for m in (
                'P2_CHALLENGE_STAGE_FLAG', 'P2_CHALLENGE_STAGE_SIDECAR', 'P2_CHALLENGE_STAGE_TABLE',
                'P2_CHALLENGE_STAGE_RESOLVED', 'P2_CHALLENGE_STAGE_ENGINE_ROW_PENDING',
                'P2_CHALLENGE_STAGE_BLOCKED', 'P2_CHALLENGE_STAGE_READY', 'PASS CHALLENGE_STAGE_BOOT',
                'P2_FIXTURE_CAPTAIN_DOWN', 'P2_CHALLENGE_STAGE_REFUSED')}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--build', type=Path, default=DEFAULT_BUILD)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline-run', type=Path, required=True)
    parser.add_argument('--selector-root', type=Path, required=True)
    parser.add_argument('--landing-root', type=Path, required=True)
    parser.add_argument('--scripts-root', type=Path, required=True)
    parser.add_argument('--skip-build', action='store_true')
    args = parser.parse_args()
    cache = parse_cache(args.build) if (args.build / 'CMakeCache.txt').is_file() else None
    ninja = cache['CMAKE_MAKE_PROGRAM'] if cache else str(Path(sys.executable).with_name('ninja.exe'))
    print('configure exit:', configure(args.source, args.build, ninja)[0])
    code, log = run(['cmake', '--build', str(args.build), '--target', 'pikmin_pc', '-j', '6'], REPO)
    (args.output / 'build-pikmin-pc.log').write_text(log, encoding='utf-8')
    print('pikmin_pc build exit:', code)
    if code:
        raise SystemExit('pikmin_pc build failed')
    artifacts = build_fixture(args.source, args.build, args.output / 'fixture-build', args.scripts_root)
    print('fixture:', artifacts)
    results = {}
    for stage in ('ch_NARI_01kusachi', 'ch_NARI_02tile'):
        run_dir = args.output / ('run-kusachi' if 'kusachi' in stage else 'run-02tile')
        if run_dir.exists():
            import shutil
            shutil.rmtree(run_dir)
        results[stage] = run_stage(args.source, Path(artifacts['exe']), stage, args.baseline_run,
                                   run_dir, args.selector_root, args.landing_root)
        print(stage, 'exit', results[stage]['exit_code'],
              {k: v for k, v in results[stage]['markers'].items() if v})
    payload = {'artifacts': artifacts, 'guard_sha256': sha256(GUARD), 'stages': results}
    (args.output / 'stage-runs.json').write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    ok = (results['ch_NARI_01kusachi']['exit_code'] == 0
          and results['ch_NARI_01kusachi']['markers']['P2_CHALLENGE_STAGE_READY']
          and results['ch_NARI_02tile']['exit_code'] == 3
          and results['ch_NARI_02tile']['markers']['P2_CHALLENGE_STAGE_RESOLVED']
          and not results['ch_NARI_02tile']['markers']['P2_CHALLENGE_STAGE_REFUSED'])
    print('RESULT:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
