"""Lane 16 Frog/MaroFrog corpse carry -> Onion delivery observation (#167/#201).

Reuses ``experimental.pikmin2_frog_runtime.build``/``run``. After preview
readiness the fixture reads the arena birth rows, lets the two registered frogs
(``201001`` Frog, ``201002`` MaroFrog) live through an observation window, then
injects the same two legal lethal ``InteractAttack`` calls the runtime fixture
uses to create native corpses. It then observes the ordinary P1 corpse-carry
path: the dead view's ``Pellet`` in ``pelletMgr``, the Pikmin that stick to it
(``getStickObject``/``mPikiCarrier``/``mCarrierCount``) and its passage to the
Onion (``Pellet::isAlive`` flips false at absorption). If P1 does not auto-carry
within a bounded window the fixture moves the surviving squad next to the corpse
once (logged assist) and never fabricates a delivery. No carry is reported as
``UNOBSERVED`` rather than PASS. See ``docs/PIKMIN2_FROG_RUNTIME_ACCEPTANCE.md``.
"""
import re

from experimental.pikmin2_frog_runtime import build as _build
from experimental.pikmin2_frog_runtime import run as _run

APP = r'''#include <cmath>
#include <algorithm>
#include "Piki.h"
#include "PikiMgr.h"
#include "Pellet.h"
#include "PelletView.h"
#include "PelletState.h"
class RoomApp : public PlugPikiApp {
 int frames=0,observed=0,corpseFrame=-1;
 Teki* frogs[2]={nullptr,nullptr};
 Pellet* corpse[2]={nullptr,nullptr};
 bool corpseSeen[2]={false,false};
 bool carried[2]={false,false};
 bool delivered[2]={false,false};
 bool injected=false,assisted=false,finished=false;
 int carryTicks[2]={0,0};
 float carryDistance[2]={0,0};
 Vector3f carryOrigin[2];
 int alivePikis(){int c=0;Iterator it(pikiMgr);CI_LOOP(it){Creature* p=*it;if(p&&p->isAlive()&&p->isPiki())++c;}return c;}
 int carriers(Pellet* pellet){int c=0;Iterator it(pikiMgr);CI_LOOP(it){Creature* p=*it;if(p&&p->isAlive()&&p->getStickObject()==static_cast<Creature*>(pellet))++c;}return c;}
 Pellet* findCorpse(Teki* actor){Pellet* found=nullptr;Iterator it(pelletMgr);CI_LOOP(it){Pellet* p=static_cast<Pellet*>(*it);if(p->isAlive()&&p->mPelletView==static_cast<PelletView*>(actor)){require(!found,"duplicate frog corpse");found=p;}}return found;}
 void assistSquad(){Creature* near=frogs[0];if(corpse[0])near=corpse[0];
  Vector3f t=near->getPosition();Navi* n=naviMgr->getNavi();if(n)n->mSRT.t=t;
  int idx=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(!p->isAlive())continue;
   const float a=6.28318530718f*float(idx)/8.0f;p->mSRT.t.set(t.x+10.0f*std::cos(a),t.y,t.z+10.0f*std::sin(a));p->mVelocity.set(0,0,0);p->mTargetVelocity.set(0,0,0);++idx;}
  std::printf("P2_FROG_CARRY_ASSIST moved=1 around=201001 pikis=%d\n",alivePikis());}
 void finish(const char* why){if(finished)return;finished=true;
  const int corpses=int(corpseSeen[0])+int(corpseSeen[1]);const int carry=int(carried[0]||carried[1]);const int deliver=int(delivered[0]||delivered[1]);
  std::printf("P2_FROG_CARRY_RESULT reason=%s corpses=%d carry=%d deliver=%d assisted=%d\n",why,corpses,carry,deliver,int(assisted));
  if(corpses==2&&carry&&deliver)std::printf("PASS P2_FROG_CARRY corpses=2 carry=1 deliver=1 assisted=%d\n",int(assisted));
  else std::printf("UNOBSERVED P2_FROG_CARRY corpses=%d carry=%d deliver=%d assisted=%d\n",corpses,carry,deliver,int(assisted));
  std::fflush(stdout);std::_Exit(0);}
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<9000,"frog carry timeout");
 if(frames%120==0){std::printf("P2_FROG_CARRY_GATE frame=%d ready=%d pause=%d ui=%d movie=%d pikis=%d\n",frames,int(pc_p2_preview_cargo_free_ready()),int(gameflow.mPauseAll),int(gameflow.mIsUIOverlayActive),int(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive),pikiMgr?alivePikis():0);std::fflush(stdout);}
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr||!pikiMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
 ++observed;
 if(observed==1){
  for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
  std::ifstream input("frog-positions.txt");unsigned id;int type,registered;float x,y,z;int count=0;
  while(input>>id>>type>>registered>>x>>y>>z){
   Teki* actor=nullptr;int matches=0;Iterator it(tekiMgr);CI_LOOP(it){Teki* a=static_cast<Teki*>(*it);if(a->mGenerator&&a->mGenerator->_70==id){actor=a;++matches;}}
   require(matches==1&&actor,"frog carry birth identity");Vector3f birth=actor->mPersonality->mPosition;
   require(std::fabs(birth.x-x)<.02&&std::fabs(birth.y-y)<.02&&std::fabs(birth.z-z)<.02,"frog carry birth XYZ");
   if(id==201001||id==201002){frogs[id-201001]=actor;require(bool(pc_p2_frog_name(static_cast<PelletView*>(actor))),"frog carry registration");}
   std::printf("P2_FROG_CARRY_BIRTH id=%u type=%d registered=%d x=%.3f y=%.3f z=%.3f\n",id,type,registered,birth.x,birth.y,birth.z);++count;}
  require(count==4&&frogs[0]&&frogs[1],"frog carry roster missing");std::fflush(stdout);}
 if(observed>=360&&!injected){
  injected=true;
  for(int i=0;i<2;++i){if(frogs[i]->isAlive()&&!frogs[i]->getTekiOption(BTeki::TEKI_OPTION_INVINCIBLE)){
   bool accepted=frogs[i]->stimulate(InteractAttack(n,nullptr,10000,false));
   std::printf("P2_FROG_INJECTED_ATTACK id=%d accepted=%d\n",201001+i,int(accepted));}
   else if(!frogs[i]->isAlive())std::printf("P2_FROG_NATURAL_DEATH id=%d\n",201001+i);}
  std::fflush(stdout);}
 for(int i=0;i<2;++i){
  if(!frogs[i])continue;
  if(corpse[i]&&!delivered[i]&&corpse[i]->isAlive()&&corpse[i]->mPelletView!=static_cast<PelletView*>(frogs[i]))corpse[i]=nullptr;
  if(!corpse[i])corpse[i]=findCorpse(frogs[i]);
  if(corpse[i]&&!corpseSeen[i]){corpseSeen[i]=true;if(corpseFrame<0)corpseFrame=frames;
   Vector3f p=corpse[i]->getPosition();std::printf("P2_FROG_CORPSE id=%d found=1 alive=%d state=%d x=%.3f y=%.3f z=%.3f\n",201001+i,int(corpse[i]->isAlive()),corpse[i]->getState(),p.x,p.y,p.z);std::fflush(stdout);}
  if(corpse[i]){
   int c=carriers(corpse[i]);
   bool carrying=corpse[i]->mPikiCarrier!=nullptr||corpse[i]->mCarrierCount>0||c>0;
   if(carrying&&!carried[i]){carried[i]=true;carryOrigin[i]=corpse[i]->getPosition();
    std::printf("P2_FROG_CARRY id=%d carried=1 carriers=%d strength=%d state=%d\n",201001+i,c,int(corpse[i]->mCarrierCount),corpse[i]->getState());std::fflush(stdout);}
   if(carried[i]&&!delivered[i]){
    ++carryTicks[i];Vector3f p=corpse[i]->getPosition();float dx=p.x-carryOrigin[i].x,dz=p.z-carryOrigin[i].z;float d=std::sqrt(dx*dx+dz*dz);if(d>carryDistance[i])carryDistance[i]=d;
    if(carryTicks[i]==1||carryTicks[i]%60==0)std::printf("P2_FROG_CARRY_TICK id=%d state=%d alive=%d strength=%d carriers=%d distance=%.3f x=%.3f y=%.3f z=%.3f\n",201001+i,corpse[i]->getState(),int(corpse[i]->isAlive()),int(corpse[i]->mCarrierCount),c,carryDistance[i],p.x,p.y,p.z);
    if(!corpse[i]->isAlive()){delivered[i]=true;std::printf("P2_FROG_DELIVER id=%d delivered=1 distance=%.3f state=%d\n",201001+i,carryDistance[i],corpse[i]->getState());std::fflush(stdout);}}}}
 bool both=corpseSeen[0]&&corpseSeen[1];
 if(both&&!assisted&&!carried[0]&&!carried[1]&&corpseFrame>=0&&frames>=corpseFrame+300){assisted=true;assistSquad();std::fflush(stdout);}
 if(both&&(carried[0]||carried[1])&&(delivered[0]||delivered[1]))finish("complete");
 else if(frames>=4800||(corpseFrame>=0&&frames>=corpseFrame+3600))finish("deadline");
 std::fflush(stdout);return result;
 }};
'''


def build(native, build_dir, output, head, resume=False):
    return _build(native, build_dir, output, head, resume, app=APP)


def run(assets, bank, output, exe):
    return _run(assets, bank, output, exe, validator=validate)


def validate(text, code):
    births = re.findall(r'P2_FROG_CARRY_BIRTH id=(\d+) type=(\d+) registered=(\d+)', text)
    corpses = sorted({i for i in re.findall(r'P2_FROG_CORPSE id=(\d+) found=1', text)})
    carry_ids = sorted({i for i in re.findall(r'P2_FROG_CARRY id=(\d+) carried=1', text)})
    deliver_ids = sorted({i for i in re.findall(r'P2_FROG_DELIVER id=(\d+) delivered=1', text)})
    injected = re.findall(r'P2_FROG_INJECTED_ATTACK id=(\d+) accepted=([01])', text)
    both_corpses = set(corpses) >= {'201001', '201002'}
    both = sorted(set(carry_ids) & set(deliver_ids))
    observed = both_corpses and bool(both)
    checks = dict(
        completion=code == 0 and 'PASS P2_FROG_CARRY ' in text,
        births=set(births) >= {('201001', '0', '1'), ('201002', '33', '1')},
        corpses=both_corpses,
        carry=bool(carry_ids),
        deliver=bool(deliver_ids),
        observed=observed,
    )
    return dict(passed=all(checks.values()), checks=checks, births=len(births),
                corpses=corpses, carry=carry_ids, deliver=deliver_ids, delivered=both,
                injected=[i for i, a in injected if a == '1'], assisted='P2_FROG_CARRY_ASSIST ' in text,
                unobserved=not observed)


if __name__ == '__main__':
    import argparse
    from pathlib import Path
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build'); r = sub.add_parser('run')
    for n in ('native', 'build-dir', 'output'):
        b.add_argument('--' + n, type=Path, required=True)
    b.add_argument('--head', required=True); b.add_argument('--resume', action='store_true')
    for n in ('assets', 'bank', 'output', 'exe'):
        r.add_argument('--' + n, type=Path, required=True)
    a = p.parse_args()
    if a.command == 'build':
        build(a.native, a.build_dir, a.output, a.head, a.resume)
    else:
        run(a.assets, a.bank, a.output, a.exe)
