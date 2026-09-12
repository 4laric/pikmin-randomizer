// Real-engine initiated pluck input regression; isolated test main only.
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
#include "Kontroller.h"
#include "KeyConfig.h"
#include "Msg.h"
#include "PaniAnimator.h"
#include <cmath>
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cstdio>
#include <cstdlib>


#include "King.h"
#include "Boss.h"
#include "pc_randomizer.h"
class EmperorApp : public PlugPikiApp {
    int frames = 0, lockedFrames = 0;
    bool damaged = false;
public:
    int idle() override {
        int result = PlugPikiApp::idle();
        if (++frames > 12000) { std::puts("FAIL Emperor timeout"); std::fflush(stdout); std::_Exit(1); }
        if (pc_randomizer_goal()) { std::puts("PASS Emperor live: dormant at 24, activates at 25, death completes"); std::fflush(stdout); std::_Exit(0); }
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) { gameflow.mMoviePlayer->requestSkip(); return result; }
        if (!bossMgr || !naviMgr || !pc_randomizer_ready() || gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;
        Navi* navi = naviMgr->getNavi(); if (!navi) return result;
        Iterator it(bossMgr);
        CI_LOOP(it) {
            Boss* boss = static_cast<Boss*>(*it);
            if (!boss || boss->mObjType != OBJTYPE_King) continue;
            navi->mSRT.t = boss->mSRT.t;
            navi->mSRT.t.y += 10.0f;
            if (pc_randomizer_repairs() < 25) {
                if (boss->getCurrentState() != KINGAI_Stay) { std::puts("FAIL Emperor woke before repairs"); std::fflush(stdout); std::_Exit(1); }
                if (++lockedFrames == 120) { std::puts("EMPEROR_LOCKED_PASS"); std::fflush(stdout); }
            } else if (!damaged && boss->getCurrentState() != KINGAI_Stay) {
                damaged = true;
                boss->subCurrentLife(boss->getCurrentLife());
            }
        }
        return result;
    }
};
int main(int argc, char** argv) {
    SDL_SetMainReady(); pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");
    pc_bbft_init(argc,argv);
    if (!pc_window_init("Emperor fixture",640,480)) return 3;
    pc_settings_init(); gsys->Initialise(); pc_settings_p2d_init();
    nodeMgr = new NodeMgr(); gsys->run(new EmperorApp()); return 0;
}
