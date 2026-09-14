#include "pc_p2_bigtreasure_attacks.h"

#include <cassert>
#include <cmath>
#include <cstdio>

// Per-element attack controller fixtures for BigTreasure, issue #246.
// Deterministic, 30 Hz source ticks, mock terrain/trace adapter. Source
// references: BTA = BigTreasureAttack.cpp, BTC = BigTreasure.cpp at research
// revision 632af937.

namespace {

constexpr float kDt = 1.0f / 30.0f;

bool near(float actual, float expected, float epsilon = 0.001f)
{
    return std::fabs(actual - expected) <= epsilon;
}

// ---------------------------------------------------------------------------
// Mock lane-owned adapter: flat floor at a configurable height, plus an
// optional vertical wall plane for bounce tests.

struct MockWorld {
    float floorY = 0.0f;
    bool hasWall = false;
    float wallX = 50.0f; // wall plane x = wallX, blocks -x crossing
    int traceCalls = 0;
    float lastRadius = 0.0f;
    float lastBounceFactor = 0.0f;
};

bool mockGround(void* context, float, float, float* outY)
{
    MockWorld& world = *static_cast<MockWorld*>(context);
    *outY = world.floorY;
    return true;
}

bool mockTrace(void* context, const P2BigTreasureVec3& position, const P2BigTreasureVec3& velocity,
               float delta, float radius, float bounceFactor, P2BigTreasureTraceResult& result)
{
    MockWorld& world = *static_cast<MockWorld*>(context);
    world.traceCalls++;
    world.lastRadius = radius;
    world.lastBounceFactor = bounceFactor;

    result.position = P2BigTreasureVec3{ position.x + velocity.x * delta,
                                         position.y + velocity.y * delta,
                                         position.z + velocity.z * delta };
    result.velocity = velocity;
    result.floor = false;
    result.wall = false;
    result.groundY = world.floorY;
    result.hasGroundY = true;

    if (result.position.y - radius < world.floorY) {
        result.position.y = world.floorY + radius;
        result.velocity.y = -velocity.y * bounceFactor;
        result.floor = true;
    }
    if (world.hasWall && position.x >= world.wallX && result.position.x < world.wallX) {
        result.position.x = world.wallX;
        result.velocity.x = -velocity.x * bounceFactor;
        result.wall = true;
    }
    return true;
}

// Fire: swept segments, spawn cadence, extent recycle, directional triplet,
// damaged scale at the 3000 boundary.
void testFire()
{
    // Parameter boundary (strict > 3000).
    assert(near(p2_bigtreasure_fire_params(6000.0f).scale, 1.0f));
    assert(near(p2_bigtreasure_fire_params(3000.0f).scale, 1.25f));
    assert(near(p2_bigtreasure_fire_params(2999.0f).scale, 1.25f));

    // Directional quadrants (BTC :1135-1145).
    const float pi = 3.14159265358979f;
    assert(p2_bigtreasure_fire_direction(0.0f) == 0);           // F
    assert(p2_bigtreasure_fire_direction(pi / 2.0f) == 1);      // FL
    assert(p2_bigtreasure_fire_direction(pi) == 2);             // FB
    assert(p2_bigtreasure_fire_direction(3.0f * pi / 2.0f) == 3); // FR
    assert(p2_bigtreasure_fire_direction(pi / 4.0f) == 0);      // boundary: not > pi/4
    assert(p2_bigtreasure_fire_direction(-pi / 2.0f) == 3);     // wrapped

    P2BigTreasureFirePolicy fire;
    assert(fire.start(p2_bigtreasure_fire_params(6000.0f)));
    assert(!fire.start(p2_bigtreasure_fire_params(6000.0f))); // already started
    assert(fire.nodeCount() == 1);                            // immediate node

    // Spawn cadence: a new node each 0.1 s while started (4th tick at 30 Hz).
    fire.tick(kDt);
    fire.tick(kDt);
    fire.tick(kDt);
    assert(fire.nodeCount() == 2);

    // Nodes self-recycle at full extent (~1/3 s at 3/s).
    fire.finish();
    int recycled = 0;
    for (int i = 0; i < 20; i++) recycled += fire.tick(kDt);
    assert(recycled >= 1);
    for (int i = 0; i < 30; i++) fire.tick(kDt);
    assert(fire.nodeCount() == 0); // in-flight nodes drained after finish

    // Hit geometry: extent 200*ratio*scale, radius 25, Y gate 40*scale.
    P2BigTreasureFirePolicy geom;
    geom.start(p2_bigtreasure_fire_params(6000.0f));
    const P2BigTreasureVec3 emitPos{ 0.0f, 100.0f, 0.0f };
    const P2BigTreasureVec3 dirZ{ 0.0f, 0.0f, 1.0f };
    // Force ratio to 0.5 by ticking ~0.1667 s.
    for (int i = 0; i < 5; i++) geom.tick(kDt);
    const float ratio = geom.nodeRatio(0);
    assert(ratio > 0.4f && ratio < 0.6f);
    const float extent = ratio * 200.0f;
    assert(geom.nodeHit(0, emitPos, dirZ, P2BigTreasureVec3{ 0.0f, 75.0f, extent }));
    assert(!geom.nodeHit(0, emitPos, dirZ, P2BigTreasureVec3{ 100.0f, 75.0f, extent })); // x outside r25
    assert(!geom.nodeHit(0, emitPos, dirZ, P2BigTreasureVec3{ 0.0f, 10.0f, extent }));  // y gate
    // Damaged scale widens the radius/gate and extent.
    P2BigTreasureFirePolicy dmg;
    dmg.start(p2_bigtreasure_fire_params(2500.0f));
    for (int i = 0; i < 5; i++) dmg.tick(kDt);
    assert(dmg.nodeHit(0, emitPos, dirZ, P2BigTreasureVec3{ 30.0f, 75.0f, extent * 1.25f }));
}

// Gas: arm layout, rotation direction + reversal, bitter freeze, radius
// switch at half extent, damaged arm sets.
void testGas()
{
    P2BigTreasureGasParams normal = p2_bigtreasure_gas_params(6000.0f, 0.0f);
    assert(normal.armNum == 3 && near(normal.rotationSpeed, 0.015f) && near(normal.reversalTime, 30.0f));
    P2BigTreasureGasParams dmg2 = p2_bigtreasure_gas_params(2500.0f, 0.25f);
    assert(dmg2.armNum == 4 && near(dmg2.rotationSpeed, 0.02f) && near(dmg2.reversalTime, 30.0f));
    P2BigTreasureGasParams dmg3 = p2_bigtreasure_gas_params(2500.0f, 0.75f);
    assert(dmg3.armNum == 4 && near(dmg3.reversalTime, 2.0f));
    // Boundary: exactly 3000 is the damaged set (strict >).
    assert(p2_bigtreasure_gas_params(3000.0f, 0.0f).armNum == 4);

    P2BigTreasureGasPolicy gas;
    assert(gas.start(normal, 0.0f, true));
    assert(gas.nodeCount() == 3); // one node per arm immediately
    assert(near(gas.armAngle(0), 0.0f));
    assert(near(gas.armAngle(1), 2.0943951f));
    assert(near(gas.armAngle(2), 4.1887902f));

    // Clockwise rotation per source update; angle wraps.
    gas.tick(kDt, false);
    assert(near(gas.armAngle(0), 0.015f));

    // Reversal after 30 s flips direction.
    for (int i = 0; i < 31 * 30; i++) gas.tick(kDt, false);
    assert(!gas.isClockwise());

    // Bitter freeze: angles do not move while bittered.
    const float frozen = gas.armAngle(0);
    gas.tick(kDt, true);
    assert(near(gas.armAngle(0), frozen));

    // Emission cadence adds a full arm set every 0.1 s.
    P2BigTreasureGasPolicy cadence;
    cadence.start(normal, 0.0f, true);
    for (int i = 0; i < 4; i++) cadence.tick(kDt, false);
    assert(cadence.nodeCount() >= 6);

    // Hit geometry: radius 10 before half extent, 15 after.
    const P2BigTreasureVec3 emitPos{ 0.0f, 15.0f, 0.0f };
    P2BigTreasureGasPolicy geom;
    geom.start(normal, 0.0f, true); // arm 0 points +z (sin 0, cos 0)... angle 0 => +z
    const float distAt = 480.0f * 0.4f; // ratio 0.4
    assert(geom.nodeHit(emitPos, 0, 0.4f, P2BigTreasureVec3{ 0.0f, 0.0f, distAt }));
    assert(!geom.nodeHit(emitPos, 0, 0.4f, P2BigTreasureVec3{ 12.0f, 0.0f, distAt })); // outside r10
    assert(geom.nodeHit(emitPos, 0, 0.6f, P2BigTreasureVec3{ 14.0f, 0.0f, 480.0f * 0.6f })); // r15 past half
    assert(!geom.nodeHit(emitPos, 0, 0.6f, P2BigTreasureVec3{ 0.0f, 100.0f, 480.0f * 0.6f })); // y gate

    // Exhaustion: 200 nodes max.
    P2BigTreasureGasPolicy exhaust;
    exhaust.start(normal, 0.0f, true);
    for (int i = 0; i < 30 * 10; i++) exhaust.tick(kDt, false); // 10 s: 100 sets * 3 = 300 > 200
    assert(exhaust.nodeCount() <= 200);
}

// Water: ballistic arc, floor impact via adapter, radius switch, damaged
// interval, persistence across finish, defeat teardown.
void testWater()
{
    P2BigTreasureWaterParams normal = p2_bigtreasure_water_params(6000.0f);
    assert(near(normal.shotInterval, 0.5f) && near(normal.jitterDistance, 100.0f));
    P2BigTreasureWaterParams damaged = p2_bigtreasure_water_params(3000.0f);
    assert(near(damaged.shotInterval, 0.25f) && near(damaged.jitterAngle, 0.4f));

    MockWorld world;
    world.floorY = 0.0f;

    P2BigTreasureWaterPolicy water;
    assert(water.start(normal));

    // Source velocity: emit at (0,100,0), target 200 ahead on z, no jitter.
    const P2BigTreasureVec3 emitPos{ 0.0f, 100.0f, 0.0f };
    const P2BigTreasureVec3 targetPos{ 0.0f, 0.0f, 200.0f };
    assert(water.emitShot(emitPos, targetPos, 0.0f, 0.0f, kDt));
    assert(water.activeCount() == 1);
    const P2BigTreasureWaterNode& shot = water.node(0);
    assert(near(shot.velocity.y, 525.0f));           // 350/dt/20
    assert(near(shot.velocity.x, 0.0f));
    // speed = 0.5*200 / (525/20) / dt = 100/26.25*30
    assert(near(shot.velocity.z, 114.2857f, 0.01f));

    // Ballistic arc: gravity -20 per update; floor impact recycles with a hit.
    int groundHits = 0;
    int recycled = 0;
    for (int i = 0; i < 90 && water.activeCount() > 0; i++) {
        int hits = 0;
        recycled += water.tick(kDt, mockGround, &world, &hits);
        groundHits += hits;
    }
    assert(recycled == 1 && groundHits == 1);
    assert(water.activeCount() == 0);

    // Hit geometry: 20 in flight, 30 on ground.
    P2BigTreasureWaterPolicy geom;
    geom.start(normal);
    geom.emitShot(emitPos, targetPos, 0.0f, 0.0f, kDt);
    assert(geom.nodeHit(0, P2BigTreasureVec3{ 0.0f, 105.0f, 5.0f }, false));
    assert(!geom.nodeHit(0, P2BigTreasureVec3{ 0.0f, 130.0f, 5.0f }, false));
    assert(geom.nodeHit(0, P2BigTreasureVec3{ 0.0f, 125.0f, 5.0f }, true)); // r30 on ground

    // Persistence across finish (source gap 2), defeat teardown.
    P2BigTreasureWaterPolicy persist;
    persist.start(normal);
    persist.emitShot(emitPos, targetPos, 0.0f, 0.0f, kDt);
    persist.finish();
    assert(persist.activeCount() == 1); // bubble survives state exit
    persist.defeat();
    assert(persist.activeCount() == 0); // lane teardown recycles it

    // Emitter cadence: shot due every 0.5 s normal / 0.25 s damaged (strict
    // > against the interval, so the first shot lands on tick 16 / 9).
    P2BigTreasureWaterPolicy cadence;
    cadence.start(normal);
    int due = 0;
    for (int i = 0; i < 33; i++) { // 1.1 s
        if (cadence.tickEmitter(kDt)) due++;
    }
    assert(due == 2);
    P2BigTreasureWaterPolicy cadenceD;
    cadenceD.start(damaged);
    due = 0;
    for (int i = 0; i < 33; i++) {
        if (cadenceD.tickEmitter(kDt)) due++;
    }
    assert(due == 4);

    // Pool exhaustion: 16 shots max.
    P2BigTreasureWaterPolicy exhaust;
    exhaust.start(normal);
    int emitted = 0;
    for (int i = 0; i < 20; i++) {
        if (exhaust.emitShot(emitPos, targetPos, 0.0f, 0.0f, kDt)) emitted++;
    }
    assert(emitted == 16);
}

// Elec: anchor + discharge spawn, adapter bounce/friction, wall bounce,
// scatter delay then pairwise chaining, chain hit geometry, invariant,
// finish recycling.
void testElec()
{
    // Parameter sets across the 3000 boundary.
    P2BigTreasureElecParams n1 = p2_bigtreasure_elec_params(6000.0f, 0.25f);
    assert(n1.maxDischarge == 10 && near(n1.scatterTime, 2.7f) && near(n1.chainInterval, 0.02f));
    P2BigTreasureElecParams n2 = p2_bigtreasure_elec_params(6000.0f, 0.75f);
    assert(n2.maxDischarge == 12 && near(n2.scatterTime, 4.5f));
    P2BigTreasureElecParams d3 = p2_bigtreasure_elec_params(3000.0f, 0.25f);
    assert(d3.maxDischarge == 8 && near(d3.scatterTime, 0.5f));
    P2BigTreasureElecParams d4 = p2_bigtreasure_elec_params(2500.0f, 0.75f);
    assert(d4.maxDischarge == 14 && near(d4.bounceFactor, 0.2f));

    MockWorld world;
    world.floorY = 0.0f;

    P2BigTreasureElecPolicy elec;
    const P2BigTreasureVec3 joint{ 0.0f, 150.0f, 0.0f };
    float zeroJit[16] = {};
    assert(elec.start(n1, joint, 0.0f, zeroJit, zeroJit, zeroJit));
    assert(elec.activeCount() == 11); // 1 anchor + 10 visible
    assert(!elec.node(0).visible);    // anchor tracks the joint

    // Invariant: 1 + maxDischarge <= 17.
    P2BigTreasureElecParams tooMany = n1;
    tooMany.maxDischarge = 17;
    P2BigTreasureElecPolicy refused;
    assert(!refused.start(tooMany, joint, 0.0f, zeroJit, zeroJit, zeroJit));
    tooMany.maxDischarge = 16;
    assert(refused.start(tooMany, joint, 0.0f, zeroJit, zeroJit, zeroJit));

    // Anchor follows the joint; visible nodes trace and bounce.
    int bounces = 0;
    elec.tick(kDt, joint, mockTrace, &world, &bounces);
    assert(world.traceCalls == 10);           // visible nodes only
    assert(world.lastRadius == 20.0f);        // radius-20 sphere
    assert(near(world.lastBounceFactor, 0.75f));
    P2BigTreasureVec3 movedJoint{ 10.0f, 150.0f, 0.0f };
    elec.tick(kDt, movedJoint, mockTrace, &world, &bounces);
    assert(near(elec.node(0).position.x, 10.0f));

    // Nodes fall, hit the floor, bounce (velocity flipped by factor) and get
    // floor friction 0.65 on x/z. Run until at least one bounce is reported.
    int totalBounces = 0;
    for (int i = 0; i < 300 && totalBounces == 0; i++) {
        int b = 0;
        elec.tick(kDt, joint, mockTrace, &world, &b);
        totalBounces += b;
    }
    assert(totalBounces > 0);

    // Wall bounce: aim a node at the wall.
    MockWorld walled;
    walled.hasWall = true;
    walled.wallX = 0.0f;
    P2BigTreasureVec3 pos{ 5.0f, 100.0f, 0.0f };
    P2BigTreasureVec3 vel{ -300.0f, 0.0f, 0.0f }; // crosses the wall in one tick
    P2BigTreasureTraceResult result;
    assert(mockTrace(&walled, pos, vel, kDt, 20.0f, 0.75f, result));
    assert(result.wall && result.velocity.x > 0.0f);

    // Scatter delay gates chaining: set 1 has 2.7 s scatter; nothing links
    // before that, pairwise links appear after.
    P2BigTreasureElecPolicy chain;
    assert(chain.start(d3, joint, 0.0f, zeroJit, zeroJit, zeroJit)); // scatter 0.5 s
    for (int i = 0; i < 14; i++) chain.tick(kDt, joint, mockTrace, &world, nullptr);
    assert(chain.chainedCount() == 0); // 0.467 s < 0.5 s scatter
    for (int i = 0; i < 20; i++) chain.tick(kDt, joint, mockTrace, &world, nullptr);
    assert(chain.chainedCount() > 0);

    // Chain hit geometry: creature between two linked nodes within the
    // 10 x 20 cross-section.
    const P2BigTreasureVec3 a{ 0.0f, 0.0f, 0.0f };
    const P2BigTreasureVec3 b{ 0.0f, 0.0f, 100.0f };
    assert(P2BigTreasureElecPolicy::chainHit(a, b, P2BigTreasureVec3{ 5.0f, 10.0f, 50.0f }));
    assert(!P2BigTreasureElecPolicy::chainHit(a, b, P2BigTreasureVec3{ 15.0f, 0.0f, 50.0f }));  // |dot1| >= 10
    assert(!P2BigTreasureElecPolicy::chainHit(a, b, P2BigTreasureVec3{ 0.0f, 25.0f, 50.0f }));  // |dot2| >= 20
    assert(!P2BigTreasureElecPolicy::chainHit(a, b, P2BigTreasureVec3{ 0.0f, 0.0f, 150.0f }));  // past segment
    assert(!P2BigTreasureElecPolicy::chainHit(a, b, P2BigTreasureVec3{ 0.0f, 0.0f, -10.0f }));  // behind

    // finish recycles every node (BTA :2979-3003).
    elec.finish();
    assert(elec.activeCount() == 0 && !elec.isStarted());
}

// Director: pacing gate + weighted pick + started flags, one attack at a
// time; bitter force-finish; defeat teardown across all element pools.
void testDirector()
{
    P2BigTreasureOwnership owner;
    for (int i = 0; i < P2BTWEAPON_Count; i++) owner.attachWeapon(i);

    P2BigTreasureAttackDirector director;
    director.pacer.reset(0.0f);

    // Below the 12 s threshold with 4 weapons: no attack.
    for (int i = 0; i < 300; i++) {
        assert(director.tickEntry(owner, kDt, true, false, 0.0f) == -1);
    }
    // Past threshold with a target: elec band starts first (threshold 0).
    int started = -1;
    for (int i = 0; i < 90 && started < 0; i++) {
        started = director.tickEntry(owner, kDt, true, false, 0.0f);
    }
    assert(started == P2BTWEAPON_Elec);
    assert(director.pools.isStarted(P2BTWEAPON_Elec));

    // Already started: re-entry is blocked until finished.
    assert(director.pools.start(P2BTWEAPON_Elec) == false);

    // Bitter + lost weapon force-finishes.
    director.bitterWeaponLost();
    assert(!director.pools.isStarted(P2BTWEAPON_Elec));

    // No weapons: no pick, no attack.
    P2BigTreasureOwnership empty;
    P2BigTreasureAttackDirector director2;
    director2.pacer.reset(100.0f); // already past any threshold
    assert(director2.tickEntry(empty, kDt, true, false, 0.0f) == -1);

    // Defeat teardown clears all pools.
    director.pools.start(P2BTWEAPON_Water);
    director.pools.emit(P2BTWEAPON_Water);
    director.defeat();
    assert(director.pools.inFlight(P2BTWEAPON_Water) == 0);
    assert(!director.pools.isStarted(P2BTWEAPON_Water));
}

} // namespace

int main()
{
    testFire();
    testGas();
    testWater();
    testElec();
    testDirector();
    std::puts("p2_bigtreasure_attacks_test: all fixtures passed");
    return 0;
}
