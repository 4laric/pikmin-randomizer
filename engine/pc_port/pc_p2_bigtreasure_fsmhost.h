#pragma once

#include "pc_p2_bigtreasure_fsm.h"
#include "pc_p2_bigtreasure_host.h"

#include <cstdint>

// FSM host binding for the BigTreasure (Titan Dweevil, enemy ID 73) 12-state
// policy, issue #246. Drives P2BigTreasureFsm against the lane-owned host seam
// (P2BigTreasureHostSeam: ownership + attack director) at the 30 Hz source
// rate, performs the actions the policy requests, and routes incoming Pikmin
// damage to weapon HP. A weapon that reaches zero HP is knocked off through the
// ownership update; that is the observable phase transition (weapon-count and
// attack-pacing change while the body only becomes damageable at zero
// weapons). Engine-free: no actor, map, damage receiver, sound or effect
// dependency; every randomness input is host-supplied.

// Per-tick host inputs. The animation flags are keyframe pulses supplied by
// the caller; `damage` is the incoming Pikmin hit for this tick, with
// `damageWeapon` naming the hit weapon coll part (or -1 for a body part).
struct P2BigTreasureFsmHostInput {
    bool hasTarget = false;
    bool bootDemoPlayed = false;
    bool animEnd = false;
    bool keyEvent2 = false;
    bool keyEvent100 = false;
    bool flickTrigger = false;
    bool attackLimitTime = false;
    bool shouldFinishMotion = false;
    bool finishIKMotion = false;
    bool itemWalkSwapped = false;
    bool killed = false;
    float pickThreshold = 0.0f; // host randWeightFloat input for pickWeapon
    float damage = 0.0f;        // 0 = no hit this tick
    int damageWeapon = -1;      // weapon coll part, or -1 for a body part
    bool damageBittered = false;
    float bossHealth = 1.0f;    // body HP (source health); <= 0 kills via animEnd
};

struct P2BigTreasureFsmHostOutput {
    P2BigTreasureFsmOutput fsm;
    P2BigTreasureDamageResult damageResult = P2BTDMG_Ignored;
    bool pinchSmoke = false;
    int knockedOff = 0;      // weapons released by this tick's damage
    int liveWeapons = 0;     // remaining attached weapons after the tick
    bool bodyExposed = true; // tam1/tam2 damageable only at zero weapons
};

class P2BigTreasureFsmHost {
public:
    void reset(const P2BigTreasureFsmParms& parms);

    // Advances one 30 Hz tick: applies incoming damage and knock-offs, steps
    // the FSM with the post-damage loadout, then performs requested actions.
    // Safe on an inactive seam (outputs stay default).
    void tick(P2BigTreasureHostSeam& seam, const P2BigTreasureFsmHostInput& in,
              P2BigTreasureFsmHostOutput& out);

    P2BigTreasurePhase phase() const { return mFsm.state(); }
    int chosenWeapon() const { return mChosenWeapon; }
    std::uint64_t knockOffs() const { return mKnockOffs; }
    float bossHealth() const { return mBossHealth; }

private:
    P2BigTreasureFsm mFsm;
    int mChosenWeapon = -1;
    float mBossHealth = 1.0f;
    std::uint64_t mKnockOffs = 0;
};
