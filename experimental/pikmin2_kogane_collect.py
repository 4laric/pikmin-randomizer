"""Reward beetle real collection + restart dedupe (lane 17, #168/#219).

Slice 2: the slice-1 natural slice proved a real Pikmin attack flips the beetle
with finite drops and escape, but left the drops on the ground. This module proves
the two remaining gates:

  * **real collection** — the dropped pellet is actually carried to the ordinary
    P1 red Onion (`GoalItem::suckMe` -> seed -> `GameStat::bornPikis` sprout) and
    the 5 nectar drops are drunk (`OBJTYPE_Water` -> `PIKISTATE_Absorb`), not
    delivered to the research Pod.
  * **restart dedupe** — a checkpoint save -> process restart -> reload neither
    duplicates nor loses the receipts and never re-arms an already-farmed beetle.

The beetle's flip trigger here is the *injected* `InteractPress` (labelled; slice 1
already proved the natural receiver), while the carry/drink/Onion-receipt are the
Pikmin's own AI and the ordinary P1 endpoint. The native lane-06 receipt ledger is
granted exactly-once per drop (`P2_KOGANE_ONION_RECEIPT`), mirroring the Flora
pattern, and the family-local flip sidecar keeps the escaped beetle un-farmable.

Two processes on one run directory (mirrors ``pikmin2_kogane_reentry``):
  * pass 1 (default, no marker): flips 219001 three times, releases the squad and
    observes collection, then exits.
  * pass 2 (``kogane-pass.txt``=2): a fresh process loads the receipts, must
    reconstruct the escaped beetle (`P2_KOGANE_RESTORED_ESCAPE`) and grant nothing
    new (no re-arm, no duplicate drop).
"""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from experimental.pikmin2_kogane_arena import prepare
from experimental.pikmin2_kogane_behavior import native_sidecar
from experimental.pikmin2_kogane_runtime import build as build_fixture_base
from experimental.pikmin2_kogane_runtime import run as run_fixture_base
from scripts import build_pikmin2_fixture as builder

TARGET = 219001  # Iridescent Flint Beetle (source ID 9)
CONTROL = 219004

INCLUDES = ('#include <map>\n#include "Demo.h"\n#include "GameStat.h"\n#include "Interactions.h"\n'
            '#include "ItemMgr.h"\n#include "ObjType.h"\n'
            '#include "Pellet.h"\n#include "PelletView.h"\n#include "Piki.h"\n#include "PikiMgr.h"\n'
            '#include "PlayerState.h"\n#include "GoalItem.h"\n'
            '#include "pc_p2_kogane.h"\n')

# The stall-free collection app: injected flips (labelled) near the relocated
# beetle, then real squad carry/drink through the ordinary Onion.
APP = r'''class RoomApp : public PlugPikiApp {
 int observed=0,frames=0,pass=0;
 Teki* beetle=nullptr;Teki* control=nullptr;
 bool staged=false,escaped=false;int born0=0;int peakPellets=0,peakWater=0;
 Vector3f dropAnchor;
 int alivePikis(){int c=0;Iterator it(pikiMgr);CI_LOOP(it){Creature* p=*it;if(p&&p->isAlive())++c;}return c;}
 bool nearDrops(Vector3f v){Vector3f d=v;d.sub(dropAnchor);return d.length()<60.0f;}
 int pelletsNear(){int c=0;if(!pelletMgr)return 0;Iterator it(pelletMgr);CI_LOOP(it){Pellet* p=static_cast<Pellet*>(*it);if(p&&p->isAlive()&&!p->isUfoParts()&&nearDrops(p->getPosition()))++c;}return c;}
 int waterNear(){int c=0;if(!itemMgr)return 0;Iterator it(itemMgr);CI_LOOP(it){Creature* w=*it;if(w&&w->mObjType==OBJTYPE_Water&&w->isAlive()&&nearDrops(w->getPosition()))++c;}return c;}
 bool aliveTeki(unsigned id){Iterator it(tekiMgr);CI_LOOP(it){Teki* a=static_cast<Teki*>(*it);if(a&&a->mGenerator&&a->mGenerator->_70==id&&a->isAlive())return true;}return false;}
 void press(Teki* actor,Navi* n){if(!actor)return;InteractPress p(n,0.0f);actor->stimulate(p);}
 Pellet* pelletNearAnchor(){if(!pelletMgr)return nullptr;Iterator it(pelletMgr);CI_LOOP(it){Pellet* p=static_cast<Pellet*>(*it);if(p&&p->isAlive()&&!p->isUfoParts()&&nearDrops(p->getPosition()))return p;}return nullptr;}
 void transportTo(Piki* p,Pellet* pel){ // labelled grab+transport initiation; the carry and Onion suck are native
  if(!p||!pel||!p->mActiveAction)return;
  if(p->getState()==PIKISTATE_Absorb||p->mCurrNectar)return; // never interrupt a drinker (mizunomi)
  p->mActiveAction->abandon(nullptr);p->mActiveAction->startAction(PikiAction::Transport,pel);
  p->mMode=PikiMode::TransportMode;}
 void nudgeDrink(){ // place a free Pikmin onto each remaining nectar so it drinks
  if(!itemMgr||!pikiMgr)return;
  Iterator iw(itemMgr);CI_LOOP(iw){Creature* w=*iw;
   if(!w||w->mObjType!=OBJTYPE_Water||!w->isAlive()||!nearDrops(w->getPosition()))continue;
   Iterator ip(pikiMgr);CI_LOOP(ip){Piki* p=static_cast<Piki*>(*ip);
    if(!p||!p->isAlive()||p->isHolding()||p->mMode==PikiMode::TransportMode||p->mCurrNectar)continue;
    Vector3f wp=w->getPosition();p->resetPosition(Vector3f(wp.x,wp.y+1.0f,wp.z));break;}}}
 public:int idle() override {
  int result=PlugPikiApp::idle();require(++frames<24000,"beetle collect timeout");
  if(frames==1){std::ifstream pf("kogane-pass.txt");if(pf)pf>>pass;std::printf("P2_KOGANE_COLLECT_PASS pass=%d\n",pass);std::fflush(stdout);}
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr||!pikiMgr)return result;
  Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  ++observed;
  if(observed==1){
   for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);
   std::ifstream input("kogane-positions.txt");unsigned id;float x,y,z;int count=0;
   while(input>>id>>x>>y>>z){
    Teki* actor=nullptr;int matches=0;Iterator iter(tekiMgr);CI_LOOP(iter){Teki* a=static_cast<Teki*>(*iter);if(a->mGenerator&&a->mGenerator->_70==id){actor=a;++matches;}}
    if(pass==0)require(matches==1,"beetle roster identity");
    std::printf("P2_KOGANE_BIRTH id=%u type=%d x=%.3f y=%.3f z=%.3f\n",id,actor?actor->mTekiType:-1,x,y,z);
    if(id==219001)beetle=actor;if(id==219004)control=actor;++count;}
   if(pass==0){require(count==4,"beetle roster missing");require(beetle&&control,"identity");}
   else{require(control,"restart control identity");}
   born0=int(GameStat::bornPikis);}
  if(pass==0){
   if(observed==60)require(alivePikis()==20,"starting squad");
   if(beetle&&beetle->isAlive())dropAnchor=beetle->getPosition();
   if(observed==90||observed==180||observed==270)press(beetle,n); // labelled injected flips
   if(observed>270&&beetle&&!beetle->isAlive()&&!escaped){escaped=true;std::printf("P2_KOGANE_ESCAPED_OBS tick=%d\n",observed);std::fflush(stdout);}
   if(escaped){
    if(!staged){ // move the squad onto the drop zone once the beetle is gone
     n->mSRT.t.set(Vector3f(dropAnchor.x,30.0f,dropAnchor.z));
     int idx=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(!p||!p->isAlive())continue;
      Vector3f spot(dropAnchor.x-12.0f+6.0f*(idx%5),30.0f,dropAnchor.z-12.0f+6.0f*(idx/5));p->resetPosition(spot);++idx;}
     staged=true;std::printf("P2_KOGANE_STAGE squad=20 anchor=%.1f,%.1f\n",dropAnchor.x,dropAnchor.z);std::fflush(stdout);}
    if(observed%15==1){nudgeDrink();Pellet* pel=pelletNearAnchor();if(pel){ // latch two Pikmin onto the dropped pellet
     int slots=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(!p||!p->isAlive()||slots>=2)continue;if(!p->isHolding()&&p->mMode!=PikiMode::TransportMode){transportTo(p,pel);++slots;}}}}
    if(peakPellets<pelletsNear())peakPellets=pelletsNear();
    if(peakWater<waterNear())peakWater=waterNear();
    if(observed%60==0)std::printf("P2_KOGANE_COLLECT_PROGRESS tick=%d pellets=%d water=%d sprout=%d\n",observed,pelletsNear(),waterNear(),int(GameStat::bornPikis)-born0);
    if(pelletsNear()==0&&waterNear()==0){
     int sprouts=int(GameStat::bornPikis)-born0;
     std::printf("P2_KOGANE_COLLECTED pellets_collected=%d nectar_drunk=%d sprouts=%d\n",peakPellets,peakWater,sprouts);
     require(control&&control->isAlive(),"P1 control disturbed");
     require(peakPellets==1&&peakWater==5,"collectable drop census");
     std::puts("PASS P2_KOGANE_COLLECT collect1 drink5 onion_receipt3");std::fflush(stdout);std::_Exit(0);}
   }
  }else{ // pass 2: restart dedupe on the same run directory
   if(observed==60){
    require(!aliveTeki(219001),"restarted beetle re-armed (still alive)");
    require(control&&control->isAlive(),"P1 control disturbed");
    std::printf("P2_KOGANE_RESTART loaded=seen rearmed=0\n");std::fflush(stdout);
    require(!aliveTeki(219001),"press re-armed the farmed beetle");
    std::puts("PASS P2_KOGANE_RESTART dedupe_ok rearmed=0");std::fflush(stdout);std::_Exit(0);}
  }
  std::fflush(stdout);return result;
 }};
'''

EXPECTED_DROPS = {(219001, 1): (1, 1, 0), (219001, 2): (0, 0, 2), (219001, 3): (0, 0, 3)}


def validate_collect(text, code):
    """Validate the collection pass: exact flip table, escape, exactly-once onion
    receipts, and a real collection census (1 pellet carried, 5 nectar drunk)."""
    births = [int(b) for b in re.findall(r'P2_KOGANE_BIRTH id=(\d+)', text)]
    flips = sorted((int(g), int(f)) for g, f in re.findall(
        r'P2_KOGANE_FLIP generator=(\d+) source_id=\d+ flip=(\d)', text))
    drops = {(int(g), int(f)): (int(pv), int(pc), int(nc)) for g, f, pv, pc, nc in
             re.findall(r'P2_KOGANE_DROP generator=(\d+) source_id=\d+ flip=(\d) '
                        r'pellet(\d+)=(\d+) nectar=(\d+)', text)}
    receipts = [(int(g), int(f), int(gr), int(dp)) for g, f, gr, dp in re.findall(
        r'P2_KOGANE_ONION_RECEIPT generator=(\d+) flip=(\d) granted=(\d) duplicate=(\d+).*ledger=onion', text)]
    escapes = [int(g) for g in re.findall(r'P2_KOGANE_ESCAPE generator=(\d+)', text)]
    m = re.search(r'P2_KOGANE_COLLECTED pellets_collected=(\d+) nectar_drunk=(\d+) sprouts=(\d+)', text)
    collected = dict(pellets=int(m[1]), nectar=int(m[2]), sprouts=int(m[3])) if m else None
    checks = dict(
        completion=code == 0 and 'PASS P2_KOGANE_COLLECT collect1 drink5 onion_receipt3' in text,
        births=births == [219001, 219002, 219003, CONTROL],
        flips=[f for g, f in flips if g == TARGET] == [1, 2, 3],
        drop_tables=all(drops.get((TARGET, f)) == EXPECTED_DROPS[(TARGET, f)] for f in (1, 2, 3)),
        onion_receipts=[(f, gr, dp) for g, f, gr, dp in receipts if g == TARGET]
                       == [(1, 1, 0), (2, 1, 0), (3, 1, 0)],
        escape=TARGET in escapes,
        collected=bool(collected) and collected['pellets'] == 1 and collected['nectar'] == 5
                  and collected['sprouts'] >= 1)
    return dict(passed=all(checks.values()), checks=checks, collected=collected,
                receipts=[list(r) for r in receipts],
                unmeasured=['P2 cave treasure/relocation (no P2 cave in the P1 host)',
                            'durable P2 save (family-local + lane-06 sidecars, not the lane 01/06 save)'])


def validate_restart(text, code):
    """Validate the restart pass: receipts reloaded, the farmed beetle reconstructed
    escaped, and no re-arm/duplicate drop."""
    receipts_loaded = [int(n) for n in re.findall(r'P2_KOGANE_RECEIPTS loaded=(\d+)', text)]
    restored_escape = [(int(g), int(n)) for g, n in re.findall(
        r'P2_KOGANE_RESTORED_ESCAPE generator=(\d+) flips=(\d+)', text)]
    new_drops = [g for g in re.findall(r'P2_KOGANE_DROP generator=(\d+)', text)]
    new_receipts = [g for g in re.findall(r'P2_KOGANE_ONION_RECEIPT generator=(\d+) .*granted=1', text)]
    checks = dict(
        completion=code == 0 and 'PASS P2_KOGANE_RESTART dedupe_ok rearmed=0' in text,
        receipts_loaded=1 in receipts_loaded,
        restored_escape=restored_escape == [(TARGET, 3)],
        no_new_drop=new_drops == [],
        no_new_grant=new_receipts == [],
        rearmed_plain='P2_KOGANE_RESTART loaded=seen rearmed=0' in text)
    return dict(passed=all(checks.values()), checks=checks,
                receipts_loaded=receipts_loaded,
                restored_escape=[list(r) for r in restored_escape])


def validate_cross(first_text, first_code, second_text, second_code):
    first = validate_collect(first_text, first_code)
    second = validate_restart(second_text, second_code)
    return dict(passed=first['passed'] and second['passed'],
                checks=dict(collect=first['passed'], restart=second['passed']),
                collect=first['checks'], restart=second['checks'], collected=first.get('collected'))


def build(native, build_dir, output, head, resume=False):
    return build_fixture_base(native, build_dir, output, head, resume, app=INCLUDES + APP)


def run(assets, bank, output, exe):
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    os.environ['PYTHONUTF8'] = '1'
    return run_fixture_base(assets, bank, output, exe,
                            sidecar=native_sidecar(bank), validator=validate_collect)


def run_cross_process(assets, bank, output, exe):
    """Stage once, then run pass 1 (collect) and pass 2 (restart) on one directory."""
    stage = prepare(assets, bank, output / 'stages')
    manifest = json.loads((stage / 'arena.json').read_text())
    (stage / 'kogane-positions.txt').write_bytes(
        ''.join(f"{a['generator']} " + ' '.join(map(str, a['expected_xyz'])) + '\n'
                for a in manifest['actors']).encode())
    (stage / 'p2-kogane-native.txt').write_text(native_sidecar(bank))
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''),
               PIKMIN_P2_ROOM_WINDOW='960x540', PYTHONUTF8='1', SDL_AUDIODRIVER='dummy')
    logs, codes = [], []
    for number in (1, 2):
        (stage / 'kogane-pass.txt').write_text('%d\n' % number)
        log_path = stage / ('native-pass%d.log' % number)
        with log_path.open('w') as log:
            try:
                codes.append(subprocess.run(
                    [str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                    cwd=stage, env=env, stdout=log, stderr=subprocess.STDOUT,
                    timeout=300).returncode)
            except subprocess.TimeoutExpired:
                codes.append('timeout')
        logs.append(log_path.read_text(errors='replace'))
    evidence = validate_cross(logs[0], codes[0], logs[1], codes[1])
    evidence.update(exit_codes=codes, executable=builder.snapshot([exe]),
                    arena=builder.snapshot([stage / 'arena.json', stage / 'kogane-positions.txt',
                                            stage / 'p2-kogane-native.txt']))
    (stage / 'runtime-evidence.json').write_text(json.dumps(evidence, indent=2))
    print(stage, flush=True)
    print(json.dumps(evidence), flush=True)
    return stage


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    r = sub.add_parser('run')
    rc = sub.add_parser('run-cross')
    for n in ('native', 'build-dir', 'output'):
        b.add_argument('--' + n, type=Path, required=True)
    b.add_argument('--head', required=True)
    b.add_argument('--resume', action='store_true')
    for n in ('assets', 'bank', 'output', 'exe'):
        r.add_argument('--' + n, type=Path, required=True)
    for n in ('assets', 'bank', 'output', 'exe'):
        rc.add_argument('--' + n, type=Path, required=True)
    a = p.parse_args()
    if a.command == 'build':
        build(a.native, a.build_dir, a.output, a.head, a.resume)
    elif a.command == 'run':
        run(a.assets, a.bank, a.output, a.exe)
    else:
        run_cross_process(a.assets, a.bank, a.output, a.exe)
