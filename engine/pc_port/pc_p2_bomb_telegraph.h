#pragma once
// Volatile Dweevil (BombOtakara, source id 93) carried-bomb telegraph policy.
// Engine-free so tools/p2_bomb_telegraph_test.cpp can check it.
//
// Pikmin 2 truth (pikmin2-research):
//   * The Dweevil carries a separate Bomb (bomb-rock) enemy. Once the Dweevil
//     forces it (BombOtakara.cpp:42-55 damageCallBack, :57-63 hipdrop,
//     :65-74 earthquake, :84 bombCallBack, OtakaraBase.cpp:699-707
//     stimulateBomb after a 1.5 s chase) the Bomb enters BOMB_Bomb
//     (bomb.cpp:403-409 forceBomb, bombState.cpp:97-103 init).
//   * StateBomb::exec (bombState.cpp:113-122): every frame it plays the loop
//     sound PSSE_EN_BOMB_LOOP and drains mHealth by the frame time
//     (addDamage(dt, 1)). The blast goes off 10 frames after mHealth <= 0
//     (bombState.cpp:115-120).
//   * The fuse length is the Bomb's own life, enemyparm fp00 = 4.5 s (retail
//     Bomb/enemyparm.txt, content output BombSarai/Bomb). The gauge is the
//     ordinary enemy life gauge: EnemyBase::doGetLifeGaugeParam
//     (enemyBase.cpp:2692-2710) shows mHealth / mMaxHealth at fp27 = 35 above
//     the bomb, EB_LifegaugeVisible is on by default (enemyBase.cpp:1078).
//   * The bomb glow (efx::TBombrockLight) is created the first time the bomb
//     animates with mHealth < 4.0 (bomb.cpp:203-207).
// The flash rate and the tick cadence are this port's telegraph (the decomp
// has no flash parameter; the retail flash lives in the HitLoop animation and
// the looped JAudio effect). P1 has no fuse flash either, only the bomb-rock
// set-down wheel (itemAI.cpp:436-466, bombItem.cpp:167-178).
#include <cmath>

namespace p2bombtelegraph {

inline constexpr float kBombLife = 4.5f;          // Bomb enemyparm fp00
inline constexpr float kLightBelowHealth = 4.0f;  // bomb.cpp:203
inline constexpr float kBlastDelaySeconds = 10.0f / 30.0f; // bombState.cpp:116 (10 frames)
inline constexpr float kGaugeHeight = 35.0f;      // Bomb enemyparm fp27
inline constexpr float kFlashSlowPeriod = 0.50f;  // port telegraph: first pulse
inline constexpr float kFlashFastPeriod = 0.07f;  // port telegraph: last pulse
inline constexpr float kTotalSeconds = kBombLife + kBlastDelaySeconds;

// Health ratio shown by the gauge (mHealth / mMaxHealth), clamped to [0, 1].
inline float gaugeRatio(float health) {
    const float r = health / kBombLife;
    return r < 0.0f ? 0.0f : (r > 1.0f ? 1.0f : r);
}

// Flash/tick period for a gauge ratio: slow at a full gauge, fast at empty,
// quadratic so most of the speed-up happens near detonation.
inline float flashPeriod(float ratio) {
    const float r = ratio < 0.0f ? 0.0f : (ratio > 1.0f ? 1.0f : ratio);
    const float t = 1.0f - r;
    return kFlashSlowPeriod - (kFlashSlowPeriod - kFlashFastPeriod) * t * t;
}

struct Step {
    bool pulse = false;     // a new flash started this step (tick + spark)
    bool lightOn = false;   // TBombrockLight threshold crossed this step
    bool detonate = false;  // blast now
};

struct Burn {
    bool burning = false;
    bool detonated = false;
    bool lightLogged = false;
    float health = kBombLife;
    float sinceEmpty = 0.0f; // time since health hit 0 (blast after kBlastDelaySeconds)
    float phase = 0.0f;      // flash phase, one unit per flash
    int pulses = 0;

    void ignite() {
        if (burning || detonated) return;
        burning = true;
        health = kBombLife;
        sinceEmpty = 0.0f;
        phase = 0.0f;
        pulses = 0;
        lightLogged = false;
    }

    float ratio() const { return gaugeRatio(health); }
    float elapsed() const { return (kBombLife - health) + sinceEmpty; }
    // Flash is lit for the first half of each phase.
    bool flashOn() const { return burning && (phase - std::floor(phase)) < 0.5f; }

    Step step(float dt) {
        Step out;
        if (!burning || detonated || !(dt > 0.0f)) return out;
        const bool wasAbove = health >= kLightBelowHealth;
        if (health > 0.0f) {
            health -= dt; // addDamage(sys->mDeltaTime, 1.0f)
            if (health < 0.0f) health = 0.0f;
        } else {
            sinceEmpty += dt;
        }
        if (wasAbove && health < kLightBelowHealth && !lightLogged) {
            lightLogged = true;
            out.lightOn = true;
        }
        const float before = phase;
        phase += dt / flashPeriod(ratio());
        if (pulses == 0 || std::floor(phase) > std::floor(before)) {
            out.pulse = true;
            ++pulses;
        }
        if (health <= 0.0f && sinceEmpty >= kBlastDelaySeconds) {
            detonated = true;
            burning = false;
            out.detonate = true;
        }
        return out;
    }
};

// The flash/tick clock alone, for a bomb whose fuse is simulated elsewhere
// (the Careening Dirigibug bombs, pc_p2_bombsarai_bomb.h): same ramp as
// Burn (flashPeriod of the gauge ratio), same lit-half-of-each-phase rule, a
// pulse on the first step and on every new phase.
struct Pulse {
    float phase = 0.0f;
    int pulses = 0;
    // Advances by dt at the given gauge ratio; true when a new flash starts.
    bool step(float dt, float ratio) {
        if (!(dt > 0.0f)) return false;
        const float before = phase;
        phase += dt / flashPeriod(ratio);
        if (pulses == 0 || std::floor(phase) > std::floor(before)) {
            ++pulses;
            return true;
        }
        return false;
    }
    bool on() const { return pulses > 0 && (phase - std::floor(phase)) < 0.5f; }
    void reset() { phase = 0.0f; pulses = 0; }
};

// Bomb placement on the Dweevil's back, in the actor's local frame (model
// units of the baked Dweevil poses, body about 41 high): the source carries
// the Bomb on the `otakara` joint (OtakaraBase.cpp:665).
struct Offset { float x, y, z; };
inline constexpr Offset kBackOffset = {0.0f, 40.0f, -4.0f};
inline constexpr float kBombScale = 1.8f;
// The bomb swells a little on each lit flash so the pulse reads at a glance.
inline constexpr float kFlashSwell = 1.2f;

// Flash colour multiplier for the bomb materials. Unlit frames stay dim and
// lit frames go bright red-orange so the pulse is unmistakable.
struct Tint { unsigned char r, g, b; };
inline Tint flashTint(bool on, float ratio) {
    if (!on) return Tint{110, 100, 100};
    // Brighten and redden as the gauge empties.
    const float t = 1.0f - (ratio < 0.0f ? 0.0f : (ratio > 1.0f ? 1.0f : ratio));
    return Tint{255, (unsigned char)(200.0f - 120.0f * t), (unsigned char)(170.0f - 120.0f * t)};
}

} // namespace p2bombtelegraph
