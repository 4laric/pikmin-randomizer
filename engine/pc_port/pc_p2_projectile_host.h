#pragma once

#include "pc_p2_cannon_stone.h"

#include <cstdint>

// Isolated host adapter for the pure Cannon Stone projectile policy
// (pc_p2_cannon_stone.h). It is the #169/#198 "pure policy vs host adapter"
// bridge: the policy owns the source state machine / steering / contact
// classification, and this adapter owns the three host services the policy
// deliberately never touches:
//
//   * Homing target selection. The host supplies the active Navi (optional)
//     and a snapshot of nearby Pikmin/Navi candidates with position + alive
//     flag; the adapter applies the source selection (active Navi first, else
//     nearest live Pikmin/Navi) and returns the policy's P2CannonStoneTarget.
//     The policy only steers (Rock.cpp:370-398).
//   * Terrain movement. The host binds a sphere-trace provider; the adapter
//     validates it and exposes a P2CannonStoneTraceFn so the policy can be
//     stepped with real terrain and wall contact (wallCallback).
//   * Strike attribution liveness. The host binds a token-liveness provider;
//     the adapter annotates P2CannonStone::contact results so a stale target
//     token is reported unreachable instead of routed, mirroring the
//     BombSarai carrier-token safety pattern (pc_p2_bombsarai_bomb.h:49-59).
//
// This file has no engine, creature, map, sound or effect dependency and adds
// no shared hooks. A future native integration owns the real MapMgr/creature
// primitives behind these callbacks. See
// docs/PIKMIN2_PROJECTILE_HOST_ADAPTER.md for the contract.
//
// Coordinate conventions (identical to pc_p2_cannon_stone):
//   * x/z are horizontal, y is up.
//   * Horizontal facing/angle is roundAng(atan2(dx, dz)) (trig.h:91-94),
//     matching Creature::getAngDist (Creature.h:386-395).
//
// Trace-space convention (explicitly NOT the Groink/P1 convention): this
// adapter's host trace provider receives and returns the projectile sphere
// CENTER. The pure Stone policy stores its position as the sphere center and
// passes collisionRadius alongside it (pc_p2_cannon_stone.h:81-89), so keeping
// the provider in center space is the direct mapping. The Groink/P1
// MapMgr::traceMove path takes a sphere BASE (center.y - radius) and returns
// base space because P1 offsets internally; that conversion is NOT applied
// here. A host binding a P1 base-space primitive must do its own center-to-base
// conversion before calling it and convert back afterward.

// Host sphere-trace output, in sphere-CENTER space. `position`/`velocity` are
// the trace-mutated center and velocity. `floor`/`wall` classify contact; on
// either contact the host must also supply a finite groundY (hasGroundY).
// P2CannonStoneTraceResult only carries `wall` (the pure policy has no floor
// field), so the adapter forwards `wall` and validates the contact/groundY
// contract without inventing a floor branch.
struct P2ProjectileHostTrace {
    P2CannonStoneVec3 position;
    P2CannonStoneVec3 velocity;
    bool floor = false;
    bool wall = false;
    float groundY = 0.0f;
    bool hasGroundY = false;
};

// Host static-map sphere trace in center space. `center` is the projectile
// sphere center and `velocity` is the policy's target velocity. Return false
// when no trace was performed.
typedef bool (*P2ProjectileHostTraceFn)(void* context, const P2CannonStoneVec3& center,
                                        const P2CannonStoneVec3& velocity, float delta,
                                        float radius, P2ProjectileHostTrace& result);

// Resolves a host-issued token (candidate / strike target / attribution source)
// to liveness. The host owns the mapping; the adapter never dereferences a
// creature. An unbound provider or token 0 is unconfirmed (false), matching the
// BombSarai no-callback fallback.
typedef bool (*P2ProjectileHostTokenLiveFn)(void* context, std::uint64_t token);

// One nearby homing candidate. `alive` mirrors Creature::isAlive(); dead
// candidates are skipped. `token` identifies the creature for strike
// attribution.
struct P2ProjectileHostCandidate {
    P2CannonStoneVec3 position;
    std::uint64_t token = 0;
    bool alive = false;
};

// Host snapshot for one homing selection. The active Navi is supplied
// separately because the source uses it unconditionally
// (naviMgr->getActiveNavi(), Rock.cpp:372-374); the candidate list covers the
// rest of the Pikmin/Navi population. A non-finite active-Navi position is
// ignored and selection falls through to the candidate list.
struct P2ProjectileHostCandidateSnapshot {
    bool hasActiveNavi = false;
    P2CannonStoneVec3 activeNaviPosition;
    std::uint64_t activeNaviToken = 0;
    const P2ProjectileHostCandidate* candidates = nullptr;
    int candidateCount = 0;
};

// Annotated result of P2CannonStone::contact. `contact` is the pure policy
// result unchanged. `targetLive`/`attributedLive` are the host liveness
// answers for the strike's target token and attribution token. `unreachable`
// is true when a strike was emitted but the target token is stale: the host
// must not route that damage to a dead/reused creature. `attributionToken` is
// the resolved routing attribution: the strike's own attributed token when it
// is live, otherwise the Stone's self token, mirroring the BombSarai
// stale-carrier fallback to bomb-self attribution.
struct P2ProjectileHostStrikeResult {
    P2CannonStoneContactResult contact;
    bool targetLive = false;
    bool attributedLive = false;
    bool unreachable = false;
    std::uint64_t attributionToken = 0;
};

class P2ProjectileHostAdapter {
public:
    // Bind the host primitives before use. Passing nullptr trace/token
    // callbacks leaves the corresponding service unavailable: trace fails and
    // tokens are unconfirmed.
    void reset(P2ProjectileHostTraceFn traceFn, void* traceContext,
               P2ProjectileHostTokenLiveFn tokenLiveFn, void* tokenLiveContext);

    // Source-faithful homing selection (Rock.cpp:370-386). Returns the active
    // Navi when present, else the nearest live candidate within sightRadius by
    // 2D x/z squared distance, else a no-target result. The source call site
    // passes a 180-degree searchAngle (unrestricted), so there is no facing or
    // y filter here. sightRadius < 0 means unlimited range, matching
    // EnemyFunc::getNearestPikminOrNavi (searchRadius < 0 -> FLT_MAX).
    // Non-finite origin/sightRadius/candidate data is ignored.
    static P2CannonStoneTarget selectTarget(const P2CannonStoneVec3& origin,
                                            const P2ProjectileHostCandidateSnapshot& snapshot,
                                            float sightRadius);

    // P2CannonStoneTraceFn bridge (pass to P2CannonStone::update). Converts and
    // validates the host center-space trace: delta must be the source delta,
    // radius must be positive, positions/velocities must be finite and
    // bounded, and a floor/wall contact must carry a finite groundY. Returns
    // false on any violation so the policy falls back to direct integration.
    static bool trace(void* context, const P2CannonStoneVec3& center,
                      const P2CannonStoneVec3& velocity, float delta, float radius,
                      P2CannonStoneTraceResult& result);

    // Calls P2CannonStone::contact and annotates the result with host token
    // liveness. A stale target token marks the strike unreachable; a stale
    // attribution token resolves attributionToken to the Stone's self token.
    P2ProjectileHostStrikeResult contact(P2CannonStone& stone, P2CannonStoneContactKind kind,
                                         bool targetOnFloor, bool targetIsRock,
                                         std::uint64_t targetToken) const;

    // Single-token liveness query; token 0 is always unconfirmed.
    bool tokenLive(std::uint64_t token) const;

    P2ProjectileHostTraceFn mTrace = nullptr;
    void* mTraceContext = nullptr;
    P2ProjectileHostTokenLiveFn mTokenLive = nullptr;
    void* mTokenLiveContext = nullptr;

private:
    static P2ProjectileHostAdapter& from(void* context)
    {
        return *static_cast<P2ProjectileHostAdapter*>(context);
    }
};
