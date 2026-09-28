// Guarded P2 challenge host-runtime fixture (lane
// challenge-hostmode-engine-hook-native, #710).
//
// Replacement-main harness that boots the REAL engine with
// --experimental-pikmin2-room --experimental-challenge-stage <cave_id> and
// enforces captain safety #632 on every idle tick. It does NOT duplicate the
// engine bridge: P2_CHALLENGE_MODE_BOOT/_TICK/_DONE plus the wiring tick
// stream are emitted by the in-engine bridge (pc_p2_challenge_runtime.cpp,
// driven from pc_bbft_update) once a valid stage row is selected. This
// fixture only guards, bounds, and reports the run.
//
// Replacement-main convention mirrors tools/p2_cave_guarded_boot_fixture.cpp
// and tools/p2_host_mode_wiring_fixture.cpp (scenario main instead of
// pc_main.cpp; 960x540 centred window; --experimental-pikmin2-room boot).
// Promotion to a first-class CMake target is a shared-owner follow-up; the
// lane links this TU against the private pikmin_pc graph without editing
// shared build files.
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
#include "pc_p2_preview.h"
#include "pc_p2_challenge_runtime.h"
#include "pc_window.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "teki.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
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
bool sForceCaptainDown = false; // env P2_CHALLENGE_HOST_RUNTIME_FORCE_CAPTAIN_DOWN=1: negative-path test only
int sTargetTicks = 600; // observed idle ticks before PASS (override --ticks N)

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
            std::printf("FAIL CHALLENGE_HOST_RUNTIME selftest row=%d orima=%d dead=%d hp=%.3f got=%d want=%d\n",
                        int(i), int(rows[i].orima), int(rows[i].dead), rows[i].hp,
                        int(down), int(rows[i].expectDown));
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_CHALLENGE_HOST_RUNTIME_SELFTEST_PASS rows=%d\n", int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}

class ChallengeHostRuntimeApp final : public PlugPikiApp {
    int frames = 0, observed = 0, waitMarks = 0;
public:
    int idle() override {
        int result = PlugPikiApp::idle();
        if (++frames > 30000) {
            std::printf("FAIL CHALLENGE_HOST_RUNTIME timeout observed=%d\n", observed);
            std::fflush(stdout);
            std::_Exit(2);
        }
        if (!naviMgr || !tekiMgr || !pikiMgr) {
            if (frames % 600 == 0) {
                std::printf("P2_CHALLENGE_HOST_RUNTIME_WAIT frames=%d navi_mgr=%d teki_mgr=%d piki_mgr=%d\n",
                            frames, int(naviMgr != nullptr), int(tekiMgr != nullptr),
                            int(pikiMgr != nullptr));
                std::fflush(stdout);
            }
            return result;
        }
        Navi* n = naviMgr->getNavi();
        if (!n) {
            if (frames % 600 == 0) {
                std::printf("P2_CHALLENGE_HOST_RUNTIME_WAIT frames=%d navi=0\n", frames);
                std::fflush(stdout);
            }
            return result;
        }
        // Guard FIRST: immediately after engine idle, before any observation.
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
        // The engine bridge (pc_bbft_update -> registered update) emits
        // P2_CHALLENGE_MODE_BOOT/_TICK/_DONE into this same log; this fixture
        // only bounds the guarded observation window. PASS here means the
        // window completed under guard, never that content was accepted.
        if (observed >= sTargetTicks) {
            std::printf("PASS CHALLENGE_HOST_RUNTIME observed=%d\n", observed);
            std::fflush(stdout);
            std::_Exit(0);
        }
        if (observed % 600 == 0 && waitMarks < 48) {
            ++waitMarks;
            std::printf("P2_CHALLENGE_HOST_RUNTIME_WAIT observed=%d\n", observed);
            std::fflush(stdout);
        }
        return result;
    }
};
} // namespace

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        if (std::string(argv[i]) == "--guard-self-test") sGuardSelfTest = true;
        else if (std::string(argv[i]) == "--guard-negative-test") sGuardNegativeTest = true;
        else if (std::string(argv[i]) == "--ticks" && i + 1 < argc) sTargetTicks = std::atoi(argv[++i]);
    }
    if (sGuardSelfTest) return guardSelfTest();
    if (sGuardNegativeTest) {
        // Exercise the exact interruption call idle() uses: must print
        // P2_FIXTURE_CAPTAIN_DOWN and exit BLOCKED (86) with no PASS.
        // Engine-independent; the exit code is the assertion.
        p2_fixture_require_captain(true, true, 0.0f, 0);
        std::printf("FAIL CHALLENGE_HOST_RUNTIME negative test did not trip\n");
        std::fflush(stdout);
        return 1;
    }
    const char* force = std::getenv("P2_CHALLENGE_HOST_RUNTIME_FORCE_CAPTAIN_DOWN");
    if (force && force[0] == '1' && force[1] == '\0') sForceCaptainDown = true;
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    if (!pc_pikipelago_room_preview()) {
        std::printf("FAIL CHALLENGE_HOST_RUNTIME requires --experimental-pikmin2-room\n");
        std::fflush(stdout);
        return 3;
    }
    {
        P2ChallengeStageParams params{};
        if (!p2_challenge_stage_params(params)) {
            std::printf("FAIL CHALLENGE_HOST_RUNTIME requires --experimental-challenge-stage <valid-key>\n");
            std::fflush(stdout);
            return 3;
        }
        std::printf("P2_CHALLENGE_HOST_RUNTIME_STAGE cave=%s ui_index=%d floors=%d\n",
                    params.caveId, params.uiIndex, params.floors);
        std::fflush(stdout);
    }
    if (!pc_window_init("P2 Challenge host runtime fixture", 960, 540)) return 3;
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
        std::printf("P2_CHALLENGE_HOST_RUNTIME_WINDOW size=%dx%d pos=%d,%d display=%dx%d centered=%d\n",
                    width, height, x, y, bounds.w, bounds.h, int(centered));
        std::fflush(stdout);
    }
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new ChallengeHostRuntimeApp());
    return 0;
}
