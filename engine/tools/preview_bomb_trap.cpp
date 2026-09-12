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


#include "ItemMgr.h"
#include "BombItem.h"
#include "pc_randomizer.h"
#include <set>
class BombTrapApp : public PlugPikiApp {
    int frames = 0, phase = 0, pausedFrames = 0, settled = 0;
    bool exploded = false;
    std::set<BombItem*> ambush;
    void require(bool ok, const char* why) {
        if (!ok) { std::printf("FAIL ambush: %s\n",why); std::fflush(stdout); std::_Exit(1); }
    }
public:
    int idle() override {
        int result = PlugPikiApp::idle();
        require(++frames < 3600, "timeout");
        MoviePlayer* movies = gameflow.mMoviePlayer;
        if (movies && movies->mIsActive) { movies->requestSkip(); return result; }
        if (!naviMgr || !itemMgr || !pc_randomizer_ready()) return result;
        Navi* navi = naviMgr->getNavi();
        if (!navi || !navi->getCurrState()) return result;
        if (phase == 0) {
            if (gameflow.mPauseAll || gameflow.mIsUIOverlayActive || navi->getCurrState()->getID()!=NAVISTATE_Walk) return result;
            gameflow.mPauseAll = true; phase = 1;
            std::puts("AMBUSH_PAUSED_READY"); std::fflush(stdout);
        }
        int lit = 0, active = 0;
        Iterator items(itemMgr);
        CI_LOOP(items) {
            ItemCreature* item = static_cast<ItemCreature*>(*items);
            if (item->mObjType != OBJTYPE_Bomb || !item->getCurrState()) continue;
            BombItem* bomb = static_cast<BombItem*>(item);
            const int state = bomb->getCurrState()->getID();
            if (state == BombAI::BOMB_Set) {
                ++lit;
                if (phase == 2) {
                    require(bomb->mSAICtx.mCurrentItemHealth > 0, "missing fuse");
                    ambush.insert(bomb);
                }
            }
            if (ambush.count(bomb)) {
                if (state == BombAI::BOMB_Bomb || state == BombAI::BOMB_Die) exploded = true;
                if (state == BombAI::BOMB_Set || state == BombAI::BOMB_Bomb) ++active;
            }
        }
        if (phase == 1) {
            require(lit == 0, "spawned while paused");
            if (pc_randomizer_benefit_pending(PC_BENEFIT_BOMB_TRAP) && ++pausedFrames > 60) {
                gameflow.mPauseAll = false; phase = 2;
            }
        } else if (phase == 2 && lit) {
            require(lit == 5 && ambush.size() == 5, "partial ambush");
            require(!pc_randomizer_benefit_pending(PC_BENEFIT_BOMB_TRAP), "receipt not consumed");
            phase = 3;
        } else if (phase == 3 && exploded && !active && ++settled > 60) {
            std::puts("PASS ambush: queued while paused, five lit bombs, native fuse and explosion, receipt consumed");
            std::fflush(stdout); std::_Exit(0);
        }
        return result;
    }
};
int main(int argc, char** argv) {
    SDL_SetMainReady(); pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");
    pc_bbft_init(argc,argv);
    if (!pc_window_init("Bomb ambush fixture",640,480)) return 3;
    pc_settings_init(); gsys->Initialise(); pc_settings_p2d_init();
    nodeMgr = new NodeMgr(); gsys->run(new BombTrapApp()); return 0;
}
