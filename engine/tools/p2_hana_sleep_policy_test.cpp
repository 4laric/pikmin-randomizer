// Buried idle / emergence timeline for Hana (pc_p2_hana_sleep_policy.h), #964.
#include "pc_p2_hana_sleep_policy.h"

#include <cassert>
#include <cmath>
#include <cstdio>

using p2hanasleep::Cursor;
using p2hanasleep::Phase;

int main()
{
    // Retail type1: 149 frames, LOOP_START 30, LOOP_END 100.
    Cursor c;
    c.configure(149.0f, 30.0f, 100.0f);

    // Spawn: StateSleep::init mDoSkipSleepStart -> frame 70, inside the loop.
    c.startSpawn();
    assert(c.phase() == Phase::Loop && std::fabs(c.frame() - 70.0f) < 1e-4f);
    assert(c.buriedPose());
    // The buried pose is never the standing body (frame 0) and stays in the loop
    // region however long the trap waits.
    for (int i = 0; i < 3000; ++i) {
        assert(!c.advance(1.0f / 30.0f));
        assert(c.frame() >= 30.0f && c.frame() < 100.0f);
        assert(c.buriedPose());
    }
    assert(c.phase01() > 0.2f && c.phase01() < 0.68f);

    // Wake: leave the loop at 60 fps and play on to the end, exactly once.
    c.startSpawn();
    c.wake();
    assert(c.phase() == Phase::Wake && !c.buriedPose());
    const float before = c.frame();
    float t = 0.0f;
    bool burst = false;
    float prev = before;
    while (!c.advance(1.0f / 30.0f)) {
        t += 1.0f / 30.0f;
        if (Cursor::crossed(prev, c.frame(), 120.0f)) {
            assert(!burst);
            burst = true;
        }
        prev = c.frame();
        assert(t < 5.0f);
    }
    assert(burst);
    // (148 - 70) frames at 60 fps = 1.3 s.
    assert(std::fabs(t - 78.0f / 60.0f) < 0.1f);
    assert(std::fabs(c.phase01() - 1.0f) < 1e-4f);

    // A GoHome re-entry dives from the standing body into the ground first.
    c.startDive();
    assert(c.phase() == Phase::Dive && c.frame() == 0.0f && !c.buriedPose());
    float dive = 0.0f;
    while (c.phase() == Phase::Dive) {
        c.advance(1.0f / 30.0f);
        dive += 1.0f / 30.0f;
        assert(dive < 3.0f);
    }
    assert(std::fabs(dive - 1.0f) < 0.1f);  // 30 frames at 30 fps
    assert(c.phase() == Phase::Loop && c.buriedPose());

    // Waking during the dive continues from the current frame.
    c.startDive();
    c.advance(0.5f);
    const float mid = c.frame();
    c.wake();
    c.advance(1.0f / 60.0f);
    assert(c.frame() > mid && c.phase() == Phase::Wake);

    // Bad loop events fall back to the retail bounds; tiny totals are clamped.
    Cursor d;
    d.configure(149.0f, -1.0f, -1.0f);
    assert(d.loopBegin() == 30.0f && d.loopEnd() == 100.0f);
    d.configure(149.0f, 120.0f, 100.0f);
    assert(d.loopBegin() == 30.0f);
    d.configure(1.0f, 30.0f, 100.0f);
    assert(d.total() >= 2.0f);

    // Wake radius: the source private radius in a seed, the sight radius in fixtures.
    assert(p2hanasleep::wakeRadius(true) == 70.0f);
    assert(p2hanasleep::wakeRadius(false) == 500.0f);

    std::puts("p2_hana_sleep_policy_test OK");
    return 0;
}
