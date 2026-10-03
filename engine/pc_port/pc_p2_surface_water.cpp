#include "pc_p2_surface_water.h"
#include "pc_p2_surface_water_policy.h"
#include "pc_p2_surface_water_drain.h"
#include "pc_bbft.h"
#include "Creature.h"
#include "MapCode.h"
#include "Shape.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <filesystem>
namespace {
BaseShape* owner=nullptr;
std::vector<p2water::Box> boxes;
std::string loadedCourse, originalSha;
std::vector<p2water::Drain> drains;
bool tutorial() {
    const char* course=pc_pikipelago_surface_course();
    return course != nullptr;
}
}
void pc_p2_surface_water_reset() {owner=nullptr;boxes.clear();loadedCourse.clear();originalSha.clear();drains.clear();}
void pc_p2_surface_water_init(BaseShape* model) {
    pc_p2_surface_water_reset();
    if (!tutorial()) return;
    // Only the new water stager installs this optional sidecar. Old dry1089 and
    // ordinary P1 course loading remain unchanged when it is absent.
    const char* course=pc_pikipelago_surface_course();
    char path[128];
    std::snprintf(path,sizeof(path),"assets/dataDir/courses/p2%s/full.water",course);
    std::error_code error;
    const bool exists=std::filesystem::exists(path,error);
    if (!exists && !error) {std::puts("P2_SURFACE_WATER_ABSENT consumer=0 legacy_dry_stage=1");return;}
    std::ifstream input(path);
    if (error || !input || !model || !model->mTriList || model->mTriCount<=0 || !p2water::read(input,boxes,course)) {
        std::puts("P2_SURFACE_WATER_REFUSED malformed_static_sidecar=1");std::fflush(nullptr);std::abort();
    }
    const char* ids[]={"tutorial","forest","yakushima","last"};
    const int counts[]={3,5,8,2};
    bool countValid=false;
    for(int i=0;i<4;++i) if(!std::strcmp(course,ids[i]) && int(boxes.size())==counts[i]) countValid=true;
    if(!countValid) {std::puts("P2_SURFACE_WATER_REFUSED course_count=1");std::abort();}
    owner=model;
    loadedCourse=course;
    std::printf("P2_SURFACE_WATER_READY boxes=%d source_sphere_overlap=1 surface_minus3=1 no_bottom=1 dynamic_lowering=0\n",int(boxes.size()));
}
bool pc_p2_surface_water_active() {
    const char* course=pc_pikipelago_surface_course();
    return owner && course && loadedCourse==course;
}
int pc_p2_surface_water_count() {return pc_p2_surface_water_active()?int(boxes.size()):0;}
int pc_p2_surface_water_box(const Vector3f& p,float radius) {
    if (!pc_p2_surface_water_active()) return -1;
    if (originalSha.empty()) return p2water::find(boxes,p.x,p.y,p.z,radius);
    for (size_t i=0;i<boxes.size();++i)
        if (p2water::containsDrained(boxes[i],drains[i],p.x,p.y,p.z,radius)) return boxes[i].id;
    return -1;
}
bool pc_p2_surface_water_bind_original(const std::string& course,const std::string& sha,
                                     const std::vector<p2water::Box>& expected) {
    if (!pc_p2_surface_water_active() || course!=loadedCourse || !originalSha.empty()
        || expected.size()!=boxes.size()) return false;
    const char* ids[]={"tutorial","forest","yakushima","last"};
    const char* hashes[]={
        "f87b0f012eeac4918acb5e1a64ae315fe6a2e3b3434f3e163fe72b17619548f3",
        "002fcf0f6b6d2bbc2fe18bdcea207a322360c530eb1239f09cb291816640c536",
        "fafe861c1951faaa8cf0ab87c2db09b3298e82a6e7f7c3eb4c077b8a1091a4c5",
        "615f214aa1515064a3c744d3c3fc6218e91fb717f842835b30ac5ea072bca2e7"};
    bool source=false;
    for(int i=0;i<4;++i) if(course==ids[i] && sha==hashes[i]) source=true;
    if(!source) return false;
    for(size_t i=0;i<boxes.size();++i) {
        const auto& a=boxes[i]; const auto& b=expected[i];
        if(!p2water::valid(b) || a.id!=b.id || a.surface!=b.surface) return false;
        for(int k=0;k<3;++k) if(a.min[k]!=b.min[k] || a.max[k]!=b.max[k]) return false;
    }
    std::vector<p2water::Drain> fresh;
    for(const auto& b:boxes) {p2water::Drain d; d.id=b.id; fresh.push_back(d);}
    drains.swap(fresh); originalSha=sha; return true;
}
bool pc_p2_surface_water_start_down(const std::string& course,const std::string& sha,int id) {
    if(!pc_p2_surface_water_active() || originalSha.empty() || course!=loadedCourse
        || sha!=originalSha || id<0 || size_t(id)>=drains.size()) return false;
    return p2water::startDrain(drains[id]);
}
void pc_p2_surface_water_update(float dt) {
    if(!pc_p2_surface_water_active() || originalSha.empty()) return;
    for(auto& d:drains) p2water::updateDrain(d,dt);
}
bool pc_p2_surface_water_snapshot(p2water::DrainSnapshot& result) {
    if(!pc_p2_surface_water_active() || originalSha.empty()) return false;
    p2water::DrainSnapshot candidate{loadedCourse,originalSha,drains};
    result=std::move(candidate); return true;
}
bool pc_p2_surface_water_restore(const p2water::DrainSnapshot& state) {
    return pc_p2_surface_water_active() && p2water::restoreDrains(state,loadedCourse,originalSha,drains);
}
int pc_p2_surface_water_attribute(const Creature* c,int legacy) {
    // Preserve P1's body convention (native feet position/collision radius).
    // This bridges exact source volumes to native P1 water FSMs, not P2 body,
    // effect-height, animation or rendering parity.
    return c && pc_p2_surface_water_box(c->mSRT.t,c->mCollisionRadius)>=0?ATTR_Water:legacy;
}
