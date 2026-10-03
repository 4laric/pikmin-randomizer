#pragma once
#include <algorithm>
#include <cmath>
// Original PomState/source-bank motion IDs. Simulation-only 30fps source clock.
namespace p2original { namespace pom {
struct Events { bool action=false, finished=false; };
struct Clock {
    unsigned motion=0;float frame=0;bool actionSent=false,finishSent=false;
    bool reset(unsigned value){if(value>5)return false;motion=value;frame=0;actionSent=finishSent=false;return true;}
    bool advance(float seconds,Events& event){
        event={};if(!std::isfinite(seconds)||seconds<0||motion>5)return false;
        constexpr float duration[]={1,40,30,30,40,20};
        const float old=frame;frame=std::min(duration[motion],old+30.f*seconds);
        const float key=motion==2?25.f:motion==4?20.f:-1.f;
        if(key>=0&&!actionSent&&old<key&&frame>=key){actionSent=true;event.action=true;}
        if(motion!=0&&!finishSent&&frame>=duration[motion]){finishSent=true;event.finished=true;}
        return true;
    }
};
} }
