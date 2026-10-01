#include "pc_p2_surface_water.h"
#include "pc_p2_surface_water_policy.h"
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
bool tutorial() {
    const char* course=pc_pikipelago_surface_course();
    return course && !std::strcmp(course,"tutorial");
}
}
void pc_p2_surface_water_reset() {owner=nullptr;boxes.clear();}
void pc_p2_surface_water_init(BaseShape* model) {
    pc_p2_surface_water_reset();
    if (!tutorial()) return;
    // Only the new water stager installs this optional sidecar. Old dry1089 and
    // ordinary P1 course loading remain unchanged when it is absent.
    const char* path="assets/dataDir/courses/p2tutorial/full.water";
    std::error_code error;
    const bool exists=std::filesystem::exists(path,error);
    if (!exists && !error) {std::puts("P2_SURFACE_WATER_ABSENT consumer=0 legacy_dry_stage=1");return;}
    std::ifstream input(path);
    if (error || !input || !model || !model->mTriList || model->mTriCount<=0 || !p2water::readTutorial(input,boxes)) {
        std::puts("P2_SURFACE_WATER_REFUSED malformed_static_sidecar=1");std::fflush(nullptr);std::abort();
    }
    owner=model;
    std::printf("P2_SURFACE_WATER_READY boxes=%d source_sphere_overlap=1 surface_minus3=1 no_bottom=1 dynamic_lowering=0\n",int(boxes.size()));
}
bool pc_p2_surface_water_active() {return owner && tutorial();}
int pc_p2_surface_water_count() {return pc_p2_surface_water_active()?int(boxes.size()):0;}
int pc_p2_surface_water_box(const Vector3f& p,float radius) {
    return pc_p2_surface_water_active()?p2water::find(boxes,p.x,p.y,p.z,radius):-1;
}
int pc_p2_surface_water_attribute(const Creature* c,int legacy) {
    // Preserve P1's body convention (native feet position/collision radius).
    // This bridges exact source volumes to native P1 water FSMs, not P2 body,
    // effect-height, animation or rendering parity.
    return c && pc_p2_surface_water_box(c->mSRT.t,c->mCollisionRadius)>=0?ATTR_Water:legacy;
}
