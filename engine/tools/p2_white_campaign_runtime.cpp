// Ordinary input only. Source providers restore their own native-card state.
// This fixture never repairs actors, ownership, cargo, budgets, economy or time.
#include <SDL2/SDL.h>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <set>
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
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "PikiHeadItem.h"
#include "ItemMgr.h"
#include "UfoItem.h"
#include "GoalItem.h"
#include "Boss.h"
#include "Pom.h"
#include "Pellet.h"
#include "PlayerState.h"
#include "Demo.h"
#include "GameStat.h"
#include "BaseInf.h"
#include "Generator.h"
#include "pc_p2_white.h"
#include "pc_p2_purple.h"
#include "pc_p2_species.h"
#include "pc_p2_white_campaign_policy.h"
#include "pc_p2_white_treasure_policy.h"
#include "pc_p2_ship_store.h"
#include "pc_p2_preview.h"
#include "pc_randomizer.h"
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "p2_fixture_captain_guard.h"
#include "p2_white_campaign_input.h"

static void require(bool good,const char* why){if(!good){std::printf("P2_WHITE_CAMPAIGN_FAIL %s\n",why);std::fflush(nullptr);std::_Exit(1);}}
static unsigned uid(const Creature* p){require(p&&p->mGenerator,"original generated actor lost generator");return p->mGenerator->_70;}
static const unsigned flowerIds[]={25,28,29};
static int phase=0,phaseTick=0,frame=0,budIndex=0;
static Vector3f goal;
static SDL_Joystick* virtualPad=nullptr;
static int nativeFrameLimit=5000;
static bool saveRequested=false,dayAdvanced=false,resumeMode=false,humanMode=false,separatingReds=false;
static WhiteSaveIntent saveIntent=WhiteSaveIntent::Neutral;
static Piki* held=nullptr;
static std::set<Piki*> naturalBodies;
static Pellet* cargo=nullptr;
static int p1Before[3][3]={};
static int p1Expected[3][3]={};
static void p1Read(int (&counts)[3][3]){for(int c=0;c<3;++c)for(int m=0;m<3;++m){require(pikiInfMgr.mPikiCounts[c][m]>=0,"negative native P1 stock");counts[c][m]=pikiInfMgr.mPikiCounts[c][m];}}
static void p1Require(){for(int c=0;c<3;++c)for(int m=0;m<3;++m)require(pikiInfMgr.mPikiCounts[c][m]==p1Expected[c][m],"native all-color/maturity original Red conservation mismatch");}
static void p1Log(const char* marker){std::printf("%s b_leaf=%d b_bud=%d b_flower=%d r_leaf=%d r_bud=%d r_flower=%d y_leaf=%d y_bud=%d y_flower=%d\n",marker,pikiInfMgr.mPikiCounts[Blue][Leaf],pikiInfMgr.mPikiCounts[Blue][Bud],pikiInfMgr.mPikiCounts[Blue][Flower],pikiInfMgr.mPikiCounts[Red][Leaf],pikiInfMgr.mPikiCounts[Red][Bud],pikiInfMgr.mPikiCounts[Red][Flower],pikiInfMgr.mPikiCounts[Yellow][Leaf],pikiInfMgr.mPikiCounts[Yellow][Bud],pikiInfMgr.mPikiCounts[Yellow][Flower]);}
static void p1ResumeExpected(){const char* text=std::getenv("P2_WHITE_CAMPAIGN_EXPECT_P1_STOCK");require(text,"source paired native card P1 stock expectation missing");for(int c=0;c<3;++c)for(int m=0;m<3;++m){char* end=nullptr;long value=std::strtol(text,&end,10);require(end!=text&&value>=0&&value<=100000,"invalid paired P1 stock expectation");p1Expected[c][m]=int(value);const bool last=c==2&&m==2;require(last?!*end:*end==',',"exact nine P1 stock expectation fields required");text=last?end:end+1;}p1Require();}
static int whiteStock(){const auto& c=p2ship::stock.counts[1];return c[0]+c[1]+c[2];}
static int spent(){int total=0;for(unsigned id:flowerIds)total+=p2whitecampaign::budget.get({0,id});return total;}
static void conservedBudget(){for(unsigned id:flowerIds)require(p2whitecampaign::budget.get({0,id})==5,"three lifetime budgets not exactly five");}
static void keyRequest(int sequence,const char* key){std::printf("P2_WHITE_NATIVE_KEY_REQUEST seq=%d key=%s actual_SDL_keyboard_required=1\n",sequence,key);std::fflush(stdout);}
// Whistle radius also reaches non-target bodies. Let ordinary throws/captures
// finish before any regroup whistle, even when the intended target is grounded.
static bool unsettledAcquisition(){
 if(!pikiMgr)return true;
 Iterator actors(pikiMgr);CI_LOOP(actors){auto* p=static_cast<Piki*>(*actors);
  if(!p->isAlive()||pc_p2_species(p)!=P2SpeciesRed)continue;
  const int state=p->getState();
  if(state==PIKISTATE_Flying||state==PIKISTATE_Swallowed||state==PIKISTATE_GoHang||state==PIKISTATE_Hanged)return true;
 }
 return false;
}
bool validNaturalGrab(Piki* p,Navi* n){
 return p&&p->isAlive()&&naturalBodies.count(p)&&pc_p2_is_white(p)&&p->mNavi==n&&p->mMode==PikiMode::FormationMode&&(p->getState()==PIKISTATE_Normal||p->getState()==PIKISTATE_GoHang||p->getState()==PIKISTATE_Hanged);
}
bool unsettledWhitePluck(){
 if(!pikiMgr)return true;
 Iterator bodies(pikiMgr);CI_LOOP(bodies){auto* p=static_cast<Piki*>(*bodies);if(!p->isAlive()||!pc_p2_is_white(p))continue;
  const int state=p->getState();
  if(state==PIKISTATE_Nukare||state==PIKISTATE_NukareWait||state==PIKISTATE_Flying||state==PIKISTATE_GoHang||state==PIKISTATE_Hanged)return true;
 }
 return false;
}
class CampaignInput:public Kontroller {
public:CampaignInput():Kontroller(1){}
 void update()override{
  u32 keys=0;float stickX=0,stickY=0;Navi* n=naviMgr?naviMgr->getNavi():nullptr;
  const bool walking=n&&n->getCurrState()&&n->getCurrState()->getID()==NAVISTATE_Walk;
  if(!humanMode||phase!=30){
   if(phase==0&&frame%30<8)keys=KBBTN_A;
   if(phase==1&&phaseTick%60<20)keys=KeyConfig::_instance->mSetCursorKey.mBind;
   if(phase==3){
    // Ordinary A: keep the pending grab held, release only after actual Hanged.
    if(walking&&n->mNextThrowPiki&&n->mNextThrowPiki->isAlive()&&pc_p2_species(n->mNextThrowPiki)==P2SpeciesRed&&n->mNextThrowPiki->mNavi==n&&n->mNextThrowPiki->mMode==PikiMode::FormationMode&&n->mNextThrowPiki->getState()==PIKISTATE_Normal&&n->mNextThrowPiki->isThrowable())keys=KeyConfig::_instance->mThrowKey.mBind;
    else if(n&&n->getCurrState()&&n->getCurrState()->getID()==NAVISTATE_ThrowWait){
     auto* grab=static_cast<NaviThrowWaitState*>(n->getCurrState());
     keys=KeyConfig::_instance->mThrowKey.mBind;
     if(grab->mHeldThrowPiki&&grab->mIsHoldingThrowPiki&&grab->mHeldThrowPiki->getState()==PIKISTATE_Hanged)keys=0;
    }
   }
   if(phase==13&&walking&&phaseTick%30<15)keys=KeyConfig::_instance->mDisbandKey.mBind;
   if(phase==5&&phaseTick%60<45)keys=KeyConfig::_instance->mThrowKey.mBind;
   if(phase==14&&walking&&pc_preferred_throw_color_for(n)!=PikiColorCount+2&&phaseTick%30<2)keys=KBBTN_DPAD_RIGHT;
   if(phase==8)keys=KeyConfig::_instance->mThrowKey.mBind;
   if(phase==11&&phaseTick%60<20)keys=KeyConfig::_instance->mSetCursorKey.mBind;
   if(phase==28&&!unsettledWhitePluck()&&!unsettledAcquisition()&&phaseTick%30<20)keys=KeyConfig::_instance->mSetCursorKey.mBind;
   if(phase==27&&!unsettledWhitePluck()&&phaseTick%30<20)keys=KeyConfig::_instance->mSetCursorKey.mBind;
   if(phase==16&&!unsettledAcquisition()&&phaseTick%30<20)keys=KeyConfig::_instance->mSetCursorKey.mBind;
   const bool move=phase==2||phase==4||phase==7||phase==11||(phase==16&&!unsettledAcquisition())||(phase==27&&!unsettledWhitePluck())||(phase==28&&!unsettledWhitePluck()&&!unsettledAcquisition())||((phase==9||phase==10)&&separatingReds)||phase==17||phase==25;
   if(move&&n&&n->mNaviCamera){
    float bx=goal.x-n->mSRT.t.x,bz=goal.z-n->mSRT.t.z;
    bool walk=phase==4||phase==17||phase==25||((phase==9||phase==10)&&separatingReds)||bx*bx+bz*bz>10000;
    if(walk||phaseTick%10==0){float dx=walk?bx:goal.x-n->mCursorWorldPos.x,dz=walk?bz:goal.z-n->mCursorWorldPos.z;float length=std::sqrt(dx*dx+dz*dz);
     if(length>(walk?15.f:3.f)){const auto& axis=n->mNaviCamera->mViewXAxis;float strength=walk?65.f:22.f;stickX=strength*(dx*axis.x+dz*axis.z)/length;stickY=strength*(dx*axis.z-dz*axis.x)/length;}}
   }
   if(phase==20&&phaseTick%20<4){switch(saveIntent){case WhiteSaveIntent::Pause:keys=KBBTN_START;break;case WhiteSaveIntent::Down:stickY=-65.f;break;case WhiteSaveIntent::Up:stickY=65.f;break;case WhiteSaveIntent::Reveal:keys=KBBTN_B;break;case WhiteSaveIntent::Confirm:case WhiteSaveIntent::Advance:keys=KBBTN_A;break;default:break;}}
  }
  SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_A,int((keys&KBBTN_A)!=0));
  SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_B,int((keys&KBBTN_B)!=0));
  SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_X,int((keys&KBBTN_X)!=0));
  SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_Y,int((keys&KBBTN_Y)!=0));
  SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_START,int((keys&KBBTN_START)!=0));
  SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_DPAD_DOWN,int((keys&KBBTN_DPAD_DOWN)!=0));
  SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_DPAD_UP,int((keys&KBBTN_DPAD_UP)!=0));
  SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_DPAD_RIGHT,int((keys&KBBTN_DPAD_RIGHT)!=0));
  SDL_JoystickSetVirtualAxis(virtualPad,SDL_CONTROLLER_AXIS_LEFTX,Sint16(white_campaign_axis(int(stickX))));
  SDL_JoystickSetVirtualAxis(virtualPad,SDL_CONTROLLER_AXIS_LEFTY,Sint16(-white_campaign_axis(int(stickY))));SDL_JoystickUpdate();
 }
};
static CampaignInput* input=nullptr;
class CampaignApp:public PlugPikiApp {
 bool initialized=false,sunsetSeen=false,physical=false,transportEnded=false;
 Pom* flowers[3]={};int baselinePellets=0,haulFrames=0,stable=0,dayBefore=0,expectedDay=0;
 unsigned saveIndexBefore=0;uint64_t generationBefore=0;
 Vector3f haulStart,destination,resumeStart;float initialDistance=0;
 void next(int value){phase=value;phaseTick=0;}
public:int idle()override{
 input->update();const int result=PlugPikiApp::idle();++frame;++phaseTick;require(frame<nativeFrameLimit,"absolute native frame bound");
 if(phase==20){sunsetSeen=sunsetSeen||gameflow.mIsDayEndActive;dayAdvanced=sunsetSeen&&gameflow.mWorldClock.mCurrentDay==expectedDay;}
 Navi* n=naviMgr?naviMgr->getNavi():nullptr;
 if(n&&n->getCurrState()){
  initialized=true;if(std::getenv("P2_WHITE_CAMPAIGN_PAUSED_DOWN"))gameflow.mPauseAll=true; // Negative-only.
  p2_fixture_require_captain(GameStat::orimaDead||naviMgr->isNaviDead(n),n->getCurrState()->getID()==NAVISTATE_Dead,
   (std::getenv("P2_WHITE_CAMPAIGN_FORCE_DOWN")||std::getenv("P2_WHITE_CAMPAIGN_PAUSED_DOWN"))?0:n->mHealth,frame);
 }else if(initialized){
  const bool expectedTeardown=phase==20&&sunsetSeen&&dayAdvanced&&gameflow.mCurrGameSectionID==SECTION_OnePlayer&&flowCont.mGameEndFlag==GAMEEND_None&&whiteStock()==15;
  if(!expectedTeardown){std::puts("P2_FIXTURE_CAPTAIN_DOWN missing_initialized_captain_or_state outcome=BLOCKED");std::fflush(nullptr);std::_Exit(86);}
 }
 if(phase!=20&&gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(phase==20){
  require(gameflow.mWorldClock.mCurrentDay<=expectedDay&&flowCont.mGameEndFlag==GAMEEND_None,"unexpected day/endgame transition");
  auto pause=pc_pause_observe();auto save=pc_save_ui_observe();const auto diary=pc_diary_observe();saveIntent=white_save_intent(saveRequested,dayAdvanced,pause,diary,save);
  if(frame%60==0)std::printf("P2_WHITE_CAMPAIGN_SAVE_UI frame=%d phase_tick=%d day=%d expected_day=%d requested=%d sunset=%d advanced=%d intent=%d pause_available=%d pause_state=%d main_ready=%d main_selection=%d sub_ready=%d sub_selection=%d diary=%d save_available=%d result_state=%d save_state=%d results_ready=%d primary_ready=%d primary_yes=%d secondary_ready=%d slot_ready=%d slot=%d memory_available=%d outer_memory_routed=%d default_available=%d memory_state=%d default_state=%d successful=%d typing_complete=%d confirmation_ready=%d nested_blocked=%d failure_available=%d failure_inactive=%d file_available=%d file_state=%d file_selection=%d\n",frame,phaseTick,gameflow.mWorldClock.mCurrentDay,expectedDay,int(saveRequested),int(sunsetSeen),int(dayAdvanced),int(saveIntent),int(pause.available),pause.state,int(pause.mainInputReady),pause.mainSelection,int(pause.sunsetInputReady),pause.subSelection,int(diary),int(save.available),save.resultState,save.saveState,int(save.resultsInputReady),int(save.primaryInputReady),int(save.primaryYes),int(save.secondaryInputReady),int(save.cardSlotInputReady),save.cardSlot,int(save.memoryAvailable),int(save.outerMemoryRouted),int(save.defaultFile.available),save.defaultFile.memoryState,save.defaultFile.state,int(save.defaultFile.successful),int(save.defaultFile.typingComplete),int(save.defaultFile.confirmationReady),int(save.nestedUiBlocked),int(save.failureAvailable),int(save.failureInactive),int(save.fileAvailable),save.fileState,int(save.fileSelection));
  require(saveIntent!=WhiteSaveIntent::Refuse,"unexpected actual native save UI choice");
  if(pause.available)saveRequested=true;
  conservedBudget();require(whiteStock()==15&&p2whitetreasure::ledger.total()==180,"stock/budget/receipt changed during native day SAVE");
  uint64_t generation=0;uint8_t hash[32];
  if(dayAdvanced&&gameflow.mGamePrefs.mHasSaveGame&&gameflow.mGamePrefs.mMostRecentSaveIndex!=saveIndexBefore&&pc_randomizer_checkpoint_info(&generation,hash)&&generation==generationBefore+1){
   p1Require();p1Log("P2_WHITE_CAMPAIGN_P1_SAVE_STOCK");std::printf("P2_WHITE_CAMPAIGN_SAVE_PASS day_before=%d day=%d stock=15 white_leaf=15 spent=15 pokos=180 generation=%llu native_save_index_before=%u native_save_index_after=%u external_CAMPAIGN_SAVED_required=1 fresh_process_resume_pending=1\n",dayBefore,expectedDay,(unsigned long long)generation,saveIndexBefore,unsigned(gameflow.mGamePrefs.mMostRecentSaveIndex));std::fflush(nullptr);std::_Exit(0);
  }
  return result;
 }
 if(!n||!n->getCurrState()||!pikiMgr||!itemMgr||gameflow.mPauseAll||gameflow.mIsUIOverlayActive||frame<90)return result;
 require(!pc_pikipelago_room_preview()&&pc_randomizer_white_campaign()&&pc_randomizer_white_treasure_campaign(),"ordinary White/retail campaign required");
 int red=0,white=0,heads=0,followers=0,whiteFollowers=0,carriers=0;bool cargoSlot=false;PikiHeadItem* head=nullptr;
 std::set<unsigned> originals;std::set<Piki*> whites;
 Iterator bodies(pikiMgr);CI_LOOP(bodies){Piki* p=static_cast<Piki*>(*bodies);if(!p->isAlive())continue;
  if(pc_p2_is_white(p)){++white;whites.insert(p);require(p->mHappa==Leaf,"natural/resumed White maturity changed");if((phase>=7&&phase<18)||phase==26||phase==27||phase==28)require(naturalBodies.count(p),"natural White pointer membership changed");}
  else{require(pc_p2_species(p)==P2SpeciesRed&&p->mHappa==Leaf,"unexpected ordinary species/Red maturity");++red;if(!resumeMode)require(p->mGenerator&&uid(p)>=1&&uid(p)<=20&&originals.insert(uid(p)).second,"original Red identity changed");}
  if(p->mMode==PikiMode::FormationMode&&p->mNavi==n){++followers;if(pc_p2_is_white(p))++whiteFollowers;}
  if(cargo&&p->getStickObject()==cargo){const bool valid=pc_p2_is_white(p)&&naturalBodies.count(p)&&p->mMode==PikiMode::TransportMode&&pc_piki_carry_strength(p)==1&&std::abs(pc_piki_carry_power(p)-3)<.001;
   if(!valid){int ordinal=0,actualOrdinal=0;for(auto* original:naturalBodies){++ordinal;if(original==p)actualOrdinal=ordinal;}
    std::printf("P2_WHITE_CAMPAIGN_ATTACHMENT_REFUSAL frame=%d phase=%d generated_uid=%u natural_ordinal=%d species=%d natural_member=%d mode=%d expected_transport_mode=%d state=%d alive=%d owned=%d strength=%d speed_power=%.6f cargo_state=%d cargo_alive=%d cargo_visible=%d native_strength=%d actor_x=%.4f actor_y=%.4f actor_z=%.4f cargo_x=%.4f cargo_y=%.4f cargo_z=%.4f\n",frame,phase,p->mGenerator?uid(p):0,actualOrdinal,int(pc_p2_species(p)),int(naturalBodies.count(p)),p->mMode,int(PikiMode::TransportMode),p->getState(),int(p->isAlive()),int(p->mNavi==n),pc_piki_carry_strength(p),pc_piki_carry_power(p),cargo->getState(),int(cargo->isAlive()),int(cargo->isVisible()),cargo->mCarrierCounter,p->mSRT.t.x,p->mSRT.t.y,p->mSRT.t.z,cargo->mSRT.t.x,cargo->mSRT.t.y,cargo->mSRT.t.z);
   }
   require(valid,"cargo attached non-natural White or wrong strength/speed/mode");++carriers;
  }
 }
 Iterator sprouts(itemMgr->getPikiHeadMgr());CI_LOOP(sprouts){auto* p=static_cast<PikiHeadItem*>(*sprouts);if(!p->isAlive())continue;require(pc_p2_species(p)==P2SpeciesWhite,"unexpected sprout species");++heads;if(p->canPullout()&&!head)head=p;}
 Iterator pellets(pelletMgr);int pelletCount=0;CI_LOOP(pellets){auto* p=static_cast<Pellet*>(*pellets);if(p==cargo)cargoSlot=true;if(p->isAlive())++pelletCount;}
 if(frame%60==0)std::printf("P2_WHITE_CAMPAIGN_OBSERVATION frame=%d phase=%d red=%d white=%d heads=%d stock=%d spent=%d followers=%d carriers=%d pokos=%d nstate=%d\n",frame,phase,red,white,heads,whiteStock(),spent(),whiteFollowers,carriers,p2whitetreasure::ledger.total(),n->getCurrState()->getID());
 if((phase==3||phase==16)&&frame%60==0){
  auto* grab=n->getCurrState()->getID()==NAVISTATE_ThrowWait?static_cast<NaviThrowWaitState*>(n->getCurrState()):nullptr;
  Piki* heldRed=grab?grab->mHeldThrowPiki:nullptr;Piki* pendingRed=grab?grab->mPendingThrowPiki:nullptr;
  std::printf("P2_WHITE_CAMPAIGN_ACQUIRE_INPUT frame=%d nstate=%d n_x=%.4f n_z=%.4f cursor_x=%.4f cursor_z=%.4f red_formation=%d held_uid=%u held_state=%d pending_uid=%u pending_state=%d actual_holding=%d\n",frame,n->getCurrState()->getID(),n->mSRT.t.x,n->mSRT.t.z,n->mCursorWorldPos.x,n->mCursorWorldPos.z,followers-whiteFollowers,heldRed&&heldRed->mGenerator?uid(heldRed):0,heldRed?heldRed->getState():-1,pendingRed&&pendingRed->mGenerator?uid(pendingRed):0,pendingRed?pendingRed->getState():-1,grab?int(grab->mIsHoldingThrowPiki):0);
  Iterator redBodies(pikiMgr);CI_LOOP(redBodies){auto* p=static_cast<Piki*>(*redBodies);if(!p->isAlive()||pc_p2_species(p)!=P2SpeciesRed)continue;std::printf("P2_WHITE_CAMPAIGN_RED_BODY uid=%u mode=%d state=%d owned=%d x=%.4f y=%.4f z=%.4f\n",uid(p),p->mMode,p->getState(),int(p->mNavi==n),p->mSRT.t.x,p->mSRT.t.y,p->mSRT.t.z);}
 }
 if(phase==0){
  if(n->getCurrState()->getID()==NAVISTATE_Starting)return result;
  int width,height,x,y;auto* window=SDL_GL_GetCurrentWindow();SDL_GetWindowSize(window,&width,&height);SDL_GetWindowPosition(window,&x,&y);SDL_Rect bounds{};SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window),&bounds);
  const bool center=std::abs(x-(bounds.x+(bounds.w-width)/2))<=2&&std::abs(y-(bounds.y+(bounds.h-height)/2))<=2;require(width==960&&height==540&&center,"actual centered960x540 required");std::printf("P2_WHITE_CAMPAIGN_WINDOW width=%d height=%d centered=%d\n",width,height,int(center));
  // One setup-only tutorial flag pass, disclosed; no later live flags writes.
  for(int flag=0;flag<DEMOFLAG_COUNT;++flag)playerState->mDemoFlags.setFlagOnly(flag);
  Iterator bosses(bossMgr);CI_LOOP(bosses){auto* boss=static_cast<Boss*>(*bosses);if(boss->mObjType!=OBJTYPE_Pom||!boss->mGenerator)continue;for(int i=0;i<3;++i)if(uid(boss)==flowerIds[i]){require(!flowers[i]&&pc_p2_ivory(static_cast<Pom*>(boss)),"Ivory source identity duplicates/mismatch");flowers[i]=static_cast<Pom*>(boss);}}
  auto* receiver=itemMgr->getContainer(Red);require(receiver&&uid(receiver)==23&&pc_p2_preview_is_pod(receiver),"source receiver missing");destination=receiver->mSRT.t;
  if(resumeMode){p1ResumeExpected();require(red==0,"fresh resume duplicated original Red field bodies");p1Log("P2_WHITE_CAMPAIGN_P1_RESUME_STOCK");require(pc_randomizer_resumed()&&whiteStock()==15&&p2ship::stock.counts[1][Leaf]==15&&white==0&&heads==0&&p2whitetreasure::ledger.total()==180,"fresh native resume stock/maturity/ledger mismatch");conservedBudget();
   const char* expected=std::getenv("P2_WHITE_CAMPAIGN_EXPECT_DAY");char* end=nullptr;long day=expected?std::strtol(expected,&end,10):0;require(expected&&end&&!*end&&day>0&&day==gameflow.mWorldClock.mCurrentDay,"fresh native resumed day mismatch");
   Iterator source(pelletMgr);CI_LOOP(source){auto* p=static_cast<Pellet*>(*source);require(!p->isAlive()||!p->mGenerator||uid(p)!=26,"consumed retail source respawned on resume");}
   goal=itemMgr->getUfo()->getGoalPos();next(17);std::puts("P2_WHITE_CAMPAIGN_RESUME_BASELINE stock=15 leaf=15 spent=15 pokos=180 consumed_source_absent=1 native_checkpoint_resumed=1");return result;
  }
  p1Read(p1Before);for(int c=0;c<3;++c)for(int m=0;m<3;++m)p1Expected[c][m]=p1Before[c][m];p1Expected[Red][Leaf]+=5;p1Log("P2_WHITE_CAMPAIGN_P1_BEFORE_STOCK");
  require(red==20&&white==0&&heads==0&&spent()==0&&whiteStock()==0&&!p2whitetreasure::ledger.delivered,"fresh20Red/bud/stock/economy baseline required");for(auto* flower:flowers)require(flower&&flower->isAlive(),"three source Ivory buds required");
  Iterator source(pelletMgr);CI_LOOP(source){auto* p=static_cast<Pellet*>(*source);if(p->isAlive()&&p->mGenerator&&uid(p)==26){require(!cargo,"duplicate original source cargo");cargo=p;cargoSlot=true;}}
  require(cargo&&cargo->mConfig&&cargo->mConfig->mCarryMinPikis()==15&&cargo->mConfig->mCarryMaxPikis()==25,"original retail15/max25 profile required");baselinePellets=pelletCount;
  std::puts("P2_WHITE_CAMPAIGN_BASELINE red=20 white=0 heads=0 stock=0 ivory=3 spent=0 cargo_uid=26 minimum=15 maximum=25 value=180");
  if(std::getenv("P2_WHITE_CAMPAIGN_READY_ONLY")){std::puts("P2_WHITE_CAMPAIGN_READY_PASS");std::fflush(nullptr);std::_Exit(0);}next(1);
 }
 if(!resumeMode){require(red+white+heads+whiteStock()==20,"ordinary population lost/duplicated");require(white+heads+whiteStock()<=15,"more than15 natural Whites");require(carriers<=15,"more than15 actual White carriers");
  if(phase<10||phase==16||phase==26||phase==27||phase==28){require(cargoSlot&&uid(cargo)==26&&cargo->isAlive()&&pelletCount==baselinePellets&&!p2whitetreasure::ledger.delivered,"cargo/receipt changed before physical hauling phase");}
  if(phase<7||phase==26||phase==27||phase==28)require(carriers==0,"premature ordinary cargo attachment");
 }else{p1Require();require(red==0&&white+whiteStock()==15&&heads==0,"fresh resumed original20 lineage lost/duplicated or unexpected Red bodies");}

 if(phase==1&&phaseTick>=30&&followers==20){goal=flowers[budIndex]->mSRT.t;next(2);}
 if(phase==2){float x=goal.x-n->mCursorWorldPos.x,z=goal.z-n->mCursorWorldPos.z;float bx=goal.x-n->mSRT.t.x,bz=goal.z-n->mSRT.t.z;if(x*x+z*z<64&&bx*bx+bz*bz>625){next(6);}}
 if(phase==6&&phaseTick>=20){float x=goal.x-n->mCursorWorldPos.x,z=goal.z-n->mCursorWorldPos.z;next(x*x+z*z<64?3:2);}
 if(phase==3&&p2whitecampaign::budget.get({0,flowerIds[budIndex]})==5&&red==20-5*(budIndex+1)&&heads==5*(budIndex+1)){
  std::printf("P2_WHITE_CAMPAIGN_IVORY_COMPLETE uid=%u natural_outputs=5 red=%d white_heads=%d spent=%d\n",flowerIds[budIndex],red,heads,spent());
  if(++budIndex<3){goal=flowers[budIndex]->mSRT.t;next(2);}else{conservedBudget();next(13);}
 }
 // A natural conversion can leave original Reds free; whistle the actual
 // unjoined body under the cursor before attempting another ordinary grab.
 if((phase==16||(phase==3&&n->getCurrState()->getID()==NAVISTATE_Walk&&!unsettledAcquisition()))&&followers-whiteFollowers<red){
  Iterator unjoined(pikiMgr);CI_LOOP(unjoined){auto* p=static_cast<Piki*>(*unjoined);if(p->isAlive()&&pc_p2_species(p)==P2SpeciesRed&&p->mMode==PikiMode::FreeMode&&p->getState()==PIKISTATE_Normal){goal=p->mSRT.t;if(phase==3)next(16);break;}}
 }
 if(phase==16&&followers-whiteFollowers==red){goal=flowers[budIndex]->mSRT.t;next(2);}
 if(phase==13&&phaseTick>=30&&followers==0&&n->getCurrState()->getID()==NAVISTATE_Walk){next(4);}
 if(phase==4&&head){goal=head->mSRT.t;float x=goal.x-n->mSRT.t.x,z=goal.z-n->mSRT.t.z;if(x*x+z*z<225)next(5);}
 if(phase==5){if(head){float x=head->mSRT.t.x-n->mSRT.t.x,z=head->mSRT.t.z-n->mSRT.t.z;if(x*x+z*z>400&&n->getCurrState()->getID()==NAVISTATE_Walk){goal=head->mSRT.t;next(4);}}
  else if(white==15&&heads==0){require(red==5,"ordinary fifteen plucks/conservation required");naturalBodies=whites;conservedBudget();next(26);}
 }
 if(phase==26||phase==27){
  require(red==5&&white==15&&heads==0,"ordinary fifteen plucked adults changed");
  if(frame%30==0){int ordinal=0;for(auto* p:whites)std::printf("P2_WHITE_CAMPAIGN_PLUCK_BODY frame=%d ordinal=%d generated_uid=%u mode=%d state=%d owned=%d formation=%d x=%.4f y=%.4f z=%.4f\n",frame,++ordinal,p->mGenerator?uid(p):0,p->mMode,p->getState(),int(p->mNavi==n),int(p->mMode==PikiMode::FormationMode&&p->mNavi==n),p->mSRT.t.x,p->mSRT.t.y,p->mSRT.t.z);}
  if(phaseTick>=30&&n->getCurrState()->getID()==NAVISTATE_Walk&&!unsettledWhitePluck()&&whiteFollowers<15){for(auto* p:whites)if(p->mMode==PikiMode::FreeMode&&p->getState()==PIKISTATE_Normal){goal=p->mSRT.t;if(phase==26)next(27);break;}}
  if(phaseTick>=30&&!unsettledWhitePluck()&&n->getCurrState()->getID()==NAVISTATE_Walk&&whiteFollowers==15){require(red==5&&whiteFollowers==15,"ordinary fifteen plucks/formation required");std::puts("P2_WHITE_CAMPAIGN_ACQUIRED red=5 white=15 heads=0 body_total=20 spent=15 ordinary_birth_pluck=1");if(humanMode){next(30);pc_window_input_assign(0,PC_INPUT_DEV_KEYBOARD,-1);std::puts("P2_WHITE_CAMPAIGN_HUMAN_READY natural_white=15 repair_writes=0 user_gameplay=1 keyboard_routing_restored=1");}else{next(28);}}
 }
 if(phase==28){
  require(red==5&&white==15&&heads==0&&whiteFollowers==15,"ordinary full squad changed before Red separation");
  if(followers-whiteFollowers<5){Iterator unjoined(pikiMgr);CI_LOOP(unjoined){auto* p=static_cast<Piki*>(*unjoined);if(p->isAlive()&&pc_p2_species(p)==P2SpeciesRed&&p->mMode==PikiMode::FreeMode&&p->getState()==PIKISTATE_Normal){goal=p->mSRT.t;break;}}}
  if(frame%30==0)std::printf("P2_WHITE_CAMPAIGN_RED_REGROUP frame=%d original_red=%d red_formation=%d natural_white_formation=%d target_x=%.4f target_z=%.4f\n",frame,red,followers-whiteFollowers,whiteFollowers,goal.x,goal.z);
  if(phaseTick>=30&&n->getCurrState()->getID()==NAVISTATE_Walk&&!unsettledWhitePluck()&&!unsettledAcquisition()&&followers-whiteFollowers==5){goal=cargo->mSRT.t;next(7);}
 }
 if(phase==7){goal=cargo->mSRT.t;float x=goal.x-n->mCursorWorldPos.x,z=goal.z-n->mCursorWorldPos.z;float bx=goal.x-n->mSRT.t.x,bz=goal.z-n->mSRT.t.z;if(x*x+z*z<64&&bx*bx+bz*bz>625&&bx*bx+bz*bz<10000)next(14);}
 if(phase==14){Piki* selected=n->mNextThrowPiki;
  if(phaseTick%15==0)std::printf("P2_WHITE_CAMPAIGN_THROW_PREFERENCE frame=%d phase_tick=%d preferred=%d expected_white=%d preview_class=%d preview_state=%d preview_natural=%d\n",frame,phaseTick,pc_preferred_throw_color_for(n),PikiColorCount+2,selected?pc_throw_selection_class(selected):-1,selected?selected->getState():-1,int(selected&&naturalBodies.count(selected)));
  if(phaseTick>=15&&phaseTick%30>=5&&pc_preferred_throw_color_for(n)==PikiColorCount+2&&n->getCurrState()->getID()==NAVISTATE_Walk&&selected&&naturalBodies.count(selected)&&selected->mNavi==n&&selected->mMode==PikiMode::FormationMode&&selected->getState()==PIKISTATE_Normal&&selected->isThrowable()){held=nullptr;next(8);}}
 if(phase==8&&n->getCurrState()->getID()==NAVISTATE_ThrowWait){
  auto* grab=static_cast<NaviThrowWaitState*>(n->getCurrState());Piki* actual=grab->mHeldThrowPiki?grab->mHeldThrowPiki:grab->mPendingThrowPiki;
  if(!held&&actual){
   int ordinal=0,actualOrdinal=0;for(auto* p:naturalBodies){++ordinal;if(p==actual)actualOrdinal=ordinal;}
   std::printf("P2_WHITE_CAMPAIGN_ACTUAL_GRAB frame=%d natural_ordinal=%d species=%d mode=%d state=%d owned=%d actual_holding=%d pending=%d preferred=%d x=%.4f y=%.4f z=%.4f\n",frame,actualOrdinal,int(pc_p2_species(actual)),actual->mMode,actual->getState(),int(actual->mNavi==n),int(grab->mIsHoldingThrowPiki),int(grab->mPendingThrowPiki!=nullptr),pc_preferred_throw_color_for(n),actual->mSRT.t.x,actual->mSRT.t.y,actual->mSRT.t.z);
   require(validNaturalGrab(actual,n),"actual native grab is not an eligible natural White");held=actual;
  }
  require((!grab->mHeldThrowPiki||grab->mHeldThrowPiki==held)&&(!grab->mPendingThrowPiki||grab->mPendingThrowPiki==held),"ordinary actual White grab pointer changed");
  if(held&&grab->mHeldThrowPiki==held&&grab->mIsHoldingThrowPiki&&held->getState()==PIKISTATE_Hanged)next(15);
 }
 if(phase==15&&held->getState()==PIKISTATE_Flying&&carriers==14){
  require(red==5&&followers-whiteFollowers==5,"all five original Reds must follow before ordinary separation");
  // The final projectile is already in native flight. Move the captain and
  // Red squad toward unchanged source route5 while cargo takes its own route.
  separatingReds=true;goal.set(110.f,0.f,-110.f);
  std::printf("P2_WHITE_CAMPAIGN_SEPARATION_BEGIN frame=%d original_red=5 red_formation=5 flying_natural_white=1 attached_white=14 source_route=5 target_x=110 target_z=-110 captain_x=%.4f captain_z=%.4f\n",frame,n->mSRT.t.x,n->mSRT.t.z);
 }
 if(phase==15&&(held->getState()==PIKISTATE_Flying||held->getStickObject()==cargo))next(9);
 if(phase==9&&held->getStickObject()==cargo){if(carriers==15){require(separatingReds,"final natural White flight not observed before separation");next(10);}else next(14);}
 if(phase==10){
  if(frame%30==0)std::printf("P2_WHITE_CAMPAIGN_SEPARATION_WALK frame=%d red_formation=%d captain_x=%.4f captain_z=%.4f target_x=%.4f target_z=%.4f\n",frame,followers-whiteFollowers,n->mSRT.t.x,n->mSRT.t.z,goal.x,goal.z);
  if(cargoSlot&&cargo->isAlive()&&carriers==15&&cargo->mCarrierCounter==15){require(!transportEnded,"retail transport resumed after interruption");float x=cargo->mSRT.t.x-destination.x,z=cargo->mSRT.t.z-destination.z,d=std::sqrt(x*x+z*z);if(!haulFrames){haulStart=cargo->mSRT.t;initialDistance=d;}++haulFrames;
   std::printf("P2_WHITE_CAMPAIGN_HAUL frame=%d cargo_uid=26 white=15 red=0 others=0 strength=15 native_strength=%d x=%.4f y=%.4f z=%.4f goal_distance=%.4f natural_body_total=20\n",frame,cargo->mCarrierCounter,cargo->mSRT.t.x,cargo->mSRT.t.y,cargo->mSRT.t.z,d);
   float hx=cargo->mSRT.t.x-haulStart.x,hz=cargo->mSRT.t.z-haulStart.z;if(haulFrames>=10&&hx*hx+hz*hz>=900&&initialDistance-d>=20)physical=true;
  }else{require(physical,"native retail transport ended before sustained physical proof");transportEnded=true;}
  if(!cargoSlot||!cargo->isAlive()){require(physical&&p2whitetreasure::ledger.total()==180,"actual physical removal/once retail callback required");if(++stable==60){next(11);std::puts("P2_WHITE_CAMPAIGN_DELIVERED cargo_removed=1 pokos=180 stable_frames=60 natural_white=15");}}
 }
 if(phase==11){if(whiteFollowers==15){goal=itemMgr->getUfo()->getGoalPos();next(17);}else{for(Piki* p:whites)if(p->mMode!=PikiMode::FormationMode){goal=p->mSRT.t;break;}}}
 if(phase==17){goal=itemMgr->getUfo()->getGoalPos();float x=goal.x-n->mSRT.t.x,z=goal.z-n->mSRT.t.z;if(x*x+z*z<10000){if(resumeMode){keyRequest(1,"CTRL_F10");next(22);}else{keyRequest(1,"SHIFT_F10");next(18);}}}
 if(phase==18&&whiteStock()==15&&white==0){require(p2ship::stock.counts[1][Leaf]==15&&red==5&&heads==0,"ordinary ship deposit conservation");dayBefore=gameflow.mWorldClock.mCurrentDay;expectedDay=pc_randomizer_next_day(dayBefore);require(expectedDay==dayBefore+1,"ordinary next day required");saveIndexBefore=gameflow.mGamePrefs.mMostRecentSaveIndex;uint8_t hash[32];pc_randomizer_checkpoint_info(&generationBefore,hash);next(20);saveRequested=false;saveIntent=WhiteSaveIntent::Pause;std::puts("P2_WHITE_CAMPAIGN_SAVE_BEGIN actual_pause_day_UI_only=1 no_clock_write=1");}
 if(phase==22&&phaseTick>=30){keyRequest(2,"F10");next(23);}
 if(phase==23){require(whiteStock()+white==15&&heads==0&&p2whitetreasure::ledger.total()==180,"resumed ordinary withdrawal conservation");if(white==15&&whiteStock()==0){require(whiteFollowers==15,"resumed fifteen Whites not usable formation");naturalBodies=whites;resumeStart=n->mSRT.t;goal=resumeStart;goal.x+=60;next(25);}else if(phaseTick%20==0)keyRequest(2+phaseTick/20,"F10");}
 if(phase==25){float x=n->mSRT.t.x-resumeStart.x,z=n->mSRT.t.z-resumeStart.z;if(x*x+z*z>900&&white==15&&whiteFollowers==15){conservedBudget();std::printf("P2_WHITE_CAMPAIGN_RESUME_PASS day=%d white=15 stock=0 leaf=15 spent=15 pokos=180 original_red_conserved=5 original_white_conserved=15 original_population=20 red_field=0 displacement=%.4f native_checkpoint_resumed=1 ordinary_ship_keyboard=1\n",gameflow.mWorldClock.mCurrentDay,std::sqrt(x*x+z*z));std::fflush(nullptr);std::_Exit(0);}}
 require(phaseTick<1600,"ordinary bounded input phase timeout");return result;
 }
};
int main(int argc,char** argv){
 setvbuf(stdout,nullptr,_IONBF,0);SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,"1");SDL_SetMainReady();pc_gpu_preference_apply();pc_bbft_init(argc,argv);
 require(pc_randomizer_enabled()&&pc_randomizer_white_campaign()&&pc_randomizer_white_treasure_campaign()&&!pc_pikipelago_room_preview(),"explicit ordinary White/retail seed required");
 resumeMode=std::getenv("P2_WHITE_CAMPAIGN_RESUME")!=nullptr;humanMode=std::getenv("P2_WHITE_CAMPAIGN_HUMAN")!=nullptr;require(!(resumeMode&&humanMode),"fixed modes exclusive");
 if(!resumeMode&&!humanMode&&!std::getenv("P2_WHITE_CAMPAIGN_READY_ONLY")&&!std::getenv("P2_WHITE_CAMPAIGN_FORCE_DOWN")&&!std::getenv("P2_WHITE_CAMPAIGN_PAUSED_DOWN"))nativeFrameLimit=7200;
 if(!pc_window_init("White retail campaign acceptance",960,540))return 3;pc_settings_init();pc_window_set_control_mode(PC_CONTROL_CLASSIC);pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);pc_window_set_window_size(960,540);pc_window_center();std::puts("Experimental preview window set to 960x540 windowed and centered");
 int device=SDL_JoystickAttachVirtual(SDL_JOYSTICK_TYPE_GAMECONTROLLER,SDL_CONTROLLER_AXIS_MAX,SDL_CONTROLLER_BUTTON_MAX,0);require(device>=0,"ordinary virtual pad attach failed");
 char guid[64];SDL_JoystickGetGUIDString(SDL_JoystickGetDeviceGUID(device),guid,sizeof(guid));std::string mapping=std::string(guid)+",White campaign pad,a:b0,b:b1,x:b2,y:b3,back:b4,guide:b5,start:b6,leftstick:b7,rightstick:b8,leftshoulder:b9,rightshoulder:b10,dpup:b11,dpdown:b12,dpleft:b13,dpright:b14,leftx:a0,lefty:a1,rightx:a2,righty:a3,lefttrigger:a4,righttrigger:a5,";require(SDL_GameControllerAddMapping(mapping.c_str())>=0,"ordinary virtual pad mapping failed");
 virtualPad=SDL_JoystickOpen(device);require(virtualPad,"virtual pad open failed");pc_window_input_assign(0,PC_INPUT_DEV_GAMEPAD,SDL_JoystickInstanceID(virtualPad));pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);pc_window_set_stick_invert(0);pc_window_set_cstick_invert(0);
 const int actions[]={PC_KEY_ACT_A,PC_KEY_ACT_B,PC_KEY_ACT_X,PC_KEY_ACT_Y,PC_KEY_ACT_START,PC_KEY_ACT_DPAD_UP,PC_KEY_ACT_DPAD_DOWN,PC_KEY_ACT_DPAD_RIGHT};
 const int buttons[]={SDL_CONTROLLER_BUTTON_A,SDL_CONTROLLER_BUTTON_B,SDL_CONTROLLER_BUTTON_X,SDL_CONTROLLER_BUTTON_Y,SDL_CONTROLLER_BUTTON_START,SDL_CONTROLLER_BUTTON_DPAD_UP,SDL_CONTROLLER_BUTTON_DPAD_DOWN,SDL_CONTROLLER_BUTTON_DPAD_RIGHT};for(int i=0;i<8;++i)pc_window_set_gamepad_binding(actions[i],buttons[i]);
 input=new CampaignInput();std::puts("P2_WHITE_CAMPAIGN_INPUT SDL_virtual_gamepad=1 ship_actual_OS_keyboard_requests=1 repair_writes=0 bounded_native_process_deadline_required=1");gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new CampaignApp());return 0;
}
