#pragma once
// Engine-free Otakara elemental attack window + effect lifecycle (Dweevil family 59-62).
//
// Owner playtest 2026-09-30: "visual indicator for the attack itself, not just for how it
// affects the pikmin" and "check for lingering visual effects after its attack is done".
//
// What the source does (OtakaraBase.cpp / OtakaraBaseState.cpp / Fire|Water|Gas|ElecOtakara.cpp):
//   * StateFlick / StateItemFlick init (OtakaraBaseState.cpp:71-84, 605-617): startChargeEffect()
//     -- a charge emitter (efx::TOtaChargefire / Chargewat / Chargegas / Chargeelec) that
//     FOLLOWS the center joint for the whole wind-up (Fire|Water|Gas|ElecOtakara.cpp
//     setupEffect/startChargeEffect).
//   * Flick event type 3 (bank frame 35, OtakaraBaseState.cpp:109-114): finishChargeEffect()
//     (fade), createDisChargeEffect() (efx::TOtaFire / Wat / Gas / Elec burst at mPosition)
//     and mAttackActiveTimer = 0.
//   * Obj::doUpdateCommon (OtakaraBase.cpp:85-92) runs EVERY frame, in any state: while
//     mAttackActiveTimer < 1.0 it adds dt and calls attackTarget(), which calls
//     interactCreature() (InteractFire/Bubble/Gas/Denki) on every live Navi and Pikmin within
//     fp22 (attack hit range, 60) on XZ and within (y - fp21, y + fp20) = (-25, +25) in height
//     (OtakaraBase.cpp:580-610). The discharge therefore lasts one second, not one frame, and
//     continues past the end of the attack clip (50 frames = 1.67 s; discharge starts at frame
//     35 = 1.17 s, so ~0.5 s of it runs during the next state).
//   * Stopping: onKill, doStartStoneState, doStartEarthquakeState and doStartEarthquakeFitState
//     all call finishChargeEffect() (OtakaraBase.cpp:65-69, 242-248, 265-271, 288-294).
//
// What the port did wrong (P2_OTAKARA_FX in pc_p2_otakara_fx.h): one P1 particle generator per
// discharge, spawned at the feet, never stopped -- pc_p2_otakara_fx_update/clear/reset had no
// caller, so looping emitters (EFF_Hiba_Fire is a flame-thrower emitter that P1's TAIhibaA stops
// with finish()) stayed alive at the spot after the attack, and there was no charge visual at
// the Dweevil at all. The Ledger below is the start/stop bookkeeping the glue drives so every
// start has exactly one stop (P2_OTAKARA_FX_START / P2_OTAKARA_FX_STOP log pairs).
namespace p2otakaraattack {

constexpr float kIdle = 12800.0f;   // OtakaraBase.cpp:45 mAttackActiveTimer initial (inactive)
constexpr float kWindow = 1.0f;     // OtakaraBase.cpp:87 attack active while timer < 1.0
constexpr float kRadius = 60.0f;    // fp22 attack hit range (mAttackRadius), all five species
constexpr float kHeightUp = 25.0f;  // fp20 max attack range: targetY < y + 25
constexpr float kHeightDown = 25.0f; // fp21 max attack angle: targetY > y - 25

// One attack frame of doUpdateCommon. Returns true when attackTarget() must run this frame.
inline bool windowStep(float& timer, float dt) {
    if (timer < kWindow) {
        timer += dt;
        return true;
    }
    return false;
}
inline bool windowActive(float timer) { return timer < kWindow; }
inline void windowOpen(float& timer) { timer = 0.0f; } // Flick event 3

// attackTarget() reach test (OtakaraBase.cpp:580-610): dxz/dy are target minus Dweevil.
inline bool inReach(float dx, float dz, float dy) {
    return dy < kHeightUp && dy > -kHeightDown && dx * dx + dz * dz < kRadius * kRadius;
}

enum class Kind { Charge = 0, Discharge = 1 };
enum class Reason { Discharge, WindowEnd, Dead, Forget, Teardown, Abort };

inline const char* kindName(Kind k) { return k == Kind::Charge ? "charge" : "discharge"; }
inline const char* reasonName(Reason r) {
    switch (r) {
    case Reason::Discharge: return "discharge_start";
    case Reason::WindowEnd: return "window_end";
    case Reason::Dead: return "dead";
    case Reason::Forget: return "forget";
    case Reason::Teardown: return "teardown";
    case Reason::Abort: return "abort";
    }
    return "unknown";
}

// Per-actor start/stop bookkeeping. start() returns false when the kind is already on (the
// caller then spawns nothing, so no generator can be orphaned); stop() returns false when it
// is already off (the caller then kills nothing).
struct Ledger {
    bool on[2] = {false, false};
    unsigned starts[2] = {0, 0};
    unsigned stops[2] = {0, 0};

    bool start(Kind k) {
        if (on[int(k)]) return false;
        on[int(k)] = true;
        ++starts[int(k)];
        return true;
    }
    bool stop(Kind k) {
        if (!on[int(k)]) return false;
        on[int(k)] = false;
        ++stops[int(k)];
        return true;
    }
    bool anyOn() const { return on[0] || on[1]; }
    // Every start has a matching stop.
    bool balanced() const { return !anyOn() && starts[0] == stops[0] && starts[1] == stops[1]; }
};

// Which effects the window end / state changes stop. The charge fades at event 3; the
// discharge ends with the one-second window; dying or being forgotten stops both.
struct Stops {
    bool charge;
    bool discharge;
};
inline Stops onDischargeEvent() { return {true, false}; }
inline Stops onWindowEnd() { return {false, true}; }
inline Stops onDead() { return {true, true}; }
inline Stops onForget() { return {true, true}; }

} // namespace p2otakaraattack
