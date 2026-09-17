#include "pc_p2_waterwraith_encounter.h"

#include "pc_p2_waterwraith_attack_policy.h"
#include "pc_p2_purple.h"

#include "Interactions.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Generator.h"
#include "teki.h"
#include "pc_randomizer.h"
#include "pc_p2_generated_placement.h"

#include <cmath>
#include <cstdio>
#include <fstream>
#include <string>

namespace {
constexpr int kMaxTargets = 64;

P2WaterwraithEncounterStats sStats;
bool sStunEdge = false;
// Last reported actor-owned steering state (muse l63, #503).
P2WaterwraithSteerMode sLastSteerMode = P2WWSTEER_Hold;
P2WaterwraithMotion sLastMotion = P2WWMOTION_None;
bool sTiredEdge = false;

// Generated-claim arm (consumer #572, gate1): bind the placement-owned
// seeded Teki named by p2-waterwraith-generated.txt. Observation only:
// verifies liveness, placement acceptance and seed source, then logs the
// bind; per-tick revalidation forgets on loss. Never touches the fixed
// rig, fixed markers, health, transport or receipts. The claimed pointer
// is compared, never dereferenced after birth (a dead actor may be freed):
// loss reasons stay coarse (lost/changed) by design.
Teki* sClaimed = nullptr;
bool sClaimSidecarTried = false;
bool sClaimSidecarValid = false;
unsigned sClaimGenerator = 0;
unsigned sClaimSlot = 0;

bool readGeneratedSidecar(unsigned& generator, unsigned& slot)
{
    generator = 0;
    slot = 0;
    std::ifstream in("p2-waterwraith-generated.txt");
    if (!in) {
        return false;
    }
    std::string magic;
    unsigned gen = 0;
    unsigned sl = 0;
    std::string tail;
    if (!(in >> magic) || magic != "P2_WATERWRAITH_GENERATED_1") {
        std::printf("P2_WATERWRAITH_GENERATED_SIDECAR skipped=bad-magic\n");
        std::fflush(stdout);
        return false;
    }
    if (!(in >> gen >> sl) || !gen || !sl || (in >> tail)) {
        std::printf("P2_WATERWRAITH_GENERATED_SIDECAR skipped=malformed\n");
        std::fflush(stdout);
        return false;
    }
    generator = gen;
    slot = sl;
    return true;
}

Teki* findGeneratedActor(unsigned generator, unsigned slot)
{
    if (!tekiMgr || !generator || !slot) {
        return nullptr;
    }
    Iterator it(tekiMgr);
    CI_LOOP(it)
    {
        Teki* candidate = static_cast<Teki*>(*it);
        if (!candidate || !candidate->mGenerator
            || candidate->mGenerator->_70 != generator) {
            continue;
        }
        if (!candidate->isAlive()) {
            continue;
        }
        if (!pc_p2_generated_placement_is_bound(static_cast<BTeki*>(candidate))) {
            continue;
        }
        const unsigned uid = pc_randomizer_generator_id(candidate->mGenerator);
        if (!uid || uid != slot) {
            continue;
        }
        if (pc_randomizer_p2_source_for_id(uid) != 99) {
            continue;
        }
        return candidate;
    }
    return nullptr;
}

void updateGeneratedClaim()
{
    if (!sClaimSidecarTried) {
        sClaimSidecarTried = true;
        sClaimSidecarValid = readGeneratedSidecar(sClaimGenerator, sClaimSlot);
    }
    if (!sClaimSidecarValid) {
        return;
    }
    Teki* actor = findGeneratedActor(sClaimGenerator, sClaimSlot);
    if (!sClaimed) {
        if (!actor) {
            return;
        }
        sClaimed = actor;
        std::printf("P2_WATERWRAITH_GENERATED_BIND generator=%u slot=%u source=99 type=%d\n",
                    sClaimGenerator, sClaimSlot, static_cast<int>(actor->mTekiType));
        std::fflush(stdout);
        return;
    }
    if (actor != sClaimed) {
        const unsigned gen = sClaimGenerator;
        sClaimed = nullptr;
        std::printf("P2_WATERWRAITH_GENERATED_FORGET generator=%u reason=%s\n",
                    gen, actor ? "changed" : "lost");
        std::fflush(stdout);
    }
}

bool hitRange(float ax, float az, float bx, float bz, float radius)
{
    return p2wwatk::inRange(ax, az, bx, bz, radius);
}
} // namespace

void pc_p2_waterwraith_encounter_reset()
{
    sStats = P2WaterwraithEncounterStats();
    sStunEdge = false;
    sLastSteerMode = P2WWSTEER_Hold;
    sLastMotion = P2WWMOTION_None;
    sTiredEdge = false;
    sClaimed = nullptr;
    sClaimSidecarTried = false;
    sClaimSidecarValid = false;
    sClaimGenerator = 0;
    sClaimSlot = 0;
}

bool pc_p2_waterwraith_encounter_ready()
{
    return true;
}

const P2WaterwraithEncounterStats& pc_p2_waterwraith_encounter_stats()
{
    return sStats;
}

void pc_p2_waterwraith_encounter_step(P2WaterwraithActor& actor, P2WaterwraithActorInput& in)
{
    p2wwatk::Rule rule;
    P2WaterwraithRig& rig = actor.rig();

    ++sStats.ticks;

    updateGeneratedClaim();

    // Autonomous driver feeds (muse l63, #503). The live active-captain XZ is
    // the source walkFunc chase target (:874); read from the live engine with
    // the same natural pattern as the crush attribution below, never
    // synthesized. This host exposes no live Pod position, so podValid stays
    // false and pod-seek remains engine-free verified.
    in.captainValid = false;
    in.podValid = false;
    if (naviMgr && naviMgr->getActiveNavi()) {
        Navi* captain = naviMgr->getActiveNavi();
        if (captain && captain->isAlive()) {
            const Vector3f captainPos = captain->getPosition();
            in.captainValid = true;
            in.captainX = captainPos.x;
            in.captainZ = captainPos.z;
        }
    }

    // Observed birth state (muse l63, #503): report the actual actor birth
    // (phase + Tyre child attachment + source IDs) once, from live state.
    if (sStats.ticks == 1) {
        const bool attached = rig.alive() && rig.attachedToOwner();
        std::printf("P2_WATERWRAITH_BIRTH phase=%s attached=%d id=99 helper=98\n",
                    P2WaterwraithActor::phaseName(actor.phase()), attached ? 1 : 0);
    }

    const bool attached = rig.alive() && rig.attachedToOwner();
    const bool damageable = attached && rig.damageable();
    const bool rolling = attached && rig.tyrePhase() != P2TYRE_Freeze;
    const P2WaterwraithVec3 reference = attached ? rig.position() : actor.position();

    // Gather the live squad's planar targets once per source tick.
    p2wwatk::Target targets[kMaxTargets];
    int count = 0;
    if (pikiMgr) {
        Iterator iterator(pikiMgr);
        CI_LOOP(iterator) {
            Piki* piki = static_cast<Piki*>(*iterator);
            if (!piki || !piki->isAlive() || count >= kMaxTargets) {
                continue;
            }
            const Vector3f position = piki->getPosition();
            p2wwatk::Target& target = targets[count++];
            target.x = position.x;
            target.z = position.z;
            target.purple = pc_p2_is_purple(piki);
            target.alive = true;
        }
    }

    const p2wwatk::Evaluation evaluation
        = p2wwatk::evaluate(rule, reference.x, reference.z, attached, damageable, rolling, targets,
                            count);

    // A Purple landing stun: request the roller quakeFreeze while the rig is
    // closed. Repeated requests are harmless (the rig accepts only Move); the
    // counter/evidence records the edge where the stun actually lands.
    if ((evaluation.actions & p2wwatk::ActionStun) != 0u) {
        in.quakeFreeze = true;
        if (!sStunEdge && rig.tyrePhase() == P2TYRE_Move) {
            ++sStats.stunned;
            std::printf("P2_WATERWRAITH_STUN tick=%llu rollerHealth=%.1f\n",
                        static_cast<unsigned long long>(sStats.ticks), rig.tyreHealth());
            sStunEdge = true;
        }
    } else {
        sStunEdge = false;
    }

    // Accepted hits: one damage packet per target in hit range. While attached
    // only Purple Pikmin damage the roller; after dismount the exposed body
    // accepts a hit from any Pikmin (source blackMan.cpp:680).
    if ((evaluation.actions & p2wwatk::ActionHit) != 0u) {
        for (int i = 0; i < count; ++i) {
            const p2wwatk::Target& target = targets[i];
            if (!target.alive
                || !hitRange(target.x, target.z, reference.x, reference.z, rule.hitRadius)) {
                continue;
            }
            if (p2_waterwraith_actor_apply_damage(actor, rule.purpleHitDamage, target.purple,
                                                  nullptr)
                == P2WWDMG_Ignored) {
                continue;
            }
            ++sStats.acceptedHits;
            sStats.damageDealt += rule.purpleHitDamage;
            std::printf("P2_WATERWRAITH_HIT tick=%llu attached=%d purple=%d rollerHealth=%.1f bodyHealth=%.1f\n",
                        static_cast<unsigned long long>(sStats.ticks), attached ? 1 : 0,
                        target.purple ? 1 : 0, rig.tyreHealth(), actor.bodyHealth());
        }
    }

    // Roller crush: flick non-Purple Pikmin under the rolling wraith. The
    // acting owner is the resident captain: the source attribution creature is
    // not present on this host actor (recorded adaptation).
    if ((evaluation.actions & p2wwatk::ActionCrush) != 0u && naviMgr && naviMgr->getNavi()) {
        Creature* owner = naviMgr->getNavi();
        int crushed = 0;
        if (pikiMgr) {
            Iterator iterator(pikiMgr);
            CI_LOOP(iterator) {
                Piki* piki = static_cast<Piki*>(*iterator);
                if (!piki || !piki->isAlive() || pc_p2_is_purple(piki)) {
                    continue;
                }
                const Vector3f position = piki->getPosition();
                if (!hitRange(position.x, position.z, reference.x, reference.z, rule.crushRadius)) {
                    continue;
                }
                if (piki->stimulate(InteractFlick(owner, rule.crushKnockback, rule.crushDamage, 0.0f))) {
                    ++crushed;
                }
            }
        }
        if (crushed > 0) {
            sStats.crushes += static_cast<std::uint64_t>(crushed);
            std::printf("P2_WATERWRAITH_CRUSH tick=%llu count=%d\n",
                        static_cast<unsigned long long>(sStats.ticks), crushed);
        }
    }

    // Host death script (source roller death -> dismount -> tyre_getoff ->
    // child removal). Once the Tyre is gone the exposed body stays damageable.
    if (attached && rig.tyreHealth() <= 0.0f) {
        if (!sStats.rollerZeroed) {
            sStats.rollerZeroed = true;
            std::printf("P2_WATERWRAITH_ROLLER_ZERO tick=%llu\n",
                        static_cast<unsigned long long>(sStats.ticks));
        }
        in.isTyreDead = true;
    } else if (!attached && rig.alive() && rig.tyreHealth() <= 0.0f && rig.ownerInvulnerableSet()) {
        if (rig.tyrePhase() != P2TYRE_Dead) {
            in.tyreDeathStart = true;
        } else {
            in.tyreDeadAnimEnd = true;
        }
    } else if (!attached && !rig.alive() && !sStats.childRemoved) {
        sStats.childRemoved = true;
        std::printf("P2_WATERWRAITH_TYRE_REMOVED tick=%llu\n",
                    static_cast<unsigned long long>(sStats.ticks));
    }

    // Wraith body resolution: end the escape, then the source Dead key sequence
    // (KEYEVENT_5 releases the treasure, KEYEVENT_END kills).
    if (actor.bodyZeroed() && !sStats.bodyZeroed) {
        sStats.bodyZeroed = true;
        std::printf("P2_WATERWRAITH_BODY_ZERO tick=%llu bodyHealth=0.0\n",
                    static_cast<unsigned long long>(sStats.ticks));
    }
    if (actor.phase() == P2BM_Escape) {
        in.animEnd = true;
    } else if (actor.phase() == P2BM_Dead) {
        if (!sStats.treasureReleased) {
            sStats.treasureReleased = true;
            in.keyEvent5 = true;
            std::printf("P2_WATERWRAITH_TREASURE tick=%llu\n",
                        static_cast<unsigned long long>(sStats.ticks));
        } else if (!sStats.killed) {
            sStats.killed = true;
            in.animEnd = true;
            std::printf("P2_WATERWRAITH_KILL tick=%llu\n",
                        static_cast<unsigned long long>(sStats.ticks));
        }
    }

    // Movement observation (muse l63, #503): report the actor-owned steering
    // state set by the last policy tick plus planar travel from the first
    // observation. Emitted on mode/motion change and every 60 ticks.
    const P2WaterwraithVec3 observed = actor.position();
    if (!sStats.birthRecorded) {
        sStats.birthRecorded = true;
        sStats.birthX = observed.x;
        sStats.birthZ = observed.z;
    }
    const float travelX = observed.x - sStats.birthX;
    const float travelZ = observed.z - sStats.birthZ;
    sStats.travel = std::sqrt(travelX * travelX + travelZ * travelZ);
    const P2WaterwraithSteerMode steerMode = actor.steerMode();
    const P2WaterwraithMotion motion = actor.lastMotion();
    if (steerMode != P2WWSTEER_Hold) {
        ++sStats.steerTicks;
    }
    if (steerMode == P2WWSTEER_Chase) {
        ++sStats.chaseTicks;
    }
    if (steerMode != sLastSteerMode || motion != sLastMotion || (sStats.ticks % 60u) == 0u) {
        const char* band = "-";
        if (in.captainValid && steerMode == P2WWSTEER_Chase) {
            const float chaseDx = in.captainX - observed.x;
            const float chaseDz = in.captainZ - observed.z;
            const float chaseD2 = chaseDx * chaseDx + chaseDz * chaseDz;
            band = chaseD2 > 640000.0f ? "far" : (chaseD2 > 160000.0f ? "mid" : "near");
        }
        std::printf("P2_WATERWRAITH_STEER tick=%llu mode=%s motion=%s band=%s travel=%.1f escape=%d\n",
                    static_cast<unsigned long long>(sStats.ticks),
                    P2WaterwraithActor::steerModeName(steerMode),
                    P2WaterwraithActor::motionName(motion), band, sStats.travel,
                    actor.escapePhase());
        sLastSteerMode = steerMode;
        sLastMotion = motion;
    }
    // Wind-down + cadence edges (muse l63, #503): report the autonomous
    // Tired entry and each route-refresh request once, from live actor state.
    if (actor.phase() == P2BM_Tired && !sTiredEdge) {
        sTiredEdge = true;
        std::printf("P2_WATERWRAITH_TIRED tick=%llu\n",
                    static_cast<unsigned long long>(sStats.ticks));
    } else if (actor.phase() != P2BM_Tired) {
        sTiredEdge = false;
    }
    if (actor.routeRefreshPending()) {
        actor.ackRouteRefresh();
        std::printf("P2_WATERWRAITH_ROUTE_REFRESH tick=%llu\n",
                    static_cast<unsigned long long>(sStats.ticks));
    }
}
