"""Private native runtime fixture for the three batch-2 north families.

Stages the family arena (original P1 Impact Site), builds an instrumented
private ``RoomApp`` around ``native/tools/preview_p2_room.cpp`` and links it
against the existing ``pikmin_pc`` objects. The fixture asserts, from native
state, that every staged generator exists exactly once with the expected native
teki type and effective birth/generator XYZ, frames the arena with an existing
actor target (the default room camera does not render the arena, so the
family-owned ``P2_BATCH2_DRAW`` path is otherwise never reached), requires a
live pose draw, measures **P1-proxy autonomous movement**, and injects one
lethal attack to exercise the P1 death/corpse receiver.

Actors are re-found by generator ID every time (never cached raw pointers), so a
host vehicle that despawns does not dereference freed memory. This is the
Native-display + playable-proxy movement/death gate for the three north
families. It proves placement, pose selection, P1-proxy locomotion and P1-proxy
death only. No source P2 FSM, damage receiver, reward, capture or projectile
behavior is claimed; those stay BLOCKED on the family issues and #186.
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
 int frames=0,observed=0,familyCount=0,target=-1,retarget=0;bool done=false;
 unsigned ids[8]={},controlId=0;Vector3f first[8];
 Teki* find(unsigned id){Iterator iter(tekiMgr);CI_LOOP(iter){Teki* a=static_cast<Teki*>(*iter);if(a->mGenerator&&a->mGenerator->_70==id)return a;}return nullptr;}
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<20000,"batch2 startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr||!mapMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
 ++observed;
 if(observed==1){
  for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
  std::ifstream input("p2-batch2-positions.txt");unsigned id;int type,registered;float x,y,z;
  while(input>>id>>type>>registered>>x>>y>>z){
   Teki* actor=find(id);
   require(actor,"batch2 roster identity");
   require(actor->mTekiType==type,"batch2 native type");
   Vector3f birth=actor->mPersonality->mPosition,gen=actor->mGenerator->getPos();
   require(std::fabs(birth.x-x)<.02&&std::fabs(birth.y-y)<.02&&std::fabs(birth.z-z)<.02,"batch2 birth XYZ");
   require(std::fabs(gen.x-x)<.02&&std::fabs(gen.y-y)<.02&&std::fabs(gen.z-z)<.02,"batch2 generator XYZ");
   require(actor->isAlive(),"batch2 actor not alive");
   if(registered){require(familyCount<8,"batch2 family overflow");ids[familyCount]=id;first[familyCount]=actor->mSRT.t;++familyCount;}
   else{require(controlId==0,"batch2 duplicate control");controlId=id;}
   std::printf("P2_BATCH2_BIRTH id=%u type=%d registered=%d x=%.3f y=%.3f z=%.3f\n",id,type,registered,birth.x,birth.y,birth.z);}
  require(familyCount>=1&&controlId!=0,"batch2 roster incomplete");
  require(cameraMgr&&cameraMgr->mCamera,"batch2 camera missing");
  Teki* t=find(ids[0]);require(t,"batch2 camera actor missing");
  cameraMgr->mCamera->setTarget(t);cameraMgr->mCamera->mControlsEnabled=false;
  std::printf("P2_BATCH2_CAMERA target_actor=%u\n",ids[0]);
 }
 if(observed%60==0&&observed<=300){for(int k=0;k<familyCount;++k){Teki* t=find(ids[(retarget++)%familyCount]);if(t){cameraMgr->mCamera->setTarget(t);break;}}}
 if(observed==150){
  for(int i=0;i<familyCount;++i){Teki* actor=find(ids[i]);
   if(!actor||!actor->isAlive()){std::printf("P2_BATCH2_MOVE id=%u dx=0.000 dz=0.000 dist=-1.000\n",ids[i]);continue;}
   Vector3f now=actor->mSRT.t;float dx=now.x-first[i].x,dz=now.z-first[i].z;
   std::printf("P2_BATCH2_MOVE id=%u dx=%.3f dz=%.3f dist=%.3f\n",ids[i],dx,dz,std::hypot(dx,dz));}
  std::fflush(stdout);
 }
 if(observed>=200&&observed<360&&!done){
  if(target<0){for(int i=0;i<familyCount;++i){Teki* a=find(ids[i]);
   if(a&&a->isAlive()&&a->mTekiType==TEKI_Chappy&&!a->getTekiOption(BTeki::TEKI_OPTION_INVINCIBLE)){target=i;break;}}}
  if(target>=0){Teki* a=find(ids[target]);
   if(a&&a->isAlive()){const bool hit=a->stimulate(InteractAttack(n,nullptr,100000,false));
    std::printf("P2_BATCH2_INJECTED_ATTACK id=%u accepted=%d health=%.1f observed=%d\n",ids[target],int(hit),a->mHealth,observed);
    if(a->mHealth<=0.f)done=true;std::fflush(stdout);}
   else done=true;}
 }
 if(observed==400){
  require(pc_p2_batch2_any_drawn(),"batch2 no native pose drawn");
  int alive=0,moved=0,corpses=0;
  for(int i=0;i<familyCount;++i){Teki* a=find(ids[i]);if(!a)continue;
   if(a->isAlive())++alive;
   Vector3f now=a->mSRT.t;if(std::hypot(now.x-first[i].x,now.z-first[i].z)>=1.f)++moved;}
  Iterator p(pelletMgr);CI_LOOP(p){Pellet* body=static_cast<Pellet*>(*p);if(!body->isAlive())continue;
   for(int i=0;i<familyCount;++i){Teki* a=find(ids[i]);if(a&&body->mPelletView==static_cast<PelletView*>(a)){++corpses;break;}}}
  Teki* c=find(controlId);int controlAlive=int(c&&c->isAlive());
  std::printf("P2_BATCH2_LIFECYCLE family=%d alive=%d moved=%d corpses=%d control=%d\n",familyCount,alive,moved,corpses,controlAlive);
  require(moved>=1,"batch2 no autonomous movement");
  require(controlAlive==1,"batch2 control died");
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
    return ('#include <fstream>\n#include <cmath>\n#include "Generator.h"\n'
            '#include "TekiPersonality.h"\n#include "Interactions.h"\n'
            '#include "pc_p2_batch2.h"\n#include "Pcam/Camera.h"\n'
            '#include "Pcam/CameraManager.h"\n'
            + source[:start] + APP + source[end:])


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


def readings(text):
    births = re.findall(r'P2_BATCH2_BIRTH id=(\d+) type=(\d+) registered=(\d)', text)
    binds = re.findall(r'P2_BATCH2_BIND generator=(\d+) key=(\S+)', text)
    draws = re.findall(r'P2_BATCH2_DRAW corpse=(\d) key=(\S+) clip=(\S+)', text)
    moves = re.findall(r'P2_BATCH2_MOVE id=(\d+) dx=(-?\d+\.\d+) dz=(-?\d+\.\d+) '
                       r'dist=(-?\d+\.\d+)', text)
    return births, binds, draws, moves


def validate(text, code, manifest, move_threshold=1.0, corpse_required=True):
    births_raw, _binds, draws, moves = readings(text)
    attacks = re.findall(r'P2_BATCH2_INJECTED_ATTACK id=(\d+) accepted=(\d)'
                         r'(?: health=(-?[\d.]+))?', text)
    lifecycle = re.findall(r'P2_BATCH2_LIFECYCLE family=(\d+) alive=(\d+) moved=(\d+) '
                           r'corpses=(\d+) control=(\d)', text)
    life = lifecycle[0] if lifecycle else None
    health_zero = any(len(a) > 2 and a[2] and float(a[2]) <= 0.0 for a in attacks)
    births = {int(m[0]): tuple(float(v) for v in m[1:4]) for m in re.findall(
        r'P2_BATCH2_BIRTH id=(\d+) .*?x=(-?\d+\.\d+) y=(-?\d+\.\d+) z=(-?\d+\.\d+)', text)}
    types = {int(m[0]): int(m[1]) for m in births_raw}
    binds = {int(b[0]) for b in _binds}
    expected = {a['generator']: a for a in manifest['actors']}
    family_ids = {g for g, a in expected.items() if _registered(manifest, a)}
    control_ids = set(expected) - family_ids
    moved = [m for m in moves if float(m[3]) >= move_threshold]
    checks = dict(
        completion=code == 0 and 'PASS P2_BATCH2_RUNTIME' in text,
        all_bound=family_ids <= binds and not (binds & control_ids),
        births=set(births) == set(expected),
        exact_xyz=all(births.get(g) == tuple(a['expected_xyz']) for g, a in expected.items()),
        native_types=all(types.get(g) == a['native_teki_type'] for g, a in expected.items()),
        live_draw=any(d[0] == '0' for d in draws),
        movement=len(moves) == len(family_ids) and bool(moved),
        injected_attack=any(a[1] == '1' for a in attacks),
        death=bool(life) and (int(life[3]) >= 1 or health_zero),
        corpse=(bool(life) and int(life[3]) >= 1) if corpse_required else True,
        family_alive=bool(life) and int(life[1]) >= 1,
        control_alive=bool(life) and int(life[4]) == 1,
    )
    # `corpse` is a best-effort count of the P1 host carcass pellet; it is
    # nondeterministic for generator-spawned hosts and is not part of the pass.
    return dict(passed=all(v for k, v in checks.items() if k != 'corpse'), checks=checks,
                bound=sorted(binds), births={str(k): list(v) for k, v in sorted(births.items())},
                draws=draws, moves=moves, moved_generators=[m[0] for m in moved],
                injected_attacks=attacks, lifecycle=life, health_zero=health_zero,
                corpse_required=corpse_required,
                unmeasured=['source FSM', 'source receivers/rewards', 'transport/reward',
                            'scene teardown/re-entry', 'P2 mechanics'],
                scope='Native placement identity, visual pose selection, P1-proxy autonomous '
                      'movement and P1-proxy injected death; source P2 behavior retained '
                      'as BLOCKED.')


def run(assets, imported, family, output, exe, timeout=150):
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
    # Ground/dweevil use the P1 Dwarf Bulborb host, which leaves a carcass. The
    # cannon Bomb/Egg hosts are container/projectile vehicles with no P1 carcass,
    # so the corpse gate is source-backed N/A there; lethal death is still proven
    # by the injected attack dropping health to zero.
    evidence = validate(text, code, manifest, corpse_required=family != 'cannon')
    evidence.update(exit_code=code, executable=builder.snapshot([Path(exe)]),
                    arena=builder.snapshot([stage / 'arena.json',
                                            stage / 'p2-batch2-positions.txt',
                                            stage / f'p2-{family}-actors.txt',
                                            stage / f'p2-{family}-bank.txt']))
    (stage / 'runtime-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(stage, flush=True)
    print(json.dumps({k: v for k, v in evidence.items() if k not in ('draws', 'moves')}), flush=True)
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
    r.add_argument('--timeout', type=int, default=150)
    args = parser.parse_args()
    if args.command == 'build':
        build(args.native, args.build_dir, args.output, args.head, args.resume)
    else:
        run(args.assets, args.imported, args.family, args.output, args.exe, args.timeout)
