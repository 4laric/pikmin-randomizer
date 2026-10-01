// Scripted native controller acquisition: no species, attachment or callback injection.
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
#include "Boss.h"
// Fixture-only access for restored state-query checks; no production headers change.
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
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "C:/Users/alari/pikmin-randomizer/scripts/p2_fixture_captain_guard.h"

static void require(bool ok,const char* reason) {
    if(!ok){std::printf("P2_IVORY_BUDGET_FAIL %s\n",reason);std::fflush(nullptr);std::_Exit(1);}
}
static int population() {
    int count=0;Iterator actors(pikiMgr);CI_LOOP(actors){if(static_cast<Piki*>(*actors)->isAlive())++count;}
    Iterator heads(itemMgr->getPikiHeadMgr());CI_LOOP(heads){if(static_cast<PikiHeadItem*>(*heads)->isAlive())++count;}
    return count;
}

static int phase=0,ticks=0,inputFrame=0;static Vector3f goal;static SDL_Joystick* virtualPad=nullptr;
class AcquisitionController:public Kontroller {
public:
 AcquisitionController():Kontroller(1){}
 void update()override{
  u32 keys=0;mMainStickX=0;mMainStickY=0;mSubStickX=0;mSubStickY=0;
  Navi* n=naviMgr?naviMgr->getNavi():nullptr;
  if(phase==1)keys=KeyConfig::_instance->mSetCursorKey.mBind;
  if((phase==2 || phase==4) && n && n->mNaviCamera){
   float bx=goal.x-n->mSRT.t.x,bz=goal.z-n->mSRT.t.z;
   bool walk=phase==4 || bx*bx+bz*bz>10000.f;
   // Cursor updates arrive through native polling. Pulse low-stick corrections
   // and let neutral input settle instead of continually circling the mouth.
   if(walk || ticks%10==0){
    float dx=walk?bx:goal.x-n->mCursorWorldPos.x,dz=walk?bz:goal.z-n->mCursorWorldPos.z,d=std::sqrt(dx*dx+dz*dz);
    if(d>(walk?15.f:3.f)){const Vector3f& axis=n->mNaviCamera->mViewXAxis;float strength=walk?65.f:22.f;keys=KBBTN_MSTICK_RIGHT;mMainStickX=s8(strength*(dx*axis.x+dz*axis.z)/d);mMainStickY=s8(strength*(dx*axis.z-dz*axis.x)/d);}
   }
  }
  if((phase==3 && ticks%60<15)||(phase==5 && ticks%60<50))keys=KeyConfig::_instance->mThrowKey.mBind;
  if(gameflow.mIsUIOverlayActive)keys=(inputFrame%30<15)?KBBTN_A:0;
  SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_A,int((keys&KBBTN_A)!=0));
  SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_B,int((keys&KBBTN_B)!=0));
  SDL_JoystickSetVirtualAxis(virtualPad,SDL_CONTROLLER_AXIS_LEFTX,Sint16(int(mMainStickX)*32767/74));
  SDL_JoystickSetVirtualAxis(virtualPad,SDL_CONTROLLER_AXIS_LEFTY,Sint16(-int(mMainStickY)*32767/74));
  SDL_JoystickUpdate();
 }
};
static AcquisitionController* scriptedInput=nullptr;
class AcquisitionApp:public PlugPikiApp {
 int frames=0;bool initialized=false;Pom* flower=nullptr;
public:
 int idle()override{
  inputFrame=frames;if(scriptedInput)scriptedInput->update();
  int result=PlugPikiApp::idle();Navi* n=naviMgr?naviMgr->getNavi():nullptr;
  if(n){initialized=true;p2_fixture_require_captain(GameStat::orimaDead,n->getCurrState()&&n->getCurrState()->getID()==NAVISTATE_Dead,std::getenv("P2_WHITE_FORCE_CAPTAIN_DOWN")?0.f:n->mHealth,frames);}
  else if(initialized){std::puts("P2_FIXTURE_CAPTAIN_DOWN missing_captain outcome=BLOCKED");std::fflush(nullptr);std::_Exit(86);}
  require(++frames<5000,"frame timeout");
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_ready()||!n||!n->getCurrState()||frames<90)return result;
  if(gameflow.mPauseAll||gameflow.mIsUIOverlayActive){if(frames%60==0){std::printf("P2_WHITE_INPUT_GATE frame=%d phase=%d paused=%d overlay=%d nstate=%d\n",frames,phase,int(gameflow.mPauseAll),int(gameflow.mIsUIOverlayActive),n->getCurrState()->getID());std::fflush(stdout);}return result;}
  ++ticks;
  for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
  if(phase==0 && n->getCurrState()->getID()==NAVISTATE_Starting)return result;
  if(phase==0){
   for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
   int count=0;Iterator actors(pikiMgr);CI_LOOP(actors){Piki* p=static_cast<Piki*>(*actors);if(p->isAlive()){++count;require(pc_p2_species(p)==P2SpeciesRed,"starting squad not Red");}}
   Iterator bosses(bossMgr);CI_LOOP(bosses){Boss* b=static_cast<Boss*>(*bosses);if(b->isAlive()&&b->mObjType==OBJTYPE_Pom&&pc_p2_ivory(static_cast<Pom*>(b))){require(!flower,"multiple Ivory buds");flower=static_cast<Pom*>(b);}}
   std::printf("P2_WHITE_BASELINE_COUNTS frame=%d red=%d bodies=%d bound_ivory=%d nstate=%d\n",frames,count,population(),int(flower!=nullptr),n->getCurrState()->getID());require(count==20&&population()==20&&flower,"fresh baseline requires twenty Reds and one Ivory");
   int w,h,x,y;SDL_Window* window=SDL_GL_GetCurrentWindow();SDL_GetWindowSize(window,&w,&h);SDL_GetWindowPosition(window,&x,&y);require(w==960&&h==540,"window dimensions");
   std::printf("P2_WHITE_ACQUISITION_BASELINE squad=20 window=%dx%d position=%d,%d hp=%.3f navi=%.2f,%.2f face=%.2f bud=%.2f,%.2f kill_same=%d capacity=%d cycles=%d..%d\n",w,h,x,y,n->mHealth,n->mSRT.t.x,n->mSRT.t.z,n->mFaceDirection,flower->mSRT.t.x,flower->mSRT.t.z,int(C_POM_PARM(flower,mDoKillSameColorPiki)),int(C_POM_PARM(flower,mMaxPikiPerCycle)),int(C_POM_PARM(flower,mMinCycles)),int(C_POM_PARM(flower,mMaxCycles)));
   // Temporarily supply query inputs, restore them before the next engine idle.
   // This policy probe is separate from the subsequent ordinary controller path.
   PomAi* ai=flower->mPomAi;int prev=ai->mPrevStickPikiCount,used=ai->mReleasedSeedCount;float timer=flower->getWalkTimer();
   ai->mPrevStickPikiCount=4;flower->setWalkTimer(.99f);require(!ai->petalCloseTransit(),"Ivory closed before five/one second");
   flower->setWalkTimer(1.01f);require(ai->petalCloseTransit(),"Ivory did not close after one second");
   flower->setWalkTimer(0.f);ai->mPrevStickPikiCount=5;require(ai->petalCloseTransit(),"Ivory five-input capacity not applied");
   Generator* binding=flower->mGenerator;flower->mGenerator=nullptr;require(!ai->petalCloseTransit(),"ordinary Pom changed by Ivory capacity");flower->mGenerator=binding;
   ai->mReleasedSeedCount=4;require(!ai->deadTransit(),"Ivory died before five spent slots");ai->mReleasedSeedCount=5;require(ai->deadTransit(),"Ivory survived five spent slots");
   ai->mPrevStickPikiCount=prev;ai->mReleasedSeedCount=used;flower->setWalkTimer(timer);
   std::puts("P2_IVORY_STATE_POLICY_PASS bound_runtime_queries=1 restored_before_idle=1 capacity=5 close_seconds=1 lifetime_slots=5 ordinary_capacity_preserved=1");
   phase=1;ticks=0;
  }
  if(phase==1&&ticks>=100){goal=flower->mSRT.t;phase=2;ticks=0;}
  if(phase==2){float dx=flower->mSRT.t.x-n->mCursorWorldPos.x,dz=flower->mSRT.t.z-n->mCursorWorldPos.z;float bx=flower->mSRT.t.x-n->mSRT.t.x,bz=flower->mSRT.t.z-n->mSRT.t.z;if(dx*dx+dz*dz<64 && bx*bx+bz*bz>625){phase=6;ticks=0;}}
  if(phase==6&&ticks>=20){float dx=flower->mSRT.t.x-n->mCursorWorldPos.x,dz=flower->mSRT.t.z-n->mCursorWorldPos.z;phase=(dx*dx+dz*dz<64)?3:2;ticks=0;}
  int red=0,white=0,heads=0,captured=0,flying=0;PikiHeadItem* head=nullptr;
  Iterator actors(pikiMgr);CI_LOOP(actors){Piki* p=static_cast<Piki*>(*actors);if(!p->isAlive())continue;if(pc_p2_is_white(p))++white;else ++red;if(p->getStickObject()==flower)++captured;if(p->getState()==PIKISTATE_Flying)++flying;}
  Iterator sprouts(itemMgr->getPikiHeadMgr());CI_LOOP(sprouts){PikiHeadItem* p=static_cast<PikiHeadItem*>(*sprouts);if(p->isAlive()){++heads;require(pc_p2_species(p)==P2SpeciesWhite,"non-White sprout");if(!head&&p->canPullout())head=p;}}
  if(ticks%60==0){std::printf("P2_WHITE_ACQUISITION_FRAME frame=%d phase=%d ticks=%d red=%d white=%d heads=%d captured=%d flying=%d bodies=%d nstate=%d navi=%.2f,%.2f cursor=%.2f,%.2f budstate=%d budalive=%d\n",frames,phase,ticks,red,white,heads,captured,flying,population(),n->getCurrState()->getID(),n->mSRT.t.x,n->mSRT.t.z,n->mCursorWorldPos.x,n->mCursorWorldPos.z,flower->getCurrentState(),int(flower->isAlive()));std::fflush(stdout);}
  if(population()!=20){std::printf("P2_WHITE_POPULATION_FAILURE frame=%d red=%d white=%d heads=%d captured=%d flying=%d bodies=%d phase=%d nstate=%d\n",frames,red,white,heads,captured,flying,population(),phase,n->getCurrState()->getID());Iterator diag(pikiMgr);CI_LOOP(diag){Piki* p=static_cast<Piki*>(*diag);std::printf("P2_WHITE_PIKI_DIAG alive=%d state=%d mode=%d x=%.2f y=%.2f z=%.2f\n",int(p->isAlive()),p->getState(),int(p->mMode),p->mSRT.t.x,p->mSRT.t.y,p->mSRT.t.z);}}
  require(population()==20,"ordinary acquisition lost/duplicated bodies");
  if(phase==3&&head){std::printf("P2_WHITE_ORDINARY_DISCHARGE sprouts=%d red=%d bodies=20\n",heads,red);goal=head->mSRT.t;phase=4;ticks=0;}
  if(phase==4&&head){goal=head->mSRT.t;float dx=goal.x-n->mSRT.t.x,dz=goal.z-n->mSRT.t.z;if(dx*dx+dz*dz<400){phase=5;ticks=0;}}
  if(white>0){Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p->isAlive()&&pc_p2_is_white(p))require(!pc_p2_has_red_immunity(p),"White inherited Red immunity");}std::printf("P2_WHITE_ACQUISITION_PASS scripted_native_controller=1 red=%d white=%d sprouts=%d bodies=20\n",red,white,heads);std::fflush(nullptr);std::_Exit(0);}
  require(ticks<1600,"ordinary controller stage did not complete");return result;
 }
};
int main(int argc,char**argv){
    SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,"1");SDL_SetMainReady();pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");pc_bbft_init(argc,argv);
    require(pc_pikipelago_room_preview(),"requires experimental room");
    if(!pc_window_init("White acquisition acceptance",960,540))return 3;
    pc_settings_init();pc_window_set_control_mode(PC_CONTROL_CLASSIC);pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);pc_window_set_window_size(960,540);pc_window_center();
    std::puts("Experimental preview window set to 960x540 windowed and centered");
    int device=SDL_JoystickAttachVirtual(SDL_JOYSTICK_TYPE_GAMECONTROLLER,SDL_CONTROLLER_AXIS_MAX,SDL_CONTROLLER_BUTTON_MAX,0);require(device>=0,"virtual gamepad attach failed");
    char guid[64];SDL_JoystickGetGUIDString(SDL_JoystickGetDeviceGUID(device),guid,sizeof(guid));std::string mapping=std::string(guid)+",White acceptance virtual pad,a:b0,b:b1,x:b2,y:b3,back:b4,guide:b5,start:b6,leftstick:b7,rightstick:b8,leftshoulder:b9,rightshoulder:b10,dpup:b11,dpdown:b12,dpleft:b13,dpright:b14,leftx:a0,lefty:a1,rightx:a2,righty:a3,lefttrigger:a4,righttrigger:a5,";require(SDL_GameControllerAddMapping(mapping.c_str())>=0,"virtual gamepad mapping failed");
    virtualPad=SDL_JoystickOpen(device);require(virtualPad!=nullptr,"virtual gamepad open failed");pc_window_input_assign(0,PC_INPUT_DEV_GAMEPAD,SDL_JoystickInstanceID(virtualPad));pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);pc_window_set_stick_invert(0);pc_window_set_cstick_invert(0);pc_window_set_gamepad_binding(PC_KEY_ACT_A,SDL_CONTROLLER_BUTTON_A);pc_window_set_gamepad_binding(PC_KEY_ACT_B,SDL_CONTROLLER_BUTTON_B);scriptedInput=new AcquisitionController();
    std::puts("P2_WHITE_INPUT_METHOD SDL_virtual_gamepad native_controller_and_UI_polling=1");
    gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new AcquisitionApp());return 0;
}
