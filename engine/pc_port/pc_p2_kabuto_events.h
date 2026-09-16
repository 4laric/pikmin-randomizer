#pragma once

#include "pc_p2_kabuto_cannon.h"
#include "pc_p2_sampled_clock.h"

#include <string>

// Family event adapter for the Cannon Beetle fire FSM (lane 20, #169 / #424).
//
// It consumes the shared sampled-animation clock/event contract (#431,
// `pc_p2_sampled_clock.h`) rather than a synthetic tick counter, so Kabuto
// attacks fire on the authoritative source frame with the shared exactly-once,
// loop, pause and one-shot semantics. The clock owns timing; this adapter owns
// the Kabuto key vocabulary and the motion-end event:
//
//   * an authored event whose key equals `key2Key` (source `KEYEVENT_2`) maps to
//     `P2KabutoEvent::Key2`;
//   * the one-shot motion end maps to `P2KabutoEvent::End`, emitted exactly once.
//
// The host must call `P2KabutoCannon::onEvent` once per returned event, in order,
// and must not advance the clock while the FSM has a pending birth it has not
// consumed. No engine, creature, map, sound or effect dependency; no shared
// hooks.

// Builds the one-shot attack clip the adapter expects: `duration` source frames,
// a single authored KEYEVENT_2 at `fireFrame`, no loop. An out-of-range
// `fireFrame`/`duration` yields an invalid clip so `begin` fails closed.
p2sampled::Clip p2_kabuto_attack_clip(int duration, int fireFrame, const char* name,
                                      const char* key2Key);

class P2KabutoEventAdapter {
public:
    // Start a motion. `clip` must pass the shared `p2sampled::Clip::valid()`
    // contract (one-shot or looping). Returns false and leaves the adapter
    // inactive on an invalid clip or empty key.
    bool begin(const p2sampled::Clip& clip, const char* key2Key = "key2");
    bool restart();
    void pause(bool paused);
    bool active() const { return mActive; }
    bool finished() const { return mActive && mClock.finished(); }
    double frame() const { return mClock.frame(); }
    std::size_t poseIndex() const { return mClock.poseIndex(); }
    std::uint64_t generation() const { return mClock.generation(); }
    std::uint64_t cycle() const { return mClock.cycle(); }

    // Advance by `sourceFrames` and write the FSM events crossed, in source
    // order, into `out` (at most `capacity`). `count` is always reset. Returns
    // false on an invalid advance, an inactive clock, or if more than `capacity`
    // events would be produced (so a caller can never silently drop an event).
    bool advance(double sourceFrames, P2KabutoEvent* out, int capacity, int& count);

private:
    p2sampled::Clock mClock;
    std::string mKey2 = "key2";
    bool mActive = false;
    bool mEndEmitted = false;
};
