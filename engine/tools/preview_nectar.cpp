// Real-engine nectar spawning and drinking regression; isolated test main only.
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
class NectarApp : public PlugPikiApp {
    int frames = 0, phase = 0, pausedFrames = 0;
    Piki* drinker = nullptr;
    bool drank = false;
    void require(bool ok, const char* why) {
        if (!ok) { std::printf("FAIL nectar: %s\n",why); std::fflush(stdout); std::_Exit(1); }
    }
public:
    int idle() override {
        int result = PlugPikiApp::idle();
        require(++frames < 2700, "timeout");
        MoviePlayer* movies = gameflow.mMoviePlayer;
        if (movies && movies->mIsActive) { movies->requestSkip(); return result; }
        if (!naviMgr || !pikiMgr || !itemMgr || !pc_randomizer_ready()) return result;
        Navi* navi = naviMgr->getNavi();
        if (!navi || !navi->getCurrState()) return result;
        if (phase == 0) {
            if (gameflow.mPauseAll || gameflow.mIsUIOverlayActive || navi->getCurrState()->getID()!=NAVISTATE_Walk) return result;
            Iterator pikis(pikiMgr);
            CI_LOOP(pikis) {
                Piki* piki = static_cast<Piki*>(*pikis);
                if (piki->isAlive() && piki->mHappa == Leaf && piki->getState() == PIKISTATE_Normal) { drinker = piki; break; }
            }
            if (!drinker) return result;
            gameflow.mPauseAll = true; phase = 1;
            std::puts("NECTAR_PAUSED_READY"); std::fflush(stdout);
        }
        int nectar = 0;
        MizuItem* target = nullptr;
        Iterator items(itemMgr);
        CI_LOOP(items) {
            Creature* item = *items;
            if (item->mObjType == OBJTYPE_Water && item->isAlive()) {
                ++nectar; target = static_cast<MizuItem*>(item);
            }
        }
        if (phase == 1) {
            require(nectar == 0, "spawned while paused");
            if (pc_randomizer_benefit_pending(PC_BENEFIT_FLOWERS) && ++pausedFrames > 60) {
                gameflow.mPauseAll = false; phase = 2;
            }
        } else if (phase == 2 && nectar) {
            require(nectar == 5, "partial shower");
            require(drinker->mHappa == Leaf, "instant flowering");
            require(!pc_randomizer_benefit_pending(PC_BENEFIT_FLOWERS), "receipt not consumed");
            // Move a leaf Pikmin onto the real spawned nectar; native collision,
            // drinking animation and growth must perform every subsequent step.
            drinker->changeMode(PikiMode::FreeMode,navi);
            drinker->mSRT.t = target->mSRT.t;
            drinker->mVelocity.set(0,0,0);
            phase = 3;
        } else if (phase == 3) {
            if (drinker->getState() == PIKISTATE_Absorb) drank = true;
            if (drinker->mHappa == Flower) {
                require(drank, "flowered without drinking");
                std::puts("PASS nectar: pause deferral, five native drops, no instant flowers, physical drinking and growth");
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
    if (!pc_window_init("Nectar fixture",640,480)) return 3;
    pc_settings_init(); gsys->Initialise(); pc_settings_p2d_init();
    nodeMgr = new NodeMgr(); gsys->run(new NectarApp()); return 0;
}
