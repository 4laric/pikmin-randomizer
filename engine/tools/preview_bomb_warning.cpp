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
#include "PikiAI.h"
#include "Interactions.h"
#include <vector>
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


struct WarningAction : ActPutBomb { using ActPutBomb::ActPutBomb; using ActPutBomb::warnPikis; };

class BombWarningApp : public PlugPikiApp {
    int frames = 0;
    void require(bool ok, const char* message) {
        if (!ok) { std::printf("FAIL bomb warning: %s\n", message); std::fflush(stdout); std::_Exit(1); }
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
        std::vector<Piki*> selected;
        Iterator pikis(pikiMgr);
        CI_LOOP(pikis) {
            Piki* piki = static_cast<Piki*>(*pikis);
            if (piki->isAlive() && piki->getState() == PIKISTATE_Normal && piki->mIsCallable) selected.push_back(piki);
            if (selected.size() == 4) break;
        }
        if (selected.size() != 4) return result;
        for (Piki* piki : selected) {
            piki->mNavi = navi;
            piki->mMode = PikiMode::PutbombMode;
            piki->mSRT.t = navi->mSRT.t;
            piki->mIsBeingDamaged = false;
            piki->mIsWhistlePending = false;
        }
        // hasBomb() is the existing held-creature predicate. These sentinels
        // are used only in synchronous warning dispatch, never an AI tick.
        for (int i = 0; i < 3; ++i) selected[i]->mGrabbedCreature.set(navi);
        WarningAction action(selected[0]);
        action.warnPikis();
        for (int i = 0; i < 3; ++i) {
            require(selected[i]->getState() == PIKISTATE_Normal, "warning interrupted a bomb carrier");
            require(selected[i]->mMode == PikiMode::PutbombMode, "warning cancelled bomb task");
            require(!selected[i]->mIsWhistlePending, "warning queued recall for carrier");
        }
        require(selected[3]->getState() == PIKISTATE_LookAt, "ordinary Pikmin did not react");
        selected[1]->mIsBeingDamaged = true;
        require(!selected[1]->stimulate(InteractWarn(selected[0])) && !selected[1]->mIsWhistlePending,
                "damaged carrier received pending warning recall");
        selected[1]->mIsBeingDamaged = false;
        for (int i = 0; i < 3; ++i) selected[i]->mGrabbedCreature.reset();
        require(selected[1]->stimulate(InteractWarn(selected[0])) && selected[1]->getState() == PIKISTATE_LookAt,
                "Pikmin without its bomb stopped responding to warnings");
        std::puts("PASS bomb warning: multiple carriers preserved, ordinary warning retained, no pending recall, released carrier reacts");
        std::fflush(stdout); std::_Exit(0);
    }
};
int main(int argc, char** argv) {
    SDL_SetMainReady(); pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");
    pc_bbft_init(argc,argv);
    if (!pc_window_init("Bomb warning fixture",640,480)) return 3;
    pc_settings_init(); gsys->Initialise(); pc_settings_p2d_init();
    nodeMgr = new NodeMgr(); gsys->run(new BombWarningApp()); return 0;
}
