#pragma once
// Source mouth-slot capture for the P2 captor families (#886 defect 3/5):
// Jigumo 63, Snagret 34/70, UmiMushi 71/101, Armor 15, UjiB 13 and Tobi 14.
// Engine-free so the runtime modules (pc_p2_jigumo.cpp, pc_p2_snakejoint.cpp,
// pc_p2_umimushi.cpp, pc_p2_armor.cpp, pc_p2_uji.cpp) and
// tools/p2_captor_mouth_test.cpp compile the same decision code. Reuses the
// #884 types and helpers of pc_p2_chappy_mouth.h (Vec3, Prey, eligible,
// localToWorld/toLocal: +z facing, heading = atan2(dx, dz)).
//
// Source of truth (read-only P2 decomp):
//   EnemyFunc::eatPikmin      plugProjectYamashitaU/enemyAction.cpp:224-257
//   EnemyFunc::swallowPikmin  plugProjectYamashitaU/enemyAction.cpp:265-288
//   EatPikminDefaultCondition include/Game/EnemyFunc.h:44-63
//   MouthSlots::setup (zero offset, joint world translation)
//                             plugProjectKandoU/collinfo.cpp:1083-1086,1136-1140
//   Jigumo   1 x kamu_joint1 r=max(18*scale,25)   plugProjectMorimuraU/jigumo.cpp:260-273
//            Attack eat (ConditionHeightCheckPiki -25..+10, not stuck)
//            jigumoState.cpp:355-356, Jigumo.h:54-86; SAttack eat jigumoState.cpp:801;
//            swallow Eat KEYEVENT_8 jigumoState.cpp:667, SAttack KEYEVENT_10 :843;
//            white poison proper fp05 (Jigumo.h:217, retail 500).
//   UmiMushi 7 x kamu_joint1..7 r=30 (Blind 25)   plugProjectMorimuraU/umiMushi.cpp:551-566
//            eat every frame while the tongue is active (KEYEVENT_3..KEYEVENT_6)
//            umiMushiState.cpp:510-514,523-524,556-566; swallow at eat END :605-607;
//            white poison proper fp11 (UmiMushi.h:188, retail 200).
//   Armor    1 x kamujnt r=25                     plugProjectNishimuraU/Armor.cpp:205-213
//            Obj::attackPikmin (same slot loop, InteractSwallow stabbed) Armor.cpp:230-260,
//            every frame 17 < f < 27 of attack2 ArmorState.cpp:586-589;
//            killSlotPiki = swallowPikmin(proper fp01, retail 300) Armor.cpp:286-289, ArmorState.cpp:652-653.
//   UjiB / Tobi 1 x kamujnt r=15                  Ujib.cpp:138-145, Tobi.cpp:206-213
//            Attack2 KEYEVENT_4 attackNavi + eatPikmin UjibState.cpp:933-936, TobiState.cpp:683-686;
//            Eat KEYEVENT_2 swallowPikmin(proper poison) UjibState.cpp:996-997, TobiState.cpp:746-747.
//   Snagret  3 x kamujnt1..3 r=15 (occupancy only) SnakeCrow.cpp:262-272, SnakeWhole.cpp:219-229.
//            Capture is NOT a slot-distance test: StateAttack KEYEVENT_3 takes
//            getAttackPiki(mAttackAnimIdx) (the five facing boxes of
//            SnakeCrow.cpp:348-397 / SnakeWhole.cpp:404-455) and swallows it
//            into getSwallowSlot() (first free slot, SnakeCrow.cpp:452-463):
//            SnakeCrowState.cpp:569-577, SnakeWholeState.cpp:737-745; swallow
//            at Eat KEYEVENT_2 SnakeCrowState.cpp:661-663, SnakeWholeState.cpp:846-848.
//
// Slot geometry (PORT APPROXIMATION, documented): no retail joint positions
// for these species exist in this tree (the root repo's extractors record
// clip/event/parm data only; nothing samples kamu joints for them), so each
// kamu joint is placed on the facing axis at feet height, at a fixed local
// offset derived from the source attack reach of the same key frame:
//   * one-slot captors: centre at half the source reach, never closer than
//     the radius (so the sphere never reaches behind the feet plane):
//       Jigumo   reach 50 (StateSAttack attackNavi 50*scale, jigumoState.cpp:805) -> z 25
//       Armor    reach 75 (retail general fp22)                                  -> z 37.5
//       UjiB/Tobi reach 70 (general fp22 header default; no retail Uji disc parms here) -> z 35
//   * UmiMushi tongue: the seven slots are spread evenly on the facing axis
//     from z = r to the source fp22 attack hit radius (retail 170), scaled by
//     the Blind setParameters 0.5 (radius unscaled, as in the source).
// Every slot satisfies z - r >= 0: a Pikmin at or behind the feet plane can
// never be captured, which is the source property the old XZ-nearest capture
// broke. The runtime logs the geometry (P2_*_MOUTH) so a Windows run can be
// compared against the visible jaw. Scale is fixed at 1 (the port does not
// roll the source random Jigumo scale; no RNG additions for netplay).
#include "pc_p2_chappy_mouth.h"
#include <cmath>

namespace p2captor {

using p2chappymouth::distance;
using p2chappymouth::localToWorld;
using p2chappymouth::Prey;
using p2chappymouth::toLocal;
using p2chappymouth::Vec3;

constexpr int MaxSlots = 7;

struct Geometry {
    unsigned source;          // P2 EnemyID
    int slots;                // source initMouthSlots count
    float radius;             // MouthCollPart::mRadius (unscaled, as the source sets it)
    float poison;             // white-Pikmin poison fed to eatWhitePikminCallBack
    const float (*local)[3];  // model-space kamu joint per slot (port approximation, see above)
};

namespace data {
inline constexpr float kJigumo[][3] = {{0.0f, 0.0f, 25.0f}};
inline constexpr float kArmor[][3] = {{0.0f, 0.0f, 37.5f}};
inline constexpr float kUji[][3] = {{0.0f, 0.0f, 35.0f}};
// z_i = 30 + (170 - 30) * i / 6
inline constexpr float kUmi[][3] = {
    {0.0f, 0.0f, 30.0f},        {0.0f, 0.0f, 53.333333f}, {0.0f, 0.0f, 76.666667f}, {0.0f, 0.0f, 100.0f},
    {0.0f, 0.0f, 123.333333f}, {0.0f, 0.0f, 146.666667f}, {0.0f, 0.0f, 170.0f},
};
// Blind: z_i = 25 + (85 - 25) * i / 6 (reach 0.5 * 170, first slot at r=25)
inline constexpr float kUmiBlind[][3] = {
    {0.0f, 0.0f, 25.0f}, {0.0f, 0.0f, 35.0f}, {0.0f, 0.0f, 45.0f}, {0.0f, 0.0f, 55.0f},
    {0.0f, 0.0f, 65.0f}, {0.0f, 0.0f, 75.0f}, {0.0f, 0.0f, 85.0f},
};
// Snagret slot joints are never distance-tested (capture is the facing-box
// rule); only the three-slot occupancy is used.
inline constexpr float kSnake[][3] = {{0.0f, 0.0f, 0.0f}, {0.0f, 0.0f, 0.0f}, {0.0f, 0.0f, 0.0f}};
} // namespace data

inline constexpr Geometry kGeometries[] = {
    {63, 1, 25.0f, 500.0f, data::kJigumo},    // retail Jigumo proper fp05 = 500
    {71, 7, 30.0f, 200.0f, data::kUmi},       // retail UmiMushi proper fp11 = 200
    {101, 7, 25.0f, 200.0f, data::kUmiBlind}, // shared UmiMushi parms block
    {15, 1, 25.0f, 300.0f, data::kArmor},     // retail Armor proper fp01 = 300
    {13, 1, 15.0f, 300.0f, data::kUji},       // Ujib proper fp01 header default 300
    {14, 1, 15.0f, 300.0f, data::kUji},       // Tobi proper fp11 header default 300
    {34, 3, 15.0f, 200.0f, data::kSnake},     // retail SnakeCrow proper fp21 = 200
    {70, 3, 15.0f, 400.0f, data::kSnake},     // retail SnakeWhole proper fp21 = 400
};

inline const Geometry* geometryFor(unsigned source)
{
    for (const Geometry& g : kGeometries) {
        if (g.source == source) return &g;
    }
    return nullptr;
}

inline Vec3 slotLocal(const Geometry& g, int slot)
{
    return Vec3{g.local[slot][0], g.local[slot][1], g.local[slot][2]};
}

inline Vec3 slotWorld(const Geometry& g, int slot, const Vec3& actor, float heading)
{
    return localToWorld(actor, heading, slotLocal(g, slot));
}

// Source EatPikminDefaultCondition plus the P1 "active Piki" test (#884).
inline bool defaultEligible(const Prey& p)
{
    return p2chappymouth::eligible(p);
}

// Source Jigumo ConditionHeightCheckPiki (Jigumo.h:54-86): not stuck to
// anything, the default condition, and feet height within [y-25, y+10].
struct JigumoHeightCheck {
    float actorY;
    bool operator()(const Prey& p) const
    {
        if (p.stuckToAny) return false;
        if (!p2chappymouth::eligible(p)) return false;
        return !(p.pos.y > actorY + 10.0f) && !(p.pos.y < actorY - 25.0f);
    }
};

// One source EnemyFunc::eatPikmin pass over world slot positions: for each
// eligible prey in manager order, the first EMPTY slot in index order whose
// 3D distance is strictly below the radius is stimulated; the slot is marked
// occupied only when the receiver accepted; the next prey follows either way.
// No reachable empty slot means no capture (no overflow, no null part).
template <class Eligible, class Stimulate>
int eatAt(const Vec3* slotPos, int slots, float radius, const Prey* prey, int count, bool* occupied,
          Eligible&& ok, Stimulate&& stimulate)
{
    if (slots <= 0 || slots > MaxSlots) return 0;
    int eaten = 0;
    for (int n = 0; n < count; ++n) {
        if (!ok(prey[n])) continue;
        for (int i = 0; i < slots; ++i) {
            if (occupied[i]) continue;
            if (distance(slotPos[i], prey[n].pos) < radius) {
                if (stimulate(n, i)) {
                    occupied[i] = true;
                    ++eaten;
                }
                break;
            }
        }
    }
    return eaten;
}

template <class Eligible, class Stimulate>
int eat(const Geometry& g, const Vec3& actor, float heading, const Prey* prey, int count, bool* occupied,
        Eligible&& ok, Stimulate&& stimulate)
{
    if (g.slots <= 0 || g.slots > MaxSlots) return 0;
    Vec3 slotPos[MaxSlots];
    for (int i = 0; i < g.slots; ++i) slotPos[i] = slotWorld(g, i, actor, heading);
    return eatAt(slotPos, g.slots, g.radius, prey, count, occupied, ok, stimulate);
}

// ---- Snagret facing boxes (SnakeCrow.cpp:323-397, SnakeWhole.cpp:379-455) ----
// Zones: 0 near, 1 normal, 2 far, 3 right, 4 left. animIdx 5 searches all
// five (the attack-start query); animIdx < 5 tests only that zone (the
// KEYEVENT_3 bite). dir = (sin f, 0, cos f), orthoDir = (-dir.z, 0, dir.x).
struct SnakeZones {
    float attackForward[5]; // setAttackPosition array1
    float attackSide[5];    // setAttackPosition array2
    float maxDot[5], minDot[5], maxPerp[5], minPerp[5];
};
inline constexpr SnakeZones kSnakeCrowZones = {
    {40.0f, 120.0f, 190.0f, 90.0f, 90.0f}, {0.0f, 0.0f, 0.0f, 80.0f, -80.0f},
    {80.0f, 160.0f, 220.0f, 130.0f, 130.0f}, {0.0f, 80.0f, 160.0f, 50.0f, 50.0f},
    {30.0f, 30.0f, 30.0f, 110.0f, -50.0f}, {-30.0f, -30.0f, -30.0f, 50.0f, -110.0f},
};
inline constexpr SnakeZones kSnakeWholeZones = {
    {60.0f, 150.0f, 220.0f, 120.0f, 120.0f}, {0.0f, 0.0f, 0.0f, 80.0f, -80.0f},
    {120.0f, 180.0f, 260.0f, 160.0f, 160.0f}, {0.0f, 120.0f, 180.0f, 80.0f, 80.0f},
    {30.0f, 30.0f, 30.0f, 110.0f, -50.0f}, {-30.0f, -30.0f, -30.0f, 50.0f, -110.0f},
};
constexpr int SnakeAnyZone = 5;

inline const SnakeZones& snakeZonesFor(unsigned source)
{
    return source == 70 ? kSnakeWholeZones : kSnakeCrowZones;
}

// setAttackPosition XZ (the caller fills y from the map floor, getMinY).
inline Vec3 snakeAttackPosition(const SnakeZones& z, int i, const Vec3& actor, float faceDir)
{
    const float dx = std::sin(faceDir), dz = std::cos(faceDir);
    const float ox = -dz, oz = dx;
    return Vec3{actor.x + dx * z.attackForward[i] + ox * z.attackSide[i], actor.y,
                actor.z + dz * z.attackForward[i] + oz * z.attackSide[i]};
}

// Zone index of `q` for getAttackPiki/getAttackNavi(animIdx), or -1.
// zoneFloorY[i] is mAttackPositions[i].y (floor under attack point i).
inline int snakeZoneOf(const SnakeZones& z, int animIdx, const Vec3& actor, float faceDir, const float* zoneFloorY,
                       const Vec3& q)
{
    int p1 = 0, p2 = 5;
    if (animIdx >= 0 && animIdx < 5) {
        p1 = animIdx;
        p2 = animIdx + 1;
    }
    const float dx = std::sin(faceDir), dz = std::cos(faceDir);
    const float ox = -dz, oz = dx;
    const float sx = q.x - actor.x, sy = q.y - actor.y, sz = q.z - actor.z;
    const float dotDir = dx * sx + dz * sz;
    const float dotPerp = ox * sx + oz * sz;
    for (int i = p1; i < p2; ++i) {
        const float h = zoneFloorY[i] - actor.y;
        if (dotDir < z.maxDot[i] && dotDir > z.minDot[i] && dotPerp < z.maxPerp[i] && dotPerp > z.minPerp[i] &&
            sy < 40.0f + h && sy > -40.0f + h) {
            return i;
        }
    }
    return -1;
}

// Source getAttackPiki eligibility: isAlive && isPikmin && !isStickToMouth
// (plus the P1 active-Piki test: drawn, not a buried sprout).
inline bool snakeEligible(const Prey& p)
{
    return p.alive && p.visible && !p.buried && !p.stuckToAnyMouth;
}

// First prey in manager order inside the zone(s); *zoneOut gets its zone.
inline int snakeAttackPiki(const SnakeZones& z, int animIdx, const Vec3& actor, float faceDir, const float* zoneFloorY,
                           const Prey* prey, int count, int* zoneOut)
{
    for (int n = 0; n < count; ++n) {
        if (!snakeEligible(prey[n])) continue;
        const int zone = snakeZoneOf(z, animIdx, actor, faceDir, zoneFloorY, prey[n].pos);
        if (zone >= 0) {
            if (zoneOut) *zoneOut = zone;
            return n;
        }
    }
    return -1;
}

// Source getSwallowSlot: first slot with no stuck creature, or -1 (the source
// would then assert in InteractSwallow::actPiki; the port refuses instead).
inline int firstFreeSlot(const bool* occupied, int slots)
{
    for (int i = 0; i < slots; ++i) {
        if (!occupied[i]) return i;
    }
    return -1;
}

// ---- Held registry ----------------------------------------------------------
// Which Pikmin this captor holds in which P2 slot. The authority on "held" is
// the physical stick (the Pikmin is still one of this actor's mouth stickers);
// the registry only maps it to a P2 slot and is revalidated against the
// sticker list before every use. forget() is the death-/birth-time hook (a
// recycled Piki slot must never inherit a capture).
template <class T>
struct Held {
    T* slot[MaxSlots] = {};

    void clear()
    {
        for (int i = 0; i < MaxSlots; ++i) slot[i] = nullptr;
    }
    bool forget(const T* p)
    {
        bool hit = false;
        for (int i = 0; i < MaxSlots; ++i) {
            if (p && slot[i] == p) {
                slot[i] = nullptr;
                hit = true;
            }
        }
        return hit;
    }
    // Drop every entry for which stillHeld(entry) is false; fill `occupied`.
    template <class StillHeld>
    int validate(int slots, bool* occupied, StillHeld&& stillHeld)
    {
        int held = 0;
        for (int i = 0; i < slots && i < MaxSlots; ++i) {
            if (slot[i] && !stillHeld(slot[i])) slot[i] = nullptr;
            occupied[i] = slot[i] != nullptr;
            held += occupied[i] ? 1 : 0;
        }
        return held;
    }
    int count(int slots) const
    {
        int n = 0;
        for (int i = 0; i < slots && i < MaxSlots; ++i) n += slot[i] ? 1 : 0;
        return n;
    }
};

// Source swallowPikmin over the held registry: only Pikmin still physically
// held (stillHeld) are killed; the registry is emptied either way. Returns
// the number killed; `whiteKilled` counts white Pikmin among them (each feeds
// the poison damage to the eater, eatWhitePikminCallBack).
template <class T, class StillHeld, class Kill, class IsWhite>
int swallow(Held<T>& held, int slots, StillHeld&& stillHeld, Kill&& kill, IsWhite&& isWhite, int* whiteKilled)
{
    int killed = 0, white = 0;
    for (int i = 0; i < slots && i < MaxSlots; ++i) {
        T* p = held.slot[i];
        held.slot[i] = nullptr;
        if (!p || !stillHeld(p)) continue;
        const bool w = isWhite(p);
        if (kill(p)) {
            ++killed;
            white += w ? 1 : 0;
        }
    }
    if (whiteKilled) *whiteKilled = white;
    return killed;
}

} // namespace p2captor
