#include "pc_p2_bombsarai_terrain.h"

#include <cassert>
#include <cmath>
#include <limits>

namespace {
constexpr float kDelta = P2BombSaraiBomb::kSourceDelta;

bool near(float actual, float expected, float epsilon = 0.0001f)
{
    return std::fabs(actual - expected) <= epsilon;
}

struct Map {
    float groundY = 0.0f;
    bool groundTriangle = false;
    bool wall = false;
    bool snapToGround = false; // realistic mode: contact only when the sphere reaches terrain
    bool traceCalled = false;
    float requestedBaseY = 0.0f;
    bool minYCalled = false;
    bool failMinY = false;
};

bool traceMove(void* opaque, const P2BombSaraiVec3& sphereBase, const P2BombSaraiVec3& velocity,
               float radius, float delta, P2BombSaraiRawTrace& result)
{
    Map& map = *static_cast<Map*>(opaque);
    map.traceCalled = true;
    map.requestedBaseY = sphereBase.y;
    (void)radius;
    result.position = { sphereBase.x + velocity.x * delta, sphereBase.y + velocity.y * delta,
                        sphereBase.z + velocity.z * delta };
    result.velocity = velocity;
    result.groundTriangle = map.groundTriangle;
    result.wall = map.wall;
    if (map.snapToGround && result.position.y <= map.groundY + 0.001f) {
        result.position.y = map.groundY;
        result.groundTriangle = true;
    }
    return true;
}

float getMinY(void* opaque, float, float)
{
    Map& map = *static_cast<Map*>(opaque);
    map.minYCalled = true;
    return map.failMinY ? std::numeric_limits<float>::quiet_NaN() : map.groundY;
}

P2BombSaraiTerrainAdapter makeAdapter(Map& map)
{
    P2BombSaraiTerrainAdapter adapter;
    adapter.reset(traceMove, &map, getMinY, &map);
    return adapter;
}
}

int main()
{
    // Base/center conversion: the raw trace receives center.y - radius and
    // the result returns position.y + radius (P1 traceMove radius contract).
    {
        Map map;
        P2BombSaraiTerrainAdapter adapter = makeAdapter(map);
        P2BombSaraiTraceResult result;
        const P2BombSaraiVec3 center{ 0.0f, 50.0f, 0.0f };
        const P2BombSaraiVec3 velocity{ 0.0f, -30.0f, 0.0f };
        assert(P2BombSaraiTerrainAdapter::trace(&adapter, center, velocity, kDelta, 5.0f, result));
        assert(near(map.requestedBaseY, 45.0f));
        assert(near(result.position.y, 45.0f - 30.0f * kDelta + 5.0f));
        assert(!result.floor && !result.wall && !result.hasGroundY);
        assert(!map.minYCalled); // no contact: no terrain sample required
    }

    // Floor contact classifies, samples groundY and clamps below-ground
    // centers to the terrain; this feeds the bomb policy's arming decision.
    {
        Map map;
        map.groundY = 10.0f;
        map.groundTriangle = true;
        P2BombSaraiTerrainAdapter adapter = makeAdapter(map);
        P2BombSaraiTraceResult result;
        assert(P2BombSaraiTerrainAdapter::trace(&adapter, { 0, 10.5f, 0 }, { 0, -300, 0 },
                                                kDelta, 5.0f, result));
        assert(result.floor && !result.wall && result.hasGroundY);
        assert(near(result.groundY, 10.0f));
        assert(map.minYCalled);
        // Traced center 5.5-300/30+5 = 0.5, below ground: clamped to groundY.
        assert(near(result.position.y, 10.0f));

        // The full bomb policy arms through the adapter on this contact.
        P2BombSaraiBombConfig config;
        config.gravityPerTick = 6.0f;
        config.fuseHealth = 1.0f;
        config.armLoopTicks = 20;
        config.bombRadius = 5.0f;
        config.blastRadius = 75.0f;
        config.naviPikiDamage = 10.0f;
        P2BombSaraiBomb bomb;
        bomb.reset(config);
        assert(bomb.capture(1, { 0, 100, 0 }));
        assert(bomb.throwBomb(P2BombSaraiThrowKind::Death, 0.0f));
        Map map2;
        map2.groundY = 10.0f;
        map2.snapToGround = true;
        P2BombSaraiTerrainAdapter adapter2 = makeAdapter(map2);
        for (int i = 0; i < 200 && bomb.phase() == P2BombSaraiBombPhase::InFlight; ++i) {
            assert(bomb.update(kDelta, P2BombSaraiTerrainAdapter::trace, &adapter2, nullptr, nullptr));
        }
        assert(bomb.phase() == P2BombSaraiBombPhase::ArmedLoop);
        // Sphere center rests at groundY + radius, not at the ground itself.
        assert(near(bomb.position().y, 15.0f));
    }

    // Wall contact classifies and samples groundY but does not arm.
    {
        Map map;
        map.groundY = 10.0f;
        map.wall = true;
        P2BombSaraiTerrainAdapter adapter = makeAdapter(map);
        P2BombSaraiTraceResult result;
        assert(P2BombSaraiTerrainAdapter::trace(&adapter, { 0, 50, 0 }, { 300, 0, 0 },
                                                kDelta, 5.0f, result));
        assert(!result.floor && result.wall && result.hasGroundY);
        assert(near(result.position.y, 50.0f - 0.0f * kDelta)); // no floor clamp on wall

        P2BombSaraiBombConfig config;
        config.gravityPerTick = 6.0f;
        config.fuseHealth = 1.0f;
        config.armLoopTicks = 20;
        config.bombRadius = 5.0f;
        config.blastRadius = 75.0f;
        config.naviPikiDamage = 10.0f;
        P2BombSaraiBomb bomb;
        bomb.reset(config);
        assert(bomb.capture(1, { 0, 50, 0 }));
        assert(bomb.throwBomb(P2BombSaraiThrowKind::Release, 0.0f));
        Map map2;
        map2.groundY = 10.0f;
        map2.wall = true;
        P2BombSaraiTerrainAdapter adapter2 = makeAdapter(map2);
        assert(bomb.update(kDelta, P2BombSaraiTerrainAdapter::trace, &adapter2, nullptr, nullptr));
        assert(bomb.phase() == P2BombSaraiBombPhase::InFlight); // wall never arms
    }

    // A contact without a terrain sample fails the trace instead of
    // inventing ground; the bomb policy despawns on invalid terminal data.
    {
        Map map;
        map.groundTriangle = true;
        map.failMinY = true;
        P2BombSaraiTerrainAdapter adapter = makeAdapter(map);
        P2BombSaraiTraceResult result;
        assert(!P2BombSaraiTerrainAdapter::trace(&adapter, { 0, 20, 0 }, { 0, -300, 0 },
                                                 kDelta, 5.0f, result));
    }

    // Validation: unbound adapter, wrong delta, non-finite or absurd input.
    {
        Map map;
        P2BombSaraiTerrainAdapter unbound;
        P2BombSaraiTraceResult result;
        assert(!P2BombSaraiTerrainAdapter::trace(&unbound, { 0, 50, 0 }, { 0, -30, 0 },
                                                 kDelta, 5.0f, result));
        P2BombSaraiTerrainAdapter adapter = makeAdapter(map);
        assert(!P2BombSaraiTerrainAdapter::trace(&adapter, { 0, 50, 0 }, { 0, -30, 0 },
                                                 1.0f / 60.0f, 5.0f, result));
        assert(!P2BombSaraiTerrainAdapter::trace(&adapter, { 0, 50, 0 }, { 0, -30, 0 },
                                                 kDelta, -5.0f, result));
        assert(!P2BombSaraiTerrainAdapter::trace(&adapter, { 200000, 50, 0 }, { 0, -30, 0 },
                                                 kDelta, 5.0f, result));
        assert(!P2BombSaraiTerrainAdapter::trace(&adapter,
                                                 { 0, std::numeric_limits<float>::quiet_NaN(), 0 },
                                                 { 0, -30, 0 }, kDelta, 5.0f, result));
    }

    // Height sampling for hover/shadow logic with finite validation.
    {
        Map map;
        map.groundY = 12.5f;
        P2BombSaraiTerrainAdapter adapter = makeAdapter(map);
        float y = 0.0f;
        assert(P2BombSaraiTerrainAdapter::getMinY(&adapter, 1.0f, 2.0f, y));
        assert(near(y, 12.5f));
        assert(!P2BombSaraiTerrainAdapter::getMinY(&adapter,
                                                   std::numeric_limits<float>::quiet_NaN(), 2.0f, y));
        P2BombSaraiTerrainAdapter unbound;
        assert(!P2BombSaraiTerrainAdapter::getMinY(&unbound, 1.0f, 2.0f, y));
    }

    return 0;
}
