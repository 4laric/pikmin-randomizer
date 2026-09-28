// Guarded replacement-main fixture proving preview pr05 reconciliation (#679).
//
// Boots the REAL game-linked engine over the P2 room preview, lets the
// reconciled setup path (pc_port/pc_p2_preview.cpp) classify pr05 pellets by
// generator id (room bolts carry id 0 and are never staged treasure/cargo),
// and asserts the reconciled treasure outcome matches the caller expectation
// (env P2_PELLET_RECONCILIATION_EXPECT_TREASURE=0/1) under a live squad.
//
// Ordering contract (#632): the canonical captain guard runs on EVERY idle
// tick immediately after the base engine idle and BEFORE any readiness
// observation or PASS. CAPTAIN_DOWN exits BLOCKED (86) with no PASS. The
// guard never changes game state.
//
// Replacement-main convention: mirrors tools/p2_kurage_runtime.cpp (scenario
// main instead of pc_main.cpp; 960x540 centred window;
// --experimental-pikmin2-room boot). Promotion to a first-class CMake target
// is a documented shared-owner follow-up; the lane build script links this TU
// against the private pikmin_pc graph without editing shared build files.
//
// Markers: P2_PELLET_RECONCILIATION_* only, plus the engine's own
// P2_PREVIEW_PR05 reconciliation summary. Successful boot ends with
// "PASS PELLET_RECONCILIATION" and exit 0. Anything else is FAIL (1),
// BLOCKED (86), or timeout (2). No PASS is ever emitted without observed
// evidence.
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "App.h"
#include "Node.h"
#include "Graphics.h"
#include "GameCoreSection.h"
#include "Generator.h"
#include "Section.h"
#include "NaviMgr.h"
#include "Navi.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "Collision.h"
#include "Creature.h"
#include "MoviePlayer.h"
#include "GameStat.h"
#include "PlayerState.h"
#include "gameflow.h"
#include "system.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_gfx.h"
#include "teki.h"
#include "pc_p2_preview.h"
#include "pc_window.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

// Captain-safety guard (#632), vendored verbatim from
// scripts/p2_fixture_captain_guard.h;
// observation-only, equivalent tested guard. The canonical header is consumed
// read-only; this vendored copy exists because a replacement-main TU cannot
// include a Python-tree script header at native build time.
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

namespace {
bool sGuardSelfTest = false;
bool sForceCaptainDown = false; // env P2_PELLET_RECONCILIATION_FORCE_CAPTAIN_DOWN=1: negative-path test only

// Engine-independent self test of the vendored guard truth table. Runs before
// any engine boot so it works without assets or a display.
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
            std::printf("FAIL PELLET_RECONCILIATION selftest row=%d orima=%d dead=%d hp=%.3f got=%d want=%d\n",
                        int(i), int(rows[i].orima), int(rows[i].dead), rows[i].hp,
                        int(down), int(rows[i].expectDown));
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_PELLET_RECONCILIATION_SELFTEST_PASS rows=%d\n", int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}

class PelletReconciliationApp final : public PlugPikiApp {
    int frames = 0, observed = 0;
    bool expectTreasure = false;
    bool readyLogged = false;
    int alivePikis() {
        int count = 0;
        Iterator it(pikiMgr);
        CI_LOOP(it) { Creature* p = *it; if (p && p->isAlive()) ++count; }
        return count;
    }
public:
    explicit PelletReconciliationApp(bool expect) : expectTreasure(expect) {}
    int idle() override {
        int result = PlugPikiApp::idle();
        if (++frames > 30000) {
            std::printf("FAIL PELLET_RECONCILIATION timeout observed=%d expect_treasure=%d\n",
                        observed, int(expectTreasure));
            std::fflush(stdout);
            std::_Exit(2);
        }
        if (!naviMgr || !tekiMgr || !pikiMgr) {
            if (frames % 600 == 0) {
                std::printf("P2_PELLET_RECONCILIATION_WAIT frames=%d navi_mgr=%d teki_mgr=%d piki_mgr=%d\n",
                            frames, int(naviMgr != nullptr), int(tekiMgr != nullptr),
                            int(pikiMgr != nullptr));
                std::fflush(stdout);
            }
            return result;
        }
        Navi* n = naviMgr->getNavi();
        if (!n) {
            if (frames % 600 == 0) {
                std::printf("P2_PELLET_RECONCILIATION_WAIT frames=%d navi=0\n", frames);
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
        // The reconciled treasure outcome is engine state applied by
        // pc_p2_preview_setup: room bolts (generator id 0) skipped, staged
        // nonzero-id pellet selected (or none). Assert it matches the staged
        // arena expectation under a live squad.
        const bool hasTreasure = pc_p2_preview_treasure() != nullptr;
        if (!readyLogged && observed % 600 == 0) {
            std::printf("P2_PELLET_RECONCILIATION_WAIT observed=%d treasure=%d expect=%d\n",
                        observed, int(hasTreasure), int(expectTreasure));
            std::fflush(stdout);
        }
        if (observed >= 600 && !readyLogged) {
            readyLogged = true;
            std::printf("P2_PELLET_RECONCILIATION_READY observed=%d treasure=%d expect=%d\n",
                        observed, int(hasTreasure), int(expectTreasure));
            std::fflush(stdout);
        }
        if (readyLogged) {
            const int alive = alivePikis();
            if (alive > 0) {
                if (hasTreasure != expectTreasure) {
                    std::printf("FAIL PELLET_RECONCILIATION treasure=%d expect=%d squad_alive=%d observed=%d\n",
                                int(hasTreasure), int(expectTreasure), alive, observed);
                    std::fflush(stdout);
                    std::_Exit(1);
                }
                std::printf("P2_PELLET_RECONCILIATION_PASS treasure=%d squad_alive=%d observed=%d\n",
                            int(hasTreasure), alive, observed);
                std::puts("PASS PELLET_RECONCILIATION");
                std::fflush(stdout);
                std::_Exit(0);
            }
        }
        return result;
    }
};
} // namespace

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        if (std::string(argv[i]) == "--guard-self-test") sGuardSelfTest = true;
        if (std::string(argv[i]) == "--guard-negative-test") {
            // Exercise the exact interruption call idle() uses: must print
            // P2_FIXTURE_CAPTAIN_DOWN and exit BLOCKED (86) with no PASS.
            // Engine-independent; the exit code is the assertion.
            p2_fixture_require_captain(true, true, 0.0f, 0);
            std::printf("FAIL PELLET_RECONCILIATION negative test did not trip\n");
            std::fflush(stdout);
            return 1;
        }
    }
    if (sGuardSelfTest) return guardSelfTest();
    const char* force = std::getenv("P2_PELLET_RECONCILIATION_FORCE_CAPTAIN_DOWN");
    if (force && force[0] == 49 && force[1] == 0) sForceCaptainDown = true;
    bool expectTreasure = false;
    if (const char* expect = std::getenv("P2_PELLET_RECONCILIATION_EXPECT_TREASURE"))
        expectTreasure = expect[0] == 49;
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    if (!pc_pikipelago_room_preview()) {
        std::printf("FAIL PELLET_RECONCILIATION requires --experimental-pikmin2-room\n");
        std::fflush(stdout);
        return 3;
    }
    if (!pc_window_init("P2 pellet reconciliation fixture", 960, 540)) return 3;
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
        std::printf("P2_PELLET_RECONCILIATION_WINDOW size=%dx%d pos=%d,%d display=%dx%d centered=%d\n",
                    width, height, x, y, bounds.w, bounds.h, int(centered));
        std::fflush(stdout);
    }
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new PelletReconciliationApp(expectTreasure));
    return 0;
}
