#pragma once
#include <cstdint>

struct P2DemonEscapeStep { float animationSpeed=30; bool escape=false; };
// NaviSaraiState's input window only; host owns attachment, switching and FSM.
class P2DemonEscapeWindow {
public:
    void reset() { flags_=0; count_=0; }
    unsigned count() const { return count_; }
    template<class Random>
    P2DemonEscapeStep step(bool attached, bool directionalDownEdge, Random&& random) {
        if ((flags_&0x08000000u)&&count_) --count_;
        flags_<<=1;
        if (attached&&directionalDownEdge) { flags_|=1; ++count_; }
        P2DemonEscapeStep out;
        if (count_>=6) {
            const float rate=count_/22.0f;
            out.animationSpeed=rate*60+60;
            // Source consumes the second sample only if the first passes.
            if (random()<rate*rate && random()<0.1f) out.escape=true;
        }
        return out;
    }
private:
    std::uint32_t flags_=0;
    std::uint16_t count_=0;
};
