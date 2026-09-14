#include "pc_p2_bombsarai_bomb.h"

#include <cassert>
#include <cmath>
#include <limits>

namespace {
constexpr float kDelta = P2BombSaraiBomb::kSourceDelta;

P2BombSaraiBombConfig testConfig()
{
    P2BombSaraiBombConfig config;
    config.gravityPerTick = 6.0f;   // arbitrary fixture value, host-owned in production
    config.fuseHealth = 1.0f;       // 30 source ticks of burn at 1.0 per second
    config.armLoopTicks = 20;
    config.bombRadius = 5.0f;
    config.blastRadius = 75.0f;
    config.blastHalfHeight = 50.0f; // fp02 default
    config.tekiDamage = 250.0f;     // fp01 default
    config.naviPikiDamage = 10.0f;
    return config;
}

bool near(float actual, float expected, float epsilon = 0.0001f)
{
    return std::fabs(actual - expected) <= epsilon;
}

struct Trace {
    bool floor = false;
    bool wall = false;
    int calls = 0;
    float radius = 0.0f;
    float groundY = 0.0f;
};
bool trace(void* opaque, const P2BombSaraiVec3& position, const P2BombSaraiVec3& velocity,
           float delta, float radius, P2BombSaraiTraceResult& result)
{
    Trace& state = *static_cast<Trace*>(opaque);
    ++state.calls;
    state.radius = radius;
    result.position = { position.x + velocity.x * delta, position.y + velocity.y * delta,
                        position.z + velocity.z * delta };
    result.velocity = velocity;
    result.floor = state.floor;
    result.wall = state.wall;
    result.groundY = state.groundY;
    result.hasGroundY = true;
    return true;
}

struct Carrier {
    bool alive = true;
    std::uint64_t queried = 0;
};
bool carrierAlive(void* opaque, std::uint64_t token)
{
    Carrier& state = *static_cast<Carrier*>(opaque);
    state.queried = token;
    return state.alive;
}

P2BombSaraiBomb makeCaptured(const P2BombSaraiBombConfig& config, std::uint64_t token)
{
    P2BombSaraiBomb bomb;
    bomb.reset(config);
    assert(bomb.capture(token, { 10.0f, 90.0f, 20.0f }));
    return bomb;
}

void runToBlast(P2BombSaraiBomb& bomb, Trace& traceState, Carrier& carrierState)
{
    // Land and arm.
    traceState.floor = true;
    assert(bomb.update(kDelta, trace, &traceState, carrierAlive, &carrierState));
    assert(bomb.phase() == P2BombSaraiBombPhase::ArmedLoop);
    traceState.floor = false;
    // 20 arm ticks then 30 burn ticks then 10 delay ticks; poll generously.
    for (int i = 0; i < 200 && !bomb.hasBlast(); ++i) {
        assert(bomb.update(kDelta, trace, &traceState, carrierAlive, &carrierState));
    }
    assert(bomb.hasBlast());
}
}

int main()
{
    const P2BombSaraiBombConfig config = testConfig();

    // Source throw velocities (BombSaraiState.cpp:528-531, :592-595, BombSarai.cpp:57-61).
    {
        const P2BombSaraiVec3 release = P2BombSaraiBomb::throwVelocity(P2BombSaraiThrowKind::Release, 0.0f);
        assert(near(release.x, 0.0f) && near(release.y, 100.0f) && near(release.z, 50.0f));
        const P2BombSaraiVec3 fall = P2BombSaraiBomb::throwVelocity(P2BombSaraiThrowKind::Fall, 0.0f);
        assert(near(fall.x, 0.0f) && near(fall.y, 300.0f) && near(fall.z, 100.0f));
        const P2BombSaraiVec3 death = P2BombSaraiBomb::throwVelocity(P2BombSaraiThrowKind::Death, 1.0f);
        assert(near(death.x, 0.0f) && near(death.y, 0.0f) && near(death.z, 0.0f));
        const float face = 0.5f;
        const P2BombSaraiVec3 angled = P2BombSaraiBomb::throwVelocity(P2BombSaraiThrowKind::Release, face);
        assert(near(angled.x, 50.0f * std::sin(face)) && near(angled.z, 50.0f * std::cos(face)));
    }

    // Capture is constrained/invulnerable: update is a host-driven no-op.
    {
        P2BombSaraiBomb bomb = makeCaptured(config, 7);
        Trace traceState;
        assert(bomb.update(kDelta, trace, &traceState, nullptr, nullptr));
        assert(bomb.phase() == P2BombSaraiBombPhase::Captured);
        assert(traceState.calls == 0);
        assert(near(bomb.position().y, 90.0f));
    }

    // Throw no-op unless captured (source null-mHeldBomb no-op).
    {
        P2BombSaraiBomb bomb;
        bomb.reset(config);
        assert(!bomb.throwBomb(P2BombSaraiThrowKind::Release, 0.0f));
        bomb = makeCaptured(config, 7);
        assert(bomb.throwBomb(P2BombSaraiThrowKind::Release, 0.0f));
        assert(!bomb.throwBomb(P2BombSaraiThrowKind::Release, 0.0f));
    }

    // Fixed-step rejection: no wall clock, no substituted delta.
    {
        P2BombSaraiBomb bomb = makeCaptured(config, 7);
        assert(bomb.throwBomb(P2BombSaraiThrowKind::Release, 0.0f));
        Trace traceState;
        assert(!bomb.update(1.0f / 60.0f, trace, &traceState, nullptr, nullptr));
        assert(!bomb.update(std::numeric_limits<float>::quiet_NaN(), trace, &traceState, nullptr, nullptr));
        assert(bomb.phase() == P2BombSaraiBombPhase::InFlight);
    }

    // Ballistic flight: no trace performs straight integration, gravity applies per tick.
    {
        P2BombSaraiBomb bomb = makeCaptured(config, 7);
        assert(bomb.throwBomb(P2BombSaraiThrowKind::Release, 0.0f));
        assert(bomb.update(kDelta, nullptr, nullptr, nullptr, nullptr));
        assert(near(bomb.position().y, 90.0f + 100.0f * kDelta));
        assert(near(bomb.velocity().y, 100.0f - 6.0f));
        assert(bomb.phase() == P2BombSaraiBombPhase::InFlight);
    }

    // Floor contact arms the fuse; wall contact alone does not.
    {
        P2BombSaraiBomb bomb = makeCaptured(config, 7);
        assert(bomb.throwBomb(P2BombSaraiThrowKind::Release, 0.0f));
        Trace traceState;
        traceState.wall = true;
        assert(bomb.update(kDelta, trace, &traceState, nullptr, nullptr));
        assert(bomb.phase() == P2BombSaraiBombPhase::InFlight);
        assert(near(traceState.radius, 5.0f));
        traceState.wall = false;
        traceState.floor = true;
        traceState.groundY = 12.0f;
        assert(bomb.update(kDelta, trace, &traceState, nullptr, nullptr));
        assert(bomb.phase() == P2BombSaraiBombPhase::ArmedLoop);
        assert(near(bomb.velocity().x, 0.0f) && near(bomb.velocity().y, 0.0f));
    }

    // Full fuse: 20 arm ticks, health-drain burn, fixed 10-tick delay, one blast.
    {
        P2BombSaraiBomb bomb = makeCaptured(config, 42);
        assert(bomb.throwBomb(P2BombSaraiThrowKind::Release, 0.0f));
        Trace traceState;
        Carrier carrierState;
        runToBlast(bomb, traceState, carrierState);
        const P2BombSaraiBlastEvent& blast = bomb.lastBlast();
        assert(near(blast.radius, 75.0f));
        assert(near(blast.halfHeight, 50.0f));
        assert(near(blast.tekiDamage, 250.0f));
        assert(near(blast.naviPikiDamage, 10.0f));
        assert(near(blast.knockbackNavi, 100.0f) && near(blast.knockbackPiki, 200.0f));
        assert(blast.hasCarrier && blast.carrierValid && blast.carrierToken == 42);
        assert(carrierState.queried == 42);
        assert(bomb.phase() == P2BombSaraiBombPhase::Despawned);
        // Blast fires exactly once; later updates are inert.
        assert(!bomb.update(kDelta, trace, &traceState, carrierAlive, &carrierState));
    }

    // Fuse timing boundaries: arm loop length and 10-tick delay are exact.
    {
        // fuseHealth 0.5 fully drains during the 20-tick arm loop, so Burning
        // starts at zero health and the fixed 10-tick delay is measured alone.
        P2BombSaraiBombConfig timed = config;
        timed.fuseHealth = 0.5f;
        P2BombSaraiBomb bomb;
        bomb.reset(timed);
        assert(bomb.capture(42, { 10.0f, 90.0f, 20.0f }));
        assert(bomb.throwBomb(P2BombSaraiThrowKind::Release, 0.0f));
        Trace traceState;
        Carrier carrierState;
        traceState.floor = true;
        assert(bomb.update(kDelta, trace, &traceState, carrierAlive, &carrierState));
        traceState.floor = false;
        for (int i = 0; i < 20; ++i) {
            assert(bomb.update(kDelta, trace, &traceState, carrierAlive, &carrierState));
            assert(i < 19 ? bomb.phase() == P2BombSaraiBombPhase::ArmedLoop
                          : bomb.phase() == P2BombSaraiBombPhase::Burning);
        }
        int burnTicks = 0;
        while (!bomb.hasBlast()) {
            assert(bomb.update(kDelta, trace, &traceState, carrierAlive, &carrierState));
            ++burnTicks;
            assert(burnTicks <= 10);
        }
        assert(burnTicks == 10); // exactly the 10-tick detonation delay
    }

    // Stale carrier: unconfirmed carrier falls back to bomb-self attribution.
    {
        P2BombSaraiBomb bomb = makeCaptured(config, 99);
        assert(bomb.throwBomb(P2BombSaraiThrowKind::Fall, 0.0f));
        Trace traceState;
        Carrier carrierState;
        carrierState.alive = false; // carrier died/was reused while the lob was in flight
        runToBlast(bomb, traceState, carrierState);
        const P2BombSaraiBlastEvent& blast = bomb.lastBlast();
        assert(blast.hasCarrier && !blast.carrierValid && blast.carrierToken == 99);
    }

    // Death drop: zero velocity, then normal floor-armed fuse.
    {
        P2BombSaraiBomb bomb = makeCaptured(config, 5);
        assert(bomb.throwBomb(P2BombSaraiThrowKind::Death, 0.0f));
        assert(near(bomb.velocity().x, 0.0f) && near(bomb.velocity().y, 0.0f));
        assert(bomb.update(kDelta, nullptr, nullptr, nullptr, nullptr));
        assert(near(bomb.velocity().y, -6.0f));
        Trace traceState;
        Carrier carrierState;
        runToBlast(bomb, traceState, carrierState);
        assert(bomb.lastBlast().carrierValid);
    }

    // Escaped-capture despawn: 200 ticks in BOMB_Wait without landing kills silently.
    {
        P2BombSaraiBomb bomb = makeCaptured(config, 5);
        assert(bomb.throwBomb(P2BombSaraiThrowKind::Release, 0.0f));
        for (int i = 0; i < 200; ++i) {
            assert(bomb.update(kDelta, nullptr, nullptr, nullptr, nullptr));
            assert(bomb.phase() == P2BombSaraiBombPhase::InFlight);
        }
        assert(bomb.update(kDelta, nullptr, nullptr, nullptr, nullptr));
        assert(bomb.phase() == P2BombSaraiBombPhase::Despawned);
        assert(!bomb.hasBlast());
    }

    // Pool: capacity, one live bomb per carrier, clean exhaustion, slot reuse.
    {
        P2BombSaraiBombPool pool(2);
        P2BombSaraiBomb* first = pool.supply(1, { 0, 90, 0 }, config);
        P2BombSaraiBomb* second = pool.supply(2, { 0, 90, 0 }, config);
        assert(first && second && first != second);
        assert(pool.activeCount() == 2);
        assert(pool.supply(3, { 0, 90, 0 }, config) == nullptr); // exhausted, no partial state
        assert(pool.activeCount() == 2);
        assert(pool.supply(1, { 0, 90, 0 }, config) == nullptr); // duplicate live carrier
        // Detonate the first bomb, then its slot is reusable.
        assert(first->throwBomb(P2BombSaraiThrowKind::Death, 0.0f));
        Trace traceState;
        Carrier carrierState;
        runToBlast(*first, traceState, carrierState);
        P2BombSaraiBomb* third = pool.supply(3, { 0, 90, 0 }, config);
        assert(third == first);
        assert(third->phase() == P2BombSaraiBombPhase::Captured);
        assert(third->carrierToken() == 3);
        assert(pool.activeCount() == 2);
        // Invalid input never mutates the pool.
        assert(pool.supply(4, { std::numeric_limits<float>::quiet_NaN(), 0, 0 }, config) == nullptr);
        assert(pool.activeCount() == 2);
    }

    // Invalid config refuses capture instead of inventing parameters.
    {
        P2BombSaraiBomb bomb;
        P2BombSaraiBombConfig bad = config;
        bad.armLoopTicks = 0;
        bomb.reset(bad);
        assert(!bomb.capture(1, { 0, 90, 0 }));
        assert(bomb.phase() == P2BombSaraiBombPhase::Inactive);
        bad = config;
        bad.gravityPerTick = -1.0f;
        bomb.reset(bad);
        assert(!bomb.capture(1, { 0, 90, 0 }));
    }

    return 0;
}
