#pragma once

// Shared by the PC whistle and its boundary regression tests.
constexpr float PC_WHISTLE_FULL_HOLD_SECONDS = 0.6f;
inline float pc_whistle_fraction(float heldSeconds)
{
    const float progress = heldSeconds / PC_WHISTLE_FULL_HOLD_SECONDS;
    return 0.35f + 0.65f * (progress < 0.0f ? 0.0f : progress > 1.0f ? 1.0f : progress);
}
inline bool pc_whistle_recall_workers(float heldSeconds, bool down)
{
    return down && heldSeconds >= PC_WHISTLE_FULL_HOLD_SECONDS;
}

// A fresh press within 350 ms of the prior press recalls workers for this whistle.
struct PcWhistleTapState {
    double lastPress = -1.0;
    bool recallWorkers = false;
    bool press(double now) {
        recallWorkers = lastPress >= 0.0 && now > lastPress && now - lastPress <= 0.35;
        lastPress = now;
        return recallWorkers;
    }
};
