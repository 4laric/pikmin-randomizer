// Actual engine course boot observation; no health/input policy changes.
#include <SDL2/SDL.h>
#include "system.h"
#include "App.h"
#include "Node.h"
#include "FlowController.h"
#include "MoviePlayer.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Camera.h"
#include <string>
#include "Piki.h"
#include "PikiState.h"
#include "PikiAI.h"
#include "pc_blue_rescue.h"
#include "PikiMgr.h"
#include "MapMgr.h"
#include "Collision.h"
#include "PlayerState.h"
#include "GameStat.h"
#include "Generator.h"
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_p2_surface_topology.h"
#include "pc_p2_surface_water.h"
#include "KeyConfig.h"
#include "Demo.h"
#include "Shape.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

static void require(bool value,const char* text) {
    if (!value) {std::printf("FAIL P2_SURFACE_BOOT %s\n",text);std::fflush(nullptr);std::_Exit(1);}
}
static bool humanSmoke(){return std::getenv("P2_SURFACE_WATER_HUMAN_SMOKE")!=nullptr;}
static SDL_Joystick* pad=nullptr;
static int phase=0;
static Vector3f goal(340,30,1000);
static bool entered=false,exited=false;
static bool speciesProbe(){return true;}
static Piki* probeRed=nullptr;
static Piki* probeBlue=nullptr;
static bool redDrown=false,blueWet=false,held=false,thrown=false;
class WaterSurfaceApp: public PlugPikiApp {
    int tick=0, ready=0, settle=0;
    Vector3f origin;
    bool captainInitialized=false;
public:
    int idle() override {
        if(pad){
            Navi* before=naviMgr?naviMgr->getNavi():nullptr;
            int sx=0,sy=0;
            if((phase==2 || phase==3)&&before&&before->mNaviCamera){float dx=goal.x-before->mSRT.t.x,dz=goal.z-before->mSRT.t.z,d=std::sqrt(dx*dx+dz*dz);if(d>10){const Vector3f& axis=before->mNaviCamera->mViewXAxis;sx=int(65*(dx*axis.x+dz*axis.z)/d);sy=int(65*(dx*axis.z-dz*axis.x)/d);}}
            for(int b=0;b<SDL_CONTROLLER_BUTTON_MAX;++b)SDL_JoystickSetVirtualButton(pad,b,0);
            SDL_JoystickSetVirtualButton(pad,SDL_CONTROLLER_BUTTON_B,phase==1);
            if(phase==7 && settle<4){
                const unsigned bits[]={KBBTN_A,KBBTN_B,KBBTN_X,KBBTN_Y,KBBTN_Z,KBBTN_L,KBBTN_START};
                const int buttons[]={SDL_CONTROLLER_BUTTON_A,SDL_CONTROLLER_BUTTON_B,SDL_CONTROLLER_BUTTON_X,SDL_CONTROLLER_BUTTON_Y,SDL_CONTROLLER_BUTTON_RIGHTSHOULDER,SDL_CONTROLLER_BUTTON_LEFTSHOULDER,SDL_CONTROLLER_BUTTON_START};
                for(int i=0;i<7;++i)if(KeyConfig::_instance->mDisbandKey.mBind&bits[i])SDL_JoystickSetVirtualButton(pad,buttons[i],1);
            }
            SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_LEFTX,Sint16(sx*32767/74));
            SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_LEFTY,Sint16(-sy*32767/74));SDL_JoystickUpdate();
        }
        int result=PlugPikiApp::idle();
        // Canonical guard boundary: inspect immediately after engine idle,
        // including movie/pause/startup frames, before any readiness return.
        Navi* n=naviMgr?naviMgr->getNavi():nullptr;
        const bool initialized=n && n->getCurrState();
        if(initialized)captainInitialized=true;
        const bool forced=std::getenv("P2_SURFACE_WATER_FORCE_CAPTAIN_DOWN") != nullptr;
        const bool pauseNegative=std::getenv("P2_SURFACE_WATER_FORCE_PAUSED_CAPTAIN_DOWN") != nullptr;
        if(initialized && pauseNegative)gameflow.mPauseAll=true; // negative observer only
        if((captainInitialized && !initialized) || (initialized &&
            (GameStat::orimaDead || naviMgr->isNaviDead(n) || n->getCurrState()->getID()==NAVISTATE_Dead
             || !std::isfinite(n->mHealth) || n->mHealth<=1.0f || forced || pauseNegative))) {
            std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f initialized=%d movie=%d pause=%d outcome=BLOCKED\n",
                tick,n?n->mHealth:0.0f,int(initialized),int(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive),int(gameflow.mPauseAll));
            std::fflush(nullptr);std::_Exit(86);
        }
        ++tick; if(!humanSmoke())require(tick<2400,"frame timeout");
        if(initialized && tick%60==0){std::printf("P2_SURFACE_WATER_READY_FRAME tick=%d phase=%d state=%d navi=%.3f,%.3f,%.3f wet=%d box=%d ground=%.3f\n",tick,phase,n->getCurrState()->getID(),n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,int(n->mIsInWater),pc_p2_surface_water_box(n->mSRT.t,n->mCollisionRadius),mapMgr?mapMgr->getMinY(n->mSRT.t.x,n->mSRT.t.z,true):0.f);std::fflush(stdout);}
        if(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
        if(!naviMgr || !pikiMgr || !mapMgr)return result;
        if(!initialized)return result;
        if(phase==0 && (n->getCurrState()->getID()!=NAVISTATE_Walk || ++ready<45))return result;
        require(flowCont.mCurrentStage && !std::strcmp(flowCont.mCurrentStage->mFileName,"stages/p2_tutorial.ini"),"wrong loaded stage");
        require(!gameflow.mIsChallengeMode && !pc_pikipelago_room_preview(),"wrong lifecycle");
        int count=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p->isAlive())++count;}
        if(!humanSmoke() || phase==0)require(count==20,"live starting squad");
        require(mapMgr->mMapModel->mTriCount==5332,"complete source face count");
        require(mapMgr->mMapModel->mTriList[673].mMapCode!=mapMgr->mMapModel->mTriList[4914].mMapCode,"duplicate slip overlay collapsed");
        for(int flag=0;flag<DEMOFLAG_COUNT;++flag)playerState->mDemoFlags.setFlagOnly(flag);
        if(gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
        if(phase==0){
            require(pc_p2_surface_water_active() && pc_p2_surface_water_count()==3,"source water not active");
            std::printf("P2_SURFACE_WATER_START navi=%.3f,%.3f,%.3f wet=%d box=%d ground=%.3f\n",n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,int(n->mIsInWater),pc_p2_surface_water_box(n->mSRT.t,n->mCollisionRadius),mapMgr->getMinY(n->mSRT.t.x,n->mSRT.t.z,true));std::fflush(stdout);
            require(!n->mIsInWater,"dry shoreline start");
            require(std::fabs(n->mSRT.t.x-220)<5 && std::fabs(n->mSRT.t.z-1000)<5,"actual shoreline generator entry");
            std::printf("P2_SURFACE_WATER_SETTINGS blues_only_water=%d piki_invincible=%d species_probe=%d\n",pc_settings_get_blues_only_water(),pc_settings_get_piki_invincible(),int(speciesProbe()));
            if(speciesProbe()){
                require(!pc_settings_get_blues_only_water() && !pc_settings_get_piki_invincible(),"hazard mod changes baseline");
                int blues=0, shorelineReds=0;Iterator roster(pikiMgr);CI_LOOP(roster){Piki* p=static_cast<Piki*>(*roster);if(p->mColor==Blue){probeBlue=p;++blues;}else if(p->mColor==Red && p->mGenerator && std::fabs(p->mGenerator->mGenPosition.x-220)<0.01f){probeRed=p;++shorelineReds;}}
                std::printf("P2_SURFACE_WATER_PROBE_ROSTER blues=%d shoreline_reds=%d\n",blues,shorelineReds);std::fflush(stdout);
                require(blues==1 && shorelineReds==1 && probeRed && probeBlue,"disclosed species probe roster");
                std::printf("P2_SURFACE_WATER_PROBE_IDENTITIES red_generator=%u red_source=%.2f,%.2f,%.2f red_current=%.2f,%.2f,%.2f blue_generator=%u blue_current=%.2f,%.2f,%.2f\n",probeRed->getGeneratorID(),probeRed->mGenerator->mGenPosition.x,probeRed->mGenerator->mGenPosition.y,probeRed->mGenerator->mGenPosition.z,probeRed->mSRT.t.x,probeRed->mSRT.t.y,probeRed->mSRT.t.z,probeBlue->getGeneratorID(),probeBlue->mSRT.t.x,probeBlue->mSRT.t.y,probeBlue->mSRT.t.z);std::fflush(stdout);
            }
            require(std::fabs(mapMgr->getMinY(220,1000,true)-56.0442f)<0.1f,"retail shoreline starting floor");
            require(pc_p2_surface_water_box(Vector3f(0,148.63f,1000),0)==-1,"upper bridge incorrectly wet");
            require(pc_p2_surface_water_box(Vector3f(0,15,1000),0)==0,"lower pool probe missing");
            require(pc_p2_surface_water_box(Vector3f(-1000,67,-300),0)==1,"source volume1 query missing");
            require(pc_p2_surface_water_box(Vector3f(0,37,1600),0)==2,"source volume2 query missing");
            auto* shape=mapMgr->mMapModel;
            auto centroid=[&](int face){Vector3f p;for(int i=0;i<3;++i)p.add(shape->mVertexList[shape->mTriList[face].mVertexIndices[i]]);p.multiply(1.f/3.f);return p;};
            auto unique=pc_p2_surface_continuation(shape,&shape->mTriList[320],1,centroid(4296));
            auto ambiguous=pc_p2_surface_continuation(shape,&shape->mTriList[551],1,centroid(727));
            require(unique.kind==p2surface::Kind::Unique&&unique.face==4296,"retail unique crossing");
            require(ambiguous.kind==p2surface::Kind::Ambiguous&&ambiguous.face==-1,"retail slip ambiguity invented neighbor");
            std::puts("P2_SURFACE_RETAIL_POLICY_PASS unique320_to4296=1 ambiguous551_to727_or4915=1 duplicate_slip_preserved=1");
            origin=n->mSRT.t;phase=humanSmoke()?4:1;ready=0;
            if(humanSmoke()){std::puts("READY P2_SURFACE_WATER_HUMAN_SMOKE faces=5332 live=20 native_input=1 mechanic=static_water_shoreline complete_gameplay=0");std::fflush(stdout);}
            if(humanSmoke() && std::getenv("P2_SURFACE_WATER_HUMAN_AUTO_STARTUP")){std::puts("PASS P2_SURFACE_WATER_HUMAN_AUTO_STARTUP live=20 manual_judgment=0");std::fflush(nullptr);std::_Exit(0);}
        } else if(phase==1&&++settle>=60){phase=2;settle=0;}
        else if(phase==2){
            if(n->mIsInWater && pc_p2_surface_water_box(n->mSRT.t,n->mCollisionRadius)==0)entered=true;
            float dx=goal.x-n->mSRT.t.x,dz=goal.z-n->mSRT.t.z;
            if(dx*dx+dz*dz<144){require(entered,"ordinary controller never entered water");phase=speciesProbe()?6:3;settle=0;goal=origin;}
        } else if(phase==6){
            require(probeRed->isAlive() && probeBlue->isAlive(),"species probe died before observation");
            if(probeRed->mInWaterTimer>0 && probeRed->getState()==PIKISTATE_Drown)redDrown=true;
            if(probeBlue->mInWaterTimer>0){require(probeBlue->getState()!=PIKISTATE_Drown,"Blue entered drown state");blueWet=true;}
            if(tick%30==0)std::printf("P2_SURFACE_WATER_SPECIES red_timer=%d red_state=%d blue_timer=%d blue_state=%d red=%.2f,%.2f,%.2f blue=%.2f,%.2f,%.2f\n",probeRed->mInWaterTimer,probeRed->getState(),probeBlue->mInWaterTimer,probeBlue->getState(),probeRed->mSRT.t.x,probeRed->mSRT.t.y,probeRed->mSRT.t.z,probeBlue->mSRT.t.x,probeBlue->mSRT.t.y,probeBlue->mSRT.t.z);
            if(redDrown && blueWet){
                WayPoint* wp=routeMgr?routeMgr->findNearestWayPoint('test',probeBlue->mSRT.t,true):nullptr;
                require(wp!=nullptr,"no dry source rescue waypoint");
                require(pc_p2_surface_water_box(wp->mPosition,0)<0,"selected rescue waypoint still submerged");
                std::printf("P2_BLUE_RESCUE_DRY_WAYPOINT index=%d source=%.2f,%.2f,%.2f radius=%.2f source_volume_wet=0\n",wp->mIndex,wp->mPosition.x,wp->mPosition.y,wp->mPosition.z,wp->mRadius);
                phase=7;settle=0;std::puts("P2_BLUE_RESCUE_INPUT disband=mapped_button whistle_after_drown=0");
            }
            else require(++settle<180,"ordinary followers failed Red drown and Blue wet immunity observation");
        } else if(phase==7){
            require(probeRed->isAlive() && probeBlue->isAlive(),"rescue actors died");
            if(pc_blue_rescue_owned(probeRed,probeBlue) && probeRed->getState()==PIKISTATE_WaterHanged)held=true;
            if(held && probeRed->getState()==PIKISTATE_Flying)thrown=true;
            if(tick%15==0)std::printf("P2_BLUE_RESCUE_OBSERVE red_state=%d red_timer=%d blue_state=%d blue_action=%d owned=%d held=%d thrown=%d red=%.2f,%.2f,%.2f blue=%.2f,%.2f,%.2f\n",probeRed->getState(),probeRed->mInWaterTimer,probeBlue->getState(),probeBlue->mActiveAction?probeBlue->mActiveAction->mCurrActionIdx:-1,int(pc_blue_rescue_owned(probeRed,probeBlue)),int(held),int(thrown),probeRed->mSRT.t.x,probeRed->mSRT.t.y,probeRed->mSRT.t.z,probeBlue->mSRT.t.x,probeBlue->mSRT.t.y,probeBlue->mSRT.t.z);
            if(thrown && probeRed->getState()!=PIKISTATE_Flying && probeRed->getState()!=PIKISTATE_WaterHanged && probeRed->getState()!=PIKISTATE_Drown && probeRed->mInWaterTimer==0 && pc_p2_surface_water_box(probeRed->mSRT.t,probeRed->mCollisionRadius)<0){
                std::printf("PASS P2_BLUE_RESCUE_RUNTIME held=1 thrown=1 dry_landing=1 live=%d faces=5332 boxes=3 ordinary_input=1 staged_species=1 natural_acquisition=0 campaign=0\n",count);std::fflush(nullptr);std::_Exit(0);
            }
            require(++settle<900,"ordinary Blue rescue did not complete dry landing");
        }
        if(tick%60==0){std::printf("P2_SURFACE_WATER_FRAME tick=%d phase=%d live=%d navi=%.3f,%.3f,%.3f hp=%.3f wet=%d box=%d\n",tick,phase,count,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,n->mHealth,int(n->mIsInWater),pc_p2_surface_water_box(n->mSRT.t,n->mCollisionRadius));std::fflush(stdout);}
        return result;
    }
};
int main(int argc,char** argv) {
    SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,"1");SDL_setenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND",humanSmoke()?"2":"1",1);SDL_SetMainReady();pc_gpu_preference_apply();pc_bbft_init(argc,argv);
    require(pc_pikipelago_surface_course()!=nullptr,"surface flag required");
    if(!pc_window_init("Blue rescue source-water scenario",960,540))return 3;
    pc_settings_init();pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();
    SDL_Window* window=SDL_GL_GetCurrentWindow();int w,h,x,y;SDL_GetWindowSize(window,&w,&h);SDL_GetWindowPosition(window,&x,&y);
    SDL_Rect bounds{};SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window),&bounds);
    const bool automaticHuman=std::getenv("P2_SURFACE_WATER_HUMAN_AUTO_STARTUP")!=nullptr;
    if(!humanSmoke() || automaticHuman)SDL_HideWindow(window);else SDL_ShowWindow(window);
    std::printf("P2_SURFACE_WATER_WINDOW_VISIBILITY hidden=%d human=%d automatic_human_startup=%d\n",int((SDL_GetWindowFlags(window)&SDL_WINDOW_HIDDEN)!=0),int(humanSmoke()),int(automaticHuman));
    bool centered=std::abs(x-(bounds.x+(bounds.w-w)/2))<=2 && std::abs(y-(bounds.y+(bounds.h-h)/2))<=2;
    require(w==960 && h==540 && centered,"window baseline");
    std::printf("P2_SURFACE_WINDOW size=%dx%d centered=%d after_settings=1\n",w,h,int(centered));
    pc_window_set_control_mode(PC_CONTROL_CLASSIC);
    if(!humanSmoke()){
    int device=SDL_JoystickAttachVirtual(SDL_JOYSTICK_TYPE_GAMECONTROLLER,SDL_CONTROLLER_AXIS_MAX,SDL_CONTROLLER_BUTTON_MAX,0);require(device>=0,"virtual controller attach");
    char guid[64];SDL_JoystickGetGUIDString(SDL_JoystickGetDeviceGUID(device),guid,sizeof(guid));
    std::string mapping=std::string(guid)+",Surface travel virtual pad,a:b0,b:b1,x:b2,y:b3,back:b4,guide:b5,start:b6,leftstick:b7,rightstick:b8,leftshoulder:b9,rightshoulder:b10,dpup:b11,dpdown:b12,dpleft:b13,dpright:b14,leftx:a0,lefty:a1,rightx:a2,righty:a3,lefttrigger:a4,righttrigger:a5,";
    require(SDL_GameControllerAddMapping(mapping.c_str())>=0,"virtual controller mapping");pad=SDL_JoystickOpen(device);require(pad!=nullptr,"virtual controller open");
    pc_window_input_assign(0,PC_INPUT_DEV_GAMEPAD,SDL_JoystickInstanceID(pad));pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);
    } else {
        int device=-1;for(int i=0;i<SDL_NumJoysticks();++i)if(SDL_IsGameController(i)){device=i;break;}
        pc_window_input_assign(0,device>=0?PC_INPUT_DEV_GAMEPAD:PC_INPUT_DEV_KEYBOARD,device>=0?SDL_JoystickGetDeviceInstanceID(device):-1);
        pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);
    }
    pc_window_set_stick_invert(0);pc_window_set_cstick_invert(0);const int bindings[]={SDL_CONTROLLER_BUTTON_A,SDL_CONTROLLER_BUTTON_B,SDL_CONTROLLER_BUTTON_X,SDL_CONTROLLER_BUTTON_Y,SDL_CONTROLLER_BUTTON_RIGHTSHOULDER,SDL_CONTROLLER_BUTTON_LEFTSHOULDER,SDL_CONTROLLER_BUTTON_START};
    for(int i=0;i<7;++i)pc_window_set_gamepad_binding(i,bindings[i]);
    gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new WaterSurfaceApp());return 0;
}
