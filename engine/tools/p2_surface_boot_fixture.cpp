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
#include "Piki.h"
#include "PikiMgr.h"
#include "MapMgr.h"
#include "Collision.h"
#include "PlayerState.h"
#include "GameStat.h"
#include "pc_window.h"
#include "pc_bbft.h"
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
class SurfaceBootApp: public PlugPikiApp {
    int tick=0, ready=0;
    bool captainInitialized=false;
public:
    int idle() override {
        int result=PlugPikiApp::idle();
        // Canonical guard boundary: inspect immediately after engine idle,
        // including movie/pause/startup frames, before any readiness return.
        Navi* n=naviMgr?naviMgr->getNavi():nullptr;
        const bool initialized=n && n->getCurrState();
        if(initialized)captainInitialized=true;
        const bool forced=std::getenv("P2_SURFACE_FORCE_CAPTAIN_DOWN") != nullptr;
        const bool pauseNegative=std::getenv("P2_SURFACE_FORCE_PAUSED_CAPTAIN_DOWN") != nullptr;
        if(initialized && pauseNegative)gameflow.mPauseAll=true; // negative observer only
        if((captainInitialized && !initialized) || (initialized &&
            (GameStat::orimaDead || naviMgr->isNaviDead(n) || n->getCurrState()->getID()==NAVISTATE_Dead
             || !std::isfinite(n->mHealth) || n->mHealth<=1.0f || forced || pauseNegative))) {
            std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f initialized=%d movie=%d pause=%d outcome=BLOCKED\n",
                tick,n?n->mHealth:0.0f,int(initialized),int(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive),int(gameflow.mPauseAll));
            std::fflush(nullptr);std::_Exit(86);
        }
        require(++tick<2400,"frame timeout");
        if(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
        if(!naviMgr || !pikiMgr || !mapMgr)return result;
        if(!initialized)return result;
        if(n->getCurrState()->getID()!=NAVISTATE_Walk || ++ready<45)return result;
        require(flowCont.mCurrentStage && !std::strcmp(flowCont.mCurrentStage->mFileName,"stages/p2_tutorial.ini"),"wrong loaded stage");
        require(!gameflow.mIsChallengeMode && !pc_pikipelago_room_preview(),"wrong lifecycle");
        int count=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p->isAlive())++count;}
        require(count==20,"live starting squad");
        require(std::fabs(mapMgr->getMinY(-190,1160,true)-80)<0.05f,"retail source floor");
        Vector3f pos(-190,86,1160),velocity(40,0,0);
        for(int i=0;i<30;++i){MoveTrace trace(pos,velocity,6,true);mapMgr->traceMove(n,trace,1.f/60.f);pos=trace.mPosition;}
        require(std::isfinite(pos.x) && pos.x>-185 && pos.x<-150 && std::fabs(pos.y-86)<2,"source floor traversal trace");
        std::printf("PASS P2_SURFACE_BOOT_RUNTIME course=tutorial live=%d ground=80 trace_x=%.3f bounded=1 full_course=0\n",count,pos.x);
        std::fflush(nullptr);std::_Exit(0);
        return result;
    }
};
int main(int argc,char** argv) {
    SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();pc_gpu_preference_apply();pc_bbft_init(argc,argv);
    require(pc_pikipelago_surface_course()!=nullptr,"surface flag required");
    if(!pc_window_init("P2 bounded tutorial surface boot",960,540))return 3;
    pc_settings_init();pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();
    SDL_Window* window=SDL_GL_GetCurrentWindow();int w,h,x,y;SDL_GetWindowSize(window,&w,&h);SDL_GetWindowPosition(window,&x,&y);
    SDL_Rect bounds{};SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window),&bounds);
    bool centered=std::abs(x-(bounds.x+(bounds.w-w)/2))<=2 && std::abs(y-(bounds.y+(bounds.h-h)/2))<=2;
    require(w==960 && h==540 && centered,"window baseline");
    std::printf("P2_SURFACE_WINDOW size=%dx%d centered=%d after_settings=1\n",w,h,int(centered));
    gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new SurfaceBootApp());return 0;
}
