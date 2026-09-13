"""Batch-1 native-display + playable-proxy runtime probe.

Families: aquatic (#374), flying (#375), snagret (#376). Private instrumented
RoomApp over ``native/tools/preview_p2_room.cpp`` which verifies each arena
generator's exact birth/generator XYZ, frames the arena with a camera target
(the default room camera does not render the arena, so the family-owned
``P2_BATCH3_DRAW`` path is otherwise never reached) and measures autonomous
movement of the P1-proxy actors across frames.

Visual-only / P1-proxy: the actors are ordinary P1 behaviour with the batch-1
visual bank overlaid. No source P2 FSM, combat, receivers or lifecycle is
claimed.
"""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from scripts import build_pikmin2_fixture as builder
from experimental.pikmin2_kochappy_arena_fixture import instrument_tutorial

APP = r'''class DisplayCameraTarget : public Creature {
public:DisplayCameraTarget():Creature(nullptr){mHealth=1;}
 void refresh(Graphics&) override{} void doKill() override{}
};
class RoomApp : public PlugPikiApp {
 int frames=0,ready=0;std::vector<unsigned> ids;std::vector<Vector3f> first;
 Teki* find(unsigned id){Iterator iter(tekiMgr);CI_LOOP(iter){Teki* a=static_cast<Teki*>(*iter);if(a->mGenerator&&a->mGenerator->_70==id)return a;}return nullptr;}
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<20000,"batch1 startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr||!mapMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;++ready;
 if(ready==1){
  std::ifstream input("batch1-positions.txt");unsigned id;std::string species;float x,y,z;float cx=0,cy=0,cz=0;
  while(input>>id>>species>>x>>y>>z){
   Teki* actor=find(id);require(actor,"batch1 roster identity");
   Vector3f birth=actor->mPersonality->mPosition,gen=actor->mGenerator->getPos();
   require(std::fabs(birth.x-x)<.02&&std::fabs(birth.y-y)<.02&&std::fabs(birth.z-z)<.02,"batch1 birth XYZ");
   require(std::fabs(gen.x-x)<.02&&std::fabs(gen.y-y)<.02&&std::fabs(gen.z-z)<.02,"batch1 generator XYZ");
   std::printf("P2_BATCH1_BIRTH id=%u type=%d species=%s x=%.3f y=%.3f z=%.3f\n",id,actor->mTekiType,species.c_str(),birth.x,birth.y,birth.z);
   ids.push_back(id);first.push_back(birth);cx+=x;cy+=y;cz+=z;}
  require(!ids.empty(),"batch1 roster missing");
  const float count=float(ids.size());cx/=count;cy/=count;cz/=count;
  require(cameraMgr&&cameraMgr->mCamera,"batch1 camera missing");auto* target=new DisplayCameraTarget();target->mSRT.t=Vector3f(cx,cy+60.f,cz);auto* camera=cameraMgr->mCamera;camera->setTarget(target);camera->mControlsEnabled=false;
  PcamMotionInfo info=camera->mTargetMotionInfo;info.mDistance=1100.f;info.mFov=40;info.mAngle=35;info.mNaviWatchWeight=0;info.mWatchAdjustment=0;camera->startMotion(info);
  std::printf("P2_BATCH1_CAMERA target=%.3f,%.3f,%.3f distance=1100 fov=40 angle=35\n",target->mSRT.t.x,target->mSRT.t.y,target->mSRT.t.z);
 }
 if(ready==150){
  for(size_t i=0;i<ids.size();++i){
   Teki* actor=find(ids[i]);require(actor,"batch1 actor lost before movement check");
   Vector3f now=actor->mSRT.t;float dx=now.x-first[i].x,dz=now.z-first[i].z;float dist=std::hypot(dx,dz);
   std::printf("P2_BATCH1_MOVE id=%u dx=%.3f dz=%.3f dist=%.3f\n",ids[i],dx,dz,dist);}
 }
 if(ready>=180){std::puts("PASS P2_BATCH1_RUNTIME birth_bind_camera_framed_moved");std::fflush(stdout);std::_Exit(0);}
 std::fflush(stdout);return result;
}};
'''


def instrument(source):
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    includes = ('#include <fstream>\n#include <string>\n#include <vector>\n'
                '#include <cmath>\n#include "Generator.h"\n#include "TekiPersonality.h"\n'
                '#include "Pcam/Camera.h"\n#include "Pcam/CameraManager.h"\n')
    return includes + source[:start] + APP + source[end:]


def build(native, build_dir, output, head):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / 'tutorial-private.inc').write_text(
        instrument_tutorial((native / 'src/plugPikiColin/newPikiGame.cpp').read_text(encoding='utf-8')),
        encoding='utf-8')
    room = output / 'room.cpp'
    room.write_text(instrument((native / 'tools/preview_p2_room.cpp').read_text(encoding='utf-8'))
                    + '\n#include "tutorial-private.inc"\n', encoding='utf-8')
    return builder.build_fixture(build_dir, native, room, output / 'build', head)


def readings(text):
    births = re.findall(r'P2_BATCH1_BIRTH id=(\d+) type=(\d+) species=(\w+) '
                        r'x=(-?\d+\.\d+) y=(-?\d+\.\d+) z=(-?\d+\.\d+)', text)
    draws = re.findall(r'P2_BATCH3_DRAW corpse=(\d) key=([\w|]+) clip=(\w+)', text)
    binds = re.findall(r'P2_BATCH3_BIND generator=(\d+) key=([\w|]+) ', text)
    moves = re.findall(r'P2_BATCH1_MOVE id=(\d+) dx=(-?\d+\.\d+) dz=(-?\d+\.\d+) '
                       r'dist=(-?\d+\.\d+)', text)
    return births, draws, binds, moves


def run(stage, exe, output=None, move_threshold=1.0):
    stage = Path(stage).resolve()
    manifest = json.loads((stage / 'arena.json').read_text())
    rows = []
    expected = {}
    for actor in manifest['actors']:
        species = actor.get('species')
        xyz = actor.get('expected_xyz') or actor.get('birth_xyz') or actor.get('xyz')
        if not species or species.startswith('P1 ') or xyz is None:
            continue
        token = species[3:] if species.startswith('P2 ') else species
        rows.append('{} {} {}'.format(actor['generator'], token,
                                      ' '.join(map(str, xyz))))
        expected[str(actor['generator'])] = token
    (stage / 'batch1-positions.txt').write_text('\n'.join(rows) + '\n')
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''),
               SDL_AUDIODRIVER='dummy')
    log_path = stage / 'batch1-native.log'
    with log_path.open('w') as log:
        try:
            code = subprocess.run([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                                  cwd=stage, env=env, stdout=log, stderr=subprocess.STDOUT,
                                  timeout=180).returncode
        except subprocess.TimeoutExpired:
            code = 'timeout'
    text = log_path.read_text(errors='replace')
    births, draws, binds, moves = readings(text)
    moved = [m for m in moves if float(m[3]) >= move_threshold]
    checks = dict(
        completion=code == 0 and 'PASS P2_BATCH1_RUNTIME ' in text,
        births=len(births) == len(expected)
        and {b[0] for b in births} == set(expected),
        bind_lines=len(binds) >= len(expected),
        draw_path=bool(draws),
        movement=len(moves) == len(expected) and bool(moved),
    )
    evidence = dict(passed=all(checks.values()), checks=checks, exit_code=code,
                    births=births, binds=binds, draws=draws, moves=moves,
                    moved_generators=[m[0] for m in moved],
                    scene=manifest.get('scene'), total_actors=len(expected),
                    scope='Native display + P1-proxy autonomous movement. '
                          'No source P2 FSM/combat/lifecycle claim.')
    (stage / 'batch1-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(stage)
    print(json.dumps(evidence))
    return evidence


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    for key in ('native', 'build-dir', 'output'):
        b.add_argument('--' + key, type=Path, required=True)
    b.add_argument('--head', required=True)
    r = sub.add_parser('run')
    for key in ('stage', 'exe'):
        r.add_argument('--' + key, type=Path, required=True)
    r.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.command == 'build':
        build(args.native.resolve(), args.build_dir.resolve(), args.output, args.head)
    else:
        run(args.stage, args.exe, args.output)
