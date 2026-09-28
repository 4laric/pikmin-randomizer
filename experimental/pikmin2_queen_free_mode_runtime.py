"""#445 Lane 24 free-mode Empress Bulblax natural-death run (NO per-tick re-pin).

The slice-2 Queen lifecycle harness killed the 5000 HP Empress with the labeled
per-tick ring re-pin, which the reviewer disclosed as staged combat (each Flick
re-fires the 32 entry blows). This harness removes that staging the same way the
King free-mode run did: the 64-red squad is authored ONCE in a ring, switched to
`PikiMode::FreeMode`, and left to its own AI. The captain is parked far outside
the Queen's territory/attack/press reach ONCE and is never healed or sustained,
so whether the Empress dies (via the proximity latch reserved for this
headless-actor fixture) and what the roll does to the squad are measured without
`P2_QUEEN_*_NAVI_HEAL` / `REPIN` markers.

No `p2-queen-inject.txt`, no bombs, no per-tick re-pin, no captain refill.
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
from experimental.pikmin2_lane24_gates import queen_free_mode_validate

APP = r'''#include "GameStat.h"
class QueenCameraTarget : public Creature {
public:QueenCameraTarget():Creature(nullptr){mHealth=1;}
 void refresh(Graphics&) override{} void doKill() override{}
};
class RoomApp : public PlugPikiApp {
 int frames=0,ready=0;bool hold=false;bool armed=false;bool finished=false;
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<24000||hold,"Queen free-mode startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr||!mapMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;++ready;
 // State-sustain only (distinct from the prohibited captain health refill):
 // keep the parked captain out of Pressed/Flick/Dead/PikiZero/demo idle states so
 // the fixture does not day-end and exit early. No health change, no NAVI_HEAL.
 {static bool sustainLogged=false;int ns=n->mStateMachine->getCurrID(n);if(ns==NAVISTATE_Pressed||ns==NAVISTATE_Flick||ns==NAVISTATE_Dead||ns==NAVISTATE_PikiZero||ns==NAVISTATE_DemoSunset||ns==NAVISTATE_DemoWait||ns==NAVISTATE_DemoInf){n->mStateMachine->transit(n,NAVISTATE_Walk);if(!sustainLogged){sustainLogged=true;std::puts("P2_QUEEN_FREEMODE_NAVI_SUSTAIN injection=1 state_transit=no_health_change");}}}
 {static bool guardLogged=false;if((int)GameStat::allPikis==0){GameStat::allPikis.set(1,Red);if(!guardLogged){guardLogged=true;std::puts("P2_QUEEN_FREEMODE_GUARD_PIKMIN injection=1");}}}
 if(ready==1){
  n->mKontroller=new FixtureController();for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);
  n->resetPosition(Vector3f(34.0f,30.0f,3200.0f)); // captain parked far outside territory/attack/press, never healed
  int red=0,other=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* a=static_cast<Piki*>(*p);if(!a||!a->isAlive())continue;if(a->mColor==Red){++red;a->changeMode(PikiMode::FreeMode,n);}else++other;}
  std::ifstream holding("queen-keep-open.txt");hold=bool(holding);
  SDL_SetWindowTitle(SDL_GL_GetCurrentWindow(),"Empress Bulblax free-mode (#445)");
  std::printf("P2_QUEEN_FREEMODE_BASELINE red=%d other=%d\n",red,other);
 }
 if(ready==30&&!armed){
  std::remove("p2-queen-inject.txt");
  std::ifstream check("p2-queen-inject.txt");require(!check,"Queen free-mode injection must be absent");
  std::ifstream raw("queen-fixture-profile.txt");auto cfg=p2queen::readActorConfig(raw);require(cfg.placements.size()==1,"Queen single placement");auto d=cfg.placements[0];
  require(cameraMgr&&cameraMgr->mCamera,"Queen camera missing");auto* target=new QueenCameraTarget();target->mSRT.t=Vector3f(d.x,d.y+85.f,d.z);auto* camera=cameraMgr->mCamera;camera->setTarget(target);camera->mControlsEnabled=false;
  PcamMotionInfo info=camera->mTargetMotionInfo;info.mDistance=1100;info.mFov=40;info.mAngle=35;info.mNaviWatchWeight=0;info.mWatchAdjustment=0;camera->startMotion(info);
  {std::ifstream src("queen-fixture-profile.txt",std::ios::binary);std::ofstream dst("p2-queen-actor.txt",std::ios::binary);dst<<src.rdbuf();dst.close();}
  const int heap=gsys->setHeap(SYSHEAP_App);pc_p2_queen_setup();gsys->setHeap(heap);
  std::puts("P2_QUEEN_FREEMODE_ARMED deploy_once=1 no_injection=1");
  armed=true;
 }
 if(armed&&!finished){
  if(pc_p2_queen_death_released()){
   capture("queen-free-mode-death.ppm");
   std::puts("PASS P2_QUEEN_FREEMODE_DEATH");
   std::fflush(nullptr);finished=true;if(!hold)std::_Exit(0);
  } else if(ready>=15000){
   capture("queen-free-mode-floor.ppm");
   std::printf("P2_QUEEN_FREEMODE_FLOOR tick=%d\n",ready);
   std::fflush(nullptr);finished=true;if(!hold)std::_Exit(0);
  }
 }
 std::fflush(stdout);return result;
 }};
'''


def instrument(source):
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    includes = ('#include <cstdio>\n#include <cstdlib>\n#include <fstream>\n#include <string>\n#include "pc_p2_queen.h"\n#include "pc_p2_queen_policy.h"\n'
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
RING_RADIUS = 220.0  # inside RootRadius 275 so the deploy-once proximity latch engages


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
        row[16:48] = b'QueenFreeMode fixture'.ljust(32, b'\0')
        ang = 2.0 * math.pi * i / SQUAD_RED
        write_position(row, [QUEEN_XYZ[0] + RING_RADIUS * math.sin(ang), 30.0, QUEEN_XYZ[2] + RING_RADIUS * math.cos(ang)])
        struct.pack_into('>I', row, 92, 1)
        entries.append(bytes(row))
    data = data[:20] + struct.pack('>I', len(entries)) + b''.join(entries)
    run = Path(output).resolve() / uuid.uuid4().hex
    run.mkdir(parents=True)
    empty = data[:20] + struct.pack('>I', 0)
    overrides = {'dataDir/stages/chal0.ini': (assets / 'dataDir/stages/practice.ini').read_bytes(),
                 'dataDir/stages/chal0/default.gen': data,
                 'dataDir/courses/pikmin2room/private-queen.txt': b'Queen free-mode fixture\n'}
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
    evidence = queen_free_mode_validate(text, code)
    evidence['directory'] = str(directory)
    evidence['exe'] = builder.snapshot([Path(exe)])
    evidence['leftover_pid'] = process.pid if pid_running(process.pid) else None
    evidence['no_leftover_process'] = evidence['leftover_pid'] is None
    evidence['passed'] = evidence['passed'] and evidence['no_leftover_process']
    (output / 'result.json').write_text(json.dumps(evidence, indent=2))
    print('queen-free-mode', evidence['passed'], 'killed=%s floor=%s' % (evidence['killed'], evidence['health_floor']),
          directory, flush=True)
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
