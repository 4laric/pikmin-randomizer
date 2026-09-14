// Standalone fixture for the engine-free Waterwraith combat rules (#443).
// Build (single line):
//   g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_waterwraith_attack_policy_test.cpp -o <out>.exe
#include "pc_p2_waterwraith_attack_policy.h"

#include <cassert>
#include <cstdio>

using namespace p2wwatk;

static Target make(float x, float z, bool purple, bool alive = true)
{
    Target t;
    t.x = x;
    t.z = z;
    t.purple = purple;
    t.alive = alive;
    return t;
}

int main()
{
    const Rule rule;

    // 1. Riding, not damageable: a Purple inside stun range sets a stun only.
    {
        Target t[] = { make(50.0f, 0.0f, true) };
        Evaluation e = evaluate(rule, 0.0f, 0.0f, true, false, true, t, 1);
        assert((e.actions & ActionStun) != 0u);
        assert((e.actions & ActionHit) == 0u);
        assert((e.actions & ActionCrush) == 0u);
        assert(e.purpleHits == 0 && e.crushTargets == 0);
    }

    // 2. Riding, damageable (frozen): Purple in hit range is accepted once each;
    //    a non-Purple in the same range is never a hit.
    {
        Target t[] = { make(60.0f, 0.0f, true), make(30.0f, 0.0f, false) };
        Evaluation e = evaluate(rule, 0.0f, 0.0f, true, true, false, t, 2);
        assert((e.actions & ActionHit) != 0u);
        assert((e.actions & ActionStun) == 0u);
        assert((e.actions & ActionCrush) == 0u);
        assert(e.purpleHits == 1);
    }

    // 3. Riding, damageable: a Purple outside the hit radius does nothing.
    {
        Target t[] = { make(400.0f, 0.0f, true) };
        Evaluation e = evaluate(rule, 0.0f, 0.0f, true, true, false, t, 1);
        assert(e.actions == ActionNone);
    }

    // 4. Rolling: non-Purple in crush range is crushed; frozen (not rolling)
    //    never crushes.
    {
        Target t[] = { make(40.0f, 20.0f, false), make(500.0f, 0.0f, false) };
        Evaluation rolling = evaluate(rule, 0.0f, 0.0f, true, false, true, t, 2);
        assert((rolling.actions & ActionCrush) != 0u);
        assert(rolling.crushTargets == 1);
        Evaluation frozen = evaluate(rule, 0.0f, 0.0f, true, true, false, t, 2);
        assert((frozen.actions & ActionCrush) == 0u);
    }

    // 5. A Purple is never crushed (it stuns/hits instead), even while rolling.
    {
        Target t[] = { make(40.0f, 0.0f, true) };
        Evaluation e = evaluate(rule, 0.0f, 0.0f, true, false, true, t, 1);
        assert((e.actions & ActionCrush) == 0u);
        assert(e.crushTargets == 0);
        assert((e.actions & ActionStun) != 0u);
    }

    // 6. Dismounted (no child): no stun, no crush; the exposed body still takes
    //    Purple hits at hit range.
    {
        Target t[] = { make(40.0f, 0.0f, true), make(20.0f, 0.0f, false) };
        Evaluation e = evaluate(rule, 0.0f, 0.0f, false, true, false, t, 2);
        assert((e.actions & ActionStun) == 0u);
        assert((e.actions & ActionCrush) == 0u);
        assert((e.actions & ActionHit) != 0u);
        assert(e.purpleHits == 1);
    }

    // 7. Dead targets are ignored.
    {
        Target t[] = { make(20.0f, 0.0f, true, false), make(10.0f, 0.0f, false, false) };
        Evaluation e = evaluate(rule, 0.0f, 0.0f, true, true, true, t, 2);
        assert(e.actions == ActionNone);
    }

    // 8. Multiple Purples in hit range each count as one hit.
    {
        Target t[] = { make(10.0f, 0.0f, true), make(20.0f, 30.0f, true), make(300.0f, 0.0f, true) };
        Evaluation e = evaluate(rule, 0.0f, 0.0f, true, true, false, t, 3);
        assert(e.purpleHits == 2);
    }

    std::puts("PASS WATERWRAITH_ATTACK_POLICY");
    return 0;
}
