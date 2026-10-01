// Standalone fixture for the Fuefuki follow-locomotion policy (#245).
// Engine-free; mirrors PikiAI::ActTeki (aiTeki.cpp) and Game::Footmarks
// (gameFootmark.cpp). Build:
//   g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_fuefuki_follow_test.cpp -o ../p2_fuefuki_follow_test.exe
#include "pc_p2_fuefuki_follow.h"

#include <cmath>
#include <cstdio>

namespace {
int gFailures = 0;

void check(bool cond, const char* what)
{
    if (!cond) {
        std::printf("FAIL: %s\n", what);
        gFailures++;
    }
}

bool near(float a, float b, float eps = 1e-4f) { return std::fabs(a - b) <= eps; }

float rndZero(void*) { return 0.0f; }
float rndOne(void*) { return 1.0f; }

const float kTick = 1.0f / 30.0f;

void buildTrail(P2FuefukiFollowController& c, const float* xs, int n)
{
    for (int i = 0; i < n; i++) c.beetleTick(xs[i], 0.0f, 1.0f);
}

void testFootmarkRingAndSpacing()
{
    P2FuefukiFollowController c;
    // Four marks at 30-unit spacing: all stored (first two skip the spacing test).
    const float xs[] = { 0.0f, 30.0f, 60.0f, 90.0f };
    buildTrail(c, xs, 4);
    check(c.markCount() == 4, "four marks stored");

    // Within 20 units of the previous mark -> Footmarks::add rejects it.
    c.beetleTick(95.0f, 0.0f, 1.0f);
    check(c.markCount() == 4, "spacing filter skips a <20 unit step");

    // Far enough again -> stored.
    c.beetleTick(120.0f, 0.0f, 1.0f);
    check(c.markCount() == 5, "mark stored once spacing clears");
    check(near(c.footmarks().at(c.footmarks().mostRecentSlot()).x, 120.0f), "most recent mark at x=120");

    // Fill past capacity 10: oldest marks fall out of the recency window.
    P2FuefukiFollowController b;
    for (int i = 0; i < 12; i++) b.beetleTick(30.0f * static_cast<float>(i), 0.0f, 1.0f);
    check(b.markCount() == 10, "ring caps at 10 valid marks");
    const P2FuefukiFootmarks& fm = b.footmarks();
    check(near(fm.at(fm.mostRecentSlot()).x, 330.0f), "most recent is x=330");
    check(near(fm.at(fm.slotAt(9)).x, 60.0f), "oldest valid mark is x=60");
}

void testCadenceAt30Hz()
{
    P2FuefukiFollowController c;
    c.beetleTick(0.0f, 0.0f, kTick); // first update records immediately
    check(c.markCount() == 1, "first 30 Hz tick records a mark");
    c.beetleTick(30.0f, 0.0f, kTick); // 33 ms since last -> below 41.7 ms
    check(c.markCount() == 1, "second consecutive 30 Hz tick is not due");
    c.beetleTick(60.0f, 0.0f, kTick); // now > interval
    check(c.markCount() == 2, "mark recorded once the interval elapses");
    check(near(c.footmarks().at(c.footmarks().mostRecentSlot()).x, 60.0f), "recorded at x=60");

    // Malformed deltas must not mutate the trail.
    const int before = c.markCount();
    c.beetleTick(999.0f, 0.0f, -1.0f);
    c.beetleTick(999.0f, 0.0f, std::nanf(""));
    check(c.markCount() == before, "negative / NaN delta rejected");
}

void testClaimRelease()
{
    P2FuefukiFollowController c;
    check(c.followerCount() == 0, "starts empty");
    c.claim(5);
    c.claim(5);
    check(c.followerCount() == 1 && c.holds(5), "claim is idempotent");
    c.release(5);
    check(c.followerCount() == 0 && !c.holds(5), "release removes the follower");
    c.release(5); // no-op
    check(c.followerCount() == 0, "second release is harmless");

    // Unclaimed ids never emit a move.
    P2FuefukiFollowMove m = c.followerTick(9, 0, 0, 0, 0, 0, 0, kTick);
    check(!m.hasMove, "unclaimed pikmin gets no move");
}

void testParentToFootprintAndApproach()
{
    P2FuefukiFollowController c;
    const float xs[] = { 0.0f, 30.0f, 60.0f, 90.0f };
    buildTrail(c, xs, 4);
    c.claim(1);

    // Parent state with a zero timer: source sets velocity zero, then picks a
    // target. The scan walks recency->old and takes the first mark within 100
    // of the beetle (x=90): the oldest mark, x=0. No movement this tick.
    P2FuefukiFollowMove m0 = c.followerTick(1, 100.0f, 0.0f, 90.0f, 0.0f, 0.0f, 0.0f, kTick, rndZero);
    check(m0.hasMove && m0.stop, "parent tick stops and acquires a target");

    // Footprint state: move toward x=0 from x=100, near speed 0.5*rand+0.5.
    P2FuefukiFollowMove m1 = c.followerTick(1, 100.0f, 0.0f, 90.0f, 0.0f, 0.0f, 0.0f, kTick, rndZero);
    check(m1.hasMove && !m1.stop, "footprint tick emits movement");
    check(near(m1.speed, 0.5f), "near speed = 0.5*0.0+0.5");
    check(near(m1.dirX, -1.0f) && near(m1.dirZ, 0.0f), "unit direction toward target");

    // makeTarget consumes the random source on the parent tick; verify the
    // upper near-speed bound with a fresh controller seeded by randFloat()==1.
    P2FuefukiFollowController d;
    buildTrail(d, xs, 4);
    d.claim(1);
    d.followerTick(1, 100.0f, 0.0f, 90.0f, 0.0f, 0.0f, 0.0f, kTick, rndOne);
    P2FuefukiFollowMove m2 = d.followerTick(1, 100.0f, 0.0f, 90.0f, 0.0f, 0.0f, 0.0f, kTick, rndZero);
    check(near(m2.speed, 1.0f), "near speed = 0.5*1.0+0.5");
}

void testArrivalReturnsToParent()
{
    P2FuefukiFollowController c;
    const float xs[] = { 0.0f, 30.0f };
    buildTrail(c, xs, 2);
    c.claim(1);

    // tick1: parent -> target x=0 (oldest within 100 of beetle x=30).
    c.followerTick(1, 40.0f, 0.0f, 30.0f, 0.0f, 0.0f, 0.0f, kTick, rndZero);
    // tick2: within 50 of the target -> stop, back to parent, timer armed.
    P2FuefukiFollowMove m = c.followerTick(1, 40.0f, 0.0f, 30.0f, 0.0f, 0.0f, 0.0f, kTick, rndZero);
    check(m.hasMove && m.stop, "arrival stops the follower");
    // tick3: parent with a live timer and in-range beetle -> stays stopped.
    P2FuefukiFollowMove m2 = c.followerTick(1, 40.0f, 0.0f, 30.0f, 0.0f, 0.0f, 0.0f, kTick, rndZero);
    check(m2.hasMove && m2.stop, "parent timer keeps the follower stopped");
}

void testFarFollowerUsesFullSpeed()
{
    P2FuefukiFollowController c;
    const float xs[] = { 0.0f, 30.0f };
    buildTrail(c, xs, 2);
    c.claim(1);

    // piki x=150 -> distance 150 > FOLLOW_DISTANCE, full speed.
    c.followerTick(1, 150.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, kTick, rndZero);
    P2FuefukiFollowMove m = c.followerTick(1, 150.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, kTick, rndZero);
    check(m.hasMove && !m.stop, "far follower emits movement");
    check(near(m.speed, 1.0f), "far follower uses full speed");
    check(near(m.dirX, -1.0f), "far follower heads toward the trail");
}
} // namespace

int main()
{
    testFootmarkRingAndSpacing();
    testCadenceAt30Hz();
    testClaimRelease();
    testParentToFootprintAndApproach();
    testArrivalReturnsToParent();
    testFarFollowerUsesFullSpeed();

    if (gFailures == 0) {
        std::printf("PASS p2_fuefuki_follow_test\n");
        return 0;
    }
    std::printf("FAILURES: %d\n", gFailures);
    return 1;
}
