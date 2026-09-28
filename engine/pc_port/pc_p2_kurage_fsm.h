// Isolated source FSM bridge for the Lesser Spotted Jellyfloat (Kurage, ID 57).
//
// Transcribed from US GPVE01 rev 0 native/pikmin2-research
// src/plugProjectNishimuraU/KurageState.cpp (all eleven states) and composes
// pc_p2_kurage_flight_policy.h for the numeric decisions. Fixed-step: the host
// supplies one Tick per simulated frame. The bridge owns mStateTimer,
// mMovePitchTimer, mFallTimer, current state/motion/flags and mIsSucking; it
// creates no engine objects and does no I/O.
//
// Shared base for the Greater Spotted Jellyfloat (OniKurage, ID 72). Passing
// `Variant::Greater` adds the OniKurage source's Drop state, captain-suck
// routing and Greater pitch offsets while leaving the default `Lesser` path
// byte-identical to the Kurage-only bridge.
//
// Host responsibilities: getSearchedTarget()/isSuck() geometry (supplied as
// targetFound/suckTarget/suckAny), actual walkToTarget movement, animation and
// KeyEvent production (#431 clock), the suck/flick receivers and rendering.
#ifndef PC_P2_KURAGE_FSM_H
#define PC_P2_KURAGE_FSM_H

#include <cstdint>
#include "pc_p2_kurage_flight_policy.h"

namespace p2kurage {

enum class State : std::uint8_t {
    Dead, Wait, Move, Chase, Attack, Fall, Land, Ground, TakeOff, FlyFlick, GroundFlick,
    Drop, // OniKurage only (OniKurageState.cpp:27); never entered by Variant::Lesser
};

enum class Motion : std::uint8_t {
    None, DeadFly, DeadGround, FlickFly, FlickGround, Wait, Move, Land, TakeOff, Fall, Attack,
};

enum class KeyEvent : std::uint8_t { None, Key1, Key2, Key3, End };

struct Flags {
    bool untargetable = false;
    bool cullable = true;
    bool damageAnimEnabled = true;
};

struct In {
    float deltaTime = 1.0f / 30.0f;
    float health = 100.0f;
    int stuckPikminCount = 0;
    bool purpleStuck = false;
    bool isFlying = true;
    bool targetFound = false;   // getSearchedTarget(altitude) != null
    bool suckTarget = false;    // isSuck(altitude, target)
    bool suckAny = false;       // isSuck(altitude, nullptr)
    float mapY = 0.0f;
    float positionY = 0.0f;
    float motionFrame = 0.0f;   // active motion frame (Attack/FlyFlick/TakeOff pitch)
    float distToTargetXZ = 1e9f; // vs 25 units for Move arrival
    KeyEvent keyEvent = KeyEvent::None;
    bool motionFinished = false;
    // OniKurage (Variant::Greater) captain-mouth facts. Defaults keep the
    // Lesser path unchanged: no Navi is ever attached and isFinishNaviSuck()
    // is vacuously true on an empty mouth-slot table.
    bool naviSucked = false;       // isNaviSucked(): >=1 captain held in a mouth slot
    bool naviSuckFinished = true;  // isFinishNaviSuck(): occupied slots at rest offsets
    float velocityY = 0.0f;        // getVelocity().y for the StateDrop ground test
};

struct Out {
    State state = State::Wait;
    Motion motion = Motion::Wait;
    bool motionChanged = false;
    bool finishing = false;
    float heightVelocity = 0.0f;
    float altitude = 0.0f;
    bool isSucking = false;
    Flags flags;
    bool kill = false;
    bool flickStick = false;      // flickStickPikmin (Dead/FlyFlick/GroundFlick)
    bool flickNearby = false;     // flickNearbyNavi + flickNearbyPikmin (GroundFlick)
    bool downEffect = false;      // Land entry
    bool deathProcedure = false;  // Dead Key3
    bool bodyBomb = false;        // Dead Key3
    bool suckStart = false;       // Attack Key2
    bool suckStop = false;        // Attack Key1 while finishing
    bool flickEffect = false;     // FlyFlick/GroundFlick entry effect
};

class Fsm {
public:
    explicit Fsm(Parms parms = Parms(), Variant variant = Variant::Lesser)
        : mParms(parms), mVariant(variant) {}

    State state() const { return mState; }
    Motion motion() const { return mMotion; }
    const Flags& flags() const { return mFlags; }
    float fallTimer() const { return mFallTimer; }
    Variant variant() const { return mVariant; }

    void spawn() { forceState(State::Wait); }

    void forceState(State state)
    {
        mState = state; mMotion = Motion::None; mStateTimer = 0.0f; mNextState = State::Wait;
        mHasNext = false; mFinishing = false; mIsSucking = false; mFlags = Flags{};
        mMovePitchTimer = 3.5f;
        enter(state);
        mPendingMotionChange = true;
    }

    Out tick(const In& in)
    {
        Out out;
        out.motionChanged = mPendingMotionChange;
        mPendingMotionChange = false;
        mLastFlying = in.isFlying;
        updateFallTimer(in.stuckPikminCount, mFallTimer, in.deltaTime);

        switch (mState) {
        case State::Dead:
            if (in.keyEvent == KeyEvent::Key2) out.flickStick = true;
            if (in.keyEvent == KeyEvent::Key3) { out.deathProcedure = true; out.bodyBomb = true; }
            if (in.motionFinished) out.kill = true;
            break;

        case State::Wait:
        case State::Move:
        case State::Chase: {
            const float pitch = onFlyingStatePitch(in);
            out.heightVelocity = heightVelocity(mParms, pitch, 0.0f, in.mapY, in.positionY);
            out.altitude = altitude(in.mapY, in.positionY);

            if (in.targetFound) {
                if (in.suckTarget) { setNext(State::Attack); mFinishing = true; }
                else if (mState == State::Wait) { setNext(State::Chase); mFinishing = true; }
                // Move/Chase with a non-suck target keeps walking (host).
            } else if (mState == State::Wait) {
                if (mStateTimer > 3.0f) { setNext(State::Move); mFinishing = true; }
            } else if (mState == State::Move) {
                if (mStateTimer > 10.0f || in.distToTargetXZ < 25.0f) { setNext(State::Wait); mFinishing = true; }
            } else { // Chase lost target
                setNext(State::Move); mFinishing = true;
            }

            const FlyingNext flying = flyingNextState(in);
            if (flying != FlyingNext::Null) { transition(out, toState(flying)); return out; }

            if (mState != State::Chase) mStateTimer += in.deltaTime;
            if (in.motionFinished && mHasNext) { transition(out, mNextState); return out; }
            break;
        }

        case State::Attack:
            if (mVariant == Variant::Greater) {
                // OniKurage StateAttack::exec (OniKurageState.cpp:330): the
                // Greater species also finishes once every occupied captain
                // mouth slot has settled while a captain is held.
                if ((in.health <= 0.0f || in.naviSuckFinished)
                    && (in.naviSucked || mStateTimer > mParms.suckTime || mFallTimer > mParms.shakeTime)) {
                    mFinishing = true;
                }
            } else if (in.health <= 0.0f || mStateTimer > mParms.suckTime || mFallTimer > mParms.shakeTime) {
                mFinishing = true;
            }
            out.heightVelocity = heightVelocity(mParms, attackPitchOffset(in.motionFrame, mVariant), 5.0f, in.mapY, in.positionY);
            out.altitude = altitude(in.mapY, in.positionY);
            if (in.keyEvent == KeyEvent::Key2) { out.suckStart = true; mIsSucking = true; }
            if (in.keyEvent == KeyEvent::Key1 && mFinishing) { out.suckStop = true; mIsSucking = false; }
            mStateTimer += in.deltaTime;
            if (in.motionFinished) {
                if (mVariant == Variant::Greater) {
                    // Source order: health death, then held-captain Drop, then
                    // the shared flying/suction routing.
                    if (in.health <= 0.0f) { transition(out, State::Dead); return out; }
                    if (in.naviSucked) { transition(out, State::Drop); return out; }
                }
                const FlyingNext flying = flyingNextState(in);
                if (flying != FlyingNext::Null) transition(out, toState(flying));
                else if (in.suckAny) transition(out, State::Attack);
                else transition(out, State::Wait);
                return out;
            }
            break;

        case State::Drop:
            if (mVariant != Variant::Greater) break; // unreachable on the shared base
            // StateDrop::exec: pure falling state, no setHeightVelocity call.
            out.altitude = altitude(in.mapY, in.positionY);
            if (dropShouldFinish(in.positionY, in.mapY, in.velocityY, mStateTimer)) mFinishing = true;
            mStateTimer += in.deltaTime;
            if (in.motionFinished) { transition(out, in.health <= 0.0f ? State::Dead : State::Land); return out; }
            break;

        case State::Fall:
            if (in.isFlying) {
                out.heightVelocity = heightVelocity(mParms, fallPitchOffset(mStateTimer, mVariant), 2.0f, in.mapY, in.positionY);
                if (mStateTimer * 30.0f > 65.0f) { mFlags.untargetable = false; mFinishing = true; }
            }
            out.altitude = altitude(in.mapY, in.positionY);
            mStateTimer += in.deltaTime;
            if (in.motionFinished) { transition(out, in.health <= 0.0f ? State::Dead : State::Land); return out; }
            break;

        case State::Land:
            if (in.motionFinished) { transition(out, in.health <= 0.0f ? State::Dead : State::Ground); return out; }
            break;

        case State::TakeOff:
            if (in.isFlying) out.heightVelocity = heightVelocity(mParms, takeOffPitchOffset(in.motionFrame, mVariant), 2.0f, in.mapY, in.positionY);
            out.altitude = altitude(in.mapY, in.positionY);
            if (in.keyEvent == KeyEvent::Key2) mFlags.untargetable = true;
            if (in.motionFinished) { transition(out, in.health <= 0.0f ? State::Dead : State::Wait); return out; }
            break;

        case State::Ground:
            if (in.stuckPikminCount == 0 || mStateTimer > mParms.groundTime) mFinishing = true;
            mStateTimer += in.deltaTime;
            if (in.motionFinished) {
                if (in.health <= 0.0f) transition(out, State::Dead);
                else if (in.stuckPikminCount != 0 || (mVariant == Variant::Greater && in.naviSucked)) transition(out, State::GroundFlick);
                else transition(out, State::TakeOff);
                return out;
            }
            break;

        case State::FlyFlick:
            out.heightVelocity = heightVelocity(mParms, flickPitchOffset(in.motionFrame, mVariant), 5.0f, in.mapY, in.positionY);
            out.altitude = altitude(in.mapY, in.positionY);
            if (in.keyEvent == KeyEvent::Key2) out.flickStick = true;
            if (in.motionFinished) {
                const FlyingNext flying = flyingNextState(in);
                if (flying != FlyingNext::Null) transition(out, toState(flying));
                else if (in.suckAny) transition(out, State::Attack);
                else transition(out, State::Wait);
                return out;
            }
            break;

        case State::GroundFlick:
            if (in.keyEvent == KeyEvent::Key3) out.flickNearby = true;
            if (in.motionFinished) { transition(out, in.health <= 0.0f ? State::Dead : State::TakeOff); return out; }
            break;
        }

        out.finishing = mFinishing;
        out.state = mState;
        out.motion = mMotion;
        out.isSucking = mIsSucking;
        out.flags = mFlags;
        return out;
    }

private:
    FlyingNext flyingNextState(const In& in) const
    {
        return p2kurage::flyingNextState(mParms, in.health, in.purpleStuck, mFallTimer, in.stuckPikminCount);
    }
    static State toState(FlyingNext next)
    {
        switch (next) {
        case FlyingNext::Dead: return State::Dead;
        case FlyingNext::Fall: return State::Fall;
        case FlyingNext::FlyFlick: return State::FlyFlick;
        default: return State::Wait;
        }
    }
    float onFlyingStatePitch(const In& in)
    {
        const float amplitude = mVariant == Variant::Greater
            ? greaterMovePitchAmplitude : lesserMovePitchAmplitude;
        return movePitchOffset(mMovePitchTimer, in.deltaTime, amplitude);
    }

    void setNext(State next) { mNextState = next; mHasNext = true; }

    void transition(Out& out, State next)
    {
        mState = next; mMotion = Motion::None; mStateTimer = 0.0f; mNextState = State::Wait;
        mHasNext = false; mFinishing = false; mIsSucking = false; mFlags = Flags{};
        mMovePitchTimer = 3.5f;
        enter(next);
        out.motionChanged = true;
        out.state = mState;
        out.motion = mMotion;
        out.flags = mFlags;
    }

    void enter(State state)
    {
        switch (state) {
        case State::Dead:
            mFlags.cullable = false; mFlags.damageAnimEnabled = false; mFlags.untargetable = true;
            mMotion = mLastFlying ? Motion::DeadFly : Motion::DeadGround;
            break;
        case State::Wait:   mFlags.untargetable = true; mMotion = Motion::Move; break;
        case State::Move:   mFlags.untargetable = true; mMotion = Motion::Move; break;
        case State::Chase:  mFlags.untargetable = true; mMotion = Motion::Move; break;
        case State::Attack: mFlags.untargetable = true; mFlags.cullable = false; mMotion = Motion::Attack; break;
        case State::Fall:   mFlags.untargetable = true; mMotion = Motion::Fall; break;
        case State::Land:   mFlags.untargetable = false; mMotion = Motion::Land; break;
        case State::Ground: mFlags.untargetable = false; mMotion = Motion::Wait; break;
        case State::TakeOff: mFlags.untargetable = false; mMotion = Motion::TakeOff; break;
        case State::FlyFlick: mFlags.untargetable = true; mMotion = Motion::FlickFly; break;
        case State::GroundFlick: mFlags.untargetable = false; mMotion = Motion::FlickGround; break;
        case State::Drop:
            // StateDrop::init disables Untargetable and reuses the Fall motion.
            mFlags.untargetable = false;
            mMotion = Motion::Fall;
            break;
        }
    }

    Parms mParms;
    Variant mVariant = Variant::Lesser;
    State mState = State::Wait;
    Motion mMotion = Motion::None;
    State mNextState = State::Wait;
    bool mHasNext = false;
    bool mFinishing = false;
    bool mIsSucking = false;
    bool mPendingMotionChange = false;
    bool mLastFlying = true;
    float mStateTimer = 0.0f;
    float mMovePitchTimer = 3.5f;
    float mFallTimer = 0.0f;
    Flags mFlags;
};

} // namespace p2kurage

#endif
