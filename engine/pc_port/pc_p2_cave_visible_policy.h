#pragma once
#include <cmath>
#include <cstdint>
#include <string>

// Presentation identity is issued by the transition owner for the live scene.
// An authored boundary is never labelled as an original generator record.
struct P2CaveVisibleBoundary {
    bool present=false, ready=false;
    std::uint64_t scene=0, seed=0;
    int floor=0;
    std::string cave, token;
    float x=0, y=0, z=0, radius=0;
    bool returning=false;
    bool valid() const {
        return present && scene && !cave.empty() && !token.empty()
            && floor>=0 && std::isfinite(x) && std::isfinite(y)
            && std::isfinite(z) && std::isfinite(radius) && radius>=20 && radius<=150;
    }
    bool near(float px,float py,float pz,float margin=0) const {
        return valid() && std::isfinite(px) && std::isfinite(py) && std::isfinite(pz)
            && std::hypot(px-x,pz-z)<=radius+margin && std::fabs(py-y)<=40;
    }
    bool same(const P2CaveVisibleBoundary& b) const {
        return valid() && b.valid() && scene==b.scene && seed==b.seed
            && floor==b.floor && cave==b.cave && token==b.token
            && returning==b.returning && x==b.x && y==b.y && z==b.z && radius==b.radius;
    }
};

class P2CaveVisibleInput {
    P2CaveVisibleBoundary bound;
    bool armed=false, released=false, used=false;
public:
    void reset(){bound={};armed=false;released=false;used=false;}
    // Sample the actual captain's mapped A button. Holding across a load/UI
    // cannot activate a second boundary. After a request, leave its interaction
    // region before returning; cancelled SAVE retains the same protection.
    bool sample(const P2CaveVisibleBoundary& b,float x,float y,float z,
                bool down,bool click,bool captainSafe){
        // Loading temporarily removes the provider snapshot. Preserve the old
        // scene and accepted action so arrival inside a boundary stays blocked.
        if(!b.valid())return false;
        if(!bound.same(b)){
            const bool hadScene=bound.valid();
            bound=b;armed=false;released=false;used=hadScene && b.near(x,y,z,20);
        }
        if(!down)released=true;
        if(used && !b.near(x,y,z,20) && !down)used=false;
        if(released && !used)armed=true;
        return armed && b.ready && captainSafe && b.near(x,y,z) && click;
    }
    void accepted(){armed=false;released=false;used=true;}
    bool prompt() const{return armed && !used;}
};
