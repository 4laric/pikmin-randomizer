// Standalone tests for the Sarai (ID 23) natural captor front end (#457).
// Build: g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_sarai_captor_test.cpp -o p2_sarai_captor_test.exe
#include "pc_p2_sarai_captor.h"
#include <cassert>
#include <cmath>
#include <cstdio>

namespace {
P2SaraiCaptor::Input base()
{
    P2SaraiCaptor::Input in;
    in.faceDirection = 0;
    in.homeDistanceSquaredXZ = 0;
    in.territoryRadius = 100;
    in.viewAngleDegrees = 90;
    in.sightRadius = 100;
    in.moveSpeed = 10;
    in.turnSpeed = 1;
    in.maxTurnAngleDegrees = 45;
    in.attackRange = 12;
    in.delta = 0.1f; // source query cap is 0.25s
    in.active = true;
    return in;
}
P2SaraiCaptor::Output prime(P2SaraiCaptor& captor, P2SaraiCaptor::Input in)
{
    P2SaraiCaptor::Output out;
    for (int i = 0; i < 31; ++i) out = captor.step(in);
    return out;
}
}

int main()
{
    P2SaraiCaptain captain{true, false, false, true, 0.0f, 100.0f};

    // Disabled acquisition returns a valid, empty selection and does not advance
    // the source query timer.
    {
        P2SaraiCaptor captor;
        auto in = base(); in.active = false; in.captains = &captain; in.count = 1;
        const auto out = captor.step(in);
        assert(out.valid && !out.targetFound && !out.beginAttack);
        assert(captor.targetTimer() == 0.0f);
    }

    // Source three-second acquisition timer gates the first selection.
    {
        P2SaraiCaptor captor;
        auto in = base(); in.captains = &captain; in.count = 1;
        P2SaraiCaptor::Output out;
        for (int i = 0; i < 30; ++i) { out = captor.step(in); assert(!out.targetFound); } // 3.0s, not > 3
        out = captor.step(in);                                                          // 3.1s
        assert(out.valid && out.targetFound && out.targetIndex == 0);
    }

    // Territory, view and sight gates each reject before the target is selected.
    {
        P2SaraiCaptor captor;
        auto in = base(); in.homeDistanceSquaredXZ = 200 * 200; // outside territory (100)
        in.captains = &captain; in.count = 1;
        assert(!prime(captor, in).targetFound);
    }
    {
        P2SaraiCaptain wide{true, false, false, true, 1.0f, 100.0f}; // 57 deg
        P2SaraiCaptor captor;
        // viewHalfAngle(10) == PI * (DEG2RAD * 10) ~= 0.548 rad.
        auto in = base(); in.captains = &wide; in.count = 1; in.viewAngleDegrees = 10;
        assert(!prime(captor, in).targetFound);
    }
    {
        P2SaraiCaptain narrow{true, false, false, true, 0.2f, 100.0f};
        P2SaraiCaptor captor;
        auto in = base(); in.captains = &narrow; in.count = 1; in.viewAngleDegrees = 10;
        assert(prime(captor, in).targetFound);
    }
    {
        P2SaraiCaptain far{true, false, false, true, 0.0f, 200.0f * 200.0f}; // outside sight 100
        P2SaraiCaptor captor;
        auto in = base(); in.captains = &far; in.count = 1;
        assert(!prime(captor, in).targetFound);
    }

    // Dead, already mouth-stuck, self-stuck and airborne candidates are skipped.
    {
        P2SaraiCaptain dead{false, false, false, true, 0.0f, 100.0f};
        P2SaraiCaptain stuck{true, true, false, true, 0.0f, 100.0f};
        P2SaraiCaptain self{true, false, true, true, 0.0f, 100.0f};
        P2SaraiCaptain airborne{true, false, false, false, 0.0f, 100.0f};
        P2SaraiCaptain live{true, false, false, true, 0.2f, 100.0f};
        P2SaraiCaptain captains[5] = {dead, stuck, self, airborne, live};
        P2SaraiCaptor captor;
        auto in = base(); in.captains = captains; in.count = 5;
        const auto out = prime(captor, in);
        assert(out.targetFound && out.targetIndex == 4);
    }

    // Approach turns toward the bearing under the source turn cap and drives
    // forward along the new facing.
    {
        P2SaraiCaptain right{true, false, false, true, 0.5f, 50.0f * 50.0f};
        P2SaraiCaptor captor;
        auto in = base(); in.captains = &right; in.count = 1;
        const auto out = prime(captor, in);
        assert(out.valid && out.targetFound && !out.beginAttack);
        assert(std::fabs(out.faceDirection - 0.5f) < 0.0001f); // 0.5*1 < 45deg cap
        assert(std::fabs(out.velocityX - std::sin(0.5f) * 10.0f) < 0.0001f);
        assert(std::fabs(out.velocityZ - std::cos(0.5f) * 10.0f) < 0.0001f);
    }

    // Turn is capped by maxTurnAngleDegrees for wide bearings.
    {
        P2SaraiCaptain behind{true, false, false, true, -1.4f, 2500.0f}; // 80 deg
        P2SaraiCaptor captor;
        auto in = base(); in.captains = &behind; in.count = 1;
        in.maxTurnAngleDegrees = 45; in.turnSpeed = 10; // |-1.4|*10 > 45deg
        const auto out = prime(captor, in);
        assert(std::fabs(out.faceDirection - (-45.0f * 3.14159265f / 180.0f)) < 0.0001f);
    }

    // Inside grab range the host is asked to begin Attack and stops driving.
    {
        P2SaraiCaptain close{true, false, false, true, 0.0f, 10.0f * 10.0f}; // 10 < attackRange 12
        P2SaraiCaptor captor;
        auto in = base(); in.captains = &close; in.count = 1;
        const auto out = prime(captor, in);
        assert(out.targetFound && out.beginAttack);
        assert(out.velocityX == 0.0f && out.velocityZ == 0.0f);
    }

    // Invalid inputs are rejected without advancing the acquisition timer.
    {
        P2SaraiCaptor captor;
        auto in = base(); in.captains = &captain; in.count = 1;
        in.delta = 0.0f;
        assert(!captor.step(in).valid);
        assert(captor.targetTimer() == 0.0f);
        in = base(); in.captains = &captain; in.count = 1; in.delta = 0.5f;
        assert(!captor.step(in).valid); // > 0.25 cap
        in = base(); in.captains = &captain; in.count = 1; in.moveSpeed = -1.0f;
        assert(!captor.step(in).valid);
    }

    // reset clears the accumulated acquisition timer.
    {
        P2SaraiCaptor captor;
        auto in = base(); in.captains = &captain; in.count = 1;
        assert(!captor.step(in).targetFound);
        captor.reset();
        assert(captor.targetTimer() == 0.0f);
        assert(prime(captor, in).targetFound);
    }

    std::puts("p2_sarai_captor_test PASS");
    return 0;
}
