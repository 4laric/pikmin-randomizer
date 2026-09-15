#pragma once
#include "pc_p2_retail_player.h"

namespace p2retail {
// Event/time coordinator only. The renderer applies its blend function to progress().
class BlendPlayer {
public:
    bool startTrack(unsigned index, const Motion& motion) {
        if(index>1 || exhausted() || !tracks_[index].start(motion)) return false;
        ready_[index]=true; ++generation_; return true;
    }
    bool seekTrack(unsigned index, float frame) {
        if(index>1 || exhausted() || !tracks_[index].seek(frame)) return false;
        ++generation_; return true;
    }
    bool finishTrack(unsigned index) {
        if(index>1 || !ready_[index]) return false;
        tracks_[index].finishMotion(); return true;
    }
    bool startBlend(float duration) {
        if(!ready_[0] || !ready_[1] || exhausted() || !std::isfinite(duration) || duration<=0) return false;
        duration_=duration; timer_=0; enabled_=true; completed_=false; ++generation_; return true;
    }
    bool endBlend() {
        if(exhausted()) return false;
        enabled_=false; completed_=false; timer_=0; ++generation_; return true;
    }
    void cancel() {
        tracks_[0].cancel(); tracks_[1].cancel(); ready_[0]=ready_[1]=false;
        enabled_=false; completed_=false; timer_=0;
        if(!exhausted()) ++generation_;
    }
    float frame(unsigned index) const {return index<2 ? tracks_[index].frame() : 0;}
    float progress() const {return enabled_ ? timer_/duration_ : 0;}
    bool enabled() const {return enabled_;}
    bool completed() const {return completed_;}

    // Receivers: event(trackIndex, Event), blendEnd(float duration).
    // Blend completion remains enabled until explicitly ended, matching SysShape.
    template<class Receiver, class Completion>
    Update advance(float delta, float primaryDelta, float secondaryDelta, Receiver&& event, Completion&& end) {
        if(advancing_) return Update::Reentrant;
        if(!ready_[0] || (enabled_ && !ready_[1])) return Update::Inactive;
        if(!validDelta(delta) || !validDelta(primaryDelta) || !validDelta(secondaryDelta)) return Update::Invalid;
        struct Guard {bool& v; Guard(bool& value):v(value){v=true;} ~Guard(){v=false;}} guard(advancing_);
        const auto generation=generation_;
        const unsigned count=enabled_ ? 2 : 1;
        for(unsigned i=0;i<count;++i) {
            Update status;
            try {
                status=tracks_[i].advance(i ? secondaryDelta : primaryDelta,
                    [&](const Event& key){
                        event(i,key);
                        if(generation_!=generation) throw DispatchReplaced{};
                    });
            } catch(const DispatchReplaced&) {return Update::Replaced;}
            if(generation_!=generation) return Update::Replaced;
            if(status!=Update::Ok) return status;
        }
        if(enabled_) {
            // Subtract before adding to avoid overflow for a very long blend.
            timer_ = delta>=duration_-timer_ ? duration_ : timer_+delta;
            if(timer_>=duration_ && !completed_) {
                completed_=true; end(duration_);
                if(generation_!=generation) return Update::Replaced;
            }
        }
        return Update::Ok;
    }
private:
    struct DispatchReplaced {};
    static bool validDelta(float value){return std::isfinite(value) && value>=0 && value<=1000000;}
    bool exhausted() const{return generation_==std::numeric_limits<std::uint64_t>::max();}
    Player tracks_[2];
    bool ready_[2]={false,false};
    std::uint64_t generation_=0;
    float timer_=0, duration_=1;
    bool enabled_=false, completed_=false, advancing_=false;
};
} // namespace p2retail
