#pragma once

#include "pc_p2_bombsarai_terrain.h"
#include "Creature.h"
#include <cstdint>

class MapMgr;

// Lane-owned P1 binding of the BombSarai terrain adapter primitives
// (#244, #169 pattern). Mirrors pc_p2_groink_map_trace.h: a dedicated
// collision proxy, never registered with an actor manager. The owner
// creature's collision fields must not be reused for bomb traces.
class P2BombSaraiTraceProxy : public Creature {
public:
    P2BombSaraiTraceProxy() : Creature(nullptr) { clear(); }
    void clear();
    void refresh(Graphics&) override {}
    void wallCallback(immut Plane&, DynCollObject*) override { wall = true; }
    bool wall = false;
protected:
    void doKill() override {}
};

// Binds the two adapter primitives to the P1 static map. Use as:
//   P2BombSaraiTerrainAdapter adapter;
//   P2BombSaraiMapBinding binding;
//   binding.reset(mapMgr);
//   adapter.reset(P2BombSaraiMapBinding::traceMove, &binding,
//                 P2BombSaraiMapBinding::getMinY, &binding);
//   bomb.update(kDelta, P2BombSaraiTerrainAdapter::trace, &adapter, ...);
// The adapter owns center/base conversion, classification and the groundY
// contract; this class only performs the raw engine calls.
class P2BombSaraiMapBinding {
public:
    void reset(MapMgr* map);
    static bool traceMove(void* context, const P2BombSaraiVec3& sphereBase,
                          const P2BombSaraiVec3& velocity, float radius, float delta,
                          P2BombSaraiRawTrace& result);
    static float getMinY(void* context, float x, float z);
    std::uint64_t calls() const { return mCalls; }
    std::uint64_t floors() const { return mFloors; }
    std::uint64_t walls() const { return mWalls; }
private:
    MapMgr* mMap = nullptr;
    P2BombSaraiTraceProxy mProxy;
    std::uint64_t mCalls = 0, mFloors = 0, mWalls = 0;
};
