// #1177. Only ordinary SDL input changes the world; all actor data is observed.
#include <SDL2/SDL.h>
#include <GL/gl.h>
#if defined(_WIN32) && defined(WIN32)
#undef WIN32
#endif
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
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
#include "PikiState.h"
#include "PikiMgr.h"
#include "MapMgr.h"
#include "Collision.h"
#include "Shape.h"
#include "Route.h"
#include "GameStat.h"
#include "KeyConfig.h"
#include "pc_bbft.h"
#include "pc_window.h"
#include "pc_gpu_preference.h"
#include "pc_p2_surface_water.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "p2_fixture_captain_guard.h"

namespace {
SDL_Joystick* pad=nullptr;
void require(bool yes,const char* why) {
 if(!yes){std::printf("FAIL P2_UPPER_TRAVERSAL %s\n",why);std::fflush(nullptr);std::_Exit(1);}
}
bool flag(const char* name){return std::getenv(name)!=nullptr;}
void input(Navi* n,float gx,bool whistle=false) {
 int x=0,y=0;
 float dx=gx-n->mSRT.t.x,dz=1000.f-n->mSRT.t.z,d=std::sqrt(dx*dx+dz*dz);
 if(d>12.f){const Vector3f& a=n->controlCamera()->mViewXAxis;
  x=int(std::lround(65.f*(dx*a.x+dz*a.z)/d));y=int(std::lround(65.f*(dx*a.z-dz*a.x)/d));}
 pc_window_input_assign(0,PC_INPUT_DEV_GAMEPAD,SDL_JoystickInstanceID(pad));
 pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);
 SDL_JoystickSetVirtualButton(pad,SDL_CONTROLLER_BUTTON_B,whistle);
 SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_LEFTX,Sint16(x*32767/74));
 SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_LEFTY,Sint16(-y*32767/74));SDL_JoystickUpdate();
}
struct Track {Creature* actor=nullptr;int outbound=0,back=0;};
class UpperApp:public PlugPikiApp {
 std::array<Track,21> roster{};
 std::array<bool,2> initializedBefore{};
 int tick=0,ready=0,phase=0,phaseAge=0,settle=0;
 float target=-250.f;
 bool bankReady=false;
 // Read the existing static contact, not a highest-ground teleport query.
 bool observe(Track& t,int uid) {
  Creature* c=t.actor;require(c&&c->isAlive(),"original actor lost");
  const Vector3f& p=c->mSRT.t;
  require(std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z),"nonfinite actual actor position");
  const float feet=p.y-c->mGroundOffset;
  auto* shape=mapMgr->mMapModel;
  auto* contact=c->mGroundTriangle;
  int face=-1;
  // Match pointers without arithmetic/comparison on an unrelated platform allocation.
  for(int i=0;contact&&i<shape->mTriCount;++i)if(contact==&shape->mTriList[i]){face=i;break;}
  float floor=0.f;
  auto* below=mapMgr->getStaticGroundBelow(p.x,p.z,feet+8.f,floor);
  const int water=pc_p2_surface_water_box(Vector3f(p.x,feet,p.z),c->getCentreSize());
  require(water==-1,"original actor entered source water");
  if(uid){auto* q=static_cast<Piki*>(c);require(q->mColor==Red&&q->mInWaterTimer==0&&q->getState()!=PIKISTATE_Drown,"original Red wet or identity changed");}
  Vector3f contactPoint(p.x,0.f,p.z);
  bool contactContains=face>=0&&contact->mTriangle.mNormal.y>0.f&&contact->inTriClampTo(contactPoint);
  // Retained coincident slip faces may both be valid contacts; do not collapse
  // them or require an arbitrary pointer tie-break from the independent query.
  bool sourceContact=contactContains&&below&&std::fabs(contactPoint.y-floor)<.1f&&std::fabs(feet-floor)<12.f;
  std::printf("P2_UPPER_ACTOR tick=%d phase=%d uid=%d xyz=%.3f,%.3f,%.3f feet=%.3f source_face=%d below_height=%.3f contact_matches=%d water=%d out=%d back=%d\n",
   tick,phase,uid,p.x,p.y,p.z,feet,face,floor,int(sourceContact),water,t.outbound,t.back);
  if(p.x>=-130.f&&p.x<=115.f&&std::fabs(p.z-1000.f)<=35.f&&face>=0)
   require(floor>60.f&&feet>60.f,"lower floor contact inside upper corridor");
  if(sourceContact&&std::fabs(p.z-1000.f)<=35.f){
   if(phase==2){if(t.outbound==0&&p.x>=-130.f&&p.x<=-95.f)t.outbound=1;
    if(t.outbound==1&&p.x>=-8.f&&p.x<=35.f)t.outbound=2;
    if(t.outbound==2&&p.x>=88.f)t.outbound=3;}
   if(phase==3&&t.outbound==3){if(t.back==0&&p.x<=8.f&&p.x>=-35.f)t.back=1;
    if(t.back==1&&p.x<=-115.f&&p.x>=-150.f)t.back=2;
    if(t.back==2&&p.x<=-230.f)t.back=3;}
  }
  return sourceContact;
 }
public:
 int idle() override {
  int result=PlugPikiApp::idle();
  // First post-engine boundary, including paused/movie/startup frames.
  for(int i=0;i<2;++i){Navi* n=naviMgr?naviMgr->getNavi(i):nullptr;
   bool initialized=n&&n->getCurrState();
   if(initializedBefore[i]&&!initialized)p2_fixture_require_captain(true,true,0.f,tick);
   if(initialized){initializedBefore[i]=true;
    bool forced=flag("P2_UPPER_FORCE_DOWN"),paused=flag("P2_UPPER_PAUSED_DOWN");
    if(paused)gameflow.mPauseAll=true; // Negative control only.
    p2_fixture_require_captain(GameStat::orimaDead||forced||paused,
     naviMgr->isNaviDead(n)||n->getCurrState()->getID()==NAVISTATE_Dead,n->mHealth,tick);}}
  ++tick;require(tick<3600,"frame bound; outer supervisor must cap60 seconds");
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  Navi* n=naviMgr?naviMgr->getNavi():nullptr;
  if(!n||!n->getCurrState()||!pikiMgr||!mapMgr||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  require(flowCont.mCurrentStage&&!std::strcmp(flowCont.mCurrentStage->mFileName,"stages/p2_tutorial.ini"),"wrong tutorial stage");
  require(!gameflow.mIsChallengeMode&&!pc_pikipelago_room_preview(),"wrong course lifecycle");
  require(mapMgr->mMapModel&&mapMgr->mMapModel->mTriCount==5332,"complete source faces missing");
  require(routeMgr&&routeMgr->getNumWayPoints('test')==102,"complete original route graph missing");
  require(pc_p2_surface_water_active()&&pc_p2_surface_water_count()==3,"source water owner missing");
  std::array<Piki*,20> current{};int count=0;
  Iterator it(pikiMgr);CI_LOOP(it){auto* q=static_cast<Piki*>(*it);if(!q->isAlive())continue;
   unsigned uid=q->getGeneratorID();require(uid>=1&&uid<=20&&!current[uid-1],"original roster UID missing/duplicate/new actor");
   current[uid-1]=q;++count;}
  require(count==20,"original twenty live Reds lost");
  if(!bankReady){if(n->getCurrState()->getID()!=NAVISTATE_Walk){ready=0;return result;}
   if(++ready<45)return result;
   require(!pc_settings_get_piki_invincible()&&!pc_settings_get_blues_only_water(),"hazard settings changed ordinary baseline");
   require(std::fabs(pc_settings_get_navi_speed_scale()-1.f)<.0001f,"captain speed changed ordinary baseline");
   require(!pc_settings_get_no_trip()&&!pc_settings_get_instant_whistle()&&!pc_settings_get_all_flowers(),"follower settings changed ordinary baseline");
   require(pc_settings_get_whistle_radius_pct()==100&&pc_settings_get_navi_health_pct()==100,"captain upgrades changed ordinary baseline");
   roster[0].actor=n;for(int i=0;i<20;++i)roster[i+1].actor=current[i];
   for(int i=0;i<21;++i)require(observe(roster[i],i),"READY requires original settled source contacts");
   require(n->mSRT.t.x<-230.f&&std::fabs(n->mSRT.t.z-1000.f)<20.f,"wrong disclosed bank start");
   bankReady=true;phase=1;phaseAge=tick;
   std::puts("P2_UPPER_READY live=20 faces=5332 waters=3 start=west_bank gameplay_pass=0");std::fflush(nullptr);
   if(flag("P2_UPPER_READY_ONLY"))std::_Exit(0);
  }
  require(roster[0].actor==n,"active captain replaced");
  for(int i=0;i<20;++i)require(roster[i+1].actor==current[i],"original roster pointer replaced");
  for(int i=0;i<21;++i)observe(roster[i],i);
  require(tick-phaseAge<1000,"finite phase budget exceeded");
  if(phase==1){input(n,-250.f,true);if(n->getPlatePikis()==20&&tick-phaseAge>=60){phase=2;phaseAge=tick;target=-115.f;}return result;}
  if(phase==2){input(n,target,true);
   if(std::fabs(n->mSRT.t.x-target)<12.f&&std::fabs(n->mSRT.t.z-1000.f)<15.f){
    if(target==-115.f)target=0.f;else if(target==0.f)target=160.f;}
   if(std::all_of(roster.begin(),roster.end(),[](const Track& t){return t.outbound==3;})){
    phase=3;phaseAge=tick;target=0.f;}return result;}
  if(phase==3){input(n,target,true);
   if(std::fabs(n->mSRT.t.x-target)<12.f&&std::fabs(n->mSRT.t.z-1000.f)<15.f){
    if(target==0.f)target=-125.f;else if(target==-125.f)target=-300.f;}
   if(std::all_of(roster.begin(),roster.end(),[](const Track& t){return t.back==3;})){
    phase=4;phaseAge=tick;}return result;}
  input(n,-250.f,true);
  if(n->getPlatePikis()!=20){settle=0;return result;}
  if(++settle>=90){std::puts("PASS P2_UPPER_TRAVERSAL original_reds=20 original_captain=1 all_outbound=21 all_returned=21 source_faces=5332 source_water=3 ordinary_SDL=1 actor_writes=0 gamefeel=UNPLAYED");std::fflush(nullptr);std::_Exit(0);}
  std::fflush(stdout);return result;
 }
};
}
int main(int argc,char** argv){
 SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,"1");SDL_SetMainReady();pc_gpu_preference_apply();pc_bbft_init(argc,argv);
 require(pc_pikipelago_surface_course()&&!std::strcmp(pc_pikipelago_surface_course(),"tutorial"),"explicit tutorial surface required");
 if(!pc_window_init("P2 upper terrain traversal",960,540))return 3;
 pc_settings_init();pc_window_set_control_mode(PC_CONTROL_CLASSIC);pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();
 SDL_Window* w=SDL_GL_GetCurrentWindow();int width,height,x,y;SDL_GetWindowSize(w,&width,&height);SDL_GetWindowPosition(w,&x,&y);SDL_Rect b{};SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(w),&b);
 require(width==960&&height==540&&std::abs(x-(b.x+(b.w-width)/2))<=2&&std::abs(y-(b.y+(b.h-height)/2))<=2,"centered960x540 baseline");
 std::puts("P2_UPPER_WINDOW size=960x540 centered=1");
 int device=SDL_JoystickAttachVirtual(SDL_JOYSTICK_TYPE_GAMECONTROLLER,SDL_CONTROLLER_AXIS_MAX,SDL_CONTROLLER_BUTTON_MAX,0);require(device>=0,"virtual pad attach");
 char guid[64];SDL_JoystickGetGUIDString(SDL_JoystickGetDeviceGUID(device),guid,sizeof(guid));
 std::string mapping=std::string(guid)+",Upper traversal pad,a:b0,b:b1,x:b2,y:b3,back:b4,guide:b5,start:b6,leftstick:b7,rightstick:b8,leftshoulder:b9,rightshoulder:b10,dpup:b11,dpdown:b12,dpleft:b13,dpright:b14,leftx:a0,lefty:a1,rightx:a2,righty:a3,lefttrigger:a4,righttrigger:a5,";
 require(SDL_GameControllerAddMapping(mapping.c_str())>=0,"virtual pad mapping");pad=SDL_JoystickOpen(device);require(pad,"virtual pad open");
 pc_window_set_stick_invert(0);pc_window_set_cstick_invert(0);pc_window_set_gamepad_binding(PC_KEY_ACT_B,SDL_CONTROLLER_BUTTON_B);
 gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new UpperApp());return 0;
}
