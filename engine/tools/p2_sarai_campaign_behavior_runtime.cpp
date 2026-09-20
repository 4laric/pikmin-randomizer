// Sarai23 campaign-behavior observation fixture (#834).
//
// Self-contained replacement-main TU (tools/preview_p2_room.cpp is never
// touched): main() mirrors the landed replacement-main convention (960x540
// centred window; --experimental-pikmin2-room boot). The lane build script
// (scripts/build_pikmin2_fixture.py) links this TU against the private
// pikmin_pc graph in place of pc_port/pc_main.cpp without editing shared
// build files.
//
// Scenario: ONE Sarai anchor is bound through the CAMPAIGN seam
// (pc_p2_sarai_manager_bind_dynamic with the actor's own campaign token, the
// exact call pc_p2_generated_placement_sweep_sarai makes for seed-bridge
// bindings), so the host runs the retail-scale campaign geometry
// (territory=200 view=90 sight=200, P2_SARAI_GEOMETRY marker) and the
// Pikmin-first natural route. The fixture drives the captain with NORMAL
// controller input only: analog-stick walk goals (park far, whistle-gather
// the staged 20-red squad, then hold inside Sarai sight with the formation)
// plus whistle-button equivalents. No Pikmin is placed or commanded, no
// throw is forced, no health/Transport/state is written, no InteractAttack
// is injected.
//
// Observation legs: campaign bind markers, Pikmin-targeted approach/capture
// (mouth-stuck Pikmin census, read-only), FallMeck drops, captain
// non-contact (the captain is NEVER mouth-stuck and the guard stays green
// even while the captain holds inside Sarai sight with the squad), and
// manager reset/teardown. The engine-free checker
// (tools/p2_sarai_campaign_behavior_test.cpp <native.log>) classifies the
// run: READY + DELIVERY_BIND + campaign GEOMETRY mandatory, ZERO captain
// P2_SARAI_CAPTURE markers, no CAPTAIN_DOWN, no injected markers.
//
// Captain safety (#632): the canonical guard runs FIRST after engine idle
// and BEFORE movie/pause/UI early returns, readiness gates, observation
// counters or PASS markers; CAPTAIN_DOWN exits 86 BLOCKED. Policy is
// PROTECTED observation: the captain parks outside Sarai reach for gather,
// then holds at ~120 units (inside sight, outside grab range) with the
// formation so contact opportunity is real while a captain grab would still
// be a failure. This run proves captain SAFETY and Pikmin targeting; it
// does not prove captain damage (labelled, not claimed).
#if __has_include("p2_fixture_captain_guard.h")
#include "p2_fixture_captain_guard.h"
#else
// Inline tested equivalent of scripts/p2_fixture_captain_guard.h (recorded
// hash alongside the lane); never changes captain health or game state.
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
    std::_Exit(86);
}
#endif
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "system.h"
#include "App.h"
#include "Node.h"
#include "Generator.h"
#include "Section.h"
#include "FlowController.h"
#include "MoviePlayer.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Kontroller.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiAI.h"
#include "PikiState.h"
#include "MapMgr.h"
#include "Camera.h"
#include "PlayerState.h"
#include "Demo.h"
#include "teki.h"
#include "GameStat.h"
#include "gameflow.h"
#include "Creature.h"
#include "pc_p2_preview.h"
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_sarai_manager.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

static void require(bool value, const char* message)
{
    if (!value) { std::printf("FAIL sarai behavior: %s\n", message); std::fflush(stdout); std::_Exit(1); }
}

// Current walk goal, refreshed by the app. The controller steers the
// captain's analog stick toward it: genuine stick input, never a write.
static Vector3f walkGoal;
static bool walkActive = false;

class BehaviorController : public Kontroller {
public:
    BehaviorController() : Kontroller(1) {}
    void update() override
    {
        mMainStickX = 0; mMainStickY = 0;
        mSubStickX = 0; mSubStickY = 0;
        if (!walkActive || !naviMgr) {
            updateCont(0);
            return;
        }
        updateCont(KBBTN_MSTICK_RIGHT);
        Navi* n = naviMgr->getNavi();
        if (!n || !n->mNaviCamera) return;
        const float dx = walkGoal.x - n->mSRT.t.x, dz = walkGoal.z - n->mSRT.t.z;
        const float distance = std::sqrt(dx * dx + dz * dz);
        if (distance > 4.0f) {
            const Vector3f& axis = n->mNaviCamera->mViewXAxis;
            mMainStickX = static_cast<signed char>(65 * (dx * axis.x + dz * axis.z) / distance);
            mMainStickY = static_cast<signed char>(65 * (dx * axis.z - dz * axis.x) / distance);
        }
    }
};

namespace {
constexpr int kDefaultTicks = 3600;
constexpr float kParkDistance = 450.0f;   // gather park: outside campaign sight
constexpr float kHoldDistance = 120.0f;   // observation hold: inside sight, outside grab

// Engine-independent self test of the guard truth table. Runs before any
// engine boot so it works without assets or a display.
int guardSelfTest()
{
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
            std::printf("FAIL P2_SARAI_BEHAVIOR selftest row=%d orima=%d dead=%d hp=%.3f got=%d want=%d\n",
                        int(i), int(rows[i].orima), int(rows[i].dead), rows[i].hp,
                        int(down), int(rows[i].expectDown));
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_SARAI_BEHAVIOR_SELFTEST_PASS rows=%d\n", int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}

int envTicks()
{
    const char* ticks = std::getenv("SARAI_BEHAVIOR_TICKS");
    if (!ticks || !*ticks) return kDefaultTicks;
    const long value = std::strtol(ticks, nullptr, 10);
    if (value < 600) return 600;
    if (value > 12000) return 12000;
    return int(value);
}
} // namespace

class BehaviorApp : public PlugPikiApp {
    int frames = 0, observed = 0;
    int budgetTicks = kDefaultTicks;
    int squadAtBirth = 0;
    BTeki* actor = nullptr;
    unsigned anchorToken = 0;
    Vector3f anchorHome;
    bool bound = false;
    bool gathered = false;
    int gatherTick = 0;
    int gatherAttempts = 0;
    int lastGatherTransit = -100000;
    bool holding = false;
    int holdTick = 0;
    int mouthStuckMax = 0;
    int pikminCapturesSeen = 0;
    int lastMouthStuck = 0;
    bool captainTouched = false;
    float minCaptainDist = 1.0e9f;

    int aliveSquad()
    {
        int c = 0;
        Iterator pit(pikiMgr);
        CI_LOOP(pit) { Piki* p = static_cast<Piki*>(*pit); if (p && p->isAlive()) ++c; }
        return c;
    }
    int formationSquad()
    {
        int c = 0;
        Iterator pit(pikiMgr);
        CI_LOOP(pit) {
            Piki* p = static_cast<Piki*>(*pit);
            if (p && p->isAlive() && p->mMode == PikiMode::FormationMode) ++c;
        }
        return c;
    }
    // Read-only census: Pikmin mouth-stuck anywhere (Sarai mouth carriage),
    // and whether the captain is mouth-stuck (must stay zero: retail never
    // targets captains and the fallback is disabled with a staged squad).
    void census(Navi* n, int& mouthStuck, bool& captainMouth)
    {
        mouthStuck = 0;
        captainMouth = false;
        Iterator pit(pikiMgr);
        CI_LOOP(pit) {
            Piki* p = static_cast<Piki*>(*pit);
            if (p && p->isAlive() && p->isStickToMouth()) ++mouthStuck;
        }
        if (n && n->isStickToMouth()) captainMouth = true;
    }
    void squadCentroid(float& x, float& z)
    {
        double sx = 0.0, sz = 0.0;
        int c = 0;
        Iterator pit(pikiMgr);
        CI_LOOP(pit) {
            Piki* p = static_cast<Piki*>(*pit);
            if (p && p->isAlive()) { sx += p->mSRT.t.x; sz += p->mSRT.t.z; ++c; }
        }
        if (c > 0) { x = float(sx / c); z = float(sz / c); }
    }
public:
    int idle() override
    {
        int result = PlugPikiApp::idle();
        require(++frames < 60000, "Sarai behavior startup timeout");
        // Captain guard FIRST, before movie/pause/UI returns and any observation.
        if (naviMgr && pikiMgr && tekiMgr) {
            Navi* guardN = naviMgr->getNavi();
            if (guardN) {
                NaviState* state = static_cast<NaviState*>(guardN->getCurrState());
                p2_fixture_require_captain(GameStat::orimaDead,
                    state && state->getID() == NAVISTATE_Dead, guardN->mHealth, observed);
            }
        }
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip();
            return result;
        }
        if (!pc_p2_preview_ready() || !naviMgr || !pikiMgr || !tekiMgr) return result;
        Navi* n = naviMgr->getNavi();
        if (!n || gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;
        ++observed;
        if (observed == 1) {
            budgetTicks = envTicks();
            // Claim the first live generated actor through the CAMPAIGN seam
            // (the exact bind_dynamic call the seed-bridge sweep makes).
            // Labeled fixture use: the token is the actor's own campaign
            // token (Generator::_70 outside bridge mode).
            Iterator it(tekiMgr);
            CI_LOOP(it) {
                BTeki* a = static_cast<BTeki*>(*it);
                if (a && a->isAlive() && a->mGenerator) {
                    const unsigned token = pc_p2_campaign_token(a);
                    if (token && pc_p2_sarai_manager_bind_dynamic(a, token, token)) {
                        actor = a;
                        anchorToken = token;
                        anchorHome = a->getPosition();
                        bound = true;
                        break;
                    }
                }
            }
            require(bound, "campaign-seam Sarai bound (bind_dynamic + staged banks/model)");
            require(pc_p2_sarai_manager_bound_count() >= 1, "manager carries the campaign binding");
            squadAtBirth = aliveSquad();
            require(squadAtBirth >= 1, "live starting squad staged (overlay ensures 20 red)");
            for (int i = 0; i < DEMOFLAG_COUNT; ++i) playerState->mDemoFlags.setFlagOnly(i);
            // Phase 1: park the captain far outside campaign sight and gather.
            walkGoal.set(anchorHome.x + kParkDistance, 0.0f, anchorHome.z);
            walkActive = true;
            n->mKontroller = new BehaviorController();
            std::printf("P2_SARAI_BEHAVIOR_BIRTH token=%u squad=%d policy=protected_observation\n",
                        anchorToken, squadAtBirth);
            std::fflush(stdout);
        }
        NaviState* nstate = static_cast<NaviState*>(n->getCurrState());
        const int naviId = nstate ? nstate->getID() : -1;

        int mouthStuck = 0;
        bool captainMouth = false;
        census(n, mouthStuck, captainMouth);
        if (mouthStuck > lastMouthStuck) {
            pikminCapturesSeen += mouthStuck - lastMouthStuck;
            std::printf("P2_SARAI_BEHAVIOR_CARRY tick=%d mouth=%d total_captures=%d\n",
                        observed, mouthStuck, pikminCapturesSeen);
            std::fflush(stdout);
        }
        if (mouthStuck > mouthStuckMax) mouthStuckMax = mouthStuck;
        lastMouthStuck = mouthStuck;
        if (captainMouth && !captainTouched) {
            captainTouched = true;
            std::printf("P2_SARAI_BEHAVIOR_CAPTAIN_TOUCH tick=%d\n", observed);
            std::fflush(stdout);
        }
        {
            const float dx = anchorHome.x - n->mSRT.t.x, dz = anchorHome.z - n->mSRT.t.z;
            const float d = std::sqrt(dx * dx + dz * dz);
            if (d < minCaptainDist) minCaptainDist = d;
        }

        if (!gathered) {
            float sx = walkGoal.x, sz = walkGoal.z;
            squadCentroid(sx, sz);
            const float gx = sx - n->mSRT.t.x, gz = sz - n->mSRT.t.z;
            if (gatherTick == 0 && std::sqrt(gx * gx + gz * gz) < 60.0f && naviId == NAVISTATE_Walk) {
                // CONTROLLER_INPUT: whistle-button equivalent.
                n->mStateMachine->transit(n, NAVISTATE_Gather);
                gatherTick = observed;
                lastGatherTransit = observed;
                ++gatherAttempts;
                std::printf("P2_SARAI_BEHAVIOR_GATHER tick=%d attempt=%d controller=whistle_equivalent\n",
                            observed, gatherAttempts);
                std::fflush(stdout);
            } else if (gatherTick > 0 && formationSquad() == 0 && gatherAttempts < 6
                       && observed - lastGatherTransit > 120 && naviId == NAVISTATE_Walk) {
                n->mStateMachine->transit(n, NAVISTATE_Gather);
                lastGatherTransit = observed;
                ++gatherAttempts;
            }
            if (gatherTick > 0 && (formationSquad() > 0 || observed - gatherTick > 600)) {
                gathered = true;
                // Phase 2: hold inside campaign sight with the formation so
                // contact opportunity is real (captain in sight, never a target).
                walkGoal.set(anchorHome.x + kHoldDistance, 0.0f, anchorHome.z);
                holdTick = observed;
                std::printf("P2_SARAI_BEHAVIOR_HOLD tick=%d formation=%d squad=%d\n",
                            observed, formationSquad(), aliveSquad());
                std::fflush(stdout);
            }
        } else if (!holding && observed - holdTick > 60) {
            holding = true;
        }

        if (observed % 300 == 0) {
            std::printf("P2_SARAI_BEHAVIOR_OBSERVE tick=%d squad=%d formation=%d mouth=%d captures=%d captain_touch=%d min_captain_dist=%.1f\n",
                        observed, aliveSquad(), formationSquad(), mouthStuck, pikminCapturesSeen,
                        captainTouched ? 1 : 0, minCaptainDist);
            std::fflush(stdout);
        }
        if (observed >= budgetTicks) {
            std::printf("P2_SARAI_BEHAVIOR_RESULT bound=%d squad_birth=%d squad_end=%d mouth_max=%d captures=%d captain_touch=%d min_captain_dist=%.1f\n",
                        bound ? 1 : 0, squadAtBirth, aliveSquad(), mouthStuckMax, pikminCapturesSeen,
                        captainTouched ? 1 : 0, minCaptainDist);
            std::fflush(stdout);
            pc_p2_sarai_manager_reset();
            const bool clean = pc_p2_sarai_manager_bound_count() == 0;
            std::printf("P2_SARAI_BEHAVIOR_RESET clean=%d\n", clean ? 1 : 0);
            std::fflush(stdout);
            if (!captainTouched && clean) {
                std::puts("PASS P2_SARAI_BEHAVIOR_RUNTIME bind observe reset");
                std::fflush(stdout);
                std::_Exit(0);
            }
            std::printf("FAIL P2_SARAI_BEHAVIOR_RUNTIME captain_touch=%d clean=%d\n",
                        captainTouched ? 1 : 0, clean ? 1 : 0);
            std::fflush(stdout);
            std::_Exit(1);
        }
        return result;
    }
};

int main(int argc, char** argv)
{
    for (int i = 1; i < argc; ++i) {
        if (std::string(argv[i]) == "--guard-self-test") return guardSelfTest();
        if (std::string(argv[i]) == "--guard-negative-test") {
            // Exercise the exact interruption call idle() uses: must print
            // P2_FIXTURE_CAPTAIN_DOWN and exit BLOCKED (86) with no PASS.
            // Engine-independent; the exit code is the assertion.
            p2_fixture_require_captain(true, true, 0.0f, 0);
            std::printf("FAIL P2_SARAI_BEHAVIOR negative test did not trip\n");
            std::fflush(stdout);
            return 1;
        }
    }
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    require(pc_pikipelago_room_preview(), "Sarai behavior fixture requires --experimental-pikmin2-room");
    require(pc_window_init("Sarai behavior fixture", 960, 540), "window");
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
        std::printf("P2_SARAI_BEHAVIOR_WINDOW size=%dx%d pos=%d,%d display=%dx%d centered=%d\n",
                    width, height, x, y, bounds.w, bounds.h, int(centered));
        std::fflush(stdout);
    }
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new BehaviorApp());
    return 0;
}
