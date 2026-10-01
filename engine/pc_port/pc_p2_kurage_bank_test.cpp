// Engine-free tests for the Jellyfloat pose-bank profile (#972).
#include "pc_p2_kurage_bank.h"
#include <cassert>
#include <cmath>
#include <sstream>

static bool parses(const char* text, p2kuragebank::Profile& out) {
    std::istringstream in(text);
    return p2kuragebank::parse(in, out);
}
static bool near(float a, float b) { return std::fabs(a - b) < 1e-4f; }

int main() {
    p2kuragebank::Profile p;
    // Two clips: wait 35 frames with 3 poses, attack 120 frames with 2 poses.
    const char* good =
        "P2_KURAGE_ANIMATION_1\n"
        "wait 3 35 0 17 34 0 10 0  0 20 0  0 10 0\n"
        "attack 2 120 0 119 0 0 0  0 100 0\n";
    assert(parses(good, p));
    assert(p.clips.size() == 2);
    const p2kuragebank::Clip* wait = p.find("wait");
    assert(wait && wait->duration == 35 && wait->frames.size() == 3 && wait->proom.size() == 3);
    assert(!p.find("missing"));

    // Clamped at both ends, exact on a pose, linear between poses.
    assert(near(p2kuragebank::proomAt(*wait, -5.f)[1], 10.f));
    assert(near(p2kuragebank::proomAt(*wait, 0.f)[1], 10.f));
    assert(near(p2kuragebank::proomAt(*wait, 17.f)[1], 20.f));
    assert(near(p2kuragebank::proomAt(*wait, 8.5f)[1], 15.f));
    assert(near(p2kuragebank::proomAt(*wait, 25.5f)[1], 15.f));
    assert(near(p2kuragebank::proomAt(*wait, 34.f)[1], 10.f));
    assert(near(p2kuragebank::proomAt(*wait, 99.f)[1], 10.f));
    const p2kuragebank::Clip* attack = p.find("attack");
    assert(near(p2kuragebank::proomAt(*attack, 59.5f)[1], 50.f));

    // #1065 corpse pose: the flattest visible pose of the death clip, rested on
    // the ground. Rows are the converted OniKurage dead1 bounds (minY, maxY,
    // width): drop, squash flat at f41, swell/thrash, collapse to a point at f95.
    {
        using p2kuragebank::Extent;
        const std::vector<Extent> dead1 = {
            {-3, 93, 91}, {-21, 60, 114}, {33, 125, 63}, {62, 198, 79}, {-5, 95, 112}, {-20, 59, 124},
            {-21, 39, 132}, {-23, 24, 135}, {-29, 20, 115}, {100, 209, 95}, {-75, 7, 103}, {-35, 81, 83},
            {88, 88, 0}};
        assert(p2kuragebank::settledIndex(dead1) == 7);              // f41: 47 units tall, 135 wide
        assert(near(p2kuragebank::groundLift(dead1[7]), 23.f));       // lowest vertex to the ground
        // The point the burst leaves (zero extent) is never chosen, even though it is "flattest".
        assert(p2kuragebank::settledIndex({{88, 88, 0}, {0, 50, 10}}) == 1);
        // Nothing visible: no settled pose (caller keeps its fallback).
        assert(p2kuragebank::settledIndex({{5, 5, 0}, {1, 1.5f, 0.5f}}) == -1);
        assert(p2kuragebank::settledIndex({}) == -1);
        // A pose resting above the origin is lowered, never left floating.
        assert(near(p2kuragebank::groundLift({47, 78, 89}), -47.f));
        // Ties keep the earlier pose (the first moment the bell lies flat).
        assert(p2kuragebank::settledIndex({{0, 20, 10}, {0, 20, 10}}) == 0);
    }

    // Every malformed profile is rejected whole.
    const char* bad[] = {
        "",                                                        // empty
        "P2_KURAGE_ANIMATION_2\nwait 2 35 0 34 0 0 0 0 0 0\n",     // wrong magic
        "P2_KURAGE_ANIMATION_1\n",                                 // no clips
        "P2_KURAGE_ANIMATION_1\nwait 2 35 1 34 0 0 0 0 0 0\n",     // first frame not 0
        "P2_KURAGE_ANIMATION_1\nwait 2 35 0 33 0 0 0 0 0 0\n",     // last frame not duration-1
        "P2_KURAGE_ANIMATION_1\nwait 3 35 0 20 20 0 0 0 0 0 0 0 0 0\n", // not strictly rising
        "P2_KURAGE_ANIMATION_1\nwait 2 35 0 34 0 0 0\n",           // missing proom values
        "P2_KURAGE_ANIMATION_1\nwait 1 35 0 0 0 0\n",              // fewer than two poses
        "P2_KURAGE_ANIMATION_1\nwait 2 35 0 34 0 0 0 0 0 nan\n",   // non-finite
        "P2_KURAGE_ANIMATION_1\nWait 2 35 0 34 0 0 0 0 0 0\n",     // bad clip name
        "P2_KURAGE_ANIMATION_1\nwait 2 35 0 34 0 0 0 0 0 0\nwait 2 35 0 34 0 0 0 0 0 0\n", // duplicate clip
        "P2_KURAGE_ANIMATION_1\nwait 65 99 0\n",                   // pose count over the cap
    };
    for (const char* text : bad) {
        p2kuragebank::Profile q;
        assert(!parses(text, q));
        assert(q.clips.empty());
    }
    return 0;
}
