#include "pc_p2_rock_hazard.h"

#include <cassert>
#include <cmath>
#include <cstdint>
#include <limits>

namespace {
constexpr float kDelta = P2RockHazard::kSourceDelta;

P2RockHazardConfig testConfig()
{
    P2RockHazardConfig config;
    config.fallSpeed = 500.0f;      // fixture host parm (mSearchDistance)
    config.fallOffset = 100.0f;     // fixture host parm (mSearchHeight)
    config.scaleUpRate = 5.0f;      // fixture host parm (mSearchAngle)
    config.sightRadius = 350.0f;    // general mSightRadius fixture
    config.attackDamage = 10.0f;    // general mAttackDamage fixture
    config.collisionRadius = 40.0f; // host fall trace radius
    config.health = 100.0f;         // general mHealth fixture
    return config;
}

P2RockHazardConfig configWith(float scaleUpRate)
{
    P2RockHazardConfig config = testConfig();
    config.scaleUpRate = scaleUpRate;
    return config;
}

bool near(float actual, float expected, float epsilon = 0.001f)
{
    return std::fabs(actual - expected) <= epsilon;
}

P2RockHazardInit makeInit(bool dropGroupNone, float y = 200.0f)
{
    P2RockHazardInit init;
    init.position = { 0.0f, y, 0.0f };
    init.dropGroupNone = dropGroupNone;
    init.timedAppear = false;
    init.initialTimer = 0.0f;
    init.sourceToken = 0;
    init.selfToken = 0;
    return init;
}

// Wait -> Appear by detection (timedAppear == false).
P2RockHazard makeWaitRock()
{
    P2RockHazard rock;
    rock.reset(testConfig());
    assert(rock.onInit(makeInit(true)));
    assert(rock.phase() == P2RockHazardPhase::Wait);
    P2RockHazardDetection detection;
    detection.olimarInSight = true;
    assert(rock.update(kDelta, detection));
    assert(rock.phase() == P2RockHazardPhase::Appear);
    return rock;
}

// Appear -> Fall by the fallRockScaleUp ramp.
P2RockHazard makeFallRock()
{
    P2RockHazard rock = makeWaitRock();
    for (int i = 0; i < 60 && rock.phase() == P2RockHazardPhase::Appear; ++i) {
        assert(rock.update(kDelta, P2RockHazardDetection{}));
    }
    assert(rock.phase() == P2RockHazardPhase::Fall);
    return rock;
}

// Drop-group onInit -> DropWait -> Fall.
P2RockHazard makeDropFallRock(std::uint64_t source = 0)
{
    P2RockHazard rock;
    rock.reset(testConfig());
    P2RockHazardInit init = makeInit(false);
    init.sourceToken = source;
    init.selfToken = 77;
    assert(rock.onInit(init));
    assert(rock.phase() == P2RockHazardPhase::DropWait);
    assert(rock.update(kDelta, P2RockHazardDetection{}));
    assert(rock.phase() == P2RockHazardPhase::Fall);
    return rock;
}

struct RockTrace {
    bool floor = false;
    bool colliding = false;
    bool useForce = false;
    int calls = 0;
    float lastRadius = 0.0f;
    P2RockHazardVec3 forceVelocity{};
};

bool trace(void* opaque, const P2RockHazardVec3& position, const P2RockHazardVec3& velocity,
           float delta, float radius, P2RockHazardTraceResult& result)
{
    RockTrace& state = *static_cast<RockTrace*>(opaque);
    ++state.calls;
    state.lastRadius = radius;
    result.position = { position.x + velocity.x * delta, position.y + velocity.y * delta,
                        position.z + velocity.z * delta };
    result.velocity = state.useForce ? state.forceVelocity : velocity;
    result.floorTriangle = state.floor;
    result.colliding = state.colliding;
    return true;
}

void testOnInitWaitBranch()
{
    P2RockHazard rock;
    rock.reset(testConfig());
    P2RockHazardInit init = makeInit(true);
    init.selfToken = 5;
    assert(rock.onInit(init));

    assert(rock.phase() == P2RockHazardPhase::Wait);
    assert(rock.isAlive());
    assert(near(rock.scale(), P2RockHazard::kInitialHiddenScale));
    assert(near(rock.timer(), 0.0f));
    // StateWait::init (RockState.cpp:30-42) + shadow del (Rock.cpp:86).
    assert(!rock.atari());
    assert(rock.untargetable());
    assert(rock.hardConstrained());
    assert(!rock.animating());
    assert(rock.modelHidden());
    assert(rock.motion() == P2RockHazardMotion::Run);
    assert(rock.motionStopped());
    assert(!rock.shadow());
    assert(rock.animationCullingOff()); // doAnimationCullingOff (Rock.cpp:80)
    assert(rock.cullable());
    assert(near(rock.targetVelocity().x, 0.0f) && near(rock.targetVelocity().y, 0.0f));
    assert(rock.selfToken() == 5);

    // A live Rock refuses a second init; the state is untouched.
    assert(!rock.onInit(init));
    assert(rock.phase() == P2RockHazardPhase::Wait);
}

void testOnInitDropWaitBranch()
{
    P2RockHazard rock;
    rock.reset(testConfig());
    P2RockHazardInit init = makeInit(false);
    init.timedAppear = true;
    init.initialTimer = 1.25f;
    init.sourceToken = 9;
    assert(rock.onInit(init));

    assert(rock.phase() == P2RockHazardPhase::DropWait);
    assert(rock.isAlive());
    assert(near(rock.scale(), 1.0f)); // no hidden scale for a drop-group Rock
    assert(rock.atari());
    assert(!rock.untargetable());
    assert(!rock.hardConstrained());
    assert(rock.animating());
    assert(!rock.modelHidden());
    assert(rock.motion() == P2RockHazardMotion::Run);
    assert(!rock.motionStopped());
    // Rock.cpp:73-76: timedAppear disables culling and seeds mTimer even on the
    // drop-group branch.
    assert(!rock.cullable());
    assert(near(rock.timer(), 1.25f));
    assert(!rock.animationCullingOff());
    assert(!rock.shadow());
    assert(rock.sourceToken() == 9);
}

void testOnInitRejectsInvalidInput()
{
    P2RockHazard rock;
    rock.reset(testConfig());
    P2RockHazardInit bad = makeInit(true);
    bad.position.x = std::numeric_limits<float>::quiet_NaN();
    assert(!rock.onInit(bad));
    assert(rock.phase() == P2RockHazardPhase::Inactive);

    rock.reset(configWith(0.0f)); // scaleUpRate 0 would stall Appear forever
    assert(!rock.onInit(makeInit(true)));
    assert(rock.phase() == P2RockHazardPhase::Inactive);

    rock.reset(testConfig());
    P2RockHazardInit badTimer = makeInit(true);
    badTimer.initialTimer = std::numeric_limits<float>::infinity();
    assert(!rock.onInit(badTimer));
    assert(rock.phase() == P2RockHazardPhase::Inactive);
}

void testWaitDetection()
{
    // isThereOlimar -> Appear.
    P2RockHazard olimar;
    olimar.reset(testConfig());
    assert(olimar.onInit(makeInit(true)));
    P2RockHazardDetection detection;
    detection.pikminInSight = true;
    assert(olimar.update(kDelta, detection));
    assert(olimar.phase() == P2RockHazardPhase::Appear);
    // StateWait::cleanup (RockState.cpp:77-83) then StateAppear::init, which
    // re-enables EB_ModelHidden (RockState.cpp:96).
    assert(!olimar.hardConstrained());
    assert(olimar.animating());
    assert(olimar.modelHidden());

    // No target keeps Wait.
    P2RockHazard idle;
    idle.reset(testConfig());
    assert(idle.onInit(makeInit(true)));
    assert(idle.update(kDelta, P2RockHazardDetection{}));
    assert(idle.phase() == P2RockHazardPhase::Wait);
}

void testWaitDuration()
{
    P2RockHazard rock;
    rock.reset(testConfig());
    P2RockHazardInit init = makeInit(true);
    init.timedAppear = true;
    init.initialTimer = 1.4f; // randWeightFloat(1.5) host value
    assert(rock.onInit(init));

    int ticks = 0;
    while (rock.phase() == P2RockHazardPhase::Wait && ticks < 60) {
        assert(rock.update(kDelta, P2RockHazardDetection{}));
        ++ticks;
    }
    assert(rock.phase() == P2RockHazardPhase::Appear);
    assert(rock.timer() > P2RockHazard::kAppearTimerSeconds);
}

void testAppearScaleUp()
{
    // Detection enters Appear and adds mFallOffset to position.y
    // (RockState.cpp:91-94).
    P2RockHazard rock = makeWaitRock();
    assert(near(rock.position().y, 300.0f));
    assert(rock.modelHidden());
    assert(!rock.cullable());
    assert(!rock.cullSound());
    assert(rock.shadow() && rock.shadowForcedVisible());
    assert(rock.motion() == P2RockHazardMotion::Run);

    // fallRockScaleUp ramps 0.0001 -> 1.0 at scaleUpRate per source second
    // (Rock.cpp:310-327) and then transits to Fall.
    int ticks = 0;
    while (rock.phase() == P2RockHazardPhase::Appear && ticks < 60) {
        assert(rock.update(kDelta, P2RockHazardDetection{}));
        ++ticks;
    }
    assert(rock.phase() == P2RockHazardPhase::Fall);
    assert(near(rock.scale(), 1.0f));
    // StateAppear::cleanup (RockState.cpp:125-131).
    assert(rock.atari());
    assert(!rock.untargetable());
    assert(!rock.modelHidden());
}

void testDropWaitFall()
{
    P2RockHazard rock = makeDropFallRock();
    // StateFall::init (RockState.cpp:170-176).
    assert(near(rock.velocity().x, 0.0f));
    assert(near(rock.velocity().y, -500.0f));
    assert(near(rock.velocity().z, 0.0f));
    assert(rock.fallEffectActive());
    // StateDropWait::cleanup (RockState.cpp:156-164).
    assert(!rock.cullable());
    assert(!rock.cullSound());
    assert(rock.shadow() && rock.shadowForcedVisible());
}

void testFallMotionAndDeath()
{
    // No trace: the source velocity integrates straight down.
    P2RockHazard freeFall = makeFallRock();
    const float startY = freeFall.position().y;
    assert(freeFall.update(kDelta, P2RockHazardDetection{}));
    assert(near(freeFall.position().y, startY - 500.0f * kDelta, 0.01f));
    assert(freeFall.phase() == P2RockHazardPhase::Fall);

    // Trace reports a floor triangle -> Dead (RockState.cpp:184-185).
    P2RockHazard floorRock = makeFallRock();
    RockTrace floorTrace;
    floorTrace.floor = true;
    assert(floorRock.update(kDelta, P2RockHazardDetection{}, trace, &floorTrace));
    assert(floorTrace.calls == 1);
    assert(near(floorTrace.lastRadius, 40.0f));
    assert(floorRock.phase() == P2RockHazardPhase::Dead);
    assert(!floorRock.fallEffectActive());
    assert(!floorRock.shadowForcedVisible());
    assert(!floorRock.shadow());
    assert(floorRock.deadEffectCreated());
    assert(floorRock.motion() == P2RockHazardMotion::Dead);

    // Trace reports EB_Colliding -> Dead.
    P2RockHazard hitRock = makeFallRock();
    RockTrace hitTrace;
    hitTrace.colliding = true;
    assert(hitRock.update(kDelta, P2RockHazardDetection{}, trace, &hitTrace));
    assert(hitRock.phase() == P2RockHazardPhase::Dead);

    // Trace position/velocity are absorbed.
    P2RockHazard traced = makeFallRock();
    RockTrace forceTrace;
    forceTrace.useForce = true;
    forceTrace.forceVelocity = { 1.0f, -2.0f, 3.0f };
    assert(traced.update(kDelta, P2RockHazardDetection{}, trace, &forceTrace));
    assert(near(traced.velocity().x, 1.0f) && near(traced.velocity().y, -2.0f)
           && near(traced.velocity().z, 3.0f));
}

void testContact()
{
    // Grounded Navi/Piki -> InteractPress attributed to the source enemy.
    P2RockHazard pressed = makeDropFallRock(111);
    P2RockHazardContactResult r =
        pressed.contact(P2RockHazardContactKind::NaviPiki, true, false, 900);
    assert(r.strikeEmitted && !r.healthZeroed && !r.ignored);
    assert(r.strike.kind == P2RockHazardStrikeKind::Press);
    assert(near(r.strike.damage, 10.0f));
    assert(r.strike.attributedToSource && r.strike.attributedToken == 111);
    assert(r.strike.targetToken == 900);

    // No source enemy -> Press attributes to the Rock itself.
    P2RockHazard self = makeDropFallRock(0);
    P2RockHazardContactResult rs =
        self.contact(P2RockHazardContactKind::NaviPiki, true, false, 900);
    assert(rs.strikeEmitted && !rs.strike.attributedToSource);
    assert(rs.strike.attributedToken == self.selfToken());

    // Airborne Navi/Piki receive nothing and the Rock does not self-destruct.
    P2RockHazard airborne = makeDropFallRock(111);
    P2RockHazardContactResult ra =
        airborne.contact(P2RockHazardContactKind::NaviPiki, false, false, 900);
    assert(!ra.strikeEmitted && !ra.healthZeroed);

    // Teki -> fixed 250 InteractAttack, health forced to zero.
    P2RockHazard teki = makeDropFallRock(111);
    P2RockHazardContactResult rt = teki.contact(P2RockHazardContactKind::Teki, true, false, 42);
    assert(rt.strikeEmitted && rt.healthZeroed);
    assert(rt.strike.kind == P2RockHazardStrikeKind::Attack);
    assert(near(rt.strike.damage, P2RockHazard::kTekiAttackDamage));
    assert(rt.strike.attributedToken == teki.selfToken());
    assert(!rt.selfCollisionSuppressed);

    // Any other non-Navi/Piki contact zeroes health without a strike.
    P2RockHazard other = makeDropFallRock(0);
    P2RockHazardContactResult ro = other.contact(P2RockHazardContactKind::Other, true, false, 7);
    assert(!ro.strikeEmitted && ro.healthZeroed);

    // Rock-vs-Rock mutual suppression: no EB_Colliding, so the Fall state
    // survives an update (Rock.cpp:225-227).
    P2RockHazard rockRock = makeDropFallRock(0);
    P2RockHazardContactResult rr = rockRock.contact(P2RockHazardContactKind::Teki, true, true, 5);
    assert(rr.selfCollisionSuppressed && rr.healthZeroed);
    assert(!rockRock.colliding());
    assert(rockRock.update(kDelta, P2RockHazardDetection{}));
    assert(rockRock.phase() == P2RockHazardPhase::Fall);

    // A non-suppressed contact sets EB_Colliding, consumed by the next Fall
    // update into Dead (RockState.cpp:186-187).
    P2RockHazard collided = makeDropFallRock(0);
    collided.contact(P2RockHazardContactKind::Teki, true, false, 5);
    assert(collided.colliding());
    assert(collided.update(kDelta, P2RockHazardDetection{}));
    assert(collided.phase() == P2RockHazardPhase::Dead);
}

void testAtariGateAndGrace()
{
    // Wait/Appear have atari off: no contact is processed (RockState.cpp:33).
    P2RockHazard waiting;
    waiting.reset(testConfig());
    P2RockHazardInit init = makeInit(true);
    init.sourceToken = 111;
    assert(waiting.onInit(init));
    P2RockHazardContactResult rw =
        waiting.contact(P2RockHazardContactKind::NaviPiki, true, false, 111);
    assert(!rw.strikeEmitted && !rw.healthZeroed && !rw.ignored);

    // A drop-group Fall keeps mTimer at 0, so the source enemy stays inside the
    // 1 s grace (Rock.cpp:298-304).
    P2RockHazard dropGrace = makeDropFallRock(111);
    assert(dropGrace.shouldIgnoreAtari(111));
    P2RockHazardContactResult rg =
        dropGrace.contact(P2RockHazardContactKind::NaviPiki, true, false, 111);
    assert(rg.ignored && !rg.strikeEmitted && !rg.healthZeroed);
    // A different creature is never ignored.
    P2RockHazardContactResult ro =
        dropGrace.contact(P2RockHazardContactKind::NaviPiki, true, false, 222);
    assert(!ro.ignored && ro.strikeEmitted);

    // A timed rock's Wait timer runs past 1.0 s before Fall, so the grace has
    // expired by the time it can be contacted.
    P2RockHazard timed;
    timed.reset(testConfig());
    P2RockHazardInit timedInit = makeInit(true);
    timedInit.timedAppear = true;
    timedInit.initialTimer = 1.4f;
    timedInit.sourceToken = 111;
    assert(timed.onInit(timedInit));
    for (int i = 0; i < 60 && timed.phase() == P2RockHazardPhase::Wait; ++i) {
        assert(timed.update(kDelta, P2RockHazardDetection{}));
    }
    assert(timed.phase() == P2RockHazardPhase::Appear);
    assert(!timed.shouldIgnoreAtari(111));
}

void testWallHipdropNoOp()
{
    // wallCallback/hipdropCallBack are Move-gated; the falling Rock has no Move
    // state (Rock.cpp:192,246).
    P2RockHazard rock = makeFallRock();
    assert(!rock.notifyWallContact());
    assert(!rock.notifyHipdrop(false));
    assert(!rock.notifyHipdrop(true));
    assert(rock.phase() == P2RockHazardPhase::Fall);
}

void testDeathAndTeardown()
{
    // finishDeath is only valid from Dead and requests kill exactly once.
    assert(!makeFallRock().finishDeath());
    P2RockHazard dead = makeFallRock();
    RockTrace floorTrace;
    floorTrace.floor = true;
    assert(dead.update(kDelta, P2RockHazardDetection{}, trace, &floorTrace));
    assert(dead.phase() == P2RockHazardPhase::Dead);
    assert(dead.finishDeath());
    assert(dead.phase() == P2RockHazardPhase::Killed);
    assert(!dead.finishDeath());
    assert(!dead.isAlive());

    // Killed is terminal: no update.
    assert(!dead.update(kDelta, P2RockHazardDetection{}));
}

void testInvalidDelta()
{
    P2RockHazard rock = makeWaitRock();
    const P2RockHazardPhase saved = rock.phase();
    const float savedScale = rock.scale();
    assert(!rock.update(1.0f / 60.0f, P2RockHazardDetection{}));
    assert(!rock.update(std::numeric_limits<float>::quiet_NaN(), P2RockHazardDetection{}));
    assert(rock.phase() == saved);
    assert(near(rock.scale(), savedScale));
}

void testPool()
{
    P2RockHazardPool pool(2);
    assert(pool.capacity() == 2);
    P2RockHazard* a = pool.spawn(makeInit(false), testConfig());
    P2RockHazard* b = pool.spawn(makeInit(true), testConfig());
    assert(a && b && a != b);
    assert(pool.activeCount() == 2);

    // Exhaustion returns nullptr with no partial state.
    assert(pool.spawn(makeInit(true), testConfig()) == nullptr);
    assert(pool.activeCount() == 2);

    // Invalid config is refused.
    P2RockHazardPool badPool(1);
    assert(badPool.spawn(makeInit(true), configWith(0.0f)) == nullptr);
    assert(badPool.activeCount() == 0);

    // Advance A to Fall, zero its health and kill it, then reuse its slot.
    assert(a->update(kDelta, P2RockHazardDetection{}));
    assert(a->phase() == P2RockHazardPhase::Fall);
    a->contact(P2RockHazardContactKind::Other, true, false, 1);
    assert(a->update(kDelta, P2RockHazardDetection{}));
    assert(a->phase() == P2RockHazardPhase::Dead);
    assert(a->finishDeath());
    assert(pool.activeCount() == 1);
    P2RockHazard* reused = pool.spawn(makeInit(true), testConfig());
    assert(reused != nullptr);
    assert(pool.activeCount() == 2);
}
} // namespace

int main()
{
    testOnInitWaitBranch();
    testOnInitDropWaitBranch();
    testOnInitRejectsInvalidInput();
    testWaitDetection();
    testWaitDuration();
    testAppearScaleUp();
    testDropWaitFall();
    testFallMotionAndDeath();
    testContact();
    testAtariGateAndGrace();
    testWallHipdropNoOp();
    testDeathAndTeardown();
    testInvalidDelta();
    testPool();
    return 0;
}
