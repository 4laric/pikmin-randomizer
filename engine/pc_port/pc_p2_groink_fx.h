#pragma once

#include "pc_p2_groink.h"
#include "pc_p2_groink_volley.h"

#include <array>
#include <cmath>
#include <cstddef>
#include <vector>

// #892: visible Gatling Groink shells.
//
// Source (MiniHoudaiShotGun.cpp, MiniHoudai.cpp) draws a Groink volley only
// through particle effects; there is no shell model:
//   emitShotGun         efx::TChibiShoot on the kuti head matrix, once per
//                       volley (:1385).
//   startShotGun        efx::TChibiShell created per shell, following the
//                       shell's mPosition along its velocity (:69-80).
//   update, floor/wall  shell raised to ground+10, effectPos = position - 10 y;
//                       efx::THdamaHit3 when that point is in water, else
//                       efx::TChibiHit; the TChibiShell fades (:98-131).
//   update, >1000 away  the TChibiShell fades, no hit effect (:141-148).
//   onKill              forceFinishShotGun fades every live shell (:1774).
//   Dead KEYEVENT_2     createDeadBombEmitEffect: TChibiShoot on kuti
//                       (MiniHoudai.cpp:766-779, MiniHoudaiState.cpp:56).
//
// P2 JPA2 particles are not portable to the P1 zen particle system, so each
// source effect maps to the closest existing P1 effect (port adaptation, same
// approach as pc_p2_otakara_fx.h):
//   TChibiShoot  -> EFF_Beatle_ShootRockHalo + EFF_Beatle_ShootRockSpecks, the
//                   P1 cannon-beetle rock-shot muzzle burst, emitted along the
//                   muzzle axis (TAIbeatle.cpp:573-585 does the same).
//   TChibiShell  -> a short one-shot puff at the shell position every
//                   kTrailInterval source ticks (a visible streak). One-shots
//                   self-terminate, so no generator handle is ever retained
//                   (a stored handle outlives its generator in the P1 pool).
//   TChibiHit    -> KandoEffect::BombLight, the P1 light bomb blast
//                   (itemAI.cpp:484).
//   THdamaHit3   -> EFF_P_Bubbles, the P1 water-landing splash
//                   (itemAI.cpp:189-191).
// Charge/smoke body effects (TChibiCharge, TChibiSmokeS/L, TChibiDeadLight,
// TChibiDeadMouth/Se) and shell sounds are out of scope here.
//
// P2GroinkShellFx turns one source tick of the engine-free FSM into ordered
// effect commands. It is engine-free; the host spawns them.

enum class P2GroinkFxKind { Shoot, Trail, Hit, WaterHit };

struct P2GroinkFxCommand {
    P2GroinkFxKind kind = P2GroinkFxKind::Shoot;
    std::size_t slot = 0; // shell slot for Trail/Hit/WaterHit
    P2GroinkVec3 pos;
    P2GroinkVec3 dir;     // unit emit direction for Shoot
};

// Everything one Fsm::tick exposed that the effects need.
struct P2GroinkFxTick {
    bool volley = false;          // TickOutput::volley > 0 (TChibiShoot)
    P2GroinkMuzzle volleyMuzzle;  // the basis the shells were emitted from
    bool deadBomb = false;        // Dead KEYEVENT_2
    P2GroinkMuzzle deadMuzzle;
    int terminals = 0;            // TickOutput::terminals (fresh only when > 0)
    const P2GroinkVolley* shells = nullptr;
};

// Host water query at an impact point (source mapMgr->findWater).
using P2GroinkWaterFn = bool (*)(void* context, const P2GroinkVec3& at);

class P2GroinkShellFx {
public:
    static constexpr int kTrailInterval = 3; // source ticks between trail puffs (10 Hz)

    void reset() {
        mLive.fill(false);
        mAge.fill(0);
    }

    // One source tick: the volley's TChibiShoot, a trail puff for live
    // shells, and the terminal effects of this tick's shell update.
    std::vector<P2GroinkFxCommand> onTick(const P2GroinkFxTick& t, P2GroinkWaterFn water, void* context) {
        std::vector<P2GroinkFxCommand> out, hits;
        if (t.volley) out.push_back(shoot(t.volleyMuzzle));
        if (t.deadBomb) out.push_back(shoot(t.deadMuzzle));
        if (!t.shells) return out;
        std::array<bool, P2GroinkVolley::kCapacity> ended{};
        if (t.terminals > 0) {
            const std::size_t n = t.shells->terminalCount();
            for (std::size_t i = 0; i < n && i < P2GroinkVolley::kCapacity; ++i) {
                const auto& term = t.shells->terminals()[i];
                if (term.slot >= P2GroinkVolley::kCapacity) continue;
                ended[term.slot] = true;
                const auto reason = term.step.reason;
                if (!term.step.valid
                    || (reason != P2GroinkTerminalReason::Floor && reason != P2GroinkTerminalReason::Wall))
                    continue; // OutOfRange / Invalid: the shell fades with no hit effect
                P2GroinkFxCommand c;
                c.slot = term.slot;
                c.pos = term.step.end; // already the source effectPos (raised position - 10 y)
                c.kind = (water && water(context, c.pos)) ? P2GroinkFxKind::WaterHit : P2GroinkFxKind::Hit;
                hits.push_back(c);
            }
        }
        for (std::size_t slot = 0; slot < P2GroinkVolley::kCapacity; ++slot) {
            const P2GroinkShell s = t.shells->shell(slot);
            if (!s.active || ended[slot]) {
                mLive[slot] = false;
                mAge[slot] = 0;
                continue;
            }
            // First sight of a live shell is its TChibiShell creation: puff at once.
            mAge[slot] = mLive[slot] ? mAge[slot] + 1 : 0;
            mLive[slot] = true;
            if (mAge[slot] % kTrailInterval != 0) continue;
            P2GroinkFxCommand c;
            c.kind = P2GroinkFxKind::Trail;
            c.slot = slot;
            c.pos = s.position;
            out.push_back(c);
        }
        out.insert(out.end(), hits.begin(), hits.end());
        return out;
    }

    bool live(std::size_t slot) const { return slot < mLive.size() && mLive[slot]; }

private:
    static P2GroinkFxCommand shoot(const P2GroinkMuzzle& m) {
        P2GroinkFxCommand c;
        c.kind = P2GroinkFxKind::Shoot;
        c.pos = m.column3;
        const float len = std::sqrt(m.column0.x * m.column0.x + m.column0.y * m.column0.y + m.column0.z * m.column0.z);
        if (len > 0.0f) c.dir = {m.column0.x / len, m.column0.y / len, m.column0.z / len};
        return c;
    }

    std::array<bool, P2GroinkVolley::kCapacity> mLive{};
    std::array<int, P2GroinkVolley::kCapacity> mAge{};
};

// P1 EffectMgr::effTypeTable ids used by the host (include/EffectMgr.h).
constexpr int kP2GroinkFxShootHalo = 137;  // EFF_Beatle_ShootRockHalo
constexpr int kP2GroinkFxShootSpecks = 138; // EFF_Beatle_ShootRockSpecks
constexpr int kP2GroinkFxTrail = 26;       // EFF_BombLight_FireGlow (bi_kona2.pcr)
constexpr int kP2GroinkFxWater = 15;       // EFF_P_Bubbles

// Engine seam (pc_p2_groink_fx.cpp): spawns one command's P1 effects; a no-op
// under P2_GROINK_FX_NO_ENGINE. Never retains a generator.
void pc_p2_groink_fx_spawn(const P2GroinkFxCommand& c);
