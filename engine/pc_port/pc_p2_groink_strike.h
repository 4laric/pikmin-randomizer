#pragma once

#include "pc_p2_groink_hit.h"
#include "pc_p2_projectile_receiver.h"

#include <cstddef>
#include <cstdint>

// Private Groink shell-strike -> health bridge (#205 receiver half). It is the
// only new host seam between the engine-free shell classifier and the lane-20
// proxy receiver: classify the supplied sweep, then map a Bomb command onto a
// proxy InteractAttack. Damage is never re-derived here; it is exactly the
// classifier command's value.
//
// Receiver dependency: lane 20's `pc_p2_projectile_receiver.{h,cpp}` (plus the
// `pc_p2_cannon_stone.h` / `pc_p2_rock_hazard.h` type headers) is integrated in
// the approved native baseline `f14c6851` and used directly. The earlier strike
// handoff vendored lane `opencode/p2-projectiles-integration` @ `be8037af`
// byte-identically; the approved tree is identical, so no copy is carried here.
//
// The receiver owns no impulse field, so the classifier's knockback vector is
// carried through the result unchanged for the host to apply separately.

struct P2GroinkStrikeInput {
    P2GroinkHitInput hit;
    std::uint64_t targetToken = 0;
    std::uint64_t attributedToken = 0;
};

struct P2GroinkStrikeResult {
    bool valid = false;
    bool insideSweep = false;
    P2GroinkHitKind kind = P2GroinkHitKind::None;
    float damage = 0.0f;
    P2GroinkVec3 impulse;
    bool applied = false;
    bool died = false;
    float health = 0.0f;
};

// Bomb -> InteractAttack with the classifier's damage applied to targetToken;
// Wind -> no receiver health change, impulse carried through; None/invalid ->
// no-op. `applied` and `died` come from the receiver's single-strike report.
P2GroinkStrikeResult p2_groink_apply_strike(P2ProjectileReceiverRegistry& registry,
                                            const P2GroinkStrikeInput& input,
                                            const P2GroinkHitCandidate& candidate);

// Host-side dedup for hosts that process one shell across many moving steps.
// It records (shellSlot, targetToken) so one shell damages a given candidate at
// most once per flight, while a different shell can still hit the same
// candidate. p2_groink_apply_strike stays pure; this tracker is the only state.
//
// Hosts consult it only after the classifier reports a non-None kind, then call
// p2_groink_apply_strike when the decision is `Apply`. `clearSlot` forgets one
// shell once its pool slot recycles so a reused slot starts a fresh flight.
//
// Supported bound: `kMaxTracked` distinct (slot, token) pairs may be in flight
// at once. The host owns this bound by recycling shell slots; live pairs are
// typically (in-flight shells) x (candidates each shell has struck). When the
// table is full a genuinely new pair cannot be recorded, so the tracker rejects
// it (`RejectedAtCapacity`) instead of reporting a hit it cannot dedup. That
// preserves the documented once-per-shell/target damage guarantee at the cost of
// dropping the untracked strike; the host can log the rejection and defer/retry
// after a `clearSlot`. Silently re-reporting an unstored pair would apply damage
// on every moving step and is exactly the bug this bound must prevent.
enum class P2GroinkStrikeDecision {
    Apply,                // newly recorded; the host may apply the strike
    AlreadyHit,           // this (slot, token) pair was already recorded
    RejectedAtCapacity,   // table full and the pair is untracked; do not apply
};

class P2GroinkStrikeTracker {
public:
    static constexpr std::size_t kMaxTracked = 64;

    // Explicit tri-state decision. Callers that only need the apply/don't-apply
    // answer may use `firstHit`.
    P2GroinkStrikeDecision decide(std::size_t shellSlot, std::uint64_t targetToken);
    // Convenience: true only for `Apply` (newly recorded). `AlreadyHit` and
    // `RejectedAtCapacity` both return false, so an untrackable pair is never
    // applied twice.
    bool firstHit(std::size_t shellSlot, std::uint64_t targetToken);
    // Forgets every pair for one shell slot. Call when that shell recycles.
    void clearSlot(std::size_t shellSlot);
    void reset();

    std::size_t tracked() const { return mCount; }
    bool full() const { return mCount >= kMaxTracked; }

private:
    struct Entry {
        std::size_t slot = 0;
        std::uint64_t token = 0;
    };
    Entry mEntries[kMaxTracked];
    std::size_t mCount = 0;
};

// Convenience wrapper for hosts that prefer a free function over the method.
// Returns true only for `P2GroinkStrikeDecision::Apply`.
bool p2_groink_strike_first_hit(P2GroinkStrikeTracker& tracker,
                                std::size_t shellSlot,
                                std::uint64_t targetToken);
