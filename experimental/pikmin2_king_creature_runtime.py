"""#445 Lane 24 King-as-Creature slice: bind the Emperor Bulblax (53) to a
generated host Teki so ordinary free Pikmin kill it through the engine.

The native sidecar `pc_p2_king_teki` binds a generated TEKI_Chappy host (the same
carcass path the preview Pod already rebind-scans), rewrites the host health to
the Emperor's 1300, draws the King model over it, and applies the source
stuck/Flick thresholds to any Pikmin actually attached in AttackMode. The engine
owns health/damage/carcass. This fixture stages the host + a Pod and a free squad,
then observes the natural free-mode kill -> corpse -> Pod corpse receipt in one
GL log. No injection, no per-tick re-pin.
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
from experimental.pikmin2_king_runtime import king_profiles
from experimental.pikmin2_mamuta_rules import load_pod_package, treasure_record, stage_cargo
from experimental.pikmin2_lane24_gates import king_creature_validate

APP = r'''#include "GameStat.h"
class KingCameraTarget : public Creature {
public:KingCameraTarget():Creature(nullptr){mHealth=1;}
 void refresh(Graphics&) override{} void doKill() override{}
};
class RoomApp : public PlugPikiApp {
 int frames=0,ready=0;bool hold=false;bool armed=false;bool finished=false;bool deathSeen=false;
 Teki* host=nullptr;bool corpseSeen=false;
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<30000||hold,"King creature startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_p2_preview_cargo_free_ready()&&!pc_p2_preview_ready())return result;
 if(!naviMgr||!tekiMgr||!mapMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;++ready;
  // NAVISTATE_Pellet is the long-idle captain->pellet turn (NaviIdleState::exec,
  // mNeutralTime > 140): forbid it so the free reds haul the carcass, not the captain.
  {int ns=n->mStateMachine->getCurrID(n);if(ns==NAVISTATE_Pressed||ns==NAVISTATE_Flick||ns==NAVISTATE_Dead||ns==NAVISTATE_PikiZero||ns==NAVISTATE_DemoSunset||ns==NAVISTATE_DemoWait||ns==NAVISTATE_DemoInf||ns==NAVISTATE_Pellet){n->mStateMachine->transit(n,NAVISTATE_Walk);}}
 {if((int)GameStat::allPikis==0)GameStat::allPikis.set(1,Red);}
 if(ready==1){
  n->mKontroller=new FixtureController();for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);
  Iterator it(tekiMgr);CI_LOOP(it){Teki* t=static_cast<Teki*>(*it);if(t&&pc_p2_king_teki_is_bound(t))host=t;}
  require(host,"King host found");
  {Vector3f near(host->mSRT.t);near.y=mapMgr->getMinY(near.x,near.z,true);n->resetPosition(near);}
  int red=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* a=static_cast<Piki*>(*p);if(a&&a->isAlive()&&a->mColor==Red){++red;a->changeMode(PikiMode::FreeMode,n);}}
  std::ifstream holding("king-keep-open.txt");hold=bool(holding);
  SDL_SetWindowTitle(SDL_GL_GetCurrentWindow(),"Emperor Bulblax creature host (#445)");
  std::printf("P2_KING_CREATURE_BASELINE red=%d\n",red);
 }
 if(ready==30&&!armed){
  require(cameraMgr&&cameraMgr->mCamera,"King camera missing");auto* target=new KingCameraTarget();target->mSRT.t=Vector3f(host->mSRT.t.x,host->mSRT.t.y+60.f,host->mSRT.t.z);auto* camera=cameraMgr->mCamera;camera->setTarget(target);camera->mControlsEnabled=false;
  PcamMotionInfo info=camera->mTargetMotionInfo;info.mDistance=1100;info.mFov=40;info.mAngle=35;info.mNaviWatchWeight=0;info.mWatchAdjustment=0;camera->startMotion(info);
  armed=true;std::puts("P2_KING_CREATURE_ARMED no_injection=1 deploy_once=1");
 }
 if(armed&&!finished){
  if(pc_p2_king_teki_dead_key_seen()&&!deathSeen){deathSeen=true;std::puts("P2_KING_CREATURE_DEATH_SEEN receiver=engine host_health=0");}
  if(deathSeen&&!corpseSeen){
   Iterator pellets(pelletMgr);CI_LOOP(pellets){Pellet* pl=static_cast<Pellet*>(*pellets);if(pl->isAlive()&&pl->mPelletView==static_cast<PelletView*>(host)){corpseSeen=true;std::puts("P2_KING_CREATURE_CORPSE_PELLET found=1");break;}}
  }
  if(deathSeen&&pc_p2_preview_pokos()>0){
   capture("king-creature-dead.ppm");
   std::printf("P2_KING_CREATURE_RECEIPT pokos=%d corpse_pellet=%d\n",pc_p2_preview_pokos(),corpseSeen?1:0);
   std::puts("PASS P2_KING_CREATURE_RUNTIME");
   std::fflush(nullptr);finished=true;if(!hold)std::_Exit(0);
  } else if(ready>=18000){
   std::printf("FAIL P2_KING_CREATURE_NO_RECEIPT corpse_pellet=%d pokos=%d\n",corpseSeen?1:0,pc_p2_preview_pokos());
   std::fflush(nullptr);finished=true;if(!hold)std::_Exit(3);
  }
 }
 std::fflush(stdout);return result;
 }};
'''


def instrument(source):
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    includes = ('#include <cstdio>\n#include <cstdlib>\n#include <fstream>\n#include <string>\n#include "pc_p2_king_teki.h"\n'
                '#include "pc_p2_preview.h"\n'
                'bool pc_p2_king_teki_dead_key_seen();\n'
                'bool pc_p2_king_teki_is_bound(const BTeki*);\n'
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


HOST_GENERATOR = 221010
HOST_TYPE = 3  # TEKI_Chappy: the carcass path the preview Pod already rebind-scans
SQUAD = 32
SPAWN = (34.0, 30.0, 1896.0)


def stage(assets, bank, pod_package, output):
    assets = Path(assets).resolve()
    source = assets / 'dataDir/stages/practice/default.gen'
    data = source.read_bytes()
    entries = records(source)
    raw = generator(assets)
    starts = [m.start() for m in re.finditer(b'    0.0v', raw)]
    rows = [raw[a:(starts[i + 1] if i + 1 < len(starts) else len(raw))] for i, a in enumerate(starts)]
    enemy = next(r for r in rows if r[72:76] == b'iket')
    piki = next(r for r in rows if r[72:76] == b'ikip')
    used = {struct.unpack_from('<I', r, 8)[0] for r in entries}
    # Chappy host TEKI (the King).
    row = bytearray(enemy)
    struct.pack_into('<I', row, 8, HOST_GENERATOR)
    row[16:48] = b'King host Chappy'.ljust(32, b'\0')
    row[80] = HOST_TYPE
    row[81] = 0  # pellet kind none (the borrowed iket personality wants a pellet)
    row[82] = 0  # pellet color
    struct.pack_into('<f', row, 119, 0.0)  # FLT_PelletAppearChance: Emperor drops none
    write_position(row, SPAWN)
    entries.append(bytes(row))
    used.add(HOST_GENERATOR)
    # Starting red squad.
    for i in range(SQUAD):
        r = bytearray(piki)
        struct.pack_into('<I', r, 8, 235200 + i)
        r[16:48] = b'King creature squad'.ljust(32, b'\0')
        ang = 2.0 * math.pi * i / SQUAD
        write_position(r, [SPAWN[0] + 40.0 * math.sin(ang), 30.0, SPAWN[2] + 40.0 * math.cos(ang)])
        struct.pack_into('>I', r, 92, 1)  # red
        entries.append(bytes(r))
    data = data[:20] + struct.pack('>I', len(entries)) + b''.join(entries)
    run = Path(output).resolve() / uuid.uuid4().hex
    run.mkdir(parents=True)
    empty = data[:20] + struct.pack('>I', 0)
    overrides = {'dataDir/stages/chal0.ini': (assets / 'dataDir/stages/practice.ini').read_bytes(),
                 'dataDir/stages/chal0/default.gen': data,
                 'dataDir/courses/pikmin2room/private-king.txt': b'King creature host fixture\n'}
    for p in (assets / 'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/' + p.name, empty)
    overlay(assets, run / 'assets', overrides)
    _, _, _, files, _ = king_profiles(bank)
    room = run / 'assets/dataDir/courses/pikmin2room'
    for name, blob in files.items():
        (room / name).write_bytes(blob)
    (run / 'p2-king-teki.txt').write_text('P2_KING_TEKI_1 1 %d %d\n' % (HOST_GENERATOR, HOST_TYPE))
    (run / 'p2-cargo-free.txt').write_text('P2_CARGO_FREE_1\n')
    package = load_pod_package(pod_package)
    stage_cargo(run, assets, package, record=treasure_record(assets))
    (run / 'king-stage.json').write_bytes((json.dumps(
        dict(scene='original P1 Impact Site', interactive=True, host_generator=HOST_GENERATOR,
             host_type=HOST_TYPE, starting_squad={'red': SQUAD},
             sidecar='p2-king-teki.txt', pod_package=package['path']), indent=2) + '\n').encode())
    return run


def pid_running(pid):
    out = subprocess.run(['tasklist', '/FI', 'PID eq %d' % pid, '/FO', 'CSV', '/NH'],
                         capture_output=True, text=True).stdout
    return str(pid) in out


def run(assets, bank, pod_package, output, exe):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    directory = stage(assets, bank, pod_package, output / 'king')
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
    evidence = king_creature_validate(text, code)
    evidence['directory'] = str(directory)
    evidence['exe'] = builder.snapshot([Path(exe)])
    evidence['leftover_pid'] = process.pid if pid_running(process.pid) else None
    evidence['no_leftover_process'] = evidence['leftover_pid'] is None
    evidence['passed'] = evidence['passed'] and evidence['no_leftover_process']
    (output / 'result.json').write_text(json.dumps(evidence, indent=2))
    print('king-creature', evidence['passed'], directory, flush=True)
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
        parser.add_argument('--pod-package', dest='pod_package', type=Path, required=True)
    a = p.parse_args()
    if a.command == 'build':
        build(a.native.resolve(), a.build_dir.resolve(), a.output, a.head)
    elif a.command == 'run':
        evidence = run(a.assets, a.bank, a.pod_package, a.output, a.exe)
        raise SystemExit(0 if evidence['passed'] else 1)
    else:
        raise SystemExit(0)
