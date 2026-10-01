#pragma once

#include "pc_p2_bigtreasure_attacks.h"
#include "Creature.h"
#include <cstdint>

class MapMgr;

// Lane-owned host binding of the BigTreasure terrain/trace adapter interface
// (pc_p2_bigtreasure_attacks.h) to the P1 static map, issue #246. Mirrors the
// #169 Groink runtime-fixture pattern (pc_p2_groink_map_trace.h/.cpp):
//
// - A dedicated Creature collision proxy records contacts. The owner boss's
//   collision fields must never be reused for attack-node traces.
// - P1 MapMgr::traceMove accepts a sphere BASE: it adds the radius before
//   collision and subtracts it afterward. The P2 policies store sphere
//   centers (the elec policy pre-raises its node by +20, source convention).
//   The adapter therefore traces with center.y - radius and returns
//   position.y + radius.
// - Floor contact = ground triangle present after the trace; wall contact =
//   wallCallback fired. On either contact the adapter samples
//   getMinY(x, z, false); a contact without a finite terrain sample fails
//   the whole trace (the adapter never invents ground).
// - P1 contact classification and restitution are host approximations, not
//   Pikmin 2 collision parity: MoveTrace carries no bounce coefficient, so
//   the source bounceFactor is validated but P1's trace-mutated velocity is
//   what the elec policy consumes (floor friction stays policy-side).

// Standalone collision recorder; never registered with an actor manager.
class P2BigTreasureTraceProxy : public Creature {
public:
    P2BigTreasureTraceProxy() : Creature(nullptr) { clear(); }
    void clear();
    void refresh(Graphics&) override { }
    void wallCallback(immut Plane&, DynCollObject*) override { wall = true; }
    bool wall = false;

protected:
    void doKill() override { }
};

class P2BigTreasureMapTrace {
public:
    void reset(MapMgr* map);

    // P2BigTreasureTraceFn implementation. `position` is the sphere center as
    // supplied by the policy (already joint-raised for elec). Only the
    // source 30 Hz delta and the elec trace radius (20) are accepted; the
    // bounce factor must be finite and in (0, 1]. Returns false when no
    // trace was performed.
    static bool trace(void* context, const P2BigTreasureVec3& position,
                      const P2BigTreasureVec3& velocity, float delta, float radius,
                      float bounceFactor, P2BigTreasureTraceResult& result);

    // P2BigTreasureGroundFn implementation (getMinY equivalent for water
    // bubble impact). Returns false when no map is loaded or the sample is
    // non-finite.
    static bool ground(void* context, float x, float z, float* outY);

    std::uint64_t calls() const { return mCalls; }
    std::uint64_t floors() const { return mFloors; }
    std::uint64_t walls() const { return mWalls; }

private:
    MapMgr* mMap = nullptr;
    P2BigTreasureTraceProxy mProxy;
    std::uint64_t mCalls = 0, mFloors = 0, mWalls = 0;
};
