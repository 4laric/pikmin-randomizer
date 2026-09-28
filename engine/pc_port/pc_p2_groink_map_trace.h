#pragma once
#include "pc_p2_groink.h"
#include "Creature.h"
#include <cstdint>

class MapMgr;

// Standalone collision recorder; never registered with an actor manager.
// The owner creature's collision fields must not be reused for shell tracing.
class P2GroinkTraceProxy : public Creature {
public:
    P2GroinkTraceProxy() : Creature(nullptr) { clear(); }
    void clear();
    void refresh(Graphics&) override {}
    void wallCallback(immut Plane&, DynCollObject*) override { wall = true; }
    bool wall = false;
protected:
    void doKill() override {}
};

class P2GroinkMapTrace {
public:
    void reset(MapMgr* map);
    static bool trace(void* context, const P2GroinkVec3& center,
        const P2GroinkVec3& velocity, float delta, float radius,
        P2GroinkTraceResult& result);
    std::uint64_t calls() const { return mCalls; }
    std::uint64_t floors() const { return mFloors; }
    std::uint64_t walls() const { return mWalls; }
private:
    MapMgr* mMap = nullptr;
    P2GroinkTraceProxy mProxy;
    std::uint64_t mCalls = 0, mFloors = 0, mWalls = 0;
};
