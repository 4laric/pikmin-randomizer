"""Receivers-lane diagnostic for the batch-3 dweevil zero-damage result (#408).

Reuses the batch-3 private fixture harness (:mod:`experimental.pikmin2_batch2_runtime`)
but replaces the instrumented ``RoomApp`` with a receiver-focused probe that
records, per injected ``InteractAttack`` frame, the placement-vehicle TAI state,
the queued ``mStoredDamage`` and ``mHealth``. This distinguishes "the receiver
accepted the attack" from "the damage was applied", which is the exact ambiguity
behind the recorded batch-3 "accepted but health stays 130" result.

The probe also counts live starting Pikmin in the real ``pikiMgr`` so the
mandatory fixture-adoption squad check has machine-readable evidence.
"""
import argparse
import re
from pathlib import Path

import experimental.pikmin2_batch2_runtime as base

APP = r'''class RoomApp : public PlugPikiApp {
 int frames=0,observed=0,familyCount=0,target=-1,retarget=0;bool done=false;
 unsigned ids[8]={},controlId=0;Vector3f first[8];
 Teki* find(unsigned id){Iterator iter(tekiMgr);CI_LOOP(iter){Teki* a=static_cast<Teki*>(*iter);if(a->mGenerator&&a->mGenerator->_70==id)return a;}return nullptr;}
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<20000,"recv startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr||!mapMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
 ++observed;
 if(observed==1){
  for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
  std::ifstream input("p2-batch2-positions.txt");unsigned id;int type,registered;float x,y,z;
  while(input>>id>>type>>registered>>x>>y>>z){
   Teki* actor=find(id);
   require(actor,"recv roster identity");
   require(actor->mTekiType==type,"recv native type");
   Vector3f birth=actor->mPersonality->mPosition,gen=actor->mGenerator->getPos();
   require(std::fabs(birth.x-x)<.02&&std::fabs(birth.y-y)<.02&&std::fabs(birth.z-z)<.02,"recv birth XYZ");
   require(actor->isAlive(),"recv actor not alive");
   if(registered){require(familyCount<8,"recv family overflow");ids[familyCount]=id;first[familyCount]=actor->mSRT.t;++familyCount;}
   else{require(controlId==0,"recv duplicate control");controlId=id;}
   std::printf("P2_BATCH2_BIRTH id=%u type=%d registered=%d x=%.3f y=%.3f z=%.3f\n",id,type,registered,birth.x,birth.y,birth.z);}
  require(familyCount>=1&&controlId!=0,"recv roster incomplete");
  int pikis=0,reds=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* v=static_cast<Piki*>(*p);if(v->isAlive()){++pikis;if(v->mColor==Red)++reds;}}
  std::printf("P2_RECV_SQUAD alive=%d reds=%d\n",pikis,reds);
  require(cameraMgr&&cameraMgr->mCamera,"recv camera missing");
  Teki* t=find(ids[0]);require(t,"recv camera actor missing");
  cameraMgr->mCamera->setTarget(t);cameraMgr->mCamera->mControlsEnabled=false;
  std::printf("P2_BATCH2_CAMERA target_actor=%u\n",ids[0]);
 }
 if(observed%60==0&&observed<=300){for(int k=0;k<familyCount;++k){Teki* t=find(ids[(retarget++)%familyCount]);if(t){cameraMgr->mCamera->setTarget(t);break;}}}
 if(observed==150){
  for(int i=0;i<familyCount;++i){Teki* actor=find(ids[i]);
   if(!actor||!actor->isAlive()){std::printf("P2_BATCH2_MOVE id=%u dx=0.000 dz=0.000 dist=-1.000\n",ids[i]);continue;}
   Vector3f now=actor->mSRT.t;float dx=now.x-first[i].x,dz=now.z-first[i].z;
   std::printf("P2_BATCH2_MOVE id=%u dx=%.3f dz=%.3f dist=%.3f\n",ids[i],dx,dz,std::hypot(dx,dz));}
  std::fflush(stdout);
 }
 if(observed>=200&&observed<360){
  if(target<0){for(int i=0;i<familyCount;++i){Teki* a=find(ids[i]);
   if(a&&a->isAlive()&&a->mTekiType==TEKI_Chappy&&!a->getTekiOption(BTeki::TEKI_OPTION_INVINCIBLE)){target=i;break;}}}
  if(target>=0){Teki* a=find(ids[target]);
   if(a&&a->isAlive()){const int inv=int(a->getTekiOption(BTeki::TEKI_OPTION_INVINCIBLE));
    const bool hit=a->stimulate(InteractAttack(n,nullptr,100000,false));
    std::printf("P2_RECV_ATTACK id=%u accepted=%d health=%.1f stored=%.1f state=%d motion=%d invincible=%d observed=%d\n",
                ids[target],int(hit),a->mHealth,a->mStoredDamage,int(a->mStateID),a->mTekiAnimator->getCurrentMotionIndex(),inv,observed);
    std::fflush(stdout);}
  }
 }
 if(observed==380){
  Teki* c=find(controlId);
  if(c&&c->isAlive()){
   const int was=int(c->getTekiOption(BTeki::TEKI_OPTION_INVINCIBLE));
   c->setTekiOption(BTeki::TEKI_OPTION_INVINCIBLE);
   const float before=c->mHealth;
   const bool hit=c->stimulate(InteractAttack(n,nullptr,100000,false));
   c->clearTekiOption(BTeki::TEKI_OPTION_INVINCIBLE);
   std::printf("P2_RECV_IMMUNITY id=%u pre_invincible=%d accepted=%d health_before=%.1f health_after=%.1f\n",
               controlId,was,int(hit),before,c->mHealth);
   std::fflush(stdout);
  }
 }
 if(observed==400){
  int alive=0,moved=0,corpses=0;
  for(int i=0;i<familyCount;++i){Teki* a=find(ids[i]);if(!a)continue;
   if(a->isAlive())++alive;
   Vector3f now=a->mSRT.t;if(std::hypot(now.x-first[i].x,now.z-first[i].z)>=1.f)++moved;}
  Iterator p(pelletMgr);CI_LOOP(p){Pellet* body=static_cast<Pellet*>(*p);if(!body->isAlive())continue;
   for(int i=0;i<familyCount;++i){Teki* a=find(ids[i]);if(a&&body->mPelletView==static_cast<PelletView*>(a)){++corpses;break;}}}
  Teki* c=find(controlId);int controlAlive=int(c&&c->isAlive());
  std::printf("P2_BATCH2_LIFECYCLE family=%d alive=%d moved=%d corpses=%d control=%d\n",familyCount,alive,moved,corpses,controlAlive);
  require(moved>=1,"recv no autonomous movement");
  require(controlAlive==1,"recv control died");
  std::puts("PASS P2_RECEIVERS_RUNTIME");std::fflush(stdout);std::_Exit(0);
 }
 std::fflush(stdout);return result;
}};
'''


def instrument(source):
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    if 'P2_RECV_SQUAD' in source:
        raise ValueError('Already instrumented')
    return ('#include <fstream>\n#include <cmath>\n#include "Generator.h"\n'
            '#include "TekiPersonality.h"\n#include "Interactions.h"\n'
            '#include "pc_p2_batch2.h"\n#include "Pcam/Camera.h"\n'
            '#include "Pcam/CameraManager.h"\n'
            + source[:start] + APP + source[end:])


base.instrument = instrument


def readings(text):
    """Parse the receivers probe: squad, queued attack, immunity gate."""
    squad = re.findall(r'P2_RECV_SQUAD alive=(\d+) reds=(\d+)', text)
    attacks = re.findall(
        r'P2_RECV_ATTACK id=(\d+) accepted=(\d) health=(-?[\d.]+) '
        r'stored=(-?[\d.]+) state=(-?\d+) motion=(-?\d+) invincible=(\d)', text)
    immunity = re.findall(
        r'P2_RECV_IMMUNITY id=(\d+) pre_invincible=(\d) accepted=(\d) '
        r'health_before=(-?[\d.]+) health_after=(-?[\d.]+)', text)
    return squad, attacks, immunity


def validate(text, code):
    """Gate the receiver paths from a private run log (see docs/PIKMIN2_RECEIVER_PATHS.md)."""
    squad, attacks, immunity = readings(text)
    healths = [float(a[2]) for a in attacks]
    checks = dict(
        completion=code == 0 and 'PASS P2_RECEIVERS_RUNTIME' in text,
        squad_live=bool(squad) and int(squad[0][0]) > 0 and int(squad[0][1]) > 0,
        attack_queued=any(int(a[1]) == 1 and float(a[3]) > 0 for a in attacks),
        damage_applied=any(h <= 0.0 for h in healths),
        immunity_gate=bool(immunity) and immunity[0][2] == '0'
                      and float(immunity[0][3]) == float(immunity[0][4]),
    )
    return dict(passed=all(checks.values()), checks=checks,
                squad=squad, attacks=attacks, immunity=immunity,
                scope='Proxy-host receiver proof only; source P2 FSM/receivers stay BLOCKED.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    r = sub.add_parser('run')
    for name in ('native', 'build-dir', 'output'):
        b.add_argument('--' + name, type=Path, required=True)
    b.add_argument('--head', required=True)
    b.add_argument('--resume', action='store_true')
    r.add_argument('--family', choices=sorted(base.FAMILIES), required=True)
    for name in ('assets', 'imported', 'output', 'exe'):
        r.add_argument('--' + name, type=Path, required=True)
    r.add_argument('--timeout', type=int, default=150)
    args = parser.parse_args()
    if args.command == 'build':
        base.build(args.native, args.build_dir, args.output, args.head, args.resume)
    else:
        base.run(args.assets, args.imported, args.family, args.output, args.exe, args.timeout)
