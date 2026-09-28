// Isolated source FSM bridge for the Swooping Snitchbug (Sarai, ID 23).
//
// Transcribed from US GPVE01 rev 0 native/pikmin2-research
// src/plugProjectNishimuraU/SaraiState.cpp (all eleven states) and composes
// pc_p2_sarai_policy.h for the numeric decisions. Fixed-step: the host supplies
// one Tick per simulated frame and consumes the returned events. The bridge
// owns only mGeneralTimer/finishing and the current state/motion/flags; it
// creates no engine objects, does no I/O and performs no rendering.
//
// Host responsibilities (not modeled here): animation/event playback (#431
// clock) that produces KeyEvent/motionFinished, target acquisition
// (getAttackableTarget), the actual catch/flick/drop receivers, movement and
// the Attack hunt-descent velocity / post-hunt mTargetVelocity decay.
#ifndef PC_P2_SARAI_FSM_H
#define PC_P2_SARAI_FSM_H

#include <cstdint>
#include "pc_p2_sarai_policy.h"

namespace p2sarai {

enum class State : std::uint8_t {
    Dead, Fall, Damage, TakeOff, Flick, Wait, Move, Attack, Fail, CatchFly, FallMeck,
};

enum class Motion : std::uint8_t {
    None, Wait, Move, Attack, CatchFly, FallMeck, Flick, Fall, Damage, TakeOff, Fail, Dead,
};

enum class KeyEvent : std::uint8_t { None, Key2, Key3, Key4, End };

struct Flags {
    bool untargetable = false;
    bool noInterrupt = false;
    bool cullable = true;
};

struct In {
    float deltaTime = 1.0f / 30.0f;
    float health = 100.0f;
    int bodyStuckCount = 0;   // mStuckPikminCount
    int mouthCarried = 0;     // getCatchTargetNum()
    bool purpleLatched = false;
    float mapY = 0.0f;
    float positionY = 0.0f;
    bool targetPresent = false;      // getAttackableTarget() this frame
    bool hasTargetCreature = false;  // Attack: mTargetCreature still valid
    float targetFrame = 0.0f;        // Attack motion frame (getMotionFrame)
    float distToPatrolTargetXZ = 1e9f; // vs 25 units (625 squared)
    KeyEvent keyEvent = KeyEvent::None;
    bool motionFinished = false;     // KEYEVENT_END reached
    float randomUnit = 0.5f;         // [0,1)
};

struct Out {
    State state = State::Wait;
    Motion motion = Motion::Wait;
    bool motionChanged = false;   // host should start Out.motion this tick
    bool finishing = false;       // source finishMotion(): cut the current motion short
    Flags flags;
    bool attemptCatch = false;    // Attack, 16 < frame <= 30 and keepMouth window active
    bool flickAttackers = false;  // flickStickTarget() on entry to Dead/Fall/Damage, Key2 in Flick
    bool drop = false;            // FallMeck KEY3: fallMeckGround()
    bool downEffect = false;      // Fall KEY2
    bool kill = false;            // Dead KEYEVENT_END
};

class Fsm {
public:
    explicit Fsm(Parms parms = Parms()) : mParms(parms) {}

    State state() const { return mState; }
    Motion motion() const { return mMotion; }
    float generalTimer() const { return mTimer; }
    const Flags& flags() const { return mFlags; }

    // Equivalent to entering Wait from EnemyBase setup with an idle choice.
    void spawn(float randomUnit)
    {
        mState = State::Wait; mMotion = Motion::None; mTimer = 0.0f;
        mFlags = Flags{}; mFlags.untargetable = true;
        mMotion = randomUnit < 0.5f ? Motion::Wait : Motion::Move;
        mPendingMotionChange = true;
    }

    void forceState(State state, float randomUnit)
    {
        mState = state; mMotion = Motion::None; mTimer = 0.0f; mFlags = Flags{};
        enter(state, randomUnit);
        mPendingMotionChange = true;
    }

    Out tick(const In& in)
    {
        Out out;
        out.motionChanged = mPendingMotionChange;
        mPendingMotionChange = false;

        switch (mState) {
        case State::Dead:
            if (in.motionFinished) out.kill = true;
            break;

        case State::Fall:
            if (altitude(in.mapY, in.positionY) < 10.0f || mTimer > 1.0f) mFinishing = true;
            mTimer += in.deltaTime;
            if (in.keyEvent == KeyEvent::Key2) out.downEffect = true;
            if (in.motionFinished) { transition(out, in.health <= 0.0f ? State::Dead : State::Damage, in.randomUnit); return out; }
            break;

        case State::Damage:
            if (in.health <= 0.0f || mTimer > mParms.strugglingTime
                || stickPikminNum(in.bodyStuckCount, in.mouthCarried) == 0) {
                mFinishing = true;
            }
            mTimer += in.deltaTime;
            if (in.motionFinished) { transition(out, in.health <= 0.0f ? State::Dead : State::TakeOff, in.randomUnit); return out; }
            break;

        case State::TakeOff:
            if (in.health <= 0.0f || altitude(in.mapY, in.positionY) > mParms.stateTransitionHeight) mFinishing = true;
            if (in.motionFinished) {
                const HeightDecision d = heightDecision(in);
                if (d != HeightDecision::None) transition(out, toState(d), in.randomUnit);
                else transition(out, in.mouthCarried ? State::CatchFly : State::Move, in.randomUnit);
                return out;
            }
            break;

        case State::Flick:
            if (in.keyEvent == KeyEvent::Key2) out.flickAttackers = true;
            if (in.motionFinished) {
                if (in.health <= 0.0f) transition(out, State::Fall, in.randomUnit);
                else if (in.mouthCarried) transition(out, State::CatchFly, in.randomUnit);
                else transition(out, State::Move, in.randomUnit);
                return out;
            }
            break;

        case State::Wait:
            if (in.targetPresent || mTimer > mParms.waitTime) mFinishing = true;
            if (altitude(in.mapY, in.positionY) > mParms.stateTransitionHeight || mTimer > 3.0f) {
                const HeightDecision d = heightDecision(in);
                if (d != HeightDecision::None) { transition(out, toState(d), in.randomUnit); return out; }
            }
            mTimer += in.deltaTime;
            if (in.motionFinished) { transition(out, in.targetPresent ? State::Attack : State::Move, in.randomUnit); return out; }
            break;

        case State::Move:
            if (in.targetPresent || mTimer > 10.0f || in.distToPatrolTargetXZ < 25.0f) mFinishing = true;
            if (altitude(in.mapY, in.positionY) > mParms.stateTransitionHeight || mTimer > 3.0f) {
                const HeightDecision d = heightDecision(in);
                if (d != HeightDecision::None) { transition(out, toState(d), in.randomUnit); return out; }
            }
            mTimer += in.deltaTime;
            if (in.motionFinished) { transition(out, in.targetPresent ? State::Attack : State::Wait, in.randomUnit); return out; }
            break;

        case State::Attack:
            if (!in.hasTargetCreature) { transition(out, State::Move, in.randomUnit); return out; }
            if (attackMayCatch(in.targetFrame) && in.targetFrame <= 30.0f) out.attemptCatch = true;
            if (in.keyEvent == KeyEvent::Key3) mFlags.noInterrupt = false;
            if (in.keyEvent == KeyEvent::Key4 && in.mouthCarried == 0) { transition(out, State::Fail, in.randomUnit); return out; }
            if (in.motionFinished) { transition(out, in.mouthCarried ? State::CatchFly : State::Move, in.randomUnit); return out; }
            break;

        case State::Fail:
            if (in.motionFinished) { transition(out, in.mouthCarried ? State::CatchFly : State::Move, in.randomUnit); return out; }
            break;

        case State::CatchFly:
            if (mTimer > 10.0f || in.distToPatrolTargetXZ < 25.0f) mFinishing = true;
            if (in.mouthCarried == 0) { transition(out, State::Move, in.randomUnit); return out; }
            if (altitude(in.mapY, in.positionY) > mParms.stateTransitionHeight || mTimer > 3.0f) {
                const HeightDecision d = heightDecision(in);
                if (d != HeightDecision::None) { transition(out, toState(d), in.randomUnit); return out; }
            }
            mTimer += in.deltaTime;
            if (in.motionFinished) { transition(out, State::FallMeck, in.randomUnit); return out; }
            break;

        case State::FallMeck:
            if (in.keyEvent == KeyEvent::Key2) mFlags.noInterrupt = true;
            if (in.keyEvent == KeyEvent::Key3) out.drop = true;
            if (in.keyEvent == KeyEvent::Key4) mFlags.noInterrupt = false;
            if (in.motionFinished) { transition(out, State::Move, in.randomUnit); return out; }
            break;
        }

        out.finishing = mFinishing;
        out.state = mState;
        out.motion = mMotion;
        out.flags = mFlags;
        return out;
    }

private:
    HeightDecision heightDecision(const In& in) const
    {
        return nextStateOnHeight(mParms, in.health, in.mouthCarried, in.bodyStuckCount,
                                 in.purpleLatched, in.randomUnit);
    }

    static State toState(HeightDecision d)
    {
        return d == HeightDecision::Flick ? State::Flick : State::Fall;
    }

    void transition(Out& out, State next, float randomUnit)
    {
        mState = next; mMotion = Motion::None; mTimer = 0.0f; mFinishing = false; mFlags = Flags{};
        enter(next, randomUnit);
        out.motionChanged = true;
        out.state = mState;
        out.motion = mMotion;
        out.flags = mFlags;
        // Dead/Fall/Damage init calls flickStickTarget().
        if (next == State::Dead || next == State::Fall || next == State::Damage) out.flickAttackers = true;
    }

    void enter(State state, float randomUnit)
    {
        switch (state) {
        case State::Dead:     mFlags.cullable = false; mMotion = Motion::Dead; break;
        case State::Fall:     mMotion = Motion::Fall; break;
        case State::Damage:   mMotion = Motion::Damage; break;
        case State::TakeOff:  mFlags.untargetable = true; mMotion = Motion::TakeOff; break;
        case State::Flick:    mFlags.untargetable = true; mFlags.noInterrupt = true; mMotion = Motion::Flick; break;
        case State::Wait:     mFlags.untargetable = true; mMotion = randomUnit < 0.5f ? Motion::Wait : Motion::Move; break;
        case State::Move:     mFlags.untargetable = true; mMotion = Motion::Move; break;
        case State::Attack:   mFlags.cullable = false; mFlags.untargetable = true; mFlags.noInterrupt = true; mMotion = Motion::Attack; break;
        case State::Fail:     mFlags.cullable = false; mFlags.untargetable = true; mMotion = Motion::Fail; break;
        case State::CatchFly: mFlags.untargetable = true; mMotion = Motion::CatchFly; break;
        case State::FallMeck: mFlags.untargetable = true; mMotion = Motion::FallMeck; break;
        }
    }

    Parms mParms;
    State mState = State::Wait;
    Motion mMotion = Motion::None;
    float mTimer = 0.0f;
    bool mFinishing = false;
    bool mPendingMotionChange = false;
    Flags mFlags;
};

} // namespace p2sarai

#endif
