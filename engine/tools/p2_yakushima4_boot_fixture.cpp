// yakushima_4 pre-stage boot-stall probe fixture (lane yakushima4-boot-stall-native-fix, #673).
//
// Purpose: boot the REAL game-linked engine over a caller-supplied yakushima_4
// input package and prove the pre-stage stall is no longer silent. Before the
// #673 fix, pc_p2_cave_setup() returned with no marker when the room preview
// was unavailable or p2-cave-entry.txt was missing, so the guarded boot stalled
// silently after texture-filtering init with no P2_CAVE_READY. The fix adds
// P2_CAVE_SETUP_PROBE / P2_CAVE_SETUP_BLOCK markers; this fixture requires the
// run to end in either P2_CAVE_READY (entry applied) or an explicit
// P2_CAVE_SETUP_BLOCK reason=... (diagnosed). A silent stall is FAIL.
//
// Room-graph consumption: when entry reaches the transition shape, the engine
// emits P2_CAVE_MARKER_DRAW from pc_p2_cave_draw_transition() (pc_p2_cave.cpp);
// the run wrapper asserts it for the collision/room-graph claim.
//
// Ordering contract (#632): the canonical captain guard runs on EVERY idle
// tick immediately after the base engine idle and BEFORE any readiness
// observation or PASS. CAPTAIN_DOWN exits BLOCKED (86) with no PASS. The guard
// never changes game state. Vendored verbatim-equivalent from
// scripts/p2_fixture_captain_guard.h (sha256
// d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474).
//
// Markers: P2_YAKUSHIMA4_BOOT_* only, plus the engine's own
// P2_CAVE_SETUP_PROBE / P2_CAVE_SETUP_BLOCK / P2_CAVE_READY / P2_CAVE_MARKER_DRAW.
// PASS YAKUSHIMA4_BOOT + exit 0 on diagnosed-or-ready; FAIL (1), BLOCKED (86),
// or timeout (2) otherwise. No PASS without observed evidence.
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
#include "pc_p2_cave.h"
#include "pc_p2_preview.h"
#include "pc_window.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

inline bool p2_fixture_captain_down(bool orimaDead, bool deadState, float hp) {
    return orimaDead || deadState || !std::isfinite(hp) || hp <= 1.0f;
}
inline void p2_fixture_require_captain(bool orimaDead, bool deadState, float hp, int tick) {
    if (!p2_fixture_captain_down(orimaDead, deadState, hp)) return;
    std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f orima_dead=%d dead_state=%d outcome=BLOCKED\n",
                tick, hp, int(orimaDead), int(deadState));
    std::fflush(nullptr);
    std::_Exit(86);
}

namespace {
bool sGuardSelfTest = false;
bool sForceCaptainDown = false;

int guardSelfTest() {
    struct Row { bool orima; bool dead; float hp; bool expectDown; };
    const Row rows[] = {
        {false, false, 100.0f, false}, {false, false, 1.5f, false},
        {false, false, 1.0f, true},    {false, false, 0.0f, true},
        {false, true, 100.0f, true},   {true, false, 100.0f, true},
        {true, true, 0.0f, true},
    };
    for (size_t i = 0; i < sizeof(rows) / sizeof(rows[0]); ++i) {
        if (p2_fixture_captain_down(rows[i].orima, rows[i].dead, rows[i].hp) != rows[i].expectDown) {
            std::printf("FAIL YAKUSHIMA4_BOOT selftest row=%d\n", int(i));
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_YAKUSHIMA4_GUARD_SELFTEST_PASS rows=%d\n", int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}

// A diagnosed setup returns a marker naming the exact blocked precondition;
// without the #673 fix this was a silent return and the run stalled.
enum class SetupOutcome { None, Ready, Blocked };
SetupOutcome sOutcome = SetupOutcome::None;
std::string sBlockReason;

class Yakushima4BootApp final : public PlugPikiApp {
    int frames = 0, observed = 0;
public:
    int idle() override {
        int result = PlugPikiApp::idle();
        if (++frames > 30000) {
            std::printf("FAIL YAKUSHIMA4_BOOT timeout outcome=%d\n", int(sOutcome));
            std::fflush(stdout);
            std::_Exit(2);
        }
        if (!naviMgr || !tekiMgr || !pikiMgr) {
            if (frames % 600 == 0) {
                std::printf("P2_YAKUSHIMA4_BOOT_WAIT frames=%d navi_mgr=%d piki_mgr=%d\n",
                            frames, int(naviMgr != nullptr), int(pikiMgr != nullptr));
                std::fflush(stdout);
            }
            return result;
        }
        Navi* n = naviMgr->getNavi();
        if (!n) return result;
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
        // pc_p2_cave_setup() runs as part of the preview entry path; the
        // outcome is read from the engine state it leaves (floor applied) and
        // from the engine's own SETUP_BLOCK markers captured in the run log.
        if (sOutcome == SetupOutcome::None && pc_p2_cave_floor() > 0) {
            sOutcome = SetupOutcome::Ready;
            std::printf("P2_YAKUSHIMA4_BOOT_ENTRY_READY floor=%d observed=%d\n",
                        pc_p2_cave_floor(), observed);
            std::fflush(stdout);
        }
        if (sOutcome == SetupOutcome::Ready) {
            std::printf("P2_YAKUSHIMA4_BOOT_DIAGNOSED outcome=ready floor=%d observed=%d\n",
                        pc_p2_cave_floor(), observed);
            std::puts("PASS YAKUSHIMA4_BOOT");
            std::fflush(stdout);
            std::_Exit(0);
        }
        return result;
    }
};
} // namespace

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        if (std::string(argv[i]) == "--guard-self-test") sGuardSelfTest = true;
        if (std::string(argv[i]) == "--guard-negative-test") {
            p2_fixture_require_captain(true, true, 0.0f, 0);
            std::printf("FAIL YAKUSHIMA4_BOOT negative test did not trip\n");
            std::fflush(stdout);
            return 1;
        }
    }
    if (sGuardSelfTest) return guardSelfTest();
    const char* force = std::getenv("P2_YAKUSHIMA4_BOOT_FORCE_CAPTAIN_DOWN");
    if (force && force[0] == 49 && force[1] == 0) sForceCaptainDown = true;
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    if (!pc_pikipelago_room_preview()) {
        std::printf("FAIL YAKUSHIMA4_BOOT requires --experimental-pikmin2-room\n");
        std::fflush(stdout);
        return 3;
    }
    if (!pc_window_init("P2 yakushima4 boot probe", 960, 540)) return 3;
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
        std::printf("P2_YAKUSHIMA4_BOOT_WINDOW size=%dx%d pos=%d,%d centered=%d\n",
                    width, height, x, y, int(centered));
        std::fflush(stdout);
    }
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new Yakushima4BootApp());
    return 0;
}
