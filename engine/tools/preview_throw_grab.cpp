// Live regression: enter throw preparation with A already released. The actual
// game must finish its grab animation and throw, for both near and approaching Pikmin.
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
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cstdio>
#include <cstdlib>

class GrabApp : public PlugPikiApp {
    int frames = 0, began = 0;
    Piki* selected = nullptr;
    bool attached = false;
public:
    int idle() override {
        int result = PlugPikiApp::idle();
        if (++frames > 1800) { std::puts("FAIL grab timeout"); std::fflush(stdout); std::_Exit(1); }
        MoviePlayer* movies = gameflow.mMoviePlayer;
        if (movies && movies->mIsActive) {
            for (MovieInfo* info = static_cast<MovieInfo*>(movies->mPlayInfoList.mChild); info;
                 info = static_cast<MovieInfo*>(info->mNext))
                if (info->mPlayer) info->mPlayer->requestSkip();
            return result;
        }
        if (!naviMgr || gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;
        Navi* navi = naviMgr->getNavi();
        if (!navi || !navi->mPlateMgr || !navi->getCurrState()) return result;
        if (!began && navi->getCurrState()->getID() == NAVISTATE_Walk) {
            if (!selected) {
                Iterator squad(pikiMgr);
                CI_LOOP(squad) {
                    Piki* piki = static_cast<Piki*>(*squad);
                    if (!selected && piki->isAlive() && piki->getState() == PIKISTATE_Normal && piki->isThrowable()) selected = piki;
                }
                if (!selected) return result;
                selected->mNavi = navi;
                selected->changeMode(PikiMode::FormationMode, navi);
                // CPlate publishes newly allocated formation slots on update.
                return result;
            }
            const float distance = std::getenv("PIKMIN_GRAB_FAR") ? 65.0f : 4.0f;
            Iterator move(navi->mPlateMgr);
            CI_LOOP(move) {
                Piki* piki = static_cast<Piki*>(*move);
                piki->mSRT.t = navi->mSRT.t + Vector3f(piki == selected ? distance : 500.0f, 0, 0);
                piki->mGrid.updateGrid(piki->mSRT.t);
            }
            navi->mStateMachine->transit(navi, NAVISTATE_ThrowWait);
            std::printf("SELECT state=%d throwable=%d\n", selected->getState(), selected->isThrowable());
            began = frames;
            std::printf("BEGIN grab distance=%.0f\n",distance); std::fflush(stdout);
        } else if (began) {
            attached |= selected->getState() == PIKISTATE_Hanged;
            if (selected->getState() == PIKISTATE_Flying) {
                // Hanged can begin and end within one idle iteration. Flying
                // is the externally observable result of the real throw event.
                std::printf("PASS released-A grab then throw: flying=1 observed_hanged=%d frames=%d\n",attached,frames-began);
                std::fflush(stdout); std::_Exit(0);
            }
            if (frames-began > 180 || navi->getCurrState()->getID() == NAVISTATE_Walk) {
                std::printf("FAIL cancelled grab: state=%d attached=%d frames=%d\n",selected->getState(),attached,frames-began);
                std::fflush(stdout); std::_Exit(1);
            }
        }
        return result;
    }
};
int main(int argc, char** argv) {
    SDL_SetMainReady(); pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");
    pc_bbft_init(argc,argv);
    if (!pc_window_init("Throw grab fixture",640,480)) return 3;
    pc_settings_init(); gsys->Initialise(); pc_settings_p2d_init();
    nodeMgr = new NodeMgr(); gsys->run(new GrabApp()); return 0;
}
