#pragma once
#include "pc_p2_surface_water_policy.h"

namespace p2water {
enum class Phase { Active, Lowering, Dead };
struct Drain {
    int id = -1;
    Phase phase = Phase::Active;
    float lowered = 0, goal = 0, timer = 0;
};
struct DrainSnapshot {
    std::string course, sourceSha;
    std::vector<Drain> boxes;
};
inline bool validDrain(const Drain& d, int id) {
    if (d.id!=id || !std::isfinite(d.lowered) || !std::isfinite(d.goal)
        || !std::isfinite(d.timer) || d.timer<0) return false;
    switch (d.phase) {
    case Phase::Active: return d.lowered==0 && d.goal==0 && d.timer==0;
    // A -100 drain completes in about 6.4 seconds. Retail timer remains < 40
    // with ordinary native frame times; 100 also admits long final frames.
    case Phase::Lowering: return d.goal==-100 && d.lowered<=0 && d.lowered>d.goal && d.timer<=100;
    case Phase::Dead: return d.goal==-100 && d.lowered==d.goal && d.timer<=100;
    }
    return false;
}
inline bool startDrain(Drain& d) {
    if (d.phase!=Phase::Active) return false;
    d.goal=-100; d.timer=0; d.phase=Phase::Lowering; return true;
}
// Retail AABBWaterBox::update: consume the old timer before advancing it.
inline void updateDrain(Drain& d, float dt) {
    if (d.phase!=Phase::Lowering || !std::isfinite(dt) || dt<=0) return;
    d.lowered -= d.timer*dt;
    d.timer += dt*5;
    if (d.lowered<=d.goal) {d.lowered=d.goal; d.phase=Phase::Dead;}
}
inline bool containsDrained(const Box& b, const Drain& d, float x,float y,float z,float radius) {
    if (d.phase==Phase::Dead) return false;
    Box live=b; live.surface+=d.lowered;
    return contains(live,x,y,z,radius);
}
inline bool restoreDrains(const DrainSnapshot& state,const std::string& course,
                          const std::string& sha,std::vector<Drain>& live) {
    if(sha.empty() || state.course!=course || state.sourceSha!=sha || state.boxes.size()!=live.size()) return false;
    for(size_t i=0;i<state.boxes.size();++i) if(!validDrain(state.boxes[i],int(i))) return false;
    live=state.boxes; return true;
}
}

// Called only by the original-course admission owner after authenticating source
// members. Exact parsed immutable bounds must agree before mutation is enabled.
bool pc_p2_surface_water_bind_original(const std::string& course, const std::string& sourceSha,
                                     const std::vector<p2water::Box>& expected);
bool pc_p2_surface_water_start_down(const std::string& course, const std::string& sourceSha, int boxId);
void pc_p2_surface_water_update(float dt);
bool pc_p2_surface_water_snapshot(p2water::DrainSnapshot& result);
bool pc_p2_surface_water_restore(const p2water::DrainSnapshot& snapshot);
