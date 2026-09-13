#pragma once
#include <cstdint>
struct P2CaveNavRate {
    bool enabled=false;
    unsigned count=0;
    std::uint32_t last=0;
    void reset(bool on){enabled=on;count=0;last=0;}
    bool due(std::uint32_t now){
        if(!enabled || count>=120 || (count && std::uint32_t(now-last)<2000))return false;
        last=now;++count;return true;
    }
};
