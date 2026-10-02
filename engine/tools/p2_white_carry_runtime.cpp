// Scripted native controller acquisition: no species, attachment or callback injection.
// pc_pad_axis_from_sdl divides SDL input by256; Controller then divides PAD by74.
// Preserve the intended PAD-domain65 walking and22 cursor inputs exactly.
static constexpr int white_carry_sdl_axis(int padAxis) { return padAxis*256; }
#if defined(P2_WHITE_CARRY_AXIS_TEST)
#include "pc_window.h"
#ifdef main
#undef main
#endif
#include <cstdio>
int main(){
 int checks=0;
 for(int value=-74;value<=74;++value){
  if(pc_pad_axis_from_sdl(white_carry_sdl_axis(value))!=value)return 1;
  if(pc_pad_axis_from_sdl(-white_carry_sdl_axis(-value))!=value)return 2;
  checks+=2;
 }
 if(white_carry_sdl_axis(65)!=16640||white_carry_sdl_axis(22)!=5632)return 3;
 if(pc_pad_axis_from_sdl(65*32767/74)!=112||pc_pad_axis_from_sdl(22*32767/74)!=38)return 4;
 std::printf("P2_WHITE_CARRY_AXIS_TEST_PASS roundtrip_checks=%d walking_pad=65 cursor_pad=22 old_walking_pad=112 old_cursor_pad=38 gamefeel=UNPROVEN\n",checks);
 return 0;
}
#else
#include <SDL2/SDL.h>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include "system.h"
#include "App.h"
#include "Node.h"
#include "Section.h"
#include "FlowController.h"
#include "MoviePlayer.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "CPlate.h"
#include "Kontroller.h"
#include "Camera.h"
#include "KeyConfig.h"
#include <cmath>
#include <string>
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "PikiHeadItem.h"
#include "ItemMgr.h"
#include "GoalItem.h"
#include "Boss.h"
#include "Pellet.h"
// Fixture-only read access to the naturally spent counter; no state mutation.
#define private public
#include "Pom.h"
#undef private
#include "PlayerState.h"
#include "Demo.h"
#include "GameStat.h"
#include "Generator.h"
#include "pc_p2_white.h"
#include "pc_p2_species.h"
#include "pc_p2_preview.h"
#include "pc_p2_cave.h"
#include "Suckable.h"
#include "teki.h"
#include "pc_p2_white_poison.h"
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "p2_fixture_captain_guard.h"
#include "pc_p2_purple.h"
#include <fstream>
#include <sstream>
#include <set>

static void require(bool ok,const char* reason) {
    if(!ok){std::printf("P2_WHITE_CARRY_FAIL %s\n",reason);std::fflush(nullptr);std::_Exit(1);}
}
static unsigned generatedUid(const Creature* actor) {
    require(actor&&actor->mGenerator,"original generated actor missing generator");
    return actor->mGenerator->_70; // Staged unique ID; getGeneratorID() is the shared name tag.
}
static int population() {
    int count=0;Iterator actors(pikiMgr);CI_LOOP(actors){if(static_cast<Piki*>(*actors)->isAlive())++count;}
    Iterator heads(itemMgr->getPikiHeadMgr());CI_LOOP(heads){if(static_cast<PikiHeadItem*>(*heads)->isAlive())++count;}
    return count;
}

static int phase=0,ticks=0,inputFrame=0,whiteBodies=0;static Vector3f goal;static Pellet* cargo=nullptr;static Piki* acquired=nullptr;static unsigned cargoUid=0,whiteUid=0;static Vector3f destination;static SDL_Joystick* virtualPad=nullptr;
class AcquisitionController:public Kontroller {
public:
 AcquisitionController():Kontroller(1){}
 void update()override{
  u32 keys=0;mMainStickX=0;mMainStickY=0;mSubStickX=0;mSubStickY=0;
  Navi* n=naviMgr?naviMgr->getNavi():nullptr;
  if(phase==13 && n && n->getCurrState() && n->getCurrState()->getID()==NAVISTATE_Walk && ticks%30<15)keys=KeyConfig::_instance->mDisbandKey.mBind;
  if(phase==14 && n && n->getCurrState() && n->getCurrState()->getID()==NAVISTATE_Walk && ticks%30<15)keys=KBBTN_DPAD_RIGHT;
  if(phase==8)keys=KeyConfig::_instance->mThrowKey.mBind;
  if(phase==1)keys=KeyConfig::_instance->mSetCursorKey.mBind;
  if((phase==2 || phase==4 || phase==7 || phase==9) && n && n->mNaviCamera){
   float bx=goal.x-n->mSRT.t.x,bz=goal.z-n->mSRT.t.z;
   bool walk=phase==4 || bx*bx+bz*bz>10000.f;
   // Cursor updates arrive through native polling. Pulse low-stick corrections
   // and let neutral input settle instead of continually circling the mouth.
   if(walk || ticks%10==0){
    float dx=walk?bx:goal.x-n->mCursorWorldPos.x,dz=walk?bz:goal.z-n->mCursorWorldPos.z,d=std::sqrt(dx*dx+dz*dz);
    if(d>(walk?15.f:3.f)){const Vector3f& axis=n->mNaviCamera->mViewXAxis;float strength=walk?65.f:22.f;keys=KBBTN_MSTICK_RIGHT;mMainStickX=s8(strength*(dx*axis.x+dz*axis.z)/d);mMainStickY=s8(strength*(dx*axis.z-dz*axis.x)/d);}
   }
  }
  if((phase==3 && whiteBodies<1 && ticks%60<15)||(phase==5 && ticks%60<50))keys=KeyConfig::_instance->mThrowKey.mBind;
  if(gameflow.mIsUIOverlayActive)keys=(inputFrame%30<15)?KBBTN_A:0;
  SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_A,int((keys&KBBTN_A)!=0));
  SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_B,int((keys&KBBTN_B)!=0));
  SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_X,int((keys&KBBTN_X)!=0));
  SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_Y,int((keys&KBBTN_Y)!=0));
  SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_DPAD_RIGHT,int((keys&KBBTN_DPAD_RIGHT)!=0));
  SDL_JoystickSetVirtualAxis(virtualPad,SDL_CONTROLLER_AXIS_LEFTX,Sint16(white_carry_sdl_axis(int(mMainStickX))));
  SDL_JoystickSetVirtualAxis(virtualPad,SDL_CONTROLLER_AXIS_LEFTY,Sint16(-white_carry_sdl_axis(int(mMainStickY))));
  SDL_JoystickUpdate();
 }
};
static AcquisitionController* scriptedInput=nullptr;
class AcquisitionApp:public PlugPikiApp {
 int frames=0;bool initialized=false;Pom* flower=nullptr;int baselinePellets=0,haulFrames=0,stable=0;bool haulProven=false,transportEnded=false;Vector3f haulStart;float initialDistance=0;
public:
 int idle()override{
  inputFrame=frames;if(scriptedInput)scriptedInput->update();
  int result=PlugPikiApp::idle();Navi* n=naviMgr?naviMgr->getNavi():nullptr;
  if(std::getenv("P2_WHITE_CARRY_PAUSED_DOWN")&&n&&n->getCurrState())gameflow.mPauseAll=true; // Negative only.
  if(n && n->getCurrState()){initialized=true;p2_fixture_require_captain(GameStat::orimaDead||naviMgr->isNaviDead(n),n->getCurrState()->getID()==NAVISTATE_Dead,(std::getenv("P2_WHITE_CARRY_FORCE_CAPTAIN_DOWN")||std::getenv("P2_WHITE_CARRY_PAUSED_DOWN"))?0.f:n->mHealth,frames);}
  else if(initialized){std::puts("P2_FIXTURE_CAPTAIN_DOWN missing_initialized_captain_or_state outcome=BLOCKED");std::fflush(nullptr);std::_Exit(86);}
  require(++frames<5000,"frame timeout");
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_ready()||!n||!n->getCurrState()||frames<90)return result;
  if(gameflow.mPauseAll||gameflow.mIsUIOverlayActive){if(frames%60==0){std::printf("P2_WHITE_INPUT_GATE frame=%d phase=%d paused=%d overlay=%d nstate=%d\n",frames,phase,int(gameflow.mPauseAll),int(gameflow.mIsUIOverlayActive),n->getCurrState()->getID());std::fflush(stdout);}return result;}
  ++ticks;
  if(phase==0 && n->getCurrState()->getID()==NAVISTATE_Starting)return result;
  if(phase==0){
   for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
   int w,h,x,y;SDL_Window* window=SDL_GL_GetCurrentWindow();SDL_GetWindowSize(window,&w,&h);SDL_GetWindowPosition(window,&x,&y);SDL_Rect bounds{};SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window),&bounds);bool centered=std::abs(x-(bounds.x+(bounds.w-w)/2))<=2&&std::abs(y-(bounds.y+(bounds.h-h)/2))<=2;require(w==960&&h==540&&centered,"window dimensions/centering");std::printf("P2_WHITE_CARRY_WINDOW width=%d height=%d centered=%d\n",w,h,int(centered));
   int count=0,white=0,red=0;Iterator actors(pikiMgr);CI_LOOP(actors){Piki* p=static_cast<Piki*>(*actors);if(p->isAlive()){++count;if(pc_p2_is_white(p))++white;else if(pc_p2_species(p)==P2SpeciesRed)++red;require(p->mHappa==Leaf,"unexpected restored maturity");}}
   require(count==20&&red==20&&white==0,"starting squad not20Red");
   std::set<unsigned> ids;Iterator roster(pikiMgr);CI_LOOP(roster){Piki* p=static_cast<Piki*>(*roster);require(p->isAlive()&&generatedUid(p)>=1&&generatedUid(p)<=20&&ids.insert(generatedUid(p)).second,"original20 unique generated Reds");}
   Iterator bosses(bossMgr);CI_LOOP(bosses){Boss* b=static_cast<Boss*>(*bosses);if(b->isAlive()&&b->mObjType==OBJTYPE_Pom&&pc_p2_ivory(static_cast<Pom*>(b))){require(!flower,"multiple Ivory buds");flower=static_cast<Pom*>(b);}}
   std::printf("P2_WHITE_BASELINE_COUNTS frame=%d red=%d bodies=%d bound_ivory=%d nstate=%d\n",frames,count,population(),int(flower!=nullptr),n->getCurrState()->getID());require(count==20&&population()==20&&flower,"fresh baseline requires twenty Reds and one Ivory");
   std::printf("P2_WHITE_ACQUISITION_BASELINE squad=20 window=%dx%d position=%d,%d hp=%.3f navi=%.2f,%.2f face=%.2f bud=%.2f,%.2f kill_same=%d capacity=%d cycles=%d..%d\n",w,h,x,y,n->mHealth,n->mSRT.t.x,n->mSRT.t.z,n->mFaceDirection,flower->mSRT.t.x,flower->mSRT.t.z,int(C_POM_PARM(flower,mDoKillSameColorPiki)),int(C_POM_PARM(flower,mMaxPikiPerCycle)),int(C_POM_PARM(flower,mMinCycles)),int(C_POM_PARM(flower,mMaxCycles)));
   Iterator pellets(pelletMgr);CI_LOOP(pellets){if(static_cast<Pellet*>(*pellets)->isAlive())++baselinePellets;}
   require(flower->mPomAi->mReleasedSeedCount==0,"Ivory starts with nonzero spent budget");
   cargo=pc_p2_preview_treasure();require(cargo&&cargo->isAlive()&&cargo->mConfig,"generated treasure missing");
   cargoUid=generatedUid(cargo);require(cargoUid==26,"cargo generator identity");
   require(cargo->mConfig->mCarryMinPikis()==1&&cargo->mConfig->mCarryMaxPikis()==1,"engineering cargo profile");
   auto* pod=itemMgr->getContainer(Red);require(pod&&pc_p2_preview_is_pod(pod),"real Pod missing");destination=pod->mSRT.t;
   require(!std::ifstream("p2-economy.txt").good()&&!std::ifstream("treasure-receipt.txt").good(),"fresh economy required");
   std::puts("P2_WHITE_CARRY_BASELINE red=20 white=0 heads=0 bodies=20 cargo_min=1 cargo_max=1 initial_pokos=0");
   if(std::getenv("P2_WHITE_CARRY_READY_ONLY")){std::puts("P2_WHITE_CARRY_READY_PASS");std::fflush(nullptr);std::_Exit(0);}
   phase=1;ticks=0;
  }
  if(phase==1&&ticks>=30){goal=flower->mSRT.t;phase=2;ticks=0;}
  if(phase==2){float dx=flower->mSRT.t.x-n->mCursorWorldPos.x,dz=flower->mSRT.t.z-n->mCursorWorldPos.z;float bx=flower->mSRT.t.x-n->mSRT.t.x,bz=flower->mSRT.t.z-n->mSRT.t.z;if(dx*dx+dz*dz<64 && bx*bx+bz*bz>625){phase=6;ticks=0;}}
  if(phase==6&&ticks>=20){float dx=flower->mSRT.t.x-n->mCursorWorldPos.x,dz=flower->mSRT.t.z-n->mCursorWorldPos.z;phase=(dx*dx+dz*dz<64)?3:2;ticks=0;}
  int red=0,white=0,heads=0,captured=0,flying=0;PikiHeadItem* head=nullptr;
  bool acquiredActive=false;std::set<unsigned> redIds;
  Iterator actors(pikiMgr);CI_LOOP(actors){Piki* p=static_cast<Piki*>(*actors);if(!p->isAlive())continue;if(p==acquired)acquiredActive=true;if(pc_p2_is_white(p))++white;else{require(pc_p2_species(p)==P2SpeciesRed&&generatedUid(p)>=1&&generatedUid(p)<=20&&redIds.insert(generatedUid(p)).second,"original Red identity/roster changed");++red;}if(p->getStickObject()==flower)++captured;if(p->getState()==PIKISTATE_Flying)++flying;}
  Iterator sprouts(itemMgr->getPikiHeadMgr());CI_LOOP(sprouts){PikiHeadItem* p=static_cast<PikiHeadItem*>(*sprouts);if(p->isAlive()){++heads;require(pc_p2_species(p)==P2SpeciesWhite,"non-White sprout");if(!head&&p->canPullout())head=p;}}
  int activeIvory=0,totalBosses=0;Iterator bossList(bossMgr);CI_LOOP(bossList){Boss* boss=static_cast<Boss*>(*bossList);++totalBosses;if(boss==flower)++activeIvory;}
  // The sole Pom stays allocated in its free pool after kill. This arena has
  // no other boss generators; reject active pool reuse before observing it.
  require(totalBosses==1 && activeIvory==1,"bound Ivory disappeared or unexpected boss birth/pool reuse");
  if(activeIvory)require(flower->mObjType==OBJTYPE_Pom && pc_p2_ivory(flower),"bound Pom identity changed");
  if(ticks%60==0){std::printf("P2_WHITE_ACQUISITION_FRAME frame=%d phase=%d ticks=%d red=%d white=%d heads=%d captured=%d flying=%d bodies=%d nstate=%d navi=%.2f,%.2f cursor=%.2f,%.2f budstate=%d budalive=%d\n",frames,phase,ticks,red,white,heads,captured,flying,population(),n->getCurrState()->getID(),n->mSRT.t.x,n->mSRT.t.z,n->mCursorWorldPos.x,n->mCursorWorldPos.z,flower->getCurrentState(),int(flower->isAlive()));std::fflush(stdout);}
  // All phases observe original cargo before dereferencing its retained pointer.
  bool cargoActive=false;Iterator cargoList(pelletMgr);CI_LOOP(cargoList){if(*cargoList==cargo)cargoActive=true;}
  int cw=0,cr=0,other=0;Iterator cargoCarriers(pikiMgr);CI_LOOP(cargoCarriers){Piki* p=static_cast<Piki*>(*cargoCarriers);if(p->isAlive()&&p->getStickObject()==cargo){
   if(pc_p2_is_white(p))++cw;else if(pc_p2_species(p)==P2SpeciesRed)++cr;else ++other;
   std::printf("P2_WHITE_CARGO_CARRIER frame=%d phase=%d generated=%d uid=%u species=%d mode=%u acquired=%d\n",frames,phase,int(p->mGenerator!=nullptr),p->mGenerator?generatedUid(p):0,unsigned(pc_p2_species(p)),unsigned(p->mMode),int(p==acquired));
  }}
  if(cargoActive){
   require(generatedUid(cargo)==cargoUid,"cargo active-slot identity changed");
   if(ticks%60==0||cr||other)std::printf("P2_WHITE_CARGO_OBSERVATION frame=%d phase=%d cargo_uid=%u white=%d red=%d other=%d native_strength=%d x=%.4f y=%.4f z=%.4f\n",frames,phase,cargoUid,cw,cr,other,cargo->mCarrierCounter,cargo->mSRT.t.x,cargo->mSRT.t.y,cargo->mSRT.t.z);
  }else{std::printf("P2_WHITE_CARGO_REMOVED frame=%d phase=%d haul_proven=%d\n",frames,phase,int(haulProven));require(phase==10&&haulProven,"cargo disappeared before actual transport proof");}
  if(phase>=7&&phase!=13&&ticks%30==0){
   Iterator squadActors(pikiMgr);CI_LOOP(squadActors){Piki* p=static_cast<Piki*>(*squadActors);if(p->isAlive())std::printf("P2_WHITE_SQUAD_OBSERVATION frame=%d phase=%d uid=%u species=%d mode=%u state=%d owned_navi=%d acquired=%d selected=%d x=%.3f z=%.3f\n",frames,phase,p->mGenerator?generatedUid(p):0,unsigned(pc_p2_species(p)),unsigned(p->mMode),p->getState(),int(p->mNavi==n),int(p==acquired),int(p==n->mNextThrowPiki),p->mSRT.t.x,p->mSRT.t.z);}
  }
  require(cr==0&&other==0&&cw<=1,"unexpected cargo carriers");
  if(cw)require(acquiredActive&&cw==1&&acquired&&acquired->getStickObject()==cargo,"cargo White must be the naturally acquired body");
  if(!haulProven)require(!std::ifstream("p2-economy.txt").good()&&!std::ifstream("treasure-receipt.txt").good(),"cargo receipt before sole White physical hauling proof");
  if(phase<7 && population()!=20){std::printf("P2_WHITE_POPULATION_FAILURE frame=%d red=%d white=%d heads=%d captured=%d flying=%d bodies=%d phase=%d nstate=%d\n",frames,red,white,heads,captured,flying,population(),phase,n->getCurrState()->getID());Iterator diag(pikiMgr);CI_LOOP(diag){Piki* p=static_cast<Piki*>(*diag);std::printf("P2_WHITE_PIKI_DIAG alive=%d state=%d mode=%d x=%.2f y=%.2f z=%.2f\n",int(p->isAlive()),p->getState(),int(p->mMode),p->mSRT.t.x,p->mSRT.t.y,p->mSRT.t.z);}}
  require(population()==20,"ordinary acquisition lost/duplicated bodies");
  whiteBodies=white+heads;
  int pellets=0;Iterator pelletList(pelletMgr);CI_LOOP(pelletList){if(static_cast<Pellet*>(*pelletList)->isAlive())++pellets;}
  require(whiteBodies<=1,"unexpected additional White output");
  if(phase<7 || phase==13)require(pellets==baselinePellets,"live pellet count changed before sole White cargo phase");
  if(phase==3 && heads==1 && captured==0){require(red==19&&heads==1,"ordinary acquisition output");goal=flower->mSRT.t;phase=13;ticks=0;std::puts("P2_WHITE_CARRY_SPROUT ordinary_birth=1 spent=1");}
  if(phase==13 && ticks>=30){int follows=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p->isAlive()&&p->mMode==PikiMode::FormationMode)++follows;}if(ticks%30==0){std::printf("P2_WHITE_CARRY_DISBAND ticks=%d follows=%d state=%d bind=%u down=%u\n",ticks,follows,n->getCurrState()->getID(),unsigned(KeyConfig::_instance->mDisbandKey.mBind),unsigned(n->mKontroller->keyDown(KeyConfig::_instance->mDisbandKey.mBind)));std::fflush(nullptr);}require(ticks<240,"ordinary Red disband timeout");if(follows==0&&n->getCurrState()->getID()==NAVISTATE_Walk){phase=4;ticks=0;std::puts("P2_WHITE_CARRY_REDS_DISMISSED");}}
  if(phase==4 && head){goal=head->mSRT.t;float dx=goal.x-n->mSRT.t.x,dz=goal.z-n->mSRT.t.z;if(dx*dx+dz*dz<225){phase=5;ticks=0;}}
  if(phase==5 && head){if(ticks%60==0){std::printf("P2_WHITE_CARRY_PLUCK_APPROACH captain=%.3f,%.3f head=%.3f,%.3f state=%d\n",n->mSRT.t.x,n->mSRT.t.z,head->mSRT.t.x,head->mSRT.t.z,n->getCurrState()->getID());std::fflush(nullptr);}float dx=head->mSRT.t.x-n->mSRT.t.x,dz=head->mSRT.t.z-n->mSRT.t.z;if(dx*dx+dz*dz>400 && n->getCurrState()->getID()==NAVISTATE_Walk){goal=head->mSRT.t;phase=4;ticks=0;}}
  if(phase==5 && white==1 && heads==0 && n->getCurrState()->getID()==NAVISTATE_Walk){
   require(red==19&&captured==0&&flower->mPomAi->mReleasedSeedCount==1,"ordinary White pluck counts/budget");
   Iterator whites(pikiMgr);CI_LOOP(whites){Piki* p=static_cast<Piki*>(*whites);if(p->isAlive()&&pc_p2_is_white(p)){require(!acquired,"multiple Whites");acquired=p;}}
   require(acquired&&!pc_p2_has_red_immunity(acquired)&&acquired->mHappa==Leaf,"natural White leaf identity/immunity");whiteUid=acquired->getGeneratorID(); // Ordinary name tag (possibly null); active pointer membership conserves this naturally born body.
   goal=cargo->mSRT.t;phase=7;ticks=0;
   std::puts("P2_WHITE_CARRY_PLUCKED red=19 white=1 heads=0 bodies=20 spent=1 ordinary_birth_pluck=1");std::fflush(nullptr);return result; // Observe active membership afresh after the next real engine idle.
  }
  if(phase>=7&&phase!=13){
   require(red==19&&white==1&&heads==0&&acquiredActive&&pc_p2_is_white(acquired)&&acquired->getGeneratorID()==whiteUid,"acquired White conserved");
   // Never dereference retained cargo after active-manager removal.
   if(cargoActive){
    require(generatedUid(cargo)==cargoUid,"cargo active-slot identity changed");
    if(phase==7){goal=cargo->mSRT.t;float dx=goal.x-n->mCursorWorldPos.x,dz=goal.z-n->mCursorWorldPos.z;float bx=goal.x-n->mSRT.t.x,bz=goal.z-n->mSRT.t.z;if(dx*dx+dz*dz<64&&bx*bx+bz*bz>625&&bx*bx+bz*bz<10000){phase=14;ticks=0;}}
    if(phase==14){
     int redFormation=0;Iterator squad(n->mPlateMgr);CI_LOOP(squad){Piki* p=static_cast<Piki*>(*squad);if(p->isAlive()&&pc_p2_species(p)==P2SpeciesRed)++redFormation;}
     Piki* selected=n->mNextThrowPiki;const int preferred=pc_preferred_throw_color_for(n);
     if(ticks%15==0)std::printf("P2_WHITE_THROW_SELECTION frame=%d ticks=%d red_formation=%d preferred=%d selected_acquired=%d acquired_mode=%u acquired_state=%d\n",frames,ticks,redFormation,preferred,int(selected==acquired),unsigned(acquired->mMode),acquired->getState());
     require(ticks<180,"ordinary White throw selection timeout");
     if(n->getCurrState()->getID()==NAVISTATE_Walk&&selected==acquired&&(!redFormation||preferred==pc_throw_selection_class(acquired))&&acquired->mNavi==n&&acquired->mMode==PikiMode::FormationMode&&acquired->getState()==PIKISTATE_Normal&&acquired->isThrowable()){
      phase=8;ticks=0;std::puts("P2_WHITE_THROW_SELECTED actual_acquired=1 ordinary_DPAD=1");
     }
    }
    if(phase==8){
     require(ticks<180,"ordinary White grab timeout");
     if(n->getCurrState()->getID()==NAVISTATE_ThrowWait){
      auto* grab=static_cast<NaviThrowWaitState*>(n->getCurrState());
      require((!grab->mHeldThrowPiki||grab->mHeldThrowPiki==acquired)&&(!grab->mPendingThrowPiki||grab->mPendingThrowPiki==acquired),"native grab selected another body");
      if(grab->mHeldThrowPiki==acquired&&grab->mIsHoldingThrowPiki&&acquired->getState()==PIKISTATE_Hanged){
       phase=15;ticks=0;std::puts("P2_WHITE_THROW_HELD actual_acquired=1 ordinary_A_release_next=1");
      }
     }
    }
    if(phase==15){
     require(ticks<180,"ordinary White release timeout");
     if(acquired->getState()==PIKISTATE_Flying||acquired->getStickObject()==cargo){phase=9;ticks=0;goal=cargo->mSRT.t;std::puts("P2_WHITE_THROW_RELEASED actual_acquired=1");}
    }
    if(phase==9 && acquired->getStickObject()==cargo){phase=10;ticks=0;}
    if(phase==10 && cw==1&&acquired->mMode==PikiMode::TransportMode&&cargo->mCarrierCounter==1){
     require(!transportEnded&&pc_piki_carry_strength(acquired)==1,"sole actual White transport sequence/strength");
     float dx=cargo->mSRT.t.x-destination.x,dz=cargo->mSRT.t.z-destination.z,d=std::sqrt(dx*dx+dz*dz);
     if(!haulFrames){haulStart=cargo->mSRT.t;initialDistance=d;}
     ++haulFrames;
     std::printf("P2_WHITE_CARRY_SAMPLE frame=%d cargo_uid=%u white_uid=%u carrier_white=%d carrier_red=%d carrier_other=%d carrier_bodies=%d strength=%d native_strength=%d speed_power=%.3f mode=%u body_total=20 heads=0 x=%.4f y=%.4f z=%.4f goal_distance=%.4f\n",frames,cargoUid,whiteUid,cw,cr,other,cw+cr+other,pc_piki_carry_strength(acquired),cargo->mCarrierCounter,pc_piki_carry_power(acquired),unsigned(acquired->mMode),cargo->mSRT.t.x,cargo->mSRT.t.y,cargo->mSRT.t.z,d);
     float mx=cargo->mSRT.t.x-haulStart.x,mz=cargo->mSRT.t.z-haulStart.z;
     if(haulFrames>=10&&mx*mx+mz*mz>=900&&initialDistance-d>=20)haulProven=true;
    }
    else if(phase==10){require(haulProven,"transport ended before physical hauling proof");transportEnded=true;}
    require(!stable,"cargo reappeared after physical removal");
   }else{
    require(phase==10&&haulProven,"cargo disappeared before actual transport proof");
    auto read=[](const char* path){std::ifstream in(path,std::ios::binary);std::ostringstream out;out<<in.rdbuf();return out.str();};
    require(read("treasure-receipt.txt")=="treasure=white_carry_smoke count=1 pokos=1\n"&&read("p2-economy.txt")=="P2_ECONOMY_1\ntreasure:white_carry_smoke 1\n","production durable receipt mismatch");
    if(++stable==60){std::puts("P2_WHITE_CARRY_PASS cargo_removed=1 stable_frames=60 red=19 white=1 heads=0 bodies=20 pokos=1");std::fflush(nullptr);std::_Exit(0);}
   }
  }
  require(ticks<1600,"ordinary controller stage did not complete");return result;
 }
};
int main(int argc,char**argv){
    SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,"1");SDL_SetMainReady();pc_gpu_preference_apply();
    SDL_setenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1",1);pc_bbft_init(argc,argv);
    require(pc_pikipelago_room_preview(),"requires experimental room");
    if(!pc_window_init("White carry acceptance",960,540))return 3;
    pc_settings_init();pc_window_set_control_mode(PC_CONTROL_CLASSIC);pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);pc_window_set_window_size(960,540);pc_window_center();
    std::puts("Experimental preview window set to 960x540 windowed and centered");
    int device=SDL_JoystickAttachVirtual(SDL_JOYSTICK_TYPE_GAMECONTROLLER,SDL_CONTROLLER_AXIS_MAX,SDL_CONTROLLER_BUTTON_MAX,0);require(device>=0,"virtual gamepad attach failed");
    char guid[64];SDL_JoystickGetGUIDString(SDL_JoystickGetDeviceGUID(device),guid,sizeof(guid));std::string mapping=std::string(guid)+",White acceptance virtual pad,a:b0,b:b1,x:b2,y:b3,back:b4,guide:b5,start:b6,leftstick:b7,rightstick:b8,leftshoulder:b9,rightshoulder:b10,dpup:b11,dpdown:b12,dpleft:b13,dpright:b14,leftx:a0,lefty:a1,rightx:a2,righty:a3,lefttrigger:a4,righttrigger:a5,";require(SDL_GameControllerAddMapping(mapping.c_str())>=0,"virtual gamepad mapping failed");
    virtualPad=SDL_JoystickOpen(device);require(virtualPad!=nullptr,"virtual gamepad open failed");pc_window_input_assign(0,PC_INPUT_DEV_GAMEPAD,SDL_JoystickInstanceID(virtualPad));pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);pc_window_set_stick_invert(0);pc_window_set_cstick_invert(0);pc_window_set_gamepad_binding(PC_KEY_ACT_A,SDL_CONTROLLER_BUTTON_A);pc_window_set_gamepad_binding(PC_KEY_ACT_B,SDL_CONTROLLER_BUTTON_B);pc_window_set_gamepad_binding(PC_KEY_ACT_X,SDL_CONTROLLER_BUTTON_X);pc_window_set_gamepad_binding(PC_KEY_ACT_Y,SDL_CONTROLLER_BUTTON_Y);pc_window_set_gamepad_binding(PC_KEY_ACT_DPAD_RIGHT,SDL_CONTROLLER_BUTTON_DPAD_RIGHT);scriptedInput=new AcquisitionController();
    std::puts("P2_WHITE_INPUT_METHOD SDL_virtual_gamepad native_controller_and_UI_polling=1");
    gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new AcquisitionApp());return 0;
}
#endif
