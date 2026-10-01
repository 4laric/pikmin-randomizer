// Pure, engine-free pieces of the Anode Beetle (ElecBug, EnemyID 28) state
// machine so the exit conditions can be unit tested (tools/p2_elecbug_fsm_test.cpp).
//
// Source: decomp ElecBugState.cpp. Key-event types in the converted bank are
// 0 = loop start, 1 = END (the point finishMotion() lets the clip stop at),
// 2 = KEYEVENT_2.
//   * StateReverse plays ELECBUGANIM_Turn (flip over, then loop belly-up). After
//     FlipTime it calls finishMotion() and leaves on the END key -> StateReturn.
//   * StateReturn plays ELECBUGANIM_Recover. The converted recover clip carries
//     NO key events, so the END key never fires: the exit is the clip length.
//   * StateReturn END, StateCharge (no partner) and StateDischarge END all go
//     to StateTurn, never back to Wait/Charge. Charge is only entered from
//     Turn/Move once mInactiveTimer > 15 (not from player sight).
#pragma once
#include <cmath>
#include <cstdlib>
#include <string>

namespace p2elecbug {

constexpr float kFps = 30.0f;
constexpr float kChargeInactiveLimit = 15.0f; // source mInactiveTimer > 15.0f

struct ClipKeys {
    int frames = 0;
    int loopStart = -1; // key type 0
    int end = -1;       // key type 1
};

// Parses the bank events token ("30:0,69:1", or "-" for none).
inline ClipKeys parseKeys(int frames, const std::string& events) {
    ClipKeys k;
    k.frames = frames;
    size_t i = 0;
    while (i < events.size()) {
        size_t comma = events.find(',', i);
        const std::string item = events.substr(i, comma == std::string::npos ? std::string::npos : comma - i);
        const size_t colon = item.find(':');
        if (colon != std::string::npos) {
            const int frame = std::atoi(item.substr(0, colon).c_str());
            const int type = std::atoi(item.substr(colon + 1).c_str());
            if (type == 0 && k.loopStart < 0) k.loopStart = frame;
            if (type == 1) k.end = frame;
        }
        if (comma == std::string::npos) break;
        i = comma + 1;
    }
    return k;
}

struct ReverseClip {
    float frame = 0.0f;
    bool finished = false; // the END key was reached after finishMotion()
};

// Source-frame position of the Reverse (Turn) clip at `t` seconds. Plays once to
// the loop start, loops loopStart..end, and once `t >= flipTime` the clip is
// "finished": it runs on to the END key and then the state exits.
inline ReverseClip reverseClip(const ClipKeys& k, float t, float flipTime) {
    ReverseClip r;
    const float frame = t * kFps;
    const int end = k.end >= 0 ? k.end : (k.frames > 0 ? k.frames - 1 : 0);
    if (k.loopStart < 0 || k.loopStart >= end) {
        r.frame = frame > float(end) ? float(end) : frame;
        r.finished = t >= flipTime && frame >= float(end);
        return r;
    }
    const float span = float(end - k.loopStart);
    if (t < flipTime) {
        r.frame = frame < float(k.loopStart) ? frame
                                             : float(k.loopStart) + std::fmod(frame - float(k.loopStart), span);
        return r;
    }
    // finishMotion() was requested at flipTime: keep the current loop position
    // and run to the END key.
    const float ft = flipTime * kFps;
    float at = ft < float(k.loopStart) ? ft
                                       : float(k.loopStart) + std::fmod(ft - float(k.loopStart), span);
    const float remaining = float(end) - at;
    const float done = frame - ft;
    r.finished = done >= remaining;
    r.frame = r.finished ? float(end) : at + done;
    return r;
}

// StateReturn exit: the converted recover clip has no END key, so use its length.
inline bool recoverDone(float stateTime, int clipFrames) {
    const float len = clipFrames > 0 ? float(clipFrames) / kFps : 1.0f;
    return stateTime >= len;
}

// Source ElecBug::checkInteract geometry (ElecBug.cpp:411-479). `a` is the
// discharging beetle, `b` its partner, `c` a Pikmin/Navi. The band is a
// segment a->b, |lateral| < 10, |vertical| < 15 (perpendicular axis).
struct V3 { float x, y, z; };
constexpr float kArcStart = 8.0f / kFps; // KEYEVENT_2 at frame 8 lights the arc
inline bool inArcBand(const V3& a, const V3& b, const V3& c) {
    auto sub = [](V3 p, V3 q) { return V3{p.x - q.x, p.y - q.y, p.z - q.z}; };
    auto dot = [](V3 p, V3 q) { return p.x * q.x + p.y * q.y + p.z * q.z; };
    auto cross = [](V3 p, V3 q) { return V3{p.y * q.z - p.z * q.y, p.z * q.x - p.x * q.z, p.x * q.y - p.y * q.x}; };
    auto norm = [&](V3 p) { const float l = std::sqrt(dot(p, p)); return l > 1e-6f ? V3{p.x / l, p.y / l, p.z / l} : p; };
    const V3 d = sub(b, a);
    const float dist = std::sqrt(dot(d, d));
    if (dist < 1e-3f) return false;
    const V3 sep = norm(d);
    const V3 lateral = norm(cross(V3{0.0f, 1.0f, 0.0f}, sep));
    const V3 perp = norm(cross(sep, lateral));
    const V3 r = sub(c, a);
    if (!(std::fabs(dot(lateral, r)) < 10.0f)) return false;
    const float along = dot(sep, r);
    if (!(along < dist && along > 0.0f)) return false;
    return std::fabs(dot(perp, r)) < 15.0f;
}

// Turn/Move end: charge only once the inactivity timer passed the source limit.
inline bool chargeDue(float inactiveTimer) { return inactiveTimer > kChargeInactiveLimit; }

} // namespace p2elecbug
