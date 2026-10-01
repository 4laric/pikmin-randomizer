#pragma once
// Titan Dweevil (BigTreasure, #246) attack visuals: where the four weapon
// effects go each source tick. Visual only and engine-free: it reads the
// element runtime (pc_p2_bigtreasure_elements.h) and writes points for the
// shared attack-effect helpers (pc_p2_attack_fx.h); it never changes a node,
// ratio or hit.
//
// What P2 draws (native/pikmin2-research BigTreasureAttack.cpp):
//   Fire   (Flare Cannon)    efx::TOootaFire on the otakara_fire_eff joint matrix, created at
//                            startFireAttack (:1213-1214) with the attack scale (1.0 normal / 1.25
//                            damaged, parms ff00/ff10) and faded at finish (:1276). Nodes sweep 200.
//   Gas    (Comedy Bomb)     one efx::TOootaGas per arm (3 normal / 4 damaged) at the gas emit
//                            position and the arm angle, created at startGasAttack (:1372) and faded
//                            at finish (:1731). Arm nodes grow to 480 units.
//   Water  (Monster Pump)    efx::TOootaWbShot at the otakara_water_eff joint on every shot (:1808),
//                            efx::TOootaWbomb on each bubble (:256-276) and TOootaWbHit where it
//                            lands (:2177-2180).
//   Elec   (Shock Therapist) efx::TOootaElecLeg on all 4x3 leg segments (:2340), TOootaElecAttack1 at
//                            the anchor (:2351-2352), then ElecAttack2 + TOootaPhouden + TOootaElec
//                            arcs between chained nodes (:2716-2737); TOootaElecparts follows each
//                            visible node (:387).
// The port layers the closest P1 effects along the same rays, arm angles, node positions and chain
// links.
#include "pc_p2_attack_fx.h"
#include "pc_p2_bigtreasure_elements.h"

#include <cmath>

namespace p2titanfx {

using p2attackfx::Element;
using p2attackfx::Kind;
using p2attackfx::Point;

constexpr int MAX_POINTS = 120;

// Source leg chain for the elec crackle: hip to gait foot per leg (4 legs).
struct Legs {
    bool set = false;
    float hip[4][3] = {};
    float foot[4][3] = {};
};

struct State {
    unsigned tick = 0;
    bool waterWasActive[P2BigTreasureWaterPolicy::kCapacity] = {};
    float waterLast[P2BigTreasureWaterPolicy::kCapacity][3] = {};
    void reset() { *this = State(); }
};

inline bool elementFor(int weapon, Element& out) {
    switch (weapon) {
    case P2BTWEAPON_Fire: out = Element::Fire; return true;
    case P2BTWEAPON_Gas: out = Element::Gas; return true;
    case P2BTWEAPON_Water: out = Element::WaterBall; return true;
    case P2BTWEAPON_Elec: out = Element::Elec; return true;
    default: return false;
    }
}

inline void unit2(float x, float z, float& dx, float& dz) {
    const float len = std::sqrt(x * x + z * z);
    if (len > 1e-6f) { dx = x / len; dz = z / len; } else { dx = 0.0f; dz = 1.0f; }
}

// Heavy layouts (gas puffs, elec arcs) emit every other tick so the pool stays
// under p2attackfx::MAX_LIVE_GENERATORS.
inline bool emitsOn(Element e, unsigned tick) {
    if (e == Element::Gas || e == Element::Elec) return (tick & 1u) == 0;
    return true;
}

// Fills `out` for the running element. Returns the point count (0 when the
// element has nothing visible yet or this tick is off-cadence). `element` is
// set whenever an element is running, even when the count is 0.
inline int layout(const P2BigTreasureElementRuntime& rt, const P2BigTreasureElementStats& stats, const Legs& legs,
                  State& st, Element& element, Point* out) {
    if (!rt.active() || !elementFor(rt.activeWeapon(), element)) return 0;
    const unsigned tick = st.tick++;
    const P2BigTreasureElementAim& aim = rt.aim();
    const P2BigTreasureVec3& o = rt.origin();
    const float gy = rt.groundHeight();
    const P2BigTreasureVec3 emit = aim.set ? aim.emit : P2BigTreasureVec3{o.x, gy + 60.0f, o.z};
    int n = 0;
    switch (rt.activeWeapon()) {
    case P2BTWEAPON_Fire: {
        if (!emitsOn(element, tick)) return 0;
        const P2BigTreasureFirePolicy& f = rt.firePolicy();
        float maxRatio = 0.0f;
        for (int i = 0; i < f.nodeCount(); ++i) maxRatio = std::fmax(maxRatio, f.nodeRatio(i));
        float dx = 0.0f, dz = 1.0f;
        if (aim.set) unit2(aim.direction.x, aim.direction.z, dx, dz);
        const float scale = f.params().scale;
        // The muzzle flame does not wait for the range to grow.
        const float range = std::fmax(p2attackfx::MIN_RANGE, P2BigTreasureFirePolicy::kExtent * scale * maxRatio);
        n = p2attackfx::layoutStream(Element::Fire, emit.x, emit.y, emit.z, dx, dz, range, tick, scale, out);
        break;
    }
    case P2BTWEAPON_Gas: {
        if (!emitsOn(element, tick)) return 0;
        const P2BigTreasureGasPolicy& g = rt.gasPolicy();
        float maxRatio = 0.0f;
        for (int i = 0; i < g.nodeCount(); ++i) maxRatio = std::fmax(maxRatio, g.nodeRatio(i));
        const float range = P2BigTreasureGasPolicy::kExtent * maxRatio;
        for (int arm = 0; arm < rt.gasArms() && n + p2attackfx::MAX_STREAM_POINTS <= MAX_POINTS; ++arm) {
            const float a = g.armAngle(arm);
            n += p2attackfx::layoutStream(Element::Gas, emit.x, emit.y - 15.0f, emit.z, std::sin(a), std::cos(a), range,
                                          tick, 1.0f, out + n);
        }
        break;
    }
    case P2BTWEAPON_Water: {
        // Monster Pump: TOootaWbShot at the mouth per shot, TOootaWbomb on each lobbed ball, TOootaWbHit
        // (splash + ground ring) where it bursts. One ball point per live node, a trail behind it along
        // the flight path, and the burst at the last flight position clamped to the ground.
        const P2BigTreasureWaterPolicy& w = rt.waterPolicy();
        if (stats.emits > 0) out[n++] = {Kind::Muzzle, emit.x, emit.y, emit.z, 1.0f, 0.0f, 1.0f};
        for (int i = 0; i < P2BigTreasureWaterPolicy::kCapacity && n < MAX_POINTS - 6; ++i) {
            const P2BigTreasureWaterNode& node = w.node(i);
            if (node.active) {
                float dx, dz;
                unit2(node.velocity.x, node.velocity.z, dx, dz);
                out[n++] = {Kind::Body, node.position.x, node.position.y, node.position.z, 1.0f, dx, dz};
                for (int k = 1; k <= 2; ++k)
                    out[n++] = {Kind::Trail, node.position.x - node.velocity.x * (1.0f / 30.0f) * float(k) * 1.5f,
                                node.position.y - node.velocity.y * (1.0f / 30.0f) * float(k) * 1.5f,
                                node.position.z - node.velocity.z * (1.0f / 30.0f) * float(k) * 1.5f, 1.0f, dx, dz};
                st.waterLast[i][0] = node.position.x;
                st.waterLast[i][1] = node.position.y;
                st.waterLast[i][2] = node.position.z;
            } else if (st.waterWasActive[i]) {
                const float gyHit = st.waterLast[i][1] < gy + 4.0f ? st.waterLast[i][1] : gy + 4.0f;
                out[n++] = {Kind::Tip, st.waterLast[i][0], gyHit, st.waterLast[i][2], 1.0f, 0.0f, 1.0f};
                out[n++] = {Kind::Ring, st.waterLast[i][0], gy + 1.0f, st.waterLast[i][2], 1.0f, 0.0f, 1.0f};
            }
            st.waterWasActive[i] = node.active;
        }
        break;
    }
    case P2BTWEAPON_Elec: {
        if (!emitsOn(element, tick)) return 0;
        const P2BigTreasureElecPolicy& e = rt.elecPolicy();
        // ElecAttack1: the glow at the anchor until the first chain forms.
        if (e.chainedCount() == 0) out[n++] = {Kind::Muzzle, emit.x, emit.y, emit.z, 1.2f, 0.0f, 1.0f};
        for (int i = 0; i < P2BigTreasureElecPolicy::kCapacity && n + p2attackfx::MAX_ARC_POINTS + 1 <= MAX_POINTS; ++i) {
            const P2BigTreasureElecNode& node = e.node(i);
            if (!node.active || !node.visible) continue;
            // TOootaElecparts follows the sphere (radius 20, raised by 20 in the trace).
            out[n++] = {Kind::Node, node.position.x, node.position.y + 20.0f, node.position.z, 1.0f, 0.0f, 1.0f};
            if (node.connected >= 0 && node.connected < P2BigTreasureElecPolicy::kCapacity) {
                const P2BigTreasureElecNode& p = e.node(node.connected);
                if (p.active)
                    n += p2attackfx::layoutArc(node.position.x, node.position.y + 20.0f, node.position.z, p.position.x,
                                               p.position.y + 20.0f, p.position.z, tick, unsigned(i), 10.0f, out + n);
            }
        }
        // TOootaElecLeg: crackle along hip -> foot on each leg.
        if (legs.set) {
            for (int l = 0; l < 4 && n + p2attackfx::MAX_ARC_POINTS <= MAX_POINTS; ++l)
                n += p2attackfx::layoutArc(legs.hip[l][0], legs.hip[l][1], legs.hip[l][2], legs.foot[l][0],
                                           legs.foot[l][1], legs.foot[l][2], tick, 100u + unsigned(l), 8.0f, out + n);
        }
        break;
    }
    default:
        break;
    }
    return n;
}

} // namespace p2titanfx
