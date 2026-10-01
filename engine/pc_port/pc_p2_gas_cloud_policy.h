#pragma once
// Poisoned-Pikmin indicator (owner playtest 2026-09-30: "need like a purple
// cloud around the head of the poison pikmin"). Engine-free placement and
// lifecycle policy; the engine side is pc_p2_gas_cloud.cpp.
//
// How the port represents a gassed Pikmin: P1 has no poison. Every P2 gas
// source (Titan Comedy Bomb, Caustic/Munge Dweevil, GasHiba, Kogane ...) goes
// through InteractGas::actPiki -> PIKISTATE_Panic (PikiPanicState, the
// PIKIPANIC_Gas flavour; interactBattle.cpp), which kills the Pikmin from poison
// when mSurvivalTimer runs out (pikiState.cpp PikiPanicState::exec). The
// indicator therefore follows that state, not the emitter: one cloud per Pikmin
// from PikiPanicState::init for exactly as long as the state runs, stopped by
// PikiPanicState::cleanup (cured or left) and Piki::doKill (death).
//
// P2 source: the poison status effect is the Pikmin's gas/panic particle
// (efx::TPkGas-style head cloud). P1 has no such asset, so the cloud is the P1
// Puffstool poison cloud (EFF_Kinoko_PostAttackCloud) puffed at the head.
#include "pc_p2_attack_fx.h"

namespace p2gascloud {

constexpr float HEAD_HEIGHT = 16.0f;   // world units above the Pikmin position
constexpr float PUFF_RADIUS = 5.0f;    // scatter around the head
constexpr unsigned PUFF_EVERY = 3;     // update ticks between puffs
constexpr int PUFFS = 2;               // puffs per emission
constexpr short PUFF_LIFE = 24;        // generator frames: a short tail, so a missed stop cannot linger
constexpr float PUFF_SCALE = 1.4f;
constexpr int EFFECT = p2attackfx::EFF_Kinoko_AttackCloud;

enum class Why { Cured, Death, Reset };
inline const char* whyName(Why w) {
    switch (w) {
    case Why::Cured: return "cured_or_left";
    case Why::Death: return "death";
    case Why::Reset: return "reset";
    }
    return "?";
}

// Puff points for one emission around the head at (x,y,z); deterministic in
// `tick` and `salt` (the Pikmin identity) so two Pikmin never puff in lockstep.
inline int layout(float x, float y, float z, unsigned tick, unsigned salt, p2attackfx::Point* out) {
    int n = 0;
    for (int i = 0; i < PUFFS; ++i) {
        const float a = p2attackfx::hashSigned(tick * 7u + salt * 13u + unsigned(i) * 101u) * 3.14159265f;
        const float u = p2attackfx::hashSigned(tick * 11u + salt * 31u + unsigned(i)) * 0.5f + 0.5f;
        const float r = PUFF_RADIUS * (0.4f + 0.6f * u);
        out[n++] = {p2attackfx::Kind::Body, x + r * __builtin_sinf(a), y + HEAD_HEIGHT + 0.5f * r * __builtin_cosf(a * 2.0f),
                    z + r * __builtin_cosf(a), PUFF_SCALE, 0.0f, 1.0f};
    }
    return n;
}

// True on the updates that emit (every PUFF_EVERY-th, starting with the first).
inline bool emitsOn(unsigned tick) { return tick % PUFF_EVERY == 0; }

struct Cloud {
    bool active = false;
    unsigned ticks = 0, points = 0, started = 0, stopped = 0;
    bool begin() {
        if (active) return false;
        active = true;
        ticks = points = 0;
        ++started;
        return true;
    }
    bool end() {
        if (!active) return false;
        active = false;
        ++stopped;
        return true;
    }
    unsigned outstanding() const { return started - stopped; }
};

} // namespace p2gascloud
