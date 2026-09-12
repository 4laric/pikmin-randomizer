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
class ProggApp : public PlugPikiApp {
    int frames = 0, phase = 0, pausedFrames = 0;
    float observed = 0.0f, moved = 0.0f;
    Vector3f origin;
    bool emerged = false;
    void require(bool ok, const char* why) {
        if (!ok) { std::printf("FAIL progg: %s\n",why); std::fflush(stdout); std::_Exit(1); }
    }
public:
    int idle() override {
        int result = PlugPikiApp::idle();
        require(++frames < 3000, "timeout");
        MoviePlayer* movies = gameflow.mMoviePlayer;
        if (movies && movies->mIsActive) { movies->requestSkip(); return result; }
        if (!naviMgr || !tekiMgr || !pc_randomizer_ready()) return result;
        Navi* navi = naviMgr->getNavi();
        if (!navi || !navi->getCurrState()) return result;
        if (phase == 0) {
            if (gameflow.mPauseAll || gameflow.mIsUIOverlayActive || navi->getCurrState()->getID()!=NAVISTATE_Walk) return result;
            require(tekiMgr->mUsingType[TEKI_Dororo], "asset not preloaded");
            // This fixture observes AI for 32 seconds unattended; tutorial UI
            // and captain death must not end that observation window.
            for (int flag = 0; flag < DEMOFLAG_COUNT; ++flag) playerState->mDemoFlags.setFlagOnly(flag);
            gameflow.mPauseAll = true; phase = 1;
            std::puts("PROGG_PAUSED_READY"); std::fflush(stdout);
        }
        navi->mHealth = C_NAVI_PARM(navi, mHealth);
        int count = 0; Teki* progg = nullptr;
        Iterator enemies(tekiMgr);
        CI_LOOP(enemies) {
            Teki* enemy = static_cast<Teki*>(*enemies);
            if (enemy->mTekiType == TEKI_Dororo && enemy->isAlive()) { ++count; progg = enemy; }
        }
        if (phase == 1) {
            require(count == 0, "spawned while paused");
            if (pc_randomizer_benefit_pending(PC_BENEFIT_PROGG) && ++pausedFrames > 30) {
                gameflow.mPauseAll = false; phase = 2;
            }
        } else if (phase == 2 && count) {
            require(count == 1 && progg->mTekiShape && !progg->mGenerator, "invalid actor");
            require(pc_randomizer_benefit_pending(PC_BENEFIT_PROGG), "consumed queued second trap");
            origin = progg->mSRT.t; phase = 3;
        } else if (phase == 3) {
            require(count == 1, "stacked or lost Progg");
            require(pc_randomizer_benefit_pending(PC_BENEFIT_PROGG), "second trap consumed");
            if (progg->mStateID >= DOROROSTATE_GoGoalPath) emerged = true;
            moved = std::max(moved, progg->mSRT.t.distance(origin));
            if (!gameflow.mPauseAll && !gameflow.mIsUIOverlayActive) observed += gsys->getFrameTime();
            const float duration = std::getenv("PROGG_FIXTURE_LONG") ? 32.0f : 8.0f;
            if (observed > duration) {
                require(emerged && moved > 1.0f, "native AI did not emerge and move");
                std::printf("PASS progg: pause, one actor, emerged, moved=%.1f, queue held for %.1fs\n", moved, observed);
                std::fflush(stdout); std::_Exit(0);
            }
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
