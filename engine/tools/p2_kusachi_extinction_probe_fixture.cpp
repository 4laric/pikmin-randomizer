// Kusachi extinction-window probe fixture (lane
// kusachi-extinction-probe-native, #793; downstream consumer #780).
//
// Boots ch_NARI_01kusachi with the p2-kusachi-probe.txt sidecar armed and
// observes a bounded window past the ~13 s extinction point, so the
// engine-emitted P2_KUSACHI_PROBE stream (per-tick navi flags + per-slot
// alive flags) lands in the run log for the consumer verdict. This TU never
// notifies and never judges the extinction: PASS means the probe stream
// flowed from the production TU with no abort and no captain-down.
// Replacement-main harness (scenario main instead of pc_main.cpp; 960x540
// centred window; --experimental-challenge-stage boot), mirroring the
// proven #747/#732 skeletons.
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
bool sForceCaptainDown = false; // env P2_KUSACHI_PROBE_FORCE_CAPTAIN_DOWN=1: negative-path test only

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
            std::printf("FAIL KUSACHI_PROBE selftest row=%d orima=%d dead=%d hp=%.3f got=%d want=%d\n",
                        int(i), int(rows[i].orima), int(rows[i].dead), rows[i].hp,
                        int(down), int(rows[i].expectDown));
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_KUSACHI_PROBE_SELFTEST_PASS rows=%d\n", int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}

class KusachiProbeApp final : public PlugPikiApp {
    int frames = 0, observed = 0;
public:
    int idle() override {
        int result = PlugPikiApp::idle();
        if (++frames > 30000) {
            std::printf("FAIL KUSACHI_PROBE timeout observed=%d\n", observed);
            std::fflush(stdout);
            std::_Exit(2);
        }
        if (!naviMgr || !tekiMgr || !pikiMgr) {
            if (frames % 600 == 0) {
                std::printf("P2_KUSACHI_PROBE_WAIT frames=%d navi_mgr=%d teki_mgr=%d piki_mgr=%d\n",
                            frames, int(naviMgr != nullptr), int(tekiMgr != nullptr),
                            int(pikiMgr != nullptr));
                std::fflush(stdout);
            }
            return result;
        }
        Navi* n = naviMgr->getNavi();
        if (!n) {
            if (frames % 600 == 0) {
                std::printf("P2_KUSACHI_PROBE_WAIT frames=%d navi=0\n", frames);
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
        // Bounded observation window past the ~13 s extinction point. PASS
        // means the production probe stream flowed with no abort and no
        // captain-down; the verdict on cascade-vs-clear belongs to the #780
        // consumer reading the log, not to this harness.
        if (observed >= 1200) {
            std::printf("P2_KUSACHI_PROBE_PASS observed=%d\n", observed);
            std::puts("PASS KUSACHI_PROBE");
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
        if (std::string(argv[i]) == "--guard-negative-test") sGuardNegativeTest = true;
    }
    if (sGuardSelfTest) return guardSelfTest();
    if (sGuardNegativeTest) {
        p2_fixture_require_captain(true, true, 0.0f, 0);
        std::printf("FAIL KUSACHI_PROBE negative test did not trip\n");
        std::fflush(stdout);
        return 1;
    }
    const char* force = std::getenv("P2_KUSACHI_PROBE_FORCE_CAPTAIN_DOWN");
    if (force && force[0] == '1' && force[1] == '\0') sForceCaptainDown = true;
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    if (!pc_pikipelago_room_preview()) {
        std::printf("FAIL KUSACHI_PROBE requires --experimental-pikmin2-room\n");
        std::fflush(stdout);
        return 3;
    }
    if (!pc_window_init("P2 Kusachi extinction probe fixture", 960, 540)) return 3;
    pc_window_center();
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new KusachiProbeApp());
    return 0;
}
