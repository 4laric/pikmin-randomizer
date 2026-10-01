#pragma once
// UmiMushi (Bloyster 71 / 101) engine-free source policy (#995).
//
// Source of truth (read-only P2 decomp, plugProjectMorimuraU/):
//   collision tree      retail umimushi/enemycoll.txt: root r180 (joint 0), head r80,
//                       kuti r40, ketu r25 and weak r10 (weak_joint2, joint 24). Only `weak`
//                       has the stickable code `st__` (CollPart::isStickable matches 's***',
//                       collinfo.cpp:806); root/head/kuti/ketu are `____`. The tail bulb is
//                       scaled by Parms::mTailScale 1.4 (Obj::setParameters, umiMushi.cpp:62).
//   damageCallBack      umiMushi.cpp:467-492: a hit that carries a collision part is accepted
//                       (full damage, flickSpeed 1.0) only when the attacker is alive and
//                       stuck (isStickTo); a partless hit is accepted only for a live attacker
//                       below position.y + 50 and is scaled by proper fp01 (retail 0.03).
//   mouth slots         umiMushi.cpp:552-566: seven slots on the joints kamu_joint1..7, r30
//                       (Blind r25); the tongue eats every frame from attack key 3 to key 6
//                       (umiMushiState.cpp:510-514); the Eat state swallows at its END.
//   Navi attack         umiMushiState.cpp:521-539 (key 5): a captain is hit only when the
//                       source `_length2` (squared length) of the slot/navi separation is
//                       below the slot radius, i.e. within ~5.5 units of a slot.
//   flick               EnemyFunc::isStartFlick (shake-off tiers from the general ip01..ip07;
//                       retail 10/3/13/6/16/9/20) and flickNearbyPikmin / flickStickPikmin
//                       with general fp16..fp19 (retail 1.0 / 120 / 1.0 / 90): Flick key 2
//                       (umiMushiState.cpp:349-362) and Attack key 6 (:541-554).
// Model-space convention is the pose-bank one (+z facing, +y up from the feet):
// world = actor + R_y(heading) * local * actor scale.
#include "pc_p2_chappy_mouth.h"
#include "pc_p2_umimushi_tables.h"

#include <cmath>
#include <cstring>

namespace p2umi {

using p2chappymouth::Vec3;

constexpr float DamageRate = 0.03f;       // proper fp01 (retail), partless hit scale
constexpr float PartlessHeight = 50.0f;   // damageCallBack: attacker y < position.y + 50
constexpr float TailScale = 1.4f;         // Parms::mTailScale
constexpr float SlotRadius = 30.0f;       // initMouthSlots, ordinary
constexpr float SlotRadiusBlind = 25.0f;  // initMouthSlots, Blind
constexpr float ShakeChance = 1.0f;       // general fp16
constexpr float ShakeKnockback = 120.0f;  // general fp17
constexpr float ShakeDamage = 1.0f;       // general fp18
constexpr float ShakeRange = 90.0f;       // general fp19
constexpr float AttackHitAngleDeg = 30.0f; // general fp23
constexpr float FlickPerHit = 1.0f;       // damageCallBack addDamage(.., 1.0f)
constexpr float Pi = 3.14159265f;

// Shake-off blow tiers (general ip01..ip07, retail UmiMushi). The rounded flick timer must
// exceed the tier of the current stuck-Pikmin count.
constexpr int BlowA = 10, Sticking1 = 3, BlowB = 13, Sticking2 = 6, BlowC = 16, Sticking3 = 9, BlowD = 20;

// Reach of the flick / shake (general fp19 = 90, retail). The source applies it unscaled to both sizes, which
// throws Pikmin around a Toady Bloyster from well outside its half-size body; owner ruling 2026-09-30 (#1020)
// treats that as a bug, so the reach follows the body scale (Toady setParameters scale 0.5, umiMushi.cpp:52).
// The Ranging Bloyster (scale 1) keeps the source 90.
inline float shakeRange(float bodyScale)
{
    return ShakeRange * (bodyScale > 0.0f ? bodyScale : 1.0f);
}

inline int flickThreshold(int stuck)
{
    if (stuck < Sticking1) return BlowA;
    if (stuck < Sticking2) return BlowB;
    if (stuck < Sticking3) return BlowC;
    return BlowD;
}

// EnemyFunc::isStartFlick without the reset (the Bloyster passes false): round half away from
// zero, (int), then u8 truncation, compared with the tier threshold.
inline bool isStartFlick(float timer, int stuck)
{
    const float rounded = timer >= 0.0f ? timer + 0.5f : timer - 0.5f;
    const int flickInt = (unsigned char)(int)rounded;
    return flickInt > flickThreshold(stuck);
}

inline float flickStuckAngle(float heading)
{
    float a = heading + Pi;
    while (a >= 2.0f * Pi) a -= 2.0f * Pi;
    while (a < 0.0f) a += 2.0f * Pi;
    return a;
}

// ---- Damage acceptance --------------------------------------------------------------
enum DamageAccept { DamageRefused = 0, DamageStuck, DamagePartless };

struct DamageAttacker {
    bool present = false;     // InteractAttack::mOwner != nullptr
    bool hasCollPart = false; // source mCollPart != nullptr (see sourceHasCollPart)
    bool alive = false;       // Creature::isAlive
    bool stuck = false;       // Creature::isStickTo (to anything)
    Vec3 pos{0.0f, 0.0f, 0.0f};
};

// Same mapping as the Emperor (pc_p2_chappy_mouth.h king::sourceHasCollPart): the source captain
// punch always carries a part, and the P1 host punch does not, so a captain owner is mapped back
// to "has a part" (a captain is never stuck, so the punch is refused, as in the source).
inline bool sourceHasCollPart(bool hostHasPart, bool ownerIsNavi)
{
    return hostHasPart || ownerIsNavi;
}

inline DamageAccept damageAccept(const Vec3& actor, const DamageAttacker& a)
{
    if (!a.present || !a.alive) return DamageRefused;
    if (a.hasCollPart) return a.stuck ? DamageStuck : DamageRefused;
    return a.pos.y < actor.y + PartlessHeight ? DamagePartless : DamageRefused;
}

inline float damageRate(DamageAccept d)
{
    switch (d) {
    case DamageStuck: return 1.0f;
    case DamagePartless: return DamageRate;
    default: return 0.0f;
    }
}

// ---- Tables ---------------------------------------------------------------------------
inline int clipIndex(const char* stem)
{
    for (int i = 0; i < p2umitables::kClipCount; ++i)
        if (std::strcmp(p2umitables::kClips[i].stem, stem) == 0) return i;
    return -1;
}

inline int clipFrames(int clip)
{
    return clip >= 0 ? p2umitables::kClips[clip].frames : 0;
}

// Linear interpolation of a per-sample table. `frame` is a (possibly fractional) source frame.
inline void lerpRow(const float* base, int samples, int frames, float frame, int stride, int index, float out[3])
{
    if (samples <= 1 || frames <= 1) {
        for (int k = 0; k < 3; ++k) out[k] = base[index * 3 + k];
        return;
    }
    float f = frame < 0.0f ? 0.0f : (frame > float(frames - 1) ? float(frames - 1) : frame);
    const float t = f * float(samples - 1) / float(frames - 1);
    int i0 = int(t);
    if (i0 > samples - 2) i0 = samples - 2;
    const float w = t - float(i0);
    const float* a = base + size_t(i0) * size_t(stride) * 3 + size_t(index) * 3;
    const float* b = base + size_t(i0 + 1) * size_t(stride) * 3 + size_t(index) * 3;
    for (int k = 0; k < 3; ++k) out[k] = a[k] + (b[k] - a[k]) * w;
}

// Model-space centre of collision node `node` (0 root, 1 head, 2 kuti, 3 ketu, 4 weak).
inline bool nodeCentre(int clip, float frame, int node, float out[3])
{
    if (clip < 0 || clip >= p2umitables::kClipCount || node < 0 || node >= p2umitables::kNodeCount) return false;
    const p2umitables::Clip& c = p2umitables::kClips[clip];
    lerpRow(p2umitables::kColl + c.collOffset, c.samples, c.frames, frame, p2umitables::kNodeCount, node, out);
    return true;
}

// Model-space world translation of kamu_joint(slot+1); false for clips without a tongue table.
inline bool kamuCentre(int clip, float frame, int slot, float out[3])
{
    if (clip < 0 || clip >= p2umitables::kClipCount || slot < 0 || slot >= p2umitables::kKamuCount) return false;
    const p2umitables::Clip& c = p2umitables::kClips[clip];
    if (c.kamuFrames <= 0) return false;
    lerpRow(p2umitables::kKamu + c.kamuOffset, c.kamuFrames, c.frames, frame, p2umitables::kKamuCount, slot, out);
    return true;
}

inline Vec3 toWorld(const Vec3& actor, float heading, float scale, const float local[3])
{
    return p2chappymouth::localToWorld(actor, heading, Vec3{local[0] * scale, local[1] * scale, local[2] * scale});
}

// The stickable node (source `weak`, index 4) must be the only `s***` code in the table.
inline int stickableCount()
{
    int n = 0;
    for (int i = 0; i < p2umitables::kNodeCount; ++i)
        if (p2umitables::kNodes[i].code[0] == 's') ++n;
    return n;
}

// Source Navi attack (attack key 5): `_length2` is the SQUARED length of the slot/navi separation
// (umiMushiState.cpp:521-539), compared with the slot radius.
inline bool naviHitBySlot(const Vec3& slot, const Vec3& navi, float radius)
{
    const float dx = slot.x - navi.x, dy = slot.y - navi.y, dz = slot.z - navi.z;
    return dx * dx + dy * dy + dz * dz < radius;
}

// ---- Attack start (umiMushi.cpp:1233 isAttackStart) ----------------------------------------------------
// A Pikmin starts the attack only inside the fp23 cone ahead (half-angle, radians) and the fp22 radius;
// the old port also started it on a bare radius test, so Pikmin beside or behind the body triggered a
// tongue that can never reach them.
inline bool withinCone(const Vec3& actor, float heading, const Vec3& q, float radius, float halfAngle)
{
    const float dx = q.x - actor.x, dz = q.z - actor.z;
    if (dx * dx + dz * dz >= radius * radius) return false;
    float a = std::atan2(dx, dz) - heading;
    while (a > Pi) a -= 2.0f * Pi;
    while (a < -Pi) a += 2.0f * Pi;
    return std::fabs(a) <= halfAngle;
}

// ---- Lock-on aim at the tail bulb ---------------------------------------------------------------
// The lock-on mod pins the throw cursor on the target's feet, but the only stickable part is the raised
// tail bulb (~75 units up, ~130 behind). A thrown Pikmin flies a parabola that ends at the cursor (flight
// time 2 * halfTime, horizontal speed distance / (2 * halfTime)), so it passes the bulb's height on the way
// up and on the way down, earlier than the cursor point. pinScale() returns the factor to apply to the XZ
// offset to the bulb so that crossing happens over the bulb (the descending crossing when it falls inside the
// flight, else the ascending one). Same idea as p2demonanchor::lockPinScale for flyers.
constexpr float LaunchLift = 10.0f; // Navi::throwPiki launches from position + (0, 10, 0)

inline float pinScale(float bulbHeightAboveFeet, float throwHeight, float gravity, float halfTime)
{
    if (!(halfTime > 0.0f) || !(gravity > 0.0f)) return 1.0f;
    const float vSpeed = gravity * 0.5f * halfTime + throwHeight / halfTime;
    const float rel = bulbHeightAboveFeet - LaunchLift; // height above the launch point
    // rel = vSpeed * t - 0.5 * gravity * t^2
    const float disc = vSpeed * vSpeed - 2.0f * gravity * rel;
    if (disc < 0.0f) return 1.0f; // the arc never reaches the bulb's height: plain pin
    const float root = std::sqrt(disc);
    const float tUp = (vSpeed - root) / gravity;
    const float tDown = (vSpeed + root) / gravity;
    const float flight = 2.0f * halfTime;
    float t = tDown <= flight ? tDown : tUp;
    if (!(t > 0.05f)) return 1.0f;
    float k = flight / t;
    if (k < 0.5f) k = 0.5f;
    if (k > 4.0f) k = 4.0f;
    return k;
}

// ---- Hit diagnostics ---------------------------------------------------------------------
// Angle (degrees, 0 = straight ahead, +-180 = directly behind) and XZ distance from the actor to a
// hit point, for the P2_UMIMUSHI_HIT log (#995).
struct Polar {
    float angleDeg;
    float distXZ;
};

inline Polar polar(const Vec3& actor, float heading, const Vec3& q)
{
    const float dx = q.x - actor.x, dz = q.z - actor.z;
    float a = std::atan2(dx, dz) - heading;
    while (a > Pi) a -= 2.0f * Pi;
    while (a < -Pi) a += 2.0f * Pi;
    return Polar{a * 180.0f / Pi, std::sqrt(dx * dx + dz * dz)};
}

} // namespace p2umi
