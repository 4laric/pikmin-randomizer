#pragma once

// The fixture emits integer native units as SDL axis*256. pc_window samples
// each axis independently only when abs(SDL axis)>loaded dead zone*256.
// This models that read-only sampling step; it never changes pad settings.
inline int pcPurpleSdlPulseSampleAxis(int nativeAxis,int deadZone) {
    return nativeAxis < -deadZone || nativeAxis > deadZone ? nativeAxis : 0;
}
