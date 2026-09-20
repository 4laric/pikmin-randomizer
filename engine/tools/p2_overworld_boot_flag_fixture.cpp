// Private game-linked guarded fixture for the overworld course boot flag (issue #767).
//
// Replacement-main harness (scenario main instead of pc_main.cpp): parses
// --experimental-overworld-course <id> through the new additive module,
// registers the course, boots the preview room, and observes guarded ticks
// with receipt-parseable markers. Fail-closed: unknown or missing course
// exits 2; --allow-unguarded exits 2 (unguarded runs refused). No
// engine/shared edits; no pc_bbft.cpp/.h or CMakeLists.txt changes (that
// wiring is the serialized follow-on after #755 via #186 + integrator).
// Captain safety (#632): vendored guard predicate checked before every
// observed tick; CAPTAIN_DOWN exits BLOCKED (86).
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "gl/pc_opengl.h"
#include "App.h"
#include "Node.h"
#include "Graphics.h"
#include "MapMgr.h"
#include "Matrix4f.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "PikiMgr.h"
#include "MoviePlayer.h"
#include "Shape.h"
#include "system.h"
#include "gameflow.h"
#include "GameStat.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_window.h"
#include "pc_p2_preview.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "pc_p2_overworld_course.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace {
// Canonical guard predicate, vendored verbatim semantics from
// scripts/p2_fixture_captain_guard.h (sha256 d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474):
// a replacement-main TU cannot include a Python-tree script header at
// native build time.
inline bool boot_flag_captain_down(bool orimaDead, bool deadState, float hp) {
    return orimaDead || deadState || !std::isfinite(hp) || hp <= 1.0f;
}
void require(bool value, const char* message) {
    if (!value) {
        std::printf("FAIL OVERWORLD_BOOT_FLAG %s\\n", message);
        std::fflush(stdout);
        std::_Exit(1);
    }
}
class BootFlagApp final : public PlugPikiApp {
    int frames = 0, observed = 0;
    bool announced = false;
public:
    int idle() override {
        int result = PlugPikiApp::idle();
        require(++frames < 3600, "timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip();
            return result;
        }
        if (gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;
        if (!naviMgr || !pikiMgr || !mapMgr) return result;
        Navi* navi = naviMgr->getNavi();
        if (!navi) return result;
        if (boot_flag_captain_down(GameStat::orimaDead, !navi->isAlive(), navi->mHealth)) {
            std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f orima_dead=%d dead_state=%d outcome=BLOCKED\\n",
                        observed, (double)navi->mHealth, (int)GameStat::orimaDead, (int)(!navi->isAlive()));
            std::fflush(stdout);
            std::_Exit(86);
        }
        ++observed;
        if (!announced) {
            announced = true;
            std::printf("P2_OVERWORLD_COURSE_OBSERVED course=%s index=%d tick=%d\\n",
                        pc_pikipelago_overworld_course_id(), pc_pikipelago_overworld_course(), observed);
            std::fflush(stdout);
        }
        if (observed >= 30) {
            std::printf("PASS OVERWORLD_BOOT_FLAG course=%s ticks=%d\\n",
                        pc_pikipelago_overworld_course_id(), observed);
            std::fflush(stdout);
            std::_Exit(0);
        }
        return result;
    }
};
}

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        if (!std::strcmp(argv[i], "--allow-unguarded")) {
            std::fprintf(stderr, "unguarded runs refused\\n");
            return 2;
        }
    }
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    pc_pikipelago_overworld_course_parse(argc, argv);
    const char* course = pc_pikipelago_overworld_course_id();
    if (!course) {
        std::fprintf(stderr, "requires --experimental-overworld-course <tutorial|forest|yakushima|last>\\n");
        return 2;
    }
    require(pc_pikipelago_overworld_course_register(), "course registration");
    std::printf("P2_OVERWORLD_COURSE_FLAG course=%s index=%d\\n", course, pc_pikipelago_overworld_course());
    std::printf("P2_OVERWORLD_COURSE_REGISTERED course=%s\\n", course);
    std::fflush(stdout);
    require(pc_pikipelago_room_preview(), "requires --experimental-pikmin2-room");
    require(pc_window_init("Overworld course boot flag fixture", 960, 540), "window init");
    std::printf("P2_OVERWORLD_BOOT_FLAG_WINDOW width=960 height=540 centred=1\\n");
    std::fflush(stdout);
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new BootFlagApp());
    return 0;
}
