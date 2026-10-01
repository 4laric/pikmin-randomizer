#pragma once
// Engine-free Otakara (Dweevil) stall detection and side-step choice.
//
// Owner playtest 2026-09-30: "trouble pathfinding, stuck on a slope".
//
// What the source does: there is no pathfinding. StateMove recomputes the destination every
// frame (OtakaraBase::isMovePositionSet -> getTargetPosition, OtakaraBase.cpp:361-444: one
// fp06 step directly away from the nearest Pikmin/Navi, projected onto the fp09 = 200 home
// territory circle) and calls EnemyFunc::walkToTarget (enemyAction.cpp:2102-2107), which turns
// toward it and sets the target velocity with EnemyBase::setTargetSpeed (EnemyBase.h:419-427):
//     vel.x = speed * sin(face); vel.y = keep; vel.z = speed * cos(face)
// i.e. the HORIZONTAL speed is exactly fp06 (80; Munge 100) whatever the slope, because P2's
// EnemyBase::doSimulationGround only accelerates toward that target velocity and the map
// collision keeps the body on the floor.
//
// What the P1 host does differently (src/plugPikiKando/creature.cpp moveVelocity): the drive is
// projected onto the ground triangle's plane and re-normalised to the drive's own length, so the
// horizontal component shrinks by the slope (80 -> 61 at 40 degrees, 52 at 50 degrees); triangles
// with |normal.y| <= 0.6 are not ground at all (mapMgr.cpp:2296-2300) and a slip-coded triangle
// (MapCode::getSlipCode != 0) adds a downhill slide every tick (creature.cpp:1302-1314). The
// retail P2 territory is cave floor; the P1 Forest of Hope slots sit on hillsides, so an escape
// direction that faces uphill across such terrain stalls the Dweevil against it while the threat
// keeps it in Move (measured from the owner's session 0930-1307 Anode log: Move-to-Move
// displacement 44 u/s average, 4 u/s minimum against 80 commanded; the same Dweevil on the flat
// spring test slot moves at 73 u/s average).
//
// Port adaptation (documented, not retail): (1) slopeGain() restores the source horizontal speed
// by scaling the drive so the projected horizontal component equals fp06; (2) a stall detector
// notices a Move that advances < 35% of its commanded distance over 0.6 s and side-steps: it
// tries the escape heading rotated by +-45/90/135 degrees, takes the first whose two probe points
// are walkable ground inside the territory, and holds it for 1.2 s before the source rule takes
// over again. No teleport, no position write: only the heading handed to the same drive.
#include <cmath>

namespace p2otakarastall {

constexpr float kWindow = 0.6f;      // seconds of Move measured per decision
constexpr float kStallRatio = 0.35f; // moved / expected below this counts as stalled
constexpr float kHold = 1.2f;        // seconds a side-step heading is kept
constexpr float kProbeNear = 35.0f;
constexpr float kProbeFar = 70.0f;
constexpr float kMinNormalY = 0.62f; // above the P1 ground threshold 0.6 (mapMgr.cpp:2296)
constexpr float kMaxRise = 1.3f;     // rise / run over the probe (about 52 degrees)
constexpr float kMaxGain = 1.8f;     // never command more than 1.8x the source drive

// One ground probe (MapMgr::getCurrTri / getMinY under the point).
struct Probe {
    bool valid = false;
    float y = 0.0f;
    float normalY = 1.0f;
    int slip = 0;
};

// Scale to apply to the fp06 drive so the PROJECTED horizontal speed equals fp06. `n` is the
// ground normal, `dx/dz` the unit horizontal heading. P1 moveVelocity: t = d - (d.n) n, the
// result has |drive| length along t, so its horizontal part is |drive| * |t_xz| / |t|.
inline float slopeGain(float nx, float ny, float nz, float dx, float dz) {
    const float dn = dx * nx + dz * nz;
    const float tx = dx - dn * nx, ty = -dn * ny, tz = dz - dn * nz;
    const float tl = std::sqrt(tx * tx + ty * ty + tz * tz);
    const float th = std::sqrt(tx * tx + tz * tz);
    if (!(th > 1.0e-4f) || !(tl > 0.0f)) return 1.0f;
    const float g = tl / th;
    return g > kMaxGain ? kMaxGain : (g < 1.0f ? 1.0f : g);
}

inline bool walkable(const Probe& here, const Probe& near, const Probe& far) {
    const Probe* p[2] = {&near, &far};
    const float run[2] = {kProbeNear, kProbeFar};
    for (int i = 0; i < 2; ++i) {
        if (!p[i]->valid) return false;
        if (p[i]->slip != 0) return false;
        if (p[i]->normalY < kMinNormalY) return false;
        if (std::fabs(p[i]->y - here.y) > kMaxRise * run[i]) return false;
    }
    return true;
}

struct Tracker {
    float window = 0.0f;
    float moved = 0.0f;
    float expected = 0.0f;
    float hold = 0.0f;         // seconds left on the side-step heading
    float holdHeading = 0.0f;  // radians
    unsigned stalls = 0;
    unsigned sidesteps = 0;
    unsigned noRoute = 0;
    int lastSide = 1;

    void reset() {
        window = moved = expected = 0.0f;
        hold = 0.0f;
    }
    // Feed one Move tick. Returns true when a window just closed as a stall.
    bool sample(float dt, float movedThisTick, float expectedThisTick) {
        window += dt;
        moved += movedThisTick;
        expected += expectedThisTick;
        if (window < kWindow) return false;
        const bool stalled = expected > 1.0f && moved < kStallRatio * expected;
        window = moved = expected = 0.0f;
        if (stalled) ++stalls;
        return stalled;
    }
    bool holding() const { return hold > 0.0f; }
    void tickHold(float dt) {
        if (hold > 0.0f) {
            hold -= dt;
            if (hold < 0.0f) hold = 0.0f;
        }
    }
};

// Side-step offsets in the order tried, alternating sides starting opposite the last one.
inline int sideOffsetDeg(int index) {
    static const int kOffsets[6] = {45, -45, 90, -90, 135, -135};
    return kOffsets[index < 0 ? 0 : (index > 5 ? 5 : index)];
}

// Picks the first walkable side-step. `ok[i]` is walkable() for offset i; `preferPositive`
// flips the try order so consecutive stalls alternate sides. Returns the offset index or -1.
inline int pickSide(const bool ok[6], bool preferPositive) {
    for (int k = 0; k < 6; ++k) {
        int i = k;
        if (!preferPositive) i = (k % 2 == 0) ? k + 1 : k - 1;
        if (ok[i]) return i;
    }
    return -1;
}

} // namespace p2otakarastall
