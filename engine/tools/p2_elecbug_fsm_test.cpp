// Exit-condition test for the Anode Beetle recovery (owner playtest: stuck in a
// recover/charge loop). Uses the real converted-bank key events for the clips.
#include "pc_p2_elecbug_fsm.h"
#include <cassert>
#include <cstdio>

using namespace p2elecbug;

int main() {
    // Bank rows: "turn 70 30:0,69:1" and "recover 30 -" (no key events at all).
    const ClipKeys turn = parseKeys(70, "30:0,69:1");
    const ClipKeys recover = parseKeys(30, "-");
    assert(turn.loopStart == 30 && turn.end == 69);
    assert(recover.loopStart < 0 && recover.end < 0);

    // The flipped beetle stays in the Turn clip for the whole FlipTime (5 s), looping
    // belly-up inside frames 30..69, and is not finished early.
    for (float t = 0.0f; t < 5.0f; t += 0.05f) {
        const ReverseClip r = reverseClip(turn, t, 5.0f);
        assert(!r.finished);
        assert(r.frame >= 0.0f && r.frame < 69.01f);
        if (t * kFps >= 30.0f) assert(r.frame >= 29.99f);
    }
    // After FlipTime it runs on to the END key and then finishes (bounded wait).
    bool finished = false;
    float finishedAt = 0.0f;
    for (float t = 5.0f; t < 8.0f; t += 0.01f) {
        if (reverseClip(turn, t, 5.0f).finished) { finished = true; finishedAt = t; break; }
    }
    assert(finished);
    assert(finishedAt < 5.0f + 40.0f / kFps + 0.05f);

    // Recover has no END key: the exit must be the clip length, exactly once.
    assert(!recoverDone(0.0f, 30));
    assert(!recoverDone(0.99f, 30));
    assert(recoverDone(1.0f, 30));
    // A missing clip falls back to 1 s rather than never exiting.
    assert(recoverDone(1.0f, 0));

    // Charge is driven by the inactivity timer, not by sight.
    assert(!chargeDue(0.0f) && !chargeDue(15.0f) && chargeDue(15.01f));
    // Source checkInteract band: beetles 200 apart on X, segment a->b.
    const V3 a{0, 0, 0}, b{200, 0, 0};
    assert(inArcBand(a, b, V3{100, 0, 0}));    // on the arc
    assert(inArcBand(a, b, V3{100, 10, 9}));   // inside |vertical|<15, |lateral|<10
    assert(!inArcBand(a, b, V3{100, 0, 12}));  // outside lateral 10
    assert(!inArcBand(a, b, V3{100, 20, 0}));  // outside vertical 15
    assert(!inArcBand(a, b, V3{-5, 0, 0}));    // behind the discharger
    assert(!inArcBand(a, b, V3{205, 0, 0}));   // beyond the partner
    assert(kArcStart > 0.26f && kArcStart < 0.27f); // frame 8 at 30 fps
    std::puts("p2_elecbug_fsm_test PASS");
    return 0;
}
