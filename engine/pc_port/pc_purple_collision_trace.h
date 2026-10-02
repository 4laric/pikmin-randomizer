#pragma once
#include <cstdint>
#include <cmath>
#include <cstring>

inline bool pcPurpleCollisionAcquisitionMode(const char* mode) {
    return mode && (std::strcmp(mode,"sdl_acquire")==0 || std::strcmp(mode,"sdl_dayend")==0);
}

struct PcPurpleQueuedForce { float x=0, y=0, z=0; };
inline bool pcPurpleForceEqual(PcPurpleQueuedForce a, PcPurpleQueuedForce b) {
    return a.x==b.x && a.y==b.y && a.z==b.z;
}
inline bool pcPurpleForceFinite(PcPurpleQueuedForce a) {
    return std::isfinite(a.x) && std::isfinite(a.y) && std::isfinite(a.z);
}
// One authoritative idle only. Captured engine writes are evidence, never commands.
class PcPurpleCollisionClosure {
public:
    bool watches(const void* actor) const { return actor && actor==captain_; }
    void beginIdle(bool active,const void* captain,std::uint64_t fixtureTick,std::uint64_t precedingAuth,
                   PcPurpleQueuedForce initial) {
        const bool initialKnown=pcPurpleForceEqual(initial,{}) || (fixtureTick>0
            && matches(captain,fixtureTick-1,precedingAuth,initial));
        begin(active && initialKnown,captain,fixtureTick,precedingAuth+1,{});
    }
    void begin(bool active,const void* captain,std::uint64_t fixtureTick,std::uint64_t expectedAuth,
               PcPurpleQueuedForce initial) {
        valid_=active && captain && fixtureTick>fixtureTick_ && expectedAuth>0
            && pcPurpleForceFinite(initial) && pcPurpleForceEqual(initial,{});
        if(fixtureTick>fixtureTick_) fixtureTick_=fixtureTick;
        captain_=active?captain:nullptr; auth_=expectedAuth; last_=initial; count_=0;
    }
    void record(const void* actor,std::uint64_t auth,bool ownedNormalFormation,
                PcPurpleQueuedForce before,PcPurpleQueuedForce after) {
        if(actor!=captain_ || pcPurpleForceEqual(before,after)) return;
        if(!valid_ || auth!=auth_ || !ownedNormalFormation || count_>=16
            || !pcPurpleForceFinite(before) || !pcPurpleForceFinite(after)
            || !pcPurpleForceEqual(before,last_)) { valid_=false; return; }
        last_=after; ++count_;
    }
    bool matches(const void* captain,std::uint64_t fixtureTick,std::uint64_t auth,
                 PcPurpleQueuedForce observed) const {
        return valid_ && count_>0 && captain==captain_ && fixtureTick==fixtureTick_
            && auth==auth_ && pcPurpleForceFinite(observed) && pcPurpleForceEqual(last_,observed);
    }
private:
    const void* captain_=nullptr;
    std::uint64_t fixtureTick_=0,auth_=0;
    PcPurpleQueuedForce last_;
    unsigned count_=0;
    bool valid_=false;
};

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
bool pc_purple_collision_owned_queued_force(const Creature* captain,std::uint64_t fixtureTick);
