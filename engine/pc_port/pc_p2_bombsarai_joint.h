#pragma once

#include "pc_p2_bombsarai_bomb.h"

#include <cmath>

// Engine-free capture-joint world transform for the Careening Dirigibug
// (BombSarai, EnemyID 58). The source captures the payload at the `kamu_jnt1`
// joint's world matrix (bomb.cpp:23-44 at projectPiki/pikmin2 revision
// 632af93787b9c95b63f0c13be32b161375ce3a96); this header provides the
// body-relative equivalent until the converter (#128) supplies the real
// animated joint so the payload rides the carrier instead of a static point.
//
// Convention matches the source Release lob decomposition
// (BombSaraiState.cpp:528-531: velocity (50*sin(face), 100, 50*cos(face))),
// i.e. a standard rotation about +Y by yaw: forward (+z local) maps to
// (sin(yaw), 0, cos(yaw)). The hover vertical bob is applied through the body
// origin (the carrier's integrated hover height); this transform adds the
// body-local offset under that rotation.
namespace P2BombSaraiJoint {

inline P2BombSaraiVec3 compute(const P2BombSaraiVec3& body, float yaw,
                              const P2BombSaraiVec3& offset)
{
    const float c = std::cos(yaw);
    const float s = std::sin(yaw);
    P2BombSaraiVec3 world;
    world.x = body.x + c * offset.x + s * offset.z;
    world.y = body.y + offset.y;
    world.z = body.z - s * offset.x + c * offset.z;
    return world;
}

} // namespace P2BombSaraiJoint
