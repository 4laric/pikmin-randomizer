#pragma once

#include <cstdint>

// Isolated BombSarai (Careening Dirigibug, EnemyID 58) bomb-rock projectile
// lifecycle policy. It deliberately has no actor, map, damage, sound, effect
// or creature dependency; a future host integration owns those concerns and
// supplies the world trace, target enumeration and carrier liveness checks.
// Source reference: projectPiki/pikmin2 revision
// 632af93787b9c95b63f0c13be32b161375ce3a96 (US GPVE01 rev 0):
//   src/plugProjectNishimuraU/BombSarai.cpp / BombSaraiState.cpp,
//   src/plugProjectMorimuraU/bomb.cpp / bombState.cpp,
//   include/Game/Entities/BombSarai.h / Bomb.h.
// See docs/PIKMIN2_BOMBSARAI_PROJECTILE_CONTRACT.md for the contract.

struct P2BombSaraiVec3 {
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
};

// Throw kinds mirror the three source throwBomb call sites:
// Release lob (BombSaraiState.cpp:528-531), Fall skyward throw (:592-595)
// and the unconditional zero-velocity drop in Obj::onKill (BombSarai.cpp:57-61).
enum class P2BombSaraiThrowKind { Release, Fall, Death };

// Lifecycle phases, mapped to source Bomb FSM states:
//   Captured  = captured at the kamu_jnt1 joint, constrained + invulnerable
//               (bomb.cpp:23-44); the host moves it with the joint.
//   InFlight  = BOMB_Wait, motion stopped, escaped capture (bombState.cpp:37-58).
//   ArmedLoop = BOMB_Wait, hit-loop playing after floor contact
//               (isAnimStart via mHasEscapedCapture && mFloorTriangle,
//               bomb.cpp:468-476); fuse health drains (bombState.cpp:60-69).
//   Burning   = BOMB_Bomb; health keeps draining, then a fixed 10-tick
//               detonation delay (bombState.cpp:97-117).
//   Despawned = killed without detonation (200-tick escaped-capture timeout,
//               bombState.cpp:53-58) or already detonated.
enum class P2BombSaraiBombPhase { Inactive, Captured, InFlight, ArmedLoop, Burning, Despawned };

struct P2BombSaraiTraceResult {
    P2BombSaraiVec3 position;
    P2BombSaraiVec3 velocity;
    bool floor = false;
    bool wall = false;
    float groundY = 0.0f;
    bool hasGroundY = false;
};

// One detonation record. The host routes it to receivers; the policy never
// enumerates or touches creatures. Friendly-fire policy from
// bombState.cpp:159-190: every Teki in the volume takes tekiDamage via
// InteractBomb (no faction check, including a grounded carrier); Navi/Pikmin
// take naviPikiDamage with the recorded knockback weights. Attribution:
// source attributes Navi/Pikmin damage to mCarrier when non-null
// (bombState.cpp:167-189). The source pointer can go stale after a throw;
// this policy carries a host-issued token instead and resolves liveness at
// blast time through P2BombSaraiCarrierFn. carrierValid=false means the host
// could not confirm a live carrier: receivers must attribute to the bomb
// itself, matching the source mCarrier==nullptr fallback (:170-172).
struct P2BombSaraiBlastEvent {
    P2BombSaraiVec3 center;
    float radius = 0.0f;        // general mAttackRadius
    float halfHeight = 0.0f;    // fp02 blast range height +-, default 50
    float tekiDamage = 0.0f;    // fp01 damage to enemies, default 250
    float naviPikiDamage = 0.0f; // general mAttackDamage
    float knockbackNavi = 100.0f;  // bombState.cpp:178-186
    float knockbackPiki = 200.0f;
    std::uint64_t carrierToken = 0;
    bool hasCarrier = false;
    bool carrierValid = false;
};

// Host-supplied parameters. Numeric defaults that are not fixed by the source
// are explicit host/converter inputs; the policy never invents them.
struct P2BombSaraiBombConfig {
    float gravityPerTick = 0.0f; // per-source-tick downward velocity decrement
                                 // (host creature-simulation adapter value)
    float fuseHealth = 0.0f;     // bomb general mHealth; drains 1.0 per source
                                 // second from arming onward (must be > 0)
    int armLoopTicks = 0;        // hit-loop animation length in source ticks
                                 // (converter/bck input, must be > 0)
    float bombRadius = 0.0f;     // trace sphere radius (host collision input)
    float blastRadius = 0.0f;    // general mAttackRadius
    float blastHalfHeight = 50.0f;  // fp02 default (Bomb.h:139)
    float tekiDamage = 250.0f;      // fp01 default (Bomb.h:138)
    float naviPikiDamage = 0.0f;    // general mAttackDamage
    int ip02TriggerLimit = 50;          // bomb-on-bomb induction trigger
                                        // limit (bomb.cpp:348-368, 426-440),
                                        // Bomb.h:142 header default; retail
                                        // 15 comes from the host/config.
                                        // Counts down from ip02 on each
                                        // induce() call; at 0 the bomb
                                        // detonates immediately.
                                        // 0 disables induction.
};

// Called once per 30 Hz source update while a bomb is in flight. Return true
// only after filling position and velocity, mirroring the source trace-mutated
// velocity contract. On floor/wall contact it must also set finite
// groundY/hasGroundY. Return false only when no trace was performed.
typedef bool (*P2BombSaraiTraceFn)(void* context, const P2BombSaraiVec3& position,
                                   const P2BombSaraiVec3& velocity, float delta,
                                   float radius, P2BombSaraiTraceResult& result);

// Resolves a carrier token to liveness at blast time. The host owns the
// token mapping; the policy never dereferences carrier objects.
typedef bool (*P2BombSaraiCarrierFn)(void* context, std::uint64_t carrierToken);

class P2BombSaraiBomb {
public:
    static constexpr float kSourceDelta = 1.0f / 30.0f;
    static constexpr int kEscapeTimeoutTicks = 200; // bombState.cpp:53-58
    static constexpr int kDetonateDelayTicks = 10;  // bombState.cpp:114-117

    void reset(const P2BombSaraiBombConfig& config);

    // Captures a fresh bomb for a carrier (supplyBomb, BombSarai.cpp:263-279).
    bool capture(std::uint64_t carrierToken, const P2BombSaraiVec3& jointPosition);

    // Ends capture and applies the source throw velocity for the kind
    // (throwBomb, BombSarai.cpp:285-294). No-op unless Captured, matching the
    // source null-mHeldBomb no-op. faceDir is the carrier facing in radians.
    bool throwBomb(P2BombSaraiThrowKind kind, float faceDir);

    // One 30 Hz source update. delta must equal kSourceDelta. When the bomb
    // detonates, exactly one blast event is recorded in lastBlast().
    bool update(float delta, P2BombSaraiTraceFn trace, void* traceContext,
                P2BombSaraiCarrierFn carrier, void* carrierContext);

    // Bomb-on-bomb induction (ip02 trigger-limit countdown, bomb.cpp:348-368,
    // 426-440). The host invokes this on every armed/burning bomb inside a
    // detonating bomb's blast volume. Each call decrements the counter by 1;
    // when it reaches 0 the bomb detonates immediately (skipping its own edge
    // fuse), recording one blast event and transitioning to Despawned. A
    // counter already at 0 never re-detonates. No-op (returns false) unless
    // the phase is ArmedLoop or Burning; a counter configured to 0 disables
    // induction entirely. Returns true only when this bomb detonated.
    bool induce(P2BombSaraiCarrierFn carrier, void* carrierContext);

    int inductionCounter() const { return mInductionCounter; }

    P2BombSaraiBombPhase phase() const { return mPhase; }
    const P2BombSaraiVec3& position() const { return mPosition; }
    const P2BombSaraiVec3& velocity() const { return mVelocity; }
    std::uint64_t carrierToken() const { return mCarrierToken; }
    bool hasBlast() const { return mHasBlast; }
    const P2BombSaraiBlastEvent& lastBlast() const { return mBlast; }
    void clearBlast() { mHasBlast = false; mBlast = P2BombSaraiBlastEvent{}; }

    // Source throw velocities, exposed for fixtures:
    // Release (50*sin(face), 100, 50*cos(face)); Fall (100*sin, 300, 100*cos);
    // Death (0, 0, 0).
    static P2BombSaraiVec3 throwVelocity(P2BombSaraiThrowKind kind, float faceDir);

private:
    void detonate(P2BombSaraiCarrierFn carrier, void* carrierContext);

    P2BombSaraiBombConfig mConfig;
    P2BombSaraiBombPhase mPhase = P2BombSaraiBombPhase::Inactive;
    P2BombSaraiVec3 mPosition;
    P2BombSaraiVec3 mVelocity;
    std::uint64_t mCarrierToken = 0;
    int mEscapeTicks = 0;
    int mArmTicksRemaining = 0;
    float mFuseHealthRemaining = 0.0f;
    int mDetonateDelayTicks = 0;
    int mInductionCounter = 0;
    bool mHasBlast = false;
    P2BombSaraiBlastEvent mBlast;
};

// Fixed-capacity supply pool. Capacity models the BombSarai roster
// preallocation (mChildNum = 2, enemyInfo.cpp:46); the host configures the
// real shared Bomb manager limit. One active bomb per carrier token mirrors
// the source !mHeldBomb guard (BombSarai.cpp:265). Exhaustion returns
// nullptr with no partial state, matching the source's silent tolerance of a
// failed manager/birth (:266-278).
class P2BombSaraiBombPool {
public:
    explicit P2BombSaraiBombPool(int capacity) : mCapacity(capacity > 0 ? capacity : 0) {}

    // Returns a captured bomb, or nullptr on pool exhaustion, a duplicate
    // live carrier token, or invalid input. No state changes on failure.
    P2BombSaraiBomb* supply(std::uint64_t carrierToken, const P2BombSaraiVec3& jointPosition,
                            const P2BombSaraiBombConfig& config);

    int capacity() const { return mCapacity; }
    int activeCount() const;

private:
    static constexpr int kMaxBombs = 16;
    int mCapacity;
    P2BombSaraiBomb mBombs[kMaxBombs];
    bool mUsed[kMaxBombs] = {};
};
