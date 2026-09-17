// Bomb birth hook call-site fixture (lane bomb-birth-hook-callsite-native,
// #732; downstream consumer #573).
//
// Proves the PRODUCTION engine fires pc_p2_bomb_birth_hook_notify on a real
// bomb birth. Unlike the engine-free fixtures, this TU NEITHER defines the
// notifier NOR calls it: the only definition linked is the strong one in
// pikmin2-research/src/plugProjectYamashitaU/generalEnemyMgr.cpp (a
// pikmin_pc object), and the only caller is that TU's
// pc_p2_general_enemy_mgr_birth entry, declared extern below. The lane
// runner links this TU against the private pikmin_pc graph (all pikmin_pc
// objects except pc_main) without editing shared build files.
//
// Scenario (mirrors the proven #691 engine harness): boot the engine with
// --experimental-pikmin2-room, guard first on every idle tick, census live
// tekiMgr actors, run pc_p2_bomb_mgr_birth_setup() against the
// p2-bomb-mgr-birth.txt sidecar, then offer each live registered carrier to
// the PRODUCTION call-site entry with the retail BombOtakara ID (93). A
// real engine-driven birth (P2_BOMB_ENGINE_BIRTH ... engine_driven=1)
// followed by P2_BOMB_BIRTH_HOOK_NOTIFY enemyID=93 -- both emitted from
// production TUs -- is the PASS. A non-bomb ID (1) is offered once to prove
// the fail-closed refuse arm; unregistered actors simply do not birth.
//
// Replacement-main convention mirrors tools/p2_bomb_engine_birth_fixture.cpp
// (scenario main instead of pc_main.cpp; 960x540 centred window;
// --experimental-pikmin2-room boot).
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
#include "pc_p2_bomb_mgr_birth.h"
#include "pc_window.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "teki.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <string>

// Production call-site entry (defined ONLY in the pikmin_pc
// generalEnemyMgr.cpp object; extern here so this TU cannot satisfy it).
extern bool pc_p2_general_enemy_mgr_birth(int enemyID, Teki* actor);
// Free-function manager seam (defined at namespace scope in
// pc_port/pc_p2_bomb_mgr_birth.cpp; the #726 header nests these inside the
// class body, so redeclare here instead of editing that header).
extern P2BombMgr& pc_p2_bomb_mgr_birth_manager();
extern void pc_p2_bomb_mgr_birth_setup();
extern bool pc_p2_bomb_mgr_birth_ready();

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
bool sForceCaptainDown = false; // env P2_BOMB_CALLSITE_FORCE_CAPTAIN_DOWN=1: negative-path test only

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
            std::printf("FAIL BOMB_CALLSITE selftest row=%d orima=%d dead=%d hp=%.3f got=%d want=%d\n",
                        int(i), int(rows[i].orima), int(rows[i].dead), rows[i].hp,
                        int(down), int(rows[i].expectDown));
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_BOMB_CALLSITE_SELFTEST_PASS rows=%d\n", int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}

class BombCallsiteApp final : public PlugPikiApp {
    int frames = 0, observed = 0, births = 0, census = 0, hooks = 0;
    bool setupDone = false, negativeDone = false;
public:
    int idle() override {
        int result = PlugPikiApp::idle();
        if (++frames > 30000) {
            std::printf("FAIL BOMB_CALLSITE timeout observed=%d births=%d hooks=%d\n",
                        observed, births, hooks);
            std::fflush(stdout);
            std::_Exit(2);
        }
        if (!naviMgr || !tekiMgr || !pikiMgr) {
            if (frames % 600 == 0) {
                std::printf("P2_BOMB_CALLSITE_WAIT frames=%d navi_mgr=%d teki_mgr=%d piki_mgr=%d\n",
                            frames, int(naviMgr != nullptr), int(tekiMgr != nullptr),
                            int(pikiMgr != nullptr));
                std::fflush(stdout);
            }
            return result;
        }
        Navi* n = naviMgr->getNavi();
        if (!n) {
            if (frames % 600 == 0) {
                std::printf("P2_BOMB_CALLSITE_WAIT frames=%d navi=0\n", frames);
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
        if (!setupDone) {
            setupDone = true;
            pc_p2_bomb_mgr_birth_setup();
            std::printf("P2_BOMB_CALLSITE_SETUP ready=%d\n", int(pc_p2_bomb_mgr_birth_ready()));
            std::fflush(stdout);
        }
        if (!negativeDone) {
            // Fail-closed negative: a non-bomb ID must be refused before any
            // poll runs. Deterministic; proves the arm, stages nothing.
            negativeDone = true;
            if (pc_p2_general_enemy_mgr_birth(1, nullptr)) {
                std::printf("FAIL BOMB_CALLSITE non_bomb_id_accepted\n");
                std::fflush(stdout);
                std::_Exit(1);
            }
            std::printf("P2_BOMB_CALLSITE_NEGATIVE_PASS refused_id=1\n");
            std::fflush(stdout);
        }
        if (census < 64) {
            Iterator it(tekiMgr);
            CI_LOOP(it) {
                if (census >= 64) break;
                Teki* actor = static_cast<Teki*>(*it);
                if (!actor) continue;
                const unsigned gen = (actor->mGenerator != nullptr)
                    ? actor->mGenerator->_70 : 0u;
                Vector3f pos = actor->getPosition();
                std::printf("P2_BOMB_CALLSITE_CENSUS idx=%d generator=%u type=%d alive=%d "
                            "x=%.3f y=%.3f z=%.3f\n",
                            census, gen, actor->mTekiType, int(actor->isAlive()),
                            pos.x, pos.y, pos.z);
                ++census;
            }
            std::fflush(stdout);
        }
        // Call-site drive: every live registered carrier is offered to the
        // PRODUCTION entry with the retail BombOtakara ID (93). The entry
        // routes to the real engine birth seam and notifies on a real birth;
        // unregistered actors simply do not birth. This TU never notifies.
        Iterator scan(tekiMgr);
        CI_LOOP(scan) {
            Teki* actor = static_cast<Teki*>(*scan);
            if (!actor || !actor->mGenerator || !actor->isAlive()) continue;
            const unsigned gen = actor->mGenerator->_70;
            if (!pc_p2_bomb_mgr_birth_manager().isRegistered(gen)) continue;
            if (pc_p2_general_enemy_mgr_birth(93, actor)) {
                ++births;
                ++hooks;
            }
        }
        if (hooks > 0) {
            std::printf("P2_BOMB_CALLSITE_PASS births=%d hooks=%d observed=%d\n",
                        births, hooks, observed);
            std::puts("PASS BOMB_BIRTH_HOOK_CALLSITE");
            std::fflush(stdout);
            std::_Exit(0);
        }
        if (observed >= 3600 && hooks == 0) {
            std::printf("FAIL BOMB_CALLSITE no_hook_observed observed=%d births=%d\n",
                        observed, births);
            std::fflush(stdout);
            std::_Exit(1);
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
        std::printf("FAIL BOMB_CALLSITE negative test did not trip\n");
        std::fflush(stdout);
        return 1;
    }
    const char* force = std::getenv("P2_BOMB_CALLSITE_FORCE_CAPTAIN_DOWN");
    if (force && force[0] == '1' && force[1] == '\0') sForceCaptainDown = true;
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    if (!pc_pikipelago_room_preview()) {
        std::printf("FAIL BOMB_CALLSITE requires --experimental-pikmin2-room\n");
        std::fflush(stdout);
        return 3;
    }
    if (!pc_window_init("P2 Bomb birth hook callsite fixture", 960, 540)) return 3;
    pc_window_center();
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new BombCallsiteApp());
    return 0;
}
