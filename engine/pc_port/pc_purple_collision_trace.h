#pragma once
#include <cstdint>

// Diagnostic bookkeeping only. This never changes an engine actor or force.
class PcPurpleCollisionTraceWindow {
public:
    void begin(bool enabled, bool active, const void* captain, std::uint64_t tick) {
        active_ = enabled && active && captain && tick > 0 && tick >= tick_;
        captain_ = active_ ? captain : nullptr;
        if (tick > tick_) { perTick_ = 0; tick_ = tick; }
    }
    bool eligible(const void* actor) const {
        return active_ && actor && actor == captain_ && perTick_ < 16 && total_ < 2048;
    }
    bool take(const void* actor, bool changed) {
        if (!changed || !eligible(actor)) return false;
        ++perTick_; ++total_; return true;
    }
    std::uint64_t tick() const { return tick_; }
    unsigned sequence() const { return total_; }
private:
    const void* captain_ = nullptr;
    std::uint64_t tick_ = 0;
    unsigned perTick_ = 0, total_ = 0;
    bool active_ = false;
};

class Creature;
// Armed only by the fixture before an existing authoritative idle. Ordinary
// targets never call this; an explicit acquisition-only environment flag is
// independently required by its implementation.
void pc_purple_collision_trace_context(const Creature* captain, bool active, std::uint64_t fixtureTick);
