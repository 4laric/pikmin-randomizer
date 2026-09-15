#pragma once

// Shared lane-20 falling-Rock host binding + Egg scripted RNG + Wait detection
// (#411/#410, parent #169). Extracted from the lane-20 projectile host seam
// (pc_p2_projectiles.cpp anonymous namespace) so cross-lane consumers — the
// lane-25 DangoMushi rain host (pc_p2_dangomushi.cpp) — reuse the primitive
// instead of forking RockMapBinding / rockDetection / ScriptRng.
//
// No behaviour change for lane 20: the static-map trace, the scripted RNG and
// the Wait-detection approximation below are the exact definitions the lane-20
// seam already used, just relocated under a named namespace. See
// pc_p2_projectiles.cpp / pc_p2_rock_hazard.h for the terrain center/base
// convention and the policy contracts.
#include "pc_p2_rock_hazard.h"
#include "Creature.h"

class MapMgr;
class Graphics;
class Plane;
class DynCollObject;

namespace p2rockhost {

// P1 static-map trace proxy. Never registered with an actor manager; its
// collision fields are used only for the static-map probe (the same pattern as
// the P2 strike probes). The `wall`/ground flags are read back by the binding.
class TraceProxy : public Creature {
public:
    TraceProxy() : Creature(nullptr) { clear(); }
    void clear();
    void refresh(Graphics&) override;
    void wallCallback(immut Plane&, DynCollObject*) override;
    bool wall = false;

protected:
    void doKill() override;
};

// Binds the falling-Rock trace primitive to the P1 static map. The Rock policy
// stores its position as the sphere center, so `base = center - (0, radius, 0)`
// is sent to traceMove and `(0, radius, 0)` is added back. `colliding` is
// host-owned (P1 has no EB_Colliding); floor contact is reported through
// mGroundTriangle.
class RockMapBinding {
public:
    void reset(MapMgr* map) { mMap = map; mProxy.clear(); mCalls = mFloors = 0; }

    static bool trace(void* context, const P2RockHazardVec3& center,
                      const P2RockHazardVec3& velocity, float delta, float radius,
                      P2RockHazardTraceResult& result);

    std::uint64_t calls() const { return mCalls; }
    std::uint64_t floors() const { return mFloors; }

private:
    MapMgr* mMap = nullptr;
    TraceProxy mProxy;
    std::uint64_t mCalls = 0, mFloors = 0;
};

// Deterministic scripted RNG for the Egg policy (the host owns the source).
struct ScriptRng {
    std::uint32_t state = 1u;
    float next();
    int nextInt(int count);
};

// ScriptRng adapters for the P2Egg policy function-pointer contracts.
float rngFloat(void* context);
int rngInt(void* context, int count);

// Host Wait-detection approximation: 3D distance to the active Navi / any live
// Pikmin within `sightRadius` (source isThereOlimar/isTherePikmin). Generalized
// from the lane-20 seam so each consumer supplies its own sight radius.
P2RockHazardDetection detectRock(const P2RockHazardVec3& from, float sightRadius);

} // namespace p2rockhost
