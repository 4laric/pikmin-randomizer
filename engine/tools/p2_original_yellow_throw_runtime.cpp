// Staged original RGB trajectory test. No original acquisition/campaign claim.
// After the one disclosed setup replacement, only controller input moves actors.
#include <SDL2/SDL.h>
#include "system.h"
#include "App.h"
#include "Node.h"
#include "FlowController.h"
#include "MoviePlayer.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "GameStat.h"
#include "pc_bbft.h"
#include "pc_window.h"
#include "pc_gpu_preference.h"
#include "pc_p2_species.h"
#include "pc_p2_original_throw.h"
#include "pc_p2_original_piki_physical.h"
#include "pc_p2_original_piki_recruit.h"
#include "pc_p2_original_progress.h"
#include "pc_p2_original_source_uid.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "Camera.h"
#include "KeyConfig.h"
#include "Kontroller.h"
#include "AIConstant.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <string>
namespace {
SDL_Joystick* pad=nullptr;
int phase=0,inputTick=0;
Piki* yellow=nullptr;
bool held=false,released=false,flying=false;
float peak=0,startY=0,expectedPeak=0;
void require(bool condition,const char* message){if(!condition){std::printf("FAIL ORIGINAL_YELLOW_THROW %s\n",message);std::fflush(nullptr);std::_Exit(1);}}
void input(unsigned keys=0){
    pc_window_input_assign(0,PC_INPUT_DEV_GAMEPAD,SDL_JoystickInstanceID(pad));
    pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);
    for(int b=0;b<SDL_CONTROLLER_BUTTON_MAX;++b)SDL_JoystickSetVirtualButton(pad,b,0);
    SDL_JoystickSetVirtualButton(pad,SDL_CONTROLLER_BUTTON_A,bool(keys&KBBTN_A));
    SDL_JoystickSetVirtualButton(pad,SDL_CONTROLLER_BUTTON_B,bool(keys&KBBTN_B));
    SDL_JoystickSetVirtualButton(pad,SDL_CONTROLLER_BUTTON_DPAD_RIGHT,bool(keys&KBBTN_DPAD_RIGHT));
    SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_LEFTX,0);
    SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_LEFTY,0);
    SDL_JoystickUpdate();
}
int live(){int n=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p&&p->isAlive())++n;}return n;}
void stage(Navi* captain){
    require(live()==20,"starting squad20");
    Iterator it(pikiMgr);it.first();auto* replace=static_cast<Piki*>(*it);
    replace->setEraseKill();replace->kill(false);
    // Verified tutorial debug Yellow source row count20. This one member is
    // placed beside the captain for a mechanic fixture, not a source spawn.
    const std::string key="tutorial/initgen.txt#2";
    const std::string fingerprint="b8a4fb5a39f8371a879eec4ece9025bee75977a4b4394111d5825e6ec79c0bbf";
    const unsigned uid=p2original::originalSourceCatalogUid(key);
    std::string error;
    require(pc_p2_original_piki_origin_install(fingerprint,{{key,uid,20,2}},error),"scoped fixture catalog");
    const std::string campaign="7e98c5bed07d3b4c39c3a3a0765b129bf2f90e22d652b1bb3bbe514b932c1bad";
    require(p2original::originalProgress().initialize(campaign,error),"scoped fixture progress");
    // This placed debug member is outside original story/day-zero acquisition.
    auto context=p2original::originalProgress().context();context.story=false;
    require(p2original::originalProgress().restoreContext(context,error),"disclosed non-story fixture context");
    require(pc_p2_original_piki_recruit_bind(campaign,fingerprint,error),"paired fixture recruitment");
    OriginalPikiBody body{{key,uid,0,1,fingerprint},{2,false,false}};
    const auto& pos=captain->mSRT.t;
    require(pc_p2_original_piki_physical_birth(body,{{pos.x+12,pos.y,pos.z}},yellow,error)==p2original::PikiBirthResult::Born,"disclosed staged Yellow birth");
    require(live()==20&&pc_p2_original_rgb_throw_species(yellow)==2,"exact Yellow authority/population");
    std::puts("ORIGINAL_YELLOW_THROW_STAGED live=20 reds=19 yellow=1 catalog_fixture=1 relocated_debug_member=1 non_story_fixture=1 acquisition=0 campaign=0");
    std::fflush(nullptr);
}
class ThrowApp:public PlugPikiApp {
    int tick=0,ready=0;
    bool captainSeen=false;
public:int idle()override {
    if(phase==1)input(KBBTN_B);
    else if(phase==2)input(KBBTN_A|((inputTick%8==0)?KBBTN_DPAD_RIGHT:0));
    else input();
    ++inputTick;
    int result=PlugPikiApp::idle();
    Navi* captain=naviMgr?naviMgr->getActiveNavi():nullptr;
    const bool initialized=captain&&captain->getCurrState();
    if(initialized)captainSeen=true;
    if((captainSeen&&!initialized)||(initialized&&(GameStat::orimaDead||naviMgr->isNaviDead(captain)
        || captain->getCurrState()->getID()==NAVISTATE_Dead||!std::isfinite(captain->mHealth)||captain->mHealth<=1
        ||std::getenv("P2_YELLOW_FORCE_CAPTAIN_DOWN")))){
        std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d\n",tick);std::fflush(nullptr);std::_Exit(86);
    }
    require(++tick<1500,"bounded trajectory observation");
    if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
    if(!initialized||!pikiMgr||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
    if(phase==0){
        if(captain->getCurrState()->getID()!=NAVISTATE_Walk||++ready<45)return result;
        stage(captain);phase=1;inputTick=0;return result;
    }
    require(live()==20&&yellow&&yellow->isAlive(),"live squad/Yellow");
    // Release whistle and let Gather return to Walk before the A click.
    // Holding A across the Gather exit loses the ordinary throw press edge.
    if(phase==1&&inputTick>=90){phase=4;inputTick=0;}
    if(phase==4&&inputTick>=15&&captain->getCurrState()->getID()==NAVISTATE_Walk){phase=2;inputTick=0;}
    if(phase==2&&yellow->getState()==PIKISTATE_Hanged){
        held=true;startY=captain->mSRT.t.y+10.0f;peak=startY;
        std::printf("ORIGINAL_YELLOW_THROW_HELD tick=%d species=%d start_y=%.3f\n",tick,pc_p2_species(yellow),startY);
        phase=3;inputTick=0;
    }
    if(phase==3){
        released=true;
        if(yellow->getState()==PIKISTATE_Flying){
            if(!flying){
                p2throw::Velocity expected;
                const float gravity=AICONST.mGravity();
                require(pc_p2_original_rgb_throw_species(yellow)==2,"canonical Yellow at flight");
                require(p2throw::rgbVelocity(2,0,gravity,expected),"finite source flight parameters");
                // The observer runs after idle. Permit up to three simulation
                // gravity steps, but reject legacy Yellow200's larger impulse.
                const float elapsedAllowance=3.0f*gravity*gsys->getFrameTime()+1.0f;
                require(yellow->mVelocity.y<=expected.vertical+1.0f
                    &&yellow->mVelocity.y>=expected.vertical-elapsedAllowance,"actual source Yellow impulse");
                expectedPeak=expected.vertical*expected.vertical/(2.0f*gravity);
                std::printf("ORIGINAL_YELLOW_THROW_FLIGHT tick=%d y=%.3f vy=%.3f source_species=2 expected_vy=%.3f expected_peak=%.3f\n",tick,yellow->mSRT.t.y,yellow->mVelocity.y,expected.vertical,expectedPeak);
            }
            flying=true;peak=std::fmax(peak,yellow->mSRT.t.y);
        } else if(flying&&yellow->getState()!=PIKISTATE_Hanged&&yellow->getState()!=PIKISTATE_Drown
            &&yellow->isCreatureFlag(CF_IsOnGround)){
            std::printf("ORIGINAL_YELLOW_THROW_LANDING tick=%d state=%d pos=%.3f,%.3f,%.3f velocity=%.3f,%.3f,%.3f peak_delta=%.3f captain=%.3f,%.3f,%.3f cursor=%.3f,%.3f,%.3f\n",tick,yellow->getState(),yellow->mSRT.t.x,yellow->mSRT.t.y,yellow->mSRT.t.z,yellow->mVelocity.x,yellow->mVelocity.y,yellow->mVelocity.z,peak-startY,captain->mSRT.t.x,captain->mSRT.t.y,captain->mSRT.t.z,captain->mCursorWorldPos.x,captain->mCursorWorldPos.y,captain->mCursorWorldPos.z);std::fflush(nullptr);
            require(held&&released&&peak>startY,"actual rising arc");
            require(std::fabs(peak-startY-expectedPeak)<expectedPeak*0.2f,"source apex band");
            std::printf("PASS ORIGINAL_YELLOW_THROW held=1 released=1 flying=1 landed=1 peak_delta=%.3f live=20 ordinary_input=1 staged_body=1 acquisition=0 campaign=0\n",peak-startY);
            std::fflush(nullptr);std::_Exit(0);
        }
    }
    if(tick%60==0){std::printf("ORIGINAL_YELLOW_THROW_PROGRESS tick=%d phase=%d state=%d mode=%d navi=%p y=%.3f peak=%.3f captain_state=%d buttons=%08x pressed=%08x next=%p\n",tick,phase,yellow->getState(),yellow->mMode,static_cast<void*>(yellow->mNavi),yellow->mSRT.t.y,peak,captain->getCurrState()->getID(),captain->mKontroller->mCurrentInput,captain->mKontroller->mInputPressed,static_cast<void*>(captain->mNextThrowPiki));std::fflush(nullptr);}
    return result;
}
};
}
int main(int argc,char**argv){
    SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_setenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1",1);SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,"1");SDL_SetMainReady();
    pc_gpu_preference_apply();pc_bbft_init(argc,argv);
    require(pc_pikipelago_surface_course()!=nullptr,"private surface fixture required");
    if(!pc_window_init("Original Yellow trajectory",960,540))return 3;
    pc_settings_init();pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();
    SDL_Window* window=SDL_GL_GetCurrentWindow();int w,h,x,y;SDL_GetWindowSize(window,&w,&h);SDL_GetWindowPosition(window,&x,&y);
    SDL_Rect bounds{};SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window),&bounds);
    require(w==960&&h==540&&std::abs(x-(bounds.x+(bounds.w-w)/2))<=2&&std::abs(y-(bounds.y+(bounds.h-h)/2))<=2,"centered960x540");
    std::puts("ORIGINAL_YELLOW_WINDOW size=960x540 centered=1");SDL_HideWindow(window);
    pc_window_set_control_mode(PC_CONTROL_CLASSIC);
    int device=SDL_JoystickAttachVirtual(SDL_JOYSTICK_TYPE_GAMECONTROLLER,SDL_CONTROLLER_AXIS_MAX,SDL_CONTROLLER_BUTTON_MAX,0);require(device>=0,"virtual pad");
    char guid[64];SDL_JoystickGetGUIDString(SDL_JoystickGetDeviceGUID(device),guid,sizeof(guid));
    std::string mapping=std::string(guid)+",Yellow trajectory pad,a:b0,b:b1,x:b2,y:b3,start:b6,dpleft:b13,dpright:b14,leftx:a0,lefty:a1,";
    require(SDL_GameControllerAddMapping(mapping.c_str())>=0,"pad mapping");pad=SDL_JoystickOpen(device);require(pad!=nullptr,"pad open");
    pc_window_input_assign(0,PC_INPUT_DEV_GAMEPAD,SDL_JoystickInstanceID(pad));pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);
    const int bindings[]={SDL_CONTROLLER_BUTTON_A,SDL_CONTROLLER_BUTTON_B,SDL_CONTROLLER_BUTTON_X,SDL_CONTROLLER_BUTTON_Y,SDL_CONTROLLER_BUTTON_RIGHTSHOULDER,SDL_CONTROLLER_BUTTON_LEFTSHOULDER,SDL_CONTROLLER_BUTTON_START};
    for(int i=0;i<7;++i)pc_window_set_gamepad_binding(i,bindings[i]);
    pc_window_set_gamepad_binding(PC_KEY_ACT_DPAD_RIGHT,SDL_CONTROLLER_BUTTON_DPAD_RIGHT);
    gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new ThrowApp());return 0;
}
