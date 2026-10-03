#pragma once
#include "pc_p2_original_honey_policy.h"
namespace p2originalresource { namespace honey {
struct Snapshot {
 ChildIdentity identity;HoneyKind kind=HoneyKind::Nectar;Phase phase=Phase::Fall;
 P2EggVec3 position,velocity;bool firstConsumption=false,jiggling=false;
 std::string animation;
};
} }
