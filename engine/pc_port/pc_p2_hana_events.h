#pragma once
// Lane-08 second consumer: drive the Creeping Chrysanthemum (Hana, EnemyID 84)
// gameplay effects (bite capture + attackNavi, swallow kill + White-Pikmin
// poison, flick knockback) from the authoritative #431 sampled-animation clock
// instead of a per-state wall-time counter (stateTime * 30 + a fired-frame set).
// See docs/PIKMIN2_SAMPLED_CLOCK_EVENTS.md and docs/PIKMIN2_ARMOR_EVENT_CLOCK.md.
//
// The source `enemyanimmgr.txt` records frame events with a type: 0/1 are visual
// loop bounds, 2 is the damage/attack event and 3 is the swallow event
// (docs/PIKMIN2_GROUND_INVERTEBRATE_ASSETS.md:83). Hana authors 18:2 (bite +
// attackNavi) and 71:3 (swallow + fp02 poison) in `attack1`, and 50:2 (flick
// knockback) in `flick`. Timing comes only from crossed events, never the
// displayed pose, so skipped frames, pause, interruption and actor recycling
// cannot duplicate or drop the effect.
#include "pc_p2_sampled_clock.h"

#include <cstdint>
#include <string>
#include <vector>

namespace p2hanaevents {

// One authored p2-ground-bank.txt clip row: source length, uniform pose count,
// loop flag and the "frame:type" events. The bank is count-only, so the clock
// keeps uniform sampling and Clock::poseIndex() reproduces the legacy selector.
struct Row {
    std::string name;
    int sourceFrames = 0;
    int poseCount = 0;
    bool loop = false;
    std::vector<p2sampled::Event> events;
};

inline p2sampled::Clip makeClip(const Row& row) {
    p2sampled::Clip clip;
    clip.poses.name = row.name;
    clip.poses.count = row.poseCount > 0 ? row.poseCount : 1;
    int duration = row.sourceFrames;
    if (duration < 2) {
        duration = row.poseCount >= 2 ? row.poseCount : 2;
    }
    clip.poses.duration = duration;
    clip.events = row.events;
    clip.loopBegin = 0.0;
    clip.loopEnd = row.loop ? double(duration) : -1.0;
    return clip;
}

// Gameplay roles carried by a source animation event. Unlike the Armor reference
// (which only dispatches type 2), Hana's swallow rides event type 3
// (KEYEVENT_3), so this receiver has a dedicated Swallow action.
enum class Action { None, Bite, Swallow, Flick };

inline Action actionFor(const std::string& clip, const std::string& key) {
    if (clip == "attack1") {
        if (key == "2") return Action::Bite;
        if (key == "3") return Action::Swallow;
    }
    if (clip == "flick" && key == "2") return Action::Flick;
    return Action::None;
}

struct Dispatched {
    Action action = Action::None;
    int frame = 0;
    std::uint64_t cycle = 0;
};

// One actor's authoritative clock. start() on a clip change bumps the clock
// generation, cancelling the previous clip's outstanding events; advance()
// returns every crossed gameplay action exactly once per crossing.
class Receiver {
public:
    bool start(const p2sampled::Clip& clip, const std::string& clipName) {
        clip_ = clipName;
        active_ = clock_.start(clip);
        return active_;
    }

    void cancel() {
        active_ = false;
        clip_.clear();
        clock_.cancel();
    }

    bool active() const { return active_; }
    const std::string& clip() const { return clip_; }
    std::uint64_t generation() const { return clock_.generation(); }
    double frame() const { return clock_.frame(); }
    void pause(bool paused) { clock_.pause(paused); }

    // Advance by `dtSeconds` of simulation time at `fps` source frames/second.
    // Non-positive deltas and paused clocks consume nothing. A budget rejection
    // (too many wraps in one call) deactivates the clock rather than emitting a
    // partial event set.
    std::vector<Dispatched> advance(double dtSeconds, double fps = 30.0) {
        std::vector<Dispatched> out;
        if (!active_ || !(dtSeconds > 0.0) || !(fps > 0.0)) {
            return out;
        }
        p2sampled::Batch batch = clock_.advance(dtSeconds * fps);
        if (!batch) {
            active_ = false;
            return out;
        }
        for (const p2sampled::Occurrence& event : batch.events) {
            const Action action = actionFor(clip_, event.key);
            if (action != Action::None) {
                Dispatched dispatched;
                dispatched.action = action;
                dispatched.frame = event.frame;
                dispatched.cycle = event.cycle;
                out.push_back(dispatched);
            }
        }
        return out;
    }

private:
    p2sampled::Clock clock_;
    std::string clip_;
    bool active_ = false;
};

// The source Hana event table (docs/PIKMIN2_GROUND_INVERTEBRATE_ASSETS.md:83 and
// experimental/pikmin2_ground_inverts_assets.py EXPECTED_EVENTS['Hana']), kept
// here so the standalone probe shares the consumer's authoritative mapping. The
// consumed table is read from the generated p2-ground-bank.txt at setup() time;
// these durations are valid representative values for the engine-free probe only.
inline std::vector<Row> hanaRows() {
    return {
        {"attack1", 80, 2, false, {{18, "2"}, {71, "3"}}},
        {"dead", 60, 2, false, {}},
        {"flick", 55, 2, false, {{50, "2"}}},
        {"move1", 45, 2, true, {{10, "0"}, {40, "1"}}},
        {"type1", 130, 2, false, {{27, "2"}, {30, "0"}, {100, "1"}, {103, "3"}, {120, "4"}}},
        {"type5", 35, 2, false, {{10, "0"}, {30, "1"}}},
        {"wait2", 30, 2, true, {}},
        {"waitact1", 45, 2, false, {{10, "0"}, {40, "1"}}},
        {"attack2", 70, 2, false, {{24, "2"}, {62, "3"}}},
    };
}

}  // namespace p2hanaevents
