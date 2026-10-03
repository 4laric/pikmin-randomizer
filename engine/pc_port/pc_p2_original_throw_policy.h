#pragma once
#include <cmath>

namespace p2throw {
// GPVE01 revision 0 user/Abe/piki/naviParms.txt (p025/p054/p026).
// Local source SHA256: dfcc8e0cf89195f06ea78fdc1a342631da4e5d2495d85380212af7d72eb2eba0.
// Only original RGB bodies are admitted here. Purple flight has its own owner.
struct Velocity { float horizontal=0.0f, vertical=0.0f; };
inline bool rgbVelocity(int species,float distance,float gravity,Velocity& out) {
    if(species<0 || species>2 || !std::isfinite(distance) || distance<0.0f
        || !std::isfinite(gravity) || gravity<=0.0f) return false;
    const float height=species==2?107.0f:72.5f;
    const float halfLandingTime=0.5f; // p026=1.0 seconds
    const float vertical=gravity*0.5f*halfLandingTime+height/halfLandingTime;
    const float timeToPeak=vertical/gravity;
    const float horizontal=distance/(2.0f*timeToPeak);
    if(!std::isfinite(vertical) || !std::isfinite(timeToPeak) || timeToPeak<=0.0f
        || !std::isfinite(horizontal)) return false;
    out={horizontal,vertical};
    return true;
}
}
