#pragma once

#include "pc_p2_bombsarai_bomb.h"

// Lane-owned host terrain adapter contract for the BombSarai (Careening
// Dirigibug) lane, mirroring the #169 Groink adapter pattern
// (pc_p2_groink_map_trace.h/.cpp, docs/PIKMIN2_GROINK_PROTOTYPE.md).
//
// The Groink adapter binds directly to P1 MapMgr/Creature. This module keeps
// the same contract but stays engine-free: the host supplies the two P1
// primitives as callbacks, and the adapter owns the conversion, contact
// classification, groundY correction and validation rules around them:
//
//   * P1 MapMgr::traceMove accepts a sphere BASE (it adds the radius before
//     collision and subtracts it afterward); the bomb policy stores its
//     CENTER. Construct the raw trace with center.y - radius and return
//     position.y + radius. Passing the center directly shifts the collision
//     sphere upward by the radius (Groink prototype doc).
//   * Floor contact means the trace proxy's ground triangle is set; wall
//     contact means its wall callback fired. The owner's collision fields
//     must never be reused for projectile traces.
//   * On floor OR wall contact the host must sample getMinY(x, z, false) and
//     provide a finite groundY; a missing sample fails the trace instead of
//     inventing terrain.
//
// P1 contact classification and bounce behavior remain host approximations,
// not Pikmin 2 collision parity.

// Raw host trace output, in sphere-BASE space exactly as P1 traceMove
// returns it (the adapter converts to center space).
struct P2BombSaraiRawTrace {
    P2BombSaraiVec3 position; // trace-mutated sphere base
    P2BombSaraiVec3 velocity; // trace-mutated velocity
    bool groundTriangle = false;
    bool wall = false;
};

// Host P1 static-map sphere trace (MapMgr::traceMove equivalent). delta is
// the source delta. Return false when no trace was performed.
typedef bool (*P2BombSaraiTraceMoveFn)(void* context, const P2BombSaraiVec3& sphereBase,
                                       const P2BombSaraiVec3& velocity, float radius,
                                       float delta, P2BombSaraiRawTrace& result);

// Host terrain height sample (MapMgr::getMinY(x, z, false) equivalent).
// Must return a finite height for valid terrain.
typedef float (*P2BombSaraiGetMinYFn)(void* context, float x, float z);

class P2BombSaraiTerrainAdapter {
public:
    // Full bomb-policy trace (P2BombSaraiTraceFn signature): converts the
    // center-space request to a base-space raw trace, classifies contacts,
    // samples groundY on contact, applies the landing correction and
    // validates all values. Out-of-range/non-finite input or a wrong delta
    // fails the trace so the policy falls back to straight integration only
    // when no trace was performed.
    static bool trace(void* context, const P2BombSaraiVec3& center,
                      const P2BombSaraiVec3& velocity, float delta, float radius,
                      P2BombSaraiTraceResult& result);

    // Terrain height for hover control and shadow/flight logic. Returns
    // false on non-finite samples.
    static bool getMinY(void* context, float x, float z, float& outY);

    // Bind the host primitives before tracing.
    void reset(P2BombSaraiTraceMoveFn traceMove, void* traceMoveContext,
               P2BombSaraiGetMinYFn getMinYFn, void* getMinYContext);

    P2BombSaraiTraceMoveFn mTraceMove = nullptr;
    void* mTraceMoveContext = nullptr;
    P2BombSaraiGetMinYFn mGetMinY = nullptr;
    void* mGetMinYContext = nullptr;

private:
    static P2BombSaraiTerrainAdapter& from(void* context)
    {
        return *static_cast<P2BombSaraiTerrainAdapter*>(context);
    }
};
