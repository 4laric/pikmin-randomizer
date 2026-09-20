// Standalone probe for the lane-08 Catfish event-clock migration (#431).
//
// Build: g++ -std=c++17 -Wall -Wextra -Werror tools/test_p2_catfish_events.cpp -o p2_catfish_events.exe
//
// Proves that the Water Dumple (Catfish) bite / swallow(-poison) / flick
// knockback / restore effects are delivered from the authoritative
// sampled-animation clock exactly once across steady stepping, skipped frames,
// clip loops, pause, a large hitch, mid-clip interruption and actor-address
// reuse. No engine, GL or arena is required.
#include "../pc_port/pc_p2_catfish_events.h"

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

using p2catfishevents::Action;
using p2catfishevents::Dispatched;
using p2catfishevents::Receiver;

std::map<std::string, p2sampled::Clip> catfishBank() {
    std::map<std::string, p2sampled::Clip> bank;
    for (const p2catfishevents::Row& row : p2catfishevents::catfishRows()) {
        p2sampled::Clip clip = p2catfishevents::makeClip(row);
        if (!clip.valid()) {
            std::fprintf(stderr, "FAIL invalid catfish clip: %s\n", row.name.c_str());
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

// Steady one-frame stepping must deliver the bite (frame 17) then the swallow
// (frame 75) once each, in source order.
void testSteadyBiteSwallow() {
    const auto bank = catfishBank();
    Receiver receiver;
    check(receiver.start(bank.at("attack"), "attack"), "attack start");

    std::vector<Dispatched> all;
    for (int frame = 0; frame < 90; ++frame) {
        for (const Dispatched& event : step(receiver, 1.0)) {
            all.push_back(event);
        }
    }
    check(count(all, Action::Bite) == 1, "steady: exactly one bite");
    check(count(all, Action::Swallow) == 1, "steady: exactly one swallow");
    check(all.size() == 2 && all.front().action == Action::Bite && all.front().frame == 17
              && all.back().action == Action::Swallow && all.back().frame == 75,
          "steady: source order 17 bite then 75 swallow");
    check(receiver.generation() == 1, "steady: single generation");
}

// A frame skip that jumps straight past both event frames must not lose either,
// and must report the exact source frames (17 / 75), not the catch-up wall time.
void testFrameSkip() {
    const auto bank = catfishBank();
    Receiver receiver;
    check(receiver.start(bank.at("attack"), "attack"), "skip attack start");

    std::vector<Dispatched> out = step(receiver, 1.0);
    check(count(out, Action::Bite) == 0, "skip: no bite before the event frame");
    out = step(receiver, 90.0);
    check(count(out, Action::Bite) == 1, "skip: bite delivered once across a large jump");
    check(count(out, Action::Swallow) == 1, "skip: swallow delivered once across a large jump");
    check(out.size() == 2 && out[0].action == Action::Bite && out[0].frame == 17
              && out[1].action == Action::Swallow && out[1].frame == 75,
          "skip: source order 17 bite then 75 swallow");
}

// A one-shot attack must not refire after it completes.
void testOneShotNoRefire() {
    const auto bank = catfishBank();
    Receiver receiver;
    check(receiver.start(bank.at("attack"), "attack"), "one-shot start");
    std::vector<Dispatched> out = step(receiver, 200.0);
    check(count(out, Action::Bite) == 1 && count(out, Action::Swallow) == 1,
          "one-shot: bite + swallow once across a huge skip");
    out = step(receiver, 200.0);
    check(count(out, Action::Bite) == 0 && count(out, Action::Swallow) == 0,
          "one-shot: does not refire");
}

// The flick clip authors knockback (frame 25) then restore (frame 47), once each.
void testFlickKnockbackRestore() {
    const auto bank = catfishBank();
    Receiver receiver;
    check(receiver.start(bank.at("flick"), "flick"), "flick start");

    std::vector<Dispatched> out = step(receiver, 60.0);  // jump 0 -> 60
    check(count(out, Action::Flick) == 1 && out.size() == 2
              && out[0].action == Action::Flick && out[0].frame == 25
              && out[1].action == Action::FlickRestore && out[1].frame == 47,
          "flick: knockback 25 then restore 47, once each across a skip");
    out = step(receiver, 60.0);
    check(out.empty(), "flick: one-shot does not refire");
}

// A looping clip fires its event once per cycle across continuous stepping.
void testLoopCycle() {
    p2catfishevents::Row row;
    row.name = "attack";
    row.sourceFrames = 10;
    row.poseCount = 2;
    row.loop = true;
    row.events = {{4, "2"}};
    Receiver receiver;
    check(receiver.start(p2catfishevents::makeClip(row), "attack"), "loop start");

    std::size_t fired = 0;
    for (int cycle = 0; cycle < 5; ++cycle) {
        fired += count(step(receiver, 10.0), Action::Bite);
    }
    check(fired == 5, "loop: one event per cycle over five cycles");

    Receiver jumping;
    check(jumping.start(p2catfishevents::makeClip(row), "attack"), "loop jump start");
    check(count(step(jumping, 30.0), Action::Bite) == 3,
          "loop: one event per wrap across a skipped-cycles advance");
}

// Pause freezes the clock and must not accumulate catch-up.
void testPause() {
    const auto bank = catfishBank();
    Receiver receiver;
    check(receiver.start(bank.at("flick"), "flick"), "pause flick start");
    receiver.pause(true);
    std::vector<Dispatched> out = step(receiver, 120.0);
    check(out.empty(), "pause: no event while paused");
    check(receiver.frame() == 0.0, "pause: clock frame holds");
    receiver.pause(false);
    out = step(receiver, 60.0);
    check(count(out, Action::Flick) == 1 && count(out, Action::FlickRestore) == 1,
          "pause: knockback + restore fire once after resume");
}

// Interrupting attack after the bite but before the swallow discards the
// pending swallow; the new clip fires its own events and a fresh attack fires a
// fresh single bite + swallow.
void testInterruption() {
    const auto bank = catfishBank();
    Receiver receiver;
    check(receiver.start(bank.at("attack"), "attack"), "interrupt attack start");
    std::vector<Dispatched> out = step(receiver, 20.0);
    check(count(out, Action::Bite) == 1, "interrupt: bite fired before the swallow frame");
    check(count(out, Action::Swallow) == 0, "interrupt: no swallow before frame 75");

    check(receiver.start(bank.at("flick"), "flick"), "interrupt into flick");
    out = step(receiver, 60.0);
    check(count(out, Action::Swallow) == 0, "interrupt: pending swallow discarded");
    check(count(out, Action::Flick) == 1 && count(out, Action::FlickRestore) == 1,
          "interrupt: flick knockback + restore delivered once");

    Receiver restarted;
    check(restarted.start(bank.at("attack"), "attack"), "re-enter attack");
    out = step(restarted, 90.0);
    check(count(out, Action::Bite) == 1 && count(out, Action::Swallow) == 1,
          "interrupt: new attack bites and swallows once each");
}

// Reusing a receiver for a recycled actor address must not replay old events.
void testAddressReuse() {
    const auto bank = catfishBank();
    Receiver receiver;
    check(receiver.start(bank.at("attack"), "attack"), "reuse first start");
    const std::uint64_t first = receiver.generation();
    std::vector<Dispatched> out = step(receiver, 90.0);
    check(count(out, Action::Bite) == 1 && count(out, Action::Swallow) == 1,
          "reuse first bite+swallow");

    check(receiver.start(bank.at("attack"), "attack"), "reuse second start");
    check(receiver.generation() > first, "reuse: generation advanced");
    out = step(receiver, 16.0);
    check(count(out, Action::Bite) == 0, "reuse: no stale bite replay");
    out = step(receiver, 80.0);
    check(count(out, Action::Bite) == 1 && count(out, Action::Swallow) == 1,
          "reuse: fresh bite+swallow once");
}

// Clip names other than attack/flick never map to gameplay actions, including
// type5 whose type-2/type-3 loop-bound events are non-gameplay.
void testVisualEventsIgnored() {
    const auto bank = catfishBank();
    for (const char* name : {"move1", "type5", "wait1", "waitact2", "dead"}) {
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
// crossed bite exactly once and does not invent a swallow before frame 75.
void testTwoSecondHitch() {
    const auto bank = catfishBank();
    Receiver receiver;
    check(receiver.start(bank.at("attack"), "attack"), "hitch attack start");

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
    testFlickKnockbackRestore();
    testLoopCycle();
    testPause();
    testInterruption();
    testAddressReuse();
    testVisualEventsIgnored();
    testTwoSecondHitch();
    if (failures == 0) {
        std::printf("PASS p2_catfish_events\n");
        return 0;
    }
    std::fprintf(stderr, "FAIL p2_catfish_events: %d failures\n", failures);
    return 1;
}
