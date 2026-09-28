#pragma once
#include "pc_p2_groink_attack.h"

// Restricted non-looping attack cursor. This is event timing, not skinning.
// Actual GPVE01 attack1.bca is 44 frames, with events2/3/4/5 at11/22/25/32.
class P2GroinkAttackCursor {
public:
    struct Clip { int frames; std::array<int,4> keys; };
    struct Step { bool valid = false; P2GroinkAttackEvent event = P2GroinkAttackEvent::None; };
    bool start(const Clip& clip) {
        if (clip.frames<2 || clip.frames>10000) return false;
        int previous=-1;
        for (int key:clip.keys) { if (key<=previous || key>=clip.frames-1) return false; previous=key; }
        mClip=clip; mFrame=0; mNext=0; mCompleted=false; mReady=true; return true;
    }
    void reset() { *this={}; }
    // Caller uses source animation speed * source delta; zero means stopped.
    // A bounded increment prevents unbounded catch-up. For several crossed
    // keys, retain the last event just like EnemyBase::onKeyEvent's single slot.
    Step animate(float increment) {
        if (!mReady || !std::isfinite(increment) || increment<0 || increment>4) return {};
        Step out; out.valid=true;
        mFrame+=increment;
        constexpr P2GroinkAttackEvent types[]{P2GroinkAttackEvent::Charge,P2GroinkAttackEvent::Smoke,
            P2GroinkAttackEvent::Fire,P2GroinkAttackEvent::Return};
        while(mNext<4 && mClip.keys[mNext]<int(mFrame)) out.event=types[mNext++];
        if (mFrame>=mClip.frames) {
            mFrame=float(mClip.frames-1);
            if (!mCompleted) { mCompleted=true; out.event=P2GroinkAttackEvent::End; }
        }
        return out;
    }
    float frame() const { return mFrame; }
    bool completed() const { return mCompleted; }
private:
    Clip mClip{};
    float mFrame=0;
    std::size_t mNext=0;
    bool mCompleted=false, mReady=false;
};
