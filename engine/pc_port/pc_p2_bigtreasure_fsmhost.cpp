#include "pc_p2_bigtreasure_fsmhost.h"

void P2BigTreasureFsmHost::reset(const P2BigTreasureFsmParms& parms)
{
    mFsm.reset(parms);
    mChosenWeapon = -1;
    mBossHealth   = 1.0f;
    mKnockOffs    = 0;
}

void P2BigTreasureFsmHost::tick(P2BigTreasureHostSeam& seam,
                                const P2BigTreasureFsmHostInput& in,
                                P2BigTreasureFsmHostOutput& out)
{
    out = P2BigTreasureFsmHostOutput{};
    if (!seam.active) {
        return;
    }
    mBossHealth = in.bossHealth;

    // 1. Incoming damage is routed by ownership against the current FSM phase
    // (Land quarters Pikmin damage; body parts only register at zero weapons).
    if (in.damage > 0.0f) {
        out.damageResult = seam.ownership.damageCallBack(
            /*fromPiki=*/true, /*hasCollPart=*/true, in.damageWeapon, in.damage, mFsm.state(),
            in.damageBittered, &out.pinchSmoke);
    }

    // 2. Knock off every weapon that reached zero HP. This is the observable
    // phase transition; the FSM observes the reduced loadout below.
    P2BigTreasureDropEvent drops[P2BTWEAPON_Count];
    const std::size_t dropped = seam.ownership.update(drops, P2BTWEAPON_Count);
    out.knockedOff = static_cast<int>(dropped);
    mKnockOffs += dropped;

    // 3. Advance the FSM with the post-damage loadout.
    P2BigTreasureFsmInput fsmIn;
    fsmIn.health        = mBossHealth;
    fsmIn.hasAnyWeapon  = seam.ownership.hasAnyWeapon();
    for (int weapon = 0; weapon < P2BTWEAPON_Count; ++weapon) {
        fsmIn.weaponAttached[weapon] = seam.ownership.isWeaponAttached(weapon);
    }
    fsmIn.chosenWeapon        = mChosenWeapon;
    fsmIn.hasTarget           = in.hasTarget;
    fsmIn.bootDemoPlayed      = in.bootDemoPlayed;
    fsmIn.animEnd             = in.animEnd;
    fsmIn.keyEvent2           = in.keyEvent2;
    fsmIn.keyEvent100         = in.keyEvent100;
    fsmIn.flickTrigger        = in.flickTrigger;
    fsmIn.attackLimitTime     = in.attackLimitTime;
    fsmIn.shouldFinishMotion  = in.shouldFinishMotion;
    fsmIn.finishIKMotion      = in.finishIKMotion;
    fsmIn.itemWalkSwapped     = in.itemWalkSwapped;
    fsmIn.killed              = in.killed;
    mFsm.update(fsmIn, out.fsm);

    // 4. Perform the actions the policy requested last tick (order matters:
    // pick first, then the attack start uses the chosen index).
    if (out.fsm.pickWeapon) {
        mChosenWeapon = seam.ownership.pickWeapon(in.pickThreshold);
    }
    if (out.fsm.resetAttackLimitTimer) {
        seam.director.pacer.reset(seam.placement.initialTimer);
    }
    if (out.fsm.startAttack && mChosenWeapon >= 0) {
        if (seam.director.pools.start(mChosenWeapon)) {
            ++seam.attacksStarted;
        }
    }
    if (out.fsm.finishAttack) {
        seam.director.pools.finishAttack();
    }
    if (out.fsm.releaseLoozy) {
        P2BigTreasureDropEvent drop;
        seam.ownership.releaseLouie(&drop);
    }

    out.liveWeapons = seam.ownership.weaponCount();
    out.bodyExposed = seam.ownership.isBodyExposed();
}
