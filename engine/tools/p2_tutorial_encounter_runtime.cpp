// #1150 ordinary imported tutorial Red encounter and original Onion carry.
// Only SDL input is scripted. Stage calendar/placements are explicit inputs;
// no positive creature, health, cargo, check or reward state is written here.
#include <SDL2/SDL.h>
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>
#include "system.h"
#include "App.h"
#include "Node.h"
#include "FlowController.h"
#include "MoviePlayer.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Camera.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiHeadItem.h"
#include "ItemMgr.h"
#include "GoalItem.h"
#include "Pellet.h"
#include "teki.h"
#include "TekiPersonality.h"
#include "Generator.h"
#include "MapMgr.h"
#include "Shape.h"
#include "Route.h"
#include "GameStat.h"
#include "PlayerState.h"
#include "KeyConfig.h"
#include "pc_bbft.h"
#include "pc_window.h"
#include "pc_gpu_preference.h"
#include "pc_p2_kochappy.h"
#include "pc_p2_kochappy_fsm.h"
#include "pc_p2_surface_water.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "p2_fixture_captain_guard.h"
namespace {
constexpr unsigned Target=0x50323101, OnionTarget=0x50324f01;
SDL_Joystick* pad=nullptr;
bool human(){return std::getenv("P2_TUTORIAL_HUMAN")!=nullptr;}
void require(bool yes,const char* message){if(!yes){std::printf("FAIL P2_TUTORIAL_ENCOUNTER %s\n",message);std::fflush(nullptr);std::_Exit(1);}}
float distance(const Vector3f& a,const Vector3f& b){float x=a.x-b.x,z=a.z-b.z;return std::sqrt(x*x+z*z);}
void input(unsigned keys=0,int x=0,int y=0,int cx=0,int cy=0){
 if(!pad)return;
 pc_window_input_assign(0,PC_INPUT_DEV_GAMEPAD,SDL_JoystickInstanceID(pad));pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);
 SDL_JoystickSetVirtualButton(pad,SDL_CONTROLLER_BUTTON_A,(keys&KBBTN_A)!=0);
 SDL_JoystickSetVirtualButton(pad,SDL_CONTROLLER_BUTTON_B,(keys&KBBTN_B)!=0);
 SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_LEFTX,Sint16(x*32767/74));
 SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_LEFTY,Sint16(-y*32767/74));
 SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_RIGHTX,Sint16(cx*32767/74));
 SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_RIGHTY,Sint16(-cy*32767/74));SDL_JoystickUpdate();
}
void point(Navi* n,const Vector3f& goal,bool walk,unsigned keys=0){
 const Vector3f& from=walk?n->mSRT.t:n->mCursorWorldPos;
 float dx=goal.x-from.x,dz=goal.z-from.z,d=std::sqrt(dx*dx+dz*dz);int x=0,y=0;
 if(d>(walk?15.f:6.f)){const Vector3f& axis=n->controlCamera()->mViewXAxis;float power=walk?65:22;
  x=int(std::lround(power*(dx*axis.x+dz*axis.z)/d));y=int(std::lround(power*(dx*axis.z-dz*axis.x)/d));}
 input(keys,x,y);
}
int heads(){int count=0;Iterator it(itemMgr->getPikiHeadMgr());CI_LOOP(it){if(static_cast<PikiHeadItem*>(*it)->isAlive())++count;}return count;}
class TutorialApp:public PlugPikiApp{
 int frame=0,age=0,ready=0,phase=0,phaseStart=0,settled=0;
 bool captainSeen=false,carried=false,nearGoal=false,corpseSeen=false;
 Teki* enemy=nullptr;GoalItem* onion=nullptr;Pellet* historicalBody=nullptr;
 Vector3f corpseOrigin;int initialRewards=0,expectedSeeds=0;float maxCorpseTravel=0;
public:
 int idle() override {
  int result=PlugPikiApp::idle();
  // Mandatory first boundary, including movies/pause and initialized disappearance.
  Navi* n=naviMgr?naviMgr->getNavi():nullptr;
  const bool initialized=n&&n->getCurrState();if(initialized)captainSeen=true;
  const bool forced=std::getenv("P2_TUTORIAL_FORCE_CAPTAIN_DOWN")!=nullptr;
  const bool paused=std::getenv("P2_TUTORIAL_FORCE_PAUSED_CAPTAIN_DOWN")!=nullptr;
  if(initialized&&paused)gameflow.mPauseAll=true; // negative case only
  if(captainSeen&&!initialized){std::puts("P2_FIXTURE_CAPTAIN_MISSING outcome=BLOCKED");p2_fixture_require_captain(true,true,0,frame);}
  if(initialized)p2_fixture_require_captain(GameStat::orimaDead||forced||paused,
   naviMgr->isNaviDead(n)||n->getCurrState()->getID()==NAVISTATE_Dead,n->mHealth,frame);
  ++frame;
  if(human()&&(SDL_GetKeyboardState(nullptr)[SDL_SCANCODE_F7]||std::ifstream("p2-reset-request").good())){std::puts("P2_TUTORIAL_RESET requested=1");std::fflush(nullptr);std::_Exit(90);}
  require(frame<3600,"frame bound; supervisor must separately cap60wallseconds");
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!initialized||!pikiMgr||!tekiMgr||!itemMgr||!mapMgr)return result;
  if(gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  if(phase==0&&(n->getCurrState()->getID()!=NAVISTATE_Walk||++ready<45))return result;
  ++age;int live=0,red=0;Iterator roster(pikiMgr);CI_LOOP(roster){Piki* p=static_cast<Piki*>(*roster);if(p->isAlive()){++live;if(p->mColor==Red)++red;}}
  if(phase==0){
   require(flowCont.mCurrentStage&&!std::strcmp(flowCont.mCurrentStage->mFileName,"stages/p2_tutorial.ini"),"original tutorial stage");
   require(!gameflow.mIsChallengeMode&&!pc_pikipelago_room_preview(),"ordinary surface lifecycle");
   require(gameflow.mWorldClock.mCurrentDay==5,"actual native day5, not metadata only");
   require(live==20&&red==20,"current20 nativeRed1 baseline");
   require(mapMgr->mMapModel&&mapMgr->mMapModel->mTriCount==5332,"all source faces");
   require(pc_p2_surface_water_active()&&pc_p2_surface_water_count()==3,"three exact source waters");
   require(routeMgr&&routeMgr->getNumWayPoints('test')==102,"all102 source route points");
   Iterator actors(tekiMgr);CI_LOOP(actors){Teki* t=static_cast<Teki*>(*actors);if(t->mGenerator&&t->mGenerator->_70==Target){require(!enemy,"duplicate original source binding");enemy=t;}}
   require(enemy&&pc_p2_kochappy_registered(enemy)&&pc_p2_kochappy_fsm_suppress_ai(enemy),"Red1 explicit native bank and own source FSM");
   require(enemy->mTekiType==TEKI_Chappy&&std::fabs(enemy->mHealth-200)<.01f,"source Red200 health");
   require(std::fabs(enemy->mGenerator->mGenPosition.x+1153.361206f)<.01f&&std::fabs(enemy->mGenerator->mGenPosition.z-2231.686035f)<.01f,"original enemy generator coordinates");
   // GenObjectTeki::birth retains BirthInfo's position in this personality.
   // Live mSRT may move naturally on sloped terrain before Walk readiness.
   require(enemy->mPersonality&&std::fabs(enemy->mPersonality->mPosition.x+1153.361206f)<.01f&&std::fabs(enemy->mPersonality->mPosition.y-47.871529f)<.01f&&std::fabs(enemy->mPersonality->mPosition.z-2231.686035f)<.01f,"original source birth coordinates");
   std::printf("P2_TUTORIAL_SOURCE_BIRTH generator=%u born=%.7f,%.7f,%.7f live=%.7f,%.7f,%.7f terrain_drift=%.3f\n",Target,enemy->mPersonality->mPosition.x,enemy->mPersonality->mPosition.y,enemy->mPersonality->mPosition.z,enemy->mSRT.t.x,enemy->mSRT.t.y,enemy->mSRT.t.z,distance(enemy->mSRT.t,enemy->mPersonality->mPosition));
   require(enemy->mPersonality&&enemy->mPersonality->mPelletColor==-1&&enemy->mPersonality->mPelletKind==0,"source random one-pellet payload mapping");
   require(enemy->getPersonalityI(TekiPersonality::INT_PelletMinCount)==1&&enemy->getPersonalityI(TekiPersonality::INT_PelletMaxCount)==2&&std::fabs(enemy->getPersonalityF(TekiPersonality::FLT_PelletAppearChance)-.4f)<.001f,"source pellet counts/chance");
   onion=itemMgr->getContainer(Red);require(onion&&onion->mGenerator&&onion->mGenerator->_70==OnionTarget,"original Red Onion binding");
   require(std::fabs(onion->mSRT.t.x+225.018997f)<.1f&&std::fabs(onion->mSRT.t.z-2784.604980f)<.1f,"original Onion coordinates");
   require(std::fabs(onion->mFaceDirection-(-49.f*3.14159265359f/180.f))<.001f,"disclosed quantized original Onion yaw");
   initialRewards=heads()+onion->getTotalStorePikis();require(initialRewards==0,"fresh reward baseline");
   std::printf("P2_TUTORIAL_READY day=5 source_id=1 generator=%u native_own=1 live=20 Red1=20 faces=5332 routes=102 waters=3 human=%d gameplay_judgment=0\n",Target,int(human()));std::fflush(nullptr);
   if(std::getenv("P2_TUTORIAL_READY_ONLY"))std::_Exit(0);
   phase=1;phaseStart=age;
  }
  if(human())return result;
  if(age%60==0){std::printf("P2_TUTORIAL_PROGRESS frame=%d phase=%d hp=%.2f live=%d followers=%d rewards=%d navi=%.2f,%.2f\n",frame,phase,n->mHealth,live,n->getPlatePikis(),heads()+onion->getTotalStorePikis(),n->mSRT.t.x,n->mSRT.t.z);std::fflush(nullptr);}
  if(phase==1){input(KeyConfig::_instance->mSetCursorKey.mBind);if(n->getPlatePikis()>=red&&age-phaseStart>30){phase=2;input();}return result;}
  if(phase==2){if(distance(n->mSRT.t,enemy->mSRT.t)<120){phase=3;phaseStart=age;input();}else point(n,enemy->mSRT.t,true);return result;}
  if(phase==3){unsigned keys=(age-phaseStart)%60<15?KeyConfig::_instance->mThrowKey.mBind:0;point(n,enemy->mSRT.t,false,keys);
   if(!enemy->isAlive()){phase=4;input();std::puts("P2_TUTORIAL_NATURAL_DEATH health_writes=0");}return result;}
  if(phase>=4){
   Pellet* body=nullptr;Iterator pellets(pelletMgr);CI_LOOP(pellets){Pellet* p=static_cast<Pellet*>(*pellets);if(p->mPelletView==static_cast<PelletView*>(enemy)){require(!body,"duplicate original corpse");body=p;}}
   if(body){
    require(body->mConfig,"corpse config");
    require(body->mConfig->mCarryMinPikis()==3&&body->mConfig->mCarryMaxPikis()==6&&body->mConfig->mMatchingOnyonSeeds()==4&&body->mConfig->mNonMatchingOnyonSeeds()==4,"actual retail Red corpse carry/reward");
    if(!corpseSeen){corpseSeen=true;historicalBody=body;corpseOrigin=body->mSRT.t;expectedSeeds=4;std::puts("P2_TUTORIAL_CORPSE min=3 max=6 seeds=4 native_config=source_private");}
    require(body==historicalBody,"corpse identity changed");
    if(body->mCarrierCount>=3){carried=true;maxCorpseTravel=std::max(maxCorpseTravel,distance(body->mSRT.t,corpseOrigin));}
    if(carried&&body->mTargetGoal==static_cast<Suckable*>(onion)&&distance(body->mSRT.t,onion->mSRT.t)<100)nearGoal=true;
    if(age%60==0){std::printf("P2_TUTORIAL_CARRY xyz=%.2f,%.2f,%.2f carriers=%u strength=%u goal_original=%d traveled=%.2f\n",body->mSRT.t.x,body->mSRT.t.y,body->mSRT.t.z,body->mCarrierCount,body->mCarrierCounter,int(body->mTargetGoal==static_cast<Suckable*>(onion)),distance(body->mSRT.t,corpseOrigin));std::fflush(nullptr);}
    if(body->mCarrierCount>=3){if(distance(n->mSRT.t,body->mSRT.t)>100)point(n,body->mSRT.t,true);else input();return result;}
    float dx=body->mSRT.t.x-n->mSRT.t.x,dz=body->mSRT.t.z-n->mSRT.t.z,d=std::sqrt(dx*dx+dz*dz);const Vector3f& a=n->controlCamera()->mViewXAxis;
    int sx=d>1?int(65*(dx*a.x+dz*a.z)/d):0,sy=d>1?int(65*(dx*a.z-dz*a.x)/d):0;input(0,d>60?sx:0,d>60?sy:0,sx,sy);return result;
   }
   input();if(!corpseSeen)return result;
   require(carried&&nearGoal&&maxCorpseTravel>800,"corpse vanished without observed ordinary long original-Onion delivery");
   const int reward=heads()+onion->getTotalStorePikis()-initialRewards;
   if(++settled<90)return result;
   // At most2 numbered one-pellets; matching color may each return2 seeds.
   require(reward>=expectedSeeds&&reward<=expectedSeeds+4,"actual Red-Onion reward budget/no duplicate carcass");
   std::printf("PASS P2_TUTORIAL_ENCOUNTER day=5 source_id=1 spawn=original ordinary_SDL_combat=1 carried=1 original_Onion=1 corpse_seed_value=4 observed_rewards=%d optional_number_drops_max=2 optional_number_seeds_max=4 live=%d source_routes=102 cleanup_observed_frames=%d Purple_gate=OPEN human_judgment=0\n",reward,live,settled);std::fflush(nullptr);std::_Exit(0);
  }
  return result;
 }
};
}
int main(int argc,char**argv){
 require(std::getenv("PIKMIN_P2_TEST_START_DAY")&&!std::strcmp(std::getenv("PIKMIN_P2_TEST_START_DAY"),"5"),"inherit existing test-only actual day5 bootstrap");
 SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,"1");SDL_SetMainReady();pc_gpu_preference_apply();pc_bbft_init(argc,argv);
 require(pc_pikipelago_surface_course()&&!std::strcmp(pc_pikipelago_surface_course(),"tutorial"),"surface tutorial argument required");
 if(!pc_window_init("P2 original tutorial encounter",960,540))return 3;
 pc_settings_init();pc_window_set_control_mode(PC_CONTROL_CLASSIC);pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();
 SDL_Window* w=SDL_GL_GetCurrentWindow();int width,height,x,y;SDL_GetWindowSize(w,&width,&height);SDL_GetWindowPosition(w,&x,&y);SDL_Rect b{};SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(w),&b);
 require(width==960&&height==540&&std::abs(x-(b.x+(b.w-width)/2))<=2&&std::abs(y-(b.y+(b.h-height)/2))<=2,"centered960x540 baseline");
 std::printf("P2_TUTORIAL_WINDOW size=%dx%d centered=1\n",width,height);
 if(!human()){
  int device=SDL_JoystickAttachVirtual(SDL_JOYSTICK_TYPE_GAMECONTROLLER,SDL_CONTROLLER_AXIS_MAX,SDL_CONTROLLER_BUTTON_MAX,0);require(device>=0,"virtual pad attach");
  char guid[64];SDL_JoystickGetGUIDString(SDL_JoystickGetDeviceGUID(device),guid,sizeof(guid));std::string mapping=std::string(guid)+",Tutorial acceptance pad,a:b0,b:b1,x:b2,y:b3,back:b4,guide:b5,start:b6,leftstick:b7,rightstick:b8,leftshoulder:b9,rightshoulder:b10,dpup:b11,dpdown:b12,dpleft:b13,dpright:b14,leftx:a0,lefty:a1,rightx:a2,righty:a3,lefttrigger:a4,righttrigger:a5,";
  require(SDL_GameControllerAddMapping(mapping.c_str())>=0,"virtual pad mapping");pad=SDL_JoystickOpen(device);require(pad,"virtual pad open");
  pc_window_set_stick_invert(0);pc_window_set_cstick_invert(0);pc_window_set_gamepad_binding(PC_KEY_ACT_A,SDL_CONTROLLER_BUTTON_A);pc_window_set_gamepad_binding(PC_KEY_ACT_B,SDL_CONTROLLER_BUTTON_B);input();
 }
 gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new TutorialApp());return 0;
}
