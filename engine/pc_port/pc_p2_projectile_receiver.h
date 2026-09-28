#pragma once

#include "pc_p2_cannon_stone.h"
#include "pc_p2_rock_hazard.h"

#include <cstdint>

// Private proxy receiver for lane 20 (parent #169 / #413 / #425).
//
// Host-owned health sink for already-computed projectile strikes. It mirrors
// the source InteractPress / InteractAttack application without dereferencing
// any engine Creature, so the `pc_p2_projectiles` contract that engine target
// health is never mutated stays true. Real engine receiver wiring and shared
// damage semantics (#186 review) remain unimplemented; this only proves the
// strike -> receiver half of the lane.
//
// Damage is never re-derived: callers pass the amount the Stone/Rock contact
// policy already produced. Kind names match the source audit: InteractPress for
// a grounded Navi/Pikmin, InteractAttack (source-fixed 250) for a Teki.

enum class P2ProjectileReceiverStrikeKind { None, InteractPress, InteractAttack };

const char* p2ProjectileReceiverStrikeKindName(P2ProjectileReceiverStrikeKind kind);

// One applied-strike report. known=false means no receiver is registered for
// targetToken (a no-op). applied=false means the receiver was already dead or
// the strike carried no positive damage. appliedDamage is clamped to the
// remaining health. died=true is set only on the single strike that reaches
// zero, so a host can emit its death marker exactly once.
struct P2ProjectileReceiverHit {
    bool known = false;
    bool applied = false;
    bool died = false;
    P2ProjectileReceiverStrikeKind kind = P2ProjectileReceiverStrikeKind::None;
    float damage = 0.0f;
    float appliedDamage = 0.0f;
    float health = 0.0f;
    std::uint64_t targetToken = 0;
    std::uint64_t attributedToken = 0;
};

class P2ProjectileReceiver {
public:
    P2ProjectileReceiver() = default;
    P2ProjectileReceiver(std::uint64_t token, float maxHealth);

    std::uint64_t token() const { return mToken; }
    float maxHealth() const { return mMaxHealth; }
    float health() const { return mHealth; }
    bool alive() const { return mAlive; }

    // Removes `damage`, clamping at zero, and returns the amount removed. A dead
    // receiver or a non-positive amount removes nothing.
    float applyDamage(float damage);

private:
    std::uint64_t mToken = 0;
    float mMaxHealth = 0.0f;
    float mHealth = 0.0f;
    bool mAlive = false;
};

// Fixed-capacity registry keyed by target token. The host populates it from
// `receiver <token> <maxHealth>` config rows.
class P2ProjectileReceiverRegistry {
public:
    static constexpr int kMaxReceivers = 16;

    void reset();
    bool add(std::uint64_t token, float maxHealth);
    // Registers a single wildcard sink for tokens with no exact receiver. It is
    // required for a real runtime demo because engine creature tokens are runtime
    // pointers an arena config cannot name in advance.
    bool addAny(float maxHealth);
    P2ProjectileReceiver* find(std::uint64_t token);
    const P2ProjectileReceiver* find(std::uint64_t token) const;
    int count() const { return mCount; }
    int aliveCount() const;

    // Core entry point. Looks up targetToken and applies `damage`; kind and
    // attributedToken are carried into the report for the host's markers. An
    // unknown token or kind None is a no-op.
    P2ProjectileReceiverHit applyStrike(P2ProjectileReceiverStrikeKind kind, float damage,
                                        std::uint64_t targetToken,
                                        std::uint64_t attributedToken);

    // Contract overloads. A contact with no strike emits nothing, so a
    // non-strike contact can never apply damage to the proxy.
    P2ProjectileReceiverHit applyStrike(const P2CannonStoneContactResult& result);
    P2ProjectileReceiverHit applyStrike(const P2RockHazardContactResult& result);

private:
    P2ProjectileReceiver mReceivers[kMaxReceivers];
    int mCount = 0;
    P2ProjectileReceiver mAny;
    bool mHasAny = false;
};
