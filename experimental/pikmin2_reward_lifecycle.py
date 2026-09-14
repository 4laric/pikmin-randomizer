"""Live duplicate-reward lifecycle fixture for the native Pod economy (#397).

Stages the real Snow-Chappy + Research-Pod room (via
:mod:`experimental.pikmin2_snow_lifecycle`) and then, in one private
instrumented ``RoomApp``:

  1. finds the registered Chappy, frames the camera, and attacks it to death
     with repeated Navi ``InteractAttack``;
  2. waits for the corpse (``mDeadState==2`` + ``mPellet``) and delivers it
     through the native Pod receiver ``pc_p2_preview_deliver``;
  3. kills the corpse pellet, respawns the same generator, and calls the new
     additive ``pc_p2_preview_rebind_corpses()``;
  4. kills the respawned actor and delivers its corpse again.

The native ``P2Economy`` must reject the second generator-keyed receipt
(``new=0``) and the ledger must keep a single ``corpse:`` row. Delivery is
injected through the Pod receiver, not a Pikmin carry route; that intervention
is recorded in the evidence.

This is a reward-registry/lifecycle contract test, not source P2 drop parity.
"""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from scripts import build_pikmin2_fixture as builder

APP = r'''class RoomApp : public PlugPikiApp {
 int frames=0,observed=0,phase=0,deathFrame=-1,secondDeath=-1,deliver1=-1,deliver2=-1;
 int spawnFrame=-1,summaryFrame=-1;
 unsigned gen=0;
 Teki* deadPtr=nullptr;Teki* dead2=nullptr;Generator* targetGen=nullptr;
 Teki* findChappy(){Iterator it(tekiMgr);CI_LOOP(it){Teki* a=static_cast<Teki*>(*it);if(a&&a->mTekiType==TEKI_Chappy&&a->mGenerator)return a;}return nullptr;}
 void frameOn(Teki* t){if(cameraMgr&&cameraMgr->mCamera){cameraMgr->mCamera->setTarget(t);cameraMgr->mCamera->mControlsEnabled=false;}}
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<30000,"reward lifecycle startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_p2_preview_ready()||pc_p2_preview_pokos()<0||!naviMgr||!tekiMgr||!cameraMgr||!cameraMgr->mCamera)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
 ++observed;
 if(observed==1){
  for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
  Teki* t=findChappy();require(t,"reward lifecycle: no registered Chappy");
  gen=t->mGenerator->_70;targetGen=t->mGenerator;frameOn(t);
  std::printf("P2_REWARD_TARGET generator=%u pokos=%d corpses=%d\n",gen,pc_p2_preview_pokos(),pc_p2_preview_corpse_count());std::fflush(stdout);
 }
 if(observed>1&&observed<=300&&observed%60==0){Teki* t=findChappy();if(t)frameOn(t);}
 if(phase==0){
  Teki* a=findChappy();
  if(!a||!a->isAlive()){deadPtr=a;deathFrame=observed;phase=1;
   std::printf("P2_REWARD_DEATH n=1 generator=%u\n",gen);std::fflush(stdout);}
  else{deadPtr=a;const bool hit=a->stimulate(InteractAttack(n,nullptr,100000,false));
   if(observed<30||observed%10==0)std::printf("P2_REWARD_ATTACK n=1 accepted=%d health=%.1f\n",int(hit),a->mHealth);}
 }
 if(phase==1){
  if(deadPtr&&deadPtr->mPellet&&deadPtr->mDeadState==2){
   const int before=pc_p2_preview_pokos();
   const bool ok=pc_p2_preview_deliver(deadPtr->mPellet);
   const int after=pc_p2_preview_pokos();deliver1=int(ok);
   std::printf("P2_REWARD_DELIVER n=1 ok=%d pokos_before=%d pokos_after=%d\n",int(ok),before,after);
   deadPtr->mPellet->kill(false);phase=2;
  } else if(observed>=deathFrame+240){std::printf("P2_REWARD_FAIL no_corpse_1\n");std::fflush(stdout);std::_Exit(2);}
 }
 if(phase==2){
  const int before=pc_p2_preview_corpse_count();
  pc_p2_preview_rebind_corpses();
  targetGen->init();spawnFrame=observed;phase=3;
  std::printf("P2_REWARD_RESPAWN generator=%u corpses_before=%d corpses_after=%d\n",gen,before,pc_p2_preview_corpse_count());std::fflush(stdout);
 }
 if(phase==3){
  Teki* fresh=findChappy();
  if(fresh&&fresh->isAlive()){frameOn(fresh);phase=4;
   std::printf("P2_REWARD_REENTRY reused=%d\n",int(fresh==deadPtr));std::fflush(stdout);}
  else if(observed>=spawnFrame+300){std::printf("P2_REWARD_FAIL no_respawn\n");std::fflush(stdout);std::_Exit(2);}
 }
 if(phase==4){
  Teki* a=findChappy();
  if(!a||!a->isAlive()){dead2=a;secondDeath=observed;phase=5;
   std::printf("P2_REWARD_DEATH n=2 generator=%u\n",gen);std::fflush(stdout);}
  else{dead2=a;const bool hit=a->stimulate(InteractAttack(n,nullptr,100000,false));
   if(observed%10==0)std::printf("P2_REWARD_ATTACK n=2 accepted=%d health=%.1f\n",int(hit),a->mHealth);}
 }
 if(phase==5){
  if(dead2&&dead2->mPellet&&dead2->mDeadState==2){
   const int before=pc_p2_preview_pokos();
   const bool ok=pc_p2_preview_deliver(dead2->mPellet);
   const int after=pc_p2_preview_pokos();deliver2=int(ok);
   std::printf("P2_REWARD_DELIVER n=2 ok=%d pokos_before=%d pokos_after=%d\n",int(ok),before,after);
   dead2->mPellet->kill(false);phase=6;summaryFrame=observed;
  } else if(observed>=secondDeath+240){std::printf("P2_REWARD_FAIL no_corpse_2\n");std::fflush(stdout);std::_Exit(2);}
 }
 if(phase==6&&observed>=summaryFrame+30){
  std::printf("P2_REWARD_SUMMARY generator=%u deliver1=%d deliver2=%d pokos=%d corpses=%d\n",
              gen,deliver1,deliver2,pc_p2_preview_pokos(),pc_p2_preview_corpse_count());
  require(deliver1==1,"first Pod delivery failed");
  require(deliver2==1,"second Pod delivery failed");
  std::printf("PASS P2_REWARD_LIFECYCLE\n");std::fflush(stdout);std::_Exit(0);
 }
 std::fflush(stdout);return result;
}};
'''


def instrument(source):
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    if 'P2_REWARD_TARGET' in source:
        raise ValueError('Already instrumented')
    head = ('#include <cmath>\n#include <cstring>\n#include "Generator.h"\n'
            '#include "TekiPersonality.h"\n#include "Interactions.h"\n'
            '#include "pc_p2_preview.h"\n'
            '#include "Pcam/Camera.h"\n#include "Pcam/CameraManager.h"\n')
    text = head + source[:start] + APP + source[end:]
    anchor = 'if(!pc_window_init("P2 room integration fixture",960,720))return 3;'
    if anchor not in text:
        raise ValueError('missing fixture window-init anchor')
    window = (anchor + '\n{int laneW=960,laneH=540;const char* laneRoomWin=std::getenv("PIKMIN_P2_ROOM_WINDOW");'
              'bool laneSmall=true;'
              'if(laneRoomWin&&(!std::strcmp(laneRoomWin,"0")||!std::strcmp(laneRoomWin,"off")))laneSmall=false;'
              'else if(laneRoomWin&&std::sscanf(laneRoomWin,"%dx%d",&laneW,&laneH)!=2){laneW=960;laneH=540;}'
              'if(laneSmall){pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);'
              'pc_window_set_window_size(laneW,laneH);pc_window_center();'
              'std::printf("[PC Port] Experimental preview window set to %dx%d windowed and centered '
              '(override with PIKMIN_P2_ROOM_WINDOW=WxH or =off).\\n",laneW,laneH);std::fflush(stdout);}}')
    return text.replace(anchor, window)


def build(native, build_dir, output, head):
    native, build_dir, output = (Path(p).resolve() for p in (native, build_dir, output))
    output.mkdir(parents=True, exist_ok=False)
    room = output / 'room.cpp'
    room.write_text(instrument((native / 'tools/preview_p2_room.cpp').read_text()))
    record = builder.build_fixture(build_dir, native, room, output / 'baseline', head)
    exe = output / 'baseline' / 'fixture.exe'
    print(exe)
    return exe


def validate(text, code, ledger=None):
    receipts = re.findall(r'P2_POD_RECEIPT id=(\S+) value=(\d+) new=(\d) pokos=(\d+)', text)
    corpse = [r for r in receipts if r[0].startswith('corpse:')]
    checks = dict(
        completion=code == 0 and 'PASS P2_REWARD_LIFECYCLE' in text,
        targeted=bool(re.search(r'P2_REWARD_TARGET generator=\d+ pokos=\d+ corpses=\d+', text)),
        two_deaths=len(re.findall(r'P2_REWARD_DEATH n=', text)) == 2,
        two_deliveries=len(re.findall(r'P2_REWARD_DELIVER n=', text)) == 2,
        respawn=bool(re.search(r'P2_REWARD_RESPAWN', text)),
        reentry=bool(re.search(r'P2_REWARD_REENTRY reused=\d+', text)),
        corpse_receipts=len(corpse) == 2 and corpse[0][0] == corpse[1][0],
        first_new=bool(corpse) and corpse[0][2] == '1',
        second_duplicate=len(corpse) == 2 and corpse[1][2] == '0',
        pokos_stable=len(corpse) == 2 and corpse[0][3] == corpse[1][3],
        value_is_2=all(r[1] == '2' for r in corpse),
    )
    ledger_exact = False
    if ledger:
        lines = [line for line in ledger.splitlines() if line.strip()]
        try:
            header = lines.pop(0)
            rows = [line.split() for line in lines]
            ledger_exact = (header == 'P2_ECONOMY_1'
                            and len([r for r in rows if r[0].startswith('corpse:')]) == 1
                            and all(len(r) == 2 for r in rows))
        except (IndexError, ValueError):
            ledger_exact = False
    result = dict(passed=all(checks.values()) and ledger_exact, checks=checks,
                  ledger_exact=ledger_exact, receipts=receipts,
                  failures=re.findall(r'FAIL p2 room: (.*)', text),
                  injection='injected Pod delivery (no Pikmin carry route); camera framing + repeated '
                            'Navi InteractAttack(100000); respawn via the actor\'s own Generator::init()')
    return result


def run(assets, converted, pod, snow, exe, output, timeout=360):
    from experimental.pikmin2_snow_lifecycle import prepare as prepare_snow
    run_dir = prepare_snow(Path(assets).resolve(), Path(converted).resolve(),
                           Path(pod).resolve(), Path(snow).resolve(), Path(output).resolve())
    env = dict(os.environ, PATH=str(Path(exe).resolve().parent) + ';C:/msys64/mingw64/bin;'
               + os.environ.get('PATH', ''), SDL_AUDIODRIVER='dummy')
    log = run_dir / 'native.log'
    with log.open('w') as stream:
        try:
            code = subprocess.run([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                                  cwd=run_dir, env=env, stdout=stream,
                                  stderr=subprocess.STDOUT, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            code = 'timeout'
    text = log.read_text(errors='replace')
    ledger_path = run_dir / 'p2-economy.txt'
    evidence = validate(text, code, ledger_path.read_text() if ledger_path.exists() else None)
    evidence.update(exit_code=code, run=str(run_dir),
                    executable=builder.snapshot([Path(exe).resolve()]))
    (run_dir / 'reward-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(evidence, indent=2))
    return evidence


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    for name in ('native', 'build-dir', 'output'):
        b.add_argument('--' + name, type=Path, required=True)
    b.add_argument('--head', required=True)
    r = sub.add_parser('run')
    for name in ('assets', 'converted', 'pod', 'snow', 'exe', 'output'):
        r.add_argument('--' + name, type=Path, required=True)
    r.add_argument('--timeout', type=int, default=360)
    args = parser.parse_args()
    if args.command == 'build':
        build(args.native, args.build_dir, args.output, args.head)
    else:
        run(args.assets, args.converted, args.pod, args.snow, args.exe, args.output, args.timeout)
