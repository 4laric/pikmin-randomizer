"""#445 Lane 24 free-mode Emperor Bulblax natural-death run (NO per-tick re-pin).

Slice 1 proved the Emperor's lethal path using the labeled per-tick re-pin of the
live squad into a ring, which the reviewer flagged as neutralising the Flick
(re-firing the entry blow for every stuck Pikmin after each Flick). This harness
removes that inflation: the 20-red squad is authored in a ring ONCE, switched to
`PikiMode::FreeMode`, and left to its own AI.

Slice 3 makes the Emperor's `receiveScan` source-faithful (a Pikmin only sticks
when it is actually attached and running the attack action, not merely inside the
root collision sphere), removes the per-frame captain refill, and parks the
captain outside `KingSight`. This run reports whether 20 free Pikmin still latch
and kill the Emperor, or an honest health floor.

No `p2-king-inject.txt`, no bombs, no per-tick re-pin, no captain refill. It
reuses the #289 sampled actor and the #234 bank.
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
from experimental.pikmin2_king_natural_flick_runtime import bomb_free_profile
from experimental.pikmin2_lane24_gates import king_free_mode_validate

APP = r'''#include "GameStat.h"
class KingCameraTarget : public Creature {
public:KingCameraTarget():Creature(nullptr){mHealth=1;}
 void refresh(Graphics&) override{} void doKill() override{}
};
class RoomApp : public PlugPikiApp {
 int frames=0,ready=0;bool hold=false;bool armed=false;bool finished=false;
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<24000||hold,"King free-mode startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr||!mapMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;++ready;
 // Slice 3: no captain refill. The captain is parked far outside KingSight once
 // and never healed or sustained, so the free-mode result is not propped up by
 // staging markers (NAVI_HEAL/NAVI_SUSTAIN are gone from this harness).
 {static bool guardLogged=false;if((int)GameStat::allPikis==0){GameStat::allPikis.set(1,Red);if(!guardLogged){guardLogged=true;std::puts("P2_KING_FREEMODE_GUARD_PIKMIN injection=1");}}}
 if(ready==1){
  n->mKontroller=new FixtureController();for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);
  n->resetPosition(Vector3f(34.0f,30.0f,400.0f)); // captain parked far outside KingSight (300)
  // Deploy once: switch the authored 20-red ring to FreeMode and leave it alone.
  int red=0,other=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* a=static_cast<Piki*>(*p);if(!a||!a->isAlive())continue;if(a->mColor==Red){++red;a->changeMode(PikiMode::FreeMode,n);}else++other;}
  std::ifstream holding("king-keep-open.txt");hold=bool(holding);
  SDL_SetWindowTitle(SDL_GL_GetCurrentWindow(),"Emperor Bulblax free-mode (#445)");
  std::printf("P2_KING_FREEMODE_BASELINE red=%d other=%d\n",red,other);
 }
 if(ready==30&&!armed){
  std::remove("p2-king-inject.txt");
  std::ifstream check("p2-king-inject.txt");require(!check,"King free-mode injection must be absent");
  std::ifstream raw("king-fixture-profile.txt");auto cfg=p2king::readActorConfig(raw);require(cfg.placements.size()>=1,"King placement fixture");auto d=cfg.placements[0];
  require(cameraMgr&&cameraMgr->mCamera,"King camera missing");auto* target=new KingCameraTarget();target->mSRT.t=Vector3f(d.x,d.y+60.f,d.z);auto* camera=cameraMgr->mCamera;camera->setTarget(target);camera->mControlsEnabled=false;
  PcamMotionInfo info=camera->mTargetMotionInfo;info.mDistance=1100;info.mFov=40;info.mAngle=35;info.mNaviWatchWeight=0;info.mWatchAdjustment=0;camera->startMotion(info);
  {std::ifstream src("king-fixture-profile.txt",std::ios::binary);std::ofstream dst("p2-king-actor.txt",std::ios::binary);dst<<src.rdbuf();dst.close();}
  const int heap=gsys->setHeap(SYSHEAP_App);pc_p2_king_setup();gsys->setHeap(heap);
  std::puts("P2_KING_FREEMODE_ARMED deploy_once=1 no_injection=1");
  armed=true;
 }
 if(armed&&!finished){
  if(pc_p2_king_dead_key_seen()){
   capture("king-free-mode-death.ppm");
   std::puts("PASS P2_KING_FREEMODE_DEATH");
   std::fflush(nullptr);finished=true;if(!hold)std::_Exit(0);
  } else if(pc_p2_king_behavior_tick()>=10800){
   capture("king-free-mode-floor.ppm");
   std::printf("P2_KING_FREEMODE_FLOOR tick=%lu\n",pc_p2_king_behavior_tick());
   std::fflush(nullptr);finished=true;if(!hold)std::_Exit(0);
  }
 }
 std::fflush(stdout);return result;
 }};
'''


def instrument(source):
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    includes = ('#include <cstdio>\n#include <cstdlib>\n#include <fstream>\n#include <string>\n#include "pc_p2_king.h"\n'
                '#include "pc_p2_king_policy.h"\n'
                'unsigned long pc_p2_king_behavior_tick();\n'
                'bool pc_p2_king_dead_key_seen();\n'
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


SQUAD_RED = 20
PLACEMENT_ID = 230020
SPAWN = (34.0, 30.0, 1896.0)
RING_RADIUS = 58.0


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
        struct.pack_into('<I', row, 8, 235200 + i)
        row[16:48] = b'KingFreeMode fixture'.ljust(32, b'\0')
        ang = 2.0 * math.pi * i / SQUAD_RED
        write_position(row, [SPAWN[0] + RING_RADIUS * math.sin(ang), 30.0, SPAWN[2] + RING_RADIUS * math.cos(ang)])
        struct.pack_into('>I', row, 92, 1)  # 1 = red
        entries.append(bytes(row))
    data = data[:20] + struct.pack('>I', len(entries)) + b''.join(entries)
    run = Path(output).resolve() / uuid.uuid4().hex
    run.mkdir(parents=True)
    empty = data[:20] + struct.pack('>I', 0)
    overrides = {'dataDir/stages/chal0.ini': (assets / 'dataDir/stages/practice.ini').read_bytes(),
                 'dataDir/stages/chal0/default.gen': data,
                 'dataDir/courses/pikmin2room/private-king.txt': b'King free-mode fixture\n'}
    for p in (assets / 'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/' + p.name, empty)
    overlay(assets, run / 'assets', overrides)
    _, _, _, files, _ = king_profiles(bank)
    room = run / 'assets/dataDir/courses/pikmin2room'
    for name, blob in files.items():
        (room / name).write_bytes(blob)
    (run / 'king-fixture-profile.txt').write_bytes(bomb_free_profile(bank))
    (run / 'p2-cargo-free.txt').write_bytes(b'P2_CARGO_FREE_1\n')
    original = {str(p.relative_to(assets)): builder.sha256(p)
                for p in (assets / 'dataDir/courses/practice').rglob('*') if p.is_file()}
    for rel, digest in original.items():
        if builder.sha256(run / 'assets' / rel) != digest:
            raise ValueError('Course changed')
    (run / 'king-stage.json').write_bytes((json.dumps(
        dict(scene='original P1 Impact Site', interactive=True, starting_squad={'red': SQUAD_RED},
             placements=[dict(placement_id=PLACEMENT_ID, variant='default', xyz=list(SPAWN), yaw=0)],
             config_sha256=builder.sha256(run / 'king-fixture-profile.txt'),
             course_sha256=original), indent=2) + '\n').encode())
    return run


def pid_running(pid):
    out = subprocess.run(['tasklist', '/FI', 'PID eq %d' % pid, '/FO', 'CSV', '/NH'],
                         capture_output=True, text=True).stdout
    return str(pid) in out


def run(assets, bank, output, exe):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    directory = stage(assets, bank, output / 'king')
    for extra in ('p2-king-inject.txt',):
        target = directory / extra
        if target.exists():
            target.unlink()
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''), SDL_AUDIODRIVER='dummy')
    with (directory / 'native.log').open('w') as log:
        process = subprocess.Popen([str(Path(exe).resolve()), '--experimental-pikmin2-room'], cwd=directory,
                                   env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            code = process.wait(timeout=420)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            code = 'timeout'
    text = (directory / 'native.log').read_text(errors='replace')
    evidence = king_free_mode_validate(text, code)
    evidence['directory'] = str(directory)
    evidence['exe'] = builder.snapshot([Path(exe)])
    evidence['leftover_pid'] = process.pid if pid_running(process.pid) else None
    evidence['no_leftover_process'] = evidence['leftover_pid'] is None
    evidence['passed'] = evidence['passed'] and evidence['no_leftover_process']
    (output / 'result.json').write_text(json.dumps(evidence, indent=2))
    print('king-free-mode', evidence['passed'], 'killed=%s floor=%s' % (evidence['killed'], evidence['health_floor']),
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
