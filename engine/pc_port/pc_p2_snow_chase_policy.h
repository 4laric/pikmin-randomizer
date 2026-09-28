#pragma once
#include "pc_p2_snow_turn_policy.h"
#include <cmath>
#include <istream>
#include <set>
#include <string>

// Source target velocity only. Native action ordering and physical motion remain.
class P2SnowChasePolicy {
    bool active=false;
    std::set<const void*> actors;
public:
    struct Result { bool valid=false;float direction=0,x=0,y=0,z=0; };
    static Result steer(float facing,float targetAngle,float velocityY) {
        Result result;
        if(!std::isfinite(velocityY))return result;
        const auto turn=P2SnowTurnPolicy::step(facing,targetAngle,0.f);
        if(!turn.valid)return result;
        result.direction=turn.direction;
        result.x=50.f*std::sin(turn.direction);result.y=velocityY;result.z=50.f*std::cos(turn.direction);
        result.valid=true;return result;
    }
    void reset() { active=false;actors.clear(); }
    bool read(std::istream& in) {
        reset();std::string version,key,value,extra;
        if(!(in>>version>>key>>value) || version!="P2_SNOW_CHASE_1" || key!="chase_profile" || value!="source_snow" || in>>extra)return false;
        active=true;return true;
    }
    bool enabled() const { return active; }
    bool contains(const void* actor) const { return active && actors.count(actor); }
    void bind(const void* actor) { if(active && actor)actors.insert(actor); }
    void forget(const void* actor) { actors.erase(actor); }
    bool evaluate(const void* actor,float facing,float targetAngle,float velocityY,Result& result) const {
        if(!contains(actor))return false;
        result=steer(facing,targetAngle,velocityY);return true;
    }
};
