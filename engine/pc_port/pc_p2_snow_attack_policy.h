#pragma once
#include <cmath>
#include <istream>
#include <set>
#include <string>

// Source YellowKochappy attack-entry geometry only; P1 bite events remain intact.
class P2SnowAttackPolicy {
    bool active=false;
    std::set<const void*> actors;
public:
    void reset() { active=false;actors.clear(); }
    bool read(std::istream& in) {
        reset();std::string version,rangeKey,range,angleKey,angle,extra;
        if(!(in>>version>>rangeKey>>range>>angleKey>>angle) || version!="P2_SNOW_ATTACK_1" ||
           rangeKey!="range" || range!="30" || angleKey!="half_angle" || angle!="20" || in>>extra)return false;
        active=true;return true;
    }
    bool enabled() const { return active; }
    void bind(const void* actor) { if(active && actor)actors.insert(actor); }
    void forget(const void* actor) { actors.erase(actor); }
    bool contains(const void* actor) const { return active && actors.count(actor); }
    static bool geometry(float distanceSquared,float angle) {
        if(!std::isfinite(distanceSquared) || !std::isfinite(angle) || distanceSquared<0)return false;
        constexpr float pi=3.14159265358979323846f;
        angle=std::remainder(angle,2.f*pi);
        return distanceSquared<30.f*30.f && std::fabs(angle)<=20.f*(pi/180.f);
    }
    bool evaluate(const void* actor,float distanceSquared,float angle,bool recognized,bool& result) const {
        if(!contains(actor))return false;
        result=recognized && geometry(distanceSquared,angle);return true;
    }
};
