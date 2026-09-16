// Standalone engine-free fixture for the BigTreasure persistent element runtime
// (pc_port/pc_p2_bigtreasure_elements.h/.cpp), issue #246. Proves the runtime
// starts the correct source controller, steps it with an injected terrain host
// and reports node/emission/bounce/ground counters, and tears down cleanly.
// Build (MinGW):
//   g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_bigtreasure_elements_test.cpp pc_port/pc_p2_bigtreasure_elements.cpp pc_port/pc_p2_bigtreasure_attacks.cpp -o <private-output>/p2_bigtreasure_elements_test.exe

#include "pc_p2_bigtreasure_elements.h"

#include <cassert>
#include <cstdio>

namespace {
constexpr float kDt = 1.0f / 30.0f;

bool mockTrace(void*, const P2BigTreasureVec3& position, const P2BigTreasureVec3& velocity,
               float, float, float, P2BigTreasureTraceResult& result)
{
    result.position = P2BigTreasureVec3{ position.x, 20.0f, position.z }; // floor at y=0
    result.velocity = P2BigTreasureVec3{ velocity.x, 0.0f, velocity.z };
    result.floor = true;
    result.wall = false;
    result.groundY = 0.0f;
    result.hasGroundY = true;
    return true;
}

bool mockGround(void*, float, float, float* outY)
{
    *outY = 0.0f;
    return true;
}

P2BigTreasureElementHost host()
{
    P2BigTreasureElementHost h;
    h.context = nullptr;
    h.trace = mockTrace;
    h.ground = mockGround;
    return h;
}

void testFireGas()
{
    P2BigTreasureElementRuntime runtime;
    P2BigTreasureElementHost h = host();
    P2BigTreasureElementStats stats;

    assert(runtime.start(P2BTWEAPON_Fire, P2BigTreasureVec3{ 0, 0, 0 }, 0.0f,
                         P2BigTreasureOwnership::kWeaponMaxHealth, 0.25f, 0.25f));
    assert(runtime.active() && runtime.activeWeapon() == P2BTWEAPON_Fire);
    int emitted = 0;
    for (int i = 0; i < 30; ++i) {
        runtime.tick(kDt, h, stats);
        emitted += stats.emits;
    }
    assert(stats.nodes > 0 && emitted > 0);
    runtime.finish();
    assert(!runtime.active());

    assert(runtime.start(P2BTWEAPON_Gas, P2BigTreasureVec3{ 0, 0, 0 }, 0.0f,
                         P2BigTreasureOwnership::kWeaponMaxHealth, 0.25f, 0.25f));
    int gasNodes = 0;
    for (int i = 0; i < 30; ++i) {
        runtime.tick(kDt, h, stats);
        gasNodes = stats.nodes;
    }
    assert(gasNodes > 0);
    runtime.defeat();
    assert(!runtime.active());
    std::puts("PASS elements_fire_gas");
}

void testWaterGroundHit()
{
    P2BigTreasureElementRuntime runtime;
    P2BigTreasureElementHost h = host();
    P2BigTreasureElementStats stats;
    assert(runtime.start(P2BTWEAPON_Water, P2BigTreasureVec3{ 0, 0, 0 }, 0.0f,
                         P2BigTreasureOwnership::kWeaponMaxHealth, 0.25f, 0.25f));
    int hits = 0;
    for (int i = 0; i < 80; ++i) {
        runtime.tick(kDt, h, stats);
        hits += stats.groundHits;
    }
    assert(hits > 0);
    runtime.defeat();
    std::puts("PASS elements_water_ground");
}

void testElecBounce()
{
    P2BigTreasureElementRuntime runtime;
    P2BigTreasureElementHost h = host();
    P2BigTreasureElementStats stats;
    assert(runtime.start(P2BTWEAPON_Elec, P2BigTreasureVec3{ 0, 0, 0 }, 0.0f,
                         P2BigTreasureOwnership::kWeaponMaxHealth, 0.25f, 0.25f));
    int bounces = 0, maxNodes = 0;
    for (int i = 0; i < 40; ++i) {
        runtime.tick(kDt, h, stats);
        bounces += stats.bounces;
        if (stats.nodes > maxNodes) maxNodes = stats.nodes;
    }
    assert(maxNodes > 1); // anchor + at least one visible node
    assert(bounces > 0);
    runtime.finish();
    std::puts("PASS elements_elec_bounce");
}

void testInvalidAndEmpty()
{
    P2BigTreasureElementRuntime runtime;
    P2BigTreasureElementHost h = host();
    P2BigTreasureElementStats stats;
    assert(!runtime.start(-1, P2BigTreasureVec3{}, 0.0f, 6000.0f, 0.25f, 0.25f));
    assert(!runtime.start(P2BTWEAPON_Count, P2BigTreasureVec3{}, 0.0f, 6000.0f, 0.25f, 0.25f));
    runtime.tick(kDt, h, stats); // inactive: no-op
    assert(stats.nodes == 0 && stats.emits == 0);
    std::puts("PASS elements_invalid");
}
void testQueryHit()
{
    P2BigTreasureElementRuntime runtime;
    P2BigTreasureElementHost h = host();
    P2BigTreasureElementStats stats;

    // Inactive runtime never reports a hit.
    assert(!runtime.queryHit(P2BigTreasureVec3{ 0, 0, 0 }));

    // Water: after the first emitted bubble, the emit anchor is inside the
    // in-flight radius.
    assert(runtime.start(P2BTWEAPON_Water, P2BigTreasureVec3{ 0, 0, 0 }, 0.0f,
                         P2BigTreasureOwnership::kWeaponMaxHealth, 0.25f, 0.25f));
    int emitted = 0;
    for (int i = 0; i < 40 && emitted == 0; ++i) {
        runtime.tick(kDt, h, stats);
        emitted = stats.nodes;
    }
    assert(emitted > 0);
    int index = -1;
    assert(runtime.queryHit(P2BigTreasureVec3{ 0, 100, 0 }, &index));
    assert(index >= 0);
    runtime.defeat();

    // Elec chain geometry (source chainHit): a point on the segment registers.
    const P2BigTreasureVec3 a{ 0, 0, 0 };
    const P2BigTreasureVec3 b{ 0, 0, 40 };
    assert(P2BigTreasureElecPolicy::chainHit(a, b, P2BigTreasureVec3{ 0, 0, 20 }));
    assert(!P2BigTreasureElecPolicy::chainHit(a, b, P2BigTreasureVec3{ 50, 0, 20 }));
    std::puts("PASS elements_query_hit");
}
} // namespace

int main()
{
    testFireGas();
    testWaterGroundHit();
    testElecBounce();
    testInvalidAndEmpty();
    testQueryHit();
    std::puts("PASS BIGTREASURE_ELEMENTS");
    return 0;
}
