#pragma once
#include <cmath>
namespace p2original { namespace gas {
// SysShape::Animator: loop end frame 3 fires only when frame < int(timer).
// An unfinished loop discards overshoot and resets to source frame zero.
inline bool advanceAttack(float& frame,float dt,bool finish) {
 frame+=dt*30.0f;
 if(!finish&&std::floor(frame)>3.0f){frame=0;return false;}
 if(frame>=4.0f){frame=3;return true;}
 return false;
}
} }
