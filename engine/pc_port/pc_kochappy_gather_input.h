#pragma once
#include <cmath>

// Input planning only. Recruitment remains the native strict XZ radius test.
enum class PcKochappyGatherInput { Refuse, Cursor, Walk };
inline PcKochappyGatherInput pc_kochappy_gather_input(float captainDistance,
    float cursorRadius, float whistleRadius, float neutral, float moveThreshold) {
    if (!std::isfinite(captainDistance) || !std::isfinite(cursorRadius)
        || !std::isfinite(whistleRadius) || !std::isfinite(neutral)
        || !std::isfinite(moveThreshold) || captainDistance < 0
        || cursorRadius <= 20 || whistleRadius <= 0 || neutral < 0
        || !(neutral < 22.f/74.f && 22.f/74.f <= moveThreshold
             && moveThreshold < 65.f/74.f)) return PcKochappyGatherInput::Refuse;
    // Reserve half the loaded whistle radius so cursor aiming has room to
    // recruit after the native expansion, rather than saturating out of reach.
    return captainDistance > cursorRadius + whistleRadius*.5f
        ? PcKochappyGatherInput::Walk : PcKochappyGatherInput::Cursor;
}
