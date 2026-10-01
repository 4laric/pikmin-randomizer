#pragma once
// Adult Chappy-family behaviour policy (owner playtest 2026-09-30, Fiery Bulblax).
// Engine-free so tools/p2_chappy_adult_test.cpp pins it without the engine.
//
// Source of truth (native/pikmin2-research):
//   src/plugProjectYamashitaU/chappyState.cpp   StateSleep / StateTurn / StateWalk /
//                                               StateTurnToHome / StateGoHome,
//                                               StateCautionBase::cautionProc
//   src/plugProjectYamashitaU/ChappyBase.cpp    Obj::isWakeup
//   src/plugProjectNishimuraU/FireChappy.cpp    startBodyEffect / updateFireState
//
// Covers Red (2), Fiery (33) and Hairy (43) Bulborb, which all run the ChappyBase
// adult FSM in pc_p2_chappy.cpp.
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <string>
#include <utility>
#include <vector>

namespace p2chappyadult {

constexpr float PI_F = 3.14159265f;

// ---- clip loops ------------------------------------------------------------
// Bank key events (enemyanimmgr.txt): 0 = LOOP_START, 1 = LOOP_END, 3 = the key
// the sleep state uses for finishSleepEffect. Before this, every non-Emperor
// clip clamped at its last pose: move1 (50 frames) froze after ~1.3 s while the
// body kept translating, which is the "glides instead of walking" report.
struct Loop {
    int start = 0;
    int end = 0; // 0/0 = no loop keys
    bool valid() const { return end > start; }
};

// Parses a bank row events token such as "5:0,33:1" or "-" into (frame,type) pairs.
inline std::vector<std::pair<int, int>> parseEvents(const std::string& token)
{
    std::vector<std::pair<int, int>> out;
    if (token.empty() || token == "-") return out;
    size_t pos = 0;
    while (pos < token.size()) {
        size_t comma = token.find(',', pos);
        if (comma == std::string::npos) comma = token.size();
        const std::string item = token.substr(pos, comma - pos);
        const size_t colon = item.find(':');
        if (colon != std::string::npos) {
            out.emplace_back(std::atoi(item.substr(0, colon).c_str()), std::atoi(item.substr(colon + 1).c_str()));
        }
        pos = comma + 1;
    }
    return out;
}

inline Loop loopFromEvents(const std::vector<std::pair<int, int>>& events)
{
    Loop l;
    int start = -1, end = -1;
    for (const auto& e : events) {
        if (e.second == 0 && start < 0) start = e.first;
        if (e.second == 1 && end < 0) end = e.first;
    }
    if (start >= 0 && end > start) { l.start = start; l.end = end; }
    return l;
}

// Frame on display after `elapsed` source frames. Without a finish request the
// clip plays 0..end and then wraps inside [start,end); a finish request (source
// finishMotion) plays through to the last frame instead.
inline float clipFrame(const Loop& loop, float elapsed, int frames, bool finishing)
{
    const float last = float(frames > 1 ? frames - 1 : 1);
    if (loop.valid() && !finishing && elapsed >= float(loop.end)) {
        const float span = float(loop.end - loop.start);
        return float(loop.start) + std::fmod(elapsed - float(loop.start), span);
    }
    return elapsed < last ? elapsed : last;
}

// Continuing a looped clip after a finish request: the loop position at the
// moment of the request becomes the new elapsed time, so the clip continues from
// where the viewer saw it instead of jumping to frame `end`.
inline float elapsedAtFinish(const Loop& loop, float elapsed, int frames)
{
    return clipFrame(loop, elapsed, frames, false);
}

// ---- animation speed -------------------------------------------------------
// setAnimationSpeed: Turn/Walk/Flick 40, finishing an exit 60, default 30
// (chappyState.cpp:280,929,2188,303,187). GoHome never sets it in the source;
// the port plays it at 40 because the body moves at the walk speed and a 30 fps
// stride visibly slides.
constexpr float SpeedDefault = 30.0f;
constexpr float SpeedMove = 40.0f;
constexpr float SpeedFinish = 60.0f;

// ---- wake ------------------------------------------------------------------
// ChappyBase::isWakeup: every adult except the Orange (BlueChappy) wakes only
// when it is taking damage or colliding (EB_TakingDamage / EB_Colliding). Sight
// does NOT wake it; the port used to wake on `sees || health < max`, i.e. any
// captain or Pikmin within 500 units.
inline bool sleepWakes(bool takingDamage, bool colliding) { return takingDamage || colliding; }

// EB_Colliding analogue: a captain or Pikmin touching the body. The bank body is
// about +-37 x / 50 z around the actor origin; creatures are ~10 wide.
constexpr float BodyTouchRadius = 50.0f;
inline bool touching(float distXZ) { return distXZ < BodyTouchRadius; }

// ---- snore bubble ----------------------------------------------------------
// StateSleep::exec: KEYEVENT_LOOP_START of the sleep clip (type1) starts the
// bubble, KEYEVENT_3 finishes it; cleanup also finishes it. Bubble shows only in
// [loopStart, key3) of the sleep clip while the state is Sleep.
inline bool snoreActive(bool inSleepState, bool sleepClip, float frame, int loopStart, int finishKey)
{
    if (!inSleepState || !sleepClip) return false;
    return frame >= float(loopStart) && frame < float(finishKey);
}

// ---- alert / search --------------------------------------------------------
// StateCautionBase::cautionProc: a captain or Pikmin inside the private radius
// (or life below fp30) re-arms a timer; while it runs the view and search angles
// widen to 180.
struct Alert {
    float timer = 1.0e9f; // start "not alerted"
};

inline void alertTick(Alert& a, bool doAlert, float alertTime, float dt)
{
    if (doAlert) a.timer = 0.0f;
    if (a.timer < alertTime) a.timer += dt;
}

inline bool alerted(const Alert& a, float alertTime) { return a.timer < alertTime; }

inline float searchAngle(const Alert& a, float alertTime, float parmAngle) { return alerted(a, alertTime) ? 180.0f : parmAngle; }

// |angle| <= half-angle (degrees); 180 accepts everything.
inline bool withinAngle(float angleRad, float halfAngleDeg)
{
    return std::fabs(angleRad) <= halfAngleDeg * PI_F / 180.0f + 1.0e-6f;
}

inline float wrapPi(float a)
{
    while (a > PI_F) a -= 2.0f * PI_F;
    while (a < -PI_F) a += 2.0f * PI_F;
    return a;
}

// ---- walk facing gate --------------------------------------------------------
// StateWalk: walk toward the target while |angle| <= fp13 view angle (90, 180
// alerted), turning at turnSpeed while moving. The port used the 25 degree
// attack angle, which bounced Walk <-> Turn every time the captain circled.
inline bool walkFacing(float angleRad, float viewAngleDeg) { return withinAngle(angleRad, viewAngleDeg); }

// ---- fire body effect --------------------------------------------------------
// FireChappy::startBodyEffect (efx::TYakiBody on the body joint matrix) runs from
// onInit while alive and dry (updateFireState); finishFireState fades it on death
// or entering water. Emitter offsets, in the actor's local frame (x right, y up,
// z forward) standing in for the body / head / rear joints of the baked pose.
struct Offset { float x, y, z; };
constexpr int FireEmitters = 3;
inline Offset fireOffset(int i)
{
    static const Offset table[FireEmitters] = {{0.0f, 40.0f, 0.0f}, {0.0f, 42.0f, 34.0f}, {0.0f, 34.0f, -30.0f}};
    return table[i < 0 ? 0 : (i >= FireEmitters ? FireEmitters - 1 : i)];
}

inline bool fireWanted(bool alive, bool inWater) { return alive && !inWater; }

// ---- finishMotion / KEYEVENT_END deferral (#994 leash) -------------------------
// chappyState.cpp StateWalk/StateGoHome/StateTurnToHome set mNextState and call
// finishMotion(); the state only changes when the current clip reaches its END
// event (transit at KEYEVENT_END). StateGoHome keeps calling walkToTarget every
// frame meanwhile (chappyState.cpp:2842-2845), so a leashed Bulborb that sights a
// target still walks home for the rest of the move1 cycle, while StateWalk stands
// still for the rest of its cycle after the territory check (chappyState.cpp:981-990).
// Changing state on the very frame the condition appears gave the Walk <-> TurnToHome
// <-> GoHome loop with zero travel that froze a leashed Fiery at the territory edge.
inline float cycleEndFrame(float elapsedFrames, int clipFrames)
{
    const float len = clipFrames > 2 ? float(clipFrames - 1) : 1.0f;
    return (std::floor(elapsedFrames / len) + 1.0f) * len;
}
inline bool cycleEnded(float elapsedFrames, float endFrame) { return elapsedFrames >= endFrame; }

} // namespace p2chappyadult
