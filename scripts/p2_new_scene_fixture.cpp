#include <SDL2/SDL.h>
#include "../src/plugPikiColin/newPikiGame.cpp"
#include "App.h"
#include "ItemMgr.h"
#include "GoalItem.h"
#include "Node.h"
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings_p2d.h"
#include "pc_p2_enemy.h"
#include "pc_p2_teki_lifetime.h"
#include "pc_p2_input_script.h"
#include "pc_randomizer.h"
#include "teki.h"
#include <cstdio>
#include <cstdlib>

// Lane 07 new-scene probe on the supported campaign path. Plays a Snow campaign
// day (real P2 family bindings), forces an ordinary day end through results/save
// to MapSelect, then drives the map-select menu with the reusable scripted-pad
// input (pc_p2_input_script) to load a fresh gameplay area in-process. The
// pc_p2_scene_generation() signal (finalSetup) is the safe new-scene readiness
// check: the transition frees the previous TekiMgr.
static bool confirmResults;

struct ResultController : Controller {
    int ticks = 0;
    ResultController() : Controller(1) {}
    void update() override { updateCont(confirmResults && (++ticks % 20 == 0) ? KBBTN_A : 0); }
};

static int countBound()
{
    int bound = 0;
    if (!tekiMgr) return 0;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        auto* e = static_cast<Teki*>(*it);
        if (e && pc_p2_enemy_name(e)) ++bound;
    }
    return bound;
}

class NewSceneApp : public PlugPikiApp {
    int frames = 0, ready = 0, held = 0;
    bool started = false, seen = false, done = false, menuPhase = false;
    unsigned long sceneBefore = 0;
    Controller* control = nullptr;
public:
    int idle() override
    {
        if (++frames > 14000) { std::printf("FAIL NEWSCENE timeout gen=%lu\n", pc_p2_scene_generation()); std::fflush(stdout); std::_Exit(1); }

        // Reusable menu automation: pulse A on the scripted pad once the
        // results/map-select UI owns the screen; release it during gameplay.
        if (menuPhase) {
            const bool pulse = ((frames / 20) % 4) == 0;
            pc_p2_input_script_set(1, pulse ? KBBTN_A : 0u);
            if (frames % 120 == 0)
                std::printf("P2_NEWSCENE_MENU frame=%d section=%d gen=%lu\n",
                            frames, int(gameflow.mCurrGameSectionID), pc_p2_scene_generation());
        } else {
            pc_p2_input_script_clear(1);
        }

        int result = PlugPikiApp::idle();
        MoviePlayer* movies = gameflow.mMoviePlayer;
        if (movies && movies->mIsActive && frames % 5 == 0) movies->requestSkip();

        if (!started && gamecore && movies && !movies->mIsActive && !gameflow.mPauseAll && !gameflow.mIsUIOverlayActive) {
            if (++ready == 60) {
                started = true;
                sceneBefore = pc_p2_scene_generation();
                std::printf("P2_NEWSCENE_BEFORE gen=%lu day=%d bound=%d\n",
                            sceneBefore, gameflow.mWorldClock.mCurrentDay, countBound());
                std::fflush(stdout);
                gameflow.mWorldClock.mCurrentDay = 7;
                gamecore->forceDayEnd();
                gameflow.mIsDayEndTriggered = TRUE;
                std::puts("P2_NEWSCENE_DAYEND forced");
            }
        }
        if (started && !seen && resultWindow) {
            seen = true;
            menuPhase = true;
            std::puts("P2_NEWSCENE_RESULTS opened; scripted pad engaged");
            std::fflush(stdout);
        }
        if (started && seen && !done) {
            // Safe new-scene signal: only touch TekiMgr after finalSetup advanced.
            if (pc_p2_scene_generation() > sceneBefore && tekiMgr) {
                const int bound = countBound();
                if (bound > 0) {
                    done = true;
                    pc_p2_input_script_clear(1);
                    std::printf("P2_NEWSCENE_RELOAD gen=%lu day=%d bound=%d\n",
                                pc_p2_scene_generation(), gameflow.mWorldClock.mCurrentDay, bound);
                    std::puts("PASS P2_NEWSCENE_RELOAD");
                    std::fflush(stdout);
                    std::_Exit(0);
                }
            }
        }
        return result;
    }
};

int main(int argc, char** argv)
{
    SDL_SetMainReady(); pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    if (!pc_window_init("Lane07 new scene probe", 960, 540)) return 3;
    pc_window_center();
    pc_settings_init(); gsys->Initialise(); pc_settings_p2d_init();
    nodeMgr = new NodeMgr(); gsys->run(new NewSceneApp()); return 0;
}
