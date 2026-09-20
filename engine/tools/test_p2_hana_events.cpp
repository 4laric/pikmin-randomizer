// Standalone probe for the lane-08 Hana event-clock migration (#431).
//
// Build: g++ -std=c++17 -Wall -Wextra -Werror tools/test_p2_hana_events.cpp -o p2_hana_events.exe
//
// Proves that the Creeping Chrysanthemum (Hana) bite / swallow(-poison) / flick
// effects are delivered from the authoritative sampled-animation clock exactly
// once across steady stepping, skipped frames, clip loops, pause, mid-clip
// interruption and actor-address reuse. No engine, GL or arena is required.
#include "../pc_port/pc_p2_hana_events.h"

#include <cstdio>
#include <map>
#include <string>
#include <vector>

namespace {

int failures = 0;

bool check(bool ok, const char* what) {
    if (!ok) {
        std::fprintf(stderr, "FAIL %s\n", what);
        ++failures;
    }
    return ok;
}

using p2hanaevents::Action;
using p2hanaevents::Dispatched;
using p2hanaevents::Receiver;

std::map<std::string, p2sampled::Clip> hanaBank() {
    std::map<std::string, p2sampled::Clip> bank;
    for (const p2hanaevents::Row& row : p2hanaevents::hanaRows()) {
        p2sampled::Clip clip = p2hanaevents::makeClip(row);
        if (!clip.valid()) {
            std::fprintf(stderr, "FAIL invalid hana clip: %s\n", row.name.c_str());
            ++failures;
        }
        bank[row.name] = clip;
    }
    return bank;
}

std::size_t count(const std::vector<Dispatched>& out, Action action) {
    std::size_t n = 0;
    for (const Dispatched& event : out) {
        if (event.action == action) {
            ++n;
        }
    }
    return n;
}

std::vector<Dispatched> step(Receiver& receiver, double frames, double fps = 30.0) {
    return receiver.advance(frames / fps, fps);
}

// Steady one-frame stepping must deliver the bite (frame 18) then the swallow
// (frame 71) once each, in source order.
void testSteadyBiteSwallow() {
    const auto bank = hanaBank();
    Receiver receiver;
    check(receiver.start(bank.at("attack1"), "attack1"), "attack1 start");

    std::vector<Dispatched> all;
    for (int frame = 0; frame < 80; ++frame) {
        for (const Dispatched& event : step(receiver, 1.0)) {
            all.push_back(event);
        }
    }
    check(count(all, Action::Bite) == 1, "steady: exactly one bite");
    check(count(all, Action::Swallow) == 1, "steady: exactly one swallow");
    check(!all.empty() && all.front().action == Action::Bite && all.front().frame == 18,
          "steady: bite first at source frame 18");
    check(all.size() == 2 && all.back().action == Action::Swallow && all.back().frame == 71,
          "steady: swallow second at source frame 71");
    check(receiver.generation() == 1, "steady: single generation");
}

// A frame skip that jumps straight past both event frames must not lose either,
// and must report the exact source frames (18 / 71), not the catch-up wall time.
void testFrameSkip() {
    const auto bank = hanaBank();
    Receiver receiver;
    check(receiver.start(bank.at("attack1"), "attack1"), "skip attack1 start");

    std::vector<Dispatched> out = step(receiver, 1.0);
    check(count(out, Action::Bite) == 0, "skip: no bite before the event frame");
    out = step(receiver, 79.0);  // one jump from frame 1 past 71
    check(count(out, Action::Bite) == 1, "skip: bite delivered once across a large jump");
    check(count(out, Action::Swallow) == 1, "skip: swallow delivered once across a large jump");
    check(out.size() == 2 && out[0].action == Action::Bite && out[0].frame == 18
              && out[1].action == Action::Swallow && out[1].frame == 71,
          "skip: source order 18 bite then 71 swallow");
}

// A one-shot attack1 must not refire after it completes.
void testOneShotNoRefire() {
    const auto bank = hanaBank();
    Receiver receiver;
    check(receiver.start(bank.at("attack1"), "attack1"), "one-shot start");
    std::vector<Dispatched> out = step(receiver, 200.0);
    check(count(out, Action::Bite) == 1 && count(out, Action::Swallow) == 1,
          "one-shot: bite + swallow once across a huge skip");
    out = step(receiver, 200.0);
    check(count(out, Action::Bite) == 0 && count(out, Action::Swallow) == 0,
          "one-shot: does not refire");
}

// A looping clip fires its event once per cycle across continuous stepping.
void testLoopCycle() {
    p2hanaevents::Row row;
    row.name = "attack1";
    row.sourceFrames = 10;
    row.poseCount = 2;
    row.loop = true;
    row.events = {{4, "2"}};
    Receiver receiver;
    check(receiver.start(p2hanaevents::makeClip(row), "attack1"), "loop start");

    std::size_t fired = 0;
    for (int cycle = 0; cycle < 5; ++cycle) {
        fired += count(step(receiver, 10.0), Action::Bite);
    }
    check(fired == 5, "loop: one event per cycle over five cycles");

    Receiver jumping;
    check(jumping.start(p2hanaevents::makeClip(row), "attack1"), "loop jump start");
    check(count(step(jumping, 30.0), Action::Bite) == 3,
          "loop: one event per wrap across a skipped-cycles advance");
}

// Pause freezes the clock and must not accumulate catch-up.
void testPause() {
    const auto bank = hanaBank();
    Receiver receiver;
    check(receiver.start(bank.at("flick"), "flick"), "pause flick start");
    receiver.pause(true);
    std::vector<Dispatched> out = step(receiver, 120.0);
    check(out.empty(), "pause: no event while paused");
    check(receiver.frame() == 0.0, "pause: clock frame holds");
    receiver.pause(false);
    out = step(receiver, 55.0);
    check(count(out, Action::Flick) == 1, "pause: flick fires once after resume");
}

// Interrupting attack1 after the bite but before the swallow discards the
// pending swallow; the new clip fires its own event and a fresh attack1 fires a
// fresh single bite + swallow.
void testInterruption() {
    const auto bank = hanaBank();
    Receiver receiver;
    check(receiver.start(bank.at("attack1"), "attack1"), "interrupt attack1 start");
    std::vector<Dispatched> out = step(receiver, 20.0);
    check(count(out, Action::Bite) == 1, "interrupt: bite fired before the swallow frame");
    check(count(out, Action::Swallow) == 0, "interrupt: no swallow before frame 71");

    check(receiver.start(bank.at("flick"), "flick"), "interrupt into flick");
    out = step(receiver, 55.0);
    check(count(out, Action::Swallow) == 0, "interrupt: pending swallow discarded");
    check(count(out, Action::Flick) == 1, "interrupt: flick delivered once");

    Receiver restarted;
    check(restarted.start(bank.at("attack1"), "attack1"), "re-enter attack1");
    out = step(restarted, 90.0);
    check(count(out, Action::Bite) == 1 && count(out, Action::Swallow) == 1,
          "interrupt: new attack bites and swallows once each");
}

// Reusing a receiver for a recycled actor address must not replay old events.
void testAddressReuse() {
    const auto bank = hanaBank();
    Receiver receiver;
    check(receiver.start(bank.at("attack1"), "attack1"), "reuse first start");
    const std::uint64_t first = receiver.generation();
    std::vector<Dispatched> out = step(receiver, 90.0);
    check(count(out, Action::Bite) == 1 && count(out, Action::Swallow) == 1,
          "reuse first bite+swallow");

    check(receiver.start(bank.at("attack1"), "attack1"), "reuse second start");
    check(receiver.generation() > first, "reuse: generation advanced");
    out = step(receiver, 17.0);
    check(count(out, Action::Bite) == 0, "reuse: no stale bite replay");
    out = step(receiver, 80.0);
    check(count(out, Action::Bite) == 1 && count(out, Action::Swallow) == 1,
          "reuse: fresh bite+swallow once");
}

// Clip names other than attack1/flick never map to gameplay actions,
// including type1 whose authored type-2/type-3 events are non-gameplay.
void testVisualEventsIgnored() {
    const auto bank = hanaBank();
    for (const char* name : {"type1", "move1", "type5", "wait2", "waitact1", "dead"}) {
        Receiver receiver;
        check(receiver.start(bank.at(name), name), "visual clip start");
        std::vector<Dispatched> out;
        for (int i = 0; i < 10; ++i) {
            for (const Dispatched& event : step(receiver, 20.0)) {
                out.push_back(event);
            }
        }
        check(out.empty(), "visual-only clip emits no gameplay action");
    }
}

// A single large advance (the runtime anti-hitch clamp now caps one tick at 0.5s,
// but a 2s hitch is exactly the kind of delta the clock must handle) delivers the
// crossed bite exactly once and does not invent a swallow before frame 71.
void testTwoSecondHitch() {
    const auto bank = hanaBank();
    Receiver receiver;
    check(receiver.start(bank.at("attack1"), "attack1"), "hitch attack1 start");

    std::vector<Dispatched> out = receiver.advance(2.0, 30.0);  // 60 source frames
    check(count(out, Action::Bite) == 1, "hitch: bite delivered once across 2s");
    check(count(out, Action::Swallow) == 0, "hitch: swallow not yet crossed");

    out = receiver.advance(1.0, 30.0);  // 60 -> 90 source frames
    check(count(out, Action::Swallow) == 1, "hitch: swallow delivered once on resume");
    out = receiver.advance(1.0, 30.0);
    check(out.empty(), "hitch: one-shot does not refire");
}

}  // namespace

int main() {
    testSteadyBiteSwallow();
    testFrameSkip();
    testOneShotNoRefire();
    testLoopCycle();
    testPause();
    testInterruption();
    testAddressReuse();
    testVisualEventsIgnored();
    testTwoSecondHitch();
    if (failures == 0) {
        std::printf("PASS p2_hana_events\n");
        return 0;
    }
    std::fprintf(stderr, "FAIL p2_hana_events: %d failures\n", failures);
    return 1;
}
