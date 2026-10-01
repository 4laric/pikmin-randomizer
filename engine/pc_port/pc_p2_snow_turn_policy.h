#pragma once
#include <algorithm>
#include <cmath>
#include <istream>
#include <set>
#include <string>

// Source proportional angular step; retain P1's arrival threshold and snap.
class P2SnowTurnPolicy {
    bool active=false;
    std::set<const void*> actors;
public:
    struct Result { bool valid=false;float direction=0;bool arrived=false; };
    static float wrap(float value) {
        constexpr float tau=6.2831853071795864769f;
        value=std::fmod(value,tau);return value<0?value+tau:value;
    }
    static Result step(float facing,float target,float arrivalStep) {
        Result result;
        if(!std::isfinite(facing) || !std::isfinite(target) || !std::isfinite(arrivalStep) || arrivalStep<0)return result;
        constexpr float pi=3.14159265358979323846f;
        facing=wrap(facing);target=wrap(target);
        float error=wrap(target-facing);if(error>=pi)error-=2*pi;
        result.arrived=std::fabs(error)<arrivalStep;
        const float cap=10.f*(pi/180.f);
        const float delta=result.arrived?error:std::max(-cap,std::min(cap,error*0.4f));
        result.direction=wrap(facing+delta);result.valid=true;return result;
    }
    void reset() { active=false;actors.clear(); }
    bool read(std::istream& in) {
        reset();std::string version,key,value,extra;
        if(!(in>>version>>key>>value) || version!="P2_SNOW_TURN_1" || key!="turn_profile" || value!="source_snow" || in>>extra)return false;
        active=true;return true;
    }
    bool enabled() const { return active; }
    void bind(const void* actor) { if(active && actor)actors.insert(actor); }
    void forget(const void* actor) { actors.erase(actor); }
    bool evaluate(const void* actor,float facing,float target,float arrivalStep,Result& result) const {
        if(!active || !actors.count(actor))return false;
        result=step(facing,target,arrivalStep);return true;
    }
};
