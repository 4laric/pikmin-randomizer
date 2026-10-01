// Engine-free buried-idle / emergence timeline for the Creeping Chrysanthemum
// (Hana, EnemyID 84), #964 owner playtest "plant guy not idling as a trap in the
// ground".
//
// Source (decomp Game::Hana / ChappyBase::StateSleep, chappyState.cpp:98-181):
// the actor starts in Sleep with mDoSkipSleepStart, so it plays the type1
// ("Sleep") clip from frame 70; type1 authors LOOP_START at 30 and LOOP_END at
// 100 (enemyanimmgr.txt), so a sleeping Hana loops frames 30..100, which is the
// seed-sized bump below ground (baked pose bounds +-8 wide, top at y=6). Frames
// 0..30 dive the standing body into the ground. When a target enters the wake
// radius, setNextState() sets the animation speed to 60 and finishMotion(): the
// loop is left and type1 plays on to its end (frames 100..END, the emergence,
// with the ground burst at KEYEVENT_4) before the FSM turns to Walk.
//
// The port used to hold type1 pose 0 while buried, which is the full standing
// body: the plant was drawn upright on the ground instead of hidden.
#pragma once

#include <cmath>

namespace p2hanasleep {

constexpr float kDefaultLoopBegin = 30.0f;  // type1 LOOP_START (event key 0)
constexpr float kDefaultLoopEnd = 100.0f;   // type1 LOOP_END (event key 1)
constexpr float kSpawnFrame = 70.0f;        // StateSleep::init mDoSkipSleepStart
constexpr float kNormalFps = 30.0f;
constexpr float kWakeFps = 60.0f;           // StateSleep::setNextState setAnimationSpeed(60)

enum class Phase { Dive, Loop, Wake };

class Cursor {
public:
    // total = type1 source frame count (149 for retail), loopBegin/loopEnd from its events.
    void configure(float total, float loopBegin, float loopEnd)
    {
        total_ = total > 2.0f ? total : 2.0f;
        if (loopBegin >= 0.0f && loopEnd > loopBegin && loopEnd < total_) {
            begin_ = loopBegin;
            end_ = loopEnd;
        } else {
            begin_ = kDefaultLoopBegin;
            end_ = kDefaultLoopEnd;
        }
    }
    // Spawn: Sleep entered with mDoSkipSleepStart (inside the loop).
    void startSpawn()
    {
        phase_ = Phase::Loop;
        frame_ = kSpawnFrame < end_ ? kSpawnFrame : begin_;
    }
    // Re-entry from GoHome: the body dives into the ground first.
    void startDive()
    {
        phase_ = Phase::Dive;
        frame_ = 0.0f;
    }
    // A target is in range: leave the loop and play on to the end at 60 fps.
    void wake()
    {
        phase_ = Phase::Wake;
    }
    // Advances the clip by dt seconds. Returns true once a woken clip reached its end.
    bool advance(float dt)
    {
        if (!(dt > 0.0f)) return done();
        switch (phase_) {
        case Phase::Dive:
            frame_ += dt * kNormalFps;
            if (frame_ >= begin_) phase_ = Phase::Loop;
            break;
        case Phase::Loop:
            frame_ += dt * kNormalFps;
            if (frame_ >= end_) frame_ = begin_ + std::fmod(frame_ - begin_, end_ - begin_);
            break;
        case Phase::Wake:
            frame_ += dt * kWakeFps;
            break;
        }
        return done();
    }
    bool done() const { return phase_ == Phase::Wake && frame_ >= total_ - 1.0f; }
    Phase phase() const { return phase_; }
    float frame() const { return frame_ > total_ - 1.0f ? total_ - 1.0f : frame_; }
    // 0..1 position in the clip, in the units the draw path expects
    // (sourceFrame = phase * (frames - 1)).
    float phase01() const { return frame() / (total_ - 1.0f); }
    float total() const { return total_; }
    float loopBegin() const { return begin_; }
    float loopEnd() const { return end_; }
    // True while the drawn body is the buried bump (the loop region): what the
    // owner should see underground.
    bool buriedPose() const { return phase_ != Phase::Wake && frame_ >= begin_ && frame_ < end_; }
    // The emergence ground burst (KEYEVENT_4 at frame 120) crossed this tick.
    static bool crossed(float before, float after, float eventFrame) { return before < eventFrame && after >= eventFrame; }

private:
    Phase phase_ = Phase::Loop;
    float frame_ = kSpawnFrame;
    float total_ = 149.0f;
    float begin_ = kDefaultLoopBegin;
    float end_ = kDefaultLoopEnd;
};

// Wake radius. Source isWakeup() tests the private radius (fp11 = 70): Hana is
// an ambusher that waits until a Navi or Pikmin is that close. The port widened
// the test to the sight radius (500) so staged fixture squads woke it; a real
// seed must use the source radius or the trap springs from across the screen.
constexpr float kSourceWakeRadius = 70.0f;
constexpr float kFixtureWakeRadius = 500.0f;
inline float wakeRadius(bool campaign) { return campaign ? kSourceWakeRadius : kFixtureWakeRadius; }

}  // namespace p2hanasleep
