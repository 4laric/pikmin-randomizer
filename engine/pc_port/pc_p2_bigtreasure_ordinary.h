#pragma once

#include "pc_p2_bigtreasure_fsmhost.h"

// Lane-owned ordinary-update drive for the BigTreasure (Titan Dweevil, enemy
// ID 73) FSM host, issue #246. The integrated host seam already runs from
// pc_p2_hardlanes_update, but it drives the injected attack shortcut
// (p2_bigtreasure_host_tick_entry: pacer -> pick -> start) directly and never
// steps the 12-state policy. This module closes that gap:
//
//  - it owns one P2BigTreasureFsmHost and a bounded natural-hit queue,
//  - it derives the source isAttackLimitTime() input from the lane's attack
//    pacer (4 + 2 * liveWeapons seconds, 3x accrual while an unstuck outsider
//    is nearby), and
//  - it steps the policy once per 30 Hz source tick from the ordinary update.
//
// Damage enters through postHit(). That is the single ingress a natural Pikmin
// attack volume (lane 10 receiver) or a collision proxy calls; it is
// deliberately not a second receiver framework and it holds at most one
// damage callback per source tick, matching the injected fixture.
//
// Engine-free by construction: every animation/target/kill input is a host
// fact the caller derives from live engine state (and, once the motion assets
// are staged, the BigTreasure visual bank's key events). The animation
// keyframe source and the real attack-volume receiver are the named remaining
// providers; see docs/PIKMIN2_BIGTREASURE_ORDINARY.md.

// One natural hit delivered to a weapon coll part, or to the body when the
// boss has no weapons left (`weapon == -1`). Mirrors the ownership
// damageCallBack inputs.
struct P2BigTreasureOrdinaryHit {
    int weapon = -1;      // P2BigTreasureWeapon coll part, or -1 for the body
    float damage = 0.0f;  // Pikmin-source damage magnitude
    bool bittered = false;
};

// Per-tick host facts. All are supplied by the caller, so fixtures stay
// deterministic and the policy owns no engine state.
struct P2BigTreasureOrdinaryFacts {
    float delta = 1.0f / 30.0f;
    bool targetInBox = false;           // live Navi/Pikmin in the 225-unit XZ box
    bool hasTarget = false;             // target within the private sensing radius
    bool unstuckOutsiderNearby = false; // 3x pacer accrual
    bool bootDemoPlayed = false;
    bool animEnd = false;
    bool keyEvent2 = false;
    bool keyEvent100 = false;
    bool flickTrigger = false;
    bool shouldFinishMotion = false;
    bool finishIKMotion = false;
    bool itemWalkSwapped = false;
    bool killed = false;
    float pickThreshold = 0.0f; // host randWeightFloat input for pickWeapon
    float bossHealth = 1.0f;    // body HP; <= 0 kills via the animEnd path
};

class P2BigTreasureOrdinary {
public:
    static constexpr int kHitQueueCapacity = 16;

    void reset(const P2BigTreasureFsmParms& parms);

    // Queues one natural hit for the next source tick. Returns false when the
    // queue is full (the hit is dropped, never silently merged) or the hit is
    // invalid (non-finite/non-positive damage or an out-of-range weapon).
    bool postHit(const P2BigTreasureOrdinaryHit& hit);

    int pendingHits() const { return mCount; }

    // Advances one 30 Hz tick: derives attackLimitTime from the seam pacer,
    // applies at most one queued natural hit, then steps the FSM policy.
    // Safe on an inactive seam (outputs stay default).
    void tick(P2BigTreasureHostSeam& seam, const P2BigTreasureOrdinaryFacts& facts,
              P2BigTreasureFsmHostOutput& out);

    P2BigTreasurePhase phase() const { return mHost.phase(); }
    int chosenWeapon() const { return mHost.chosenWeapon(); }
    std::uint64_t knockOffs() const { return mHost.knockOffs(); }
    float bossHealth() const { return mHost.bossHealth(); }

private:
    bool pop(P2BigTreasureOrdinaryHit& out);

    P2BigTreasureFsmHost mHost;
    P2BigTreasureOrdinaryHit mHits[kHitQueueCapacity];
    int mHead = 0;
    int mCount = 0;
};
