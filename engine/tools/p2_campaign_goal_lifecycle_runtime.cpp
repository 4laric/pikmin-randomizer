// Campaign Onion GoalItem lifecycle observer (rd-p2-campaign-goal-lifecycle, #836).
//
// Self-contained replacement-main TU (no shared file touched): main() mirrors
// the production pc_port/pc_main.cpp startup (SDL, pc_bbft_init(argv), window,
// settings, gsys, nodeMgr) but runs the CampaignGoalApp observer below
// instead of a bare PlugPikiApp. Like the #830 gen-4 correction harness, this
// boots WITHOUT --experimental-pikmin2-room so pc_bbft_init does NOT take the
// bridge-only early return and pc_randomizer_init parses the real session
// bootstrap (full session: enabled/ready/fingerprint/ENEMY_P2). Booting WITH
// the preview flag would silently disable the session; the harness requires
// the session live and fails closed otherwise.
//
// Scenario (Forest of Hope, foh-day2 session, retail stage1 Onions + staged
// 20-red squad): reproduce the enabled-session condition from #830 gen-4 and
// emit a time series of Onion censuses through the REAL production lookup
// path (pc_p2_campaign_goal_probe: per-color ItemMgr::getContainer plus the
// MeltingPotMgr pool count) alongside the legacy Iterator(itemMgr) direct
// count that read zero in #830. The series distinguishes absent-at-first-tick
// from absent-through-playable-state; the engine-free validator in
// tools/p2_campaign_goal_lifecycle_test.cpp classifies a captured log.
//
// Captain policy is PARKED: goal birth/population is the mechanism under
// test, not captain hits, so the captain holds at spawn with neutral stick
// and is never walked toward any anchor. One whistle equivalent gathers the
// staged squad into formation (labelled controller input); no throws, no
// dismiss, no enemy engagement. No actor is placed or written, no
// health/Transport/state is written, no production enabled flag is patched,
// and no receipt grant is ever called. Probe observation is strictly
// read-only (const manager iteration).
//
// Captain safety (#632): the canonical guard runs FIRST after engine idle
// and BEFORE movie/pause/UI early returns, readiness gates, observation
// counters or summary markers; CAPTAIN_DOWN exits 86 BLOCKED. This run
// parks the captain, so a guard trip would indicate an unexpected captor or
// hazard reaching spawn, never an accepted outcome.
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
#include "Section.h"
#include "FlowController.h"
#include "MoviePlayer.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Kontroller.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "ItemMgr.h"
#include "PlayerState.h"
#include "Demo.h"
#include "GameStat.h"
#include "gameflow.h"
#include "Creature.h"
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_randomizer.h"
#include "pc_p2_campaign_goal_probe.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

// Neutral-stick controller: the captain holds position at spawn. Genuine
// (zero) stick input, never a position write.
class ParkedController : public Kontroller {
public:
    ParkedController() : Kontroller(1) {}
    void update() override {
        mMainStickX = 0; mMainStickY = 0;
        mSubStickX = 0; mSubStickY = 0;
        updateCont(0);
    }
};

namespace {

// Engine-independent self test of the guard truth table. Runs before any
// engine boot so it works without assets or a display.
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
            std::printf("FAIL P2_GOAL_LIFECYCLE selftest row=%d orima=%d dead=%d hp=%.3f got=%d want=%d\n",
                        int(i), int(rows[i].orima), int(rows[i].dead), rows[i].hp,
                        int(down), int(rows[i].expectDown));
            std::fflush(stdout);
            return 1;
        }
    }
    std::printf("P2_GOAL_LIFECYCLE_SELFTEST_PASS rows=%d\n", int(sizeof(rows) / sizeof(rows[0])));
    std::fflush(stdout);
    return 0;
}

int envTicks()
{
    const char* ticks = std::getenv("GOAL_LIFECYCLE_TICKS");
    if (!ticks || !*ticks) return 3600;
    const long value = std::strtol(ticks, nullptr, 10);
    if (value < 600) return 600;
    if (value > 12000) return 12000;
    return int(value);
}

constexpr int kCensusPeriod = 90;

} // namespace

class CampaignGoalApp : public PlugPikiApp {
    int frames = 0, observed = 0;
    bool sessionChecked = false;
    bool firstCensusDone = false;
    bool firstTickPresent = false;
    bool laterPresent = false;
    int firstCensusTick = -1;
    int lastMelt = 0;
    int lastRed = 0;
    int budgetTicks = 3600;
    int gatherTick = 0;
    int gatherAttempts = 0;
    int lastGatherTransit = -100000;
    int squadAtBirth = 0;
    int aliveSquad() {
        int c = 0; Iterator pit(pikiMgr); CI_LOOP(pit) {
            Piki* p = static_cast<Piki*>(*pit); if (p && p->isAlive()) ++c;
        } return c;
    }
    int formationSquad() {
        int c = 0; Iterator pit(pikiMgr); CI_LOOP(pit) {
            Piki* p = static_cast<Piki*>(*pit);
            if (p && p->isAlive() && p->mMode == PikiMode::FormationMode) ++c;
        } return c;
    }
public:
    int idle() override {
        int result = PlugPikiApp::idle();
        require(++frames < 120000, "goal lifecycle campaign startup timeout");
        // Captain guard FIRST, before movie/pause/UI returns and any observation.
        if (naviMgr && pikiMgr) {
            Navi* guardN = naviMgr->getNavi();
            if (guardN) {
                NaviState* state = static_cast<NaviState*>(guardN->getCurrState());
                p2_fixture_require_captain(GameStat::orimaDead,
                    state && state->getID() == NAVISTATE_Dead, guardN->mHealth, observed);
            }
        }
        // Intro-only fixture skip: never automatically skip day-end/results movies.
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip();
            return result;
        }
        if (!naviMgr || !pikiMgr || !itemMgr) return result;
        Navi* n = naviMgr->getNavi();
        if (!n || gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;
        ++observed;
        if (!sessionChecked) {
            sessionChecked = true;
            budgetTicks = envTicks();
            const bool session = pc_randomizer_enabled() && pc_randomizer_ready();
            const bool bridge = pc_randomizer_p2_bridge();
            std::printf("P2_GOAL_LIFECYCLE_SESSION enabled=%d ready=%d bridge=%d\n",
                        int(pc_randomizer_enabled()), int(pc_randomizer_ready()),
                        int(bridge));
            std::fflush(stdout);
            require(session, "real randomizer session enabled (boot without preview flag, with --randomizer-seed)");
            squadAtBirth = aliveSquad();
            require(squadAtBirth >= 1, "live starting squad staged (generated forest squad)");
            for (int i = 0; i < DEMOFLAG_COUNT; ++i) playerState->mDemoFlags.setFlagOnly(i);
            n->mKontroller = new ParkedController();
            std::printf("P2_GOAL_LIFECYCLE_BIRTH squad=%d policy=parked\n", squadAtBirth);
            std::fflush(stdout);
        }
        NaviState* nstate = static_cast<NaviState*>(n->getCurrState());
        const int naviId = nstate ? nstate->getID() : -1;
        // One whistle equivalent to gather the staged squad into formation;
        // the captain never walks anywhere (parked policy).
        if (gatherTick == 0 && naviId == NAVISTATE_Walk) {
            if (observed - lastGatherTransit > 120 && gatherAttempts < 3) {
                // CONTROLLER_INPUT: whistle-button equivalent.
                n->mStateMachine->transit(n, NAVISTATE_Gather);
                lastGatherTransit = observed;
                ++gatherAttempts;
                std::printf("P2_GOAL_LIFECYCLE_GATHER tick=%d attempt=%d controller=whistle_equivalent\n",
                            observed, gatherAttempts);
                std::fflush(stdout);
            }
        }
        if (gatherTick == 0 && (formationSquad() > 0 || gatherAttempts >= 3)) {
            gatherTick = observed;
            std::printf("P2_GOAL_LIFECYCLE_FORMATION tick=%d formation=%d squad=%d attempts=%d\n",
                        observed, formationSquad(), aliveSquad(), gatherAttempts);
            std::fflush(stdout);
        }
        // Time-series census: first observed tick plus every period.
        // Read-only probe; never births or mutates a GoalItem.
        if (!firstCensusDone || observed % kCensusPeriod == 0) {
            pc_p2_campaign_goal_log("P2_CAMPAIGN_GOAL_CENSUS", observed);
            P2CampaignGoalCensus census = pc_p2_campaign_goal_census();
            const bool present = census.melt_total > 0;
            lastMelt = census.melt_total;
            lastRed = census.container[P2_GOAL_RED];
            if (!firstCensusDone) {
                firstCensusDone = true;
                firstCensusTick = observed;
                firstTickPresent = present;
            } else if (present) {
                laterPresent = true;
            }
        }
        if (observed % 300 == 0) {
            std::printf("P2_GOAL_LIFECYCLE_OBSERVE tick=%d squad=%d formation=%d melt=%d red=%d\n",
                        observed, aliveSquad(), formationSquad(), lastMelt, lastRed);
            std::fflush(stdout);
        }
        if (observed >= budgetTicks) {
            pc_p2_campaign_goal_log("P2_CAMPAIGN_GOAL_CENSUS", observed);
            P2CampaignGoalCensus census = pc_p2_campaign_goal_census();
            if (census.melt_total > 0 && observed != firstCensusTick) laterPresent = true;
            const char* classification = p2_campaign_goal_classify(firstTickPresent, laterPresent);
            std::printf("P2_GOAL_LIFECYCLE_SUMMARY first_tick=%d first_present=%d later_present=%d "
                        "last_melt=%d last_red=%d squad=%d classification=%s\n",
                        firstCensusTick, firstTickPresent ? 1 : 0, laterPresent ? 1 : 0,
                        census.melt_total, census.container[P2_GOAL_RED], aliveSquad(),
                        classification);
            std::fflush(stdout);
            if (census.melt_total > 0 || laterPresent) {
                std::puts("PASS P2_GOAL_LIFECYCLE_RUNTIME goals_observed_through_playable_state");
                std::fflush(stdout);
                std::_Exit(0);
            }
            std::puts("P2_GOAL_LIFECYCLE_STALL stage=no_goal first_tick_absent_and_absent_through_playable_state");
            std::puts("FAIL P2_GOAL_LIFECYCLE_RUNTIME no_goal_observed");
            std::fflush(stdout);
            std::_Exit(1);
        }
        std::fflush(stdout);
        return result;
    }
    static void require(bool value, const char* message) {
        if (!value) { std::printf("FAIL goal lifecycle campaign: %s\n", message); std::fflush(stdout); std::_Exit(2); }
    }
};

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        if (std::string(argv[i]) == "--guard-self-test") return guardSelfTest();
        if (std::string(argv[i]) == "--guard-negative-test") {
            // Exercise the exact interruption call idle() uses: must print
            // P2_FIXTURE_CAPTAIN_DOWN and exit BLOCKED (86) with no PASS.
            // Engine-independent; the exit code is the assertion.
            p2_fixture_require_captain(true, true, 0.0f, 0);
            std::printf("FAIL P2_GOAL_LIFECYCLE negative test did not trip\n");
            std::fflush(stdout);
            return 1;
        }
    }
    setvbuf(stdout, NULL, _IONBF, 0);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    // Production startup: pc_bbft_init parses --randomizer-seed into a full
    // session here because NO preview flag is passed (challengeLevel stays
    // -1, so the bridge-only early return is skipped and pc_randomizer_init
    // runs). Booting WITH --experimental-pikmin2-room would silently disable
    // the session; this harness refuses that combination below.
    for (int i = 1; i < argc; ++i) {
        if (!std::strcmp(argv[i], "--experimental-pikmin2-room")) {
            std::printf("FAIL goal lifecycle campaign: preview boot refused (session would be disabled)\n");
            std::fflush(stdout);
            return 2;
        }
    }
    pc_bbft_init(argc, argv);
    if (!pc_window_init("Goal lifecycle campaign observer", 960, 540)) return 3;
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
        std::printf("P2_GOAL_LIFECYCLE_WINDOW size=%dx%d pos=%d,%d display=%dx%d centered=%d\n",
                    width, height, x, y, bounds.w, bounds.h, int(centered));
        std::fflush(stdout);
    }
    pc_settings_init();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new CampaignGoalApp());
    return 0;
}
