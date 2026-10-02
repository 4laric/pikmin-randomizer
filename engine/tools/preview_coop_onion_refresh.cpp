// Fixture-only injected live-count scenario. Ordinary native initialization,
// authoritative NaviContainerState and real menus/input remain in use.
#include "App.h"
#include "AIConstant.h"
#include "GameStat.h"
#include "GoalItem.h"
#include "ItemMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "MoviePlayer.h"
#include "zen/DrawContainer.h"
#include "p2_fixture_captain_guard.h"
#include "netplay/pc_netplay_det.h"
#include "system.h"
#include <SDL.h>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <algorithm>
extern zen::DrawContainer* containerWindow;
extern zen::DrawContainer* containerWindow2;
namespace {
bool human = false;
void require(bool ok, const char* detail) {
 if (!ok) { std::printf("FAIL COOP_ONION_SMOKE %s\n", detail); std::fflush(nullptr); std::_Exit(1); }
}
class OnionSmokeApp final : public PlugPikiApp {
 bool seen[2] = {false,false};
 bool staged = false;
 unsigned last = 0;
 unsigned start = 0;
 GoalItem* goals[2] = {nullptr,nullptr};
 int baseLimit = 20;
 int beforeCloseStock[2] = {0,0};
 int selectedAtClose[2] = {0,0};
 int freeAtClose = 0;
 int live() { int count=0; Iterator it(pikiMgr); CI_LOOP(it) { if(static_cast<Piki*>(*it)->isAlive()) ++count; } return count; }
 void note(unsigned tick, const char* event) {
  GameStat::update();
  std::printf("ONION_SMOKE tick=%u event=%s injected=1 live=%d field=%d pending=%d limit=%d paused=%d",tick,event,live(),int(GameStat::mapPikis),itemMgr->getContainerExitCount(),int(AICONST.mMaxPikisOnField()),int(gameflow.mPauseAll));
  zen::DrawContainer* menus[2]={containerWindow,containerWindow2};
  for(int i=0;i<2;i++) std::printf(" p%d_state=%d stock=%d display=%d query_withdraw10=%d",i,int(menus[i]->getStatus()),goals[i]->getTotalStorePikis(),menus[i]->getContainerPikiDisp(),menus[i]->revalidateTransfer(-10));
  std::puts("");std::fflush(stdout);
 }
 public:
 int idle() override {
  const int result=PlugPikiApp::idle();
  const unsigned tick=pc_netplay_tick();
  // Unconditional observation before any movie/readiness/tick early return.
  for(int i=0;i<2;i++) {
   Navi* n=naviMgr && naviMgr->getNaviCount()>i ? naviMgr->getNavi(i):nullptr;
   if(n) {seen[i]=true;p2_fixture_require_captain(GameStat::orimaDead,n->getCurrState() && n->getCurrState()->getID()==NAVISTATE_Dead,((std::getenv("COOP_ONION_FORCE_DOWN") && tick>=5) ? 0.0f : n->mHealth),int(tick));}
   else if(seen[i]) {std::puts("P2_FIXTURE_CAPTAIN_DOWN outcome=BLOCKED disappeared=1");std::fflush(nullptr);std::_Exit(86);}
  }
  if(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {gameflow.mMoviePlayer->requestSkip();return result;}
  if(tick==last)return result;last=tick;
  if(!naviMgr || naviMgr->getNaviCount()!=2 || !pikiMgr || !itemMgr || !containerWindow2 || gameflow.mPauseAll || gameflow.mIsUIOverlayActive)return result;
  if(!staged) {
   if(tick<360 || live()!=20)return result;
   goals[0]=itemMgr->getContainer(Red);
   for(int c=0;c<3;c++) {GoalItem* g=itemMgr->getContainer(c);if(g && g!=goals[0]){goals[1]=g;break;}}
   require(goals[0] && goals[1],"two distinct native Onion objects required");
   GameStat::update();baseLimit=int(AICONST.mMaxPikisOnField());
   require(baseLimit==30,"authoritative starting flarlic3 capacity30");
   const int reserve=baseLimit-int(GameStat::mapPikis)-itemMgr->getContainerExitCount();
   require(reserve>=0 && reserve<=10,"starting20live plus source heads fit known field budget");
   for(int i=0;i<2;i++){goals[i]->mHeldPikis[Leaf]=10;goals[i]->mHeldPikis[Bud]=goals[i]->mHeldPikis[Flower]=0;}
   goals[1]->exitPikis(reserve,1);
   for(int i=0;i<2;i++) {
    Navi* n=naviMgr->getNavi(i);n->mGoalItem=goals[i];n->mStateMachine->transit(n,NAVISTATE_Container);
   }
   staged=true;start=tick;note(tick,"READY_FULL20_TWO_ONIONS_STOCK10");
   return result;
  }
  const unsigned age=tick-start;
  if(age==40) {
   std::vector<Piki*> victims;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p->isAlive() && victims.size()<5)victims.push_back(p);}
   require(victims.size()==5,"five death targets");for(Piki* p:victims)p->kill(false);
   note(tick,"DEATH5_FREES_ROOM");
  }
  if(age==70) {goals[0]->mHeldPikis[Leaf]=2;note(tick,"STOCK_SHRINK2");}
  if(age==90) {goals[0]->mHeldPikis[Leaf]=10;goals[1]->mHeldPikis[Leaf]=10;note(tick,"STOCK_GROW10");}
  if(age==100) {goals[1]->exitPikis(2,1);note(tick,"PENDING_EXIT2");}
  if(age==120) {goals[0]->exitPikis(1,0);note(tick,"PENDING_EXIT1_SHRINKS_ROOM");}
  if(age==135) {Piki* victim=nullptr;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p->isAlive()){victim=p;break;}}require(victim,"growth death target");victim->kill(false);note(tick,"DEATH1_GROWS_ROOM");}
  if(age>=40 && age%10==0)note(tick,"OBSERVE");
  if(!human && (age==41 || age==71 || age==91 || age==101 || age==121 || age==136)) {
   GameStat::update();const int room=std::max(0,int(AICONST.mMaxPikisOnField())-int(GameStat::mapPikis)-itemMgr->getContainerExitCount());
   zen::DrawContainer* menus[2]={containerWindow,containerWindow2};
   for(int i=0;i<2;i++) {
    const int stock=std::max(0,int(goals[i]->getTotalStorePikis())-goals[i]->mPikisToExit);
    const int delta=menus[i]->getContainerPikiDisp()-stock;
    const int squad=menus[i]->getMyPikiDisp()+delta;
    const int expected=-std::min({10,stock,room,std::max(0,int(AICONST.mMaxPikisOnField())-squad)});
    require(menus[i]->revalidateTransfer(-10)==expected,"both menu live query on tick after mutation");
    require(delta<=0 && -delta<=std::min(stock,room),"display/selection live clamp after mutation");
   }
   note(tick,"ASSERT_BOTH_REFRESH_PASS");
  }
  if(!human && age==60) {
   require(containerWindow->getContainerPikiDisp()<int(goals[0]->getTotalStorePikis())-goals[0]->mPikisToExit,"P1 ordinary down input withdraws after deaths");
   require(containerWindow2->getContainerPikiDisp()<int(goals[1]->getTotalStorePikis())-goals[1]->mPikisToExit,"P2 ordinary down input withdraws after deaths");
   note(tick,"ASSERT_BOTH_NORMAL_SELECTION_PASS");
  }
  if(!human && age==150) {
   GameStat::update();freeAtClose=baseLimit-int(GameStat::mapPikis)-itemMgr->getContainerExitCount();
   zen::DrawContainer* menus[2]={containerWindow,containerWindow2};
   for(int i=0;i<2;i++) {
    beforeCloseStock[i]=goals[i]->getTotalStorePikis();
    selectedAtClose[i]=beforeCloseStock[i]-goals[i]->mPikisToExit-menus[i]->getContainerPikiDisp();
    require(menus[i]->getStatus()==zen::DrawContainer::STATE_End && selectedAtClose[i]>0,"both normal confirm animations with selected withdrawals");
   }
   require(selectedAtClose[0]+selectedAtClose[1]>freeAtClose,"closing race actually competes for shared slots");note(tick,"ASSERT_COMPETING_CLOSE_PASS");
  }
  if(age==200 && !human) {
   require(int(GameStat::mapPikis)+itemMgr->getContainerExitCount()<=int(AICONST.mMaxPikisOnField()),"closing-race field budget");
   for(int i=0;i<2;i++)require(naviMgr->getNavi(i)->getCurrState()->getID()==NAVISTATE_Walk,"both normal menu confirmations complete");
   const int delivered0=beforeCloseStock[0]-int(goals[0]->getTotalStorePikis());
   const int delivered1=beforeCloseStock[1]-int(goals[1]->getTotalStorePikis());
   require(delivered0>=0 && delivered1>=0 && delivered0+delivered1>0,"actual nonzero Onion withdrawal dispatch delivers actors; second zero allowed");
   require(delivered0+delivered1<=freeAtClose && (delivered0<selectedAtClose[0] || delivered1<selectedAtClose[1]),"at least one closing transfer clamped and no overbooking");
   std::printf("PASS COOP_ONION_SMOKE delivered=%d,%d selected=%d,%d free=%d staged_live_counts bounded=1\n",delivered0,delivered1,selectedAtClose[0],selectedAtClose[1],freeAtClose);std::fflush(stdout);
  }
  return result;
 }
};
}
#define PlugPikiApp OnionSmokeApp
#define main onion_native_entry
#include "../pc_port/pc_main.cpp"
#undef main
#undef PlugPikiApp
int main(int argc,char** argv) {
 human=std::getenv("COOP_ONION_HUMAN")!=nullptr;
 return onion_native_entry(argc,argv);
}
