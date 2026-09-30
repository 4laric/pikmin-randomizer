// Isolated engine fixture. Each optional mode needs its own runtime evidence.
// P2_PURPLE_DAYEND=1: after storage tests, drive ordinary sunset/results/save.
// P2_PURPLE_RESUME=1 + P2_PURPLE_EXPECT_DAY=<emitted expected_day>: verify a
// fresh-process native campaign restore without injecting population/day/save.
// The harness MUST additionally require the production CAMPAIGN_SAVED log in
// the day-end run. This fixture never invokes a checkpoint writer directly.
// Scripted setup/input and injected maturity do not certify player controls.
#include <SDL2/SDL.h>
#include "system.h"
#include "App.h"
#include "Node.h"
#include "FlowController.h"
#include "MoviePlayer.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "PikiAI.h"
#include "Pellet.h"
#include "PelletState.h"
#include "MapMgr.h"
#include "PikiHeadItem.h"
#include "Pom.h"
#include "Boss.h"
#include "BaseInf.h"
#include "ItemMgr.h"
#include "GameStat.h"
#include "Stream.h"
#include "pc_randomizer.h"
#include "pc_p2_ship.h"
#include "pc_p2_ship_store.h"
#include "pc_p2_purple.h"
#include "pc_p2_input_script.h"
#include "Controller.h"
#include "gameflow.h"
#include "WorldClock.h"
#include "pc_window.h"
#include "pc_gpu_preference.h"
#include "pc_bbft.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>

// Equivalent to the canonical fixture guard; negative mode exits 86 before boot.
static void p2_fixture_require_captain(bool dead, bool deadState, float hp, int tick) {
    if (!dead && !deadState && std::isfinite(hp) && hp > 1.0f) return;
    std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f orima_dead=%d dead_state=%d outcome=BLOCKED\n", tick, hp, int(dead), int(deadState));
    std::fflush(nullptr); std::_Exit(86);
}
static void require(bool ok, const char* why) {
    if (!ok) { std::printf("P2_PURPLE_CAMPAIGN_FAIL %s\n", why); std::fflush(nullptr); std::_Exit(1); }
}
struct TransportFixtureAccess : ActTransport {
    static int slot(const ActTransport& action) {
        int ActTransport::* member = &TransportFixtureAccess::mSlotIndex;
        return action.*member;
    }
};
class PurpleCampaignApp : public PlugPikiApp {
    int ticks = 0;
    bool captainSeen = false;
    int phase = 0, phaseTicks = 0, startingField = 0, pluckAttempts = 0;
    Piki* input = nullptr;
    Piki* acquired = nullptr;
    Pellet* cargo = nullptr;
    Piki* controlRed = nullptr;
    Vector3f cargoStart;
    int carryPhase = 0, carryTicks = 0, carryStable = 0;
    bool carryStep(Navi* n, Piki* purple) {
        ++carryTicks;
        auto assign = [&](Piki* p) {
            require(cargo->isAlive() && cargo->isVisible() && cargo->getState() == PELSTATE_Normal,
                "carry cargo not yet ready");
            p->mActiveAction->abandon(nullptr);
            require(p->isAlive() && p->getState() == PIKISTATE_Normal && !p->isStickTo(), "carry actor not ready");
            p->mActiveAction->mCurrActionIdx = PikiAction::Transport;
            p->mActiveAction->mChildActions[PikiAction::Transport].initialise(cargo);
            p->mMode = PikiMode::TransportMode;
            const auto* action = static_cast<ActTransport*>(p->mActiveAction->mChildActions[PikiAction::Transport].mAction);
            const int slot = TransportFixtureAccess::slot(*action);
            require(slot >= 0 && cargo->isSlotFree(slot), "native carry slot unavailable");
            // Stage once before the first action update. Native exec still must
            // attach, count strength, lift and transport; approach is excluded.
            p->resetPosition(cargo->getSlotGlobalPos(slot, 0.0f));
            p->mVelocity.set(0,0,0); p->mTargetVelocity.set(0,0,0); p->mVolatileVelocity.set(0,0,0);
            std::printf("P2_PURPLE_CARRY_ASSIGN purple=%d slot=%d slot_position_staged=1 approach_bypassed=1 cargo_state=%d visible=%d\n",int(pc_p2_is_purple(p)),slot,cargo->getState(),int(cargo->isVisible()));
        };
        auto release = [&](Piki* p) {
            p->mActiveAction->abandon(nullptr);
            p->changeMode(PikiMode::FormationMode, n);
        };
        if (carryPhase == 0) {
            Iterator bodies(pikiMgr);
            CI_LOOP(bodies) {
                Piki* p = static_cast<Piki*>(*bodies);
                if (p->isAlive() && p->mColor == Red && !p->mP2White && !pc_p2_is_purple(p) && p->getState() == PIKISTATE_Normal
                    && p->mMode == PikiMode::FormationMode) { controlRed = p; break; }
            }
            require(controlRed != nullptr, "carry control unavailable");
            cargo = pelletMgr->newNumberPellet(Red, NUMPEL_TenPellet);
            require(cargo && cargo->mConfig->mCarryMinPikis() == 10, "loaded native ten pellet unavailable");
            Vector3f pos = n->mSRT.t + Vector3f(80, 0, 0);
            pos.y = mapMgr->getMinY(pos.x, pos.z, true) + 5;
            cargo->init(pos); cargo->startAI(TRUE); cargoStart = pos;
            carryPhase = 1; carryTicks = 0;
            std::puts("P2_PURPLE_CARRY_BEGIN injected_cargo=1 native_weight=10 scripted_assignment=1");
        } else if (carryPhase == 1) {
            require(cargo->isAlive(), "carry cargo died before assignment");
            const Vector3f delta = cargo->mSRT.t - cargoStart;
            const float drift = delta.x*delta.x + delta.z*delta.z;
            require(std::isfinite(drift) && std::isfinite(cargo->mSRT.t.y), "carry cargo position invalid");
            // A supported instant spawn excludes appearance from this fixture.
            // Observe an uncarried horizontal baseline; vertical physics jitter
            // must not prevent a test of horizontal carry displacement.
            if (carryTicks < 90 || drift >= 0.25f) {
                cargoStart = cargo->mSRT.t; carryStable = 0;
            } else ++carryStable;
            if (carryTicks % 30 == 0)
                std::printf("P2_PURPLE_CARGO_READY tick=%d state=%d visible=%d ground=%d stable=%d drift=%.3f pos=%.2f,%.2f,%.2f velocity=%.2f,%.2f,%.2f updates_enabled=%u\n",
                    carryTicks,cargo->getState(),int(cargo->isVisible()),int(cargo->onGround()),carryStable,std::sqrt(drift),
                    cargo->mSRT.t.x,cargo->mSRT.t.y,cargo->mSRT.t.z,cargo->mVelocity.x,cargo->mVelocity.y,cargo->mVelocity.z,unsigned(pelletMgr->isMovieFlag(4)));
            if (carryStable >= 30 && cargo->isVisible() && cargo->getState() == PELSTATE_Normal) {
                cargoStart = cargo->mSRT.t;
                assign(controlRed); carryPhase = 2; carryTicks = 0;
            }
        } else if (carryPhase >= 2) {
            require(cargo->isAlive(), "carry cargo disappeared before movement observation");
            const Vector3f d = cargo->mSRT.t - cargoStart;
            const float distanceSquared = d.x*d.x + d.z*d.z;
            if (carryPhase == 2) {
                require(distanceSquared < 4, "one ordinary Pikmin moved native ten pellet");
                if (cargo->mCarrierCounter == 1 && carryTicks >= 120) {
                    release(controlRed); cargoStart = cargo->mSRT.t; assign(purple); carryPhase = 3; carryTicks = 0;
                    std::puts("P2_PURPLE_CARRY_RED_CONTROL_PASS strength=1 displacement_under_2=1");
                }
            } else {
                int attached = 0; Iterator bodies(pikiMgr);
                CI_LOOP(bodies) if (static_cast<Piki*>(*bodies)->getStickObject() == cargo) ++attached;
                require(cargo->mCarrierCounter <= 10, "unexpected extra carrier strength");
                if (cargo->mCarrierCounter == 10 && attached == 1 && distanceSquared > 100) {
                    std::printf("P2_PURPLE_CARRY_PASS strength=10 attached=1 distance=%.2f native_transport=1 injected_cargo=1 scripted_assignment=1\n",std::sqrt(distanceSquared));
                    release(purple); cargo->kill(false); return true;
                }
            }
            if (carryTicks % 120 == 0) {
                Piki* carrier = carryPhase == 2 ? controlRed : purple;
                std::printf("P2_PURPLE_CARRY_PROGRESS phase=%d strength=%d distance=%.2f actor_state=%d mode=%d action=%d attached=%d position=%.1f,%.1f,%.1f cargo_state=%d visible=%d\n",
                    carryPhase,cargo->mCarrierCounter,std::sqrt(distanceSquared),carrier->getState(),int(carrier->mMode),
                    carrier->mActiveAction->mCurrActionIdx,int(carrier->getStickObject()==cargo),
                    carrier->mSRT.t.x,carrier->mSRT.t.y,carrier->mSRT.t.z,cargo->getState(),int(cargo->isVisible()));
            }
        }
        require(carryTicks < 1800, "native ten-strength carry timeout");
        return false;
    }
    bool sunsetRequested = false, sunsetSeen = false;
    int sunsetTicks = 0, sunsetDay = -1, expectedDay = -1, resumeReady = 0;
    unsigned saveIndexBefore = 0;
    static bool flowerStockOne() {
        return p2ship::stock.total() == 1 && p2ship::stock.counts[0][Flower] == 1;
    }
    static void finishSuccess(const char* marker) {
        pc_p2_input_script_clear(1);
        std::puts(marker); std::fflush(nullptr); std::_Exit(0);
    }
    bool advanceSunset() {
        require(++sunsetTicks < 9000, "ordinary sunset/results/save timeout");
        require(gameflow.mCurrGameSectionID == SECTION_OnePlayer, "sunset left ordinary one-player section");
        require(flowCont.mGameEndFlag == GAMEEND_None, "sunset became extinction/captain-down/endgame");
        if (gameflow.mIsDayEndActive) sunsetSeen = true;
        require(gameflow.mWorldClock.mCurrentDay <= expectedDay, "unexpected extra day advance");
        // A fresh native save index is updated AFTER memoryCard.cpp calls the
        // campaign writer. The external harness must still require its log.
        // Creating the initial card also advances the index, before any game
        // save exists. Wait for both signals rather than treating formatting
        // as a failed/completed campaign save.
        if (sunsetSeen && gameflow.mGamePrefs.mHasSaveGame
            && gameflow.mGamePrefs.mMostRecentSaveIndex != saveIndexBefore) {
            require(gameflow.mWorldClock.mCurrentDay == expectedDay, "save did not advance expected day");
            require(flowerStockOne(), "sunset stock/maturity not conserved");
            std::printf("P2_PURPLE_DAYEND_EVIDENCE day_before=%d expected_day=%d day=%d stock=1 flower=1 native_save_index_before=%u native_save_index_after=%u external_campaign_saved_required=1\n",
                sunsetDay, expectedDay, gameflow.mWorldClock.mCurrentDay, saveIndexBefore,
                unsigned(gameflow.mGamePrefs.mMostRecentSaveIndex));
            finishSuccess("P2_PURPLE_DAYEND_NATIVE_SAVE_OBSERVED external_CAMPAIGN_SAVED_required=1 fresh_process_resume_pending=1");
        }
        // Remain input-neutral during the sunset itself. Once the ordinary
        // sequence advances the day, edge-triggered A drives diary/results/save.
        const bool confirming = sunsetSeen && gameflow.mWorldClock.mCurrentDay == expectedDay;
        pc_p2_input_script_set(1, confirming && (sunsetTicks % 20 < 4) ? KBBTN_A : 0, 0, 0);
        if (sunsetTicks % 120 == 0)
            std::printf("P2_PURPLE_DAYEND_PROGRESS ticks=%d active=%d day=%d stock=%d save_index=%u\n",
                sunsetTicks, int(gameflow.mIsDayEndActive), gameflow.mWorldClock.mCurrentDay,
                p2ship::stock.total(), unsigned(gameflow.mGamePrefs.mMostRecentSaveIndex));
        return true;
    }
    Piki* naturalStep(Navi* n) {
        ++phaseTicks;
        Pom* violet = nullptr; int count = 0;
        Iterator flowers(bossMgr);
        CI_LOOP(flowers) {
            Boss* b = static_cast<Boss*>(*flowers);
            if (b && b->isAlive() && b->mObjType == OBJTYPE_Pom && pc_p2_violet(static_cast<Pom*>(b))) { violet = static_cast<Pom*>(b); ++count; }
        }
        if (phase == 0) {
            require(count == 1, "exact bound Violet missing");
            Iterator bodies(pikiMgr);
            CI_LOOP(bodies) {
                Piki* p = static_cast<Piki*>(*bodies);
                if (p->isAlive() && p->getState() == PIKISTATE_Normal && p->mMode == PikiMode::FormationMode && !pc_p2_is_purple(p)) { input = p; break; }
            }
            if (!input) return nullptr;
            GameStat::update(); startingField = GameStat::mapPikis;
            phase = 1; phaseTicks = 0;
            std::printf("P2_PURPLE_NATURAL_START field=%d violet=%.1f,%.1f,%.1f\n", startingField, violet->mSRT.t.x, violet->mSRT.t.y, violet->mSRT.t.z);
        }
        if (phase == 1) {
            if (input && input->isAlive() && !pc_p2_is_purple(input) && !input->isStickTo() && violet
                && input->getState() == PIKISTATE_Normal && phaseTicks % 60 == 0) {
                input->changeMode(PikiMode::FreeMode,n); input->mFSM->transit(input,PIKISTATE_Flying);
                // Sweep the scripted reticle through the native arc; its nominal
                // endpoint is not the ground intercept when hold height varies.
                const char* fixedAim = std::getenv("P2_PURPLE_AIM_SCALE");
                const float aimScale = fixedAim ? std::atof(fixedAim) : 0.8f + 0.1f * ((phaseTicks / 60) % 9);
                Vector3f aim = n->mSRT.t + (violet->mSRT.t - n->mSRT.t) * aimScale;
                n->throwPiki(input,aim);
                std::printf("P2_PURPLE_SCRIPTED_THROW real_collision=1 aim_scale=%.2f captain=%.1f,%.1f,%.1f velocity=%.1f,%.1f,%.1f\n",
                    aimScale,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,input->mVelocity.x,input->mVelocity.y,input->mVelocity.z);
            }
            Iterator heads(itemMgr->getPikiHeadMgr());
            CI_LOOP(heads) {
                PikiHeadItem* h = static_cast<PikiHeadItem*>(*heads);
                if (h && h->isAlive() && h->mP2Purple && h->canPullout()) {
                    // Fixture staging bypasses captain approach/pathfinding only.
                    // The sprout stays where native Violet conversion placed it.
                    n->resetPosition(h->mSRT.t + Vector3f(-12,0,0));
                    ++pluckAttempts;
                    std::printf("P2_PURPLE_PLUCK_ATTEMPT attempt=%d captain_position_staged=1 native_pluck=1 pathfinding_validated=0 player_controls_validated=0\n", pluckAttempts);
                    n->mSproutToPluck=h; n->mPikiToPluck=nullptr;
                    n->mStateMachine->transit(n,NAVISTATE_NukuAdjust);
                    phase=2; phaseTicks=0; input=nullptr;
                    std::puts("P2_VIOLET_REAL_SPROUT captain_pluck_started=1"); break;
                }
            }
        }
        if (phase == 2) {
            Iterator bodies(pikiMgr);
            CI_LOOP(bodies) {
                Piki* p=static_cast<Piki*>(*bodies);
                if (p->isAlive() && pc_p2_is_purple(p) && p->getState()==PIKISTATE_Normal && p->mMode==PikiMode::FormationMode) {
                    GameStat::update(); require(int(GameStat::mapPikis)==startingField,"conversion/pluck population");
                    require(pc_throw_selection_class(p)==4 && pc_piki_carry_strength(p)==10,"selection/strength");
                    std::puts("P2_PURPLE_ACQUISITION_PASS scripted_throw=1 native_conversion=1 captain_pluck=1 selection=4 strength=10");
                    return p;
                }
            }
        }
        if (phase == 2 && phaseTicks > 0 && phaseTicks % 180 == 0) {
            Iterator retryHeads(itemMgr->getPikiHeadMgr());
            CI_LOOP(retryHeads) {
                PikiHeadItem* h = static_cast<PikiHeadItem*>(*retryHeads);
                if (!h || !h->isAlive() || !h->mP2Purple || !h->canPullout()) continue;
                require(pluckAttempts < 3, "native pluck failed after three staged attempts");
                n->resetPosition(h->mSRT.t + Vector3f(-12,0,0));
                ++pluckAttempts;
                std::printf("P2_PURPLE_PLUCK_ATTEMPT attempt=%d captain_position_staged=1 retry=1 phase_ticks=%d native_pluck=1 pathfinding_validated=0 player_controls_validated=0\n",
                    pluckAttempts, phaseTicks);
                n->mSproutToPluck = h; n->mPikiToPluck = nullptr;
                n->mStateMachine->transit(n, NAVISTATE_NukuAdjust);
                break;
            }
        }
        if(phaseTicks%120==0) std::printf("P2_PURPLE_NATURAL_PROGRESS phase=%d ticks=%d violet_state=%d\n",phase,phaseTicks,violet?violet->getCurrentState():-1);
        require(phaseTicks<1800,"natural acquisition timeout"); return nullptr;
    }
public:
    int idle() override {
        const int result = PlugPikiApp::idle();
        Navi* n = naviMgr ? naviMgr->getNavi() : nullptr;
        if (n) {
            captainSeen = true;
            p2_fixture_require_captain(GameStat::orimaDead,
                n->getCurrState() && n->getCurrState()->getID() == NAVISTATE_Dead, n->mHealth, ticks);
        } else {
            // exitStage clears naviMgr during ordinary one-player teardown.
            // Only tolerate absence after observing our requested sunset; never
            // hide a live captain death, including while paused or in a movie.
            const bool expectedTeardown = sunsetRequested && sunsetSeen
                && gameflow.mCurrGameSectionID == SECTION_OnePlayer
                && flowCont.mGameEndFlag == GAMEEND_None
                && gameflow.mWorldClock.mCurrentDay == expectedDay && flowerStockOne();
            require(!captainSeen || expectedTeardown, "captain disappeared outside expected sunset teardown");
        }
        require(++ticks < (sunsetRequested ? 15000 : 6000), "fixture timeout");
        if (std::getenv("P2_PURPLE_RESUME"))
            pc_p2_input_script_set(1, (!n || gameflow.mIsUIOverlayActive) && ticks % 20 < 4 ? KBBTN_A : 0, 0, 0);
        if (sunsetRequested) {
            advanceSunset();
            if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive)
                gameflow.mMoviePlayer->requestSkip();
            return result;
        }
        if (std::getenv("P2_PURPLE_NATURAL") && ticks % 120 == 0)
            std::printf("P2_PURPLE_GATE tick=%d navi=%d pause=%d ui=%d movie=%d phase=%d input_state=%d\n", ticks,
                n && n->getCurrState() ? n->getCurrState()->getID() : -1,
                int(gameflow.mPauseAll), int(gameflow.mIsUIOverlayActive),
                gameflow.mMoviePlayer ? int(gameflow.mMoviePlayer->mIsActive) : -1, phase,
                input && input->isAlive() ? input->getState() : -1);
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip(); return result;
        }
        const bool natural = std::getenv("P2_PURPLE_NATURAL") != nullptr;
        if (!n || !pikiMgr || !itemMgr || gameflow.mPauseAll || gameflow.mIsUIOverlayActive
            || !n->getCurrState()) return result;
        const int naviState = n->getCurrState()->getID();
        // Native idle is healthy and expected after ten seconds without input.
        // Do not stall sprout observation just because the captain stops walking.
        if (naviState != NAVISTATE_Walk && !((natural || std::getenv("P2_PURPLE_RESUME")) && naviState == NAVISTATE_Idle)) return result;
        if (std::getenv("P2_PURPLE_RESUME")) {
            require(pc_randomizer_resumed(), "resume mode loaded no native campaign checkpoint");
            const char* expected = std::getenv("P2_PURPLE_EXPECT_DAY");
            require(expected && *expected, "resume requires P2_PURPLE_EXPECT_DAY from prior evidence");
            char* end = nullptr; const long day = std::strtol(expected, &end, 10);
            require(end && !*end && day > 0 && day < 100000, "invalid expected resume day");
            require(gameflow.mWorldClock.mCurrentDay == day, "native resumed day mismatch");
            require(flowerStockOne(), "native resumed Purple stock/maturity mismatch");
            // Reach a healthy, unpaused, post-intro stage for multiple frames.
            if (++resumeReady >= 60) {
                Piki* purple = pc_p2_ship_withdraw(n, 3);
                require(purple && pc_p2_is_purple(purple) && purple->mHappa == Flower,
                    "resumed stock cannot withdraw as Flower Purple");
                require(p2ship::stock.total() == 0 && pc_p2_ship_deposit(purple) && flowerStockOne(),
                    "resumed withdrawal/deposit conservation");
                std::printf("P2_PURPLE_NATIVE_RESUME_EVIDENCE day=%d stock=1 flower=1 checkpoint_resumed=1 injected_population=0\n", int(day));
                finishSuccess("P2_PURPLE_NATIVE_RESUME_PASS fresh_process_required=1");
            }
            return result;
        }
        Piki* picked = nullptr;
        if (natural) {
            if (!acquired) acquired = naturalStep(n);
            picked = acquired;
        }
        else {
            Iterator it(pikiMgr);
            CI_LOOP(it) {
                Piki* p = static_cast<Piki*>(*it);
                if (p->isAlive() && p->getState() == PIKISTATE_Normal && p->mMode == PikiMode::FormationMode) { picked = p; break; }
            }
        }
        if (!picked) return result;
        if (std::getenv("P2_PURPLE_CARRY") && !carryStep(n, picked)) return result;
        require(pc_randomizer_purple_campaign() && pc_p2_purples_enabled(), "ordinary opt-in not ready");
        picked->setFlower(Flower); if (!natural) pc_p2_make_purple(picked);
        GameStat::update();
        const int field = GameStat::mapPikis, ship = p2ship::stock.total();
        const int red = pikiInfMgr.getColorTotal(Red);
        require(pc_piki_carry_strength(picked) == 10, "Purple strength");
        require(pc_p2_ship_deposit(picked), "deposit");
        require(int(GameStat::mapPikis) == field-1 && p2ship::stock.total() == ship+1, "deposit conservation");
        require(pikiInfMgr.getColorTotal(Red) == red, "Red stock altered");
        Piki* restored = pc_p2_ship_withdraw(n, 3);
        require(restored && pc_p2_is_purple(restored) && restored->mHappa == Flower, "withdraw identity/maturity");
        require(int(GameStat::mapPikis) == field && p2ship::stock.total() == ship, "withdraw conservation");
        require(!pc_p2_ship_withdraw(n, 4), "White unexpectedly enabled");
        for (int i = 0; i < 5; ++i) {
            require(pc_p2_ship_deposit(restored), "repeat deposit");
            restored = pc_p2_ship_withdraw(n, 3);
            require(restored && int(GameStat::mapPikis) == field && p2ship::stock.total() == ship, "repeat drift");
        }
        require(pc_p2_ship_deposit(restored), "reserve one sprout slot");
        PikiHeadItem* sprout = static_cast<PikiHeadItem*>(itemMgr->birth(OBJTYPE_Pikihead));
        require(sprout != nullptr, "sprout allocation");
        sprout->init(n->mSRT.t); sprout->setColor(Red); sprout->mP2Purple = true; sprout->mFlowerStage = Bud;
        BPikiInf saved, loaded; saved.store(sprout);
        unsigned char bytes[32] = {}; RamStream out(bytes, sizeof(bytes)); saved.saveCard(out);
        RamStream in(bytes, sizeof(bytes)); loaded.loadCard(in);
        sprout->setColor(Red); loaded.doRestore(sprout);
        require(sprout->mP2Purple && sprout->mFlowerStage == Bud, "buried save identity/maturity");
        std::printf("P2_PURPLE_CAMPAIGN_STORAGE_PASS injected_identity=%d injected_maturity=1 live_squad=1 population_conserved=1 red_stock_unchanged=1\n",int(!natural));
        if (std::getenv("P2_PURPLE_DAYEND")) {
            require(ship == 0 && flowerStockOne(), "day-end fixture requires fresh empty ship baseline");
            // This serialization-only test sprout never ran startAI, so it has
            // no mePikis accounting or emitted effects. Return its pool slot
            // directly; PikiHeadItem::doKill would invent a pluck work counter.
            itemMgr->kill(sprout);
            GameStat::update();
            require(int(GameStat::mapPikis) == field - 1, "test sprout retirement changed population");
            restored = pc_p2_ship_withdraw(n, 3);
            require(restored && restored->mHappa == Flower && pc_p2_is_purple(restored)
                && restored->mMode == PikiMode::FormationMode && int(GameStat::mapPikis) == field
                && p2ship::stock.total() == 0, "sunset Purple setup");
            sunsetDay = gameflow.mWorldClock.mCurrentDay;
            expectedDay = pc_randomizer_next_day(sunsetDay);
            require(expectedDay == sunsetDay + 1, "fixture requires ordinary next-day advance");
            saveIndexBefore = gameflow.mGamePrefs.mMostRecentSaveIndex;
            require(flowCont.mGameEndFlag == GAMEEND_None, "sunset initial endgame flag");
            sunsetRequested = true; input = nullptr;
            pc_p2_input_script_set(1, 0, 0, 0);
            std::printf("P2_PURPLE_DAYEND_BEGIN day=%d expected_day=%d field=%d stock=0 flower_in_formation=1 injected_maturity=1\n",
                sunsetDay, expectedDay, field);
            // Natural PlayingGameModeState end-hour branch starts sunset. Do
            // not call cleanupDayEnd/exitDayEnd or any save routine directly.
            gameflow.mWorldClock.setTime(gameflow.mParameters->mEndHour());
            return result;
        }
        std::fflush(nullptr); std::_Exit(0);
    }
};
int main(int argc, char** argv) {
    if (std::getenv("P2_FIXTURE_FORCE_CAPTAIN_DOWN")) p2_fixture_require_captain(false, false, 0, 0);
    require(!(std::getenv("P2_PURPLE_DAYEND") && std::getenv("P2_PURPLE_RESUME")), "dayend/resume modes are exclusive");
    require(!std::getenv("P2_PURPLE_CARRY") || std::getenv("P2_PURPLE_NATURAL"), "carry mode requires natural acquisition");
    setvbuf(stdout, nullptr, _IONBF, 0);
    SDL_SetMainReady(); pc_gpu_preference_apply();
    pc_bbft_init(argc, argv);
    if (!pc_randomizer_purple_campaign()) return 2;
    if (!pc_window_init("Purple campaign storage fixture", 960, 540)) return 3;
    pc_settings_init();
    pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);
    pc_window_set_window_size(960, 540); pc_window_center();
    std::puts("Experimental preview window set to 960x540 windowed and centered");
    int w=0,h=0,x=0,y=0; SDL_Window* window=SDL_GL_GetCurrentWindow();
    SDL_GetWindowSize(window,&w,&h); SDL_GetWindowPosition(window,&x,&y);
    require(w==960 && h==540,"window dimensions");
    std::printf("P2_FIXTURE_WINDOW width=%d height=%d x=%d y=%d\n",w,h,x,y);
    gsys->Initialise(); pc_settings_p2d_init(); nodeMgr = new NodeMgr();
    gsys->run(new PurpleCampaignApp()); return 0;
}

