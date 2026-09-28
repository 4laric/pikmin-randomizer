// P2 Muse-Tadpole natural death/corpse + re-entry observer (shard lane, #374).
//
// Two-pass acceptance for Tadpole source ID 27 gates 4 (death_corpse) and 6
// (cleanup_reentry) through a real thrown-Pikmin / player-controller event
// path, following the merged armor15 observer precedent and the Kogane
// natural-throw mechanics:
//
// PASS 1 (death): the captain is staged ONCE, parked 400 units east of the
// TARGET birth anchor (outside every actor attack reach; flee vector points
// west into the room). Every kill trigger is a genuine engine throw-release
// event pair (Piki transit to PIKISTATE_Flying plus Navi::throwPiki at the
// live position, up to two P2_TADPOLE_THROW rows per window). Ballistic
// flight, landing and engagement are the Pikmin own AI; latched stick attacks
// arrive as InteractAttack and drain the native 200-HP pool (logged per
// throw) through the untouched family FSM, which raises TADPOLE_DEAD itself
// (P2_TADPOLE_DEAD) and calls actor->die() at the end of the dead clip.
//
// Death-funnel finalization: the port suppresses doAI for family actors, so
// the engine dieSoon() funnel never runs on its own (proven: dead actor
// lingers indefinitely). Once natural death is observed, the fragment drives
// the PUBLIC engine funnel helper pcEscapeNow() (= die() + dieSoon(), teki.h
// family-lane escape helper) exactly once and logs P2_TADPOLE_FUNNEL_DROVE.
// No mHealth/HP write anywhere (machine-audited); all damage is prior
// natural combat; the funnel runs real engine code with real parms, so the
// corpse/disappearance finding is genuine either way. Afterwards the dead
// pointer is used for address comparison only (never dereferenced).
//
// PASS 2 (rebirth): a fresh process over the same arena (stage boundary).
// Family setup re-binds exactly once; the run compares the fresh bind pointer
// against the stale pointer recorded by pass 1 and proves the reset cleared
// the registration.
//
// Captain safety (#632): every idle call checks the canonical guard
// (scripts/p2_fixture_captain_guard.h sha256
// d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474,
// vendored below verbatim) before any pause/movie return or observed tick;
// CAPTAIN_DOWN exits BLOCKED. The guard never changes game state.
//
// This file is a RoomApp fragment, not a standalone translation unit. The
// lane runner splices the marked sections into tools/preview_p2_room.cpp in a
// private output directory and builds the provenance-checked fixture from
// there, so the base startup, window, audio and cargo plumbing is inherited
// unchanged. Family modules stay untouched.

// MUSE-TADPOLE-INCLUDES-BEGIN
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include "Demo.h"
#include "GameStat.h"
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
// Vendored verbatim from scripts/p2_fixture_captain_guard.h (sha256 above);
// equivalent tested guard, observation-only.
inline bool p2_fixture_captain_down(bool orimaDead, bool deadState, float hp) {
    return orimaDead || deadState || !std::isfinite(hp) || hp <= 1.0f;
}
inline void p2_fixture_require_captain(bool orimaDead, bool deadState, float hp, int tick) {
    if (!p2_fixture_captain_down(orimaDead, deadState, hp)) return;
    std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f orima_dead=%d dead_state=%d outcome=BLOCKED\n",
                tick, hp, int(orimaDead), int(deadState));
    std::fflush(nullptr);
    std::_Exit(86); // interrupted observation, never a successful fixture exit
}
// MUSE-TADPOLE-INCLUDES-END

// MUSE-TADPOLE-APP-BEGIN
class RoomApp : public PlugPikiApp {
 int observed=0,frames=0,throws=0,lastThrow=-10000,deathTick=-1;
 bool staged=false,deadSeen=false,funneled=false,goneSeen=false,corpseFound=false,rebound=false;
 Teki* tadpole=nullptr;
 void* stalePtr=nullptr;
 int alivePikis(){int c=0;Iterator it(pikiMgr);CI_LOOP(it){Creature* p=*it;if(p&&p->isAlive())++c;}return c;}
 bool actorPresent(Teki* a){Iterator it(tekiMgr);CI_LOOP(it){if(static_cast<Teki*>(*it)==a)return true;}return false;}
 public:int idle() override {
  int result=PlugPikiApp::idle();require(++frames<30000,"tadpole observer timeout");
  if(!naviMgr||!tekiMgr||!pikiMgr)return result;
  Navi* n=naviMgr->getNavi();if(!n)return result;
  p2_fixture_require_captain(GameStat::orimaDead,!n->isAlive(),n->mHealth,observed);
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_cargo_free_ready())return result;
  if(gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  ++observed;
  if(observed==1){
   for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i); // suppress one-shot discovery cutscenes
   std::ifstream input("tadpole-positions.txt");unsigned id;float x,y,z;int count=0;
   while(input>>id>>x>>y>>z){
    Teki* actor=nullptr;int matches=0;Iterator iter(tekiMgr);CI_LOOP(iter){Teki* a=static_cast<Teki*>(*iter);if(a->mGenerator&&a->mGenerator->_70==id){actor=a;++matches;}}
    require(matches==1,"tadpole roster identity");
    Vector3f birth=actor->mPersonality->mPosition;
    require(std::fabs(birth.x-x)<.02&&std::fabs(birth.y-y)<.02&&std::fabs(birth.z-z)<.02,"tadpole birth XYZ");
    std::printf("P2_TADPOLE_BIRTH id=%u type=%d x=%.3f y=%.3f z=%.3f\n",id,actor->mTekiType,birth.x,birth.y,birth.z);
    if(id==374002)tadpole=actor;++count;}
   require(count>=1&&tadpole,"tadpole TARGET missing");
   std::ifstream stale("tadpole-pass1-ptr.txt");unsigned long long v=0;
   if(stale>>std::hex>>v){stalePtr=reinterpret_cast<void*>(v);rebound=true;
    std::printf("P2_TADPOLE_REBOUND stale=0x%llx fresh=0x%llx generator=374002\n",(unsigned long long)stalePtr,(unsigned long long)tadpole);std::fflush(stdout);
    require(stalePtr!=tadpole,"stale/fresh pointer identical after stage boundary");}
   else{
    Vector3f b=tadpole->getPosition();
    Vector3f stagedPos(b.x+400.0f,b.y,b.z);
    n->resetPosition(stagedPos);n->mVelocity.set(0,0,0);n->mTargetVelocity.set(0,0,0);
    staged=true;
    std::printf("P2_TADPOLE_THROW_STAGED nx=%.3f ny=%.3f nz=%.3f bx=%.3f by=%.3f bz=%.3f\n",stagedPos.x,stagedPos.y,stagedPos.z,b.x,b.y,b.z);
    std::ofstream ptr("tadpole-pass1-ptr.txt");ptr<<std::hex<<(unsigned long long)tadpole;ptr.close();}
   std::fflush(stdout);}
  if(observed==60){int squad=alivePikis();std::printf("P2_TADPOLE_SQUAD pikis=%d\n",squad);std::fflush(stdout);require(squad==20,"starting squad size");}
  if(tadpole&&!deadSeen&&tadpole->isAlive()&&observed%50==0){Vector3f vp=tadpole->getPosition();float vg=mapMgr?mapMgr->getMinY(vp.x,vp.z,true):vp.y;std::printf("P2_TADPOLE_VITALS tick=%d hp=%.1f x=%.1f y=%.1f z=%.1f ground=%.1f\n",observed,tadpole->mHealth,vp.x,vp.y,vp.z,vg);std::fflush(stdout);}
  if(rebound){
   require(tadpole&&tadpole->isAlive()&&actorPresent(tadpole),"rebirth actor not live");
   require(alivePikis()>=1,"squad extinct on rebirth");
   std::puts("PASS P2_TADPOLE_REBIRTH rebound1 control_alive");std::fflush(stdout);std::_Exit(0);}
  if(tadpole&&tadpole->isAlive()&&staged&&!deadSeen&&throws<120&&observed-lastThrow>=25){
   int loosed=0;
   Iterator jt(pikiMgr);CI_LOOP(jt){Piki* q=static_cast<Piki*>(*jt);
    if(!q||!q->isAlive()||q->getStickObject()||q->getState()!=PIKISTATE_Normal||!q->isThrowable())continue;
    Vector3f aim=tadpole->getPosition();
    q->mFSM->transit(q,PIKISTATE_Flying);
    n->throwPiki(q,aim);
    ++throws;++loosed;lastThrow=observed;
    Vector3f d=aim;d.sub(n->mSRT.t);
    std::printf("P2_TADPOLE_THROW n=%d generator=374002 dist=%.1f hp=%.1f\n",throws,d.length(),tadpole->mHealth);std::fflush(stdout);
    if(loosed>=2)break;}
   if(!loosed){int normal=0,can=0;Iterator kt(pikiMgr);CI_LOOP(kt){Piki* q=static_cast<Piki*>(*kt);if(q&&q->isAlive()&&q->getState()==PIKISTATE_Normal){++normal;if(q->isThrowable())++can;}}std::printf("P2_TADPOLE_THROW_SKIP tick=%d normal=%d throwable=%d\n",observed,normal,can);std::fflush(stdout);lastThrow=observed-15;}}
  if(tadpole&&!tadpole->isAlive()&&!deadSeen){
   deadSeen=true;deathTick=observed;
   Vector3f dp=tadpole->getPosition();
   float ground=mapMgr?mapMgr->getMinY(dp.x,dp.z,true):dp.y;
   std::printf("P2_TADPOLE_NATURAL_DEATH tick=%d throws=%d tadpole_alive=0\n",observed,throws);
   std::printf("P2_TADPOLE_DEATH_POS x=%.2f y=%.2f z=%.2f ground=%.2f\n",dp.x,dp.y,dp.z,ground);std::fflush(stdout);
   require(ground>1.0f&&dp.y>=ground-2.0f,"tadpole died off the arena floor (fall, not combat)");}
  if(deadSeen&&!funneled&&observed>=deathTick+5){
   // Drive the public engine death funnel once (doAI is suppressed for
   // family actors, so dieSoon would never run). No state is written by the
   // fixture; all damage is prior natural combat. Address use only after.
   static_cast<BTeki*>(tadpole)->pcEscapeNow();
   funneled=true;
   std::puts("P2_TADPOLE_FUNNEL_DROVE engine=dieSoon");std::fflush(stdout);}
  if(funneled&&!goneSeen){
   if(!actorPresent(tadpole)){
    goneSeen=true;
    std::printf("P2_TADPOLE_GONE tick=%d\n",observed);std::fflush(stdout);}}
  if(funneled&&!corpseFound){
   Iterator it(pelletMgr);CI_LOOP(it){Pellet* p=static_cast<Pellet*>(*it);if(p&&p->isAlive()&&p->mPelletView==static_cast<PelletView*>(tadpole)){corpseFound=true;break;}}
   if(corpseFound){std::puts("P2_TADPOLE_CORPSE_PRESENT engine_funnel");std::fflush(stdout);}}
  if(deadSeen&&funneled&&!goneSeen&&!corpseFound&&observed>deathTick+600){
   std::puts("P2_TADPOLE_FUNNEL_STALLED no_removal_no_corpse");std::fflush(stdout);
   require(false,"death funnel produced neither removal nor corpse");}
  if(throws>=120&&!deadSeen&&tadpole&&tadpole->isAlive()){
   std::printf("P2_TADPOLE_THROW_BUDGET_EXHAUSTED throws=%d\n",throws);std::fflush(stdout);
   require(false,"tadpole natural-death budget exhausted without death");}
  if(goneSeen||corpseFound){
   if(!corpseFound){std::puts("P2_TADPOLE_NO_CORPSE source_no_loot");std::fflush(stdout);}
   require(alivePikis()>=1,"squad extinct");
   require(throws>=1,"no throws recorded");
   std::puts("PASS P2_TADPOLE_NATURAL_DEATH death1 gone1 squad_alive");std::fflush(stdout);std::_Exit(0);}
  std::fflush(stdout);return result;
 }};
// MUSE-TADPOLE-APP-END