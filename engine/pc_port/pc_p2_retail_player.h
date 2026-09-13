#pragma once
#include "pc_p2_motion_events.h"
#include <limits>

namespace p2retail {
enum class Update { Ok, Inactive, Invalid, Reentrant, Replaced };
// Positive-timer SysShape event semantics. Host owns receivers and actor lifetime.
class Player {
public:
    bool start(const Motion& motion) {
        if(motion.duration<1 || motion.duration>10000 || motion.events.size()>4096 ||
           generation_==std::numeric_limits<std::uint64_t>::max()) return false;
        int previous=-1, loop=-1;
        for(const auto& e:motion.events){
            if(e.frame<0 || e.frame<previous || e.frame>=motion.duration || e.type<0 || e.type>=1000) return false;
            if(e.type==0) loop=e.frame;
            if(e.type==1 && (loop<0 || loop>=e.frame)) return false;
            previous=e.frame;
        }
        motion_=motion; ++generation_; timer_=0; cursor_=0;
        active_=true; completed_=false; finishing_=false; return true;
    }
    void cancel(){active_=false;}
    void finishMotion(bool finish=true){finishing_=finish;}
    // SysShape::setCurrFrame: reposition keys and clear completion/finish flags.
    // Unlike the original unchecked API, reject out-of-clip and nonfinite input.
    bool seek(float frame){
        if(!active_ || !std::isfinite(frame) || frame<0 || frame>=motion_.duration ||
           generation_==std::numeric_limits<std::uint64_t>::max()) return false;
        ++generation_; timer_=frame; cursor_=0;
        while(cursor_<motion_.events.size() && motion_.events[cursor_].frame<int(frame)) ++cursor_;
        completed_=false; finishing_=false; return true;
    }
    bool seekLastFrame(){return active_ && seek(float(motion_.duration-1));}
    bool seekKey(int type){
        if(!active_) return false;
        if(type==1000) return seekLastFrame();
        for(const auto& event:motion_.events)
            if(event.type==type) return seek(float(event.frame));
        return false;
    }
    float frame() const{return timer_;}
    int poseFrame() const{return int(timer_);}
    bool completed() const{return completed_;}
    std::uint64_t generation() const{return generation_;}

    template<class Receiver> Update advance(float delta, Receiver&& receive){
        if(advancing_) return Update::Reentrant;
        if(!active_) return Update::Inactive;
        if(!std::isfinite(delta) || delta<0 || delta>1000000) return Update::Invalid;
        struct Guard {bool& value;Guard(bool& v):value(v){value=true;}~Guard(){value=false;}} guard(advancing_);
        const auto generation=generation_;
        timer_+=delta;
        while(cursor_<motion_.events.size() && due(motion_.events[cursor_],timer_)){
            const auto index=cursor_++;
            const Event event=motion_.events[index];
            receive(event); // Finish-motion may change inside this callback.
            if(!active_ || generation_!=generation) return Update::Replaced;
            if(event.type==1 && !finishing_){
                std::size_t start=index;
                while(start>0 && motion_.events[start].type!=0) --start;
                timer_=float(motion_.events[start].frame);
                cursor_=0;
                while(cursor_<motion_.events.size() && motion_.events[cursor_].frame<int(timer_)) ++cursor_;
                return Update::Ok; // Retail discards overshoot and stops this update.
            }
        }
        if(timer_>=motion_.duration){
            timer_=float(motion_.duration-1);
            if(!completed_){
                completed_=true; receive(Event{motion_.duration,1000});
                if(!active_ || generation_!=generation) return Update::Replaced;
            }
        }
        return Update::Ok;
    }
private:
    Motion motion_;
    float timer_=0;
    std::size_t cursor_=0;
    std::uint64_t generation_=0;
    bool active_=false, completed_=false, finishing_=false, advancing_=false;
};
} // namespace p2retail
