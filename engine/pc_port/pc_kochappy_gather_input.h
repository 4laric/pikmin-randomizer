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

enum class PcKochappyCatchupInput { Refuse, Hold, Continue };
// Fixture input pacing only; clocks, roster and positions remain native-owned.
struct PcKochappyRouteCatchup {
    bool active=false;
    int guide=-1, elapsed=0, stable=0, lastProgress=0;
    float best=-1;
    bool begin(int visitedGuide) {
        if(active || visitedGuide<0 || visitedGuide>=128)return false;
        active=true;guide=visitedGuide;elapsed=stable=lastProgress=0;best=-1;
        return true;
    }
    PcKochappyCatchupInput observe(bool originalRoster, float lag, float limit, float captainSpeed, bool settled=true) {
        using I=PcKochappyCatchupInput;
        if(!active || !originalRoster || !std::isfinite(lag) || lag<0
            || !std::isfinite(limit) || limit<=0 || limit>=512
            || !std::isfinite(captainSpeed) || captainSpeed<0)return I::Refuse;
        ++elapsed;
        if(best<0 || lag<best-1.f){best=lag;lastProgress=elapsed;}
        // Ordinary neutral input does not freeze native collision/slip motion.
        // Read the roster against the current pose on every observation.
        if(lag<=limit && settled)++stable;else stable=0;
        if(stable>=3){active=false;return I::Continue;}
        if(elapsed>=180 || elapsed-lastProgress>=90)return I::Refuse;
        return I::Hold;
    }
};

// Read-only observations of the actual modern ActCrowd/CPlate party action.
// Unk0, trips and native routes may settle; Sort and foreign slots refuse.
struct PcKochappyCrowdObservation {
    bool actionOwner=false,plateOwner=false,slotsAvailable=false;
    bool occupantOwner=false,listenerOwner=false,finiteGeometry=false;
    bool neutral=false,tripping=false,route=false;
    int state=-1,slot=-1,used=-1,capacity=-1;
    bool valid() const {
        return actionOwner && plateOwner && slotsAvailable && occupantOwner && listenerOwner
            && finiteGeometry && (state==0 || state==1)
            && capacity>0 && used>0 && used<=capacity && slot>=0 && slot<used;
    }
    bool settled() const { return valid() && state==1 && neutral && !tripping && !route; }
};
