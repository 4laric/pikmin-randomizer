#pragma once
#include <algorithm>
#include <cmath>
namespace p2sprays {
// GPVE01 rev0 user/Abe/piki/pikiParms.txt P007/P008/P009.
constexpr float Duration = 40.0f, Damage = 10.0f, RunSpeed = 190.0f;
constexpr int BerriesPerSpray = 10; // user/Kando/aiConstants.txt dopecount
struct SpicyStatus {
    float remaining = 0;
    bool active() const { return remaining > 0; }
    void begin() { remaining = Duration; }
    void clear() { remaining = 0; }
    // Validated campaign adoption preserves remaining time; no use replay.
    bool restore(float seconds) {
        if (!std::isfinite(seconds) || seconds < 0 || seconds > Duration) return false;
        remaining = seconds;
        return true;
    }
    // Source doAnimation clock: gameplay time, never wall clock or paused UI.
    bool tick(float dt, bool gameplay) {
        if (!gameplay || !active() || !std::isfinite(dt) || dt <= 0) return false;
        remaining = std::max(0.0f, remaining - dt);
        return !active();
    }
    float animationRate() const { return active() ? 2.0f : 1.0f; }
};
}
