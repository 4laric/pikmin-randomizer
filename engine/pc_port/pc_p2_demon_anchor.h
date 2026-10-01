// Demon (32, Bumbling Snitchbug) anchor collision + flight policy (#215).
//
// Engine-free: the campaign Demon is a private P2SaraiHost drawn at its own
// mSRT, while the slot's P1 anchor BTeki is the creature the Pikmin throw at,
// stick to and damage. Before this header the anchor kept its Dwarf Bulborb
// vehicle collision (joint spheres sampled during the anchor's own draw) and
// was never flagged flying, so a hovering Demon had ground Pikmin milling and
// jumping underneath a body they could not reach, and the anchor's spheres
// did not follow the drawn Demon body.
//
// This header mirrors the retail Sarai/Demon contract:
//  * enemy/data/Demon enemycoll.txt: a radius-30 bounding sphere on bodyjnt
//    (code '____', never stickable) with two stickable 'st__' spheres
//    (13.0 @ (-6,7,0) and 12.5 @ (0,4,0)) on the same joint. The P1 CollInfo
//    built from this tree makes thrown Pikmin latch only on the body spheres
//    (pikiState FLYING collide -> isCollisionType && isStickable), exactly as
//    P2 Sarai::Obj sticks them, and never on the bounding sphere.
//  * Sarai::Obj / SaraiState: EB_Untargetable is set while hovering (Wait,
//    Move, Attack, CatchFly, TakeOff, Flick, Fail, FallMeck) and cleared by
//    Fall/Damage/Dead. The P1 counterpart is CF_IsFlying on the anchor:
//    ground Pikmin skip flying targets (aiAttack.cpp:217, piki.cpp:1000) and
//    abandon an unstuck attack on one (aiAttack.cpp:325), while thrown Pikmin
//    still stick (pikiState.cpp FLYING collide has no flying check) and stuck
//    Pikmin keep biting (aiAttack.cpp:743). Once the stuck weight drags the
//    Demon into Fall -> Damage it lands, the flag clears and the whole squad
//    can attack until fp23 (strugglingTime) or the last sticker drops.
//
// The body joint rest offset comes from the staged rest-pose mesh: the P2
// model root sits under the body, the vertex centroid of demon_wait1_0000
// is (0.0, 16.4, 2.8) and the lying poses (type2/dead) keep the body between
// y 0 and 32 with the root on the floor, so bodyjnt ~ root + (0, 16, 3). The
// host measures the centroid of its loaded rest mesh at runtime and falls
// back to this constant when the mesh is unavailable.
#pragma once

#include <cmath>
#include <cstddef>

namespace p2demonanchor {

struct Vec3 {
    float x = 0.0f, y = 0.0f, z = 0.0f;
};

// Retail Demon collision tree (enemy/data/Demon enemycoll.txt), pre-order.
struct CollSphere {
    const char* id;    // synthetic unique id (retail ids are all 'none')
    const char* code;  // retail code: '____' bounding, 'st__' stickable
    float radius;
    Vec3 offset;       // bodyjnt-local offset
    int parent;        // pre-order parent index, -1 for the root
};

constexpr int kSphereCount = 3;
inline const CollSphere* spheres()
{
    static const CollSphere kSpheres[kSphereCount] = {
        {"body", "____", 30.0f, {0.0f, 0.0f, 0.0f}, -1},
        {"st_1", "st__", 13.0f, {-6.0f, 7.0f, 0.0f}, 0},
        {"st_2", "st__", 12.5f, {0.0f, 4.0f, 0.0f}, 0},
    };
    return kSpheres;
}

// Fallback body joint rest offset (root -> bodyjnt), see the header comment.
inline Vec3 defaultBodyOffset() { return Vec3{0.0f, 16.0f, 3.0f}; }

// Body joint estimate from a rest-pose vertex cloud: the centroid. Returns
// false (and leaves `out` untouched) for an empty or non-finite cloud so the
// caller keeps the fallback.
template <typename VertexAt>
inline bool bodyOffsetFromMesh(std::size_t count, VertexAt vertexAt, Vec3& out)
{
    if (count == 0) return false;
    double sx = 0.0, sy = 0.0, sz = 0.0;
    for (std::size_t i = 0; i < count; ++i) {
        const Vec3 v = vertexAt(i);
        if (!std::isfinite(v.x) || !std::isfinite(v.y) || !std::isfinite(v.z)) return false;
        sx += v.x; sy += v.y; sz += v.z;
    }
    out.x = float(sx / double(count));
    out.y = float(sy / double(count));
    out.z = float(sz / double(count));
    return std::fabs(out.x) < 1.0e4f && std::fabs(out.y) < 1.0e4f && std::fabs(out.z) < 1.0e4f;
}

// World centre of sphere `index` for a host at `root` facing `yaw` (radians,
// P1 convention: +x = sin(yaw), +z = cos(yaw)) with the body joint at
// root + R(yaw) * bodyOffset. Offsets rotate with the body.
inline Vec3 sphereCentre(int index, const Vec3& root, float yaw, const Vec3& bodyOffset)
{
    const CollSphere& s = spheres()[index < 0 ? 0 : (index >= kSphereCount ? kSphereCount - 1 : index)];
    const float lx = bodyOffset.x + s.offset.x;
    const float ly = bodyOffset.y + s.offset.y;
    const float lz = bodyOffset.z + s.offset.z;
    const float c = std::cos(yaw), sn = std::sin(yaw);
    Vec3 w;
    w.x = root.x + c * lx + sn * lz;
    w.y = root.y + ly;
    w.z = root.z - sn * lx + c * lz;
    return w;
}

// Lowest point of the stickable collision above `root`: what a thrown Pikmin
// must reach. Used by the tests and the runtime log only.
inline float stickableBottom(const Vec3& bodyOffset)
{
    float best = 1.0e9f;
    for (int i = 0; i < kSphereCount; ++i) {
        const CollSphere& s = spheres()[i];
        if (s.code[0] != 's') continue;
        const float bottom = bodyOffset.y + s.offset.y - s.radius;
        if (bottom < best) best = bottom;
    }
    return best;
}

// CF_IsFlying for the anchor this tick: the FSM's EB_Untargetable mirror
// (flags().untargetable) except in Fall/Damage/Dead, where the source runs
// doSimulationGround and the P1 port runs host gravity (pc_p2_sarai_demon.cpp
// exec physics: `flying = false` for those three states).
inline bool anchorFlying(bool untargetable, bool fallDamageOrDead)
{
    return untargetable && !fallDamageOrDead;
}

// Lock-On cursor pin for a flying target (port convenience, navi.cpp
// pcPinCursorToLock): P1 throwPiki puts the arc's peak at half the cursor
// distance (hSpeed = dist / flightTime, peak at flightTime / 2), and the
// Pikmin reaches the cursor XZ on the way down at 32..72 units (80..100
// throw height, gravity 550, 1.0 s). Pinning the cursor at twice the target
// offset puts the peak over a hovering target instead of under it. Grounded
// targets keep the plain pin.
inline float lockPinScale(bool targetFlying) { return targetFlying ? 2.0f : 1.0f; }

} // namespace p2demonanchor
