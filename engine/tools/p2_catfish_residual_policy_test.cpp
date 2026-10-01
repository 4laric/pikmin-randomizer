#include "pc_p2_catfish_residual_policy.h"

#include <cstdio>

// Standalone residual matrix for Catfish (Water Dumple, EnemyID 26): two-slot
// mouth capture, attackNavi captain damage, fp02 White-Pikmin poison and the
// banked flick event dispatch. Source: KochappyBase::StateAttack/StateFlick
// (kochappyState.cpp:1398-1799), Catfish::Obj::initMouthSlots (Catfish.cpp:83)
// and EnemyFunc::eatPikmin/swallowPikmin/attackNavi (enemyAction.cpp:1107-1205)
// at research revision 632af93787b9c95b63f0c13be32b161375ce3a96.
// Build: g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port
//            tools/p2_catfish_residual_policy_test.cpp -o catfish_residual_test

#undef assert
#define assert(condition) do { if (!(condition)) return __LINE__; } while (false)

using namespace p2catfish;

int main()
{
    // Banked attack events: bite (17,2) -> Bite, swallow (75,3) -> Swallow.
    assert(attackEvent(2) == AttackEvent::Bite);
    assert(attackEvent(3) == AttackEvent::Swallow);
    assert(attackEvent(0) == AttackEvent::None);
    assert(attackEvent(1) == AttackEvent::None);
    assert(attackEvent(1000) == AttackEvent::None);

    // Banked flick events: (25,2) -> Knockback, (47,3) -> RestoreNonStone.
    assert(flickEvent(2) == FlickEvent::Knockback);
    assert(flickEvent(3) == FlickEvent::RestoreNonStone);
    assert(flickEvent(0) == FlickEvent::None);
    assert(flickEvent(1) == FlickEvent::None);

    // attackNavi uses general fp22=50 hit radius and fp23=15 deg hit angle.
    assert(attackNaviHits(0.0f, 0.0f));
    assert(attackNaviHits(49.9f, 0.2617993f));
    assert(!attackNaviHits(50.0f, 0.0f));
    assert(!attackNaviHits(10.0f, 0.2618f));
    assert(!attackNaviHits(kAttackHitRadius - 1.0f, kAttackHitAngle));

    // Flick range is general fp19 default 120.
    assert(inFlickRange(119.9f));
    assert(!inFlickRange(120.0f));
    assert(!inFlickRange(120.1f));

    // Two-slot mouth: nearest-first, at most two, never the same index twice.
    {
        Candidate candidates[4];
        candidates[0] = {40.0f, true, false};
        candidates[1] = {10.0f, true, false};
        candidates[2] = {20.0f, true, false};
        candidates[3] = {5.0f, true, false};
        int chosen[kMouthSlots] = {-1, -1};
        const int count = selectMouthCaptures(candidates, 4, chosen);
        assert(count == 2);
        assert(chosen[0] == 3); // nearest (5.0)
        assert(chosen[1] == 1); // next nearest (10.0)
    }

    // Held creatures are never ingested twice; ineligible ones are never taken.
    {
        Candidate candidates[3];
        candidates[0] = {5.0f, true, true};   // already in a mouth slot
        candidates[1] = {8.0f, false, false}; // outside the attack sweep
        candidates[2] = {30.0f, true, false};
        int chosen[kMouthSlots] = {-1, -1};
        const int count = selectMouthCaptures(candidates, 3, chosen);
        assert(count == 1);
        assert(chosen[0] == 2);
    }

    // Fewer than two eligible: fill what is available.
    {
        Candidate candidates[2];
        candidates[0] = {15.0f, true, false};
        candidates[1] = {60.0f, false, false};
        int chosen[kMouthSlots] = {-1, -1};
        assert(selectMouthCaptures(candidates, 2, chosen) == 1);
        assert(chosen[0] == 0);
    }

    // Empty / all ineligible / all held: zero captures.
    {
        int chosen[kMouthSlots] = {-1, -1};
        assert(selectMouthCaptures(nullptr, 0, chosen) == 0);
        Candidate ineligible[1] = {{5.0f, false, false}};
        assert(selectMouthCaptures(ineligible, 1, chosen) == 0);
        Candidate held[1] = {{5.0f, true, true}};
        assert(selectMouthCaptures(held, 1, chosen) == 0);
    }

    // swallowPikmin: non-White dies without poison.
    {
        const SwallowResult r = swallowResult(false, false);
        assert(r.kill);
        assert(!r.poison);
        assert(r.poisonDamage == 0.0f);
    }

    // swallowPikmin: White dies and poisons the eater with proper fp02=300.
    {
        const SwallowResult r = swallowResult(true, false);
        assert(r.kill);
        assert(r.poison);
        assert(r.poisonDamage == kPoisonDamage);
        assert(kPoisonDamage == 300.0f);
    }

    // Exactly-once: a creature already consumed yields no second kill/poison.
    {
        const SwallowResult white = swallowResult(true, true);
        assert(!white.kill);
        assert(!white.poison);
        assert(white.poisonDamage == 0.0f);
        const SwallowResult normal = swallowResult(false, true);
        assert(!normal.kill);
    }

    std::puts("p2_catfish_residual_policy_test PASS");
    return 0;
}
