// Tutorial-2 descend-policy fixture (lane tutorial2-descend-policy-native,
// #757; downstream consumer #747).
//
// Proves staged tutorial floors 3-8 boot through the extended engine path:
// entry P2_CAVE_ENTRY_4 admitted by pc_p2_cave.cpp, P2_CAVE_READY observed,
// the restored squad alive under a guarded captain, and the engine-emitted
// P2_TUTORIAL2_DESCEND_POLICY line proving the descend decision in-band.
// Replacement-main harness (scenario main instead of pc_main.cpp; 960x540
// centred window; --experimental-pikmin2-room boot), mirroring the proven
// #747/#691 skeletons. This TU never notifies: all markers below are
// fixture-observed engine lines.
//
// Modes: --floor N (3..8) boots floor N and passes on READY + live squad;
// --check-entry <file> validates an entry header through the production
// pc_p2_tutorial2_entry_check (no engine, no abort) for the fail-closed
// battery; --guard-self-test / --guard-negative-test exercise the #632
// guard without booting.
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
#include "pc_p2_cave.h"
#include "pc_window.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "teki.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <string>

// Production entry-header validator (defined ONLY in the pikmin_pc
// pc_p2_cave.cpp object; extern here so this TU cannot satisfy it).
extern bool pc_p2_tutorial2_entry_check(const char* path, int* floorOut);

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
bool sForceCaptainDown = false; // env P2_TUTORIAL2_DESCEND_FORCE_CAPTAIN_DOWN=1: negative-path test only
int sWantFloor = 0;
const char* sCheckEntry = nullptr;

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
            std::printf("FAIL TUTORIAL2_DESCEND selftest row=%d orima=%d dead=%d hp=%.3f got=%d want=%d\n",
                        int(i), int(rows[i].orima), int(rows[i].dead), rows[i].hp,
                        int(down), int(rows[i].expectDown));
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_TUTORIAL2_DESCEND_SELFTEST_PASS rows=%d\n", int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}

class Tutorial2DescendApp final : public PlugPikiApp {
    int frames = 0, observed = 0;
    bool entrySeen = false;
    int alivePikis() {
        int count = 0;
        Iterator it(pikiMgr);
        CI_LOOP(it) { Creature* p = *it; if (p && p->isAlive()) ++count; }
        return count;
    }
public:
    int idle() override {
        int result = PlugPikiApp::idle();
        if (++frames > 30000) {
            std::printf("FAIL TUTORIAL2_DESCEND timeout want_floor=%d entry_seen=%d observed=%d\n",
                        sWantFloor, int(entrySeen), observed);
            std::fflush(stdout);
            std::_Exit(2);
        }
        if (!naviMgr || !tekiMgr || !pikiMgr) {
            if (frames % 600 == 0) {
                std::printf("P2_TUTORIAL2_DESCEND_WAIT frames=%d navi_mgr=%d teki_mgr=%d piki_mgr=%d\n",
                            frames, int(naviMgr != nullptr), int(tekiMgr != nullptr),
                            int(pikiMgr != nullptr));
                std::fflush(stdout);
            }
            return result;
        }
        Navi* n = naviMgr->getNavi();
        if (!n) {
            if (frames % 600 == 0) {
                std::printf("P2_TUTORIAL2_DESCEND_WAIT frames=%d navi=0 floor=%d\n",
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
        if (floor <= 0 && observed % 600 == 0) {
            std::printf("P2_TUTORIAL2_DESCEND_WAIT observed=%d floor=0 alive=%d\n",
                        observed, alivePikis());
            std::fflush(stdout);
        }
        if (floor == sWantFloor && !entrySeen) {
            entrySeen = true;
            std::printf("P2_TUTORIAL2_DESCEND_ENTRY_READY floor=%d observed=%d\n", floor, observed);
            std::fflush(stdout);
        }
        if (entrySeen) {
            const int alive = alivePikis();
            if (alive > 0) {
                std::printf("P2_TUTORIAL2_DESCEND_PASS floor=%d squad_alive=%d observed=%d\n",
                            floor, alive, observed);
                std::puts("PASS TUTORIAL2_DESCEND");
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
        if (std::string(argv[i]) == "--guard-negative-test") sGuardNegativeTest = true;
        if (std::string(argv[i]) == "--floor" && i + 1 < argc) sWantFloor = std::atoi(argv[++i]);
        if (std::string(argv[i]) == "--check-entry" && i + 1 < argc) sCheckEntry = argv[++i];
    }
    if (sGuardSelfTest) return guardSelfTest();
    if (sGuardNegativeTest) {
        p2_fixture_require_captain(true, true, 0.0f, 0);
        std::printf("FAIL TUTORIAL2_DESCEND negative test did not trip\n");
        std::fflush(stdout);
        return 1;
    }
    if (sCheckEntry) {
        // Engine-free header validation through the production mapping.
        int floor = 0;
        const bool ok = pc_p2_tutorial2_entry_check(sCheckEntry, &floor);
        std::printf("P2_TUTORIAL2_ENTRY_CHECK path=%s admitted=%d floor=%d\n",
                    sCheckEntry, int(ok), floor);
        std::fflush(stdout);
        return ok ? 0 : 1;
    }
    if (sWantFloor < 3 || sWantFloor > 8) {
        std::printf("FAIL TUTORIAL2_DESCEND want_floor=%d outside 3-8\n", sWantFloor);
        std::fflush(stdout);
        return 1;
    }
    const char* force = std::getenv("P2_TUTORIAL2_DESCEND_FORCE_CAPTAIN_DOWN");
    if (force && force[0] == '1' && force[1] == '\0') sForceCaptainDown = true;
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    if (!pc_pikipelago_room_preview()) {
        std::printf("FAIL TUTORIAL2_DESCEND requires --experimental-pikmin2-room\n");
        std::fflush(stdout);
        return 3;
    }
    if (!pc_window_init("P2 Tutorial2 descend fixture", 960, 540)) return 3;
    pc_window_center();
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new Tutorial2DescendApp());
    return 0;
}
