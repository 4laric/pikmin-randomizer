// Real-engine Progg ambush and native AI regression; isolated test main only.
#include <SDL2/SDL.h>
#include "system.h"
#include "App.h"
#include "Node.h"
#include "Section.h"
#include "FlowController.h"
#include "MoviePlayer.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "CPlate.h"
#include "pc_whistle.h"
#include <cmath>
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cstdio>
#include <cstdlib>


#include "ItemMgr.h"
#include "MizuItem.h"
#include "pc_randomizer.h"
#include <set>
#include "teki.h"
#include "TAI/Dororo.h"
#include "PlayerState.h"
#include "Demo.h"
#include <algorithm>
#include "Boss.h"
#include "Pom.h"
#include "Mizu.h"
#include <vector>
class ProggApp : public PlugPikiApp {
    int frames=0, phase=0, paused=0;
    float remaining=0;
    struct Original { Boss* boss; bool alive, atari; };
    std::vector<Original> originals;
    void require(bool ok,const char* why) { if(!ok) { std::printf("FAIL prerelease: %s\n",why); std::fflush(stdout); std::_Exit(1); } }
public:
    int idle() override {
        int result=PlugPikiApp::idle(); require(++frames<7000,"timeout");
        if(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) { gameflow.mMoviePlayer->requestSkip(); return result; }
        if(!bossMgr || !naviMgr || !pc_randomizer_ready()) return result;
        Navi* navi=naviMgr->getNavi(); if(!navi || !navi->getCurrState()) return result;
        navi->mHealth=C_NAVI_PARM(navi,mHealth);
        if(phase==0) {
            if(gameflow.mPauseAll || gameflow.mIsUIOverlayActive || navi->getCurrState()->getID()!=NAVISTATE_Walk) return result;
            for(int flag=0;flag<DEMOFLAG_COUNT;++flag) playerState->mDemoFlags.setFlagOnly(flag);
            Iterator iter(bossMgr); CI_LOOP(iter) { Boss* b=static_cast<Boss*>(*iter); if(dynamic_cast<Pom*>(b) || dynamic_cast<Mizu*>(b)) originals.push_back({b,b->isAlive(),b->isAtari()}); }
            require(!originals.empty(),"no fixtures");
            gameflow.mPauseAll=true; phase=1; std::puts("PRERELEASE_PAUSED_READY"); std::fflush(stdout);
        } else if(phase==1) {
            require(bossMgr->prereleaseSeconds()==0,"triggered while paused");
            if(pc_randomizer_benefit_pending(PC_BENEFIT_PRERELEASE) && ++paused>30) { gameflow.mPauseAll=false; phase=2; }
        } else if(phase==2 && bossMgr->prereleaseSeconds()>0) {
            originals.erase(std::remove_if(originals.begin(),originals.end(),[](const Original& o) { return o.boss->isAlive() || o.boss->isAtari(); }),originals.end()); require(!originals.empty(),"no parked fixtures");
            remaining=bossMgr->prereleaseSeconds(); gameflow.mPauseAll=true; paused=0; phase=3;
        } else if(phase==3) {
            require(bossMgr->prereleaseSeconds()==remaining,"timer advanced during pause");
            if(++paused>30) { gameflow.mPauseAll=false; phase=4; }
        } else if(phase==4 && bossMgr->prereleaseSeconds()==0) {
            for(auto& o:originals) require(o.boss->isAlive()==o.alive && o.boss->isAtari()==o.atari,"original flags not restored");
            std::printf("PASS prerelease: %zu fixtures, pause, 60s expiry, restoration\n",originals.size()); std::fflush(stdout); std::_Exit(0);
        }
        return result;
    }
};
int main(int argc, char** argv) {
    SDL_SetMainReady(); pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");
    pc_bbft_init(argc,argv);
    if (!pc_window_init("Progg fixture",640,480)) return 3;
    pc_settings_init(); gsys->Initialise(); pc_settings_p2d_init();
    nodeMgr = new NodeMgr(); gsys->run(new ProggApp()); return 0;
}
