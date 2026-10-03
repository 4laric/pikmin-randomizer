// Ordinary input only. Source providers restore their own native-card state.
// This fixture never repairs actors, ownership, cargo, budgets, economy or time.
#include <SDL2/SDL.h>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <set>
#include <vector>
#include <map>
#include <string>
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
#include "Collision.h"
#include "Kontroller.h"
#include "Camera.h"
#include "KeyConfig.h"
#include "pc_world_map_observer.h"
#include "pc_pad_bindings.h"
#include "pc_window.h"
#include "zen/ogSave.h"
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

#include "teki.h"
#include "pc_p2_white_poison.h"

static void require(bool ok,const char*why){if(!ok){std::printf("P2_WHITE_ADULT_FAIL %s\n",why);std::fflush(nullptr);std::_Exit(1);}}
static constexpr unsigned PredatorUID=436207616u;
static int phase=0,tick=0,frame=0,sequence=0,lastStock=15,ackTick=0,consumed=0;
static int grabRetries=0;
static bool initialized=false;static SDL_Joystick* virtualPad=nullptr;
static Vector3f goal;static Teki* originalPredator=nullptr;static Piki* held=nullptr;
static std::set<Piki*> restored,captured,lost;static std::set<Pellet*> baselinePellets;
static PcWorldMapResumeInput mapInput;
static int whiteStock(){const auto&c=p2ship::stock.counts[1];return c[0]+c[1]+c[2];}
static bool settled(int state){return state==NAVISTATE_Walk||state==NAVISTATE_Idle;}
static void next(int value){phase=value;tick=0;}
static void request(const char*key){std::printf("P2_WHITE_NATIVE_KEY_REQUEST seq=%d key=%s actual_SDL_keyboard_required=1\n",++sequence,key);std::fflush(nullptr);}
static bool retryBody(Piki*p,Navi*n){
 return p&&p->isAlive()&&restored.count(p)&&!captured.count(p)&&pc_p2_is_white(p)&&p->mNavi==n&&p->mMode==PikiMode::FormationMode&&p->getState()==PIKISTATE_Normal&&p->isCreatureFlag(CF_IsOnGround)&&!p->isHolding()&&!p->isStickTo()&&p->getStickObject()==nullptr;
}
// Mirrors the ordinary A action priority using current manager objects only.
static bool actionClear(const Vector3f&position,bool disclose,float margin=0.f){
 auto*ship=itemMgr?itemMgr->getUfo():nullptr;if(!ship||!pelletMgr)return false;
 const float shipDx=ship->mSRT.t.x-position.x,shipDz=ship->mSRT.t.z-position.z;
 if(shipDx*shipDx+shipDz*shipDz<=(50.f+margin)*(50.f+margin)){if(disclose)std::printf("P2_WHITE_ADULT_ACTION_BLOCK ship x=%.3f z=%.3f\n",ship->mSRT.t.x,ship->mSRT.t.z);return false;}
 Iterator current(pelletMgr);CI_LOOP(current){auto*p=static_cast<Pellet*>(*current);if(!p->mConfig)continue;
  if(p->mConfig->mPelletType()!=PELTYPE_UfoPart||!p->onGround()||p->getState()!=0)continue;
  const auto shipPosition=ship->getGoalPos();float dx=p->mSRT.t.x-shipPosition.x,dz=p->mSRT.t.z-shipPosition.z;
  if(dx*dx+dz*dz<900&&p->mCarrierCounter!=0)continue;
  dx=p->mSRT.t.x-position.x;dz=p->mSRT.t.z-position.z;float radius=p->getBottomRadius()+20.f+margin;
  if(dx*dx+dz*dz<=radius*radius){if(disclose)std::printf("P2_WHITE_ADULT_ACTION_BLOCK part=%p model=%u x=%.3f z=%.3f bottom_radius=%.3f native_action_range=20\n",(void*)p,p->mConfig->mModelId.mId,p->mSRT.t.x,p->mSRT.t.z,p->getBottomRadius());return false;}
 }
 return true;
}
class Input:public Kontroller{
public:Input():Kontroller(1){}
 void update()override{
  u32 keys=0;int sx=0,sy=0;Navi*n=naviMgr?naviMgr->getNavi():nullptr;
  if(phase==0){
   auto map=pc_world_map_observe();auto action=mapInput.observe(map,gsys->mTotalFrames,pc_randomizer_start_stage());
   require(action!=PcWorldMapInput::Refuse,"actual owned Forest map input refused");
   if(action==PcWorldMapInput::Confirm)keys=KBBTN_A;
   if(action==PcWorldMapInput::Left||action==PcWorldMapInput::Right||action==PcWorldMapInput::Up||action==PcWorldMapInput::Down){
    const int invert=pc_window_get_stick_invert(),deadzone=pc_window_get_stick_dead_zone();
    require(pc_world_map_stick_command(action,invert,deadzone,true,false,sx,sy),"native map loaded direction unsupported");
    int bindings[PC_KEY_ACT_COUNT];for(int i=0;i<PC_KEY_ACT_COUNT;++i)bindings[i]=pc_window_get_gamepad_binding(i);
    PcPadRoute route;pc_pad_route_build(bindings,&route,invert,pc_window_get_cstick_invert());
    PcPadRaw raw={};raw.axis[SDL_CONTROLLER_AXIS_LEFTX]=sx*256;raw.axis[SDL_CONTROLLER_AXIS_LEFTY]=-sy*256;
    const int nx=(invert&1)?-sx:sx,ny=(invert&2)?-sy:sy;
    bool live=pc_pad_route_stick_live(route.stick,nx?nx:ny,nx==0),extra=false;
    for(int i=0;i<PC_KEY_ACT_COUNT;++i)if((i<PC_KEY_ACT_STICK_UP||i>PC_KEY_ACT_STICK_RIGHT)&&pc_pad_raw_bind_held(raw,route.bind[i]))extra=true;
    require(pc_world_map_stick_command(action,invert,deadzone,live,extra,sx,sy),"native map loaded binding cleared or duplicated");
   }
  }
  if(n&&n->getCurrState()&&n->mNaviCamera&&(phase==1||phase==5||phase==11)){
   float bx=goal.x-n->mSRT.t.x,bz=goal.z-n->mSRT.t.z;bool walk=phase==1||phase==11||bx*bx+bz*bz>10000;
   if(walk||tick%10==0){float dx=walk?bx:goal.x-n->mCursorWorldPos.x,dz=walk?bz:goal.z-n->mCursorWorldPos.z,d=std::hypot(dx,dz);
    if(d>(walk?15:3)){const auto&axis=n->mNaviCamera->mViewXAxis;float strength=walk?65:22;sx=int(strength*(dx*axis.x+dz*axis.z)/d);sy=int(strength*(dx*axis.z-dz*axis.x)/d);}
   }
  }
  if(phase==6)keys=KeyConfig::_instance->mThrowKey.mBind;
  if(gameflow.mIsUIOverlayActive&&phase>0)keys=(frame%30<15)?KBBTN_A:0;
  SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_A,int((keys&KBBTN_A)!=0));
  SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_B,int((keys&KBBTN_B)!=0));
  SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_X,int((keys&KBBTN_X)!=0));
  SDL_JoystickSetVirtualAxis(virtualPad,SDL_CONTROLLER_AXIS_LEFTX,Sint16(sx*256));
  SDL_JoystickSetVirtualAxis(virtualPad,SDL_CONTROLLER_AXIS_LEFTY,Sint16(-sy*256));SDL_JoystickUpdate();
 }
};static Input* input=nullptr;
class Scenario:public PlugPikiApp{
public:int idle()override{
 ++frame;if(input)input->update();int result=PlugPikiApp::idle();Navi*n=naviMgr?naviMgr->getNavi():nullptr;
 if(n&&n->getCurrState()){initialized=true;p2_fixture_require_captain(GameStat::orimaDead,n->getCurrState()->getID()==NAVISTATE_Dead,std::getenv("P2_WHITE_ADULT_FORCE_DOWN")?0.f:n->mHealth,frame);}
 else if(initialized){std::puts("P2_FIXTURE_CAPTAIN_DOWN missing_initialized_captain_or_state outcome=BLOCKED");std::fflush(nullptr);std::_Exit(86);}
 require(frame<5000,"ordinary adult frame backstop");
 if((phase==5||phase==6||phase==10)&&frame%30==0&&n&&n->getCurrState()&&pikiMgr){
  auto*grab=n->getCurrState()->getID()==NAVISTATE_ThrowWait?static_cast<NaviThrowWaitState*>(n->getCurrState()):nullptr;
  auto*hand=n->mCollInfo?n->mCollInfo->getSphere('rhnd'):nullptr;
  std::printf("P2_WHITE_ADULT_GRAB_NATIVE frame=%d phase=%d movie=%d nstate=%d held=%p pending=%p holding=%d timeout=%.3f n_x=%.3f n_y=%.3f n_z=%.3f hand=%d hand_x=%.3f hand_y=%.3f hand_z=%.3f\n",frame,phase,int(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive),n->getCurrState()->getID(),grab?(void*)grab->mHeldThrowPiki:nullptr,grab?(void*)grab->mPendingThrowPiki:nullptr,grab?int(grab->mIsHoldingThrowPiki):0,grab?grab->mPendingThrowPikiTimeout:0.f,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,int(hand!=nullptr),hand?hand->mCentre.x:0.f,hand?hand->mCentre.y:0.f,hand?hand->mCentre.z:0.f);
  Iterator observed(pikiMgr);CI_LOOP(observed){auto*p=static_cast<Piki*>(*observed);if(!p->isAlive())continue;
   std::printf("P2_WHITE_ADULT_GRAB_BODY frame=%d body=%p restored=%d captured=%d white=%d state=%d mode=%d owned=%d ground=%d holding=%d stick=%d x=%.3f y=%.3f z=%.3f\n",frame,(void*)p,int(restored.count(p)!=0),int(captured.count(p)!=0),int(pc_p2_is_white(p)),p->getState(),p->mMode,int(p->mNavi==n),int(p->isCreatureFlag(CF_IsOnGround)),int(p->isHolding()),int(p->isStickTo()||p->getStickObject()!=nullptr),p->mSRT.t.x,p->mSRT.t.y,p->mSRT.t.z);
  }
 }
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){if(phase==0)gameflow.mMoviePlayer->requestSkip();return result;}
 if(!n||!n->getCurrState()||!pikiMgr||!itemMgr||!tekiMgr||!flowCont.mCurrentStage)return result;
 if(phase==0&&n->getCurrState()->getID()==NAVISTATE_Starting)return result;
 if(gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
 require(flowCont.mCurrentStage->mStageID==1,"actual Forest field required");++tick;
 int white=0,followers=0,heads=0;std::set<Piki*>live;
 Iterator bodies(pikiMgr);CI_LOOP(bodies){auto*p=static_cast<Piki*>(*bodies);if(!p->isAlive())continue;
  require(pc_p2_is_white(p)&&p->mHappa==Leaf,"unexpected field species/maturity");++white;live.insert(p);
  if(p->mNavi==n&&p->mMode==PikiMode::FormationMode)++followers;
  if(!restored.empty())require(restored.count(p),"replacement or foreign White body");
 }
 Iterator sprouts(itemMgr->getPikiHeadMgr());CI_LOOP(sprouts){if(static_cast<PikiHeadItem*>(*sprouts)->isAlive())++heads;}
 require(heads==0,"unexpected unplucked head");
 for(int c=0;c<3;++c)for(int m=0;m<3;++m)require(pikiInfMgr.mPikiCounts[c][m]==((c==Red&&m==Leaf)?5:0),"stored original all-color Reds changed");
 require(p2ship::stock.counts[1][1]==0&&p2ship::stock.counts[1][2]==0,"stored White maturity changed");
 require(p2whitetreasure::ledger.total()==180,"original retail receipt changed");
 Teki*predator=nullptr;bool currentOriginal=false;
 Iterator enemies(tekiMgr);CI_LOOP(enemies){auto*t=static_cast<Teki*>(*enemies);
  if(t==originalPredator)currentOriginal=true;
  if(t->mGenerator&&t->mGenerator->_70==PredatorUID){require(!predator&&t->mTekiType==TEKI_Swallow,"duplicate or wrong registered adult source");predator=t;}
 }
 if(!originalPredator&&predator)originalPredator=predator;
 if(predator)require(predator==originalPredator,"predator source pointer swapped");
 if(!predator&&currentOriginal&&originalPredator->mDeadState==2&&originalPredator->mPellet)predator=originalPredator;
 require(predator,"current live or actual corpse-producing predator owner absent");
 if(phase==0){
  require(white==0&&whiteStock()==15,"same genuine saved White baseline required");
  require(pc_randomizer_resumed()&&gameflow.mWorldClock.mCurrentDay==3,"genuine day3 native resume required");
  uint64_t checkpointGeneration=0;uint8_t checkpointHash[32]{};
  require(pc_randomizer_checkpoint_info(&checkpointGeneration,checkpointHash)&&checkpointGeneration>0,"actual resumed checkpoint observation missing");
  std::printf("P2_WHITE_ADULT_CHECKPOINT generation=%llu sha256=",static_cast<unsigned long long>(checkpointGeneration));
  for(uint8_t b:checkpointHash)std::printf("%02x",static_cast<unsigned int>(b));std::putchar('\n');
  require(predator->isAlive()&&pc_p2_white_poison_predator(predator),"ordinary supported poison provider unavailable");
  int w,h,x,y;auto*window=SDL_GL_GetCurrentWindow();SDL_GetWindowSize(window,&w,&h);SDL_GetWindowPosition(window,&x,&y);SDL_Rect bounds{};SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window),&bounds);
  require(w==960&&h==540&&std::abs(x-(bounds.x+(bounds.w-w)/2))<=2&&std::abs(y-(bounds.y+(bounds.h-h)/2))<=2,"centered960 baseline required");
  Iterator pellets(pelletMgr);CI_LOOP(pellets){auto*p=static_cast<Pellet*>(*pellets);if(p->isAlive())baselinePellets.insert(p);}
  auto*ship=itemMgr->getUfo();require(ship&&ship->isAlive(),"current ordinary ship required");goal=ship->getGoalPos();
  std::printf("P2_WHITE_ADULT_BASELINE stage=1 saved_white=15 saved_red=5 field=0 total=20 predator_uid=%u predator=%p native_hp=%.3f original_card_required=1\n",PredatorUID,(void*)predator,predator->mHealth);next(1);return result;
 }
 if(phase<4)require(white+whiteStock()==15,"ordinary withdrawal conservation");
 if(phase>=4){
  require(whiteStock()==13&&restored.size()==2,"two restored bodies and thirteen stored Whites required");
  for(auto*p:live)if(p->isStickToMouth()&&p->getStickObject()==predator&&captured.insert(p).second)
   std::printf("P2_WHITE_ADULT_CAPTURE frame=%d victim=%p predator=%p hp=%.3f\n",frame,(void*)p,(void*)predator,predator->mHealth);
  for(auto*p:restored)if(!live.count(p)&&lost.insert(p).second){require(captured.count(p),"White disappeared without actual mouth capture");++consumed;std::printf("P2_WHITE_ADULT_CASUALTY frame=%d victim=%p consumed_count=%d field=%d stored=13 original_red=5\n",frame,(void*)p,consumed,white);}
  require(white+consumed==2&&consumed<=2,"restored White casualty conservation");
 }
 if(frame%30==0)std::printf("P2_WHITE_ADULT_FRAME frame=%d phase=%d field=%d followers=%d stock=%d consumed=%d hp=%.3f stored_damage=%.3f dead_state=%d nstate=%d n_x=%.3f n_z=%.3f cursor_x=%.3f cursor_z=%.3f predator_x=%.3f predator_z=%.3f\n",frame,phase,white,followers,whiteStock(),consumed,predator->mHealth,predator->mStoredDamage,predator->mDeadState,n->getCurrState()->getID(),n->mSRT.t.x,n->mSRT.t.z,n->mCursorWorldPos.x,n->mCursorWorldPos.z,predator->mSRT.t.x,predator->mSRT.t.z);
 if(phase==1){auto*ship=itemMgr->getUfo();require(ship,"current ship absent");goal=ship->getGoalPos();float dx=goal.x-n->mSRT.t.x,dz=goal.z-n->mSRT.t.z;if(dx*dx+dz*dz<3600&&settled(n->getCurrState()->getID())){request("CTRL_F10");next(2);return result;}}
 if(phase==2&&tick>=20){next(3);ackTick=0;return result;}
 if(phase==3){if(whiteStock()!=lastStock){require(whiteStock()==lastStock-1,"ordinary withdrawal stock acknowledgement");lastStock=whiteStock();ackTick=tick;}
  if(white==2&&whiteStock()==13&&followers==2&&tick-ackTick>=20&&settled(n->getCurrState()->getID())){restored=live;next(4);return result;}
  if(whiteStock()>13&&tick-ackTick>=20&&tick%30==0&&settled(n->getCurrState()->getID()))request("F10");
 }
 if(phase==4&&tick>=20&&followers==2&&settled(n->getCurrState()->getID())){goal=predator->mSRT.t;next(5);return result;}
 if(phase==5){require(predator->isAlive(),"predator died before two witnessed consumptions");goal=predator->mSRT.t;
  float dx=goal.x-n->mCursorWorldPos.x,dz=goal.z-n->mCursorWorldPos.z,bx=goal.x-n->mSRT.t.x,bz=goal.z-n->mSRT.t.z;
  if(dx*dx+dz*dz<144&&bx*bx+bz*bz>1600&&bx*bx+bz*bz<10000&&n->getCurrState()->getID()==NAVISTATE_Walk){
   if(!actionClear(n->mSRT.t,true)){
    bool found=false;float closest=1e30f;
    for(int i=0;i<8;++i){float angle=i*0.78539816339f;Vector3f candidate(predator->mSRT.t.x+70.f*std::sin(angle),predator->mSRT.t.y,predator->mSRT.t.z+70.f*std::cos(angle));
     if(!actionClear(candidate,false,16.f))continue;float ax=candidate.x-n->mSRT.t.x,az=candidate.z-n->mSRT.t.z,distance=ax*ax+az*az;
     if(distance<closest){closest=distance;goal=candidate;found=true;}
    }
    require(found,"no native action-clear ordinary throw approach");std::printf("P2_WHITE_ADULT_ACTION_ROUTE x=%.3f z=%.3f ordinary_SDL_walk=1 prospective_terrain_unproved=1\n",goal.x,goal.z);next(11);return result;
   }
   held=nullptr;next(6);return result;
  }
 }
 if(phase==11){float dx=goal.x-n->mSRT.t.x,dz=goal.z-n->mSRT.t.z;
  if(dx*dx+dz*dz<225&&settled(n->getCurrState()->getID())&&actionClear(n->mSRT.t,false)){goal=predator->mSRT.t;next(5);return result;}
 }
 if(phase==6&&n->getCurrState()->getID()==NAVISTATE_ThrowWait){auto*grab=static_cast<NaviThrowWaitState*>(n->getCurrState());Piki*actual=grab->mHeldThrowPiki?grab->mHeldThrowPiki:grab->mPendingThrowPiki;
  if(!held&&actual){
   const bool known=live.count(actual)!=0;
   const bool valid=known&&restored.count(actual)&&!captured.count(actual)&&pc_p2_is_white(actual)&&actual->mNavi==n&&actual->mMode==PikiMode::FormationMode&&(actual->getState()==PIKISTATE_Normal||actual->getState()==PIKISTATE_GoHang||actual->getState()==PIKISTATE_Hanged);
   if(!valid)std::printf("P2_WHITE_ADULT_GRAB_REFUSE frame=%d actual=%p live=%d restored=%d previously_captured=%d species=%d state=%d mode=%d owned=%d held=%p pending=%p\n",frame,(void*)actual,int(known),int(restored.count(actual)!=0),int(captured.count(actual)!=0),known?int(pc_p2_species(actual)):-1,known?actual->getState():-1,known?actual->mMode:-1,known?int(actual->mNavi==n):-1,(void*)grab->mHeldThrowPiki,(void*)grab->mPendingThrowPiki);
   require(valid,"actual throw selected foreign or ineligible White");held=actual;
  }
  require((!grab->mHeldThrowPiki||grab->mHeldThrowPiki==held)&&(!grab->mPendingThrowPiki||grab->mPendingThrowPiki==held),"actual native throw pointer swapped");
  if(held&&grab->mHeldThrowPiki==held&&grab->mIsHoldingThrowPiki&&held->getState()==PIKISTATE_Hanged){next(7);return result;}
 }
 if(phase==6&&settled(n->getCurrState()->getID())&&tick>=5){
  bool eligible=!live.empty()&&white+consumed==2;
  for(auto*p:live){eligible=eligible&&retryBody(p,n);
   if(frame%30==0)std::printf("P2_WHITE_ADULT_GRAB_SETTLE frame=%d body=%p state=%d mode=%d owned=%d grounded=%d holding=%d sticking=%d captured=%d x=%.3f y=%.3f z=%.3f retries=%d\n",frame,(void*)p,p->getState(),p->mMode,int(p->mNavi==n),int(p->isCreatureFlag(CF_IsOnGround)),int(p->isHolding()),int(p->isStickTo()||p->getStickObject()!=nullptr),int(captured.count(p)!=0),p->mSRT.t.x,p->mSRT.t.y,p->mSRT.t.z,grabRetries);
  }
  if(held)eligible=eligible&&live.count(held)&&retryBody(held,n);
  if(eligible){require(++grabRetries<=8,"bounded ordinary grab retries exhausted");std::printf("P2_WHITE_ADULT_GRAB_RETRY frame=%d attempt=%d released_actual_A=1 no_actor_state_writes=1\n",frame,grabRetries);held=nullptr;next(10);return result;}
 }
 if(phase==10&&tick>=5&&settled(n->getCurrState()->getID())){
  bool eligible=!live.empty();for(auto*p:live)eligible=eligible&&retryBody(p,n);
  if(eligible){goal=predator->mSRT.t;next(5);return result;}
 }
 if(phase==7&&held&&live.count(held)&&held->getState()==PIKISTATE_Flying){std::printf("P2_WHITE_ADULT_THROW frame=%d victim=%p ordinary_flight=1\n",frame,(void*)held);next(8);return result;}
 if(phase==8&&held&&lost.count(held)){held=nullptr;if(consumed==1){next(5);return result;}next(9);return result;}
 if(phase==9&&consumed==2&&predator->mHealth<=0&&predator->mDeadState==2&&predator->mPellet){
  Pellet*corpse=nullptr;Iterator pellets(pelletMgr);CI_LOOP(pellets){auto*p=static_cast<Pellet*>(*pellets);if(p==predator->mPellet&&p->isAlive())corpse=p;}
  require(corpse&&!baselinePellets.count(corpse),"native owned new corpse not live");
  std::printf("P2_WHITE_ADULT_PASS consumed=2 field_white=0 stored_white=13 original_red=5 remaining_total=18 damage_per_victim=750 native_health=%.3f native_dead_state=%d corpse=%p predator=%p source_uid=%u actual_ordinary_inputs=1 no_HP_callback_actor_stock_writes=1\n",predator->mHealth,predator->mDeadState,(void*)corpse,(void*)predator,PredatorUID);std::fflush(nullptr);std::_Exit(0);
 }
 require(tick<1600,"bounded ordinary adult phase timeout");return result;
 }};
int main(int argc,char**argv){
 setvbuf(stdout,nullptr,_IONBF,0);SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,"1");SDL_SetMainReady();pc_gpu_preference_apply();pc_bbft_init(argc,argv);
 require(pc_randomizer_white_campaign()&&!pc_pikipelago_room_preview(),"explicit ordinary White campaign required");
 require(pc_window_init("Ordinary White adult ingestion",960,540),"window failed");pc_settings_init();pc_window_set_control_mode(PC_CONTROL_CLASSIC);pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);pc_window_set_window_size(960,540);pc_window_center();
 int device=SDL_JoystickAttachVirtual(SDL_JOYSTICK_TYPE_GAMECONTROLLER,SDL_CONTROLLER_AXIS_MAX,SDL_CONTROLLER_BUTTON_MAX,0);require(device>=0,"ordinary virtual gamepad attach failed");
 char guid[64];SDL_JoystickGetGUIDString(SDL_JoystickGetDeviceGUID(device),guid,sizeof(guid));std::string mapping=std::string(guid)+",White adult pad,a:b0,b:b1,x:b2,y:b3,back:b4,guide:b5,start:b6,leftstick:b7,rightstick:b8,leftshoulder:b9,rightshoulder:b10,dpup:b11,dpdown:b12,dpleft:b13,dpright:b14,leftx:a0,lefty:a1,rightx:a2,righty:a3,lefttrigger:a4,righttrigger:a5,";require(SDL_GameControllerAddMapping(mapping.c_str())>=0,"ordinary pad mapping failed");
 virtualPad=SDL_JoystickOpen(device);require(virtualPad,"ordinary pad open failed");pc_window_input_assign(0,PC_INPUT_DEV_GAMEPAD,SDL_JoystickInstanceID(virtualPad));pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);pc_window_set_stick_invert(0);pc_window_set_cstick_invert(0);
 pc_window_set_gamepad_binding(PC_KEY_ACT_A,SDL_CONTROLLER_BUTTON_A);pc_window_set_gamepad_binding(PC_KEY_ACT_B,SDL_CONTROLLER_BUTTON_B);pc_window_set_gamepad_binding(PC_KEY_ACT_X,SDL_CONTROLLER_BUTTON_X);
 input=new Input();gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new Scenario());return 0;
}
