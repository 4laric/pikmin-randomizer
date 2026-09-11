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
#include "Kontroller.h"
#include <cmath>
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cstdio>
#include <initializer_list>
#include <cstdlib>



class BombApp : public PlugPikiApp {
    int frames = 0;
    Piki* regular = nullptr;
    Piki* bomb = nullptr;
    void require(bool ok, const char* message) {
        if (!ok) { std::printf("FAIL bomb selection: %s\n",message); std::fflush(stdout); std::_Exit(1); }
    }
public:
    int idle() override {
        int result = PlugPikiApp::idle();
        require(++frames < 1800, "startup timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) { gameflow.mMoviePlayer->requestSkip(); return result; }
        if (!naviMgr || !pikiMgr || gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;
        Navi* navi = naviMgr->getNavi();
        if (!navi || !navi->getCurrState() || navi->getCurrState()->getID() != NAVISTATE_Walk) return result;
        if (!regular || !bomb) {
            Iterator all(pikiMgr);
            CI_LOOP(all) {
                Piki* piki = static_cast<Piki*>(*all);
                if (!piki->isAlive() || piki->getState() != PIKISTATE_Normal) continue;
                if (!regular) regular = piki;
                else if (piki != regular && !bomb) bomb = piki;
            }
            if (!regular || !bomb) return result;
            for (Piki* piki : {regular, bomb}) {
                piki->mNavi = navi;
                piki->initColor(Yellow);
                piki->changeMode(PikiMode::FormationMode,navi);
            }
            return result; // Publish CPlate slots before exercising selection.
        }
        // This red-only seed enforces locked colors during AI updates. Set
        // selection color synchronously with the sentinel and never tick it.
        regular->mColor = Yellow;
        bomb->mColor = Yellow;
        regular->mSRT.t = navi->mSRT.t + Vector3f(10,0,0);
        bomb->mSRT.t = navi->mSRT.t + Vector3f(20,0,0);
        regular->mGrid.updateGrid(regular->mSRT.t);
        bomb->mGrid.updateGrid(bomb->mSRT.t);
        // hasBomb() uses the held-creature flag. Use a sentinel only during
        // these synchronous selection calls; never run game AI with it set.
        bomb->mGrabbedCreature.set(navi);
        require(pc_throw_selection_class(regular) == Yellow, "regular class");
        require(pc_throw_selection_class(bomb) == PikiColorCount, "bomb class");
        navi->mKontroller->mInputPressed = KBBTN_DPAD_RIGHT;
        require(pc_cycle_throw_color(navi,regular) == bomb, "right must select bomb yellow");
        navi->findNextThrowPiki();
        require(navi->mNextThrowPiki == bomb, "preview lost bomb preference");
        navi->mKontroller->mInputPressed = KBBTN_DPAD_LEFT;
        require(pc_cycle_throw_color(navi,bomb) == regular, "left must select regular yellow");
        navi->findNextThrowPiki();
        require(navi->mNextThrowPiki == regular, "preview chose bomb for regular class");
        navi->mKontroller->mInputPressed = KBBTN_DPAD_LEFT | KBBTN_DPAD_RIGHT;
        require(!pc_cycle_throw_color(navi,regular), "simultaneous directions must cancel");
        bomb->mGrabbedCreature.reset();
        navi->mKontroller->mInputPressed = KBBTN_DPAD_RIGHT;
        require(!pc_cycle_throw_color(navi,regular), "empty bomb group should be skipped");
        std::puts("PASS bomb selection: distinct yellows, left/right, persistent preview, empty-group skip, simultaneous cancellation");
        std::fflush(stdout); std::_Exit(0);
    }
};
int main(int argc, char** argv) {
    SDL_SetMainReady(); pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");
    pc_bbft_init(argc,argv);
    if (!pc_window_init("Bomb selection fixture",640,480)) return 3;
    pc_settings_init(); gsys->Initialise(); pc_settings_p2d_init();
    nodeMgr = new NodeMgr(); gsys->run(new BombApp()); return 0;
}
