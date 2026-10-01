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
#include "PikiMgr.h"
#include "MapMgr.h"
#include "Collision.h"
#include "PlayerState.h"
#include "GameStat.h"
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_p2_surface_topology.h"
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
static bool humanSmoke(){return std::getenv("P2_FULL_SURFACE_HUMAN_SMOKE")!=nullptr;}
static SDL_Joystick* pad=nullptr;
static int phase=0;
static Vector3f goal(-190,80,1000);
class FullSurfaceApp: public PlugPikiApp {
    int tick=0, ready=0, settle=0;
    Vector3f origin;
    bool captainInitialized=false;
public:
    int idle() override {
        if(pad){
            Navi* before=naviMgr?naviMgr->getNavi():nullptr;
            int sx=0,sy=0;
            if(phase==2&&before&&before->mNaviCamera){float dx=goal.x-before->mSRT.t.x,dz=goal.z-before->mSRT.t.z,d=std::sqrt(dx*dx+dz*dz);if(d>10){const Vector3f& axis=before->mNaviCamera->mViewXAxis;sx=int(65*(dx*axis.x+dz*axis.z)/d);sy=int(65*(dx*axis.z-dz*axis.x)/d);}}
            SDL_JoystickSetVirtualButton(pad,SDL_CONTROLLER_BUTTON_B,phase==1);
            SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_LEFTX,Sint16(sx*32767/74));
            SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_LEFTY,Sint16(-sy*32767/74));SDL_JoystickUpdate();
        }
        int result=PlugPikiApp::idle();
        // Canonical guard boundary: inspect immediately after engine idle,
        // including movie/pause/startup frames, before any readiness return.
        Navi* n=naviMgr?naviMgr->getNavi():nullptr;
        const bool initialized=n && n->getCurrState();
        if(initialized)captainInitialized=true;
        const bool forced=std::getenv("P2_FULL_SURFACE_FORCE_CAPTAIN_DOWN") != nullptr;
        const bool pauseNegative=std::getenv("P2_FULL_SURFACE_FORCE_PAUSED_CAPTAIN_DOWN") != nullptr;
        if(initialized && pauseNegative)gameflow.mPauseAll=true; // negative observer only
        if((captainInitialized && !initialized) || (initialized &&
            (GameStat::orimaDead || naviMgr->isNaviDead(n) || n->getCurrState()->getID()==NAVISTATE_Dead
             || !std::isfinite(n->mHealth) || n->mHealth<=1.0f || forced || pauseNegative))) {
            std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f initialized=%d movie=%d pause=%d outcome=BLOCKED\n",
                tick,n?n->mHealth:0.0f,int(initialized),int(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive),int(gameflow.mPauseAll));
            std::fflush(nullptr);std::_Exit(86);
        }
        ++tick; if(!humanSmoke())require(tick<2400,"frame timeout");
        if(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
        if(!naviMgr || !pikiMgr || !mapMgr)return result;
        if(!initialized)return result;
        if(phase==0 && (n->getCurrState()->getID()!=NAVISTATE_Walk || ++ready<45))return result;
        require(flowCont.mCurrentStage && !std::strcmp(flowCont.mCurrentStage->mFileName,"stages/p2_tutorial.ini"),"wrong loaded stage");
        require(!gameflow.mIsChallengeMode && !pc_pikipelago_room_preview(),"wrong lifecycle");
        int count=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p->isAlive())++count;}
        require(count==20,"live starting squad");
        require(mapMgr->mMapModel->mTriCount==5332,"complete source face count");
        require(mapMgr->mMapModel->mTriList[673].mMapCode!=mapMgr->mMapModel->mTriList[4914].mMapCode,"duplicate slip overlay collapsed");
        for(int flag=0;flag<DEMOFLAG_COUNT;++flag)playerState->mDemoFlags.setFlagOnly(flag);
        if(gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
        if(phase==0){
            require(std::fabs(mapMgr->getMinY(-190,1160,true)-80)<0.05f,"retail starting floor");
            auto* shape=mapMgr->mMapModel;
            auto centroid=[&](int face){Vector3f p;for(int i=0;i<3;++i)p.add(shape->mVertexList[shape->mTriList[face].mVertexIndices[i]]);p.multiply(1.f/3.f);return p;};
            auto unique=pc_p2_surface_continuation(shape,&shape->mTriList[320],1,centroid(4296));
            auto ambiguous=pc_p2_surface_continuation(shape,&shape->mTriList[551],1,centroid(727));
            require(unique.kind==p2surface::Kind::Unique&&unique.face==4296,"retail unique crossing");
            require(ambiguous.kind==p2surface::Kind::Ambiguous&&ambiguous.face==-1,"retail slip ambiguity invented neighbor");
            std::puts("P2_SURFACE_RETAIL_POLICY_PASS unique320_to4296=1 ambiguous551_to727_or4915=1 duplicate_slip_preserved=1");
            origin=n->mSRT.t;phase=humanSmoke()?4:1;ready=0;
            if(humanSmoke()){std::puts("READY P2_FULL_SURFACE_HUMAN_SMOKE faces=5332 live=20 native_input=1 mechanic=dry_terrain_traversal complete_gameplay=0");std::fflush(stdout);}
        } else if(phase==1&&++settle>=60){phase=2;settle=0;}
        else if(phase==2){float dx=goal.x-n->mSRT.t.x,dz=goal.z-n->mSRT.t.z;if(dx*dx+dz*dz<144){phase=3;settle=0;}}
        else if(phase==3&&++settle>=90){
            float dx=n->mSRT.t.x-origin.x,dz=n->mSRT.t.z-origin.z;
            require(dx*dx+dz*dz>120*120,"controller did not leave original60unit pocket");
            require(std::isfinite(n->mSRT.t.y)&&n->mSRT.t.y>70,"captain fell through full terrain");
            std::printf("PASS P2_FULL_SURFACE_RUNTIME faces=5332 live=%d native_controller=1 distance=%.3f x=%.3f y=%.3f z=%.3f ambiguous_queries=%u complete_gameplay=0\n",count,std::sqrt(dx*dx+dz*dz),n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,pc_p2_surface_ambiguous_queries());
            std::fflush(nullptr);std::_Exit(0);
        }
        if(tick%60==0){std::printf("P2_FULL_SURFACE_FRAME tick=%d phase=%d live=%d navi=%.3f,%.3f,%.3f hp=%.3f\n",tick,phase,count,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,n->mHealth);std::fflush(stdout);}
        return result;
    }
};
int main(int argc,char** argv) {
    SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,"1");_putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");SDL_SetMainReady();pc_gpu_preference_apply();pc_bbft_init(argc,argv);
    require(pc_pikipelago_surface_course()!=nullptr,"surface flag required");
    if(!pc_window_init("P2 complete tutorial terrain",960,540))return 3;
    pc_settings_init();pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();
    SDL_Window* window=SDL_GL_GetCurrentWindow();int w,h,x,y;SDL_GetWindowSize(window,&w,&h);SDL_GetWindowPosition(window,&x,&y);
    SDL_Rect bounds{};SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window),&bounds);
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
    pc_window_set_stick_invert(0);pc_window_set_cstick_invert(0);pc_window_set_gamepad_binding(PC_KEY_ACT_B,SDL_CONTROLLER_BUTTON_B);
    gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new FullSurfaceApp());return 0;
}
