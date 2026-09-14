#include "pc_p2_demon_captor.h"
#include <cassert>
#include <cmath>
#include <cstdio>

namespace {
P2DemonCaptor::Input base() {
    P2DemonCaptor::Input in;
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
// Advance the acquisition timer past the source three-second gate.
P2DemonCaptor::Output prime(P2DemonCaptor& captor, P2DemonCaptor::Input in) {
    P2DemonCaptor::Output out;
    for (int i = 0; i < 31; ++i) out = captor.step(in);
    return out;
}
}

int main() {
    P2DemonCaptain captain{true, false, 0.0f, 100.0f};

    // Disabled acquisition returns a valid, empty selection and still advances
    // the source query timer.
    {
        P2DemonCaptor captor;
        auto in = base(); in.active = false; in.captains = &captain; in.count = 1;
        const auto out = captor.step(in);
        assert(out.valid && !out.targetFound && !out.beginAttack);
        assert(captor.targetTimer() == 0.0f); // disabled queries do not advance the source timer
    }

    // Source three-second acquisition timer gates the first selection.
    {
        P2DemonCaptor captor;
        auto in = base(); in.captains = &captain; in.count = 1;
        P2DemonCaptor::Output out;
        for (int i = 0; i < 30; ++i) { out = captor.step(in); assert(!out.targetFound); } // 3.0s, not > 3
        out = captor.step(in);                                                          // 3.1s
        assert(out.valid && out.targetFound && out.targetIndex == 0);
    }

    // Territory, view and sight gates each reject before the target is selected.
    {
        P2DemonCaptor captor;
        auto in = base();
        in.homeDistanceSquaredXZ = 200 * 200; // outside territory (100)
        in.captains = &captain; in.count = 1;
        assert(!prime(captor, in).targetFound);
    }
    {
        P2DemonCaptain wide{true, false, 1.5f, 100.0f}; // 86 deg, view half-angle 60
        P2DemonCaptor captor;
        auto in = base(); in.captains = &wide; in.count = 1; in.viewAngleDegrees = 60;
        assert(!prime(captor, in).targetFound);
    }
    {
        P2DemonCaptain far{true, false, 0.0f, 200.0f * 200.0f}; // outside sight 100
        P2DemonCaptor captor;
        auto in = base(); in.captains = &far; in.count = 1;
        assert(!prime(captor, in).targetFound);
    }

    // Dead or already mouth-stuck candidates are skipped.
    {
        P2DemonCaptain dead{false, false, 0.0f, 100.0f};
        P2DemonCaptain stuck{true, true, 0.0f, 100.0f};
        P2DemonCaptain live{true, false, 0.2f, 100.0f};
        P2DemonCaptain captains[3] = {dead, stuck, live};
        P2DemonCaptor captor;
        auto in = base(); in.captains = captains; in.count = 3;
        const auto out = prime(captor, in);
        assert(out.targetFound && out.targetIndex == 2);
    }

    // Approach turns toward the bearing under the source turn cap and drives
    // forward along the new facing.
    {
        P2DemonCaptain right{true, false, 0.5f, 50.0f * 50.0f};
        P2DemonCaptor captor;
        auto in = base(); in.captains = &right; in.count = 1;
        const auto out = prime(captor, in);
        assert(out.valid && out.targetFound && !out.beginAttack);
        assert(std::fabs(out.faceDirection - 0.5f) < 0.0001f); // 0.5*1 < 45deg cap
        assert(std::fabs(out.velocityX - std::sin(0.5f) * 10.0f) < 0.0001f);
        assert(std::fabs(out.velocityZ - std::cos(0.5f) * 10.0f) < 0.0001f);
    }

    // Turn is capped by maxTurnAngleDegrees for wide bearings.
    {
        P2DemonCaptain behind{true, false, -1.4f, 2500.0f}; // 80 deg, inside 90 half-angle
        P2DemonCaptor captor;
        auto in = base(); in.captains = &behind; in.count = 1;
        in.maxTurnAngleDegrees = 45; in.turnSpeed = 10; // |-1.4|*10 > 45deg
        const auto out = prime(captor, in);
        assert(std::fabs(out.faceDirection - (-45.0f * 3.14159265f / 180.0f)) < 0.0001f);
    }

    // Inside grab range the host is asked to begin Attack and stops driving.
    {
        P2DemonCaptain close{true, false, 0.0f, 10.0f * 10.0f}; // 10 < attackRange 12
        P2DemonCaptor captor;
        auto in = base(); in.captains = &close; in.count = 1;
        const auto out = prime(captor, in);
        assert(out.targetFound && out.beginAttack);
        assert(out.velocityX == 0.0f && out.velocityZ == 0.0f);
    }

    // Invalid inputs are rejected without advancing the acquisition timer.
    {
        P2DemonCaptor captor;
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
        P2DemonCaptor captor;
        auto in = base(); in.captains = &captain; in.count = 1;
        assert(!captor.step(in).targetFound);
        captor.reset();
        assert(captor.targetTimer() == 0.0f);
        assert(prime(captor, in).targetFound);
    }

    std::puts("p2_demon_captor_test PASS");
    return 0;
}
