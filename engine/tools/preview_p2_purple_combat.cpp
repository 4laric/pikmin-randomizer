// #940 isolated campaign combat fixture: adult_direct, dwarf_quake, dwarf_crush_stunned.
// Quake acceptance additionally requires matching accepted production QUAKE/
// IMPACT tokens and no DIRECT event for the tested source/target. Stunned crush
// instead requires exactly one direct native 16-to-2 transition for its sole
// crush throw. Exit zero supplies evidence; reward delivery is not exercised.
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
#include "pc_p2_purple_direct.h"
#include "pc_p2_purple_flight.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_chappy.h"
#include "pc_p2_kochappy.h"
#include "pc_p2_kochappy_stun.h"
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
    bool crushMode() const {
        const char* mode=std::getenv("P2_PURPLE_COMBAT_MODE");
        return mode && std::strcmp(mode,"dwarf_crush_stunned")==0;
    }
    bool dwarfMode() const {
        const char* mode=std::getenv("P2_PURPLE_COMBAT_MODE");
        return mode && (std::strcmp(mode,"dwarf_quake")==0 || crushMode());
    }
    BTeki* dwarf=nullptr;
    unsigned dwarfUid=0;
    unsigned long long dwarfLifetime=0;
    float dwarfHealth=0, retainedFit=0, lastFit=0;
    int quakeAttempts=0, quakeTick=0, quakeLastPhase=0;
    bool quakeFlying=false, quakeStaged=false, quakeAccepted=false;
    bool quakeBounce=false, quakeAirborne=false, quakeRecovery=false;
    bool quakeFit=false, quakeRepeat=false, quakeRetained=false;
    bool quakePositionChecked=false;
    bool crushStarted=false, crushThrown=false, crushStaged=false, crushPressed=false, crushDead=false;
    bool crushIsolated=false, crushCancelled=false;
    int crushTicks=0, crushPressEntries=0, crushPreviousState=16, crushCorpseTicks=0, crushKillsBefore=0;
    PelletView* crushView=nullptr;
    std::set<Pellet*> crushCorpses;
    std::chrono::steady_clock::time_point acquisitionTime;

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

    bool dwarfPresent() const {
        Iterator enemies(tekiMgr);
        CI_LOOP(enemies) {
            BTeki* actor=static_cast<BTeki*>(*enemies);
            if(actor==dwarf && pc_p2_campaign_source(actor)==1
                && pc_randomizer_generator_id(actor->mGenerator)==dwarfUid) return true;
        }
        return false;
    }

    void crushStep(Navi* n) {
        require(++crushTicks<1800,"stunned crush press/death/corpse path timed out");
        require(acquired->isAlive() && pc_p2_is_purple(acquired),"crush acquired Purple lost");
        // Once native death detaches the generator, pointer/lifetime observation
        // replaces the now-unavailable live seed lookup. Never dereference an
        // actor absent from the manager; corpse linkage is compared as a value.
        bool present=false;
        Iterator enemies(tekiMgr);
        CI_LOOP(enemies) if(static_cast<BTeki*>(*enemies)==dwarf) { present=true; break; }
        const auto stun=pc_p2_kochappy_stun_sample(dwarf);
        int state=-1; float hp=-1, queue=-1;
        if(present) {
            state=dwarf->mStateID; hp=dwarf->mHealth; queue=dwarf->mStoredDamage;
            if(dwarf->mGenerator) require(pc_p2_campaign_source(dwarf)==1
                && pc_randomizer_generator_id(dwarf->mGenerator)==dwarfUid,"crush actor identity changed");
            if(stun.registered) require(stun.lifetime==dwarfLifetime,"crush actor lifetime reused");
            if(state==2 && crushPreviousState!=2) {
                ++crushPressEntries;
                require(crushThrown && crushPressEntries==1 && crushPreviousState==16,
                    "expected exactly one observed native Fit16-to-Pressed2 transition");
                require(stun.phase==0,"native press did not cancel quake lifecycle");
                crushPressed=true; crushCancelled=true;
                std::printf("P2_PURPLE_CRUSH_PRESSED_EVIDENCE uid=%u source=1 target=%p piki=%p pre_state=16 post_state=2 entries=%d stun_phase=%d health=%.3f queued=%.3f external_direct_marker_required=1\n",
                    dwarfUid,static_cast<void*>(dwarf),static_cast<void*>(acquired),crushPressEntries,stun.phase,hp,queue);
            }
            if(crushPressed && (dwarf->mDeadState || !dwarf->isAlive())) crushDead=true;
            crushPreviousState=state;
        }
        if(crushTicks%30==0 || crushTicks==1) std::printf("P2_PURPLE_CRUSH_PROGRESS uid=%u source=1 tick=%d present=%d state=%d stun_phase=%d fit=%.6f health=%.3f queued=%.3f pressed=%d dead=%d corpse_count=%zu kill_delta=%d\n",
            dwarfUid,crushTicks,int(present),state,stun.phase,stun.fitElapsed,hp,queue,int(crushPressed),int(crushDead),crushCorpses.size(),int(GameStat::killTekis)-crushKillsBefore);
        if(!crushThrown) {
            require(present && dwarfPresent() && state==16 && stun.registered && stun.phase==2 && stun.fitElapsed>0.f
                && stun.fitElapsed<7.f && dwarf->isAlive() && hp==dwarfHealth && queue==0.f,
                "stunned crush needs untouched naturally rolled Fit with enough throw time");
            crushView=static_cast<PelletView*>(dwarf); crushKillsBefore=GameStat::killTekis;
            require(pelletMgr!=nullptr,"crush missing pellet manager");
            Iterator pellets(pelletMgr);
            CI_LOOP(pellets) require(static_cast<Pellet*>(*pellets)->mPelletView!=crushView,"crush target already owns a corpse");
            const Vector3f pos=dwarf->mSRT.t;
            n->resetPosition(Vector3f(pos.x-100.f,mapMgr->getMinY(pos.x-100.f,pos.z,true),pos.z));
            acquired->changeMode(PikiMode::FreeMode,n); acquired->mFSM->transit(acquired,PIKISTATE_Flying);
            n->throwPiki(acquired,Vector3f(pos.x+42.f,pos.y,pos.z));
            require(pc_p2_purple_flight_active(acquired),"stunned crush native throw not armed");
            crushThrown=true;
            std::printf("P2_PURPLE_CRUSH_THROW uid=%u source=1 target=%p piki=%p target_state=16 stun_phase=2 fit=%.6f health_before=%.3f native_throw=1 throw_count=1 captain_position_staged=1 enemy_modified=0 controls_validated=0\n",
                dwarfUid,static_cast<void*>(dwarf),static_cast<void*>(acquired),stun.fitElapsed,hp);
            return;
        }
        if(!crushPressed) {
            require(present && state==16 && stun.phase==2 && dwarf->isAlive(),"crush target left native Fit before direct press");
            require(hp==dwarfHealth && queue==0.f,"pre-press health changed; direct/ordinary damage contaminates crush");
            if(!crushStaged && pc_p2_purple_flight_sample(acquired).phase==PcP2PurpleFlightPhase::Descent) {
                acquired->resetPosition(dwarf->mSRT.t+Vector3f(0,45.f,0));
                acquired->mVelocity=Vector3f(0,-100,0); acquired->mTargetVelocity=acquired->mVelocity;
                crushStaged=true;
                std::printf("P2_PURPLE_CRUSH_DESCENT_SETUP uid=%u source=1 pre_state=%d fit=%.6f source_position_staged=1 source_velocity_staged=1 enemy_modified=0 forced_rng=0 flight_phase_injected=0\n",dwarfUid,state,stun.fitElapsed);
            }
        }
        if(crushPressed && !crushIsolated) {
            if(acquired->isStickTo()) acquired->endStickObject();
            acquired->changeMode(PikiMode::FreeMode,n); acquired->resetPosition(parkPosition); n->resetPosition(parkPosition);
            crushIsolated=true;
        }
        require(present || crushPressed,"crush target disappeared before press evidence");
        if(crushPressed) require(stun.phase==0,"quake lifecycle reactivated after lethal press");
        int liveCorpses=0;
        Iterator pellets(pelletMgr);
        CI_LOOP(pellets) {
            Pellet* corpse=static_cast<Pellet*>(*pellets);
            if(corpse && corpse->isAlive() && corpse->mPelletView==crushView) { ++liveCorpses; crushCorpses.insert(corpse); }
        }
        require(liveCorpses<=1 && crushCorpses.size()<=1,"duplicate native corpse observed");
        const int kills=int(GameStat::killTekis)-crushKillsBefore;
        require(kills>=0 && kills<=1,"kill counter changed more than once during crush observation");
        if(liveCorpses==1) {
            require(crushPressed && crushCancelled && crushDead && crushPressEntries==1,"corpse without complete native press/death evidence");
            if(++crushCorpseTicks>=60) {
                require(kills==1,"native corpse did not produce exactly one kill count");
                std::printf("P2_PURPLE_CRUSH_STUNNED_EVIDENCE uid=%u source=1 target=%p piki=%p natural_fit=1 native_throw_count=1 observed_press_entries=1 stun_cancelled=1 native_death=1 unique_corpse=1 corpse_observed_frames=%d kill_delta=1 health_before=%.3f health_after=%.3f injected_damage=0 forced_enemy_state=0 forced_rng=0 external_direct_16_to_2_exactly_once_required=1 delivery_rewards_validated=0 death_animation_fidelity_validated=0\n",
                    dwarfUid,static_cast<void*>(dwarf),static_cast<void*>(acquired),crushCorpseTicks,dwarfHealth,hp);
                std::fflush(nullptr); std::_Exit(0);
            }
        } else require(crushCorpseTicks==0,"native corpse disappeared before duplicate-observation window completed");
    }
    void quakeStep(Navi* n) {
        ++quakeTick;
        require(acquired->isAlive() && pc_p2_is_purple(acquired),"quake acquired Purple lost");
        if (!dwarf) {
            require(pc_p2_purple_impact_enabled() && pc_p2_purple_flight_enabled(),"quake/flight profiles disabled");
            unsigned wanted=0;
            if (const char* text=std::getenv("P2_PURPLE_COMBAT_UID")) {
                char* end=nullptr; errno=0; const unsigned long value=std::strtoul(text,&end,10);
                require(*text && *text!='-' && end && !*end && !errno && value>0 && value<=UINT_MAX,"invalid decimal dwarf UID");
                wanted=static_cast<unsigned>(value);
            }
            Iterator enemies(tekiMgr);
            CI_LOOP(enemies) {
                BTeki* actor=static_cast<BTeki*>(*enemies);
                if (!actor || !actor->isAlive() || pc_p2_campaign_source(actor)!=1 || !pc_p2_kochappy_registered(actor)) continue;
                const unsigned uid=pc_randomizer_generator_id(actor->mGenerator);
                if (wanted && wanted!=uid) continue;
                if (!dwarf || uid<dwarfUid) { dwarf=actor; dwarfUid=uid; }
            }
            if (!dwarf) {
                if(quakeTick%120==0) std::printf("P2_PURPLE_QUAKE_FIXTURE_WAIT requested_uid=%u source=1 reason=no_registered_loaded_actor\n",wanted);
                return;
            }
            const auto sample=pc_p2_kochappy_stun_sample(dwarf);
            require(sample.registered && sample.phase==0,"dwarf initially stunned/unregistered");
            dwarfLifetime=sample.lifetime; dwarfHealth=dwarf->mHealth;
            require(std::isfinite(dwarfHealth) && dwarfHealth>0 && std::fabs(dwarfHealth-dwarf->getMaxLife())<0.01f
                && dwarf->mStoredDamage==0.f,"quake requires undamaged full-health dwarf");
            parkPosition=n->mSRT.t;
            Iterator squad(pikiMgr);
            CI_LOOP(squad) {
                Piki* p=static_cast<Piki*>(*squad);
                if(p && p!=acquired && p->isAlive()) {
                    require(!p->isStickTo(),"quake other squad member attached");
                    p->changeMode(PikiMode::FreeMode,n); p->resetPosition(parkPosition);
                }
            }
            std::printf("P2_PURPLE_QUAKE_FIXTURE_TARGET uid=%u source=1 target=%p piki=%p lifetime=%llu health=%.3f generated_actor=1 other_squad_parked=1\n",
                dwarfUid,static_cast<void*>(dwarf),static_cast<void*>(acquired),dwarfLifetime,dwarfHealth);
        }
        require(dwarfPresent() && dwarf->isAlive() && !dwarf->mDeadState,"quake target disappeared/died");
        const auto stun=pc_p2_kochappy_stun_sample(dwarf);
        require(stun.registered && stun.lifetime==dwarfLifetime,"quake target registration/lifetime changed");
        require(std::isfinite(dwarf->mHealth) && std::fabs(dwarf->mHealth-dwarfHealth)<0.01f
            && dwarf->mStoredDamage==0.f,"quake changed health/queued damage (direct hit or ordinary attack contaminates test)");
        require(std::isfinite(stun.fitElapsed) && std::isfinite(stun.fitDuration) && std::fabs(stun.fitDuration-10.f)<0.01f,
            "quake invalid Red Fit duration/timer");
        const bool eligible=dwarf->mGroundTriangle && !dwarf->isFlying()
            && !dwarf->getTekiOption(BTeki::TEKI_OPTION_INVINCIBLE)
            && dwarf->mStateID>=4 && dwarf->mStateID!=13 && dwarf->mStateID!=14 && dwarf->mStateID<=16;
        const auto flight=pc_p2_purple_flight_sample(acquired);
        if(quakeTick%60==0 || stun.phase!=quakeLastPhase) {
            std::printf("P2_PURPLE_QUAKE_FIXTURE_PROGRESS uid=%u source=1 attempt=%d tick=%d state=%d phase=%d previous_phase=%d fit=%.6f duration=%.3f bounce_updates=%u grounded=%d vy=%.3f eligible=%d flight=%d source_state=%d health=%.3f queued=%.3f repeated=%d retained=%d\n",
                dwarfUid,quakeAttempts,quakeTick,dwarf->mStateID,stun.phase,quakeLastPhase,stun.fitElapsed,stun.fitDuration,
                stun.bounceUpdates,int(dwarf->mGroundTriangle!=nullptr),dwarf->mVelocity.y,int(eligible),int(flight.phase),acquired->getState(),
                dwarf->mHealth,dwarf->mStoredDamage,int(quakeRepeat),int(quakeRetained));
        }
        if(quakeRepeat && quakeFlying && !quakeAccepted && stun.phase==2)
            retainedFit=stun.fitElapsed; // Last observed live timer before repeat contact.
        if(quakeFlying && stun.phase==1) {
            if(!quakeAccepted) {
                require(quakeStaged,"quake accepted before disclosed ground-only descent setup");
                quakeAccepted=true;
                if(quakeRepeat) {
                    const float dt=NSystem::getFrameTime();
                    require(std::isfinite(dt) && dt>0.f && dt<=0.5f && retainedFit>0.f
                        && stun.fitElapsed>=retainedFit && stun.fitElapsed<=retainedFit+dt+0.01f,
                        "repeat quake did not preserve observed positive Fit timer");
                }
                std::printf("P2_PURPLE_QUAKE_FIXTURE_BOUNCE uid=%u source=1 attempt=%d retained_before=%.6f retained_now=%.6f external_accepted_quake_required=1\n",
                    dwarfUid,quakeAttempts,retainedFit,stun.fitElapsed);
            }
            if(dwarf->mVelocity.y>0.f) quakeBounce=true;
            if(!dwarf->mGroundTriangle) quakeAirborne=true;
        }
        if(stun.phase==2 && quakeAccepted) {
            require(quakeBounce && quakeAirborne,"Fit without observed physical bounce/airborne interval");
            quakeFit=true; lastFit=stun.fitElapsed;
            if(quakeRepeat) {
                require(stun.fitElapsed>=retainedFit,"repeat return to Fit lost retained elapsed time");
                quakeRetained=true;
            }
        }
        if(quakeRetained && quakeLastPhase==2 && stun.phase==0) {
            const float dt=NSystem::getFrameTime();
            require(std::isfinite(dt) && dt>0 && dt<=0.5f && lastFit+dt>stun.fitDuration-0.01f
                && dwarf->mStateID!=16,"Fit interrupted before native timed recovery");
            require(quakeRecovery && quakePositionChecked,"missing natural source ground recovery/landing geometry");
            std::printf("P2_PURPLE_QUAKE_LIFECYCLE_EVIDENCE uid=%u source=1 target=%p piki=%p attempts=%d health_before=%.3f health_after=%.3f queued=%.3f bounce=1 airborne=1 natural_fit=1 repeated_quake=1 retained_fit=%.6f timed_recovery=1 injected_damage=0 forced_enemy_state=0 forced_rng=0 external_accepted_tokens_required=1 matching_direct_marker_forbidden=1 death_during_stun_pending=1 dwarf_crush_pending=1\n",
                dwarfUid,static_cast<void*>(dwarf),static_cast<void*>(acquired),quakeAttempts,dwarfHealth,dwarf->mHealth,dwarf->mStoredDamage,retainedFit);
            std::fflush(nullptr); std::_Exit(0);
        }
        if(quakeFlying && !quakeStaged && flight.phase==PcP2PurpleFlightPhase::Descent) {
            const float radius=dwarf->mCollisionRadius;
            require(std::isfinite(radius) && radius>=0.f,"invalid dwarf collision radius");
            const float x=dwarf->mSRT.t.x+radius+40.f, z=dwarf->mSRT.t.z;
            const float y=mapMgr->getMinY(x,z,true);
            require(std::isfinite(y),"nonfinite quake landing terrain");
            acquired->resetPosition(Vector3f(x,y+35.f,z));
            acquired->mVelocity=Vector3f(0,-100,0); acquired->mTargetVelocity=acquired->mVelocity;
            quakeStaged=true;
            std::printf("P2_PURPLE_QUAKE_DESCENT_SETUP uid=%u source=1 attempt=%d offset=%.3f terrain_y=%.3f source_position_staged=1 source_velocity_staged=1 enemy_modified=0 flight_phase_injected=0 collision_injected=0\n",
                dwarfUid,quakeAttempts,radius+40.f,y);
        }
        if(quakeFlying && flight.phase==PcP2PurpleFlightPhase::Recovery && !quakePositionChecked) {
            const float dx=acquired->mSRT.t.x-dwarf->mSRT.t.x, dz=acquired->mSRT.t.z-dwarf->mSRT.t.z;
            const float distance=std::sqrt(dx*dx+dz*dz), radius=dwarf->mCollisionRadius;
            std::printf("P2_PURPLE_QUAKE_LANDING uid=%u source=1 attempt=%d distance_xz=%.3f target_radius=%.3f wave_radius=%.3f source_recovery=1\n",dwarfUid,quakeAttempts,distance,radius,radius+60.f);
            require(std::isfinite(distance) && distance>radius+10.f && distance<=radius+60.f,"quake landing outside disclosed wave-only annulus");
            quakePositionChecked=true; quakeRecovery=true;
        }
        const bool sourceReady=acquired->getState()==PIKISTATE_Normal && !pc_p2_purple_flight_active(acquired) && !acquired->isStickTo();
        if(quakeFlying && sourceReady) {
            require(quakeRecovery && quakePositionChecked,"throw ended without observed ground recovery (possible direct collision)");
            acquired->changeMode(PikiMode::FreeMode,n); acquired->resetPosition(parkPosition); n->resetPosition(parkPosition);
            quakeFlying=false;
        }
        if(crushMode() && quakeFit && !quakeFlying && sourceReady && eligible && stun.phase==2 && stun.fitElapsed>=1.f) {
            require(quakeRecovery && quakePositionChecked,"crush missing preceding quake ground recovery");
            crushStarted=true; crushStep(n); return;
        }
        // Retry a naturally rejected/no-Fit branch only after source recovery.
        // During Fit, one further throw verifies retained time, then wait out
        // the native timer without another attack or target manipulation.
        const bool wantRepeat=!crushMode() && quakeFit && !quakeRepeat && stun.phase==2 && stun.fitElapsed>=1.f;
        const bool wantNew=!quakeFit && stun.phase==0;
        if(!quakeFlying && sourceReady && eligible && (wantRepeat || wantNew)) {
            require(quakeAttempts<24,"natural Fit/repeat branch unachieved after 24 completed throws");
            if(wantRepeat) { quakeRepeat=true; retainedFit=stun.fitElapsed; }
            const float radius=dwarf->mCollisionRadius;
            require(std::isfinite(radius) && radius>=0.f,"invalid prethrow dwarf radius");
            const float x=dwarf->mSRT.t.x+radius+140.f, z=dwarf->mSRT.t.z;
            n->resetPosition(Vector3f(x,mapMgr->getMinY(x,z,true),z));
            acquired->changeMode(PikiMode::FreeMode,n); acquired->mFSM->transit(acquired,PIKISTATE_Flying);
            n->throwPiki(acquired,Vector3f(dwarf->mSRT.t.x+radius+40.f,dwarf->mSRT.t.y,z));
            require(pc_p2_purple_flight_active(acquired),"quake native throw not armed");
            ++quakeAttempts; quakeFlying=true; quakeStaged=false; quakeAccepted=false;
            quakeBounce=false; quakeAirborne=false; quakeRecovery=false; quakePositionChecked=false;
            std::printf("P2_PURPLE_QUAKE_FIXTURE_THROW uid=%u source=1 target=%p piki=%p attempt=%d repeat_during_fit=%d fit_before=%.6f native_throw=1 captain_position_staged=1 controls_validated=0\n",
                dwarfUid,static_cast<void*>(dwarf),static_cast<void*>(acquired),quakeAttempts,int(quakeRepeat),retainedFit);
        }
        quakeLastPhase=stun.phase;
    }
public:
    int idle() override {
        const int result=PlugPikiApp::idle();
        Navi* n=naviMgr?naviMgr->getNavi():nullptr;
        if(n) {
            captainSeen=true;
            p2_fixture_require_captain(GameStat::orimaDead,n->getCurrState()&&n->getCurrState()->getID()==NAVISTATE_Dead,n->mHealth,ticks);
        } else require(!captainSeen,"captain disappeared");
        if (++ticks%120==0) diagnostics(n);
        if(dwarfMode() && acquired) {
            const double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-acquisitionTime).count();
            const double limit=crushMode()?300.0:240.0;
            if(seconds>=limit) std::printf("P2_PURPLE_QUAKE_TIMEOUT seconds=%.3f attempts=%d fit=%d repeat=%d retained=%d phase=%d\n",
                seconds,quakeAttempts,int(quakeFit),int(quakeRepeat),int(quakeRetained),quakeLastPhase);
            require(seconds<limit,"dwarf natural branch/death/recovery unachieved within mode wall-clock bound");
        } else require(ticks<6000,"global startup/acquisition/combat timeout");
        if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive) { gameflow.mMoviePlayer->requestSkip(); return result; }
        if(!n||!pikiMgr||!itemMgr||!bossMgr||!tekiMgr||!mapMgr||!n->getCurrState()
            ||gameflow.mPauseAll||gameflow.mIsUIOverlayActive) return result;
        if (!acquired) {
            const int state=n->getCurrState()->getID();
            if(state==NAVISTATE_Walk||state==NAVISTATE_Idle) {
                acquired=naturalStep(n);
                if(acquired) acquisitionTime=std::chrono::steady_clock::now();
            }
            return result;
        }
        if(crushStarted) crushStep(n); else if(dwarfMode()) quakeStep(n); else combatStep(n); return result;
    }
};
int main(int argc,char** argv) {
    if(std::getenv("P2_FIXTURE_FORCE_CAPTAIN_DOWN")) p2_fixture_require_captain(false,false,0,0);
    setvbuf(stdout,nullptr,_IONBF,0);
    const char* mode=std::getenv("P2_PURPLE_COMBAT_MODE");
    if(mode && std::strcmp(mode,"adult_direct") && std::strcmp(mode,"dwarf_quake") && std::strcmp(mode,"dwarf_crush_stunned")) {
        std::printf("P2_PURPLE_COMBAT_UNIMPLEMENTED mode=%s implemented=adult_direct,dwarf_quake,dwarf_crush_stunned\n",mode); return 2;
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
