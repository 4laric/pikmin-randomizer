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
#include "Kontroller.h"
#include "CPlate.h"
#include "Camera.h"
#include "Piki.h"
#include "PikiState.h"
#include "PikiMgr.h"
#include "Generator.h"
#include "MapMgr.h"
#include "Collision.h"
#include "MapCode.h"
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
unsigned whistleBind=0;int whistleButton=-1,requestedX=0,requestedY=0;bool requestedWhistle=false;
int whistle_action(unsigned binding){
 if(binding==KBBTN_A)return PC_KEY_ACT_A;if(binding==KBBTN_B)return PC_KEY_ACT_B;
 if(binding==KBBTN_X)return PC_KEY_ACT_X;if(binding==KBBTN_Y)return PC_KEY_ACT_Y;
 require(false,"unsupported loaded whistle action");return -1;
}
void publish_input(int x,int y,bool whistle,int rx=0,int ry=0){
 pc_window_input_assign(0,PC_INPUT_DEV_GAMEPAD,SDL_JoystickInstanceID(pad));
 pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);
 require(x>=-74&&x<=74&&y>=-74&&y<=74,"ordinary GC axis domain");
 require(rx>=-74&&rx<=74&&ry>=-74&&ry<=74,"ordinary GC squad axis domain");
 for(int button=0;button<SDL_CONTROLLER_BUTTON_MAX;++button)SDL_JoystickSetVirtualButton(pad,button,0);
 if(whistle){require(whistleButton>=0&&whistleButton<SDL_CONTROLLER_BUTTON_MAX,"unadmitted whistle button");SDL_JoystickSetVirtualButton(pad,whistleButton,1);}
 requestedX=x;requestedY=y;requestedWhistle=whistle;
 SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_LEFTX,Sint16(x*256));
 SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_LEFTY,Sint16(-y*256));
 SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_RIGHTX,Sint16(rx*256));
 SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_RIGHTY,Sint16(-ry*256));SDL_JoystickUpdate();
}
void input(Navi* n,float gx,bool whistle=false,float gz=1000.f,float squadX=0.f,float squadZ=0.f) {
 int x=0,y=0,rx=0,ry=0;
 float dx=gx-n->mSRT.t.x,dz=gz-n->mSRT.t.z,d=std::sqrt(dx*dx+dz*dz);
 if(d>12.f){const Vector3f& a=n->controlCamera()->mViewXAxis;
  x=int(std::lround(65.f*(dx*a.x+dz*a.z)/d));y=int(std::lround(65.f*(dx*a.z-dz*a.x)/d));}
 if(d<=12.f&&!whistle){
  const float length=std::sqrt(squadX*squadX+squadZ*squadZ);
  if(length>1.f){const Vector3f& a=n->controlCamera()->mViewXAxis;
   rx=int(std::lround(65.f*(squadX*a.x+squadZ*a.z)/length));
   ry=int(std::lround(65.f*(squadX*a.z-squadZ*a.x)/length));}
 }
 publish_input(x,y,whistle,rx,ry); // Faithful SDL/PAD256 and GC74 domain.
}
// Release previously published alignment input without dereferencing actors/camera.
void neutral_input() {
 publish_input(0,0,false);
}
// Actual retail cave entrance and route vertices 20/19; the high ridge is
// a source cliff, not an authored captain travel corridor.
struct Waypoint {float x,z,floor;};
constexpr std::array<Waypoint,3> route{{{-190.f,1160.f,80.f},
 {-257.914246f,1351.235229f,50.f},{-434.148010f,1271.501343f,50.f}}};
struct Track {Creature* actor=nullptr;int outbound=0,back=0;};
class UpperApp:public PlugPikiApp {
 std::array<Track,21> roster{};
 std::array<bool,2> initializedBefore{};
 int tick=0,ready=0,phase=0,phaseAge=0,settle=0;
 float target=-250.f,targetZ=1000.f;
 int routeStep=0;
 bool bankReady=false;
 int gatherStage=0,gatherSince=0,gatherUid=0,lastTelemetryPhase=-1;
 void route_input(Navi* n,bool outbound){
  const int index=outbound?routeStep:2-routeStep;
  float fromX,fromZ;
  if(outbound&&index==0){fromX=-250.f;fromZ=1025.f;}
  else if(!outbound&&index==2){fromX=2*route[2].x-route[1].x;fromZ=2*route[2].z-route[1].z;}
  else{const int previous=outbound?index-1:index+1;fromX=route[previous].x;fromZ=route[previous].z;}
  // Once the captain arrives, use the ordinary C-stick to guide the existing
  // formation across this exact checkpoint; no actor or plate writes.
  input(n,target,false,targetZ,route[index].x-fromX,route[index].z-fromZ);
  if(tick%15==0)std::printf("P2_UPPER_SQUAD_INPUT tick=%d checkpoint=%d requested_next_SDL_right=%d,%d observed_tick_native_sub=%d,%d observed_tick_world_cstick=%.6f,%.6f,%.6f ordinary_SDL=1 actor_writes=0\n",
   tick,index,int(SDL_JoystickGetAxis(pad,SDL_CONTROLLER_AXIS_RIGHTX)),int(SDL_JoystickGetAxis(pad,SDL_CONTROLLER_AXIS_RIGHTY)),
   int(n->mKontroller->mSubStickX),int(n->mKontroller->mSubStickY),n->mCStick.x,n->mCStick.y,n->mCStick.z);
 }
 bool plate_membership(Navi* n,const std::array<Piki*,20>& current,std::array<bool,20>& joined){
  joined.fill(false);int members=0;
  // PC occupied slots are authoritative immediately after Pikmin update.
  // CPlate's iterator uses the earlier Navi-refreshed layout count instead.
  const int occupied=n->getPlatePikis();
  require(occupied>=0&&occupied<=20,"actual occupied plate count outside original roster");
  for(int slot=0;slot<occupied;++slot){Creature* member=n->mPlateMgr->getCreature(slot);int uid=-1;
   for(int i=0;i<20;++i)if(member==current[i])uid=i;
   require(uid>=0&&!joined[uid],"unexpected duplicate/nonoriginal plate member");
   require(current[uid]->mNavi==n&&current[uid]->mMode==PikiMode::FormationMode,"actual plate ownership/mode mismatch");joined[uid]=true;++members;
  }
  require(members==n->getPlatePikis(),"actual plate count mismatch");return members==20;
 }
 void approach_telemetry(Navi* n) {
  if(phase!=2||tick%15)return;
  const Vector3f& a=n->controlCamera()->mViewXAxis;
  const Vector3f zero(0.f,0.f,0.f);
  const Vector3f& ground=n->mGroundTriangle?n->mGroundTriangle->mTriangle.mNormal:zero;
  const Vector3f& wall=n->mWallPlane?n->mWallPlane->mNormal:zero;
  const Vector3f& last=n->mCollNormal?*n->mCollNormal:zero;
  int groundFace=-1;
  for(int i=0;n->mGroundTriangle&&i<mapMgr->mMapModel->mTriCount;++i)
   if(n->mGroundTriangle==&mapMgr->mMapModel->mTriList[i]){groundFace=i;break;}
  std::printf("P2_UPPER_APPROACH tick=%d phase=%d age=%d goal=%.3f,%.3f xyz=%.3f,%.3f,%.3f camera_x=%.7f,%.7f,%.7f world_transformed_stick=%.7f,%.7f,%.7f target_velocity=%.7f,%.7f,%.7f velocity=%.7f,%.7f,%.7f force_B0=%.7f,%.7f,%.7f volatile=%.7f,%.7f,%.7f ground_face=%d ground_normal=%.7f,%.7f,%.7f ground_mapcode=%u ground_slip=%d wall_present=%d wall_normal=%.7f,%.7f,%.7f last_collision_present=%d last_collision_normal=%.7f,%.7f,%.7f collision_radius=%.7f feet_offset=%.7f ordinary_SDL=1 actor_writes=0 collision_events=UNOBSERVED\n",
   tick,phase,tick-phaseAge,target,targetZ,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,a.x,a.y,a.z,
   n->mMainStick.x,n->mMainStick.y,n->mMainStick.z,n->mTargetVelocity.x,n->mTargetVelocity.y,n->mTargetVelocity.z,
   n->mVelocity.x,n->mVelocity.y,n->mVelocity.z,n->_B0.x,n->_B0.y,n->_B0.z,
   n->mVolatileVelocity.x,n->mVolatileVelocity.y,n->mVolatileVelocity.z,groundFace,ground.x,ground.y,ground.z,
   n->mGroundTriangle?unsigned(n->mGroundTriangle->mMapCode):0u,MapCode::getSlipCode(n->mGroundTriangle),
   int(n->mWallPlane!=nullptr),wall.x,wall.y,wall.z,int(n->mCollNormal!=nullptr),last.x,last.y,last.z,n->mCollisionRadius,n->mGroundOffset);
  std::fflush(stdout);
 }
 void recruitment_telemetry(Navi* n,const std::array<Piki*,20>& current,const std::array<bool,20>& joined){
  if(tick%15&&lastTelemetryPhase==phase)return;lastTelemetryPhase=phase;
  float radius=0.f;if(n->getCurrState()->getID()==NAVISTATE_Gather)radius=static_cast<NaviGatherState*>(n->getCurrState())->mWhistleCallRadius;
  int assigned=-1;int kind=pc_window_input_get_assignment(0,&assigned);
  std::printf("P2_UPPER_INPUT tick=%d phase=%d phase_age=%d gather_stage=%d target_uid=%d plate=%d state=%d whistle_bind=%u extract_bind=%u throw_bind=%u SDL_button=%d requested_whistle=%d requested_pad=%d,%d SDL_axes=%d,%d native_bits=%u down=%d click=%d up=%d native_axes=%d,%d frozen=%d port=%u assigned_kind=%d assigned_id=%d cursor_visible=%d cursor=%.3f,%.3f,%.3f radius=%.7f held_timer=%.7f ordinary_SDL=1 actor_writes=0\n",
   tick,phase,tick-phaseAge,gatherStage,gatherUid,n->getPlatePikis(),n->getCurrState()->getID(),whistleBind,KeyConfig::_instance->mExtractKey.mBind,KeyConfig::_instance->mThrowKey.mBind,whistleButton,int(requestedWhistle),requestedX,requestedY,int(SDL_JoystickGetAxis(pad,SDL_CONTROLLER_AXIS_LEFTX)),int(SDL_JoystickGetAxis(pad,SDL_CONTROLLER_AXIS_LEFTY)),unsigned(n->mKontroller->mCurrentInput),int(n->mKontroller->keyDown(whistleBind)),int(n->mKontroller->keyClick(whistleBind)),int(n->mKontroller->keyUp(whistleBind)),int(n->mKontroller->mMainStickX),int(n->mKontroller->mMainStickY),int(n->mKontroller->mIsControllerFrozen),unsigned(n->mKontroller->mPlayerNum),kind,assigned,int(n->mIsCursorVisible),n->mCursorWorldPos.x,n->mCursorWorldPos.y,n->mCursorWorldPos.z,radius,n->mWhistleTimer);
  for(int i=0;i<20;++i){Piki* p=current[i];float dx=p->mSRT.t.x-n->mCursorWorldPos.x,dz=p->mSRT.t.z-n->mCursorWorldPos.z;
   std::printf("P2_UPPER_RECRUIT tick=%d phase=%d uid=%d joined=%d mode=%u state=%d owned_navi=%d callable_flag=%d buried=%d cursor_distance=%.4f\n",tick,phase,i+1,int(joined[i]),unsigned(p->mMode),p->getState(),int(p->mNavi==n),int(p->mIsCallable),int(p->isBuried()),std::sqrt(dx*dx+dz*dz));}
  std::fflush(stdout);
 }
 void point_red(Navi* n,Piki* p){
  float bx=p->mSRT.t.x-n->mSRT.t.x,bz=p->mSRT.t.z-n->mSRT.t.z;bool walk=bx*bx+bz*bz>150.f*150.f;
  const Vector3f& from=walk?n->mSRT.t:n->mCursorWorldPos;float dx=p->mSRT.t.x-from.x,dz=p->mSRT.t.z-from.z,d=std::sqrt(dx*dx+dz*dz);int x=0,y=0;
  if(d>(walk?15.f:6.f)){const Vector3f& axis=n->controlCamera()->mViewXAxis;float power=walk?65.f:22.f;x=int(std::lround(power*(dx*axis.x+dz*axis.z)/d));y=int(std::lround(power*(dx*axis.z-dz*axis.x)/d));
   if(!walk){float magnitude=std::sqrt(float(x*x+y*y))/74.f;require(magnitude>C_NAVI_PARM(n,mNeutralStickThreshold)&&magnitude<=C_NAVI_PARM(n,mCursorMoveStickThreshold),"loaded cursor-only stick band unsupported");}
  }
  publish_input(x,y,false);
 }
 bool regroup(Navi* n,const std::array<Piki*,20>& current,const std::array<bool,20>& joined,bool allJoined){
  require(KeyConfig::_instance->mSetCursorKey.mBind==whistleBind&&pc_window_get_gamepad_binding(whistle_action(whistleBind))==whistleButton,"loaded whistle mapping changed");
  if(!gatherStage&&allJoined&&n->getCurrState()->getID()==NAVISTATE_Walk)return true;
  if(!gatherStage){gatherUid=0;float closest=1e30f;for(int i=0;i<20;++i)if(!joined[i]){float dx=current[i]->mSRT.t.x-n->mSRT.t.x,dz=current[i]->mSRT.t.z-n->mSRT.t.z,d=dx*dx+dz*dz;if(d<closest){closest=d;gatherUid=i+1;}}
   gatherStage=allJoined?3:1;gatherSince=tick;require(allJoined||gatherUid,"unjoined original Red missing");
  }
  if(gatherStage==1){
   if(joined[gatherUid-1]){gatherStage=3;gatherSince=tick;neutral_input();return false;}
   require(n->getCurrState()->getID()==NAVISTATE_Walk,"cursor aim requires actual Walk");Piki* p=current[gatherUid-1];point_red(n,p);
   float dx=p->mSRT.t.x-n->mCursorWorldPos.x,dz=p->mSRT.t.z-n->mCursorWorldPos.z;
   if(dx*dx+dz*dz<=36.f){require(n->mIsCursorVisible,"ordinary whistle cursor hidden");gatherStage=2;gatherSince=tick;publish_input(0,0,true);}return false;
  }
  if(gatherStage==2){
   if(joined[gatherUid-1]||allJoined||tick-gatherSince>=60){gatherStage=3;gatherSince=tick;neutral_input();}
   else publish_input(0,0,true);return false;
  }
  neutral_input(); // Explicit ordinary key-up; never reset phaseAge on an attempt.
  if(n->getCurrState()->getID()==NAVISTATE_Walk&&n->mKontroller->keyUp(whistleBind)){gatherStage=0;gatherUid=0;return allJoined;}
  return false;
 }
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
  if(sourceContact){
   auto at=[&](const Waypoint& q){float dx=p.x-q.x,dz=p.z-q.z;
    return dx*dx+dz*dz<=50.f*50.f&&std::fabs(floor-q.floor)<=12.f;};
   // Every original body must independently make actual source contact at
   // all three anchors in order; arrival by the captain alone never advances.
   if(phase==2&&t.outbound<3&&at(route[t.outbound]))++t.outbound;
   if(phase==3&&t.outbound==3&&t.back<3&&at(route[2-t.back]))++t.back;
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
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){if(!bankReady){ready=0;neutral_input();}gameflow.mMoviePlayer->requestSkip();return result;}
  Navi* n=naviMgr?naviMgr->getNavi():nullptr;
  if(!n||!n->getCurrState()||!pikiMgr||!mapMgr||gameflow.mPauseAll||gameflow.mIsUIOverlayActive){if(!bankReady){ready=0;neutral_input();}return result;}
  require(flowCont.mCurrentStage&&!std::strcmp(flowCont.mCurrentStage->mFileName,"stages/p2_tutorial.ini"),"wrong tutorial stage");
  require(!gameflow.mIsChallengeMode&&!pc_pikipelago_room_preview(),"wrong course lifecycle");
  require(mapMgr->mMapModel&&mapMgr->mMapModel->mTriCount==5332,"complete source faces missing");
  require(routeMgr&&routeMgr->getNumWayPoints('test')==102,"complete original route graph missing");
  require(pc_p2_surface_water_active()&&pc_p2_surface_water_count()==3,"source water owner missing");
  std::array<Piki*,20> current{};int count=0;
  Iterator it(pikiMgr);CI_LOOP(it){auto* q=static_cast<Piki*>(*it);if(!q->isAlive())continue;
   unsigned uid=q->mGenerator?static_cast<unsigned>(q->mGenerator->_70):0;require(uid>=1&&uid<=20&&!current[uid-1],"original roster UID missing/duplicate/new actor");
   current[uid-1]=q;++count;}
  require(count==20,"original twenty live Reds lost");
  if(!bankReady){if(n->getCurrState()->getID()!=NAVISTATE_Walk){ready=0;neutral_input();return result;}
   // Engineering spawn clearance settles through ordinary gravity/collisions.
   // Reacquire the disclosed bank anchor using the existing calibrated SDL path;
   // preserve the exact pose gate rather than assuming the birth pose is stationary.
   input(n,-250.f,false); // No whistle transition during Walk-only alignment.
   if(tick%15==0){
    std::printf("P2_UPPER_BANK_ALIGNMENT tick=%d state=%d xyz=%.3f,%.3f,%.3f velocity=%.3f,%.3f,%.3f target_velocity=%.3f,%.3f,%.3f ground=%d wall=%d ordinary_SDL=1 actor_writes=0 ready_frames=%d\n",
     tick,n->getCurrState()->getID(),n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,n->mVelocity.x,n->mVelocity.y,n->mVelocity.z,n->mTargetVelocity.x,n->mTargetVelocity.y,n->mTargetVelocity.z,int(n->mGroundTriangle!=nullptr),int(n->mWallPlane!=nullptr),ready);
    std::fflush(nullptr);
   }
   if(!(n->mSRT.t.x<-230.f&&std::fabs(n->mSRT.t.z-1000.f)<20.f)){ready=0;return result;}
   if(++ready<45)return result;
   require(!pc_settings_get_piki_invincible()&&!pc_settings_get_blues_only_water(),"hazard settings changed ordinary baseline");
   require(std::fabs(pc_settings_get_navi_speed_scale()-1.f)<.0001f,"captain speed changed ordinary baseline");
   require(!pc_settings_get_no_trip()&&!pc_settings_get_instant_whistle()&&!pc_settings_get_all_flowers(),"follower settings changed ordinary baseline");
   require(pc_settings_get_whistle_radius_pct()==100&&pc_settings_get_navi_health_pct()==100,"captain upgrades changed ordinary baseline");
   roster[0].actor=n;for(int i=0;i<20;++i)roster[i+1].actor=current[i];
   bool originalContacts=true;
   for(int i=0;i<21;++i)if(!observe(roster[i],i))originalContacts=false;
   // Native actors settle asynchronously on overlapping source faces. Keep
   // the exact contact predicate and bounded startup; wait for all originals
   // instead of accepting or rejecting one arbitrary readiness sample.
   if(!originalContacts){neutral_input();return result;}
   require(n->mSRT.t.x<-230.f&&std::fabs(n->mSRT.t.z-1000.f)<20.f,"wrong disclosed bank start");
   require(KeyConfig::_instance&&n->mKontroller&&n->mPlateMgr&&n->mProps,"loaded ordinary control/plate missing");
   whistleBind=KeyConfig::_instance->mSetCursorKey.mBind;
   require(whistleBind!=KeyConfig::_instance->mExtractKey.mBind&&whistleBind!=KeyConfig::_instance->mThrowKey.mBind,"unsupported shared whistle action binding");
   int action=whistle_action(whistleBind);whistleButton=pc_window_get_gamepad_binding(action);
   require(whistleButton>=0&&whistleButton<SDL_CONTROLLER_BUTTON_MAX,"loaded whistle needs ordinary SDL button");
   for(int other: {PC_KEY_ACT_A,PC_KEY_ACT_B,PC_KEY_ACT_X,PC_KEY_ACT_Y})require(other==action||pc_window_get_gamepad_binding(other)!=whistleButton,"ambiguous loaded gamepad button mapping");
   bankReady=true;phase=1;phaseAge=tick;
   std::puts("P2_UPPER_READY live=20 faces=5332 waters=3 start=west_bank gameplay_pass=0");std::fflush(nullptr);
   if(flag("P2_UPPER_READY_ONLY"))std::_Exit(0);
  }
  require(roster[0].actor==n,"active captain replaced");
  for(int i=0;i<20;++i)require(roster[i+1].actor==current[i],"original roster pointer replaced");
  bool allSettled=true;for(int i=0;i<21;++i)if(!observe(roster[i],i))allSettled=false;
  require(tick-phaseAge<1000,"finite phase budget exceeded");
  std::array<bool,20> joined{};bool allJoined=plate_membership(n,current,joined);recruitment_telemetry(n,current,joined);
  approach_telemetry(n);
  bool gathered=regroup(n,current,joined,allJoined);
  if(!gathered){settle=0;return result;}
  if(phase==1){neutral_input();if(tick-phaseAge>=60){phase=2;phaseAge=tick;routeStep=0;target=route[0].x;targetZ=route[0].z;}return result;}
  if(phase==2){route_input(n,true);
   if(std::all_of(roster.begin(),roster.end(),[&](const Track& t){return t.outbound>routeStep;})){
    neutral_input();
    if(++routeStep==3){phase=3;phaseAge=tick;routeStep=0;target=route[2].x;targetZ=route[2].z;}
    else {target=route[routeStep].x;targetZ=route[routeStep].z;}}
   return result;}
  if(phase==3){route_input(n,false);
   if(std::all_of(roster.begin(),roster.end(),[&](const Track& t){return t.back>routeStep;})){
    neutral_input();
    if(++routeStep==3){phase=4;phaseAge=tick;target=-250.f;targetZ=1025.f;}
    else {target=route[2-routeStep].x;targetZ=route[2-routeStep].z;}}
   return result;}
  const bool atBank=std::all_of(roster.begin(),roster.end(),[](const Track& t){
   const Vector3f& p=t.actor->mSRT.t;float dx=p.x+250.f,dz=p.z-1025.f;
   return dx*dx+dz*dz<=50.f*50.f&&std::fabs(p.y-t.actor->mGroundOffset-80.f)<=12.f;});
  // Guide the ordinary formation over the original bank anchor, then release
  // both sticks for the unchanged all-body settled acceptance interval.
  if(!atBank){input(n,target,false,targetZ,target-route[0].x,targetZ-route[0].z);settle=0;return result;}
  neutral_input();
  if(n->getPlatePikis()!=20||n->getCurrState()->getID()!=NAVISTATE_Walk||!n->mKontroller->keyUp(whistleBind)||!allSettled){settle=0;return result;}
  if(++settle>=90){std::puts("PASS P2_UPPER_TRAVERSAL original_reds=20 original_captain=1 all_outbound=21 all_returned=21 source_faces=5332 source_water=3 route=retail_bank_20_19 high_ridge=UNPROVEN ordinary_SDL=1 actor_writes=0 gamefeel=UNPLAYED");std::fflush(nullptr);std::_Exit(0);}
  std::fflush(stdout);return result;
 }
};
}
int main(int argc,char** argv){
 SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,"1");SDL_SetMainReady();pc_gpu_preference_apply();pc_bbft_init(argc,argv);
 require(pc_pikipelago_surface_course()&&!std::strcmp(pc_pikipelago_surface_course(),"tutorial"),"explicit tutorial surface required");
 if(!pc_window_init("P2 upper terrain traversal",960,540))return 3;
 pc_settings_init();pc_window_set_control_mode(PC_CONTROL_CLASSIC);pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();
 require(!pc_settings_get_free_camera(),"ordinary C-stick squad control requires classic camera settings");
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
