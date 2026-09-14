"""Reward beetle natural press receiver (lane 17, #168/#219).

The accepted batch-4 behavior fixture (``pikmin2_kogane_behavior``) drives the
flip/drop/escape cycle with injected ``InteractPress`` stimuli. This slice proves
the *natural receiver* instead: a real Pikmin attack on a registered beetle now
routes to the flip in ``native/pc_port/pc_p2_kogane.cpp``
(``pc_p2_kogane_attacked``), so no press/attack stimulus is injected anywhere in
this fixture.

The RoomApp issues the engine's own C-stick transition — ``TopAction::abandon`` +
``startAction(PikiAction::Attack, beetle)`` + ``PikiMode::AttackMode`` — which is
exactly what ``piki.cpp`` does when the player releases a Pikmin at a target. From
there the Pikmin approach, attack-animation timing and the ``InteractAttack``
stimulus are the Pikmin's own AI; the beetle's flip, frame-7 drop, finite cap and
escape are all native. To keep the wandering beetle under a landing the fixture
re-co-locates up to four squad Pikmin next to it (equivalent to repeated successful
C-stick throws) and re-issues the attack command whenever one falls out of
``AttackMode``; that is the only intervention and it is labelled, never an injected
health/interaction write.

Acceptance markers asserted: ``P2_KOGANE_NATURAL_ATTACK generator=219001`` (the new
native log), the three finite ``P2_KOGANE_FLIP``/``P2_KOGANE_DROP`` rows for
Iridescent Flint Beetle (source ID 9), the source escape after the third flip and a
live P1 control. See ``docs/PIKMIN2_KOGANE_NATURAL.md``.
"""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from experimental.pikmin2_kogane_arena import prepare
from experimental.pikmin2_kogane_behavior import EXPECTED_DROPS, native_sidecar
from experimental.pikmin2_kogane_runtime import build as build_fixture_base
from experimental.pikmin2_kogane_runtime import run as run_fixture_base
from scripts import build_pikmin2_fixture as builder

IDS = (219001, 219002, 219003)
TARGET = 219001  # Iridescent Flint Beetle (source ID 9)
SPECIES_ID = {219001: 9, 219002: 10, 219003: 11}

APP = r'''class RoomApp : public PlugPikiApp {
 int observed=0,frames=0;
 Teki* beetle=nullptr;Teki* control=nullptr;
 Piki* attackers[5]={nullptr,nullptr,nullptr,nullptr,nullptr};
 bool escaped=false;int censusOnce=0;
 std::map<Piki*,Vector3f> pin; // the observing squad is pinned clear of the drop zone
 int alivePikis(){int c=0;Iterator it(pikiMgr);CI_LOOP(it){Creature* p=*it;if(p&&p->isAlive())++c;}return c;}
 bool aliveTeki(unsigned id){Iterator it(tekiMgr);CI_LOOP(it){Teki* a=static_cast<Teki*>(*it);if(a&&a->mGenerator&&a->mGenerator->_70==id&&a->isAlive())return true;}return false;}
 bool isAttacker(Piki* q){for(int i=0;i<5;++i)if(attackers[i]==q)return true;return false;}
 void command(Piki* p,int idx){
  if(!p||!beetle||!p->isAlive()||beetle->mDeadState!=0)return;
  Vector3f b=beetle->getPosition();
  Vector3f spot(b.x-40.0f+4.0f*idx,b.y,b.z+(idx-2)*6.0f); // far side away from Wealty/Fart
  p->resetPosition(spot);p->mVelocity.set(0,0,0);p->mTargetVelocity.set(0,0,0);
  if(p->mActiveAction){p->mActiveAction->abandon(nullptr);p->mActiveAction->startAction(PikiAction::Attack,beetle);}
  p->mMode=PikiMode::AttackMode;
 }
 void requeue(){ // re-issue the attack (no teleport), never interrupt a drinking Pikmin
  for(int i=0;i<5;++i){Piki* p=attackers[i];
   if(!p||!p->isAlive()||!beetle||!beetle->isAlive())continue;
   if(p->mMode!=PikiMode::AttackMode&&p->getState()!=PIKISTATE_Absorb&&!p->mCurrNectar){
    if(p->mActiveAction){p->mActiveAction->abandon(nullptr);p->mActiveAction->startAction(PikiAction::Attack,beetle);}
    p->mMode=PikiMode::AttackMode;}}
 }
 void naturalProgress(){std::printf("P2_KOGANE_NATURAL_PROGRESS tick=%d beetle_alive=%d control_alive=%d squad=%d\n",observed,int(beetle&&beetle->isAlive()),int(aliveTeki(219004)),alivePikis());std::fflush(stdout);}
 public:int idle() override {
  int result=PlugPikiApp::idle();require(++frames<20000,"beetle natural timeout");
  if(frames%120==0){std::printf("P2_KOGANE_GATE frame=%d pause=%d ui=%d ready=%d all=%d dead=%d\n",frames,int(gameflow.mPauseAll),int(gameflow.mIsUIOverlayActive),int(pc_p2_preview_cargo_free_ready()),int(GameStat::allPikis),int(GameStat::deadPikis));std::fflush(stdout);}
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr||!pikiMgr)return result;
  Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  ++observed;
  if(observed==1){
   for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i); // suppress one-shot discovery cutscenes
   std::ifstream input("kogane-positions.txt");unsigned id;float x,y,z;int count=0;
   while(input>>id>>x>>y>>z){
    Teki* actor=nullptr;int matches=0;Iterator iter(tekiMgr);CI_LOOP(iter){Teki* a=static_cast<Teki*>(*iter);if(a->mGenerator&&a->mGenerator->_70==id){actor=a;++matches;}}
    require(matches==1,"beetle roster identity");
    Vector3f birth=actor->mPersonality->mPosition;
    require(std::fabs(birth.x-x)<.02&&std::fabs(birth.y-y)<.02&&std::fabs(birth.z-z)<.02,"beetle birth XYZ");
    std::printf("P2_KOGANE_BIRTH id=%u type=%d x=%.3f y=%.3f z=%.3f\n",id,actor->mTekiType,birth.x,birth.y,birth.z);
    if(id==219001)beetle=actor;if(id==219004)control=actor;++count;}
   require(count==4,"beetle roster missing");
   require(beetle&&control&&beetle!=control,"beetle/control identity");}
  if(observed==60)require(alivePikis()==20,"starting squad size");
  // Pin every observing squad Pikmin clear of the drop zone so only the five
  // commanded attackers engage the beetle and no Pikmin drinks a drop.
  {Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(!p||!p->isAlive()||isAttacker(p))continue;
   if(pin.find(p)==pin.end())pin[p]=Vector3f(-240.0f+5.0f*(pin.size()%10),30.0f,1790.0f-5.0f*(pin.size()/10));
   p->mSRT.t.set(pin[p]);p->mVelocity.set(0,0,0);p->mTargetVelocity.set(0,0,0);}}
  if(observed==80){ // issue the C-stick style attack commands against the Kogane
   int idx=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(!p||!p->isAlive()||idx>=5)continue;attackers[idx]=p;command(p,idx);++idx;}
   std::printf("P2_KOGANE_NATURAL_COMMAND attackers=%d\n",idx);std::fflush(stdout);}
  // Keep up to five Pikmin latched while the beetle is present; re-issue the
  // attack command only when one falls out of AttackMode (and never mid-drink).
  if(beetle&&beetle->isAlive()&&observed>80&&observed%12==1)requeue();
  if(beetle&&!beetle->isAlive()&&!escaped){
   escaped=true;
   std::printf("P2_KOGANE_NATURAL_ESCAPED tick=%d beetle_alive=0\n",observed);std::fflush(stdout);}
  if(observed%60==0)naturalProgress();
  if(escaped){
   if(++censusOnce==1){ // one tick later, after all three drops are on the ground
    int pellets=0,nectar=0;
    Iterator ip(pelletMgr);CI_LOOP(ip){Creature* p=*ip;if(p&&p->isAlive())++pellets;}
    if(itemMgr){Iterator iw(itemMgr);CI_LOOP(iw){Creature* w=*iw;if(w&&w->mObjType==OBJTYPE_Water&&w->isAlive())++nectar;}}
    std::printf("P2_KOGANE_NATURAL_CENSUS pellets=%d nectar=%d pikis=%d\n",pellets,nectar,alivePikis());std::fflush(stdout);
    require(control&&control->isAlive(),"P1 control disturbed");
    require(alivePikis()>=1,"squad extinct");
    std::puts("PASS P2_KOGANE_NATURAL natural_attack flip3 escape1 control_alive");std::fflush(stdout);std::_Exit(0);}}
  std::fflush(stdout);return result;
 }};
'''

INCLUDES = ('#include <map>\n#include "Demo.h"\n#include "GameStat.h"\n#include "Interactions.h"\n'
            '#include "ItemMgr.h"\n#include "ObjType.h"\n'
            '#include "Pellet.h"\n#include "PelletView.h"\n#include "Piki.h"\n#include "PikiMgr.h"\n'
            '#include "PikiAI.h"\n#include "PlayerState.h"\n'
            '#include "pc_p2_kogane.h"\n')

EXPECTED_HEALTH = {219001: '1000.0'}


def validate_natural(text, code):
    """Validate a natural-attack run: real Pikmin attacks flip ID 9 once per damage
    clip, drop exactly the audited table and escape on the third flip, with no
    injected stimulus and a live control."""
    naturals = sorted((int(g), int(f)) for g, f in re.findall(
        r'P2_KOGANE_NATURAL_ATTACK generator=(\d+) source_id=\d+ flip=(\d)', text))
    flips = sorted((int(g), int(f)) for g, f in re.findall(
        r'P2_KOGANE_FLIP generator=(\d+) source_id=\d+ flip=(\d)', text))
    drops = {(int(g), int(f)): (int(pv), int(pc), int(nc)) for g, f, pv, pc, nc in
             re.findall(r'P2_KOGANE_DROP generator=(\d+) source_id=\d+ flip=(\d) '
                        r'pellet(\d+)=(\d+) nectar=(\d+)', text)}
    escapes = sorted(int(g) for g in re.findall(r'P2_KOGANE_ESCAPE generator=(\d+)', text))
    births = [int(b) for b in re.findall(r'P2_KOGANE_BIRTH id=(\d+)', text)]
    m = re.search(r'P2_KOGANE_NATURAL_CENSUS pellets=(\d+) nectar=(\d+) pikis=(\d+)', text)
    census = dict(pellets=int(m[1]), nectar=int(m[2]), pikis=int(m[3])) if m else None
    # ID 9 (Kogane): flip1 1x 1-pellet, flip2 2 nectar, flip3 3 nectar (spray fallback).
    kogane = {f: EXPECTED_DROPS[(TARGET, f)] for f in (1, 2, 3)}
    target_flips = [f for g, f in flips if g == TARGET]
    target_naturals = [f for g, f in naturals if g == TARGET]
    checks = dict(
        completion=code == 0 and 'PASS P2_KOGANE_NATURAL natural_attack flip3 escape1 control_alive' in text,
        births=births == list(IDS) + [219004],
        command='P2_KOGANE_NATURAL_COMMAND' in text,
        natural_attacks=target_naturals == [1, 2, 3],
        flips=target_flips == [1, 2, 3],
        drop_tables=all(drops.get((TARGET, f)) == kogane[f] for f in (1, 2, 3)),
        escape=TARGET in escapes,
        census=bool(census) and census['pikis'] >= 1)
    return dict(passed=all(checks.values()), checks=checks, census=census,
                naturals=[list(n) for n in naturals],
                flips=[list(f) for f in flips],
                drops={f'{g}:{f}': list(v) for (g, f), v in sorted(drops.items())},
                unmeasured=['real collection into the Onion (pellets/nectar persist; carry not observed)',
                            'cave relocation (no P2 cave in the P1 host)',
                            'treasure override (disabled: no P2 treasure in P1 host)'])


def build(native, build_dir, output, head, resume=False):
    return build_fixture_base(native, build_dir, output, head, resume, app=INCLUDES + APP)


def run(assets, bank, output, exe):
    # Standard acceptance launch: 960x540 centred window, UTF-8, dummy audio.
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    os.environ['PYTHONUTF8'] = '1'
    return run_fixture_base(assets, bank, output, exe,
                            sidecar=native_sidecar(bank), validator=validate_natural)


def instrument(source):
    from experimental.pikmin2_kogane_runtime import instrument as base
    return base(source, INCLUDES + APP)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    r = sub.add_parser('run')
    for n in ('native', 'build-dir', 'output'):
        b.add_argument('--' + n, type=Path, required=True)
    b.add_argument('--head', required=True)
    b.add_argument('--resume', action='store_true')
    for n in ('assets', 'bank', 'output', 'exe'):
        r.add_argument('--' + n, type=Path, required=True)
    a = p.parse_args()
    if a.command == 'build':
        build(a.native, a.build_dir, a.output, a.head, a.resume)
    else:
        run(a.assets, a.bank, a.output, a.exe)
