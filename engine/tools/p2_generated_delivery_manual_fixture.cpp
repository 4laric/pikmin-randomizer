// #1131 physical-input companion for the original admitted source44 AP case.
// Fresh TEST_BACKGROUND withdrawal/tutorial/movie setup is disclosed. No actor,
// health, attachment, route, check, reward or physical input writes.
#include <SDL2/SDL.h>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
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
#include "teki.h"
#include "GameStat.h"
#include "PlayerState.h"
#include "Demo.h"
#include "pc_randomizer.h"
#include "pc_p2_species.h"
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"

namespace {
constexpr unsigned Target=3921089765;
bool option(const char* name) { return std::getenv(name)!=nullptr; }
void require(bool ok,const char* reason) {
    if(ok)return;
    std::printf("FAIL P2_GENERATED_MANUAL %s\n",reason);
    std::fflush(nullptr);std::_Exit(1);
}
class ManualDeliveryApp final:public PlugPikiApp {
    bool initialized=false,ready=false;
    int frames=0;
    void guard() {
        Navi* n=naviMgr?naviMgr->getNavi():nullptr;
        if(n&&n->getCurrState())initialized=true;
        if(!initialized)return;
        const bool negative=option("P2_GENERATED_MANUAL_FORCE_CAPTAIN_DOWN");
        const bool missing=option("P2_GENERATED_MANUAL_FORCE_MISSING_CAPTAIN");
        const float hp=n?n->mHealth:0.f;
        const bool dead=missing || !n || !n->getCurrState() || naviMgr->isNaviDead(n)
            || n->getCurrState()->getID()==NAVISTATE_Dead;
        if(!negative&&!GameStat::orimaDead&&!dead&&std::isfinite(hp)&&hp>1.f)return;
        std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d initialized=1 hp=%.3f dead=%d outcome=BLOCKED\n",frames,hp,int(dead));
        std::fflush(nullptr);std::_Exit(86);
    }
public:
    int idle() override {
        guard();
        const int result=PlugPikiApp::idle();
        guard(); // Immediately after engine idle, before every readiness return.
        require(++frames<7200,"frame ceiling; external60-second supervisor required");
        if(SDL_GetKeyboardState(nullptr)[SDL_SCANCODE_F7] || std::ifstream("manual-reset.request").good()) {
            std::puts("P2_GENERATED_MANUAL_RESET_REQUEST fresh_session_required=1");
            std::fflush(nullptr);std::_Exit(90);
        }
        // Same disclosed startup instrumentation as the accepted scripted case.
        if(playerState)for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
        if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip();return result;
        }
        Navi* n=naviMgr?naviMgr->getNavi():nullptr;
        if(gameflow.mPauseAll||gameflow.mIsUIOverlayActive||!pc_randomizer_ready()
            ||!n||!n->getCurrState()||!pikiMgr||!tekiMgr)return result;
        if(n->getCurrState()->getID()==NAVISTATE_Starting)return result;
        if(!ready) {
            int alive=0,red=0;Iterator bodies(pikiMgr);CI_LOOP(bodies) {
                Piki* p=static_cast<Piki*>(*bodies);if(!p||!p->isAlive())continue;
                ++alive;if(pc_p2_species(p)==P2SpeciesRed)++red;
            }
            if(alive<20)return result; // Native Onion exits are spread over ticks.
            require(alive==20&&red==20,"fresh20 native Reds required");
            int targets=0;Iterator enemies(tekiMgr);CI_LOOP(enemies) {
                Teki* t=static_cast<Teki*>(*enemies);
                const auto* view=static_cast<PelletView*>(t);
                if(pc_randomizer_p2_source_for(view)==44&&pc_randomizer_p2_generator_for(view)==Target) {
                    ++targets;require(t->isAlive(),"original target must start alive");
                }
            }
            require(targets==1,"original source44 singleton required");
            require(gameflow.mWorldClock.mCurrentDay==2,"fresh initial day required");
            require(!pc_randomizer_checked("P2:44"),"fresh session must not start credited");
            int width,height,x,y;SDL_Window* window=SDL_GL_GetCurrentWindow();
            require(window,"current window required");SDL_GetWindowSize(window,&width,&height);SDL_GetWindowPosition(window,&x,&y);
            SDL_Rect bounds{};require(SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window),&bounds)==0,"display bounds");
            require(width==960&&height==540&&std::abs(x+width/2-bounds.x-bounds.w/2)<=2
                &&std::abs(y+height/2-bounds.y-bounds.h/2)<=2,"centered960x540 startup");
            ready=true;
            std::puts("P2_GENERATED_MANUAL_READY source=44 original_uid=3921089765 live=20 red_id=1 centered=1 physical_input=1 scripted_input=0 actor_writes=0");
            std::fflush(nullptr);
            if(option("P2_GENERATED_MANUAL_READY_ONLY"))std::_Exit(0);
        }
        if(ready&&pc_randomizer_checked("P2:44")) {
            std::puts("PASS P2_GENERATED_MANUAL_DELIVERY actual_native_check=1 physical_input=1 direct_event_writes=0");
            std::fflush(nullptr);std::_Exit(0);
        }
        return result;
    }
};
}
int main(int argc,char** argv) {
    SDL_SetMainReady();pc_gpu_preference_apply();
    // Exact1 hides automated ready/guard tests;2 keeps human startup visible.
    SDL_setenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND",option("P2_GENERATED_MANUAL_READY_ONLY")
        ||option("P2_GENERATED_MANUAL_FORCE_CAPTAIN_DOWN")||option("P2_GENERATED_MANUAL_FORCE_MISSING_CAPTAIN")?"1":"2",1);
    pc_bbft_init(argc,argv);require(pc_randomizer_enabled()&&pc_randomizer_p2_bridge(),"generated P2 full-session bootstrap required");
    if(!pc_window_init("P2 enemy gameplay smoke - F7 restarts",960,540))return 3;
    pc_settings_init();pc_window_set_control_mode(PC_CONTROL_CLASSIC);pc_window_set_display_mode(0);
    pc_window_set_window_size(960,540);pc_window_center();
    int device=-1;for(int i=0;i<SDL_NumJoysticks();++i)if(!SDL_JoystickIsVirtual(i)&&SDL_IsGameController(i)){device=i;break;}
    pc_window_input_assign(0,device>=0?PC_INPUT_DEV_GAMEPAD:PC_INPUT_DEV_KEYBOARD,
        device>=0?SDL_JoystickGetDeviceInstanceID(device):-1);
    pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);
    std::puts("P2_GENERATED_MANUAL_SCOPE fresh20_native_withdrawal=1 movie_tutorial_setup=1 physical_controls=1 scripted_input=0 timeout_external=60");
    gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new ManualDeliveryApp());return 0;
}
