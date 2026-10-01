#pragma once
// Cloaking Burrow-nit (Armor, P2 EnemyID 15) engine-free source policy (#1014).
//
// Source of truth (read-only P2 decomp, plugProjectNishimuraU/ and the retail armor/enemycoll.txt):
//   collision tree   retail enemycoll.txt: root r40 (joint 6 kosijnt, `____`), `dmg1` r17.5 (joint 1
//                    headjnt, offset 7.5,0,0, `st__`) and the shell sphere r22.5 (joint 7 kourajnt,
//                    offset 7.5,-5,0, `_t__`). Only `dmg1` is stickable (CollPart::isStickable matches
//                    's***', collinfo.cpp:806). The shell (kourajnt = "koura") is neither stickable nor
//                    damageable.
//   damageCallBack   Armor.cpp:117-128: damage only while Bittered or when the part id is 'dmg1'.
//   hipdropCallBack  Armor.cpp:134-141: the same predicate with the purple stun damage.
//   bombCallBack     NOT overridden: EnemyBase::bombCallBack (enemyBase.cpp:2908) is an unconditional
//                    addDamage(damage, 1.0f), so a bomb hurts the Armor on any part.
//   mouth slot       Armor.cpp:205-213: one slot on the joint `kamujnt` (joint 2), radius 25.
//   attackPikmin     Armor.cpp:232-261: every frame 17 < f < 27 of attack2 (ArmorState.cpp:586-589) each
//                    live Pikmin not already stuck to the Armor, with the 3D distance to the slot below the
//                    slot radius, is stabbed (InteractSwallow, mIsStabbed). There is no facing test: the
//                    mouth position decides, and the mouth lunges forward during those frames.
//   attack start     ArmorState.cpp:231-233 / :470: isTargetAttackable(target, angle, fp20, fp21) and
//                    getNearestPikminOrNavi(fp21, fp20): |angle| <= 15 deg and XZ range 75 (retail fp20/21).
//   Navi attack      ArmorState.cpp:603: attackNavi(range fp22 = 75, angle fp23 = 15, damage fp24 = 10).
// Model-space convention is the pose-bank one (+z facing, +y up from the feet):
// world = actor + R_y(heading) * local * actor scale.
#include "pc_p2_armor_receiver_policy.h"
#include "pc_p2_armor_tables.h"
#include "pc_p2_chappy_mouth.h"

#include <cmath>
#include <cstring>

namespace p2armor {

using p2chappymouth::Vec3;

constexpr float Pi = 3.14159265f;
constexpr float AttackRange = 75.0f;       // general fp20 "attackable range"
constexpr float AttackAngleDeg = 15.0f;    // general fp21 "attackable angle"
constexpr float HitRange = 75.0f;          // general fp22 "attack hit range"
constexpr float HitAngleDeg = 15.0f;       // general fp23 "attack hit angle"
constexpr float HitDamage = 10.0f;         // general fp24 "attack power"
constexpr float MouthRadius = 25.0f;       // initMouthSlots
constexpr float PoisonDamage = 300.0f;     // proper fp01 (white Pikmin)
constexpr float BiteAfterFrame = 17.0f;    // attackPikmin runs while 17 < frame < 27
constexpr float BiteBeforeFrame = 27.0f;

constexpr int NodeRoot = 0, NodeDmg1 = 1, NodeShell = 2;

inline bool inBiteWindow(float frame) { return frame > BiteAfterFrame && frame < BiteBeforeFrame; }

// ---- Tables ---------------------------------------------------------------------------
inline int clipIndex(const char* stem)
{
    for (int i = 0; i < p2armortables::kClipCount; ++i)
        if (std::strcmp(p2armortables::kClips[i].stem, stem) == 0) return i;
    return -1;
}

inline int clipFrames(int clip)
{
    return clip >= 0 && clip < p2armortables::kClipCount ? p2armortables::kClips[clip].frames : 0;
}

inline void lerpRow(const float* base, int frames, float frame, int stride, int index, float out[3])
{
    if (frames <= 1) {
        for (int k = 0; k < 3; ++k) out[k] = base[index * 3 + k];
        return;
    }
    float f = frame < 0.0f ? 0.0f : (frame > float(frames - 1) ? float(frames - 1) : frame);
    int i0 = int(f);
    if (i0 > frames - 2) i0 = frames - 2;
    const float w = f - float(i0);
    const float* a = base + size_t(i0) * size_t(stride) * 3 + size_t(index) * 3;
    const float* b = base + size_t(i0 + 1) * size_t(stride) * 3 + size_t(index) * 3;
    for (int k = 0; k < 3; ++k) out[k] = a[k] + (b[k] - a[k]) * w;
}

// Model-space centre of collision node `node` (0 root, 1 dmg1 head, 2 shell) at a source frame.
inline bool nodeCentre(int clip, float frame, int node, float out[3])
{
    if (clip < 0 || clip >= p2armortables::kClipCount || node < 0 || node >= p2armortables::kNodeCount) return false;
    const p2armortables::Clip& c = p2armortables::kClips[clip];
    lerpRow(p2armortables::kColl + c.collOffset, c.frames, frame, p2armortables::kNodeCount, node, out);
    return true;
}

// Model-space world translation of the kamujnt joint (the mouth slot) at a source frame.
inline bool mouthCentre(int clip, float frame, float out[3])
{
    if (clip < 0 || clip >= p2armortables::kClipCount) return false;
    const p2armortables::Clip& c = p2armortables::kClips[clip];
    lerpRow(p2armortables::kMouth + c.mouthOffset, c.frames, frame, 1, 0, out);
    return true;
}

inline Vec3 toWorld(const Vec3& actor, float heading, float scale, const float local[3])
{
    return p2chappymouth::localToWorld(actor, heading, Vec3{local[0] * scale, local[1] * scale, local[2] * scale});
}

// ---- Angles ---------------------------------------------------------------------------
struct Polar {
    float angleDeg;  // 0 = straight ahead of the body, positive toward +x (the body's left in model space)
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

// Source isTargetAttackable / getNearestPikmin: XZ range below `range` and |angle| <= `angleDeg`.
inline bool withinCone(const Vec3& actor, float heading, const Vec3& q, float range, float angleDeg)
{
    const Polar p = polar(actor, heading, q);
    return p.distXZ < range && std::fabs(p.angleDeg) <= angleDeg;
}

inline bool attackable(const Vec3& actor, float heading, const Vec3& q)
{
    return withinCone(actor, heading, q, AttackRange, AttackAngleDeg);
}

// Source EnemyFunc::attackNavi (enemyAction.cpp:1179-1203): |angle| < fp23 and the 3D distance < fp22.
inline bool naviHit(const Vec3& actor, float heading, const Vec3& q)
{
    const Polar p = polar(actor, heading, q);
    return std::fabs(p.angleDeg) < HitAngleDeg && p2chappymouth::distance(actor, q) < HitRange;
}

// attackPikmin slot test: 3D distance below the slot radius.
inline bool mouthHit(const Vec3& mouth, const Vec3& prey)
{
    return p2chappymouth::distance(mouth, prey) < MouthRadius;
}

// ---- Damage acceptance ---------------------------------------------------------------------
// The part codes of the retail tree. Stickable = the first code char is 's' (collinfo.cpp:806).
inline bool codeStickable(const char* code) { return code && code[0] == 's'; }

inline int stickableCount()
{
    int n = 0;
    for (int i = 0; i < p2armortables::kNodeCount; ++i)
        if (codeStickable(p2armortables::kNodes[i].code)) ++n;
    return n;
}

// Source damageCallBack for an InteractAttack that carries a part (a latched Pikmin).
inline bool partAccepts(bool bittered, std::uint32_t partId)
{
    return p2armorreceiver::sourceAccepts(bittered, true, partId);
}

// A captain punch is the hand hitting one part (NaviPunchState::hitCallback). The port punch carries no
// part, so the hand is the facing punch point: the punch lands on `dmg1` only when that sphere is
// within `reach` of the captain (the part the hand reaches), never on the shell or the body.
inline bool punchReachesHead(const Vec3& navi, float naviFace, const Vec3& head, float headRadius, float reach)
{
    const float dx = head.x - navi.x, dz = head.z - navi.z;
    const float dist = std::sqrt(dx * dx + dz * dz);
    if (dist > headRadius + reach) return false;
    float a = std::atan2(dx, dz) - naviFace;
    while (a > Pi) a -= 2.0f * Pi;
    while (a < -Pi) a += 2.0f * Pi;
    return std::fabs(a) < 2.3561945f;  // the port punch's own 135 degree facing cone (naviState.cpp)
}

// ---- Idle homing and burrowing (#1063) ---------------------------------------------------------------
// Source ArmorState.cpp:
//   StateMove::exec :220-274  no Pikmin/Navi in view -> GoHome (:249-252); a target that is not attackable and a
//                             position beyond the territory radius (fp09) -> GoHome (:236-239); a Pikmin/Navi
//                             inside attack range/angle -> Attack2 (:240-245). The change happens at the move
//                             clip's KEYEVENT_END (:267-269).
//   StateGoHome::exec :461-500 walk to mHomePosition; Pikmin/Navi in attack range -> Attack2 (:470-473); within the
//                             home radius (fp10) -> Dive (:476-483), taken at clip end.
//   StateDive :168-198        dive clip, then Stay; StateStay :75-106 stays hidden (hard constrained) until a
//                             Pikmin/Navi is in view (fp12 sight, fp13 view angle), then Appear -> Move.
enum Next { KeepMoving = 0, ToAttack2, ToGoHome, ToDive };

inline Next moveNext(bool hasTarget, bool attackable, bool nearAttackTarget, float distHome, float territory)
{
    if (!hasTarget) return ToGoHome;
    if (attackable) return ToAttack2;
    if (distHome > territory) return ToGoHome;
    if (nearAttackTarget) return ToAttack2;
    return KeepMoving;
}

inline Next goHomeNext(bool nearAttackTarget, float distHome, float homeRadius)
{
    if (nearAttackTarget) return ToAttack2;
    if (distHome < homeRadius) return ToDive;
    return KeepMoving;
}

}  // namespace p2armor
