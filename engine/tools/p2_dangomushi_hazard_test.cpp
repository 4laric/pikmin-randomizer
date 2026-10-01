#include "pc_p2_dangomushi_hazard.h"

// Release builds pass -DNDEBUG; force assertions (and their embedded
// side effects) on so this engine-free gate is not vacuous under ctest.
#undef NDEBUG
#include <cassert>
#include <cmath>
#include <cstdio>

// Standalone fixture for the lane-owned DangoMushi Turn vulnerability window and
// Rock/Egg flip-hazard spawner decisions. Source:
// docs/PIKMIN2_SNAGRET_CRAWBSTER_AUDIT.md (US GPVE01 rev 0).

namespace {
void enterTurn(P2DangoMushiHazardPolicy& p, P2DangoMushiHazardOutput& out,
               float frame, float share, float roll)
{
    P2DangoMushiHazardInput in;
    in.turnEntered = true;
    in.turnFrame = frame;
    in.activeCaptainGroupShare = share;
    in.eggRoll = roll;
    p.update(in, out);
}
}

int main()
{
    const P2DangoMushiHazardParms parms;

    // Vulnerability window: only between the turn loop-start key (32) and key 3
    // (108); the body is invulnerable outside it.
    {
        P2DangoMushiHazardPolicy policy;
        policy.reset(parms);
        P2DangoMushiHazardOutput out;
        enterTurn(policy, out, 10.0f, 1.0f, 1.0f);
        assert(out.invulnerable && !out.stickable);
        // The host damage gate consumes this shared predicate: an attack/bomb is
        // rejected whenever the body is not stickable.
        assert(P2DangoMushiHazardPolicy::attackRejected(out.stickable));
        assert(!P2DangoMushiHazardPolicy::attackRejected(true));

        P2DangoMushiHazardInput in;
        in.turnFrame = 31.9f;
        policy.update(in, out);
        assert(out.invulnerable);
        in.turnFrame = 32.0f;
        policy.update(in, out);
        assert(out.stickable && !out.invulnerable);
        assert(policy.windowActive());
        assert(!P2DangoMushiHazardPolicy::attackRejected(out.stickable));
        in.turnFrame = 107.9f;
        policy.update(in, out);
        assert(out.stickable);
        in.turnFrame = 108.0f;
        policy.update(in, out);
        assert(out.invulnerable && !out.stickable);

        in = P2DangoMushiHazardInput();
        in.turnExited = true;
        policy.update(in, out);
        assert(out.invulnerable && !out.stickable && !policy.windowActive());
    }

    // Rock rain (#897): createCrashEnemy fires 10 Rocks (30 s) on EVERY Turn.
    // There is no lifetime budget: the 4th, 5th ... Turn still rains 10.
    {
        P2DangoMushiHazardPolicy policy;
        policy.reset(parms);
        P2DangoMushiHazardOutput out;
        for (int turn = 1; turn <= 8; ++turn) {
            P2DangoMushiHazardInput in;
            in.turnEntered = true; in.turnFrame = 0.0f;
            policy.update(in, out);
            assert(out.rocksToSpawn == 10 && out.rockLifetime == 30.0f);
            assert(out.turnIndex == turn);
            // Only the entry tick of a Turn rains.
            in.turnEntered = false; in.turnFrame = 40.0f;
            policy.update(in, out);
            assert(out.rocksToSpawn == 0);
            in = P2DangoMushiHazardInput(); in.turnExited = true;
            policy.update(in, out);
        }
        assert(policy.turns() == 8);
    }

    // Egg: one at home with probability equal to the captain's Pikmin share,
    // decided once per Turn, never budget-limited.
    {
        P2DangoMushiHazardPolicy policy;
        policy.reset(parms);
        P2DangoMushiHazardOutput out;
        enterTurn(policy, out, 10.0f, 0.5f, 0.4f); // 0.4 < 0.5 -> Egg
        assert(out.eggRequested);
        P2DangoMushiHazardInput in;
        in.turnFrame = 10.0f; in.activeCaptainGroupShare = 1.0f; in.eggRoll = 0.0f;
        policy.update(in, out); // same Turn: no second decision
        assert(!out.eggRequested);
        int eggs = 0;
        for (int i = 0; i < 15; ++i) {
            enterTurn(policy, out, 0.0f, 1.0f, 0.2f);
            eggs += out.eggRequested ? 1 : 0;
        }
        assert(eggs == 15);
        enterTurn(policy, out, 0.0f, 0.5f, 0.6f); // 0.6 >= 0.5 -> none
        assert(!out.eggRequested);
    }

    // Source createCrashEnemy ring layout (jitter at its midpoint).
    {
        float x0 = 0.0f, z0 = 0.0f, x1 = 0.0f, z1 = 0.0f;
        P2DangoMushiHazardPolicy::rockOffset(0, 10, 0.0f, &x0, &z0);
        P2DangoMushiHazardPolicy::rockOffset(0, 10, 0.0f, &x1, &z1);
        assert(x0 == x1 && z0 == z1);
        assert(std::fabs(std::sqrt(x0 * x0 + z0 * z0) - 7.5f) < 1e-3f);
        for (int i = 1; i < 4; ++i) {
            float x = 0.0f, z = 0.0f;
            P2DangoMushiHazardPolicy::rockOffset(i, 10, 0.3f, &x, &z);
            assert(std::fabs(std::sqrt(x * x + z * z) - 77.5f) < 1e-3f);
        }
        for (int i = 4; i < 10; ++i) {
            float x = 0.0f, z = 0.0f;
            P2DangoMushiHazardPolicy::rockOffset(i, 10, 0.3f, &x, &z);
            assert(std::fabs(std::sqrt(x * x + z * z) - 147.5f) < 1e-3f);
        }
    }

    std::puts("PASS DANGOMUSHI_HAZARD");
    return 0;
}
