#include "pc_p2_waterwraith_encounter.h"

#include "pc_p2_waterwraith_attack_policy.h"
#include "pc_p2_purple.h"

#include "Interactions.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Piki.h"
#include "PikiMgr.h"

#include <cmath>
#include <cstdio>

namespace {
constexpr int kMaxTargets = 64;

P2WaterwraithEncounterStats sStats;
bool sStunEdge = false;

bool hitRange(float ax, float az, float bx, float bz, float radius)
{
    return p2wwatk::inRange(ax, az, bx, bz, radius);
}
} // namespace

void pc_p2_waterwraith_encounter_reset()
{
    sStats = P2WaterwraithEncounterStats();
    sStunEdge = false;
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

    // Accepted Purple hits: one damage packet per Purple target in hit range.
    if ((evaluation.actions & p2wwatk::ActionHit) != 0u) {
        for (int i = 0; i < count; ++i) {
            const p2wwatk::Target& target = targets[i];
            if (!target.alive || !target.purple
                || !hitRange(target.x, target.z, reference.x, reference.z, rule.hitRadius)) {
                continue;
            }
            if (p2_waterwraith_actor_apply_damage(actor, rule.purpleHitDamage, true, nullptr) == P2WWDMG_Ignored) {
                continue;
            }
            ++sStats.purpleHits;
            sStats.damageDealt += rule.purpleHitDamage;
            std::printf("P2_WATERWRAITH_HIT tick=%llu attached=%d rollerHealth=%.1f bodyHealth=%.1f\n",
                        static_cast<unsigned long long>(sStats.ticks), attached ? 1 : 0,
                        rig.tyreHealth(), actor.bodyHealth());
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
}
