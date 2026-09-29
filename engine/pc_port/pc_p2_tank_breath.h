#pragma once
// Fiery/Watery Blowhog breath exposure (issue #884). Engine-free: the runtime
// (pc_p2_tank.cpp doBreath) and tools/p2_tank_breath_test.cpp share this one
// decision path.
//
// Source basis (native/pikmin2-research, src/plugProjectNishimuraU):
//   Tank.cpp:266-319  Obj::isAttackable(true): every alive Navi/Pikmin inside
//                     the emitter box (|dy|<radius, |lateral|<radius,
//                     0<forward<range) gets interactCreature(). No count, no
//                     break; immunity is the receiver's decision
//                     (Ftank.cpp:121-125 InteractFire, Wtank.cpp:119-123
//                     InteractBubble; kandoU interactPiki.cpp:445-523).
//   Tank.cpp:325-368  Obj::emitCollideRatio: range = maxRange * timer using the
//                     pre-increment timer; timer seeds at 0.001 and grows 2/s.
//   TankState.cpp:862-900 StateAttack::exec: discharge runs while mIsBlowing,
//                     which KEYEVENT_2 sets after the discharge check, so the
//                     first discharge lands one frame after the key event.
// Retail constants come from experimental/pikmin2_tank_assets.py (attack.bca
// duration 95, enemyanimmgr events [[55,2]], frame-55 hoppe emitter origin
// (0.00004, 6.3969, 35.8169) model space). Map-trace clipping of the range
// (the traceMove branch of emitCollideRatio) is not ported.
#include <cmath>
#include <cstddef>
#include <vector>

namespace p2tankbreath {
constexpr int   ATTACK_CLIP_FRAMES = 95;       // attack.bca duration
constexpr int   KEYEVENT2_FRAME    = 55;       // attack.bca events [[55,2]]
constexpr float ANIM_FPS           = 30.0f;    // enemyAnimatorBase.cpp:4
constexpr float GROWTH_PER_SECOND  = 2.0f;     // Tank.cpp:352
constexpr float TIMER_SEED         = 0.001f;   // Tank.cpp:329
constexpr float EMIT_UP            = 6.3969f;  // hoppe emitter origin y, attack f55
constexpr float EMIT_FORWARD       = 35.8169f; // hoppe emitter origin z, attack f55

inline float keyEventSeconds() { return KEYEVENT2_FRAME / ANIM_FPS; }

// Tank.cpp:325-368 without the map trace. Returns the range for this frame.
struct Emit { float timer = 0.0f; float maxGrowth = 1.0f; };
inline float advance(Emit& e, float maxRange, float dt) {
    const float range = maxRange * e.timer; // pre-increment (:327)
    if (e.timer == 0.0f) { e.timer = TIMER_SEED; e.maxGrowth = 1.0f; }
    if (e.timer < e.maxGrowth) {
        e.timer += GROWTH_PER_SECOND * dt;
        if (e.timer > e.maxGrowth) e.timer = e.maxGrowth;
    }
    return range;
}

// Emitter frame from the actor ground position and heading. Native heading
// and source faceDir share dir = (sin h, 0, cos h) (Tank.cpp:268-271).
struct Frame { float ox, oy, oz, dx, dz, range, radius; };
inline Frame frame(float px, float py, float pz, float heading, float range, float radius) {
    const float dx = std::sin(heading), dz = std::cos(heading);
    return {px + dx * EMIT_FORWARD, py + EMIT_UP, pz + dz * EMIT_FORWARD, dx, dz, range, radius};
}

// Tank.cpp:300-305: |dy| < radius, |lateral| < radius, 0 < forward < range.
inline bool exposed(const Frame& f, float x, float y, float z) {
    const float rx = x - f.ox, ry = y - f.oy, rz = z - f.oz;
    if (!(std::fabs(ry) < f.radius)) return false;
    const float lat = -f.dz * rx + f.dx * rz; // (cos, 0, sin) = (-dir.z, 0, dir.x)
    if (!(std::fabs(lat) < f.radius)) return false;
    const float fwd = f.dx * rx + f.dz * rz;
    return fwd < f.range && fwd > 0.0f;
}

// Snapshot every alive exposed actor from the full population. No cap and no
// early exit: membership depends only on each actor's own state, so it does
// not depend on population order.
template <class T, class Pos, class Alive>
void collect(const Frame& f, const std::vector<T*>& population, Pos pos, Alive alive, std::vector<T*>& out) {
    for (T* a : population) {
        if (!a || !alive(a)) continue;
        float x, y, z;
        pos(a, x, y, z);
        if (exposed(f, x, y, z)) out.push_back(a);
    }
}

// Attack trigger: Tank.cpp:266-319 with check=false. The FSM enters
// TANK_Attack only through isAttackable(false) (TankState.cpp:91,184,724,811),
// which tests the same emitter box at the full mMaxAttackRange (ratio is not
// grown when check is false, Tank.cpp:277-280) and returns true for the first
// alive Pikmin/Navi inside it, making that creature mTargetCreature
// (:309-310). The trigger region therefore equals the full-range breath box,
// so every breath the FSM commits to reaches the actor that started it once
// the range has grown. Returns the first exposed actor, or nullptr.
inline Frame triggerFrame(float px, float py, float pz, float heading, float maxRange, float radius) {
    return frame(px, py, pz, heading, maxRange, radius);
}
template <class T, class Pos, class Alive>
T* firstExposed(const Frame& f, const std::vector<T*>& population, Pos pos, Alive alive) {
    for (T* a : population) {
        if (!a || !alive(a)) continue;
        float x, y, z;
        pos(a, x, y, z);
        if (exposed(f, x, y, z)) return a;
    }
    return nullptr;
}

// Stimulate a snapshot. A receiver may kill or remove any actor, including
// later snapshot entries, so liveness is re-checked before each stimulus.
// Returns the number of stimuli the receivers accepted.
template <class T, class Alive, class Stim>
int dispatch(const std::vector<T*>& snapshot, Alive alive, Stim stimulate) {
    int accepted = 0;
    for (T* a : snapshot) {
        if (!a || !alive(a)) continue;
        if (stimulate(a)) ++accepted;
    }
    return accepted;
}

// Per-breath evidence counters.
struct Stats {
    int frames = 0;
    int maxExposedPiki = 0;
    int maxExposedNavi = 0;
    float maxRange = 0.0f;
};
} // namespace p2tankbreath
