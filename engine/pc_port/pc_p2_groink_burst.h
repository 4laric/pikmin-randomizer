#pragma once
// #892 Gatling Groink shell burst policy. Engine-free.
//
// Source: MiniHoudai attack1 has ONE emit key (KEYEVENT_4, frame 25 of 44; the retail
// bank in p2-groink-bank.txt lists a single type-4 event). StateAttack::exec calls
// Obj::emitShotGun on that key (MiniHoudaiState.cpp:326-330), and
// MiniHoudaiShotGunMgr::emitShotGun (MiniHoudaiShotGun.cpp:1345-1384) runs
// `for (int i = 0; i < 3; i++)` in that single call: each iteration takes an inactive
// node, places it 25 units ahead of the kuti joint along its x axis, jitters the unit
// direction by randWeightFloat(0.2) - 0.1 per axis (factors[] = {0.1, 0.1, 0.1}),
// scales by mShellSpeed and starts it (only i == 0 flags the camera/rumble shell). So a
// burst is three shells in the SAME source tick: interval 0, spread +/-0.1 per axis. It
// is not staggered. The pool holds six nodes, so a second volley launched while the
// first is still in flight still gets three (six in the air); a full pool skips nodes
// (`if (!node) continue`) and still fires the muzzle effect.

#include "pc_p2_groink_volley.h"

#include <algorithm>
#include <cmath>
#include <cstddef>

namespace p2groinkburst {

constexpr int kShots = 3;          // emitShotGun loop count
constexpr int kIntervalTicks = 0;  // all shells spawn inside one emitShotGun call
constexpr float kSpread = 0.1f;    // factors[i]: per-axis direction jitter half-range
constexpr int kEmitKeyFrame = 25;  // attack1 KEYEVENT_4 (retail clip, 44 frames)
constexpr int kEmitKeyType = 4;
constexpr float kMuzzleAhead = 25.0f; // gunPos += xVec * 25

struct Summary {
    int shots = 0;              // shells actually spawned
    int intervalTicks = kIntervalTicks;
    bool sameTick = true;
    bool primaryFirst = false;  // slot order: shell 0 carries the camera/rumble flag
    float maxSpreadDeg = 0.0f;  // largest pairwise angle between the shell velocities
};

inline float angleDeg(const P2GroinkVec3& a, const P2GroinkVec3& b)
{
    const float la = std::sqrt(a.x * a.x + a.y * a.y + a.z * a.z);
    const float lb = std::sqrt(b.x * b.x + b.y * b.y + b.z * b.z);
    if (!(la > 0.0f) || !(lb > 0.0f)) return 0.0f;
    float d = (a.x * b.x + a.y * b.y + a.z * b.z) / (la * lb);
    d = std::max(-1.0f, std::min(1.0f, d));
    return std::acos(d) * 57.2957795f;
}

// Summarise the shells one emit() call spawned.
inline Summary summarize(const P2GroinkVolley& pool, const P2GroinkVolley::Emission& e)
{
    Summary s;
    if (!e.valid) return s;
    s.shots = int(e.count);
    s.primaryFirst = e.count > 0 && pool.shell(e.slots[0]).primary;
    for (std::size_t i = 0; i < e.count; ++i)
        for (std::size_t j = i + 1; j < e.count; ++j)
            s.maxSpreadDeg = std::max(s.maxSpreadDeg, angleDeg(pool.shell(e.slots[i]).velocity, pool.shell(e.slots[j]).velocity));
    return s;
}

// Fixed-size expectation for a burst given the free nodes in the pool.
inline int expectedShots(std::size_t freeNodes) { return int(std::min<std::size_t>(freeNodes, std::size_t(kShots))); }

} // namespace p2groinkburst
