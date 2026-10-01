// Acceptance additionally requires a production P2_PURPLE_DIRECT stage=hipdrop
// marker for the printed target/source pointers, family=adult_bulborb and
// damage_applied=1 and queued_after-queued_before=50, together with the
// regeneration-compensated 50 HP delta below. Adult accepted=0
// is expected (that flag describes dwarf press). Health alone is NOT acceptance.
// Natural Violet conversion/native pluck precede the test. Captain positioning,
// a single descending-source placement, and post-contact source isolation are
// fixture setup, not player controls, throw accuracy, or pathfinding coverage.
#include <SDL2/SDL.h>
#include "system.h"
#include "App.h"
#include "Node.h"
#include "MoviePlayer.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "PikiHeadItem.h"
#include "Pellet.h"
#include "Pom.h"
#include "Boss.h"
#include "ItemMgr.h"
#include "GameStat.h"
#include "MapMgr.h"
#include "nlib/System.h"
#include "gameflow.h"
#include "pc_randomizer.h"
#include "pc_p2_purple.h"
#include "pc_p2_ship.h"
#include "pc_p2_ship_store.h"
#include "pc_p2_input_script.h"
#include "FlowController.h"
#include "WorldClock.h"
#include "pc_p2_purple_direct.h"
#include "pc_p2_purple_flight.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_chappy.h"
#include "pc_p2_purple_impact.h"
#include "pc_window.h"
#include "pc_gpu_preference.h"
#include "pc_bbft.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cerrno>
#include <climits>
#include <chrono>
#include <set>

static void p2_fixture_require_captain(bool dead, bool deadState, float hp, int tick) {
    if (!dead && !deadState && std::isfinite(hp) && hp > 1.0f) return;
    std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f orima_dead=%d dead_state=%d outcome=BLOCKED\n", tick,hp,int(dead),int(deadState));
    std::fflush(nullptr); std::_Exit(86);
}
static void require(bool ok, const char* why) {
    if (!ok) { std::printf("P2_PURPLE_COMBAT_FAIL reason=%s\n",why); std::fflush(nullptr); std::_Exit(1); }
}
class PurpleCombatApp : public PlugPikiApp {
    int ticks=0, phase=0, phaseTicks=0, startingField=0, pluckAttempts=0;
    int combatTicks=0, observedTicks=0, throwAttempts=0, throwTick=0;
    bool captainSeen=false, thrown=false, descentStaged=false, isolated=false;
    Piki* input=nullptr;
    Piki* acquired=nullptr;
    BTeki* target=nullptr;
    unsigned targetUid=0;
    float initialHealth=0, maxQueued=0, regeneration=0;
    int regenerationFrames=0;
    Vector3f parkPosition;
    bool sunsetRequested=false, sunsetSeen=false;
    int sunsetTicks=0, sunsetDay=-1, expectedDay=-1, savedMaturity=-1, resumeReady=0;
    unsigned saveIndexBefore=0;
    bool mode(const char* name) const {
        const char* value=std::getenv("P2_PURPLE_COMBAT_MODE");
        return value && std::strcmp(value,name)==0;
    }
    bool stockOne() const {
        return savedMaturity>=0 && savedMaturity<3 && p2ship::stock.total()==1
            && p2ship::stock.counts[0][savedMaturity]==1;
    }
    void boundAdult(bool liveRequired=true) {
        require(pc_p2_purple_direct_enabled(),"combat profile missing after save/restart");
        // Restart confirms the map's default Impact Site, where this Hope
        // generator is absent. The saved seed mapping must still be exact;
        // never manufacture an actor merely to validate an absent-stage row.
        require(pc_randomizer_p2_source_for_id(3640055869u)==2,"persisted seed combat mapping mismatch");
        bool found=false;
        Iterator it(tekiMgr);
        CI_LOOP(it) {
            BTeki* actor=static_cast<BTeki*>(*it);
            if (actor && actor->isAlive() && pc_p2_campaign_source(actor)==2
                && pc_p2_purple_direct_adult_registered(actor)) {
                std::printf("P2_PURPLE_PERSIST_BINDING uid=%u source=2 registered=1\n",pc_p2_campaign_token(actor));
                found=true; break;
            }
        }
        std::printf("P2_PURPLE_PERSIST_CATALOG uid=3640055869 source=2 profile_enabled=1 live_registered=%d live_required=%d stage=%d\n",
            int(found),int(liveRequired),gameflow.mCurrentStageID);
        require(!liveRequired || found,"no exact live adult combat binding in persistence fixture");
    }
    void sunsetStep() {
        require(++sunsetTicks<9000,"ordinary day-save timeout");
        require(gameflow.mCurrGameSectionID==SECTION_OnePlayer && flowCont.mGameEndFlag==GAMEEND_None,
            "sunset left ordinary healthy campaign");
        if(gameflow.mIsDayEndActive) sunsetSeen=true;
        require(gameflow.mWorldClock.mCurrentDay<=expectedDay,"unexpected extra day advance");
        if(sunsetSeen && gameflow.mGamePrefs.mHasSaveGame
            && gameflow.mGamePrefs.mMostRecentSaveIndex!=saveIndexBefore) {
            require(gameflow.mWorldClock.mCurrentDay==expectedDay && stockOne(),"day-save identity/maturity/day mismatch");
            pc_p2_input_script_clear(1);
            std::printf("P2_PURPLE_PERSIST_SAVED day_before=%d day=%d maturity=%d stock=1 native_save_index_before=%u native_save_index_after=%u external_CAMPAIGN_SAVED_required=1 identity_injected=0 maturity_injected=0\n",
                sunsetDay,expectedDay,savedMaturity,saveIndexBefore,unsigned(gameflow.mGamePrefs.mMostRecentSaveIndex));
            std::fflush(nullptr); std::_Exit(0);
        }
        const bool confirming=sunsetSeen && gameflow.mWorldClock.mCurrentDay==expectedDay;
        pc_p2_input_script_set(1,confirming && sunsetTicks%20<4?KBBTN_A:0,0,0);
        if(sunsetTicks%120==0) std::printf("P2_PURPLE_PERSIST_PROGRESS ticks=%d day=%d active=%d stock=%d\n",
            sunsetTicks,gameflow.mWorldClock.mCurrentDay,int(gameflow.mIsDayEndActive),p2ship::stock.total());
    }
    void beginPersistence(Navi* n) {
        require(acquired && acquired->isAlive() && pc_p2_is_purple(acquired),"persistence requires naturally acquired Purple");
        require(!pc_randomizer_resumed() && p2ship::stock.total()==0,"day-save requires fresh empty baseline");
        boundAdult(); savedMaturity=acquired->mHappa;
        require(savedMaturity>=0 && savedMaturity<3,"invalid acquired maturity");
        GameStat::update(); const int field=GameStat::mapPikis;
        require(field==20,"fresh conversion must conserve starting20");
        require(pc_p2_ship_deposit(acquired) && stockOne() && int(GameStat::mapPikis)==field-1,"deposit identity/population");
        Piki* restored=pc_p2_ship_withdraw(n,3);
        require(restored && pc_p2_is_purple(restored) && !restored->mP2White
            && restored->mHappa==savedMaturity && pc_piki_carry_strength(restored)==10
            && pc_throw_selection_class(restored)==4 && p2ship::stock.total()==0
            && int(GameStat::mapPikis)==field && restored->mMode==PikiMode::FormationMode,"withdraw identity/population");
        sunsetDay=gameflow.mWorldClock.mCurrentDay; expectedDay=pc_randomizer_next_day(sunsetDay);
        require(expectedDay==sunsetDay+1 && flowCont.mGameEndFlag==GAMEEND_None,"ordinary next day required");
        saveIndexBefore=gameflow.mGamePrefs.mMostRecentSaveIndex;
        sunsetRequested=true; acquired=nullptr; input=nullptr;
        pc_p2_input_script_set(1,0,0,0);
        std::printf("P2_PURPLE_PERSIST_BEGIN day=%d expected_day=%d maturity=%d field=%d stock=0 identity_injected=0 maturity_injected=0 clock_advanced=1 menu_input_scripted=1\n",
            sunsetDay,expectedDay,savedMaturity,field);
        gameflow.mWorldClock.setTime(gameflow.mParameters->mEndHour());
    }
    static int expectedNumber(const char* name,int minimum,int maximum) {
        const char* text=std::getenv(name); require(text && *text,"missing restart expectation");
        char* end=nullptr; errno=0; const long n=std::strtol(text,&end,10);
        require(!errno && end && !*end && n>=minimum && n<=maximum,"invalid restart expectation"); return int(n);
    }
    void resumePersistence(Navi* n) {
        savedMaturity=expectedNumber("P2_PURPLE_EXPECT_MATURITY",0,2);
        expectedDay=expectedNumber("P2_PURPLE_EXPECT_DAY",1,99999);
        require(pc_randomizer_resumed() && gameflow.mWorldClock.mCurrentDay==expectedDay && stockOne(),
            "native restart checkpoint/day/stock/maturity mismatch");
        if(++resumeReady<60) return;
        boundAdult(false); GameStat::update(); const int field=GameStat::mapPikis;
        Iterator bodies(pikiMgr); CI_LOOP(bodies) {
            Piki* p=static_cast<Piki*>(*bodies);
            require(!p || !p->isAlive() || !pc_p2_is_purple(p),"duplicate field Purple before withdrawal");
        }
        Piki* restored=pc_p2_ship_withdraw(n,3);
        require(restored && pc_p2_is_purple(restored) && !restored->mP2White
            && restored->mHappa==savedMaturity && pc_piki_carry_strength(restored)==10
            && pc_throw_selection_class(restored)==4 && p2ship::stock.total()==0
            && int(GameStat::mapPikis)==field+1,"restart withdrawal identity/population");
        require(!pc_p2_ship_withdraw(n,3),"restart duplicated stock");
        require(pc_p2_ship_deposit(restored) && stockOne() && int(GameStat::mapPikis)==field,"restart redeposit conservation");
        pc_p2_input_script_clear(1);
        std::printf("P2_PURPLE_PERSIST_RESUME_PASS day=%d maturity=%d stock=1 field_before=%d field_after=%d checkpoint_resumed=1 identity_injected=0 maturity_injected=0 strength=10 selection=4\n",
            expectedDay,savedMaturity,field,int(GameStat::mapPikis));
        std::fflush(nullptr); std::_Exit(0);
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
            Iterator existing(pikiMgr);
            CI_LOOP(existing) {
                Piki* p=static_cast<Piki*>(*existing);
                require(!p || !p->isAlive() || !pc_p2_is_purple(p), "pre-existing Purple invalidates natural acquisition");
            }
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

    bool targetPresent() const {
        if (!tekiMgr) return false;
        Iterator it(tekiMgr);
        CI_LOOP(it) {
            BTeki* actor=static_cast<BTeki*>(*it);
            if (actor==target && pc_p2_campaign_source(actor)==2
                && pc_randomizer_generator_id(actor->mGenerator)==targetUid) return true;
        }
        return false;
    }
    void diagnostics(Navi* n) {
        const char* state="unavailable"; const char* clip="unavailable"; float clipPhase=0;
        const bool present=target && targetPresent();
        if (present) pc_p2_chappy_probe(target,&state,&clip,&clipPhase);
        if (present && acquired) std::printf("P2_PURPLE_COMBAT_GEOMETRY uid=%u target=%.3f,%.3f,%.3f source=%.3f,%.3f,%.3f source_velocity=%.3f,%.3f,%.3f\n",
            targetUid,target->mSRT.t.x,target->mSRT.t.y,target->mSRT.t.z,
            acquired->mSRT.t.x,acquired->mSRT.t.y,acquired->mSRT.t.z,
            acquired->mVelocity.x,acquired->mVelocity.y,acquired->mVelocity.z);
        const auto flight=pc_p2_purple_flight_sample(acquired);
        std::printf("P2_PURPLE_COMBAT_PROGRESS tick=%d acquisition_phase=%d acquisition_ticks=%d combat_ticks=%d navi=%d pause=%d ui=%d target_present=%d uid=%u source=2 health=%.3f queued=%.3f enemy_state=%s clip=%s clip_phase=%.3f piki_state=%d flight=%d staged=%d isolated=%d\n",
            ticks,phase,phaseTicks,combatTicks,n&&n->getCurrState()?n->getCurrState()->getID():-1,
            int(gameflow.mPauseAll),int(gameflow.mIsUIOverlayActive),int(present),targetUid,
            present?target->mHealth:-1.f,present?target->mStoredDamage:-1.f,state?state:"null",clip?clip:"null",clipPhase,
            acquired?acquired->getState():-1,int(flight.phase),int(descentStaged),int(isolated));
    }
    void combatStep(Navi* n) {
        require(++combatTicks<900,"adult direct contact/damage timeout (see progress)");
        require(acquired->isAlive() && pc_p2_is_purple(acquired),"acquired Purple lost");
        if (!target) {
            require(pc_p2_purple_direct_enabled() && pc_p2_purple_flight_enabled(),"direct/flight profiles disabled");
            unsigned requested=0;
            const char* uidText=std::getenv("P2_PURPLE_COMBAT_UID");
            if (uidText) {
                char* end=nullptr; errno=0;
                const unsigned long value=std::strtoul(uidText,&end,10);
                require(*uidText && *uidText!='-' && end && !*end && !errno && value>0 && value<=UINT_MAX,"invalid decimal target UID");
                requested=static_cast<unsigned>(value);
            }
            Iterator enemies(tekiMgr);
            CI_LOOP(enemies) {
                BTeki* candidate=static_cast<BTeki*>(*enemies);
                if (!candidate || !candidate->isAlive() || pc_p2_campaign_source(candidate)!=2
                    || !pc_p2_chappy_registered(candidate) || !pc_p2_purple_direct_adult_registered(candidate)) continue;
                const unsigned uid=pc_randomizer_generator_id(candidate->mGenerator);
                if (requested && uid!=requested) continue;
                if (!target || uid<targetUid) { target=candidate; targetUid=uid; }
            }
            if (!target) return; // Later generated actors may register after stage entry.
            require(target->mHealth>50.f && std::isfinite(target->mHealth) && target->mStoredDamage==0.f,
                "adult must be alive above 50 HP with no pending damage");
            parkPosition=n->mSRT.t;
            // Park other squad members at the acquisition site and detach them
            // from formation before moving the captain. No enemy is relocated.
            Iterator squad(pikiMgr);
            CI_LOOP(squad) {
                Piki* p=static_cast<Piki*>(*squad);
                if (p && p!=acquired && p->isAlive()) {
                    require(!p->isStickTo(),"other squad member already attached");
                    p->changeMode(PikiMode::FreeMode,n); p->resetPosition(parkPosition);
                }
            }
            initialHealth=target->mHealth;
            std::printf("P2_PURPLE_COMBAT_BASELINE uid=%u target=%p view=%p health=%.3f native_max=%.3f family_max=%.3f regen_rate=%.6f\n",
                targetUid,static_cast<void*>(target),static_cast<void*>(static_cast<PelletView*>(target)),
                initialHealth,target->getMaxLife(),pc_p2_chappy_max_health(target,-1.f),target->getParameterF(TPF_LifeRecoverRate));
            require(std::isfinite(target->getMaxLife()) && std::fabs(initialHealth-target->getMaxLife())<0.01f,
                "adult must start at native maximum health for regeneration accounting");
            std::printf("P2_PURPLE_COMBAT_TARGET uid=%u source=2 target=%p piki=%p health_before=%.3f queued_before=%.3f generated_actor=1 adapter_registered=1 other_squad_parked=1\n",
                targetUid,static_cast<void*>(target),static_cast<void*>(acquired),initialHealth,target->mStoredDamage);
        }
        require(targetPresent() && target->isAlive(),"configured generated adult disappeared/died");
        require(pc_p2_chappy_registered(target) && pc_p2_purple_direct_adult_registered(target),"adult adapter registration lost");
        if (!thrown) {
            const Vector3f pos=target->mSRT.t;
            n->resetPosition(Vector3f(pos.x-90.f,mapMgr->getMinY(pos.x-90.f,pos.z,true),pos.z));
            acquired->changeMode(PikiMode::FreeMode,n);
            acquired->mFSM->transit(acquired,PIKISTATE_Flying);
            n->throwPiki(acquired,Vector3f(pos.x+42.f,pos.y,pos.z));
            require(pc_p2_purple_flight_active(acquired),"native throw did not arm Purple flight");
            thrown=true; throwTick=combatTicks; ++throwAttempts;
            std::printf("P2_PURPLE_COMBAT_THROW attempt=%d uid=%u source=2 target=%p piki=%p native_throw=1 captain_position_staged=1 enemy_modified=0 controls_validated=0\n",
                throwAttempts,targetUid,static_cast<void*>(target),static_cast<void*>(acquired));
            return;
        }
        maxQueued=target->mStoredDamage>maxQueued?target->mStoredDamage:maxQueued;
        const float delta=initialHealth-target->mHealth;
        require(std::isfinite(delta) && std::isfinite(target->mStoredDamage),"nonfinite target damage");
        // BTeki::update applies queued damage through chappy_update, then
        // regenerates dt * (getMaxLife() * LifeRecoverRate). Include the first
        // observed damaged frame. Earlier full-health frames clamp to maximum
        // and contribute nothing. Each subsequent still-damaged frame counts.
        const float dt=NSystem::getFrameTime();
        const float maximum=target->getMaxLife();
        const float rate=target->getParameterF(TPF_LifeRecoverRate);
        const float frameRecovery=dt*(maximum*rate);
        require(std::isfinite(dt) && dt>0.f && dt<=0.5f && std::isfinite(maximum)
            && maximum>0.f && std::fabs(maximum-initialHealth)<0.01f
            && std::isfinite(rate) && rate>=0.f && std::isfinite(frameRecovery),
            "invalid/changing native regeneration parameters");
        if (delta>0.f) {
            regeneration+=frameRecovery; ++regenerationFrames;
            require(regeneration<5.f,"native regeneration exceeds bounded 5 HP observation budget");
            std::printf("P2_PURPLE_COMBAT_REGEN uid=%u frame=%d dt=%.6f max_health=%.3f rate=%.8f frame_recovery=%.6f total_recovery=%.6f raw_delta=%.6f compensated_delta=%.6f\n",
                targetUid,regenerationFrames,dt,maximum,rate,frameRecovery,regeneration,delta,delta+regeneration);
        }
        const auto flight=pc_p2_purple_flight_sample(acquired);
        // Let the native throw reach its descent phase. Stage only the source
        // once; collision traversal and attack dispatch remain engine-owned.
        // This bounded collision setup deliberately does not certify aiming.
        if (!descentStaged && !isolated && delta==0.f && maxQueued==0.f
            && flight.phase==PcP2PurpleFlightPhase::Descent) {
            acquired->resetPosition(target->mSRT.t+Vector3f(0,80,0));
            acquired->mVelocity=Vector3f(0,-100,0);
            acquired->mTargetVelocity=acquired->mVelocity;
            descentStaged=true;
            std::printf("P2_PURPLE_COMBAT_DESCENT_SETUP uid=%u source=2 source_position_staged=1 source_velocity_staged=1 flight_phase_injected=0 enemy_modified=0 collision_injected=0\n",targetUid);
        }
        if (!isolated && (delta>0.f || maxQueued>0.f)) {
            // Stop follow-up ordinary attacks after native collision evidence.
            // Do not touch enemy damage queues, health, or FSM.
            if (acquired->isStickTo()) acquired->endStickObject();
            acquired->changeMode(PikiMode::FreeMode,n);
            acquired->resetPosition(parkPosition);
            n->resetPosition(parkPosition);
            isolated=true;
            std::printf("P2_PURPLE_COMBAT_CONTACT_OBSERVATION uid=%u source=2 target=%p piki=%p health_before=%.3f health_after=%.3f delta=%.3f queued=%.3f flight=%d post_contact_source_isolated=1 production_collision_marker_required=1\n",
                targetUid,static_cast<void*>(target),static_cast<void*>(acquired),initialHealth,target->mHealth,delta,target->mStoredDamage,int(flight.phase));
        }
        // Retry only an undamaging completed throw after native recovery; do
        // not force the Pikmin state/flight to finish or replay a claimed hit.
        if (!isolated && combatTicks-throwTick>=180 && delta==0.f && maxQueued==0.f
            && acquired->getState()==PIKISTATE_Normal && !acquired->isStickTo()
            && !pc_p2_purple_flight_active(acquired)) {
            require(throwAttempts<3,"three completed native throws missed adult direct damage");
            std::printf("P2_PURPLE_COMBAT_RETRY uid=%u source=2 completed_attempt=%d native_recovery=1 health=%.3f queue=%.3f\n",
                targetUid,throwAttempts,target->mHealth,target->mStoredDamage);
            thrown=false; descentStaged=false;
        }
        if (isolated && ++observedTicks>=30 && target->mStoredDamage==0.f) {
            require(delta>45.f && delta<=50.f && std::fabs(delta+regeneration-50.f)<0.05f,
                "adult native health delta plus measured regeneration is not 50");
            require(maxQueued==0.f || std::fabs(maxQueued-50.f)<0.01f,"unexpected observed queued damage");
            std::printf("P2_PURPLE_COMBAT_HEALTH_EVIDENCE mode=adult_direct uid=%u source=2 target=%p piki=%p health_before=%.3f health_after=%.3f delta=%.3f max_observed_queue=%.3f regeneration=%.6f compensated_delta=%.6f regen_frames=%d exact_production_queue_delta_required=50 native_throw=1 injected_damage=0 forced_enemy_state=0 production_collision_marker_required=1 dwarf_quake_pending=1 dwarf_crush_pending=1\n",
                targetUid,static_cast<void*>(target),static_cast<void*>(acquired),initialHealth,target->mHealth,delta,maxQueued,regeneration,delta+regeneration,regenerationFrames);
            std::fflush(nullptr); std::_Exit(0);
        }
    }


public:
    int idle() override {
        const int result=PlugPikiApp::idle();
        Navi* n=naviMgr?naviMgr->getNavi():nullptr;
        if(n) {
            captainSeen=true;
            p2_fixture_require_captain(GameStat::orimaDead,n->getCurrState()&&n->getCurrState()->getID()==NAVISTATE_Dead,n->mHealth,ticks);
        } else {
            const bool expectedTeardown=sunsetRequested && sunsetSeen
                && gameflow.mCurrGameSectionID==SECTION_OnePlayer && flowCont.mGameEndFlag==GAMEEND_None
                && gameflow.mWorldClock.mCurrentDay==expectedDay && stockOne();
            require(!captainSeen || expectedTeardown,"captain disappeared outside expected sunset teardown");
        }
        if (++ticks%120==0) diagnostics(n);
        require(ticks<(sunsetRequested?15000:6000),"global fixture timeout");
        if(mode("persistence_resume")) pc_p2_input_script_set(1,(!n || gameflow.mIsUIOverlayActive) && ticks%20<4?KBBTN_A:0,0,0);
        if(sunsetRequested) {
            sunsetStep();
            if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive) gameflow.mMoviePlayer->requestSkip();
            return result;
        }
        if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive) { gameflow.mMoviePlayer->requestSkip(); return result; }
        if(!n||!pikiMgr||!itemMgr||!bossMgr||!tekiMgr||!mapMgr||!n->getCurrState()
            ||gameflow.mPauseAll||gameflow.mIsUIOverlayActive) return result;
        if(mode("persistence_resume")) {
            // The restored captain exists during ship/map entry before the
            // playable stage actors are ready. Match the ordinary fixture's
            // active walk/idle gate before checking live combat bindings.
            const int state=n->getCurrState()->getID();
            if(state==NAVISTATE_Walk || state==NAVISTATE_Idle) resumePersistence(n);
            return result;
        }
        if (!acquired) {
            const int state=n->getCurrState()->getID();
            if(state==NAVISTATE_Walk||state==NAVISTATE_Idle) {
                acquired=naturalStep(n);
            }
            return result;
        }
        if(mode("persistence_dayend")) beginPersistence(n); else combatStep(n);
        return result;
    }
};
int main(int argc,char** argv) {
    if(std::getenv("P2_FIXTURE_FORCE_CAPTAIN_DOWN")) p2_fixture_require_captain(false,false,0,0);
    setvbuf(stdout,nullptr,_IONBF,0);
    const char* mode=std::getenv("P2_PURPLE_COMBAT_MODE");
    if(mode && std::strcmp(mode,"adult_direct") && std::strcmp(mode,"persistence_dayend") && std::strcmp(mode,"persistence_resume")) {
        std::printf("P2_PURPLE_COMBAT_UNIMPLEMENTED mode=%s implemented=adult_direct,persistence_dayend,persistence_resume\n",mode); return 2;
    }
    SDL_SetMainReady(); pc_gpu_preference_apply(); pc_bbft_init(argc,argv);
    require(pc_randomizer_purple_campaign() && pc_randomizer_p2_bridge(),"ordinary Purple seed campaign required");
    if(!pc_window_init("Purple campaign combat fixture",960,540)) return 3;
    pc_settings_init(); pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);
    pc_window_set_window_size(960,540); pc_window_center();
    std::puts("Experimental preview window set to 960x540 windowed and centered");
    int w=0,h=0,x=0,y=0; SDL_Window* window=SDL_GL_GetCurrentWindow();
    SDL_GetWindowSize(window,&w,&h); SDL_GetWindowPosition(window,&x,&y);
    require(w==960&&h==540,"window dimensions");
    std::printf("P2_FIXTURE_WINDOW width=%d height=%d x=%d y=%d\n",w,h,x,y);
    std::printf("P2_PURPLE_COMBAT_SCOPE mode=%s natural_acquisition=1 player_controls_validated=0 production_collision_marker_required=1\n",mode?mode:"adult_direct");
    gsys->Initialise(); pc_settings_p2d_init(); nodeMgr=new NodeMgr();
    gsys->run(new PurpleCombatApp()); return 0;
}
