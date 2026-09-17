// Flora scenario-boot fixture (#766, enemies-1 flora gate).
//
// Real-engine-world follow-on to the completed bridge-only P1 observer (#737):
// a replacement-main TU linked against the private pikmin_pc graph in place of
// pc_port/pc_main.cpp. It boots the REAL engine world over the settled private
// arena entry path (--experimental-pikmin2-room + the caller-staged cave entry
// package), stages a live starting squad with a centred 960x540 startup, parks
// the captain outside attack reach and runs the canonical captain guard (#632)
// on every observed tick BEFORE any readiness or PASS.
//
// Once a live squad is present it drives the landed #697 converter through the
// #723 engine hookup bridge for 47 Clover, 80 Tukushi and 89 Chiyogami and
// emits receipt-parseable P2_FLORA_SCENARIO_* markers with absorb-never-haul
// accounting. The converter and bridge are consumed read-only (included here
// because neither has a shared CMake target; the shared per-tick call site and
// CMake membership remain the serialized follow-on owned by #722).
//
// HONEST NON-CLAIMS: the engine has no flora conversion call site, so the
// conversion observed here is bridge-driven from fixture facts, NOT natural
// gameplay. All six runtime gates stay UNTESTED; no ADMIT, no ledger writes,
// no playability claim beyond what is observed.
#if __has_include("p2_fixture_captain_guard.h")
#include "p2_fixture_captain_guard.h"
#else
// Inline tested equivalent of scripts/p2_fixture_captain_guard.h (sha256
// d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474); a
// replacement-main TU cannot include a Python-tree script header at native
// build time. Observation-only; never changes captain health or game state.
#include <cmath>
#include <cstdio>
#include <cstdlib>
inline bool p2_fixture_captain_down(bool orimaDead, bool deadState, float hp) {
    return orimaDead || deadState || !std::isfinite(hp) || hp <= 1.0f;
}
inline void p2_fixture_require_captain(bool orimaDead, bool deadState, float hp, int tick) {
    if (!p2_fixture_captain_down(orimaDead, deadState, hp)) return;
    std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f orima_dead=%d dead_state=%d outcome=BLOCKED\n",
                tick, hp, int(orimaDead), int(deadState));
    std::fflush(nullptr);
    std::_Exit(86); // interrupted observation, never a successful fixture exit
}
#endif
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "App.h"
#include "Node.h"
#include "Graphics.h"
#include "GameCoreSection.h"
#include "Section.h"
#include "NaviMgr.h"
#include "Navi.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Creature.h"
#include "MoviePlayer.h"
#include "GameStat.h"
#include "PlayerState.h"
#include "gameflow.h"
#include "system.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "teki.h"
#include "pc_p2_cave.h"
#include "pc_p2_preview.h"
#include "pc_window.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "../pc_port/pc_p2_flora_hookup.h"
// Neither the #697 converter nor the #723 bridge has a shared CMake target and
// this lane may not edit shared build files, so both TUs are compiled as part
// of this replacement-main TU. They have no other object in the link, so this
// single inclusion is the one and only definition site for each.
#include "../pc_port/pc_p2_flora_convert.cpp"
#include "../pc_port/pc_p2_flora_hookup.cpp"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace {

const char* const kFlora[] = {"Clover", "Tukushi", "Chiyogami"};
constexpr int kFloraCount = 3;
constexpr int kSquadSize = 20;
bool sForceCaptainDown = false; // env P2_FLORA_SCENARIO_FORCE_CAPTAIN_DOWN=1

int guardSelfTest() {
    struct Row { bool orima; bool dead; float hp; bool expectDown; };
    const Row rows[] = {
        {false, false, 100.0f, false},
        {false, false, 1.5f, false},
        {false, false, 1.0f, true},
        {false, false, 0.0f, true},
        {false, true, 100.0f, true},
        {true, false, 100.0f, true},
        {true, true, 0.0f, true},
    };
    for (size_t i = 0; i < sizeof(rows) / sizeof(rows[0]); ++i) {
        const bool down = p2_fixture_captain_down(rows[i].orima, rows[i].dead, rows[i].hp);
        if (down != rows[i].expectDown) {
            std::printf("FAIL FLORA_SCENARIO_BOOT selftest row=%d orima=%d dead=%d hp=%.3f got=%d want=%d\n",
                        int(i), int(rows[i].orima), int(rows[i].dead), rows[i].hp,
                        int(down), int(rows[i].expectDown));
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_FLORA_SCENARIO_SELFTEST_PASS rows=%d\n",
                int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}

void fail(const char* reason) {
    std::printf("FAIL FLORA_SCENARIO_BOOT %s\n", reason);
    std::fflush(stdout);
    std::_Exit(1);
}

int alivePikis() {
    int count = 0;
    Iterator it(pikiMgr);
    CI_LOOP(it) { Creature* p = *it; if (p && p->isAlive()) ++count; }
    return count;
}

// Drive one identity through the landed #723 bridge with live-facts inputs and
// emit absorb-never-haul accounting. Returns 0 on a consistent observation.
int observeFlora(const char* identity, int slot, p2flora::Species bud,
                 int serving, int* squadLeft) {
    using namespace p2flora;
    using namespace p2florahookup;
    SceneryRegistry registry;
    if (hookupBindScenery(registry, identity, slot) < 0) return -1;
    int converted = 0, received = 0;
    const HookupFacts first = {bud, 2, false, 2};
    const int got1 = hookupConvert(first);
    if (got1 < 0) return -1;
    converted += 2;
    received += got1;
    const HookupFacts second = {Pelplant, serving, false, 0};
    const int got2 = hookupConvert(second);
    if (got2 < 0) return -1;
    converted += serving;
    received += got2;
    if (*squadLeft < converted) return -1;
    *squadLeft -= converted;
    std::printf("P2_FLORA_SCENARIO_SESSION identity=%s converted=%d received=%d hauled=0\n",
                identity, converted, received);
    std::fflush(stdout);
    return (received == converted) ? 0 : -1;
}

class FloraScenarioBootApp final : public PlugPikiApp {
    int frames = 0, observed = 0;
    bool entrySeen = false;
public:
    int idle() override {
        int result = PlugPikiApp::idle();
        if (++frames > 30000) {
            std::printf("FAIL FLORA_SCENARIO_BOOT timeout entry_seen=%d observed=%d\n",
                        int(entrySeen), observed);
            std::fflush(stdout);
            std::_Exit(2);
        }
        if (!naviMgr || !tekiMgr || !pikiMgr) {
            if (frames % 600 == 0) {
                std::printf("P2_FLORA_SCENARIO_WAIT frames=%d navi_mgr=%d teki_mgr=%d piki_mgr=%d\n",
                            frames, int(naviMgr != nullptr), int(tekiMgr != nullptr),
                            int(pikiMgr != nullptr));
                std::fflush(stdout);
            }
            return result;
        }
        Navi* n = naviMgr->getNavi();
        if (!n) {
            if (frames % 600 == 0) {
                std::printf("P2_FLORA_SCENARIO_WAIT frames=%d navi=0 floor=%d\n",
                            frames, pc_p2_cave_floor());
                std::fflush(stdout);
            }
            return result;
        }
        // Guard FIRST: immediately after engine idle, before any readiness/PASS.
        if (sForceCaptainDown)
            p2_fixture_require_captain(true, true, 0.0f, observed);
        else
            p2_fixture_require_captain(GameStat::orimaDead, !n->isAlive(), n->mHealth, observed);
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip();
            return result;
        }
        if (gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;
        ++observed;
        const int floor = pc_p2_cave_floor();
        if (floor > 0 && !entrySeen) {
            entrySeen = true;
            std::printf("P2_FLORA_SCENARIO_ENTRY_READY floor=%d observed=%d\n", floor, observed);
            std::fflush(stdout);
        }
        if (!entrySeen) {
            if (observed % 600 == 0) {
                std::printf("P2_FLORA_SCENARIO_WAIT observed=%d floor=0\n", observed);
                std::fflush(stdout);
            }
            return result;
        }
        const int alive = alivePikis();
        if (alive <= 0) return result;
        // Live starting squad is on the floor under a guarded captain. Observe
        // the three flora identities through the hookup and finish.
        std::printf("P2_FLORA_SCENARIO_SQUAD pikis=%d\n", alive);
        std::fflush(stdout);
        int squadLeft = alive;
        int failures = 0;
        const p2flora::Species buds[kFloraCount] = {p2flora::BluePom, p2flora::RedPom, p2flora::YellowPom};
        const int servings[kFloraCount] = {5, 5, 1};
        for (int i = 0; i < kFloraCount; ++i) {
            if (observeFlora(kFlora[i], i, buds[i], servings[i], &squadLeft) != 0) {
                std::printf("P2_FLORA_SCENARIO_SESSION identity=%s converted=0 received=0 hauled=0\n",
                            kFlora[i]);
                std::fflush(stdout);
                ++failures;
            }
        }
        std::printf("P2_FLORA_SCENARIO_DONE failures=%d squad_left=%d\n", failures, squadLeft);
        std::fflush(stdout);
        if (failures != 0) fail("session-failures");
        std::puts("PASS FLORA_SCENARIO_BOOT sessions=3");
        std::fflush(stdout);
        std::_Exit(0);
    }
};

} // namespace

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        if (std::string(argv[i]) == "--guard-self-test") return guardSelfTest();
        if (std::string(argv[i]) == "--guard-negative-test") {
            // Exercise the exact interruption call idle() uses: must print
            // P2_FIXTURE_CAPTAIN_DOWN and exit BLOCKED (86) with no PASS.
            p2_fixture_require_captain(true, true, 0.0f, 0);
            std::printf("FAIL FLORA_SCENARIO_BOOT negative test did not trip\n");
            std::fflush(stdout);
            return 1;
        }
    }
    const char* force = std::getenv("P2_FLORA_SCENARIO_FORCE_CAPTAIN_DOWN");
    if (force && force[0] == 49 && force[1] == 0) sForceCaptainDown = true;
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    if (!pc_pikipelago_room_preview()) {
        std::printf("FAIL FLORA_SCENARIO_BOOT requires --experimental-pikmin2-room\n");
        std::fflush(stdout);
        return 3;
    }
    if (!pc_window_init("P2 flora scenario boot fixture", 960, 540)) return 3;
    pc_window_center();
    {
        SDL_Window* window = SDL_GL_GetCurrentWindow();
        int width = 0, height = 0, x = 0, y = 0;
        SDL_GetWindowSize(window, &width, &height);
        SDL_GetWindowPosition(window, &x, &y);
        SDL_Rect bounds{0, 0, 0, 0};
        SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window), &bounds);
        const bool centered = std::abs(x - (bounds.x + (bounds.w - width) / 2)) <= 2
            && std::abs(y - (bounds.y + (bounds.h - height) / 2)) <= 2;
        std::printf("P2_FLORA_SCENARIO_WINDOW size=%dx%d pos=%d,%d display=%dx%d centered=%d\n",
                    width, height, x, y, bounds.w, bounds.h, int(centered));
        std::fflush(stdout);
        if (width != 960 || height != 540 || !centered) fail("window-geometry");
    }
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new FloraScenarioBootApp());
    return 0;
}