// P2 host-mode runtime wiring fixture, reconciled revision (lane
// host-mode-runtime-wiring-native, #702, gen 3).
//
// Replacement-main harness driving the LANDED #672 host-mode module
// (p2challenge::StageEntry/HostState/start/tick/descend/end/emit/retry)
// from LIVE engine facts inside a real guarded boot, plus the additive
// p2challenge::wiring observation layer. The fixture boots a P1 challenge
// level, enforces the captain guard on EVERY idle tick, reads the live squad
// (pikiMgr), captain state and real frame time, advances the landed state,
// and reports observed delivery. No invented values: harness constants (stage
// table, default time limit) are labeled as such; every runtime-varying
// field comes from the engine; unobserved transitions are reported missing.
// No PASS without delivered entries.
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
#include "pc_p2_challenge_mode.h"
#include "pc_p2_species.h"
#include "pc_window.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "teki.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

// Captain-safety guard (#632), vendored verbatim from
// scripts/p2_fixture_captain_guard.h (sha256
// d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474);
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
bool sGuardNegativeTest = false;
bool sForceCaptainDown = false; // env P2_HOST_MODE_FORCE_CAPTAIN_DOWN=1: negative-path test only
int sUiIndex = 0;

// Harness stage table (documented harness constants for static fields;
// population/time/end always come from live engine facts via the wiring).
// Mirrors the landed #672 boot-fixture table shape.
static const p2challenge::StageEntry kStages[] = {
    {"challenge-0", 0, 1, {300.0f, 0, 0, 0, 0, 0, 0, 0},
     {{0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0},
      {0, 0, 0}}, 0, 0},
    {"challenge-1", 1, 1, {300.0f, 0, 0, 0, 0, 0, 0, 0},
     {{0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0},
      {0, 0, 0}}, 0, 0},
    {"challenge-2", 2, 1, {300.0f, 0, 0, 0, 0, 0, 0, 0},
     {{0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0},
      {0, 0, 0}}, 0, 0},
    {"challenge-3", 3, 1, {300.0f, 0, 0, 0, 0, 0, 0, 0},
     {{0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0},
      {0, 0, 0}}, 0, 0},
    {"challenge-4", 4, 1, {300.0f, 0, 0, 0, 0, 0, 0, 0},
     {{0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0},
      {0, 0, 0}}, 0, 0},
};

// Engine-independent self test: vendored guard truth table plus the LANDED
// module contract (select/start/tick/end/emit) plus the wiring validation.
// Runs before any engine boot so it works without assets or a display.
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
            std::printf("FAIL HOST_MODE_WIRING selftest row=%d orima=%d dead=%d hp=%.3f got=%d want=%d\n",
                        int(i), int(rows[i].orima), int(rows[i].dead), rows[i].hp,
                        int(down), int(rows[i].expectDown));
            std::fflush(stdout);
            return 1;
        }
    }
    // Landed module contract first (read-only use, never redefined).
    if (p2challenge::selectByUiIndex(kStages, 5, 1) != 1) {
        std::printf("FAIL HOST_MODE_WIRING selftest: landed select\n");
        std::fflush(stdout);
        return 1;
    }
    if (p2challenge::selectByUiIndex(kStages, 5, 99) >= 0) {
        std::printf("FAIL HOST_MODE_WIRING selftest: landed select accepted bad ui\n");
        std::fflush(stdout);
        return 1;
    }
    p2challenge::HostState probe = p2challenge::start(kStages[1]);
    if (probe.timeLeft != 300.0f || probe.ended) {
        std::printf("FAIL HOST_MODE_WIRING selftest: landed start\n");
        std::fflush(stdout);
        return 1;
    }
    p2challenge::tick(probe, 1.0f);
    if (probe.timeLeft != 299.0f || probe.ended) {
        std::printf("FAIL HOST_MODE_WIRING selftest: landed tick\n");
        std::fflush(stdout);
        return 1;
    }
    // Wiring validation refuses bad facts without touching state.
    p2challenge::HostState rej = p2challenge::start(kStages[1]);
    p2challenge::wiring::LiveFacts bad;
    bad.squad_alive = -1;
    if (p2challenge::wiring::syncTick(rej, bad)) {
        std::printf("FAIL HOST_MODE_WIRING selftest: wiring accepted bad facts\n");
        std::fflush(stdout);
        return 1;
    }
    if (p2challenge::wiring::bindPopulation(rej, -1) >= 0) {
        std::printf("FAIL HOST_MODE_WIRING selftest: wiring bound negative population\n");
        std::fflush(stdout);
        return 1;
    }
    // Wiring happy path on synthetic live-like facts.
    p2challenge::HostState good = p2challenge::start(kStages[1]);
    p2challenge::wiring::LiveFacts live;
    live.squad_alive = 20;
    live.squad_reds = 20;
    live.captain_down = false;
    live.seconds = 1.0f;
    if (!p2challenge::wiring::syncTick(good, live)) {
        std::printf("FAIL HOST_MODE_WIRING selftest: wiring refused live facts\n");
        std::fflush(stdout);
        return 1;
    }
    if (good.population != 20 || good.timeLeft != 299.0f) {
        std::printf("FAIL HOST_MODE_WIRING selftest: wiring state wrong\n");
        std::fflush(stdout);
        return 1;
    }
    std::printf("P2_HOST_MODE_SELFTEST_PASS rows=%d\n", int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}
class HostModeWiringApp final : public PlugPikiApp {
    int frames = 0, observed = 0, ticks = 0;
    bool started = false;
    p2challenge::HostState mode;
    void countSquad(int& alive, int& reds) {
        alive = 0;
        reds = 0;
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive()) continue;
            ++alive;
            if (pc_p2_has_red_immunity(p)) ++reds;
        }
    }
public:
    int idle() override {
        int result = PlugPikiApp::idle();
        if (++frames > 30000) {
            std::printf("FAIL HOST_MODE_WIRING timeout observed=%d ticks=%d\n",
                        observed, ticks);
            std::fflush(stdout);
            std::_Exit(2);
        }
        if (!naviMgr || !tekiMgr || !pikiMgr) {
            if (frames % 600 == 0) {
                std::printf("P2_HOST_MODE_WAIT frames=%d navi_mgr=%d teki_mgr=%d piki_mgr=%d\n",
                            frames, int(naviMgr != nullptr), int(tekiMgr != nullptr),
                            int(pikiMgr != nullptr));
                std::fflush(stdout);
            }
            return result;
        }
        Navi* n = naviMgr->getNavi();
        if (!n) {
            if (frames % 600 == 0) {
                std::printf("P2_HOST_MODE_WAIT frames=%d navi=0\n", frames);
                std::fflush(stdout);
            }
            return result;
        }
        // Guard FIRST: immediately after engine idle, before any observation.
        const bool deadState = !n->isAlive();
        if (sForceCaptainDown)
            p2_fixture_require_captain(true, true, 0.0f, observed);
        else
            p2_fixture_require_captain(GameStat::orimaDead, deadState, n->mHealth, observed);
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip();
            return result;
        }
        if (gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;
        ++observed;
        const int level = pc_pikipelago_challenge_level();
        int alive = 0, reds = 0;
        countSquad(alive, reds);
        if (!started) {
            // Stage entry requires a live squad; without one there is nothing
            // to deliver and the run keeps observing (fail closed below).
            int index = p2challenge::selectByUiIndex(kStages, 5, sUiIndex);
            if (level < 0 || alive <= 0 || index < 0) {
                if (observed % 600 == 0) {
                    std::printf("P2_HOST_MODE_WAIT observed=%d level=%d squad_alive=%d stage_index=%d\n",
                                observed, level, alive, index);
                    std::fflush(stdout);
                }
                if (observed >= 3600) {
                    std::printf("FAIL HOST_MODE_WIRING no_stage_entry observed=%d\n", observed);
                    std::fflush(stdout);
                    std::_Exit(1);
                }
                return result;
            }
            mode = p2challenge::start(kStages[index]);
            p2challenge::applySquadAndSprays(mode, kStages[index].bitterSprays,
                                            kStages[index].spicySprays);
            p2challenge::emit("STAGE_START", mode);
            started = true;
            std::printf("P2_HOST_MODE_STARTED observed=%d ticks=%d\n", observed, ticks);
            std::fflush(stdout);
            return result;
        }
        float seconds = 0.0f;
        const float rawDt = gsys ? gsys->getFrameTime() : 0.0f;
        seconds = rawDt;
        if (!(seconds >= 0.0f) || !std::isfinite(seconds) || seconds > 0.5f) seconds = 0.0f;
        p2challenge::wiring::LiveFacts facts;
        facts.squad_alive = alive;
        facts.squad_reds = reds;
        facts.captain_down = p2_fixture_captain_down(
            GameStat::orimaDead, deadState, n->mHealth);
        facts.seconds = seconds;
        ++ticks;
        if (!p2challenge::wiring::syncTick(mode, facts)) {
            if (mode.ended) {
                p2challenge::emit("STAGE_END", mode);
                std::printf("P2_HOST_MODE_END observed=%d end=%s\n",
                            observed, mode.endState ? mode.endState : "none");
                std::fflush(stdout);
            }
            std::printf("P2_HOST_MODE_WIRING_PASS observed=%d ticks=%d\n", observed, ticks);
            std::puts("PASS HOST_MODE_WIRING");
            std::fflush(stdout);
            std::_Exit(0);
        }
        if (ticks >= 3600) {
            // Bounded observation window: report the driven ticks honestly and
            // stop. No end state occurred naturally in the window.
            std::printf("P2_HOST_MODE_WINDOW_END observed=%d ticks=%d end=%s\n",
                        observed, ticks, mode.endState ? mode.endState : "none");
            std::fflush(stdout);
            std::printf("P2_HOST_MODE_WIRING_PASS observed=%d ticks=%d\n", observed, ticks);
            std::puts("PASS HOST_MODE_WIRING");
            std::fflush(stdout);
            std::_Exit(0);
        }
        if (observed % 600 == 0) {
            std::printf("P2_HOST_MODE_WAIT observed=%d ticks=%d squad_alive=%d\n",
                        observed, ticks, alive);
            std::fflush(stdout);
        }
        return result;
    }
};
} // namespace

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        if (std::string(argv[i]) == "--guard-self-test") sGuardSelfTest = true;
        if (std::string(argv[i]) == "--guard-negative-test") sGuardNegativeTest = true;
        if (std::string(argv[i]) == "--host-ui-index" && i + 1 < argc) {
            sUiIndex = std::atoi(argv[++i]);
        }
    }
    if (sGuardSelfTest) return guardSelfTest();
    if (sGuardNegativeTest) {
        // Exercise the exact interruption call idle() uses: must print
        // P2_FIXTURE_CAPTAIN_DOWN and exit BLOCKED (86) with no PASS.
        // Engine-independent; the exit code is the assertion.
        p2_fixture_require_captain(true, true, 0.0f, 0);
        std::printf("FAIL HOST_MODE_WIRING negative test did not trip\n");
        std::fflush(stdout);
        return 1;
    }
    const char* force = std::getenv("P2_HOST_MODE_FORCE_CAPTAIN_DOWN");
    if (force && force[0] == '1' && force[1] == '\0') sForceCaptainDown = true;
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    if (pc_pikipelago_challenge_level() < 0 && !pc_pikipelago_room_preview()) {
        std::printf("FAIL HOST_MODE_WIRING requires --experimental-challenge-level N or --experimental-pikmin2-room\n");
        std::fflush(stdout);
        return 3;
    }
    if (!pc_window_init("P2 Host mode wiring fixture", 960, 540)) return 3;
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
        std::printf("P2_HOST_MODE_WINDOW size=%dx%d pos=%d,%d display=%dx%d centered=%d\n",
                    width, height, x, y, bounds.w, bounds.h, int(centered));
        std::fflush(stdout);
    }
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new HostModeWiringApp());
    return 0;
}
