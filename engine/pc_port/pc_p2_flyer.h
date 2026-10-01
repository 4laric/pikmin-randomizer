// Shared P2 flyer targeting + body-collision policy (wave 3 flyers, #960).
//
// Engine-free. Pikmin 1 Pikmin never acquire an airborne target
// (piki.cpp graspSituation `!isFlying()`, aiAttack.cpp `!isFlying()` in
// findTarget and the ActAttack re-target at :325), yet in Pikmin 2 the very
// same enemies are hit: thrown Pikmin latch onto the hovering body and, once
// enough weight drags it down (or it lands to attack), the whole squad fights
// it. Rather than editing generic Piki AI (which would change vanilla P1
// flyers), the port mirrors the P2 rule onto the existing P1 flag:
//
//   P2  EnemyBase::isFlying()  ==  isEvent(0, EB_Untargetable)   (EnemyBase.h:167)
//   P1  CF_IsFlying on the bound actor
//
//  * hovering / attacking / flicking states enable EB_Untargetable, so the
//    actor is CF_IsFlying: ground Pikmin skip it (piki.cpp:1000, aiAttack.cpp
//    :217), abandon an unstuck attack on it (aiAttack.cpp:325), while THROWN
//    Pikmin still stick (pikiState.cpp FLYING collide has no flying check) and
//    STUCK Pikmin keep biting (aiAttack.cpp:743). CF_IsFlying is also the P1
//    "no gravity" flag (creatureMove.cpp:139), which matches the source: the
//    species drives its own height while EB_Untargetable and is under gravity
//    the rest of the time.
//  * Fall (after its descent frame), Land, Ground, TakeOff (before its KEY2)
//    and GroundFlick clear EB_Untargetable, so the flag drops, gravity
//    applies, and the whole squad can engage the grounded body.
//
// The flag is a pure function of species FSM state, so it is deterministic and
// identical on every netplay peer (no wall clock, no RNG).
#pragma once

#include <cmath>
#include <cstddef>

namespace p2flyer {

struct Vec3 {
    float x = 0.0f, y = 0.0f, z = 0.0f;
};

// One node of a retail enemycoll tree, pre-order (parent before children).
struct Sphere {
    const char* id;    // four-character part id ('bod1', 'suck', ...)
    const char* code;  // 'st__' stickable, '____' plain
    float radius;
    Vec3 offset;       // body-joint-local offset
    int parent;        // pre-order parent index, -1 for the root
};

constexpr int kMaxSpheres = 8;

// EnemyBase::isFlying(): the P1 CF_IsFlying mirror of EB_Untargetable.
inline bool airborne(bool untargetable) { return untargetable; }

// World centre of sphere `index` for a host at `root` facing `yaw` (radians,
// P1 convention +x = sin, +z = cos) with the body joint at
// root + R(yaw) * bodyOffset. Offsets rotate with the body.
inline Vec3 sphereCentre(const Sphere* table, int count, int index, const Vec3& root, float yaw,
                         const Vec3& bodyOffset)
{
    const Sphere& s = table[index < 0 ? 0 : (index >= count ? count - 1 : index)];
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

// Lowest point of the stickable spheres above `root`: what a thrown Pikmin
// must reach to latch. Runtime log / tests only.
inline float stickableBottom(const Sphere* table, int count, const Vec3& bodyOffset)
{
    float best = 1.0e9f;
    for (int i = 0; i < count; ++i) {
        const Sphere& s = table[i];
        if (s.code[0] != 's') continue;
        const float bottom = bodyOffset.y + s.offset.y - s.radius;
        if (bottom < best) best = bottom;
    }
    return best;
}

// Body joint estimate from a rest-pose vertex cloud: its centroid. Returns
// false (leaving `out`) for an empty or non-finite cloud so the caller keeps
// its fallback.
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
    const Vec3 c{float(sx / double(count)), float(sy / double(count)), float(sz / double(count))};
    if (!(std::fabs(c.x) < 1.0e4f && std::fabs(c.y) < 1.0e4f && std::fabs(c.z) < 1.0e4f)) return false;
    out = c;
    return true;
}

// EnemyBase::turnToTarget(pos, turnFactor, maxTurnAngleDeg): one source tick of
// the facing turn. angleDist is the signed shortest angle from the current
// facing to the target direction; the step is clamp(angleDist * turnFactor,
// +-radians(maxTurnAngleDeg)).
constexpr float kPi = 3.14159265358979323846f;
inline float roundAng(float a)
{
    while (a > kPi) a -= 2.0f * kPi;
    while (a < -kPi) a += 2.0f * kPi;
    return a;
}
inline float angleDist(float yaw, float dx, float dz)
{
    return roundAng(std::atan2(dx, dz) - yaw);
}
inline float turnStep(float yaw, float dx, float dz, float turnFactor, float maxTurnAngleDeg)
{
    const float dist = angleDist(yaw, dx, dz);
    const float maxStep = maxTurnAngleDeg * kPi / 180.0f;
    float step = dist * turnFactor;
    if (step > maxStep) step = maxStep;
    if (step < -maxStep) step = -maxStep;
    return roundAng(yaw + step);
}
// EnemyFunc::walkToTarget(pos): horizontal target velocity along the facing.
inline void walkVelocity(float yaw, float speed, float& vx, float& vz)
{
    vx = speed * std::sin(yaw);
    vz = speed * std::cos(yaw);
}

// The Fall-state kick: at the descent frame the source adds -100 to the Y
// velocity so the body drops under gravity (KurageState.cpp StateFall::exec).
constexpr float kFallKick = -100.0f;

} // namespace p2flyer
