#include "pc_p2_bigtreasure_ordinary.h"

#include <cmath>

void P2BigTreasureOrdinary::reset(const P2BigTreasureFsmParms& parms)
{
    mHost.reset(parms);
    mHead = 0;
    mCount = 0;
}

bool P2BigTreasureOrdinary::postHit(const P2BigTreasureOrdinaryHit& hit)
{
    if (!std::isfinite(hit.damage) || hit.damage <= 0.0f) {
        return false;
    }
    if (hit.weapon < -1 || hit.weapon >= P2BTWEAPON_Count) {
        return false;
    }
    if (mCount >= kHitQueueCapacity) {
        return false;
    }
    mHits[(mHead + mCount) % kHitQueueCapacity] = hit;
    ++mCount;
    return true;
}

bool P2BigTreasureOrdinary::pop(P2BigTreasureOrdinaryHit& out)
{
    if (mCount <= 0) {
        return false;
    }
    out = mHits[mHead];
    mHead = (mHead + 1) % kHitQueueCapacity;
    --mCount;
    return true;
}

void P2BigTreasureOrdinary::tick(P2BigTreasureHostSeam& seam,
                                 const P2BigTreasureOrdinaryFacts& facts,
                                 P2BigTreasureFsmHostOutput& out)
{
    out = P2BigTreasureFsmHostOutput{};
    if (!seam.active) {
        return;
    }

    P2BigTreasureFsmHostInput in;
    in.hasTarget = facts.hasTarget;
    in.bootDemoPlayed = facts.bootDemoPlayed;
    in.animEnd = facts.animEnd;
    in.keyEvent2 = facts.keyEvent2;
    in.keyEvent100 = facts.keyEvent100;
    in.flickTrigger = facts.flickTrigger;
    in.shouldFinishMotion = facts.shouldFinishMotion;
    in.finishIKMotion = facts.finishIKMotion;
    in.itemWalkSwapped = facts.itemWalkSwapped;
    in.killed = facts.killed;
    in.pickThreshold = facts.pickThreshold;
    in.bossHealth = facts.bossHealth;

    // Source isAttackLimitTime(): the pacing timer gates the ItemWalk / ItemWait
    // -> PreAttack transition. It accrues here, exactly once per source tick,
    // and the policy resets it (resetAttackLimitTimer action) on PreAttack.
    in.attackLimitTime = seam.director.pacer.tick(
        facts.delta, seam.ownership.weaponCount(), facts.targetInBox,
        facts.unstuckOutsiderNearby);

    // Natural-hit ingress: at most one damage callback per source tick, in
    // arrival order.
    P2BigTreasureOrdinaryHit hit;
    if (pop(hit)) {
        in.damage = hit.damage;
        in.damageWeapon = hit.weapon;
        in.damageBittered = hit.bittered;
    }

    mHost.tick(seam, in, out);
}
