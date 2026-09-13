#pragma once

#include <cmath>
#include <cstdint>
#include <map>
#include <set>

namespace p2purpleimpact {

constexpr float EarthquakeRadius = 60.0f;
constexpr float BounceBaseVelocity = 200.0f;
constexpr float BounceRandomVelocity = 100.0f;
constexpr float RedFitChance = 0.3f;
constexpr float RedFitDuration = 10.0f;

using Lifetime = std::uint64_t;
using Token = std::uint64_t;

struct Event {
    Lifetime sourceLifetime = 0;
    Token attackToken = 0;
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
};

inline bool inRange(const Event& event, float x, float z, float collisionRadius)
{
    if (!std::isfinite(collisionRadius) || collisionRadius < 0.0f) {
        return false;
    }
    const float dx = x - event.x;
    const float dz = z - event.z;
    const float range = EarthquakeRadius + collisionRadius;
    return dx * dx + dz * dz <= range * range;
}

struct SourceState {
    Lifetime lifetime = 0;
    Token token = 0;
    bool armed = false;
    bool emitted = false;
};

class Sources {
public:
    Event arm(const void* actor, float x = 0.0f, float y = 0.0f, float z = 0.0f)
    {
        SourceState& state = mStates[actor];
        state.lifetime = ++mNextLifetime;
        state.token = ++mNextToken;
        state.armed = true;
        state.emitted = false;
        return { state.lifetime, state.token, x, y, z };
    }

    bool consume(const void* actor, Event& event, float x, float y, float z)
    {
        auto found = mStates.find(actor);
        if (found == mStates.end() || !found->second.armed || found->second.emitted) {
            return false;
        }
        found->second.emitted = true;
        event = { found->second.lifetime, found->second.token, x, y, z };
        return true;
    }

    void forget(const void* actor) { mStates.erase(actor); }
    void reset() { mStates.clear(); }

private:
    std::map<const void*, SourceState> mStates;
    Lifetime mNextLifetime = 0;
    Token mNextToken = 0;
};

enum class Phase { None, Bounce, Fit };

struct ReceiverState {
    Lifetime targetLifetime = 0;
    Phase phase = Phase::None;
    unsigned bounceUpdates = 0;
    float fitElapsed = 0.0f;
};

inline float bounceVelocity(float bounceFactor, float roll)
{
    return BounceBaseVelocity * bounceFactor + BounceRandomVelocity * roll;
}

inline void receive(ReceiverState& state, Lifetime targetLifetime)
{
    if (state.targetLifetime != targetLifetime) {
        state = {};
        state.targetLifetime = targetLifetime;
    }
    state.phase = Phase::Bounce;
    state.bounceUpdates = 0;
    // P2 retains a positive Fit timer across another earthquake.
}

inline bool updateBounce(ReceiverState& state, bool onGround, float fitRoll)
{
    if (state.phase != Phase::Bounce) {
        return false;
    }
    ++state.bounceUpdates;
    if (state.bounceUpdates <= 3 || !onGround) {
        return false;
    }
    if (state.fitElapsed > 0.0f || fitRoll < RedFitChance) {
        state.phase = Phase::Fit;
        return true;
    }
    state.phase = Phase::None;
    return false;
}

inline bool updateFit(ReceiverState& state, float deltaTime, bool interrupted)
{
    if (state.phase != Phase::Fit) {
        return false;
    }
    if (interrupted) {
        state.phase = Phase::None;
        return false;
    }
    state.fitElapsed += deltaTime;
    if (state.fitElapsed > RedFitDuration) {
        state.phase = Phase::None;
        state.fitElapsed = 0.0f;
        return false;
    }
    return true;
}

} // namespace p2purpleimpact
