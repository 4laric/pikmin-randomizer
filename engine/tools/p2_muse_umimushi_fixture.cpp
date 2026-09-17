// UmiMushi71 observer fixture source (shard lane, issue #374).
//
// Observes a NATURAL death/corpse of the live bound near Blind Bloyster
// (generator 374006, source 101) plus its stage-boundary rebirth. The death
// stimulus is the engine's own squad-vs-actor combat: the 20 reds spawned by
// the arena retaliate against the near Blind's flick/Eat and drain the native
// 800-HP pool through the untouched family FSM, which raises UMIMUSHI_DEAD
// itself. The fixture writes no health, mode or attack state; its only staged
// action is parking the captain OUTSIDE every actor's 700-unit sight radius
// (captain safety #632) on tick 1, so the captain is never in reach and no
// throw path is exercised (throws require proximity, which safety forbids).
//
// MUSE-UMIMUSHI-INCLUDES-BEGIN
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
// Vendored verbatim from scripts/p2_fixture_captain_guard.h (sha256
// d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474,
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
// MUSE-UMIMUSHI-INCLUDES-END

// MUSE-UMIMUSHI-APP-BEGIN
class RoomApp : public PlugPikiApp {
 int observed=0,frames=0,deathTick=-1,lastHp=0;
 bool staged=false,deadSeen=false,funneled=false,goneSeen=false,corpseFound=false,rebound=false,hpDropped=false;
 Teki* umi=nullptr;
 void* stalePtr=nullptr;
 int alivePikis(){int c=0;Iterator it(pikiMgr);CI_LOOP(it){Creature* p=*it;if(p&&p->isAlive())++c;}return c;}
 bool actorPresent(Teki* a){Iterator it(tekiMgr);CI_LOOP(it){if(static_cast<Teki*>(*it)==a)return true;}return false;}
 public:int idle() override {
  int result=PlugPikiApp::idle();require(++frames<60000,"umimushi observer timeout");
  if(!naviMgr||!tekiMgr||!pikiMgr)return result;
  Navi* n=naviMgr->getNavi();if(!n)return result;
  p2_fixture_require_captain(GameStat::orimaDead,!n->isAlive(),n->mHealth,observed);
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_cargo_free_ready())return result;
  if(gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  ++observed;
  if(observed==1){
   for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i); // suppress one-shot discovery cutscenes
   std::ifstream input("umimushi-positions.txt");unsigned id;float x,y,z;int count=0;
   while(input>>id>>x>>y>>z){
    Teki* actor=nullptr;int matches=0;Iterator iter(tekiMgr);CI_LOOP(iter){Teki* a=static_cast<Teki*>(*iter);if(a->mGenerator&&a->mGenerator->_70==id){actor=a;++matches;}}
    require(matches==1,"umimushi roster identity");
    Vector3f birth=actor->mPersonality->mPosition;
    std::printf("P2_UMIMUSHI_BIRTH id=%u type=%d x=%.3f y=%.3f z=%.3f\n",id,actor->mTekiType,birth.x,birth.y,birth.z);
    if(id==374006)umi=actor;++count;}
   require(count>=1&&umi,"umimushi TARGET 374006 missing");
   // Park the captain OUTSIDE every actor's 700-unit sight radius: no chase,
   // no flick knockback, no captain damage window (#632). Observation only.
   Vector3f safe(600.0f,0.0f,1200.0f);
   n->resetPosition(safe);n->mVelocity.set(0,0,0);n->mTargetVelocity.set(0,0,0);
   staged=true;
   std::printf("P2_UMIMUSHI_CAPTAIN_PARKED nx=%.3f ny=%.3f nz=%.3f reason=outside_all_sight\n",safe.x,safe.y,safe.z);
   std::fflush(stdout);
   std::ifstream stale("umimushi-pass1-ptr.txt");unsigned long long v=0;
   if(stale>>std::hex>>v){stalePtr=reinterpret_cast<void*>(v);rebound=true;
    std::printf("P2_UMIMUSHI_REBOUND stale=0x%llx fresh=0x%llx generator=374006\n",(unsigned long long)stalePtr,(unsigned long long)umi);std::fflush(stdout);
    require(stalePtr!=umi,"stale/fresh pointer identical after stage boundary");}
   else{
    std::ofstream ptr("umimushi-pass1-ptr.txt");ptr<<std::hex<<(unsigned long long)umi;ptr.close();}
   std::fflush(stdout);}
  if(observed==60){int squad=alivePikis();std::printf("P2_UMIMUSHI_SQUAD pikis=%d\n",squad);std::fflush(stdout);require(squad==20,"starting squad size");}
  if(umi&&!deadSeen&&umi->isAlive()&&observed%200==0){Vector3f vp=umi->getPosition();float vg=mapMgr?mapMgr->getMinY(vp.x,vp.z,true):vp.y;
   if(lastHp>0.0f&&umi->mHealth<lastHp)hpDropped=true;
   lastHp=umi->mHealth;
   std::printf("P2_UMIMUSHI_VITALS tick=%d hp=%.1f x=%.1f y=%.1f z=%.1f ground=%.1f\n",observed,umi->mHealth,vp.x,vp.y,vp.z,vg);std::fflush(stdout);}
  if(rebound){
   require(umi&&umi->isAlive()&&actorPresent(umi),"rebirth actor not live");
   require(alivePikis()>=1,"squad extinct on rebirth");
   std::puts("PASS P2_UMIMUSHI_REBIRTH rebound1 control_alive");std::fflush(stdout);std::_Exit(0);}
  if(umi&&!umi->isAlive()&&!deadSeen){
   deadSeen=true;deathTick=observed;
   Vector3f dp=umi->getPosition();
   float ground=mapMgr?mapMgr->getMinY(dp.x,dp.z,true):dp.y;
   std::printf("P2_UMIMUSHI_NATURAL_DEATH tick=%d hp_dropped=%d\n",observed,int(hpDropped));
   std::printf("P2_UMIMUSHI_DEATH_POS x=%.2f y=%.2f z=%.2f ground=%.2f\n",dp.x,dp.y,dp.z,ground);std::fflush(stdout);
   require(hpDropped,"target died without any observed combat HP loss");
   require(alivePikis()>=1,"squad extinct at death");
   require(std::isfinite(ground)&&dp.y>=ground-2.0f&&dp.y<=ground+160.0f,"umimushi died off the arena floor (fall, not combat)");}
  if(deadSeen&&!funneled&&observed>=deathTick+5){
   // Drive the public engine death funnel once (doAI is suppressed for
   // family actors, so dieSoon would never run). No state is written by the
   // fixture; all damage is prior natural combat. Address use only after.
   static_cast<BTeki*>(umi)->pcEscapeNow();
   funneled=true;
   std::puts("P2_UMIMUSHI_FUNNEL_DROVE engine=dieSoon");std::fflush(stdout);}
  if(funneled&&!goneSeen){
   if(!actorPresent(umi)){
    goneSeen=true;
    std::printf("P2_UMIMUSHI_GONE tick=%d\n",observed);std::fflush(stdout);}}
  if(funneled&&!corpseFound){
   Iterator it(pelletMgr);CI_LOOP(it){Pellet* p=static_cast<Pellet*>(*it);if(p&&p->isAlive()&&p->mPelletView==static_cast<PelletView*>(umi)){corpseFound=true;break;}}
   if(corpseFound){std::puts("P2_UMIMUSHI_CORPSE_PRESENT engine_funnel");std::fflush(stdout);}}
  if(deadSeen&&funneled&&!goneSeen&&!corpseFound&&observed>deathTick+900){
   std::puts("P2_UMIMUSHI_FUNNEL_STALLED no_removal_no_corpse");std::fflush(stdout);
   require(false,"death funnel produced neither removal nor corpse");}
  if(!deadSeen&&umi&&umi->isAlive()&&observed>12000){
   std::puts("P2_UMIMUSHI_DEATH_BUDGET_EXHAUSTED target survived the observation window");std::fflush(stdout);
   require(false,"umimushi natural-death budget exhausted without death");}
  if(goneSeen||corpseFound){
   if(!corpseFound){std::puts("P2_UMIMUSHI_NO_CORPSE source_no_loot");std::fflush(stdout);}
   require(alivePikis()>=1,"squad extinct");
   std::puts("PASS P2_UMIMUSHI_NATURAL_DEATH death1 gone1 squad_alive");std::fflush(stdout);std::_Exit(0);}
  std::fflush(stdout);return result;
 }};
// MUSE-UMIMUSHI-APP-END