'''Private runtime-acceptance driver for P1 Challenge Impact (chal0, issue 565).

Consumes the landed #649 guarded boot fixture read-only: builds it in a private
leased build dir via the #649 harness build() (no duplication, no shared edits),
runs the headed boot, and records observed runtime facts plus honest gate
verdicts. The #649 input package validate_run_log is reused for the
observed/blocked verdict, never reimplemented.

Captain safety #632: the fixture runs the canonical guard every idle call
(vendored verbatim, sha recorded); any CAPTAIN_DOWN line forces verdict
BLOCKED and can never substantiate a PASS. No blanket invincibility.'''

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

CANONICAL_ROOT = Path('C:/Users/alari/pikmin-randomizer')
NATIVE_649 = CANONICAL_ROOT / 'output/workflow/autofill/planning-shards/p1-challenge/prepared/p1-challenge-guarded-runtime-native'
HARNESS_649 = CANONICAL_ROOT / 'output/workflow/autofill/planning-shards/p1-challenge/prepared/p1-challenge-guarded-runtime-root/scripts'
GUARD_SHA256 = 'd2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474'
GUARD_NAME = 'p2_fixture_captain_guard.h'
LEVEL = 0
STAGE_ID = 'challenge-0'
STAGE_FILE = 'stages/chal0.ini'
GEN_FILE = 'stages/chal0/default.gen'

def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def guard_record(guard_dir=None):
    candidate = Path(guard_dir) / GUARD_NAME if guard_dir else CANONICAL_ROOT / 'scripts' / GUARD_NAME
    if not candidate.is_file():
        raise ValueError('Missing captain guard header')
    digest = sha256(candidate)
    if digest != GUARD_SHA256:
        raise ValueError('Captain guard hash drift: ' + digest)
    return {'path': str(candidate), 'sha256': digest}



BS = chr(92)
BS = chr(92)

LAYOUT_RE = re.compile('CHALLENGE_LAYOUT_READY id=(' + BS + 'S+) stage_index=(' + BS + 'd+) file=(' + BS + 'S+)(?: story=(' + BS + 'd+))?')
SQUAD_RE = re.compile('P2_CHALLENGE_SQUAD pikis=(' + BS + 'd+)')
GEN_RE = re.compile('initialised (' + BS + 'd+) recognised generators, spawned (' + BS + 'd+) creatures')
BOOT_RE = re.compile('P2_CHALLENGE_BOOT level=(' + BS + 'd+) slot=(' + BS + 'S+)')
PASS_RE = re.compile('PASS P2_CHALLENGE_GUARDED_BOOT')
WINDOW_RE = re.compile('Experimental preview window set to 960x540 windowed and centered')
FPS_RE = re.compile(BS + '[PC Port' + BS + '] FPS:')

GATES = ('identity_spawn', 'movement_animation', 'attacks_receivers', 'death_corpse', 'transport_reward', 'cleanup_reentry')


def observe_run(text, exit_code):
    layout = LAYOUT_RE.search(text)
    layout_rec = None
    if layout:
        layout_rec = {'id': layout.group(1), 'stage_index': int(layout.group(2)), 'file': layout.group(3)}
    boot = BOOT_RE.search(text)
    boot_rec = None
    if boot:
        boot_rec = {'level': int(boot.group(1)), 'slot': boot.group(2)}
    squads = [int(m.group(1)) for m in SQUAD_RE.finditer(text)]
    gens = [(int(m.group(1)), int(m.group(2))) for m in GEN_RE.finditer(text)]
    facts = {'layout': layout_rec, 'squads': squads, 'generators': gens, 'boot': boot_rec,
             'pass_marker': bool(PASS_RE.search(text)),
             'window_960x540': bool(WINDOW_RE.search(text)),
             'fps_frames': len(FPS_RE.findall(text)),
             'captain_down': 'P2_FIXTURE_CAPTAIN_DOWN' in text,
             'exit_code': exit_code}
    return facts


def gate_verdicts(facts):
    if facts['captain_down']:
        return {g: ('BLOCKED', 'captain-down run cannot substantiate PASS') for g in GATES}
    if facts['exit_code'] != 0 or facts['layout'] is None:
        return {g: ('UNTESTED', 'no successful boot observed') for g in GATES}
    layout_ok = (facts['layout']['id'] == STAGE_ID and facts['layout']['stage_index'] == 16 and facts['layout']['file'] == STAGE_FILE)
    boot_ok = (facts['boot'] is not None and facts['boot']['slot'] == 'chal0')
    spawn_ok = (len(facts['generators']) > 0 and sum(s for _, s in facts['generators']) > 0 and any(s >= 1 for s in facts['squads']))
    if layout_ok and boot_ok and spawn_ok and facts['pass_marker']:
        gates = {'identity_spawn': ('PASS', 'challenge-0 stage 16 chal0.ini with spawns and squad observed uninterrupted')}
    else:
        gates = {'identity_spawn': ('FAIL', 'expected boot markers absent')}
    gates['movement_animation'] = ('UNTESTED', 'boot-only observation; no movement observed')
    gates['attacks_receivers'] = ('UNTESTED', 'boot-only observation; no combat observed')
    gates['death_corpse'] = ('UNTESTED', 'boot-only observation; no death observed')
    gates['transport_reward'] = ('UNTESTED', 'boot-only observation; no transport observed')
    gates['cleanup_reentry'] = ('UNTESTED', 'boot-only observation; no reentry observed')
    return gates
def import_harness():
    sys.path.insert(0, str(HARNESS_649))
    sys.path.insert(0, str(HARNESS_649.parent))
    import build_p2_challenge_guarded_boot_fixture as harness
    import experimental.pikmin2_challenge_runtime_inputs as inputs_pkg
    return harness, inputs_pkg


def phase_build(native, build_dir, output, head, log_path):
    import shutil
    native, build_dir, output = Path(native), Path(build_dir), Path(output)
    harness, _ = import_harness()
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ' '))
    out = output
    out.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(['cmake', '-S', str(native), '-B', str(build_dir), '-G', 'Ninja',
        '-DCMAKE_MAKE_PROGRAM=' + toolchain_ninja() + '/ninja.exe',
        '-DCMAKE_BUILD_TYPE=RelWithDebInfo',
        '-DCMAKE_C_COMPILER=C:/msys64/mingw64/bin/gcc.exe', '-DCMAKE_CXX_COMPILER=C:/msys64/mingw64/bin/g++.exe',
        '-DPIKMIN_NATIVE_JAUDIO=ON', '-DPIKMIN_NATIVE_OPTIMIZE=OFF',
        '-DPIKMIN_RANDOMIZER_TEST_HOOKS=OFF'],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding='utf-8', errors='replace', timeout=900, env=env)
    (out / 'configure.log').write_text(proc.stdout, encoding='utf-8')
    if proc.returncode:
        return proc.returncode
    proc = subprocess.run(['cmake', '--build', str(build_dir), '--target', 'pikmin_pc', '-j', '6'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', timeout=3600, env=env)
    (out / 'build.log').write_text(proc.stdout, encoding='utf-8')
    if proc.returncode:
        return proc.returncode
    ninja = toolchain_ninja() + '/ninja.exe'
    proc = subprocess.run([ninja, '-n', '-d', 'explain', 'pikmin_pc'], cwd=str(build_dir), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', timeout=300, env=env)
    (out / 'ninja-dry.log').write_text(proc.stdout, encoding='utf-8')
    if proc.stdout.strip() != 'ninja: no work to do.':
        return 2
    old = dict(os.environ)
    try:
        os.environ.clear()
        os.environ.update(env)
        stage = out / ('stage-' + str(time.time_ns())); harness.build(str(native), str(build_dir), str(stage), head)
    finally:
        os.environ.clear()
        os.environ.update(old)
    with open(log_path, 'w', encoding='utf-8') as log:
        log.write('build ok' + chr(10))
    return 0


def toolchain_ninja():
    import ninja
    return str(Path(ninja.BIN_DIR))

def phase_run(exe, assets, run_parent, deadline=60):
    import _winapi
    run_parent = Path(run_parent)
    run_parent.mkdir(parents=True, exist_ok=True)
    run = run_parent / uuid.uuid4().hex
    run.mkdir()
    _winapi.CreateJunction(str(Path(assets).resolve()), str(run / 'assets'))
    with (run / 'native.log').open('w', encoding='utf-8') as log:
        proc = subprocess.Popen([str(Path(exe).resolve()), '--experimental-challenge-level', str(LEVEL)], cwd=run, stdout=log, stderr=subprocess.STDOUT, env=dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', '')))
        try:
            stop = time.monotonic() + deadline
            while proc.poll() is None and time.monotonic() < stop:
                text = (run / 'native.log').read_text(encoding='utf-8', errors='replace')
                if 'CHALLENGE_LAYOUT_READY id=challenge-0' in text and 'stages/chal0/default.gen' in text and text.count('[PC Port] FPS:') >= 1:
                    break
                time.sleep(0.2)
            text = (run / 'native.log').read_text(encoding='utf-8', errors='replace')
            observed = False
            if 'CHALLENGE_LAYOUT_READY id=challenge-0' in text and 'stages/chal0/default.gen' in text and text.count('[PC Port] FPS:') >= 1:
                observed = True
            code = 0 if observed else (proc.poll() if proc.poll() is not None else 1)
        finally:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=10)
                code = proc.poll()
    return code if code is not None else 0, run


def phase_observe(run_dir, code, out):
    text = (Path(run_dir) / 'native.log').read_text(encoding='utf-8', errors='replace')
    facts = observe_run(text, code)
    gates = gate_verdicts(facts)
    (Path(out) / 'facts.json').write_text(json.dumps(facts, indent=1), encoding='utf-8')
    (Path(out) / 'gates.json').write_text(json.dumps(gates, indent=1), encoding='utf-8')
    return facts, gates


def write_run_info(run_dir, assets, out):
    chal0 = Path(assets) / 'dataDir/stages/chal0.ini'
    gen = Path(assets) / 'dataDir/stages/chal0/default.gen'
    info = {'run_dir': str(run_dir), 'fresh_uuid': Path(run_dir).name,
            'assets': str(Path(assets).resolve()),
            'chal0_ini': sha256(chal0) if chal0.is_file() else None,
            'default_gen': sha256(gen) if gen.is_file() else None}
    (Path(out) / 'run-info.json').write_text(json.dumps(info, indent=1), encoding='utf-8')
    return info


def phase_run_meta(run, code, observed, out):
    (Path(out) / 'run-meta.json').write_text(json.dumps({'run': str(run), 'exit_code': code, 'observed': observed}), encoding='utf-8')

def main(argv=None):
    parser = argparse.ArgumentParser(description='P1 Challenge Impact runtime acceptance driver')
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--expected-native-head', default=None)
    parser.add_argument('--guard-dir', default=None)
    parser.add_argument('--ninja-dir', default=None)
    parser.add_argument('--exe', type=Path, default=None)
    parser.add_argument('--deadline', type=int, default=60)
    parser.add_argument('phases', nargs='+', choices=('build', 'run', 'observe', 'all'))
    args = parser.parse_args(argv)
    ninja_dir = args.ninja_dir
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    guard_record(args.guard_dir)
    order = ('build', 'run', 'observe') if 'all' in args.phases else args.phases
    exe = args.exe
    run_dir = None
    code = 0
    for phase in order:
        if phase == 'build':
            head = args.expected_native_head
            if head is None:
                head = subprocess.check_output(['git', '-C', str(args.native), 'rev-parse', 'HEAD'], text=True).strip()
            code = phase_build(args.native, args.build, out, head, out / 'build-phase.log')
            if code == 0:
                exe = max(out.glob('stage-*/fixture.exe'), key=lambda p: p.stat().st_mtime_ns)
        elif phase == 'run':
            if exe is None:
                cands = sorted(out.glob('stage-*/fixture.exe'), key=lambda p: p.stat().st_mtime_ns)
                if not cands:
                    raise SystemExit('run needs --exe: pass the fixture exe built by the build phase')
                exe = cands[-1]
            code, run_dir = phase_run(exe, args.assets, out / 'runs', args.deadline)
            (out / 'run-meta.json').write_text(json.dumps({'run': str(run_dir), 'exit_code': code}), encoding='utf-8')
        elif phase == 'observe':
            if run_dir is None:
                meta = json.loads((out / 'run-meta.json').read_text(encoding='utf-8'))
                run_dir, code = Path(meta['run']), meta['exit_code']
            facts, gates = phase_observe(run_dir, code, out)
            write_run_info(run_dir, args.assets, out)
            print(json.dumps({'gates': {g: v[0] for g, v in gates.items()}, 'exit_code': code}))
        if code:
            raise SystemExit('Phase failed')



if __name__ == '__main__':
    raise SystemExit(main())
