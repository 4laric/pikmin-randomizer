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


class PluckApp : public PlugPikiApp {
    int frames = 0;
    void require(bool ok, const char* message) {
        if (!ok) { std::printf("FAIL pluck: %s\n", message); std::fflush(stdout); std::_Exit(1); }
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
        navi->mIsCursorVisible = false;
        navi->mPikiToPluck = selected;
        navi->mFastPluckKeyTaps = 0;
        const u32 extract = KeyConfig::_instance->mExtractKey.mBind;
        const u32 cancel = KeyConfig::_instance->mSetCursorKey.mBind;
        navi->mKontroller->mCurrentInput = extract;
        navi->mStateMachine->transit(navi, NAVISTATE_Nuku);
        NaviNukuState* pluck = static_cast<NaviNukuState*>(navi->getCurrState());
        for (int i = 0; i < 20; ++i) pluck->exec(navi);
        require(pluck->mWantsNextPluck, "unbroken hold did not continue");
        require(navi->mFastPluckKeyTaps == 0, "hold inflated fast tap count");
        navi->mKontroller->mCurrentInput = 0;
        pluck->exec(navi);
        require(!pluck->mWantsNextPluck, "release left a queued pluck");
        navi->mKontroller->mCurrentInput = extract | cancel;
        pluck->exec(navi);
        require(!pluck->mWantsNextPluck, "cancel did not stop continuation");
        navi->mKontroller->mCurrentInput = extract;
        pluck->exec(navi);
        require(pluck->mWantsNextPluck, "re-press did not resume request");
        // Release between exec and the finished animation event: it must be
        // sampled again at the boundary rather than consuming the stale flag.
        navi->mKontroller->mCurrentInput = 0;
        PaniAnimKeyEvent event(KEY_Finished);
        MsgAnim message(&event);
        pluck->procAnimMsg(navi, &message);
        require(navi->getCurrState()->getID() == NAVISTATE_Walk, "stale held input continued at boundary");
        std::puts("PASS pluck: unbroken hold, release, cancel, re-press, boundary release, bounded fast counter");
        std::fflush(stdout); std::_Exit(0);
    }
};
int main(int argc, char** argv) {
    SDL_SetMainReady(); pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");
    pc_bbft_init(argc,argv);
    if (!pc_window_init("Pluck fixture",640,480)) return 3;
    pc_settings_init(); gsys->Initialise(); pc_settings_p2d_init();
    nodeMgr = new NodeMgr(); gsys->run(new PluckApp()); return 0;
}
