#pragma once
// Lane-08 reference consumer: drive the Cloaking Burrow-nit (Armor, EnemyID 15)
// gameplay effects from the authoritative #431 sampled-animation clock instead
// of a per-state wall-time counter. See docs/PIKMIN2_SAMPLED_CLOCK_EVENTS.md and
// docs/PIKMIN2_ARMOR_EVENT_CLOCK.md.
//
// The source `enemyanimmgr.txt` records frame events with a type: 0/1 are
// visual loop bounds and 2 is the damage/drop event (see
// docs/PIKMIN2_GROUND_INVERTEBRATE_ASSETS.md:73). Armor authors exactly one
// type-2 event in each of attack2 (frame 18), eat (frame 60) and flick
// (frame 39), which this receiver maps to the family's bite, eat-kill and
// flick actions. Timing comes only from crossed events, never the displayed
// pose, so skipped frames, pause, interruption and actor recycling cannot
// duplicate or drop the effect.
#include "pc_p2_sampled_clock.h"

#include <cstdint>
#include <string>
#include <vector>

namespace p2armorevents {

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

// Gameplay roles carried by a source type-2 animation event.
enum class Action { None, Bite, Eat, Flick };

inline Action actionFor(const std::string& clip, const std::string& key) {
    if (key != "2") {
        return Action::None;
    }
    if (clip == "attack2") {
        return Action::Bite;
    }
    if (clip == "eat") {
        return Action::Eat;
    }
    if (clip == "flick") {
        return Action::Flick;
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

// Build the source Armor event table used by the arena bank. Kept here so the
// native consumer and its standalone probe share one authoritative definition.
inline std::vector<Row> armorRows() {
    return {
        {"dead", 125, 2, false, {{17, "2"}}},
        {"appear", 60, 2, false, {{15, "2"}, {30, "2"}, {45, "2"}}},
        {"dive", 40, 2, false, {{15, "2"}}},
        {"move", 20, 2, true, {{0, "0"}, {19, "1"}}},
        {"attack1", 20, 2, false, {{15, "2"}}},
        {"attack2", 40, 2, false, {{12, "0"}, {14, "1"}, {18, "2"}, {22, "3"}}},
        {"eat", 65, 2, false, {{60, "2"}}},
        {"flick", 60, 2, false, {{39, "2"}}},
        {"attack_fail", 10, 2, false, {}},
        {"carry", 40, 2, false, {{10, "0"}, {29, "1"}}},
    };
}

}  // namespace p2armorevents
