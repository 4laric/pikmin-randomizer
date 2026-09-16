#pragma once
#include <cmath>

// SaraiState.cpp StateAttack, inherited by Demon. This policy does not move actors.
enum class P2DemonAttackNext { None, Move, Fail, CatchFly, FallMeck };
enum class P2DemonHeightNext { None, Flick, Fall };
enum class P2DemonAttackEvent { None, Dash, Interruptible, CaptureCheck, End };
struct P2DemonAttackDecision {
    bool valid=false;
    bool attemptCapture=false;
    bool dash=false;
    bool clearNoInterrupt=false;
    P2DemonAttackNext next=P2DemonAttackNext::None;
    P2DemonHeightNext heightNext=P2DemonHeightNext::None;
};
class P2DemonAttackWindow {
    bool floorLatched=false;
public:
    void reset() { floorLatched=false; }
    P2DemonAttackDecision step(float frame, bool targetPresent, bool floorContact) {
        P2DemonAttackDecision out;
        if(!std::isfinite(frame)||frame<0) return out;
        out.valid=true;
        if(!targetPresent) out.next=P2DemonAttackNext::Move;
        else if(frame>10 && frame<=30) {
            if(floorContact) floorLatched=true;
            out.attemptCapture=!floorLatched && frame>16;
        }
        return out;
    }
    static P2DemonAttackDecision eventDecision(bool targetPresent, bool eventPlaying,
            P2DemonAttackEvent event, unsigned occupiedSlots) {
        P2DemonAttackDecision out;
        if(occupiedSlots>2) return out;
        out.valid=true;
        // Source continues processing animation events after a missing-target transit.
        // Caller supplies actual occupancy AFTER applying any capture attempt.
        if(eventPlaying) {
            if(event==P2DemonAttackEvent::Dash) out.dash=targetPresent;
            else if(event==P2DemonAttackEvent::Interruptible) out.clearNoInterrupt=true;
            else if(event==P2DemonAttackEvent::CaptureCheck && !occupiedSlots) out.next=P2DemonAttackNext::Fail;
            else if(event==P2DemonAttackEvent::End)
                out.next=occupiedSlots?P2DemonAttackNext::CatchFly:P2DemonAttackNext::Move;
        }
        return out;
    }
};
