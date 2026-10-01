// Adult Chappy policy (owner playtest 2026-09-30): clip loops, wake rule, snore
// bubble window, alert cone, walk facing gate, retail territory/home parms.
#include "pc_p2_chappy_adult.h"
#include "pc_p2_chappy_policy.h"

#include <cassert>
#include <cmath>
#include <cstdio>

using namespace p2chappyadult;

static bool near(float a, float b) { return std::fabs(a - b) < 1.0e-3f; }

int main()
{
    // Bank event parsing (real rows from p2-chappy-bank.txt).
    auto move1 = parseEvents("5:0,33:1");
    assert(move1.size() == 2);
    Loop mv = loopFromEvents(move1);
    assert(mv.start == 5 && mv.end == 33 && mv.valid());
    Loop sleep = loopFromEvents(parseEvents("77:2,80:0,139:1,142:3"));
    assert(sleep.start == 80 && sleep.end == 139);
    assert(!loopFromEvents(parseEvents("-")).valid());
    assert(!loopFromEvents(parseEvents("10:2,33:3,40:4")).valid());

    // Walk: 50-frame clip must keep moving after it once ran past the loop end.
    float prev = -1.0f;
    bool moved = false;
    for (int i = 0; i < 400; ++i) {
        const float f = clipFrame(mv, float(i) * 40.0f / 30.0f, 50, false);
        assert(f >= 0.0f && f <= 49.0f);
        if (i > 60 && !near(f, prev)) moved = true;
        assert(i <= 30 || f >= float(mv.start) - 1e-3f); // never back before the loop start once looping
        prev = f;
    }
    assert(moved); // frame still changing ten seconds in: no freeze on the last pose
    // The pre-fix behaviour was a clamp; prove the two differ after the loop end.
    assert(clipFrame(mv, 200.0f, 50, false) < 33.0f);
    assert(clipFrame(mv, 200.0f, 50, true) == 49.0f);

    // Finish request continues from the loop position, not from the loop end.
    const float e = elapsedAtFinish(sleep, 500.0f, 190);
    assert(e >= 80.0f && e < 139.0f);
    assert(clipFrame(sleep, e, 190, true) == e);

    // Wake: damage or collision only. Sight (a captain 400 away) never wakes.
    assert(!sleepWakes(false, false));
    assert(sleepWakes(true, false));
    assert(sleepWakes(false, true));
    assert(touching(40.0f) && !touching(120.0f) && !touching(400.0f));

    // Snore bubble: only inside the sleep loop window, never awake.
    assert(!snoreActive(false, true, 100.0f, 80, 142));
    assert(!snoreActive(true, false, 100.0f, 80, 142));
    assert(!snoreActive(true, true, 70.0f, 80, 142));
    assert(snoreActive(true, true, 80.0f, 80, 142));
    assert(snoreActive(true, true, 141.0f, 80, 142));
    assert(!snoreActive(true, true, 142.0f, 80, 142));
    assert(!snoreActive(true, true, 189.0f, 80, 142));

    // Alert: inside the private radius widens the cone to 180 for alertTime.
    Alert a;
    assert(!alerted(a, 7.0f) && near(searchAngle(a, 7.0f, 90.0f), 90.0f));
    alertTick(a, true, 7.0f, 1.0f / 30.0f);
    assert(alerted(a, 7.0f) && near(searchAngle(a, 7.0f, 90.0f), 180.0f));
    for (int i = 0; i < 30 * 8; ++i) alertTick(a, false, 7.0f, 1.0f / 30.0f);
    assert(!alerted(a, 7.0f));

    // Cone and walk gate.
    assert(withinAngle(1.5f, 90.0f) && !withinAngle(1.7f, 90.0f) && withinAngle(3.1f, 180.0f));
    assert(walkFacing(0.6f, 90.0f)); // 34 degrees off: used to bounce to Turn at 25
    assert(!walkFacing(2.0f, 90.0f) && walkFacing(2.0f, 180.0f));

    // Retail parms: territory 400 / home 15 for the three ChappyBase adults.
    for (unsigned id : {2u, 33u, 43u}) {
        const auto* sp = p2chappy::speciesForSource(id);
        assert(sp);
        assert(near(sp->territory, 400.0f) && near(sp->homeRadius, 15.0f) && near(sp->privateRadius, 70.0f));
        assert(near(sp->viewAngle, 90.0f));
    }
    assert(near(p2chappy::speciesForSource(33)->searchAngle, 120.0f));
    assert(near(p2chappy::speciesForSource(33)->alertTime, 15.0f));
    assert(near(p2chappy::speciesForSource(53)->territory, 300.0f)); // Emperor unchanged

    // Fire: three anchors, alive and dry only.
    assert(fireWanted(true, false) && !fireWanted(false, false) && !fireWanted(true, true));
    assert(near(fireOffset(1).z, 34.0f) && near(fireOffset(2).z, -30.0f));

    // #994 leash: state changes wait for the clip END (finishMotion), never the same frame.
    {
        assert(near(cycleEndFrame(0.0f, 41), 40.0f));
        assert(near(cycleEndFrame(12.5f, 41), 40.0f));
        assert(near(cycleEndFrame(40.0f, 41), 80.0f));
        assert(!cycleEnded(39.9f, 40.0f) && cycleEnded(40.0f, 40.0f));
        assert(cycleEndFrame(3.0f, 1) > 3.0f); // degenerate clip still advances
        // Leash loop: territory 400, GoHome still sights the target. Walk stands one cycle, GoHome walks
        // one full cycle toward home, so the net travel per loop is positive (the port used to make 0).
        const float speed = 110.0f, fps = 40.0f; // fp06 move speed; SpeedMove clip rate
        const int frames = 81;                    // a move1-sized clip
        const float cycleSec = float(frames - 1) / fps;
        float t = 0.0f, pos = 405.0f;             // 405 from home: just past the 400 territory
        // Walk: request at elapsed 0 -> stands for one cycle.
        float walkEnd = cycleEndFrame(0.0f, frames);
        t += walkEnd / fps;
        // GoHome: sighted target only requests Walk; it keeps walking until its own clip END.
        float goEnd = cycleEndFrame(0.0f, frames);
        pos -= speed * (goEnd / fps);
        assert(pos < 400.0f - 100.0f && t > 0.0f && cycleSec > 1.0f);
    }

    std::puts("p2_chappy_adult_test PASS");
    return 0;
}
