#pragma once
#include <istream>
#include <set>
#include <string>

// One source-backed opt-in delta. Does not mutate the P1 family's shared params.
class P2SnowHealthPolicy {
    bool active=false;
    std::set<const void*> actors;
public:
    void reset() { active=false;actors.clear(); }
    bool read(std::istream& in) {
        reset();
        std::string version,key,value,extra;
        if(!(in>>version>>key>>value) || version!="P2_SNOW_POLICY_1" || key!="health" || value!="150" || in>>extra)return false;
        active=true;return true;
    }
    bool enabled() const { return active; }
    void bind(const void* actor) { if(active && actor)actors.insert(actor); }
    void forget(const void* actor) { actors.erase(actor); }
    float life(const void* actor,float fallback) const { return active && actors.count(actor)?150.f:fallback; }
};
