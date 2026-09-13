"""Private beetle arena runtime probe: placement/load gates only.

The beetle family has no native registration (pc_p2_kogane does not exist;
flagged for the native track on #219), so this probe stages the batch-2 arena
with a private instrumented RoomApp and verifies ONLY:
  - exact spawn of the four roster generator IDs at the expected birth XYZ
    (beetle rows spawn as the template's P1 placement-vehicle type; beetle
    identity is NOT claimed),
  - the P1 control actor alive at the end,
  - installed artifact hashes readable from the run directory.
Flip/drop, Fart gas, forced escape and cave relocation remain BLOCKED gates.
"""
import argparse, hashlib, json, os, re, subprocess
from pathlib import Path
from scripts import build_pikmin2_fixture as builder
from experimental.pikmin2_kogane_arena import prepare
from experimental.pikmin2_kochappy_arena_fixture import instrument_tutorial

APP = r'''class RoomApp : public PlugPikiApp {
 int observed=0,frames=0;
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<15000,"beetle startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
 ++observed;
 if(observed==1){
  std::ifstream input("kogane-positions.txt");unsigned id;float x,y,z;int count=0;
  while(input>>id>>x>>y>>z){
   Teki* actor=nullptr;int matches=0;Iterator iter(tekiMgr);CI_LOOP(iter){Teki* a=static_cast<Teki*>(*iter);if(a->mGenerator&&a->mGenerator->_70==id){actor=a;++matches;}}
   require(matches==1,"beetle roster identity");
   Vector3f birth=actor->mPersonality->mPosition,gen=actor->mGenerator->getPos();
   require(std::fabs(birth.x-x)<.02&&std::fabs(birth.y-y)<.02&&std::fabs(birth.z-z)<.02,"beetle birth XYZ");
   require(std::fabs(gen.x-x)<.02&&std::fabs(gen.y-y)<.02&&std::fabs(gen.z-z)<.02,"beetle generator XYZ");
   std::printf("P2_KOGANE_BIRTH id=%u type=%d x=%.3f y=%.3f z=%.3f\n",id,actor->mTekiType,birth.x,birth.y,birth.z);++count;}
  require(count==4,"beetle roster missing");}
 if(observed==300){
  int alive=0;Iterator iter(tekiMgr);CI_LOOP(iter){Teki* a=static_cast<Teki*>(*iter);if(a->mGenerator&&a->mGenerator->_70>=219001&&a->mGenerator->_70<=219004&&a->isAlive())++alive;}
  require(alive==4,"beetle arena actors died");
  std::puts("PASS P2_KOGANE_RUNTIME births4 alive4 behavior=unregistered");std::fflush(stdout);std::_Exit(0);}
 std::fflush(stdout);return result;
}};
'''


def instrument(source, app=APP):
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    return ('#include <fstream>\n#include "Generator.h"\n#include "TekiPersonality.h"\n'
            + source[:start] + app + source[end:])


def build(native, build_dir, output, head, resume=False, app=None):
    native = native.resolve()
    build_dir = build_dir.resolve()
    output = output.resolve()
    room = output / 'room.cpp'
    source = instrument((native / 'tools/preview_p2_room.cpp').read_text(), app or APP)
    if resume:
        if (output / 'instrumentation.json').exists() or room.read_text() != source:
            raise ValueError('Cannot resume completed or changed fixture')
        record = json.loads((output / 'baseline/provenance.json').read_text())
        if record.get('status') != 'built' or record.get('expected_native_head') != head \
                or builder.git_state(native) != record['observed_source']:
            raise ValueError('Baseline no longer matches source')
        for key in ('inputs', 'fixture_inputs', 'configuration_inputs'):
            builder.check_snapshot(record[key])
    else:
        output.mkdir(parents=True, exist_ok=False)
        room.write_text(source)
        record = builder.build_fixture(build_dir, native, room, output / 'baseline', head)
    compile_cmd = list(record['commands'][-2])
    compile_cmd[builder.option_index(compile_cmd, '-o')] = str(output / 'room.obj')
    compile_cmd[builder.option_index(compile_cmd, '-MF')] = str(output / 'room.d')
    link = list(record['commands'][-1])
    targets = [i for i, a in enumerate(link) if a.endswith('\\fixture.obj') or a.endswith('/fixture.obj')]
    if len(targets) != 1:
        raise ValueError('Expected one private room object')
    link[targets[0]] = str(output / 'room.obj')
    link[builder.option_index(link, '-o')] = str(output / 'fixture.exe')
    link = [('-Wl,--out-implib,' + str(output / 'fixture.dll.a')) if a.startswith('-Wl,--out-implib,') else a for a in link]
    tutorial = native / 'src/plugPikiColin/newPikiGame.cpp'
    tutorial_private = output / 'tutorial.cpp'
    tutorial_private.write_text(instrument_tutorial(tutorial.read_text()))
    tutorial_compile = [str(tutorial_private) if a == str(room) else a for a in compile_cmd]
    tutorial_compile[builder.option_index(tutorial_compile, '-o')] = str(output / 'tutorial.obj')
    tutorial_compile[builder.option_index(tutorial_compile, '-MF')] = str(output / 'tutorial.d')
    targets = [i for i, a in enumerate(link) if a.endswith('-libpikmin_legacy.a')]
    if len(targets) != 1:
        raise ValueError('Expected one private legacy archive')
    # The original tutorial translation unit lives in the archive. Supplying its
    # complete replacement first prevents the linker extracting that member.
    link.insert(targets[0], str(output / 'tutorial.obj'))
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''))
    audit = dict(original_fixture=builder.snapshot([native / 'tools/preview_p2_room.cpp', tutorial]),
                 instrumented=builder.snapshot([room, tutorial_private]),
                 commands=[compile_cmd, tutorial_compile, link], freshness_checks=[])
    for name, command in [('room-compile', compile_cmd), ('tutorial-compile', tutorial_compile), ('room-link', link)]:
        code, text = builder.run(command, build_dir, env)
        (output / (name + '.log')).write_text(text)
        if code:
            raise RuntimeError(name + ' failed')
    builder.require_fresh(Path(record['toolchain']['ninja']['path']), build_dir, audit['freshness_checks'])
    builder.check_snapshot(record['inputs'])
    builder.check_snapshot(record['fixture_inputs'])
    builder.check_snapshot(record['configuration_inputs'])
    if builder.git_state(native) != record['observed_source']:
        raise RuntimeError('Native changed during private replacement')
    audit['artifacts'] = builder.snapshot([output / 'fixture.exe', output / 'room.obj'])
    audit['status'] = 'built'
    (output / 'instrumentation.json').write_text(json.dumps(audit, indent=2) + '\n')


def validate(text, code):
    births = re.findall(r'P2_KOGANE_BIRTH id=(\d+) type=(\d+) x=(-?\d+\.\d+) y=(-?\d+\.\d+) z=(-?\d+\.\d+)', text)
    checks = dict(completion=code == 0 and 'PASS P2_KOGANE_RUNTIME ' in text,
                  births=[int(b[0]) for b in births] == [219001, 219002, 219003, 219004],
                  one_type_per_row=len({b[1] for b in births[:3]}) >= 1)
    return dict(passed=all(checks.values()), checks=checks, births=births,
                unmeasured=['beetle identity (template placement vehicle only)',
                            'flip/drop cycle', 'Fart gas', 'forced escape', 'cave relocation', 'reload'],
                blocked_gates='no pc_p2_kogane native registration; flagged on #219 for the native track')


def run(assets, bank, output, exe, sidecar=None, validator=None):
    stage = prepare(assets, bank, output / 'stages')
    manifest = json.loads((stage / 'arena.json').read_text())
    (stage / 'kogane-positions.txt').write_bytes(
        ''.join(f"{a['generator']} " + ' '.join(map(str, a['expected_xyz'])) + '\n'
                for a in manifest['actors']).encode())
    arena_files = [stage / 'arena.json', stage / 'kogane-positions.txt',
                   stage / 'p2-kogane-actors.txt', stage / 'kogane-install.json']
    if sidecar is not None:
        (stage / 'p2-kogane-native.txt').write_text(sidecar)
        arena_files.append(stage / 'p2-kogane-native.txt')
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''), SDL_AUDIODRIVER='dummy')
    with (stage / 'native.log').open('w') as log:
        try:
            code = subprocess.run([str(exe.resolve()), '--experimental-pikmin2-room'],
                                  cwd=stage, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180).returncode
        except subprocess.TimeoutExpired:
            code = 'timeout'
    evidence = (validator or validate)((stage / 'native.log').read_text(errors='replace'), code)
    evidence.update(exit_code=code, executable=builder.snapshot([exe]),
                    arena=builder.snapshot(arena_files))
    (stage / 'runtime-evidence.json').write_text(json.dumps(evidence, indent=2))
    print(stage, flush=True)
    print(json.dumps(evidence), flush=True)


BINDING_IDS = {219001: 9, 219002: 10, 219003: 11, 219004: -1}


def validate_binding(text, code):
    """Validate a native binding-check log (root #228 BindingCheck.exe output).

    Verifies the typed source-ID mapping (9/10/11 for the three beetle actors,
    -1/control for 219004), exact birth XYZ against the arena roster, a native
    draw invocation and the PASS marker. P1 host AI remains; no source-FSM,
    drop or gas claim is made here.
    """
    ids = {int(i): (int(s), int(c)) for i, s, c in
           re.findall(r'P2_KOGANE_ID id=(\d+) source_id=(-?\d+) control=(\d)', text)}
    births = {int(m[0]): (float(m[2]), float(m[3]), float(m[4])) for m in
              re.findall(r'P2_KOGANE_BIRTH id=(\d+) type=(\d+) x=(-?\d+\.\d+) y=(-?\d+\.\d+) z=(-?\d+\.\d+)', text)}
    from experimental.pikmin2_kogane_arena import IDS, POSITIONS
    expected = dict(zip(IDS, POSITIONS))
    checks = dict(
        completion=code == 0 and 'PASS P2_KOGANE_RUNTIME ' in text,
        typed_mapping={i: ids.get(i, (None,))[0] for i in BINDING_IDS} ==
                      {i: s for i, s in BINDING_IDS.items()},
        control_flag=ids.get(219004, (None, None))[1] == 1 and
                     all(ids.get(i, (None, 1))[1] == 0 for i in (219001, 219002, 219003)),
        exact_xyz=all(births.get(i) == tuple(p) for i, p in expected.items()),
        draw='P2_KOGANE_DRAW corpse=0' in text,
        host_ai_disclaimed='behavior=P1_visual_binding_source_FSM_pending' in text)
    return dict(passed=all(checks.values()), checks=checks,
                typed={str(k): v for k, v in sorted(ids.items())},
                births={str(k): list(v) for k, v in sorted(births.items())},
                unmeasured=['source FSM', 'flips/drops/gas', 'material/texture fidelity', 'manager reset/reentry'],
                scope='Native source-ID registration and visual binding; P1 host AI retained')


def verify_fixed_run(stage, install_receipt=None):
    """Host-side verification of a fixed binding run bundle (Check.cmd directory).

    Re-hashes every file listed in fixed-manifest.json, requires the recorded
    evidence to have passed, and — when given this lane's install receipt —
    proves the binding consumed the lane's installed configs unchanged.
    """
    stage = Path(stage)
    manifest = json.loads((stage / 'fixed-manifest.json').read_text())
    if manifest.get('schema') != 1:
        raise ValueError('Unsupported fixed manifest schema')
    mismatched = [name for name, digest in manifest.get('files', {}).items()
                  if not (stage / name).is_file()
                  or hashlib.sha256((stage / name).read_bytes()).hexdigest() != digest]
    evidence = manifest.get('evidence', {})
    checks = dict(files_intact=not mismatched,
                  evidence_passed=evidence.get('passed') is True,
                  command_recorded=bool(manifest.get('command')) and bool(manifest.get('native_head')))
    result = dict(passed=all(checks.values()), checks=checks, mismatched=mismatched,
                  native_head=manifest.get('native_head'))
    if install_receipt is not None:
        receipt = json.loads(Path(install_receipt).read_text())
        lane = dict(profile=receipt['profile_config_sha256'], bank=receipt['bank_config_sha256'],
                    actors=receipt['actors_config_sha256'])
        bound = dict(profile=manifest['files'].get('p2-kogane-profile.txt'),
                     bank=manifest['files'].get('p2-kogane-bank.txt'),
                     actors=manifest['files'].get('p2-kogane-actors.txt'))
        result['lane_configs_consumed_unchanged'] = lane == bound
        result['passed'] = result['passed'] and result['lane_configs_consumed_unchanged']
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    r = sub.add_parser('run')
    for n in ('native', 'build-dir', 'output'):
        b.add_argument('--' + n, type=Path, required=True)
    b.add_argument('--head', required=True)
    b.add_argument('--resume', action='store_true')
    for n in ('assets', 'bank', 'output', 'exe'):
        r.add_argument('--' + n, type=Path, required=True)
    a = p.parse_args()
    if a.command == 'build':
        build(a.native, a.build_dir, a.output, a.head, a.resume)
    else:
        run(a.assets, a.bank, a.output, a.exe)
