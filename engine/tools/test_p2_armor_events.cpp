// Standalone probe for the lane-08 Armor event-clock migration (#431).
//
// Build: g++ -std=c++17 -Wall -Wextra -Werror tools/test_p2_armor_events.cpp -o p2_armor_events.exe
//
// Proves that the Cloaking Burrow-nit (Armor) bite / eat-kill / flick effects are
// delivered from the authoritative sampled-animation clock exactly once across
// steady stepping, skipped frames, clip loops, pause, mid-clip interruption and
// actor-address reuse. No engine, GL or arena is required.
#include "../pc_port/pc_p2_armor_events.h"

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

using p2armorevents::Action;
using p2armorevents::Dispatched;
using p2armorevents::Receiver;

std::map<std::string, p2sampled::Clip> armorBank() {
    std::map<std::string, p2sampled::Clip> bank;
    for (const p2armorevents::Row& row : p2armorevents::armorRows()) {
        p2sampled::Clip clip = p2armorevents::makeClip(row);
        if (!clip.valid()) {
            std::fprintf(stderr, "FAIL invalid armor clip: %s\n", row.name.c_str());
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

// Steady one-frame stepping must deliver the bite once at the source frame.
void testSteadyBite() {
    const auto bank = armorBank();
    Receiver receiver;
    check(receiver.start(bank.at("attack2"), "attack2"), "attack2 start");

    std::vector<Dispatched> all;
    for (int frame = 0; frame < 40; ++frame) {
        for (const Dispatched& event : step(receiver, 1.0)) {
            all.push_back(event);
        }
    }
    check(count(all, Action::Bite) == 1, "steady: exactly one bite");
    check(!all.empty() && all.front().frame == 18, "steady: bite at source frame 18");
    check(receiver.generation() == 1, "steady: single generation");
}

// A frame skip that jumps straight past the bite frame must not lose it.
void testFrameSkip() {
    const auto bank = armorBank();
    Receiver receiver;
    check(receiver.start(bank.at("attack2"), "attack2"), "skip attack2 start");

    std::vector<Dispatched> out = step(receiver, 1.0);
    check(count(out, Action::Bite) == 0, "skip: no bite before the event frame");
    out = step(receiver, 39.0);  // one 39-frame jump from frame 1 past frame 18
    check(count(out, Action::Bite) == 1, "skip: bite delivered once across a large jump");
    check(!out.empty() && out.front().frame == 18, "skip: reported source frame 18");
}

// Eat-kill after a skipped attack2 must still be exactly once.
void testEatExactlyOnce() {
    const auto bank = armorBank();
    Receiver receiver;
    check(receiver.start(bank.at("eat"), "eat"), "eat start");
    std::vector<Dispatched> out = step(receiver, 200.0);
    check(count(out, Action::Eat) == 1, "eat: once across a huge skip");
    check(!out.empty() && out.front().frame == 60, "eat: source frame 60");
    out = step(receiver, 200.0);
    check(count(out, Action::Eat) == 0, "eat: one-shot does not refire");
}

// A looping clip fires its event once per cycle across continuous stepping.
void testLoopCycle() {
    p2armorevents::Row row;
    row.name = "attack2";
    row.sourceFrames = 10;
    row.poseCount = 2;
    row.loop = true;
    row.events = {{4, "2"}};
    Receiver receiver;
    check(receiver.start(p2armorevents::makeClip(row), "attack2"), "loop start");

    std::size_t fired = 0;
    for (int cycle = 0; cycle < 5; ++cycle) {
        fired += count(step(receiver, 10.0), Action::Bite);
    }
    check(fired == 5, "loop: one event per cycle over five cycles");

    // Wrap with a single large advance: 30 frames == 3 cycles -> 3 events.
    Receiver jumping;
    check(jumping.start(p2armorevents::makeClip(row), "attack2"), "loop jump start");
    check(count(step(jumping, 30.0), Action::Bite) == 3,
          "loop: one event per wrap across a skipped-cycles advance");
}

// Pause freezes the clock and must not accumulate catch-up.
void testPause() {
    const auto bank = armorBank();
    Receiver receiver;
    check(receiver.start(bank.at("flick"), "flick"), "pause flick start");
    receiver.pause(true);
    std::vector<Dispatched> out = step(receiver, 120.0);
    check(out.empty(), "pause: no event while paused");
    check(receiver.frame() == 0.0, "pause: clock frame holds");
    receiver.pause(false);
    out = step(receiver, 39.0);
    check(count(out, Action::Flick) == 1, "pause: flick fires once after resume");
}

// Interrupting attack2 before its event discards the pending bite; the new clip
// fires its own event, and restarting attack2 fires a fresh single bite.
void testInterruption() {
    const auto bank = armorBank();
    Receiver receiver;
    check(receiver.start(bank.at("attack2"), "attack2"), "interrupt attack2 start");
    check(count(step(receiver, 6.0), Action::Bite) == 0, "interrupt: no early bite");

    check(receiver.start(bank.at("eat"), "eat"), "interrupt into eat");
    std::vector<Dispatched> out = step(receiver, 65.0);
    check(count(out, Action::Bite) == 0, "interrupt: pending bite discarded");
    check(count(out, Action::Eat) == 1, "interrupt: eat delivered once");

    Receiver restarted;
    check(restarted.start(bank.at("attack2"), "attack2"), "re-enter attack2");
    check(count(step(restarted, 40.0), Action::Bite) == 1, "interrupt: new attack bites once");
}

// Reusing a receiver for a recycled actor address must not replay old events.
void testAddressReuse() {
    const auto bank = armorBank();
    Receiver receiver;
    check(receiver.start(bank.at("attack2"), "attack2"), "reuse first start");
    const std::uint64_t first = receiver.generation();
    check(count(step(receiver, 40.0), Action::Bite) == 1, "reuse first bite");

    // Recycled actor: start() again (same address) with no forget in between.
    check(receiver.start(bank.at("attack2"), "attack2"), "reuse second start");
    check(receiver.generation() > first, "reuse: generation advanced");
    check(count(step(receiver, 15.0), Action::Bite) == 0, "reuse: no stale bite replay");
    check(count(step(receiver, 25.0), Action::Bite) == 1, "reuse: fresh bite once");
}

// Visual loop-bound events (types 0/1/3) never map to gameplay actions.
void testVisualEventsIgnored() {
    const auto bank = armorBank();
    Receiver receiver;
    check(receiver.start(bank.at("move"), "move"), "move start");
    std::vector<Dispatched> out;
    for (int i = 0; i < 10; ++i) {
        for (const Dispatched& event : step(receiver, 4.0)) {
            out.push_back(event);
        }
    }
    check(out.empty(), "visual-only loop emits no gameplay action");
}

}  // namespace

int main() {
    testSteadyBite();
    testFrameSkip();
    testEatExactlyOnce();
    testLoopCycle();
    testPause();
    testInterruption();
    testAddressReuse();
    testVisualEventsIgnored();
    if (failures == 0) {
        std::printf("PASS p2_armor_events\n");
        return 0;
    }
    std::fprintf(stderr, "FAIL p2_armor_events: %d failures\n", failures);
    return 1;
}
