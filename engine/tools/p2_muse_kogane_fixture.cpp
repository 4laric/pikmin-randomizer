// P2 Muse-Kogane natural-throw acceptance fixture (lane 54, #494).
//
// Acceptance run for Kogane source ID 9 gate 3 (attacks/receivers) through a
// real thrown-Pikmin / player-controller event path. The captain is staged
// ONCE beside the beetle; every flip trigger is a genuine engine throw-release
// event pair -- Piki transit to PIKISTATE_Flying plus Navi::throwPiki toward
// the beetle's live position -- identical to the KEY_Action0 release sequence
// in NaviThrowState::procAnimMsg. After release the Pikmin flies ballistically
// under its own physics, lands, and its own attack AI engages the beetle on
// contact; the stick attack arrives as InteractAttack and flips the beetle
// through the native pc_p2_kogane_attacked receiver. No attack directive is
// issued to any Pikmin, no Pikmin is repositioned, and nothing is pinned or
// held per frame: the squad roams free and the other beetles wander free.
//
// This file is a RoomApp fragment, not a standalone translation unit. The
// lane runner splices the marked sections into tools/preview_p2_room.cpp in a
// private output directory (same instrument() mechanics as the legacy lane 17
// runners) and builds the provenance-checked fixture from there, so the base
// startup, window, audio and cargo plumbing is inherited unchanged.

// MUSE-KOGANE-INCLUDES-BEGIN
#include <cmath>
#include <fstream>
#include "Demo.h"
#include "GameStat.h"
#include "Generator.h"
#include "Interactions.h"
#include "ItemMgr.h"
#include "ObjType.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Pellet.h"
#include "PelletView.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiAI.h"
#include "PikiState.h"
#include "PlayerState.h"
#include "TekiPersonality.h"
#include "pc_p2_kogane.h"
// MUSE-KOGANE-INCLUDES-END

// MUSE-KOGANE-APP-BEGIN
class RoomApp : public PlugPikiApp {
 int observed=0,frames=0,throws=0,lastThrow=-10000;
 bool staged=false,escaped=false;
 Teki* beetle=nullptr;Teki* control=nullptr;
 int alivePikis(){int c=0;Iterator it(pikiMgr);CI_LOOP(it){Creature* p=*it;if(p&&p->isAlive())++c;}return c;}
 public:int idle() override {
  int result=PlugPikiApp::idle();require(++frames<15000,"kogane natural-throw timeout");
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
   require(beetle&&control&&beetle!=control,"beetle/control identity");
   // Single staged captain position beside the TARGET birth anchor. This is the
   // only repositioning in the run and happens once, before any throw.
   Vector3f b=beetle->getPosition();
   Vector3f stagedPos(b.x-150.0f,b.y,b.z);
   n->resetPosition(stagedPos);n->mVelocity.set(0,0,0);n->mTargetVelocity.set(0,0,0);
   staged=true;
   std::printf("P2_KOGANE_THROW_STAGED nx=%.3f ny=%.3f nz=%.3f bx=%.3f by=%.3f bz=%.3f\n",stagedPos.x,stagedPos.y,stagedPos.z,b.x,b.y,b.z);
   std::fflush(stdout);}
  if(observed==60){int squad=alivePikis();std::printf("P2_KOGANE_SQUAD pikis=%d\n",squad);std::fflush(stdout);require(squad==20,"starting squad size");}
  // Throw loop: one genuine throw-release event pair per cooldown window at the
  // beetle's live position. The engine selector picks the Pikmin; ballistic
  // flight, landing and engagement are the Pikmin's own.
  if(beetle&&beetle->isAlive()&&staged&&!escaped&&throws<30&&observed-lastThrow>=180){
   n->findNextThrowPiki();
   Piki* p=n->mNextThrowPiki;
   if(p&&p->isAlive()&&p->getState()==PIKISTATE_Normal&&p->isThrowable()){
    Vector3f aim=beetle->getPosition();
    p->mFSM->transit(p,PIKISTATE_Flying);
    n->throwPiki(p,aim);
    ++throws;lastThrow=observed;
    Vector3f d=aim;d.sub(n->mSRT.t);
    std::printf("P2_KOGANE_THROW n=%d generator=219001 dist=%.1f\n",throws,d.length());std::fflush(stdout);}
   else{std::printf("P2_KOGANE_THROW_SKIP tick=%d\n",observed);std::fflush(stdout);lastThrow=observed-120;}}
  if(beetle&&!beetle->isAlive()&&!escaped){
   escaped=true;
   std::printf("P2_KOGANE_NATURAL_ESCAPED tick=%d throws=%d beetle_alive=0\n",observed,throws);std::fflush(stdout);}
  if(throws>=30&&!escaped&&beetle&&beetle->isAlive()){
   std::printf("P2_KOGANE_THROW_BUDGET_EXHAUSTED throws=%d\n",throws);std::fflush(stdout);
   require(false,"kogane natural-throw budget exhausted without escape");}
  if(escaped){
   require(control&&control->isAlive(),"P1 control disturbed");
   require(alivePikis()>=1,"squad extinct");
   require(throws>=1,"no throws recorded");
   std::puts("PASS P2_KOGANE_NATURAL_THROW flips3 escape1 control_alive");std::fflush(stdout);std::_Exit(0);}
  std::fflush(stdout);return result;
 }};
// MUSE-KOGANE-APP-END
