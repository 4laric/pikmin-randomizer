#pragma once
#include "pc_p2_original_pod.h"
struct Vector3f;
namespace p2retailcargo {
// Both providers must resolve the independently authenticated prepared floor,
// not copy the requested birth/position back as proof.
// Output yaw is radians; NativeFloor's authored yawDegrees needs conversion.
using PlacementAuthority=std::function<bool(const p2retail::SceneIdentity&,unsigned,unsigned,Vector3f&,float&,std::string&)>;
struct Config {
    p2retail::Snapshot floor;
    p2originalpod::ContextProvider context;
    p2retail::FloorIdentityAuthority* births=nullptr;
    PlacementAuthority placement;
};
// Synchronous operation supplied by the actual receiver lifecycle owner.
// Success must mean it released its Pod; this is not a retention/receipt token.
using PodTeardown=std::function<bool(std::string&)>;
}
bool pc_p2_retail_treasure_cargo_preflight(const p2retailcargo::Config&,std::string&);
// Direct native PelletMgr allocation with private original-profile PelletView;
// never a numbered pellet, P1 generator, Onion or preview treasure actor.
bool pc_p2_retail_treasure_cargo_birth(const p2retail::BirthIdentity&,Pellet*&,std::string&);
bool pc_p2_retail_treasure_cargo_absent(const p2retail::BirthIdentity&,const std::string& receipt,std::string&);
bool pc_p2_retail_treasure_cargo_carry_radius(Pellet*,float&);
// Prepared rollback cannot consume cargo; committed unfinished graphs remain
// owned until a real floor/cache provider can retain and restore them. These
// teardown functions coordinate the matching Pod rollback/release first. A
// wrapper owner supplies its own release operation through the overload, so
// both its native receiver and bookkeeping transition exactly once.
bool pc_p2_retail_treasure_cargo_abort_prepared(std::string&);
// Read-only boundary readiness while the actual selected scene is still live.
// Does not release the receiver, retire actors or authorize SAVE/retention.
bool pc_p2_retail_treasure_cargo_can_release_collected(std::string&);
bool pc_p2_retail_treasure_cargo_release_collected(std::string&);
bool pc_p2_retail_treasure_cargo_abort_prepared(p2retailcargo::PodTeardown,std::string&);
bool pc_p2_retail_treasure_cargo_release_collected(p2retailcargo::PodTeardown,std::string&);
