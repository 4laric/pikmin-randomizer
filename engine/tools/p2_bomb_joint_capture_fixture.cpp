// Guarded replacement-main fixture proving otakara joint-matrix capture (#700).
//
// Boots the REAL game-linked engine over the P2 room preview, polls the
// otakara joint-matrix capture hook
// (pc_port/pc_p2_otakara_joint_capture.{h,cpp}) against the live room Chappy
// vehicle every guarded idle tick, and requires an observed joint capture
// under a live squad before PASS. No injection, no simulation: only
// engine-spawned actors are ever observed (the #691 birth-path principle).
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
// Markers: P2_BOMB_JOINT_CAPTURE_* only, plus the hook's own
// P2_OTAKARA_JOINT_CAPTURE / P2_OTAKARA_JOINT_ABSENT markers. Successful boot
// ends with "PASS BOMB_JOINT_CAPTURE" and exit 0. Anything else is FAIL (1),
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
#include "pc_p2_otakara_joint_capture.h"
// Unity-included capture implementation (established #616/#677/#691 pattern
// for provider fixtures): the hook TU is not in any CMake target (shared
// CMakeLists edits are forbidden), so this fixture carries it directly. The
// lane links NO separate hook object, hence no duplicate symbols.
#include "pc_p2_otakara_joint_capture.cpp"
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
bool sForceCaptainDown = false; // env P2_BOMB_JOINT_FORCE_CAPTAIN_DOWN=1: negative-path test only

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
            std::printf("FAIL BOMB_JOINT_CAPTURE selftest row=%d orima=%d dead=%d hp=%.3f got=%d want=%d\n",
                        int(i), int(rows[i].orima), int(rows[i].dead), rows[i].hp,
                        int(down), int(rows[i].expectDown));
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_BOMB_JOINT_CAPTURE_SELFTEST_PASS rows=%d\n", int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}

class BombJointCaptureApp final : public PlugPikiApp {
    int frames = 0, observed = 0;

    bool readyLogged = false;
    int alivePikis() {
        int count = 0;
        Iterator it(pikiMgr);
        CI_LOOP(it) { Creature* p = *it; if (p && p->isAlive()) ++count; }
        return count;
    }
public:
    BombJointCaptureApp() {}
    int idle() override {
        int result = PlugPikiApp::idle();
        if (++frames > 30000) {
            std::printf("FAIL BOMB_JOINT_CAPTURE timeout observed=%d captured=%d\n",
                        observed, int(pc_p2_otakara_joint_capture_ready()));
            std::fflush(stdout);
            std::_Exit(2);
        }
        if (!naviMgr || !tekiMgr || !pikiMgr) {
            if (frames % 600 == 0) {
                std::printf("P2_BOMB_JOINT_CAPTURE_WAIT frames=%d navi_mgr=%d teki_mgr=%d piki_mgr=%d\n",
                            frames, int(naviMgr != nullptr), int(tekiMgr != nullptr),
                            int(pikiMgr != nullptr));
                std::fflush(stdout);
            }
            return result;
        }
        Navi* n = naviMgr->getNavi();
        if (!n) {
            if (frames % 600 == 0) {
                std::printf("P2_BOMB_JOINT_CAPTURE_WAIT frames=%d navi=0\n", frames);
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
        // Poll the capture hook against live engine actors (never injected).
        // PASS requires a real observed joint capture plus a live squad.
        pc_p2_otakara_joint_capture_poll();
        const bool captured = pc_p2_otakara_joint_capture_ready();
        if (!readyLogged && observed % 600 == 0) {
            std::printf("P2_BOMB_JOINT_CAPTURE_WAIT observed=%d captured=%d actors=%d joints=%d\n",
                        observed, int(captured),
                        pc_p2_otakara_joint_capture_actor_count(),
                        pc_p2_otakara_joint_capture_joint_count());
            std::fflush(stdout);
        }
        if (observed >= 600 && !readyLogged) {
            readyLogged = true;
            std::printf("P2_BOMB_JOINT_CAPTURE_READY observed=%d captured=%d actors=%d joints=%d generator=%u\n",
                        observed, int(captured),
                        pc_p2_otakara_joint_capture_actor_count(),
                        pc_p2_otakara_joint_capture_joint_count(),
                        pc_p2_otakara_joint_capture_last_generator());
            std::fflush(stdout);
        }
        if (readyLogged) {
            const int alive = alivePikis();
            if (alive > 0 && captured) {
                std::printf("P2_BOMB_JOINT_CAPTURE_PASS captured=%d actors=%d joints=%d generator=%u squad_alive=%d observed=%d\n",
                            int(captured),
                            pc_p2_otakara_joint_capture_actor_count(),
                            pc_p2_otakara_joint_capture_joint_count(),
                            pc_p2_otakara_joint_capture_last_generator(), alive, observed);
                std::puts("PASS BOMB_JOINT_CAPTURE");
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
            std::printf("FAIL BOMB_JOINT_CAPTURE negative test did not trip\n");
            std::fflush(stdout);
            return 1;
        }
    }
    if (sGuardSelfTest) return guardSelfTest();
    const char* force = std::getenv("P2_BOMB_JOINT_FORCE_CAPTAIN_DOWN");
    if (force && force[0] == 49 && force[1] == 0) sForceCaptainDown = true;
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    if (!pc_pikipelago_room_preview()) {
        std::printf("FAIL BOMB_JOINT_CAPTURE requires --experimental-pikmin2-room\n");
        std::fflush(stdout);
        return 3;
    }
    if (!pc_window_init("P2 bomb joint capture fixture", 960, 540)) return 3;
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
        std::printf("P2_BOMB_JOINT_CAPTURE_WINDOW size=%dx%d pos=%d,%d display=%dx%d centered=%d\n",
                    width, height, x, y, bounds.w, bounds.h, int(centered));
        std::fflush(stdout);
    }
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    pc_p2_otakara_joint_capture_setup();
    gsys->run(new BombJointCaptureApp());
    return 0;
}
