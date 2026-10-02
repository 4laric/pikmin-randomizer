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

// Only previously visited guides may be replayed. Missing or malformed
// observations refuse rather than selecting a future shortcut.
inline int pc_kochappy_route_reentry(const double* spans, int count, int next) {
    if (!spans || count < 1 || count > 128 || next < 1 || next > count) return -1;
    int chosen=-1;double best=512.;
    for(int i=0;i<next;++i) {
        if(!std::isfinite(spans[i]) || spans[i]<0) return -1;
        if(spans[i]<best){best=spans[i];chosen=i;}
    }
    return chosen;
}
struct PcKochappyReentryProgress {
    int count=0;
    int retainedNext=-1;
    bool mayBegin(int next) const {
        return next>0 && count<4 && (retainedNext<0 || next>retainedNext);
    }
    bool begin(int next, int chosen) {
        if(!mayBegin(next) || chosen<0 || chosen>=next) return false;
        ++count;retainedNext=next;return true;
    }
};
