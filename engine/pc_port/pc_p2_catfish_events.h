#pragma once
// Lane-08 consumer migration: drive the Water Dumple (Catfish, EnemyID 26)
// gameplay effects (attack bite capture + attackNavi, swallow kill + White
// poison, flick knockback + non-stone restore) from the authoritative #431
// sampled-animation clock instead of a per-state wall-time counter (a
// `stateTime >= frame/30` test plus a fired-frame set). See
// docs/PIKMIN2_SAMPLED_CLOCK_EVENTS.md and docs/PIKMIN2_ARMOR_EVENT_CLOCK.md.
//
// The source `enemyanimmgr.txt` records frame events with a type: 0/1 are visual
// loop bounds, 2 is the attack/knockback event and 3 the swallow/restore event
// (docs/PIKMIN2_AQUATIC_REMAINDER_ASSETS.md). Catfish authors `attack` 17:2
// (KEYEVENT_2 bite + attackNavi) and 75:3 (KEYEVENT_3 swallow + fp02 poison),
// and `flick` 25:2 (knockback) and 47:3 (reset-non-stone). Timing comes only
// from crossed events, never the displayed pose, so skipped frames, pause,
// interruption and actor recycling cannot duplicate or drop the effect.
#include "pc_p2_sampled_clock.h"

#include <cstdint>
#include <string>
#include <vector>

namespace p2catfishevents {

// One authored p2-aquatic-bank.txt clip row: source length, uniform pose count,
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
// (type 2 only), Catfish routes different keys per clip: the attack clip carries
// bite (type 2) and swallow (type 3), while the flick clip carries knockback
// (type 2) and non-stone restore (type 3).
enum class Action { None, Bite, Swallow, Flick, FlickRestore };

inline Action actionFor(const std::string& clip, const std::string& key) {
    if (clip == "attack") {
        if (key == "2") return Action::Bite;
        if (key == "3") return Action::Swallow;
    }
    if (clip == "flick") {
        if (key == "2") return Action::Flick;
        if (key == "3") return Action::FlickRestore;
    }
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

// The source Catfish event table (docs/PIKMIN2_AQUATIC_REMAINDER_ASSETS.md:70 and
// experimental/pikmin2_aquatic_assets.py EXPECTED_EVENTS['Catfish']), kept here
// so the standalone probe shares the consumer's authoritative mapping. The
// consumed table is read from the generated p2-aquatic-bank.txt at setup() time;
// these durations are valid representative values for the engine-free probe only.
inline std::vector<Row> catfishRows() {
    return {
        {"attack", 90, 2, false, {{17, "2"}, {75, "3"}}},
        {"dead", 60, 2, false, {}},
        {"flick", 55, 2, false, {{25, "2"}, {47, "3"}}},
        {"move1", 30, 2, true, {{0, "0"}, {24, "1"}}},
        {"type5", 35, 2, false, {{10, "0"}, {29, "1"}}},
        {"wait1", 30, 2, true, {}},
        {"waitact2", 45, 2, false, {}},
    };
}

}  // namespace p2catfishevents
