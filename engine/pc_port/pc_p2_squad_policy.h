#pragma once
#include "pc_p2_captain_policy.h"

#include <cstddef>
#include <cstdint>

// Lane 12 per-captain squad split + inactive-captain follow + dismiss/whistle
// priority policy (#130), engine-free.
//
// pc_p2_captain_policy.h owns captain identity, health/knockout, captor
// ownership and capture/release. This header owns the derived squad decisions a
// second captain needs and that can be decided without the engine, so the
// standalone policy test can exercise them under g++ and pc_p2_captain.cpp only
// has to marshal positions:
//
//   * P2SquadFollowPolicy mirrors NaviFollowState::exec for the *inactive*
//     captain (source: native/pikmin2-research
//     src/plugProjectKandoU/naviState.cpp:1361-1552). The inactive captain
//     walks toward the controlled captain, halts inside 30 units
//     (naviState.cpp:1531-1534), averages velocities inside 60
//     (naviState.cpp:1538-1541), idles/goofs after 90 still frames
//     (naviState.cpp:1453-1499) and leaves the party beyond 430
//     (naviState.cpp:1543-1547).
//   * P2WhistleClaim mirrors the mNavi ownership check in the P1 port's
//     Navi::callPikis: a captain whistles free Pikmin and its own Pikmin,
//     never the other captain's (src/plugPikiKando/navi.cpp:1186).
//   * P2DismissPlan mirrors Navi::releasePikis (source navi.cpp:4070-4104):
//     dismissing the controlled captain's squad also dismisses the inactive
//     captain only while that captain is in the follow state.

// ---------------------------------------------------------------------------
// Whistle priority
// ---------------------------------------------------------------------------

// A free (unowned) actor or an actor already owned by the whistler is
// claimable; an actor owned by the other captain is refused.
enum class P2WhistleClaim {
    Refuse, // owned by the other captain
    Claim,  // free, or already owned by the whistler
};

inline P2WhistleClaim p2_whistle_claim(int whistler, int actorOwner)
{
    if (!p2_is_captain(whistler)) return P2WhistleClaim::Refuse;
    if (actorOwner == P2CaptainInvalid) return P2WhistleClaim::Claim; // free
    if (actorOwner == whistler) return P2WhistleClaim::Claim;        // own
    return P2WhistleClaim::Refuse;                                   // other's
}

// ---------------------------------------------------------------------------
// Dismiss priority
// ---------------------------------------------------------------------------

// Dismiss always releases the caller's own plate; the inactive captain is only
// sent walking (InteractKaisan) when it is currently following.
struct P2DismissPlan {
    bool releaseSelf      = true;
    bool releaseInactive  = false;
};

inline P2DismissPlan p2_dismiss_plan(bool inactiveFollowing)
{
    P2DismissPlan plan;
    plan.releaseSelf     = true;
    plan.releaseInactive = inactiveFollowing;
    return plan;
}

// ---------------------------------------------------------------------------
// Inactive-captain follow state
// ---------------------------------------------------------------------------

enum class P2FollowPhase {
    Idle,    // within the stop radius: stand still (source targetDist < 30)
    Follow,  // move toward the controlled captain
    TooFar,  // beyond the leash: leave the party (source targetDist > 430)
};

class P2SquadFollowPolicy {
public:
    // Source thresholds (naviState.cpp:1531-1547).
    static constexpr float kStopDistance  = 30.0f;
    static constexpr float kBlendDistance = 60.0f;
    static constexpr float kLeashDistance = 430.0f;
    static constexpr int kIdleGoofFrames  = 90;

    void reset()
    {
        mPhase      = P2FollowPhase::Idle;
        mIdleFrames = 0;
    }

    P2FollowPhase phase() const { return mPhase; }
    int idleFrames() const { return mIdleFrames; }

    // Advance from the horizontal leader/inactive distance. `leaderMoving` is
    // the source `leaderSpeed > 20.0f` test. Pure apart from the idle counter.
    P2FollowPhase update(float distance, bool leaderMoving)
    {
        if (!(distance >= 0.0f)) distance = 0.0f; // NaN / negative target guard
        if (distance > kLeashDistance) {
            mPhase      = P2FollowPhase::TooFar;
            mIdleFrames = 0;
            return mPhase;
        }
        if (distance <= kStopDistance) {
            mPhase = P2FollowPhase::Idle;
            if (leaderMoving) {
                mIdleFrames = 0;
            } else if (mIdleFrames < kIdleGoofFrames) {
                ++mIdleFrames;
            }
            return mPhase;
        }
        mPhase      = P2FollowPhase::Follow;
        mIdleFrames = 0;
        return mPhase;
    }

    // Source follow speed (naviState.cpp:1523-1541): full move speed, halted
    // inside the stop radius, half-blended with the leader inside the blend
    // band. Returns 0 for a non-positive speed or a distance inside the stop
    // radius.
    static float followSpeed(float distance, float moveSpeed)
    {
        if (!(moveSpeed > 0.0f) || !(distance > kStopDistance)) return 0.0f;
        if (distance < kBlendDistance) return moveSpeed * 0.5f;
        return moveSpeed;
    }

private:
    P2FollowPhase mPhase = P2FollowPhase::Idle;
    int mIdleFrames      = 0;
};
