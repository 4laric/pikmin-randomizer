#pragma once
#include <algorithm>
#include <cmath>

namespace p2frog {
// GPVE01 user/Kando/aiConstants.txt. Frog::doSimulationFlying clamps upward
// velocity at zero instead of letting gravity pull it down during JumpWait.
constexpr float flightGravity = 560.0f;
struct Flight {
    float x=0, y=0, z=0, vx=0, vy=0, vz=0, elapsed=0;
};
inline Flight launchFlight(float x,float y,float z,float tx,float tz,float airTime,float jumpSpeed) {
    return {x,y,z,2.0f*(tx-x)/airTime,jumpSpeed,2.0f*(tz-z)/airTime,0.0f};
}
inline void advanceFlying(Flight& f,float tx,float tz,float airTime,float dt) {
    // Source caps the new horizontal speed at the previous frame's speed.
    const float remaining=airTime-f.elapsed;
    if(remaining>0.0f){
        const float dx=tx-f.x,dz=tz-f.z,distance=std::sqrt(dx*dx+dz*dz);
        const float speed=std::sqrt(f.vx*f.vx+f.vz*f.vz);
        const float next=2.0f*distance/remaining;
        if(next<=speed){
            f.vx=distance>0.0f?next*dx/distance:0.0f;
            f.vz=distance>0.0f?next*dz/distance:0.0f;
        }
    }else{f.vx=0.0f;f.vz=0.0f;}
    f.vy=std::max(0.0f,f.vy-flightGravity*dt);
    f.x+=f.vx*dt;f.y+=f.vy*dt;f.z+=f.vz*dt;f.elapsed+=dt;
}
inline void startFall(Flight& f,float fallSpeed){f.vx=0.0f;f.vz=0.0f;f.vy=-fallSpeed;}
inline bool readyToFall(float elapsed,float waitTime,float airTime,float clipDuration){
    // A finish request before the first loop still plays the whole wait clip.
    const float tail=std::max(0.0f,clipDuration-19.0f/30.0f);
    return waitTime>=clipDuration && elapsed>=airTime+tail;
}
inline bool advanceFalling(Flight& f,float floorY,float dt){
    f.vy-=flightGravity*dt;
    f.y+=f.vy*dt;
    if(f.y<=floorY){f.y=floorY;return true;}
    return false;
}
}
