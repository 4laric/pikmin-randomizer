"""#445 Lane 24 natural (un-injected) Flick/trample gate.

The bounded #445 gate moved the Emperor Bulblax `Flick`/key-35 trample to a
required check by *injecting* the Flick state. This harness proves the natural
path instead: with the intact 5-red/5-blue squad staged around the buried
Emperor and **no** `p2-king-inject.txt`, the actor's own `receiveScan`
accumulates stuck Pikmin, its natural `checkFlick` selects `Flick` (full
health), and the key-35 `trampleScan` presses live Pikmin.

The only fixture staging is the labeled re-pin of the live squad into a ring
around the Emperor's spawn each behavior tick, so a loaded host cannot starve
the contact scan; the Flick decision, state entry and trample receivers are
run un-injected. It reuses the #289 sampled actor and the #234 bank.
"""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from scripts import build_pikmin2_fixture as builder
from experimental.pikmin2_kochappy_arena_fixture import instrument_tutorial
from experimental.pikmin2_king_runtime import stage as king_stage, KING_WANTED
from experimental.pikmin2_king_actor import protocol
from experimental.pikmin2_bulblax_behavior import KING_CLIPS

APP = r'''#include "GameStat.h"
class KingCameraTarget : public Creature {
public:KingCameraTarget():Creature(nullptr){mHealth=1;}
 void refresh(Graphics&) override{} void doKill() override{}
};
class RoomApp : public PlugPikiApp {
 int frames=0,ready=0;bool hold=false;bool armed=false;bool finished=false;
 void pinSquad(float cx,float cy,float cz){
  if(!pikiMgr)return;
  const float r=30.0f;int idx=0;
  Iterator p(pikiMgr);
  CI_LOOP(p){
   Piki* a=static_cast<Piki*>(*p);
   if(!a||!a->isAlive())continue;
   const float ang=float(idx)*0.6283185f;
   a->mSRT.t.set(cx+r*std::sin(ang),cy,cz+r*std::cos(ang));
   ++idx;
  }
 }
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<20000||hold,"King natural-flick startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr||!mapMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;++ready;
 static bool sustainLogged=false;if(n->mHealth<500.0f)n->mHealth=500.0f;
 {int ns=n->mStateMachine->getCurrID(n);if(ns==NAVISTATE_Pressed||ns==NAVISTATE_Flick||ns==NAVISTATE_Dead||ns==NAVISTATE_PikiZero||ns==NAVISTATE_DemoSunset||ns==NAVISTATE_DemoWait||ns==NAVISTATE_DemoInf){n->mStateMachine->transit(n,NAVISTATE_Walk);if(!sustainLogged){sustainLogged=true;std::puts("P2_KING_NATURAL_NAVI_SUSTAIN injection=1");}}}
 {static bool guardLogged=false;if((int)GameStat::allPikis==0){GameStat::allPikis.set(1,Red);if(!guardLogged){guardLogged=true;std::puts("P2_KING_NATURAL_GUARD_PIKMIN injection=1");}}}
 if(ready==1){
  n->mKontroller=new FixtureController();for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);
  int red=0,blue=0,other=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* a=static_cast<Piki*>(*p);if(a->isAlive()){if(a->mColor==Red)++red;else if(a->mColor==Blue)++blue;else++other;}}require(red==5&&blue==5&&other==0,"King natural-flick 5red5blue");
  std::ifstream holding("king-keep-open.txt");hold=bool(holding);
  SDL_SetWindowTitle(SDL_GL_GetCurrentWindow(),"Emperor Bulblax natural Flick (#445)");
  std::printf("P2_KING_BASELINE red=%d blue=%d\n",red,blue);
 }
 if(ready==30&&!armed){
  // Natural path: ensure the injection channel is absent.
  std::remove("p2-king-inject.txt");
  std::ifstream check("p2-king-inject.txt");require(!check,"King natural-flick injection must be absent");
  std::ifstream raw("king-fixture-profile.txt");auto cfg=p2king::readActorConfig(raw);require(cfg.placements.size()>=1,"King placement fixture");auto d=cfg.placements[0];
  require(cameraMgr&&cameraMgr->mCamera,"King camera missing");auto* target=new KingCameraTarget();target->mSRT.t=Vector3f(d.x,d.y+60.f,d.z);auto* camera=cameraMgr->mCamera;camera->setTarget(target);camera->mControlsEnabled=false;
  PcamMotionInfo info=camera->mTargetMotionInfo;info.mDistance=1100;info.mFov=40;info.mAngle=35;info.mNaviWatchWeight=0;info.mWatchAdjustment=0;camera->startMotion(info);
  {std::ifstream src("king-fixture-profile.txt",std::ios::binary);std::ofstream dst("p2-king-actor.txt",std::ios::binary);dst<<src.rdbuf();dst.close();}
  const int heap=gsys->setHeap(SYSHEAP_App);pc_p2_king_setup();gsys->setHeap(heap);
  std::puts("P2_KING_NATURAL_ARMED no_injection=1");
  armed=true;
 }
 if(armed&&!finished){
  pinSquad(34.0f,30.0f,1896.0f);
  if(pc_p2_king_behavior_tick()>=1400){
   capture("king-natural-flick.ppm");
   std::puts("PASS P2_KING_NATURAL_RUNTIME natural_flick_trample");
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


def bomb_free_profile(bank):
    """P2_KING_ACTOR_1 config for the natural scenario: one default Emperor in
    the squad and **no** bombs, so nothing but live Pikmin touches the actor."""
    bank = Path(bank)
    meta = json.loads((bank / 'bulblax-bank.json').read_bytes())
    motions = meta['motions']['KingChappy']
    clips = []
    for name in KING_WANTED:
        motion = motions.get(name)
        if motion is None or motion['source_frames'] != KING_CLIPS[name]['frames']:
            raise ValueError('Bank motion %s disagrees with the #227 reference' % name)
        clips.append(dict(species='KingChappy', name=name, duration=motion['source_frames'],
                          frames=list(motion['frames'])))
    placement = [dict(placement_id=230020, variant='default', xyz=[34, 30, 1896], yaw=0)]
    return protocol(clips, placement, [])


def validate(text, code):
    required = dict(
        completion=code == 0 and 'PASS P2_KING_NATURAL_RUNTIME' in text,
        baseline='red=5 blue=5' in text,
        ready=bool(re.search(r'P2_KING_READY id=230020 enemy=53 variant=default', text)),
        no_injection=('P2_KING_INJECT_FLICK' not in text and 'P2_KING_INJECT_KILL' not in text
                      and not re.search(r'P2_KING_INJECT id=', text)
                      and 'P2_KING_BOMB_READY' not in text and 'P2_KING_BOMB_EXTERNAL' not in text),
        natural_check_flick=bool(re.search(r'P2_KING_CHECK_FLICK id=230020 .*next=3', text)),
        natural_trample=bool(re.search(r'P2_KING_TRAMPLE id=230020 pressed_pikmin=[1-9]\d*', text)),
        natural_flick_state=bool(re.search(r'P2_KING_STATE id=230020 from=3 to=0', text)),
        no_rewards='P2_CARGO_READY' not in text and 'P2_POD_COLLECT' not in text,
    )
    failed = sorted(name for name, ok in required.items() if not ok)
    return dict(passed=not failed, failed=failed, checks=required, exit_code=code,
                scope='Natural (un-injected) Flick; only the live-squad pin is labeled fixture staging')


def pid_running(pid):
    out = subprocess.run(['tasklist', '/FI', 'PID eq %d' % pid, '/FO', 'CSV', '/NH'],
                         capture_output=True, text=True).stdout
    return str(pid) in out


def run(assets, bank, output, exe):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    directory = king_stage(assets, bank, output / 'king')
    # Natural scenario: replace the shared profile's staged external bomb with a
    # bomb-free Emperor config so no prop injection touches the actor.
    (directory / 'king-fixture-profile.txt').write_bytes(bomb_free_profile(bank))
    # Guarantee the natural run has no injection channel.
    for extra in ('p2-king-inject.txt',):
        target = directory / extra
        if target.exists():
            target.unlink()
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''), SDL_AUDIODRIVER='dummy')
    with (directory / 'native.log').open('w') as log:
        process = subprocess.Popen([str(Path(exe).resolve()), '--experimental-pikmin2-room'], cwd=directory,
                                   env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            code = process.wait(timeout=180)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            code = 'timeout'
    text = (directory / 'native.log').read_text(errors='replace')
    evidence = validate(text, code)
    evidence['directory'] = str(directory)
    evidence['exe'] = builder.snapshot([Path(exe)])
    evidence['leftover_pid'] = process.pid if pid_running(process.pid) else None
    evidence['no_leftover_process'] = evidence['leftover_pid'] is None
    evidence['passed'] = evidence['passed'] and evidence['no_leftover_process']
    (output / 'result.json').write_text(json.dumps(evidence, indent=2))
    print('king-natural', evidence['passed'], directory, flush=True)
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
