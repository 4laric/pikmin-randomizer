#include "pc_p2_cannon_stone.h"

#include <cassert>
#include <cmath>
#include <cstdint>
#include <limits>

namespace {
constexpr float kDelta = P2CannonStone::kSourceDelta;
constexpr float kPi = 3.14159265358979323846f;

P2CannonStoneConfig testConfig()
{
    P2CannonStoneConfig config;
    config.variant = P2CannonStoneVariant::Stone;
    config.moveSpeed = 250.0f;          // Stone general fp06 disc value
    config.searchRumbleSpeed = 100.0f;  // Rock proper fp01 disc value
    config.turnSpeed = 1.0f;            // fixture rate; host parm in production
    config.maxTurnAngle = 180.0f;       // fixture cap (degrees)
    config.attackDamage = 10.0f;        // Stone general mAttackDamage fixture
    config.sightRadius = 550.0f;
    config.collisionRadius = 40.0f;     // Rock root radius
    config.health = 99999.0f;           // Stone disc mHealth
    return config;
}

bool near(float actual, float expected, float epsilon = 0.001f)
{
    return std::fabs(actual - expected) <= epsilon;
}

struct StoneTrace {
    bool wall = false;
    bool useForce = false;
    int calls = 0;
    float lastRadius = 0.0f;
    P2CannonStoneVec3 forceVelocity{};
};

bool trace(void* opaque, const P2CannonStoneVec3& position, const P2CannonStoneVec3& velocity,
           float delta, float radius, P2CannonStoneTraceResult& result)
{
    StoneTrace& state = *static_cast<StoneTrace*>(opaque);
    ++state.calls;
    state.lastRadius = radius;
    result.position = { position.x + velocity.x * delta, position.y + velocity.y * delta,
                        position.z + velocity.z * delta };
    result.velocity = state.useForce ? state.forceVelocity : velocity;
    result.wall = state.wall;
    return true;
}

P2CannonStone makeStone(float faceDir, bool homing, std::uint64_t source = 0)
{
    P2CannonStone stone;
    stone.reset(testConfig());
    assert(stone.birth({ 0.0f, 50.0f, 0.0f }, faceDir, homing, source, 222));
    return stone;
}

void tick(P2CannonStone& stone, int count, P2CannonStoneTraceFn fn = nullptr,
          void* context = nullptr, const P2CannonStoneTarget& target = P2CannonStoneTarget{})
{
    for (int i = 0; i < count; ++i) {
        assert(stone.update(kDelta, target, fn, context));
    }
}

void testBirth()
{
    // mouthBirthPosition adds the source +25 y (Kabuto.cpp:276).
    const P2CannonStoneVec3 mouth = P2CannonStone::mouthBirthPosition({ 10.0f, 100.0f, -30.0f });
    assert(near(mouth.x, 10.0f) && near(mouth.y, 125.0f) && near(mouth.z, -30.0f));

    // getDirection(0) * moveSpeed = (0, 0, moveSpeed).
    const P2CannonStoneVec3 vel = P2CannonStone::initialVelocity(0.0f, 250.0f);
    assert(near(vel.x, 0.0f) && near(vel.y, 0.0f) && near(vel.z, 250.0f));

    P2CannonStone stone = makeStone(0.0f, false, 111);
    assert(stone.phase() == P2CannonStonePhase::Move);
    assert(stone.isAlive());
    assert(near(stone.scale(), P2CannonStone::kInitialScale));
    assert(near(stone.health(), 99999.0f));
    assert(near(stone.timer(), 0.0f));
    assert(near(stone.velocity().z, 250.0f));
    assert(near(stone.targetVelocity().z, 250.0f));
    assert(stone.sourceToken() == 111 && stone.selfToken() == 222);
    assert(!stone.homing());

    // A live Stone refuses a second birth; a bad config is refused outright.
    assert(!stone.birth({ 0.0f, 0.0f, 0.0f }, 0.0f, false, 0, 0));
    P2CannonStone bad;
    P2CannonStoneConfig invalid = testConfig();
    invalid.moveSpeed = std::numeric_limits<float>::quiet_NaN();
    bad.reset(invalid);
    assert(!bad.birth({ 0.0f, 0.0f, 0.0f }, 0.0f, false, 0, 0));
    assert(bad.phase() == P2CannonStonePhase::Inactive);
}

void testNonHomingMotion()
{
    P2CannonStone stone = makeStone(0.0f, false);
    StoneTrace state;
    tick(stone, 1, trace, &state);
    assert(state.calls == 1);
    assert(near(state.lastRadius, 40.0f));
    // Straight roll along +z, target velocity unchanged.
    assert(near(stone.position().z, 250.0f * kDelta));
    assert(near(stone.faceDir(), 0.0f));
    assert(near(stone.targetVelocity().z, 250.0f));

    // Scale ramps at 5/s from 0.0001 and clamps at 1.0 after 6 ticks.
    P2CannonStone scaleStone = makeStone(0.0f, false);
    StoneTrace scaleTrace;
    tick(scaleStone, 5, trace, &scaleTrace);
    assert(scaleStone.scale() < 1.0f);
    tick(scaleStone, 1, trace, &scaleTrace);
    assert(near(scaleStone.scale(), 1.0f));

    // Non-homing 0.01/0.99 smoothing uses the traced current velocity.
    P2CannonStone smoothed = makeStone(0.0f, false);
    StoneTrace smoothTrace;
    smoothTrace.useForce = true;
    smoothTrace.forceVelocity = { 100.0f, 0.0f, 0.0f };
    tick(smoothed, 1, trace, &smoothTrace);
    // Second tick: x = 0.01*100 + 0.99*0; z = 0.01*0 + 0.99*250.
    tick(smoothed, 1, trace, &smoothTrace);
    assert(near(smoothed.targetVelocity().x, 1.0f, 0.01f));
    assert(near(smoothed.targetVelocity().z, 247.5f, 0.01f));
}

void testHomingMotion()
{
    // Target due +x of a +z-facing Stone: face snaps toward +x.
    P2CannonStone stone = makeStone(0.0f, true);
    StoneTrace state;
    P2CannonStoneTarget target;
    target.hasTarget = true;
    target.position = { 100.0f, 50.0f, 0.0f };
    assert(stone.update(kDelta, target, trace, &state));
    assert(near(stone.faceDir(), kPi / 2.0f, 0.02f));
    assert(near(stone.targetVelocity().x, 100.0f, 0.5f));
    assert(near(stone.targetVelocity().z, 0.0f, 0.5f));

    // Max turn angle clamps the per-update turn (30 deg here).
    P2CannonStone clamped = makeStone(0.0f, true);
    P2CannonStoneConfig cfg = testConfig();
    cfg.turnSpeed = 1000.0f;
    cfg.maxTurnAngle = 30.0f;
    clamped.reset(cfg);
    assert(clamped.birth({ 0.0f, 0.0f, 0.0f }, 0.0f, true, 0, 1));
    assert(clamped.update(kDelta, target, trace, &state));
    assert(near(clamped.faceDir(), 30.0f * kPi / 180.0f, 0.001f));

    // Target loss keeps the current heading; a NaN target is treated as none.
    P2CannonStone lost = makeStone(0.0f, true);
    P2CannonStoneTarget none;
    assert(lost.update(kDelta, none, trace, &state));
    assert(near(lost.faceDir(), 0.0f));
    P2CannonStoneTarget nan;
    nan.hasTarget = true;
    nan.position = { std::numeric_limits<float>::quiet_NaN(), 0.0f, 0.0f };
    assert(lost.update(kDelta, nan, trace, &state));
    assert(near(lost.faceDir(), 0.0f));
}

void testContact()
{
    // Grounded Navi/Piki -> InteractPress attributed to the source enemy.
    P2CannonStone pressed = makeStone(0.0f, false, 111);
    P2CannonStoneContactResult r =
        pressed.contact(P2CannonStoneContactKind::NaviPiki, true, false, 900);
    assert(r.strikeEmitted && !r.healthZeroed && !r.ignored);
    assert(r.strike.kind == P2CannonStoneStrikeKind::Press);
    assert(near(r.strike.damage, 10.0f));
    assert(r.strike.attributedToSource && r.strike.attributedToken == 111);
    assert(r.strike.targetToken == 900);
    assert(pressed.phase() == P2CannonStonePhase::Move);

    // Airborne Navi/Piki receive nothing and the Stone does not self-destruct.
    P2CannonStone airborne = makeStone(0.0f, false, 111);
    P2CannonStoneContactResult ra =
        airborne.contact(P2CannonStoneContactKind::NaviPiki, false, false, 900);
    assert(!ra.strikeEmitted && !ra.healthZeroed);

    // No source enemy -> Press attributes to the Stone itself.
    P2CannonStone self = makeStone(0.0f, false, 0);
    P2CannonStoneContactResult rs =
        self.contact(P2CannonStoneContactKind::NaviPiki, true, false, 900);
    assert(rs.strikeEmitted && !rs.strike.attributedToSource);
    assert(rs.strike.attributedToken == self.selfToken());

    // Teki -> fixed 250 InteractAttack, health forced to zero.
    P2CannonStone teki = makeStone(0.0f, false, 111);
    P2CannonStoneContactResult rt = teki.contact(P2CannonStoneContactKind::Teki, true, false, 42);
    assert(rt.strikeEmitted && rt.healthZeroed);
    assert(rt.strike.kind == P2CannonStoneStrikeKind::Attack);
    assert(near(rt.strike.damage, P2CannonStone::kTekiAttackDamage));
    assert(rt.strike.attributedToken == teki.selfToken());
    assert(teki.hasHealthZeroed());

    // Any other non-Navi/Piki contact zeroes health without a strike.
    P2CannonStone other = makeStone(0.0f, false, 0);
    P2CannonStoneContactResult ro = other.contact(P2CannonStoneContactKind::Other, true, false, 7);
    assert(!ro.strikeEmitted && ro.healthZeroed);

    // Rock-vs-Rock mutual suppression only for the Rock variant.
    P2CannonStone rock;
    P2CannonStoneConfig rockCfg = testConfig();
    rockCfg.variant = P2CannonStoneVariant::Rock;
    rock.reset(rockCfg);
    assert(rock.birth({ 0.0f, 0.0f, 0.0f }, 0.0f, false, 0, 1));
    P2CannonStoneContactResult rr = rock.contact(P2CannonStoneContactKind::Teki, true, true, 5);
    assert(rr.selfCollisionSuppressed && rr.healthZeroed);
    P2CannonStone stoneRock = makeStone(0.0f, false, 0);
    P2CannonStoneContactResult sr = stoneRock.contact(P2CannonStoneContactKind::Teki, true, true, 5);
    assert(!sr.selfCollisionSuppressed);
}

void testAtariGrace()
{
    P2CannonStone stone = makeStone(0.0f, false, 111);
    // Source-enemy contact within the first second is ignored.
    P2CannonStoneContactResult first =
        stone.contact(P2CannonStoneContactKind::NaviPiki, true, false, 111);
    assert(first.ignored && !first.strikeEmitted && !first.healthZeroed);
    assert(stone.shouldIgnoreAtari(111));
    assert(!stone.shouldIgnoreAtari(222));

    tick(stone, 31); // timer > 1.0 s
    P2CannonStoneContactResult later =
        stone.contact(P2CannonStoneContactKind::NaviPiki, true, false, 111);
    assert(!later.ignored && later.strikeEmitted);
    assert(!stone.shouldIgnoreAtari(111));
}

void testInterruption()
{
    // Wall reported by the trace interrupts Move (wallCallback).
    P2CannonStone wall = makeStone(0.0f, false);
    StoneTrace wallTrace;
    wallTrace.wall = true;
    assert(wall.update(kDelta, P2CannonStoneTarget{}, trace, &wallTrace));
    assert(wall.phase() == P2CannonStonePhase::Dead);
    assert(near(wall.targetVelocity().z, 0.0f));

    // Explicit wall / hipdrop notifications.
    P2CannonStone wall2 = makeStone(0.0f, false);
    assert(wall2.notifyWallContact());
    assert(wall2.phase() == P2CannonStonePhase::Dead);
    P2CannonStone hip = makeStone(0.0f, false);
    assert(!hip.notifyHipdrop(true)); // bittered: ignored
    assert(hip.phase() == P2CannonStonePhase::Move);
    assert(hip.notifyHipdrop(false));
    assert(hip.phase() == P2CannonStonePhase::Dead);

    // Contact-driven health zero is only consumed by the next Move update.
    P2CannonStone struck = makeStone(0.0f, false, 0);
    struck.contact(P2CannonStoneContactKind::Teki, true, false, 3);
    assert(struck.phase() == P2CannonStonePhase::Move);
    assert(struck.update(kDelta, P2CannonStoneTarget{}));
    assert(struck.phase() == P2CannonStonePhase::Dead);
}

void testDestructionAndTeardown()
{
    // 15 s timeout (RockState.cpp:238). 450 ticks = 15 s; allow float slack.
    P2CannonStone stone = makeStone(0.0f, false);
    tick(stone, 449);
    assert(stone.phase() == P2CannonStonePhase::Move);
    int extra = 0;
    while (stone.phase() == P2CannonStonePhase::Move && extra < 5) {
        stone.update(kDelta, P2CannonStoneTarget{});
        ++extra;
    }
    assert(stone.phase() == P2CannonStonePhase::Dead);

    // finishDeath is only valid from Dead and requests kill exactly once.
    assert(!makeStone(0.0f, false).finishDeath());
    assert(stone.finishDeath());
    assert(stone.phase() == P2CannonStonePhase::Killed);
    assert(!stone.finishDeath());

    // Killed is terminal: no update, no contact, no interruption.
    assert(!stone.update(kDelta, P2CannonStoneTarget{}));
    P2CannonStoneContactResult r =
        stone.contact(P2CannonStoneContactKind::NaviPiki, true, false, 4);
    assert(!r.strikeEmitted && !r.healthZeroed);
    assert(!stone.notifyWallContact());
}

void testInvalidDelta()
{
    P2CannonStone stone = makeStone(0.0f, false);
    const float savedFaceDir = stone.faceDir();
    assert(!stone.update(1.0f / 60.0f, P2CannonStoneTarget{}));
    assert(!stone.update(std::numeric_limits<float>::quiet_NaN(), P2CannonStoneTarget{}));
    assert(stone.phase() == P2CannonStonePhase::Move);
    assert(near(stone.timer(), 0.0f) && near(stone.faceDir(), savedFaceDir));
}

void testPool()
{
    P2CannonStonePool pool(2);
    assert(pool.capacity() == 2);
    P2CannonStone* a = pool.spawn({ 0.0f, 25.0f, 0.0f }, 0.0f, false, 100, 1, testConfig());
    P2CannonStone* b = pool.spawn({ 0.0f, 25.0f, 0.0f }, 0.0f, false, 100, 2, testConfig());
    assert(a && b && a != b);
    assert(pool.activeCount() == 2);

    // Exhaustion returns nullptr with no partial state.
    P2CannonStone* c = pool.spawn({ 0.0f, 25.0f, 0.0f }, 0.0f, false, 100, 3, testConfig());
    assert(c == nullptr);
    assert(pool.activeCount() == 2);

    // Invalid config is refused.
    P2CannonStoneConfig invalid = testConfig();
    invalid.collisionRadius = 0.0f;
    P2CannonStonePool badPool(1);
    assert(badPool.spawn({ 0.0f, 0.0f, 0.0f }, 0.0f, false, 0, 1, invalid) == nullptr);

    // Kill A and reuse its slot.
    a->contact(P2CannonStoneContactKind::Teki, true, false, 9);
    a->update(kDelta, P2CannonStoneTarget{});
    assert(a->finishDeath());
    assert(pool.activeCount() == 1);
    P2CannonStone* reused = pool.spawn({ 0.0f, 25.0f, 0.0f }, 0.0f, false, 100, 4, testConfig());
    assert(reused != nullptr);
    assert(pool.activeCount() == 2);
}
} // namespace

int main()
{
    testBirth();
    testNonHomingMotion();
    testHomingMotion();
    testContact();
    testAtariGrace();
    testInterruption();
    testDestructionAndTeardown();
    testInvalidDelta();
    testPool();
    return 0;
}
