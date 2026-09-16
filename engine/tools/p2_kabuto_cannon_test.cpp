#include "pc_p2_kabuto_cannon.h"

#include <cassert>
#include <cmath>
#include <limits>

namespace {
constexpr float kPi = 3.14159265358979323846f;

P2KabutoCannonConfig testConfig()
{
    P2KabutoCannonConfig config;
    config.maxAttackAngle = 30.0f; // fixture general mMaxAttackAngle
    config.health = 850.0f;        // Kabuto disc life fp00
    return config;
}

bool near(float actual, float expected, float epsilon = 0.001f)
{
    return std::fabs(actual - expected) <= epsilon;
}

P2KabutoHostState liveHost()
{
    P2KabutoHostState host;
    host.health = 850.0f;
    return host;
}

P2KabutoCannon make(P2KabutoSpecies species, P2KabutoPhase start = P2KabutoPhase::Wait)
{
    P2KabutoCannon cannon;
    cannon.reset(testConfig(), species);
    assert(cannon.start());
    if (start == P2KabutoPhase::Turn) {
        // walk there through the event stream
        P2KabutoHostState host = liveHost();
        host.targetPresent = true;
        assert(cannon.onEvent(P2KabutoEvent::End, host) == P2KabutoAction::ToTurn);
    }
    return cannon;
}

void testStartAndSpecies()
{
    P2KabutoCannon cannon;
    cannon.reset(testConfig(), P2KabutoSpecies::Kabuto);
    assert(cannon.phase() == P2KabutoPhase::Inactive);
    assert(cannon.start());
    assert(cannon.phase() == P2KabutoPhase::Wait);
    assert(cannon.isAlive());
    assert(!cannon.start()); // already started
    assert(cannon.species() == P2KabutoSpecies::Kabuto);

    P2KabutoCannon bad;
    P2KabutoCannonConfig invalid = testConfig();
    invalid.health = 0.0f;
    bad.reset(invalid, P2KabutoSpecies::Kabuto);
    assert(!bad.start());
    P2KabutoCannon bad2;
    P2KabutoCannonConfig invalid2 = testConfig();
    invalid2.maxAttackAngle = std::numeric_limits<float>::quiet_NaN();
    bad2.reset(invalid2, P2KabutoSpecies::Kabuto);
    assert(!bad2.start());
}

void testFireAndHoming()
{
    // Kabuto is non-homing; the Stone birth adds the +25 y mouth offset.
    P2KabutoCannon kabuto = make(P2KabutoSpecies::Kabuto);
    P2KabutoHostState host = liveHost();
    assert(kabuto.beginAttack());
    assert(kabuto.phase() == P2KabutoPhase::Attack);
    assert(kabuto.onEvent(P2KabutoEvent::Key2, host) == P2KabutoAction::FireStone);
    assert(kabuto.hasPendingBirth());
    P2KabutoStoneBirth birth;
    assert(kabuto.takeBirth({ 10.0f, 40.0f, -5.0f }, 1.25f, birth));
    assert(birth.valid && !birth.homing);
    assert(near(birth.mouthPosition.x, 10.0f) && near(birth.mouthPosition.y, 65.0f)
           && near(birth.mouthPosition.z, -5.0f));
    assert(near(birth.faceDir, 1.25f));
    assert(!kabuto.hasPendingBirth());
    assert(!kabuto.takeBirth({ 0, 0, 0 }, 0.0f, birth)); // consumed

    // Rkabuto homing only (Kabuto.cpp:285-287).
    P2KabutoCannon red = make(P2KabutoSpecies::Rkabuto);
    assert(red.beginAttack());
    assert(red.onEvent(P2KabutoEvent::Key2, host) == P2KabutoAction::FireStone);
    P2KabutoStoneBirth redBirth;
    assert(red.takeBirth({ 0, 0, 0 }, 0.0f, redBirth));
    assert(redBirth.homing);

    // Fkabuto fires the same Stone, still non-homing.
    P2KabutoCannon fix = make(P2KabutoSpecies::Fkabuto);
    assert(fix.beginFixAttack());
    assert(fix.onEvent(P2KabutoEvent::Key2, host) == P2KabutoAction::FireStone);
    P2KabutoStoneBirth fixBirth;
    assert(fix.takeBirth({ 1, 2, 3 }, 0.5f, fixBirth));
    assert(fixBirth.valid && !fixBirth.homing);

    // Invalid mouth/face input is refused and the pending fire is retained.
    P2KabutoCannon guard = make(P2KabutoSpecies::Kabuto);
    assert(guard.beginAttack());
    guard.onEvent(P2KabutoEvent::Key2, host);
    P2KabutoStoneBirth bad;
    assert(!guard.takeBirth({ 0, 0, 0 }, std::numeric_limits<float>::quiet_NaN(), bad));
    assert(guard.hasPendingBirth());
    assert(!guard.takeBirth({ std::numeric_limits<float>::quiet_NaN(), 0, 0 }, 0.0f, bad));
    assert(guard.hasPendingBirth());
}

void testWaitTurnTransitions()
{
    P2KabutoCannon wait = make(P2KabutoSpecies::Kabuto);
    P2KabutoHostState host = liveHost();

    // Wait END with neither condition keeps waiting.
    assert(wait.onEvent(P2KabutoEvent::End, host) == P2KabutoAction::None);
    assert(wait.phase() == P2KabutoPhase::Wait);

    // Wait END with flick request -> Flick.
    host.flickRequested = true;
    assert(wait.onEvent(P2KabutoEvent::End, host) == P2KabutoAction::ToFlick);
    assert(wait.phase() == P2KabutoPhase::Flick);
    host.flickRequested = false;

    // Flick END with a target -> Turn, without -> Wait.
    host.targetPresent = true;
    assert(wait.onEvent(P2KabutoEvent::End, host) == P2KabutoAction::ToTurn);
    assert(wait.phase() == P2KabutoPhase::Turn);

    // Turn END: target but not attackable -> stay Turn.
    assert(wait.onEvent(P2KabutoEvent::End, host) == P2KabutoAction::None);
    assert(wait.phase() == P2KabutoPhase::Turn);

    // Turn END: attackable -> Attack.
    host.targetAttackable = true;
    assert(wait.onEvent(P2KabutoEvent::End, host) == P2KabutoAction::ToAttack);
    assert(wait.phase() == P2KabutoPhase::Attack);

    P2KabutoCannon noTarget = make(P2KabutoSpecies::Kabuto);
    P2KabutoHostState none = liveHost();
    none.targetPresent = false;
    assert(noTarget.onEvent(P2KabutoEvent::End, none) == P2KabutoAction::None);
    assert(noTarget.phase() == P2KabutoPhase::Wait);
}

void testAttackEnd()
{
    // Attack END: flick wins, then target, else Wait.
    P2KabutoCannon flick = make(P2KabutoSpecies::Kabuto);
    assert(flick.beginAttack());
    P2KabutoHostState host = liveHost();
    host.flickRequested = true;
    assert(flick.onEvent(P2KabutoEvent::End, host) == P2KabutoAction::ToFlick);

    P2KabutoCannon target = make(P2KabutoSpecies::Kabuto);
    assert(target.beginAttack());
    host.flickRequested = false;
    host.targetPresent = true;
    assert(target.onEvent(P2KabutoEvent::End, host) == P2KabutoAction::ToTurn);

    P2KabutoCannon idle = make(P2KabutoSpecies::Kabuto);
    assert(idle.beginAttack());
    host.targetPresent = false;
    assert(idle.onEvent(P2KabutoEvent::End, host) == P2KabutoAction::ToWait);
    assert(idle.phase() == P2KabutoPhase::Wait);
}

void testFixAttackEnd()
{
    // FixAttack END decision table (KabutoState.cpp:725-748).
    P2KabutoCannon fix = make(P2KabutoSpecies::Fkabuto);
    P2KabutoHostState host = liveHost();

    assert(fix.beginFixAttack());
    host.flickRequested = true;
    assert(fix.onEvent(P2KabutoEvent::End, host) == P2KabutoAction::ToFlick);
    host.flickRequested = false;

    assert(fix.beginFixAttack());
    host.targetAttackable = true;
    assert(fix.onEvent(P2KabutoEvent::End, host) == P2KabutoAction::ToFixAttack);
    assert(fix.phase() == P2KabutoPhase::FixAttack);
    host.targetAttackable = false;

    // Within max attack angle -> FixWait.
    assert(fix.beginFixAttack());
    host.targetPresent = true;
    host.targetAngle = 30.0f * kPi / 180.0f; // exactly at the boundary
    assert(fix.onEvent(P2KabutoEvent::End, host) == P2KabutoAction::ToFixWait);
    assert(fix.phase() == P2KabutoPhase::FixWait);

    // Outside -> FixTurn.
    assert(fix.beginFixAttack());
    host.targetAngle = 45.0f * kPi / 180.0f;
    assert(fix.onEvent(P2KabutoEvent::End, host) == P2KabutoAction::ToFixTurn);
    assert(fix.phase() == P2KabutoPhase::FixTurn);

    // No target -> FixHide.
    assert(fix.beginFixAttack());
    host.targetPresent = false;
    assert(fix.onEvent(P2KabutoEvent::End, host) == P2KabutoAction::ToFixHide);
    assert(fix.phase() == P2KabutoPhase::FixHide);

    // FixWait can re-enter FixAttack and fire again.
    assert(fix.beginFixAttack());
    host.targetAttackable = true;
    assert(fix.onEvent(P2KabutoEvent::Key2, host) == P2KabutoAction::FireStone);
}

void testDeath()
{
    P2KabutoCannon cannon = make(P2KabutoSpecies::Kabuto);
    assert(cannon.beginAttack());
    P2KabutoHostState host = liveHost();
    host.health = 0.0f;
    assert(cannon.onEvent(P2KabutoEvent::None, host) == P2KabutoAction::ToDead);
    assert(cannon.phase() == P2KabutoPhase::Dead);
    assert(!cannon.isAlive());

    // Dead END requests the kill, then the FSM is terminal.
    assert(cannon.onEvent(P2KabutoEvent::End, host) == P2KabutoAction::None);
    assert(cannon.killRequested());
    assert(cannon.onEvent(P2KabutoEvent::End, host) == P2KabutoAction::None);
    assert(cannon.onEvent(P2KabutoEvent::Key2, host) == P2KabutoAction::None);

    // Explicit beginDead from a live state.
    P2KabutoCannon other = make(P2KabutoSpecies::Kabuto);
    assert(other.beginDead());
    assert(other.phase() == P2KabutoPhase::Dead);
}

void testBuriedEmergence()
{
    // onInit: Fkabuto starts buried in FixStay (Kabuto.cpp:48-54).
    P2KabutoCannon buried = make(P2KabutoSpecies::Fkabuto);
    assert(buried.phase() == P2KabutoPhase::FixStay);
    P2KabutoHostState host = liveHost();

    // Invulnerable stay ignores health and waits for a target.
    host.health = 0.0f;
    assert(buried.onEvent(P2KabutoEvent::None, host) == P2KabutoAction::None);
    assert(buried.phase() == P2KabutoPhase::FixStay);
    host.health = 850.0f;

    host.targetPresent = true;
    assert(buried.onEvent(P2KabutoEvent::None, host) == P2KabutoAction::ToFixAppear);
    assert(buried.phase() == P2KabutoPhase::FixAppear);

    auto freshAppear = [&]() {
        P2KabutoCannon c = make(P2KabutoSpecies::Fkabuto);
        P2KabutoHostState h = liveHost();
        h.targetPresent = true;
        assert(c.onEvent(P2KabutoEvent::None, h) == P2KabutoAction::ToFixAppear);
        return c;
    };
    auto freshFixWait = [&]() {
        P2KabutoCannon c = freshAppear();
        P2KabutoHostState h = liveHost();
        h.targetPresent = true;
        h.targetAngle = 0.0f;
        assert(c.onEvent(P2KabutoEvent::End, h) == P2KabutoAction::ToFixWait);
        return c;
    };
    auto freshFixTurn = [&]() {
        P2KabutoCannon c = freshAppear();
        P2KabutoHostState h = liveHost();
        h.targetPresent = true;
        h.targetAngle = 45.0f * kPi / 180.0f;
        assert(c.onEvent(P2KabutoEvent::End, h) == P2KabutoAction::ToFixTurn);
        return c;
    };

    // FixAppear END: health -> Dead.
    P2KabutoCannon dead = freshAppear();
    P2KabutoHostState hd = liveHost();
    hd.health = 0.0f;
    assert(dead.onEvent(P2KabutoEvent::End, hd) == P2KabutoAction::ToDead);

    // FixAppear END: flick / attackable / within / outside / none.
    P2KabutoCannon a1 = freshAppear();
    P2KabutoHostState h1 = liveHost();
    h1.flickRequested = true;
    assert(a1.onEvent(P2KabutoEvent::End, h1) == P2KabutoAction::ToFlick);

    P2KabutoCannon a2 = freshAppear();
    P2KabutoHostState h2 = liveHost();
    h2.targetAttackable = true;
    assert(a2.onEvent(P2KabutoEvent::End, h2) == P2KabutoAction::ToFixAttack);

    P2KabutoCannon a3 = freshAppear();
    P2KabutoHostState h3 = liveHost();
    h3.targetPresent = true;
    h3.targetAngle = 30.0f * kPi / 180.0f;
    assert(a3.onEvent(P2KabutoEvent::End, h3) == P2KabutoAction::ToFixWait);

    P2KabutoCannon a4 = freshAppear();
    P2KabutoHostState h4 = liveHost();
    h4.targetPresent = true;
    h4.targetAngle = 45.0f * kPi / 180.0f;
    assert(a4.onEvent(P2KabutoEvent::End, h4) == P2KabutoAction::ToFixTurn);

    P2KabutoCannon a5 = freshAppear();
    P2KabutoHostState h5 = liveHost();
    h5.targetPresent = false;
    assert(a5.onEvent(P2KabutoEvent::End, h5) == P2KabutoAction::ToFixHide);
    assert(a5.phase() == P2KabutoPhase::FixHide);

    // FixHide END -> FixStay.
    assert(a5.onEvent(P2KabutoEvent::End, h5) == P2KabutoAction::ToFixStay);
    assert(a5.phase() == P2KabutoPhase::FixStay);

    // FixWait END: within -> FixWait; attackable -> FixAttack.
    P2KabutoCannon w = freshFixWait();
    P2KabutoHostState hw = liveHost();
    hw.targetPresent = true;
    hw.targetAngle = 0.0f;
    assert(w.onEvent(P2KabutoEvent::End, hw) == P2KabutoAction::ToFixWait);
    assert(w.phase() == P2KabutoPhase::FixWait);
    hw.targetAttackable = true;
    assert(w.onEvent(P2KabutoEvent::End, hw) == P2KabutoAction::ToFixAttack);

    // FixWait END: flick and outside/none.
    P2KabutoCannon w2 = freshFixWait();
    P2KabutoHostState hw2 = liveHost();
    hw2.flickRequested = true;
    assert(w2.onEvent(P2KabutoEvent::End, hw2) == P2KabutoAction::ToFlick);
    P2KabutoCannon w3 = freshFixWait();
    P2KabutoHostState hw3 = liveHost();
    hw3.targetPresent = true;
    hw3.targetAngle = 45.0f * kPi / 180.0f;
    assert(w3.onEvent(P2KabutoEvent::End, hw3) == P2KabutoAction::ToFixTurn);
    P2KabutoCannon w4 = freshFixWait();
    P2KabutoHostState hw4 = liveHost();
    hw4.targetPresent = false;
    assert(w4.onEvent(P2KabutoEvent::End, hw4) == P2KabutoAction::ToFixHide);

    // FixTurn END: attackable -> FixAttack; within -> FixWait; else keep turning;
    // none -> FixHide.
    P2KabutoCannon t1 = freshFixTurn();
    P2KabutoHostState ht1 = liveHost();
    ht1.targetPresent = true;
    ht1.targetAttackable = true;
    assert(t1.onEvent(P2KabutoEvent::End, ht1) == P2KabutoAction::ToFixAttack);

    P2KabutoCannon t2 = freshFixTurn();
    P2KabutoHostState ht2 = liveHost();
    ht2.targetPresent = true;
    ht2.targetAngle = 10.0f * kPi / 180.0f;
    assert(t2.onEvent(P2KabutoEvent::End, ht2) == P2KabutoAction::ToFixWait);

    P2KabutoCannon t3 = freshFixTurn();
    P2KabutoHostState ht3 = liveHost();
    ht3.targetPresent = true;
    ht3.targetAngle = 45.0f * kPi / 180.0f;
    assert(t3.onEvent(P2KabutoEvent::End, ht3) == P2KabutoAction::None);
    assert(t3.phase() == P2KabutoPhase::FixTurn);

    P2KabutoCannon t4 = freshFixTurn();
    P2KabutoHostState ht4 = liveHost();
    ht4.targetPresent = false;
    assert(t4.onEvent(P2KabutoEvent::End, ht4) == P2KabutoAction::ToFixHide);

    // FixWait can fire after re-entering FixAttack.
    P2KabutoCannon fire = freshFixWait();
    P2KabutoHostState hf = liveHost();
    hf.targetPresent = true;
    assert(fire.beginFixAttack());
    assert(fire.onEvent(P2KabutoEvent::Key2, hf) == P2KabutoAction::FireStone);
}

void testInvalidInput()
{
    P2KabutoCannon cannon = make(P2KabutoSpecies::Kabuto);
    P2KabutoHostState host = liveHost();
    host.health = std::numeric_limits<float>::quiet_NaN();
    assert(cannon.onEvent(P2KabutoEvent::End, host) == P2KabutoAction::None);
    assert(cannon.phase() == P2KabutoPhase::Wait);
    host.health = 850.0f;
    host.targetAngle = std::numeric_limits<float>::quiet_NaN();
    assert(cannon.onEvent(P2KabutoEvent::End, host) == P2KabutoAction::None);
    assert(cannon.phase() == P2KabutoPhase::Wait);
}
} // namespace

int main()
{
    testStartAndSpecies();
    testFireAndHoming();
    testWaitTurnTransitions();
    testAttackEnd();
    testFixAttackEnd();
    testDeath();
    testBuriedEmergence();
    testInvalidInput();
    return 0;
}
