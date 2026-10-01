// #1096 generated source44 -> ordinary native combat/carry -> durable AP check.
// Existing production TEST_BACKGROUND withdraws20. No creature/health/check writes.
#include <SDL2/SDL.h>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>
#include <queue>
#include "system.h"
#include "App.h"
#include "Node.h"
#include "Section.h"
#include "FlowController.h"
#include "MoviePlayer.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Camera.h"
#include "Route.h"
#include "BuildingItem.h"
#include "ItemMgr.h"
#include "KeyConfig.h"
#include "Kontroller.h"
#include "CPlate.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "Pellet.h"
#include "teki.h"
#include "GameStat.h"
#include "GameFlow.h"
#include "PlayerState.h"
#include "Demo.h"
#include "pc_randomizer.h"
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "C:/Users/alari/pikmin-randomizer/scripts/p2_fixture_captain_guard.h"

namespace {
constexpr unsigned Target=3921089765;
const char* Check="P2:44"; // Native resolved key; AP human label is resolved by NativeRun.
SDL_Joystick* pad=nullptr;int requestedX=0,requestedY=0;
void require(bool yes,const char* reason){if(!yes){std::printf("FAIL P2_GENERATED_DELIVERY %s\n",reason);std::fflush(nullptr);std::_Exit(1);}}
void input(unsigned keys=0,int x=0,int y=0,int cx=0,int cy=0){
 requestedX=x;requestedY=y;
 // Campaign card selection resets device routing; keep the disclosed virtual P1.
 int id=-1;int kind=pc_window_input_get_assignment(0,&id);
 if(kind!=PC_INPUT_DEV_GAMEPAD || id!=SDL_JoystickInstanceID(pad)){std::printf("P2_GENERATED_ROUTE_RESTORE previous_kind=%d previous_id=%d virtual_id=%d\n",kind,id,int(SDL_JoystickInstanceID(pad)));std::fflush(nullptr);pc_window_input_assign(0,PC_INPUT_DEV_GAMEPAD,SDL_JoystickInstanceID(pad));pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);}
 SDL_JoystickSetVirtualButton(pad,SDL_CONTROLLER_BUTTON_A,(keys&KBBTN_A)!=0);
 SDL_JoystickSetVirtualButton(pad,SDL_CONTROLLER_BUTTON_B,(keys&KBBTN_B)!=0);
 SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_LEFTX,Sint16(x*32767/74));
 SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_LEFTY,Sint16(-y*32767/74));
 SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_RIGHTX,Sint16(cx*32767/74));
 SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_RIGHTY,Sint16(-cy*32767/74));
 SDL_JoystickUpdate();
}
void point(Navi* n,const Vector3f& goal,bool walk,unsigned keys=0){
 const Vector3f& from=walk?n->mSRT.t:n->mCursorWorldPos;
 float dx=goal.x-from.x,dz=goal.z-from.z,d=std::sqrt(dx*dx+dz*dz);
 int x=0,y=0;
 if(d>(walk?15.f:6.f)){
  const Vector3f& axis=n->controlCamera()->mViewXAxis;float power=walk?65:22;
  x=int(std::lround(power*(dx*axis.x+dz*axis.z)/d));y=int(std::lround(power*(dx*axis.z-dz*axis.x)/d));
 }
 input(keys,x,y);
}
BuildingItem* routeGate=nullptr;
std::vector<Vector3f> approachRoute(const Vector3f& from,const Vector3f& goal){
 routeGate=nullptr;require(routeMgr,"native route graph missing");const unsigned handle='test';int count=routeMgr->getNumWayPoints(handle);require(count>0 && count<=4096,"native route graph size");
 int start=-1,end=-1;float nearStart=1e30f,nearEnd=1e30f;
 for(int i=0;i<count;++i){WayPoint* w=routeMgr->getWayPoint(handle,i);if(!w || !w->mIsOpen || w->inWater())continue;
  float dx=w->mPosition.x-from.x,dz=w->mPosition.z-from.z,dy=w->mPosition.y-from.y;float a=dx*dx+dz*dz+9*dy*dy;
  dx=w->mPosition.x-goal.x;dz=w->mPosition.z-goal.z;dy=w->mPosition.y-goal.y;float b=dx*dx+dz*dz+9*dy*dy;
  if(a<nearStart){nearStart=a;start=i;}if(b<nearEnd){nearEnd=b;end=i;}}
 require(start>=0 && end>=0,"open land route endpoints missing");std::vector<int> parent(count,-1);std::queue<int> pending;parent[start]=start;pending.push(start);
 while(!pending.empty() && parent[end]<0){int here=pending.front();pending.pop();WayPoint* w=routeMgr->getWayPoint(handle,here);
  for(int i=0;i<int(w->mLinkCount) && i<8;++i){int next=w->mLinkIndices[i];if(next<0 || next>=count || parent[next]>=0)continue;WayPoint* candidate=routeMgr->getWayPoint(handle,next);if(!candidate || candidate->inWater())continue;parent[next]=here;pending.push(next);}}
 for(int i=0;i<count;++i){WayPoint* w=routeMgr->getWayPoint(handle,i);if(w)std::printf("P2_GENERATED_ROUTE_NODE index=%d xyz=%.3f,%.3f,%.3f open=%d water=%d reached=%d links=%d\n",i,w->mPosition.x,w->mPosition.y,w->mPosition.z,int(w->mIsOpen),int(w->inWater()),int(parent[i]>=0),w->mLinkCount);}
 std::printf("P2_GENERATED_ROUTE_ENDPOINT start=%d end=%d count=%d\n",start,end,count);std::fflush(nullptr);require(parent[end]>=0,"original slot has no land route");std::vector<int> reversed;for(int i=end;;i=parent[i]){reversed.push_back(i);if(i==start)break;require(reversed.size()<=size_t(count),"route cycle");}
 std::vector<Vector3f> route;for(auto i=reversed.rbegin();i!=reversed.rend();++i){WayPoint* w=routeMgr->getWayPoint(handle,*i);if(!w->mIsOpen){require(itemMgr && itemMgr->getMeltingPotMgr(),"gate item manager missing");Iterator items(itemMgr->getMeltingPotMgr());CI_LOOP(items){Creature* c=*items;if(c->isSluice()){BuildingItem* b=static_cast<BuildingItem*>(c);if(b->mWayPoint && b->mWayPoint->mIndex==*i){require(!routeGate,"duplicate closed gate owner");routeGate=b;}}}require(routeGate,"closed route has no gate owner");require(routeGate->mObjType==OBJTYPE_SluiceSoft || routeGate->mObjType==OBJTYPE_SluiceHard,"bomb gate unsupported");std::printf("P2_GENERATED_GATE_WORK waypoint=%d type=%d stage=%d/%d hp=%.3f xyz=%.3f,%.3f,%.3f direct_writes=0\n",*i,routeGate->mObjType,routeGate->mCurrStage,routeGate->mNumStages,routeGate->mHealth,routeGate->mSRT.t.x,routeGate->mSRT.t.y,routeGate->mSRT.t.z);break;}route.push_back(w->mPosition);std::printf("P2_GENERATED_ROUTE_LEG index=%d waypoint=%d xyz=%.3f,%.3f,%.3f open_land=1 world_writes=0\n",int(route.size()-1),*i,w->mPosition.x,w->mPosition.y,w->mPosition.z);}
 std::fflush(nullptr);return route;
}
class DeliveryApp:public PlugPikiApp {
 int frames=0,observed=0,phase=0,phaseStart=0;bool captainSeen=false;Teki* enemy=nullptr;std::vector<Vector3f> route;size_t routeLeg=0;
 public:
 int idle()override{
  int result=PlugPikiApp::idle();Navi* n=naviMgr?naviMgr->getNavi():nullptr;
  if(n){captainSeen=true;p2_fixture_require_captain(GameStat::orimaDead,!n->getCurrState() || naviMgr->isNaviDead(n) || n->getCurrState()->getID()==NAVISTATE_Dead,std::getenv("P2_GENERATED_FORCE_CAPTAIN_DOWN")?0:n->mHealth,frames);}
  else if(captainSeen)p2_fixture_require_captain(true,true,0,frames);
  require(++frames<5000,"frame ceiling");
  if(frames<60 || frames%60==0){std::printf("P2_GENERATED_GATE frame=%d ready=%d pause=%d overlay=%d movie=%d nstate=%d managers=%d hp=%.3f\n",frames,int(pc_randomizer_ready()),int(gameflow.mPauseAll),int(gameflow.mIsUIOverlayActive),int(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive),n && n->getCurrState()?n->getCurrState()->getID():-1,int(tekiMgr && pikiMgr),n?n->mHealth:-1.f);std::fflush(nullptr);}
  if(playerState)for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f); // Disclosed tutorial instrumentation before starting-state wait.
  if(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(gameflow.mIsUIOverlayActive){input(frames%30<15?KBBTN_A:0);return result;}
  if(gameflow.mPauseAll || !pc_randomizer_ready() || !n || !n->getCurrState() || !tekiMgr || !pikiMgr || !n->controlCamera())return result;
  ++observed;
  if(phase==0 && n->getCurrState()->getID()==NAVISTATE_Starting){
   if(frames%10==0){NaviStartingState* start=static_cast<NaviStartingState*>(n->getCurrState());int count=0;Iterator ps(pikiMgr);CI_LOOP(ps){if(static_cast<Piki*>(*ps)->isAlive())++count;}std::printf("P2_GENERATED_START frame=%d phase=%d timer=%.4f anim_complete=%d dt=%.5f alive=%d navi=%.3f,%.3f target=%.3f,%.3f\n",frames,int(start->mStartPhase),start->mStartDelayTimer,int(start->mIsStartAnimComplete),gsys->getFrameTime(),count,n->mSRT.t.x,n->mSRT.t.z,start->mWalkTargetPos.x,start->mWalkTargetPos.z);std::fflush(nullptr);}
   return result;
  }
  int alive=0;Iterator pikis(pikiMgr);CI_LOOP(pikis){if(static_cast<Piki*>(*pikis)->isAlive())++alive;}
  if(!enemy){Iterator it(tekiMgr);CI_LOOP(it){Teki* t=static_cast<Teki*>(*it);if(pc_randomizer_p2_source_for(static_cast<PelletView*>(t))==44 && pc_randomizer_p2_generator_for(static_cast<PelletView*>(t))==Target){require(!enemy,"duplicate singleton source");enemy=t;}}}
  if(phase==0){
   if(observed<2)return result;
   int w,h,x,y;SDL_Window* window=SDL_GL_GetCurrentWindow();require(window,"current SDL window");SDL_GetWindowSize(window,&w,&h);SDL_GetWindowPosition(window,&x,&y);SDL_Rect bounds;require(SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window),&bounds)==0,"display bounds");
   std::printf("P2_GENERATED_WINDOW width=%d height=%d x=%d y=%d display=%d,%d,%d,%d\n",w,h,x,y,bounds.x,bounds.y,bounds.w,bounds.h);require(w==960 && h==540,"window dimensions");require(std::abs((x+w/2)-(bounds.x+bounds.w/2))<=2 && std::abs((y+h/2)-(bounds.y+bounds.h/2))<=2,"window centering");
   require(enemy,"generated source44 singleton not born");require(alive==20,"starting field squad differs from disclosed20");
   require(gameflow.mWorldClock.mCurrentDay==2,"unexpected initial day");
   std::printf("P2_GENERATED_BASELINE source=44 uid=%u day=2 alive=%d enemy=%.3f,%.3f,%.3f navi=%.3f,%.3f,%.3f hp=%.3f\n",Target,alive,enemy->mSRT.t.x,enemy->mSRT.t.y,enemy->mSRT.t.z,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,n->mHealth);
   for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f); // Disclosed tutorial instrumentation.
   phase=1;phaseStart=observed;
  }
  if(observed%60==0){std::printf("P2_GENERATED_SQUAD_INPUT followers=%d free_camera=%d right_SDL=%d,%d right_native=%.4f,%.4f whistle_bind=%u throw_bind=%u\n",n->getPlatePikis(),pc_settings_get_free_camera(),int(SDL_JoystickGetAxis(pad,SDL_CONTROLLER_AXIS_RIGHTX)),int(SDL_JoystickGetAxis(pad,SDL_CONTROLLER_AXIS_RIGHTY)),n->mKontroller->getSubStickX(),n->mKontroller->getSubStickY(),KeyConfig::_instance->mSetCursorKey.mBind,KeyConfig::_instance->mThrowKey.mBind);int assigned=-1;int kind=pc_window_input_get_assignment(0,&assigned);const Vector3f& axis=n->controlCamera()->mViewXAxis;std::printf("P2_GENERATED_INPUT_OBS request=%d,%d SDL=%d,%d native=%d,%d frozen=%d port=%d assigned_kind=%d assigned_id=%d camera_axis=%.3f,%.3f,%.3f\n",requestedX,requestedY,int(SDL_JoystickGetAxis(pad,SDL_CONTROLLER_AXIS_LEFTX)),int(SDL_JoystickGetAxis(pad,SDL_CONTROLLER_AXIS_LEFTY)),int(n->mKontroller->mMainStickX),int(n->mKontroller->mMainStickY),int(n->mKontroller->mIsControllerFrozen),n->mKontroller->mPlayerNum,kind,assigned,axis.x,axis.y,axis.z);std::printf("P2_GENERATED_PROGRESS frame=%d phase=%d alive=%d enemy_alive=%d hp=%.3f navi=%.3f,%.3f enemy=%.3f,%.3f\n",frames,phase,alive,int(enemy->isAlive()),n->mHealth,n->mSRT.t.x,n->mSRT.t.z,enemy->mSRT.t.x,enemy->mSRT.t.z);std::fflush(nullptr);}
  if(pc_randomizer_checked(Check)){std::puts("PASS P2_GENERATED_DELIVERY actual_native_check=1 direct_event_writes=0 scripted_virtual_P1=1");std::fflush(nullptr);std::_Exit(0);}
  if(phase==1){
   require(alive==20,"gather squad conservation");
   if(n->getPlatePikis()<20){std::vector<Creature*> joined;Iterator formation(n->mPlateMgr);CI_LOOP(formation){joined.push_back(*formation);}Piki* target=nullptr;float closest=1e30f;Iterator all(pikiMgr);CI_LOOP(all){Piki* p=static_cast<Piki*>(*all);if(!p->isAlive())continue;bool follows=false;for(auto c:joined)if(c==p)follows=true;if(follows)continue;float px=p->mSRT.t.x-n->mSRT.t.x,pz=p->mSRT.t.z-n->mSRT.t.z;float distance=px*px+pz*pz;if(distance<closest){closest=distance;target=p;}}require(target,"unjoined live Pikmin missing");if(observed%30==0){std::printf("P2_GENERATED_GATHER following=%d target=%.3f,%.3f,%.3f state=%d distance=%.3f direct_join_writes=0\n",n->getPlatePikis(),target->mSRT.t.x,target->mSRT.t.y,target->mSRT.t.z,target->getCurrState()?target->getCurrState()->getID():-1,std::sqrt(closest));std::fflush(nullptr);}point(n,target->mSRT.t,closest>150*150,KeyConfig::_instance->mSetCursorKey.mBind);return result;}
   std::printf("P2_GENERATED_GATHER_COMPLETE following=%d alive=%d ordinary_whistle=1\n",n->getPlatePikis(),alive);phase=2;phaseStart=observed;routeLeg=0;route=approachRoute(n->mSRT.t,enemy->mSRT.t);return result;}

  float dx=enemy->mSRT.t.x-n->mSRT.t.x,dz=enemy->mSRT.t.z-n->mSRT.t.z;
  if(phase==2){
   while(routeLeg<route.size()){float rx=route[routeLeg].x-n->mSRT.t.x,rz=route[routeLeg].z-n->mSRT.t.z;if(rx*rx+rz*rz>25*25)break;std::printf("P2_GENERATED_ROUTE_REACHED leg=%d navi=%.3f,%.3f\n",int(routeLeg),n->mSRT.t.x,n->mSRT.t.z);++routeLeg;}
   if(routeLeg==route.size() && routeGate){phase=6;phaseStart=observed;input();return result;}point(n,routeLeg<route.size()?route[routeLeg]:enemy->mSRT.t,true);if(dx*dx+dz*dz<120*120){phase=3;phaseStart=observed;input();}return result;}
  if(phase==6){require(routeGate,"gate work target missing");if(observed%30==0){std::printf("P2_GENERATED_GATE_PROGRESS stage=%d/%d hp=%.3f completed=%d alive=%d\n",routeGate->mCurrStage,routeGate->mNumStages,routeGate->mHealth,int(routeGate->isCompleted()),alive);std::fflush(nullptr);}if(routeGate->isCompleted()){std::puts("P2_GENERATED_GATE_COMPLETED production=1 direct_writes=0");phase=1;phaseStart=observed;input(KeyConfig::_instance->mSetCursorKey.mBind);return result;}float gx=routeGate->mSRT.t.x-n->mSRT.t.x,gz=routeGate->mSRT.t.z-n->mSRT.t.z;float distance=std::sqrt(gx*gx+gz*gz);const Vector3f& axis=n->controlCamera()->mViewXAxis;int sx=int(65*(gx*axis.x+gz*axis.z)/distance),sy=int(65*(gx*axis.z-gz*axis.x)/distance);input(0,distance>60?sx:0,distance>60?sy:0,sx,sy);return result;}
  if(phase==3){
   unsigned keys=(observed-phaseStart)%60<15?KeyConfig::_instance->mThrowKey.mBind:0;
   point(n,enemy->mSRT.t,false,keys);
   if(!enemy->isAlive()){phase=4;phaseStart=observed;std::puts("P2_GENERATED_NATURAL_DEATH observed=1 health_writes=0");}
   return result;
  }
  // Observe the actual production corpse; never attach carriers or emit receipts.
  if(phase==4 || phase==5){Pellet* body=nullptr;Iterator pellets(pelletMgr);CI_LOOP(pellets){Pellet* p=static_cast<Pellet*>(*pellets);unsigned source=p->mPelletView?pc_randomizer_p2_source_for(p->mPelletView):0;unsigned uid=p->mPelletView?pc_randomizer_p2_generator_for(p->mPelletView):0;if(observed%60==0 && p->mPelletView)std::printf("P2_GENERATED_PELLET source=%u uid=%u xyz=%.3f,%.3f,%.3f carriers=%u strength=%u min=%d state=%u\n",source,uid,p->mSRT.t.x,p->mSRT.t.y,p->mSRT.t.z,p->mCarrierCount,p->mCarrierCounter,p->mConfig?p->mConfig->mCarryMinPikis():-1,p->mCarryState);if(source==44 && uid==Target){require(!body,"duplicate bound corpse");body=p;}}if(!body){input();return result;}dx=body->mSRT.t.x-n->mSRT.t.x;dz=body->mSRT.t.z-n->mSRT.t.z;float d=std::sqrt(dx*dx+dz*dz);require(body->mConfig,"corpse config missing");if(body->mCarrierCount>=body->mConfig->mCarryMinPikis()){input();return result;}const Vector3f& axis=n->controlCamera()->mViewXAxis;int sx=d>1?int(65*(dx*axis.x+dz*axis.z)/d):0,sy=d>1?int(65*(dx*axis.z-dz*axis.x)/d):0;input(0,d>60?sx:0,d>60?sy:0,sx,sy);phase=5;return result;}

  return result;
 }
};
}
int main(int argc,char**argv){
 SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,"1");SDL_SetMainReady();pc_gpu_preference_apply();
 _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");pc_bbft_init(argc,argv);require(pc_randomizer_enabled(),"requires generated full-session bootstrap");
 if(!pc_window_init("Generated P2 delivery acceptance",960,540))return 3;
 pc_settings_init();pc_window_set_control_mode(PC_CONTROL_CLASSIC);pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);pc_window_set_window_size(960,540);pc_window_center();
 std::puts("Experimental preview window set to 960x540 windowed and centered");
 int device=SDL_JoystickAttachVirtual(SDL_JOYSTICK_TYPE_GAMECONTROLLER,SDL_CONTROLLER_AXIS_MAX,SDL_CONTROLLER_BUTTON_MAX,0);require(device>=0,"virtual pad attach");
 char guid[64];SDL_JoystickGetGUIDString(SDL_JoystickGetDeviceGUID(device),guid,sizeof(guid));std::string mapping=std::string(guid)+",Generated delivery pad,a:b0,b:b1,x:b2,y:b3,back:b4,guide:b5,start:b6,leftstick:b7,rightstick:b8,leftshoulder:b9,rightshoulder:b10,dpup:b11,dpdown:b12,dpleft:b13,dpright:b14,leftx:a0,lefty:a1,rightx:a2,righty:a3,lefttrigger:a4,righttrigger:a5,";
 require(SDL_GameControllerAddMapping(mapping.c_str())>=0,"virtual pad mapping");pad=SDL_JoystickOpen(device);require(pad!=nullptr,"virtual pad open");
 pc_window_input_assign(0,PC_INPUT_DEV_GAMEPAD,SDL_JoystickInstanceID(pad));pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);pc_window_set_stick_invert(0);pc_window_set_cstick_invert(0);
 pc_window_set_gamepad_binding(PC_KEY_ACT_A,SDL_CONTROLLER_BUTTON_A);pc_window_set_gamepad_binding(PC_KEY_ACT_B,SDL_CONTROLLER_BUTTON_B);
 std::puts("P2_GENERATED_INPUT SDL_virtual_P1 native_polling=1 ordinary_combat_carry=1");
 gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new DeliveryApp());return 0;
}
