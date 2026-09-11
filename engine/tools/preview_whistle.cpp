// Real-engine whistle recruitment regression; isolated test main only.
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


class WhistleApp : public PlugPikiApp {
    int frames = 0;
    void require(bool ok, const char* message) {
        if (!ok) { std::printf("FAIL whistle: %s\n", message); std::fflush(stdout); std::_Exit(1); }
    }
public:
    int idle() override {
        int result = PlugPikiApp::idle();
        require(++frames < 1800, "startup timeout");
        MoviePlayer* movies = gameflow.mMoviePlayer;
        if (movies && movies->mIsActive) { movies->requestSkip(); return result; }
        if (!naviMgr || !pikiMgr || gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;
        Navi* navi = naviMgr->getNavi();
        if (!navi || !navi->getCurrState() || navi->getCurrState()->getID() != NAVISTATE_Walk) return result;
        Piki* selected = nullptr;
        Iterator pikis(pikiMgr);
        CI_LOOP(pikis) {
            Piki* piki = static_cast<Piki*>(*pikis);
            if (piki->isAlive() && piki->getState() == PIKISTATE_Normal && piki->mIsCallable) { selected = piki; break; }
        }
        if (!selected) return result;
        require(std::fabs(pc_whistle_fraction(0) - .35f) < .0001f, "initial radius fraction");
        require(pc_whistle_fraction(.3f) > .35f && pc_whistle_fraction(.3f) < 1, "continuous expansion");
        require(pc_whistle_fraction(.6f) == 1 && pc_whistle_fraction(5) == 1, "maximum clamp");
        require(!pc_whistle_recall_workers(.599f, true), "early hold interrupts");
        require(pc_whistle_recall_workers(.6f, true), "full hold missing");
        require(!pc_whistle_recall_workers(1, false), "release interrupts");
        selected->mNavi = navi;
        navi->mCursorWorldPos = selected->mSRT.t;
        // Only change the mode tag for protected calls: they must leave the
        // real action/state untouched. Restore it before running normal recall.
        int originalMode = selected->mMode;
        int protectedModes = 0;
        for (int mode = PikiMode::AttackMode; mode < PikiMode::COUNT; ++mode) {
            selected->mMode = mode;
            navi->callPikis(100.0f, false);
            require(selected->getState() == PIKISTATE_Normal && selected->mMode == mode, "tap abandoned task");
            ++protectedModes;
        }
        selected->mMode = originalMode;
        navi->mCursorWorldPos.x += 200.0f;
        navi->callPikis(100.0f, true);
        require(selected->getState() == PIKISTATE_Normal, "called out-of-range target");
        navi->mCursorWorldPos = selected->mSRT.t;
        selected->mMode = PikiMode::TransportMode;
        navi->callPikis(100.0f, pc_whistle_recall_workers(.6f, true));
        require(selected->getState() == PIKISTATE_LookAt, "hold did not recall worker");
        selected->mMode = originalMode;
        selected->mFSM->transit(selected, PIKISTATE_Normal);
        selected->mMode = PikiMode::FreeMode;
        navi->callPikis(100.0f, false);
        require(selected->getState() == PIKISTATE_LookAt, "tap did not call idle Pikmin");
        std::printf("PASS whistle: %d protected modes, idle tap, full hold, range, timing and radius\n", protectedModes);
        std::fflush(stdout); std::_Exit(0);
    }
};
int main(int argc, char** argv) {
    SDL_SetMainReady(); pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");
    pc_bbft_init(argc,argv);
    if (!pc_window_init("Whistle fixture",640,480)) return 3;
    pc_settings_init(); gsys->Initialise(); pc_settings_p2d_init();
    nodeMgr = new NodeMgr(); gsys->run(new WhistleApp()); return 0;
}
