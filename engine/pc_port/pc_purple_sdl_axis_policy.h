#pragma once
#include <cmath>

// The fixture emits integer native units as SDL axis*256. pc_window samples
// each axis independently only when abs(SDL axis)>loaded dead zone*256.
// This models that read-only sampling step; it never changes pad settings.
inline int pcPurpleSdlPulseSampleAxis(int nativeAxis,int deadZone) {
    return nativeAxis < -deadZone || nativeAxis > deadZone ? nativeAxis : 0;
}

inline bool pcPurpleCursorBandSafe(float magnitude,float neutral,float cursor,float targetLength) {
    return std::isfinite(magnitude) && std::isfinite(neutral) && std::isfinite(cursor)
        && std::isfinite(targetLength) && magnitude>neutral && magnitude<=cursor && targetLength==0.f;
}
class PcPurplePoseProbeBudget {
public:
    bool take() { if(frames_>=64)return false; ++frames_; return true; }
    unsigned frames() const { return frames_; }
private:
    unsigned frames_=0;
};
