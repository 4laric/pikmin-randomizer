"""#445 Lane 24 Empress Bulblax (Queen, enemy 30) natural lifecycle.

Proves, un-injected, the three remaining Queen arrows: (1) natural larva births
from the source 2.0 s birth timer with exactly-once accounting (`born=` counter),
(2) a natural Baby captain bite on a live captain (the larva walks within
BabySight 800 of the captain and bites), and (3) Queen death releasing/cleaning
all live larvae (the new family-local larva-pool cleanup; no injected health —
the King-style continuous latch damage drives the 5000 HP Queen to 0).

Staging is limited and labeled: the captain is repositioned near the Queen once
so a larva can reach it, and the 32-red squad is held away during the birth/bite
window then held in a ring around the Queen for combat (the same labeled re-pin
as the slice-1 King run; there is no health injection and no `p2-queen-inject.txt`).
"""
import argparse
import json
import math
import os
import re
import struct
import subprocess
import uuid
from pathlib import Path

from scripts import build_pikmin2_fixture as builder
from scripts.preview_pikmin2_room import records, generator, overlay
from experimental.pikmin2_generator_pose import write_position
from experimental.pikmin2_kochappy_arena_fixture import instrument_tutorial
from experimental.pikmin2_queen_actor import protocol
from experimental.pikmin2_bulblax_behavior import QUEEN_CLIPS, BABY_CLIPS
from experimental.pikmin2_lane24_gates import queen_natural_validate

APP = r'''#include "GameStat.h"
class QueenCameraTarget : public Creature {
public:QueenCameraTarget():Creature(nullptr){mHealth=1;}
 void refresh(Graphics&) override{} void doKill() override{}
};
class RoomApp : public PlugPikiApp {
 int frames=0,ready=0;bool hold=false;bool armed=false;bool finished=false;bool deployed=false;
 void pinSquad(float cx,float cy,float cz,float r){
  if(!pikiMgr)return;
  int idx=0;
  Iterator p(pikiMgr);
  CI_LOOP(p){
   Piki* a=static_cast<Piki*>(*p);
   if(!a||!a->isAlive())continue;
   const float ang=float(idx)*6.2831853f/64.f;
   a->mSRT.t.set(cx+r*std::sin(ang),cy,cz+r*std::cos(ang));
   ++idx;
  }
 }
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<36000||hold,"Queen natural startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr||!mapMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;++ready;
 static bool sustainLogged=false;if(n->mHealth<500.0f)n->mHealth=500.0f;
 {int ns=n->mStateMachine->getCurrID(n);if(ns==NAVISTATE_Pressed||ns==NAVISTATE_Flick||ns==NAVISTATE_Dead||ns==NAVISTATE_PikiZero||ns==NAVISTATE_DemoSunset||ns==NAVISTATE_DemoWait||ns==NAVISTATE_DemoInf){n->mStateMachine->transit(n,NAVISTATE_Walk);if(!sustainLogged){sustainLogged=true;std::puts("P2_QUEEN_NATURAL_NAVI_SUSTAIN injection=1");}}}
 {static bool guardLogged=false;if((int)GameStat::allPikis==0){GameStat::allPikis.set(1,Red);if(!guardLogged){guardLogged=true;std::puts("P2_QUEEN_NATURAL_GUARD_PIKMIN injection=1");}}}
 if(ready==1){
  n->mKontroller=new FixtureController();for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);
  int red=0,other=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* a=static_cast<Piki*>(*p);if(a->isAlive()){if(a->mColor==Red)++red;else++other;}}
  std::ifstream holding("queen-keep-open.txt");hold=bool(holding);
  n->resetPosition(Vector3f(34.0f,30.0f,1500.0f));
  SDL_SetWindowTitle(SDL_GL_GetCurrentWindow(),"Empress Bulblax natural lifecycle (#445)");
  std::printf("P2_QUEEN_NATURAL_BASELINE red=%d other=%d\n",red,other);
  std::puts("P2_QUEEN_NATURAL_CAPTAIN xyz=34,30,1500");
 }
 if(ready==30&&!armed){
  std::remove("p2-queen-inject.txt");
  std::ifstream check("p2-queen-inject.txt");require(!check,"Queen natural injection must be absent");
  std::ifstream raw("queen-fixture-profile.txt");auto cfg=p2queen::readActorConfig(raw);require(cfg.placements.size()==1,"Queen single placement");auto d=cfg.placements[0];
  require(cameraMgr&&cameraMgr->mCamera,"Queen camera missing");auto* target=new QueenCameraTarget();target->mSRT.t=Vector3f(d.x,d.y+85.f,d.z);auto* camera=cameraMgr->mCamera;camera->setTarget(target);camera->mControlsEnabled=false;
  PcamMotionInfo info=camera->mTargetMotionInfo;info.mDistance=1100;info.mFov=40;info.mAngle=35;info.mNaviWatchWeight=0;info.mWatchAdjustment=0;camera->startMotion(info);
  {std::ifstream src("queen-fixture-profile.txt",std::ios::binary);std::ofstream dst("p2-queen-actor.txt",std::ios::binary);dst<<src.rdbuf();dst.close();}
  const int heap=gsys->setHeap(SYSHEAP_App);pc_p2_queen_setup();gsys->setHeap(heap);
  std::puts("P2_QUEEN_NATURAL_ARMED larvae=1 no_injection=1");
  armed=true;
 }
 if(armed&&!finished){
  if(ready<900){
   pinSquad(34.0f,30.0f,2200.0f,40.0f); // hold-away: far north, outside BabySight and the root
   if(ready==60)std::puts("P2_QUEEN_NATURAL_PHASE hold_away");
  } else {
   if(!deployed){deployed=true;std::puts("P2_QUEEN_NATURAL_PHASE combat");}
   pinSquad(34.0f,30.0f,1200.0f,240.0f); // combat: labeled re-pin into the root so the receiver can kill it
  }
  if(pc_p2_queen_death_released()){
   capture("queen-natural-death.ppm");
   std::puts("PASS P2_QUEEN_NATURAL_RUNTIME");
   std::fflush(nullptr);finished=true;if(!hold)std::_Exit(0);
  } else if(ready>=20000){
   std::puts("FAIL P2_QUEEN_NATURAL_NO_DEATH");
   std::fflush(nullptr);finished=true;if(!hold)std::_Exit(3);
  }
 }
 std::fflush(stdout);return result;
 }};
'''


def instrument(source):
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    includes = ('#include <fstream>\n#include <string>\n#include "pc_p2_queen.h"\n#include "pc_p2_queen_policy.h"\n'
                'bool pc_p2_queen_death_released();\n'
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


QUEEN_WANTED = ('dead', 'sleep', 'wait1', 'damage', 'flick', 'rolling_l', 'rolling_r', 'born')
BABY_WANTED = ('born', 'move', 'dead')
SQUAD_RED = 64
PLACEMENT_ID = 230010
QUEEN_XYZ = (34.0, 30.0, 1200.0)


def queen_bank_profiles(bank):
    bank = Path(bank)
    meta = json.loads((bank / 'bulblax-bank.json').read_bytes())
    clips = []
    files = {}
    for species, wanted, reference in (('Queen', QUEEN_WANTED, QUEEN_CLIPS), ('Baby', BABY_WANTED, BABY_CLIPS)):
        motions = meta['motions'][species]
        for name in wanted:
            motion = motions.get(name)
            if motion is None or motion['source_frames'] != reference[name]['frames']:
                raise ValueError('Bank motion %s/%s disagrees with the #227 reference' % (species, name))
            clips.append(dict(species=species, name=name, duration=motion['source_frames'],
                              frames=list(motion['frames'])))
            for i in range(motion['poses']):
                fname = 'bulblax_%s_%s_%02d.mod' % (species, name, i)
                data = (bank / species / fname).read_bytes()
                if builder.sha256(bank / species / fname) != meta['file_sha256'][fname]:
                    raise ValueError('Model identity mismatch')
                files[fname] = data
    placement = dict(placement_id=PLACEMENT_ID, variant='default', larvae=True, xyz=list(QUEEN_XYZ), yaw=0)
    return protocol(clips, [placement]), files


def stage(assets, bank, output):
    assets = Path(assets).resolve()
    source = assets / 'dataDir/stages/practice/default.gen'
    data = source.read_bytes()
    entries = records(source)
    raw = generator(assets)
    starts = [m.start() for m in re.finditer(b'    0.0v', raw)]
    rows = [raw[a:(starts[i + 1] if i + 1 < len(starts) else len(raw))] for i, a in enumerate(starts)]
    template = next(r for r in rows if r[72:76] == b'ikip')
    for i in range(SQUAD_RED):
        row = bytearray(template)
        struct.pack_into('<I', row, 8, 235100 + i)
        row[16:48] = b'QueenNatural fixture'.ljust(32, b'\0')
        write_position(row, [-350.0 + i % 8 * 60.0, 30.0, 1850.0 + i // 8 * 12.0])
        struct.pack_into('>I', row, 92, 1)
        entries.append(bytes(row))
    data = data[:20] + struct.pack('>I', len(entries)) + b''.join(entries)
    run = Path(output).resolve() / uuid.uuid4().hex
    run.mkdir(parents=True)
    empty = data[:20] + struct.pack('>I', 0)
    overrides = {'dataDir/stages/chal0.ini': (assets / 'dataDir/stages/practice.ini').read_bytes(),
                 'dataDir/stages/chal0/default.gen': data,
                 'dataDir/courses/pikmin2room/private-queen.txt': b'Queen natural fixture\n'}
    for p in (assets / 'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/' + p.name, empty)
    overlay(assets, run / 'assets', overrides)
    config, files = queen_bank_profiles(bank)
    room = run / 'assets/dataDir/courses/pikmin2room'
    for name, blob in files.items():
        (room / name).write_bytes(blob)
    (run / 'queen-fixture-profile.txt').write_bytes(config)
    (run / 'p2-cargo-free.txt').write_bytes(b'P2_CARGO_FREE_1\n')
    original = {str(p.relative_to(assets)): builder.sha256(p)
                for p in (assets / 'dataDir/courses/practice').rglob('*') if p.is_file()}
    for rel, digest in original.items():
        if builder.sha256(run / 'assets' / rel) != digest:
            raise ValueError('Course changed')
    (run / 'queen-stage.json').write_bytes((json.dumps(
        dict(scene='original P1 Impact Site', interactive=True, starting_squad={'red': SQUAD_RED},
             placements=[dict(placement_id=PLACEMENT_ID, variant='default', larvae=True, xyz=list(QUEEN_XYZ), yaw=0)],
             config_sha256=builder.sha256(run / 'queen-fixture-profile.txt'),
             course_sha256=original), indent=2) + '\n').encode())
    return run


def pid_running(pid):
    out = subprocess.run(['tasklist', '/FI', 'PID eq %d' % pid, '/FO', 'CSV', '/NH'],
                         capture_output=True, text=True).stdout
    return str(pid) in out


def run(assets, bank, output, exe):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    directory = stage(assets, bank, output / 'queen')
    for extra in ('p2-queen-inject.txt',):
        target = directory / extra
        if target.exists():
            target.unlink()
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''), SDL_AUDIODRIVER='dummy')
    with (directory / 'native.log').open('w') as log:
        process = subprocess.Popen([str(Path(exe).resolve()), '--experimental-pikmin2-room'], cwd=directory,
                                   env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            code = process.wait(timeout=600)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            code = 'timeout'
    text = (directory / 'native.log').read_text(errors='replace')
    evidence = queen_natural_validate(text, code)
    evidence['directory'] = str(directory)
    evidence['exe'] = builder.snapshot([Path(exe)])
    evidence['leftover_pid'] = process.pid if pid_running(process.pid) else None
    evidence['no_leftover_process'] = evidence['leftover_pid'] is None
    evidence['passed'] = evidence['passed'] and evidence['no_leftover_process']
    (output / 'result.json').write_text(json.dumps(evidence, indent=2))
    print('queen-natural', evidence['passed'], directory, flush=True)
    return evidence


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    for key in ('native', 'build-dir', 'output'):
        b.add_argument('--' + key, type=Path, required=True)
    b.add_argument('--head', required=True)
    for parser in (sub.add_parser('run'), sub.add_parser('play')):
        for key in ('assets', 'bank', 'output', 'exe'):
            parser.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args()
    if a.command == 'build':
        build(a.native.resolve(), a.build_dir.resolve(), a.output, a.head)
    elif a.command == 'run':
        evidence = run(a.assets, a.bank, a.output, a.exe)
        raise SystemExit(0 if evidence['passed'] else 1)
    else:
        raise SystemExit(0)
