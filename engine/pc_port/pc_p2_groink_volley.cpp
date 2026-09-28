#include "pc_p2_groink_volley.h"
#include <algorithm>

namespace {
struct RequiredTrace {
    P2GroinkTraceFn function;
    void* context;
    bool failed = false;
    static bool call(void* raw, const P2GroinkVec3& position, const P2GroinkVec3& velocity,
                     float delta, float radius, P2GroinkTraceResult& result) {
        auto& self = *static_cast<RequiredTrace*>(raw);
        if (self.function(self.context, position, velocity, delta, radius, result)) return true;
        self.failed = true;
        // Make the underlying policy record an invalid terminal at its original
        // position; do not invoke its optional no-map integration fallback.
        result.position = {NAN, NAN, NAN};
        return true;
    }
};
}

void P2GroinkVolley::reset() {
    mNodes = {};
    mPrimary = {};
    mActive = {};
    mTerminals = {};
    mActiveCount = mTerminalCount = 0;
    mInactiveCount = kCapacity;
    for (std::size_t i = 0; i < kCapacity; ++i) mInactive[i] = i;
}

P2GroinkVolley::Emission P2GroinkVolley::emit(const P2GroinkMuzzle& muzzle, float speed,
    const std::array<P2GroinkVec3, kVolleySize>& samples) {
    const std::size_t count = std::min(kVolleySize, mInactiveCount);
    std::array<P2GroinkPolicy, kVolleySize> prepared;
    for (std::size_t i = 0; i < count; ++i)
        if (!prepared[i].emit(muzzle, speed, samples[i])) return {};
    for (std::size_t i = 0; i < count; ++i) {
        const std::size_t slot = mInactive[i];
        mNodes[slot] = prepared[i];
        mPrimary[slot] = i == 0;
        mActive[mActiveCount++] = slot;
    }
    for (std::size_t i = count; i < mInactiveCount; ++i) mInactive[i-count] = mInactive[i];
    mInactiveCount -= count;
    return {true, count};
}

bool P2GroinkVolley::update(const P2GroinkVec3& owner, float delta,
                           P2GroinkTraceFn trace, void* context) {
    if (!trace || !std::isfinite(delta) || std::fabs(delta-P2GroinkPolicy::kSourceDelta) > 1e-6f
        || !std::isfinite(owner.x) || !std::isfinite(owner.y) || !std::isfinite(owner.z)) return false;
    mTerminals = {};
    mTerminalCount = 0;
    std::size_t survivors = 0;
    bool valid = true;
    const auto previous = mActive;
    const std::size_t count = mActiveCount;
    for (std::size_t i = 0; i < count; ++i) {
        const std::size_t slot = previous[i];
        auto& node = mNodes[slot];
        node.clearTerminalStep();
        RequiredTrace required{trace, context};
        node.update(owner, delta, RequiredTrace::call, &required);
        if (!node.shell().active) {
            const auto terminal = node.lastTerminalStep();
            mTerminals[mTerminalCount++] = {slot, mPrimary[slot], terminal};
            mInactive[mInactiveCount++] = slot;
            valid = valid && !required.failed && terminal.reason != P2GroinkTerminalReason::Invalid;
        } else {
            mActive[survivors++] = slot;
        }
    }
    mActiveCount = survivors;
    return valid;
}

P2GroinkShell P2GroinkVolley::shell(std::size_t slot) const {
    if (slot >= kCapacity) return {};
    auto result = mNodes[slot].shell();
    result.primary = mPrimary[slot];
    return result;
}
