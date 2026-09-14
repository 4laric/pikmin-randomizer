#include "pc_p2_dangomushi_hazard.h"

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

        P2DangoMushiHazardInput in;
        in.turnFrame = 31.9f;
        policy.update(in, out);
        assert(out.invulnerable);
        in.turnFrame = 32.0f;
        policy.update(in, out);
        assert(out.stickable && !out.invulnerable);
        assert(policy.windowActive());
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

    // Rock rain: 10 per turn with a 30 s lifetime, capped by the reserved 30.
    {
        P2DangoMushiHazardPolicy policy;
        policy.reset(parms);
        P2DangoMushiHazardOutput out;
        enterTurn(policy, out, 10.0f, 0.0f, 1.0f);
        assert(out.rocksToSpawn == 10 && out.rockLifetime == 30.0f);
        assert(out.rocksRemaining == 20);
        P2DangoMushiHazardInput in;
        in.turnEntered = true; in.turnFrame = 10.0f;
        policy.update(in, out);
        assert(out.rocksToSpawn == 10 && out.rocksRemaining == 10);
        policy.update(in, out);
        assert(out.rocksToSpawn == 10 && out.rocksRemaining == 0);
        policy.update(in, out);
        assert(out.rocksToSpawn == 0 && out.rocksRemaining == 0); // budget exhausted
    }

    // Egg: one at home with probability equal to the captain's Pikmin share,
    // capped by the reserved 10.
    {
        P2DangoMushiHazardPolicy policy;
        policy.reset(parms);
        P2DangoMushiHazardOutput out;
        enterTurn(policy, out, 10.0f, 0.5f, 0.4f); // 0.4 < 0.5 -> Egg
        assert(out.eggRequested && out.eggsRemaining == 9);
        P2DangoMushiHazardInput in;
        in.turnEntered = true; in.turnFrame = 10.0f;
        in.activeCaptainGroupShare = 0.5f; in.eggRoll = 0.6f; // 0.6 >= 0.5 -> none
        policy.update(in, out);
        assert(!out.eggRequested && out.eggsRemaining == 9);
        for (int i = 0; i < 12; ++i) {
            policy.update(in, out); // only the first of each turn can spawn
        }
        assert(out.eggsRemaining == 9);
    }

    // Deterministic ring offsets instead of engine RNG.
    {
        float x0 = 0.0f, z0 = 0.0f, x1 = 0.0f, z1 = 0.0f;
        P2DangoMushiHazardPolicy::rockOffset(0, 10, 0.0f, &x0, &z0);
        P2DangoMushiHazardPolicy::rockOffset(0, 10, 0.0f, &x1, &z1);
        assert(x0 == x1 && z0 == z1);
        assert(std::fabs(x0 - 100.0f) < 1e-3f && std::fabs(z0) < 1e-3f);
        float x2 = 0.0f, z2 = 0.0f;
        P2DangoMushiHazardPolicy::rockOffset(5, 10, 0.0f, &x2, &z2);
        assert(std::fabs(x2 + 100.0f) < 1e-3f);
    }

    std::puts("PASS DANGOMUSHI_HAZARD");
    return 0;
}
