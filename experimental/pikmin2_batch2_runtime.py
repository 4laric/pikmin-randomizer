"""Private native spawn fixture for the three batch-2 north families.

Stages the family arena (original P1 Impact Site), builds an instrumented
private ``RoomApp`` around ``native/tools/preview_p2_room.cpp`` and links it
against the existing ``pikmin_pc`` objects. The fixture asserts, from native
state, that every staged generator exists exactly once with the expected native
teki type and effective birth/generator XYZ, then drives the camera onto the
family actors so ``pc_p2_batch2_draw`` runs, and requires that a live pose was
drawn before exiting.

It proves placement and pose selection only. No source P2 FSM, damage receiver,
reward, capture or projectile behavior is claimed; those stay BLOCKED on the
family issues and #186.
"""
import argparse
import importlib
import json
import os
import re
import subprocess
from pathlib import Path

from scripts import build_pikmin2_fixture as builder
from experimental.pikmin2_kochappy_arena_fixture import instrument_tutorial

FAMILIES = {
    'ground': 'experimental.pikmin2_ground_inverts_arena',
    'dweevil': 'experimental.pikmin2_dweevil_arena',
    'cannon': 'experimental.pikmin2_cannon_projectile_arena',
}

APP = r'''class RoomApp : public PlugPikiApp {
 int frames=0,observed=0,familyCount=0;Teki* family[8]={};Teki* control=nullptr;
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<15000,"batch2 startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
 ++observed;
 if(observed==1){
  for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
  std::ifstream input("p2-batch2-positions.txt");unsigned id;int type,registered;float x,y,z;
  while(input>>id>>type>>registered>>x>>y>>z){
   Teki* actor=nullptr;int matches=0;Iterator iter(tekiMgr);CI_LOOP(iter){Teki* a=static_cast<Teki*>(*iter);if(a->mGenerator&&a->mGenerator->_70==id){actor=a;++matches;}}
   require(matches==1,"batch2 roster identity");
   require(actor->mTekiType==type,"batch2 native type");
   Vector3f birth=actor->mPersonality->mPosition,gen=actor->mGenerator->getPos();
   require(std::fabs(birth.x-x)<.02&&std::fabs(birth.y-y)<.02&&std::fabs(birth.z-z)<.02,"batch2 birth XYZ");
   require(std::fabs(gen.x-x)<.02&&std::fabs(gen.y-y)<.02&&std::fabs(gen.z-z)<.02,"batch2 generator XYZ");
   require(actor->isAlive(),"batch2 actor not alive");
   if(registered){require(familyCount<8,"batch2 family overflow");family[familyCount++]=actor;}
   else{require(control==nullptr,"batch2 duplicate control");control=actor;}
   std::printf("P2_BATCH2_BIRTH id=%u type=%d registered=%d x=%.3f y=%.3f z=%.3f\n",id,type,registered,birth.x,birth.y,birth.z);}
  require(familyCount>=1&&control!=nullptr,"batch2 roster incomplete");
  require(cameraMgr&&cameraMgr->mCamera,"batch2 camera missing");
  cameraMgr->mCamera->setTarget(family[0]);
 }
 if(observed%60==0&&observed<=300)cameraMgr->mCamera->setTarget(family[(observed/60)%familyCount]);
 if(observed==120)capture("batch2-pose-a.ppm");
 if(observed==240)capture("batch2-pose-b.ppm");
 if(observed==360){
  require(pc_p2_batch2_any_drawn(),"batch2 no native pose drawn");
  int alive=0;for(int i=0;i<familyCount;++i)if(family[i]->isAlive())++alive;
  std::printf("P2_BATCH2_ALIVE family=%d/%d control=%d\n",alive,familyCount,int(control->isAlive()));
  require(control->isAlive(),"batch2 control died");
  std::puts("PASS P2_BATCH2_RUNTIME");std::fflush(stdout);std::_Exit(0);
 }
 std::fflush(stdout);return result;
}};
'''


def family_module(name):
    return importlib.import_module(FAMILIES[name])


def instrument(source):
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    if 'P2_BATCH2_BIRTH' in source:
        raise ValueError('Already instrumented')
    return ('#include <fstream>\n#include "Generator.h"\n#include "TekiPersonality.h"\n'
            '#include "pc_p2_batch2.h"\n#include "Pcam/Camera.h"\n'
            '#include "Pcam/CameraManager.h"\n' + source[:start] + APP + source[end:])


def build(native, build_dir, output, head, resume=False):
    native = native.resolve()
    build_dir = build_dir.resolve()
    output = output.resolve()
    room = output / 'room.cpp'
    source = instrument((native / 'tools/preview_p2_room.cpp').read_text())
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


def _registered(manifest, actor):
    return 0 if actor['species'] == manifest['control'] else 1


def write_positions(stage, manifest):
    (stage / 'p2-batch2-positions.txt').write_bytes(
        ''.join(f"{a['generator']} {a['native_teki_type']} {_registered(manifest, a)} "
                + ' '.join(str(v) for v in a['expected_xyz']) + '\n'
                for a in manifest['actors']).encode('ascii'))


def validate(text, code, manifest):
    binds = {int(g) for g in re.findall(r'P2_BATCH2_BIND generator=(\d+)', text)}
    births = {int(m[0]): tuple(float(v) for v in m[1:4]) for m in re.findall(
        r'P2_BATCH2_BIRTH id=(\d+) .*?x=(-?\d+\.\d+) y=(-?\d+\.\d+) z=(-?\d+\.\d+)', text)}
    types = {int(m[0]): int(m[1]) for m in re.findall(
        r'P2_BATCH2_BIRTH id=(\d+) type=(\d+)', text)}
    draws = re.findall(r'P2_BATCH2_DRAW corpse=(\d) key=(\S+) clip=(\S+)', text)
    expected = {a['generator']: a for a in manifest['actors']}
    family_ids = {g for g, a in expected.items() if _registered(manifest, a)}
    control_ids = set(expected) - family_ids
    checks = dict(
        completion=code == 0 and 'PASS P2_BATCH2_RUNTIME' in text,
        all_bound=family_ids <= binds and not (binds & control_ids),
        births=set(births) == set(expected),
        exact_xyz=all(births.get(g) == tuple(a['expected_xyz']) for g, a in expected.items()),
        native_types=all(types.get(g) == a['native_teki_type'] for g, a in expected.items()),
        live_draw=any(d[0] == '0' for d in draws),
    )
    return dict(passed=all(checks.values()), checks=checks,
                bound=sorted(binds), births={str(k): list(v) for k, v in sorted(births.items())},
                draws=draws,
                unmeasured=['source FSM', 'combat/receivers', 'death/corpse', 'transport/reward',
                            'reset/re-entry', 'P2 mechanics'],
                scope='Native placement identity and visual pose selection; P1 host AI retained.')


def run(assets, imported, family, output, exe, timeout=120):
    module = family_module(family)
    stage = module.prepare(assets, imported, output / 'stages')
    manifest = json.loads((stage / 'arena.json').read_text())
    write_positions(stage, manifest)
    build_bin = str(Path(exe).resolve().parent)
    env = dict(os.environ, PATH=build_bin + ';C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''),
               SDL_AUDIODRIVER='dummy')
    with (stage / 'native.log').open('w') as log:
        try:
            code = subprocess.run([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                                  cwd=stage, env=env, stdout=log, stderr=subprocess.STDOUT,
                                  timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            code = 'timeout'
    text = (stage / 'native.log').read_text(errors='replace')
    evidence = validate(text, code, manifest)
    evidence.update(exit_code=code, executable=builder.snapshot([Path(exe)]),
                    arena=builder.snapshot([stage / 'arena.json',
                                            stage / 'p2-batch2-positions.txt',
                                            stage / f'p2-{family}-actors.txt',
                                            stage / f'p2-{family}-bank.txt']))
    (stage / 'runtime-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(stage, flush=True)
    print(json.dumps({k: v for k, v in evidence.items() if k != 'draws'}), flush=True)
    return evidence


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    r = sub.add_parser('run')
    for name in ('native', 'build-dir', 'output'):
        b.add_argument('--' + name, type=Path, required=True)
    b.add_argument('--head', required=True)
    b.add_argument('--resume', action='store_true')
    r.add_argument('--family', choices=sorted(FAMILIES), required=True)
    for name in ('assets', 'imported', 'output', 'exe'):
        r.add_argument('--' + name, type=Path, required=True)
    r.add_argument('--timeout', type=int, default=120)
    args = parser.parse_args()
    if args.command == 'build':
        build(args.native, args.build_dir, args.output, args.head, args.resume)
    else:
        run(args.assets, args.imported, args.family, args.output, args.exe, args.timeout)
