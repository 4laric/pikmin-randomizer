#pragma once

// Engine-free Man-at-Legs (Houdai, P2 source id 66) brain (#173).
//
// Source: native/pikmin2-research src/plugProjectNishimuraU/{Houdai,HoudaiState,
// HoudaiShotGun,IKSystemMgr}.cpp and src/plugProjectYamashitaU/enemyAction.cpp
// (EnemyFunc::isStartFlick / flickStickPikmin). One call is one 30 Hz source
// tick (sys->mDeltaTime = 1/30). The brain owns the state machine, the
// animation clock of every clip (clip lengths and key frames read from the US
// GPVE01 rev 0 disc: enemy/data/Houdai/anim.szs + houdai/enemyanimmgr.txt), the
// flick counter, the shot-gun burst/aim timers and gun rotation, the IK stride
// cycle and the Walk target rule. The host (pc_p2_long_legs.cpp) senses the
// world (nearest Pikmin/captain, stuck count, accepted hits), applies the
// requested effects (flick stuck Pikmin, spawn shells, move the body, kill) and
// never decides a transition itself.
//
// Documented port approximations (no IKSystemMgr / J3D joints in the P1 port):
//  * The IK walk is a stride cycle of fixed duration `strideSeconds`: at each
//    cycle start the source setNextCentrePosition rule picks the next centre
//    (move up to mMoveSpeed=250 toward the target when it lies inside the IK
//    view angle 30 deg, otherwise turn in place by at most mMaxTurnAngle=60
//    deg); the body interpolates to it over the cycle. finishIKMotion lets the
//    running cycle complete (isFinishIKMotion waits for all four legs).
//  * The gun is a downward turret at the bind-pose `gun` joint (y=112 above the
//    body origin, x axis pointing down). Yaw/tilt turn at the source 0.05
//    rad/tick while aiming and return at 0.025 rad/tick.

#include "pc_p2_long_legs_fsm.h"

struct P2HoudaiVec {
    float x = 0.0f, y = 0.0f, z = 0.0f;
};

// Retail disc values (houdai/enemyparm.txt in enemy/parm/enemyParms.szs). The
// header defaults differ; see docs/PIKMIN2_LONG_LEGS_AUDIT.md for the header.
struct P2HoudaiParms {
    float maxHealth = 2800.0f;       // fp00
    float privateRadius = 70.0f;     // fp11 mPrivateRadius
    float territoryRadius = 800.0f;  // fp09
    float homeRadius = 75.0f;        // fp10
    float sightRadius = 600.0f;      // fp12
    float viewAngleDeg = 180.0f;     // fp13 (Walk nearest-Pikmin cone)
    float searchDistance = 800.0f;   // fp14 (gun target range)
    float burstCooldown = 40.0f;     // fp26 mSearchHeight, reused as seconds
    float maxAimSeconds = 7.0f;      // fp15 mSearchAngle, reused as seconds
    float shakeChance = 1.0f;        // fp16
    float shakeKnockback = 500.0f;   // fp17
    float shakeDamage = 0.0f;        // fp18
    float attackRadius = 10.0f;      // fp22 shell capsule radius
    float attackHitAngle = 0.004f;   // fp23 shell direction jitter
    float attackDamage = 10.0f;      // fp24 shell InteractBomb damage
    int shakeOffBlowA = 10, shakeOffSticking1 = 30;  // ip01, ip02
    int shakeOffBlowB = 15, shakeOffSticking2 = 37;  // ip03, ip04
    int shakeOffBlowC = 25, shakeOffSticking3 = 50;  // ip05, ip06
    int shakeOffBlowD = 30;                          // ip07
    float maxShootingOn = 2.5f;      // proper fp10
    float minShootingOn = 0.5f;      // proper fp11
    float maxShootingOff = 1.0f;     // proper fp12
    float minShootingOff = 0.06f;    // proper fp13
    float strideLength = 250.0f;     // fp06 mMoveSpeed -> IKSystemParms::mMoveSpeed
    float ikViewAngleDeg = 30.0f;    // IKSystemParms default mEnragedAngle (getViewAngle)
    float maxTurnDeg = 60.0f;        // fp28 mMaxTurnAngle
    float strideSeconds = 2.0f;      // port approximation of one four-leg IK cycle
    float gunHeight = 112.0f;        // bind-pose `gun` joint height (enemy.bmd JNT1)
    float gunMuzzle = 45.0f;         // emitShotGun: 45 units along the gun x axis
    float shellSpeed = 600.0f;       // emitShotGun
};

struct P2HoudaiInput {
    float health = 0.0f;
    bool wake = false;          // captain or Pikmin inside mPrivateRadius
    bool damageAttempt = false; // stuck-Pikmin hit arrived while dormant (Stay wakes)
    bool tookDamage = false;    // EB_TakingDamage this tick (accepted damage)
    int hits = 0;               // accepted hits this tick (addDamage flickSpeed 1.0 each)
    int stuck = 0;              // mStuckPikminCount
    P2HoudaiVec pos;            // body position
    float faceDir = 0.0f;
    bool walkPikiFound = false; // nearest non-stuck Pikmin in view cone / sight radius
    P2HoudaiVec walkPiki;
    bool gunTargetFound = false; // nearest non-stuck Pikmin or captain, 180 deg / search distance
    P2HoudaiVec gunTarget;
    float roll[4] = {0.0f, 0.0f, 0.0f, 0.0f}; // host uniform [0,1)
    float modelScale = 1.0f;    // host draw scale of the bind mesh (gun joint height follows it)
    // World position of the posed gun joint (#1012): the pivot does not move when the head turns
    // or the gun pitches, so the host reads it from the clip pose (rig draw). Without a rig
    // (gunPosValid false) the brain falls back to the bind-pose joint height above the body.
    bool gunPosValid = false;
    P2HoudaiVec gunPos;
};

struct P2HoudaiOutput {
    P2LongLegsState state = P2LongLegsState::Stay;
    P2LongLegsState from = P2LongLegsState::Stay;
    bool entered = false;
    float chosenSeconds = 0.0f;
    // flickStickPikmin request (chance, knockback, damage, FLICK_BACKWARD_ANGLE)
    bool flickStuck = false;
    float flickChance = 0.0f, flickKnockback = 0.0f, flickDamage = 0.0f;
    const char* flickCause = "";
    // emitShotGun request
    bool fireShell = false;
    P2HoudaiVec shellPos, shellVel;
    // Walk body motion (target position and facing this tick)
    bool moving = false;
    P2HoudaiVec bodyPos;
    float bodyFace = 0.0f;
    bool strideStart = false;
    P2HoudaiVec strideTo;       // stride end centre (setNextCentrePosition), valid on strideStart
    float strideFace = 0.0f;    // stride end facing, valid on strideStart
    P2HoudaiVec walkTarget;
    // Shot bookkeeping edges (diagnostics)
    bool aimStart = false, burstOn = false, burstOff = false, aimEnd = false;
    bool deadEnd = false;       // dead clip END: throwupItem + explode + kill
    bool drawHidden = false;    // Stay (bind-pose host only: the rig draw shows landing frame 0 instead)
    float landDrop = 0.0f;      // Land drop-in offset for the bind-pose host (the rig draw plays the landing clip)
    float damageRate = 0.0f;    // receiver multiplier this state (0 = reject)
};

class P2HoudaiFsm {
public:
    static constexpr float kDelta = 1.0f / 30.0f;
    // Disc clip lengths / keys (frames at 30 fps).
    static constexpr int kLandingFrames = 230; // keys 54:2 84:3 100:4 130:5 150:6
    static constexpr int kWaitFrames = 40;     // keys 0:0 39:1 (loop)
    static constexpr int kFlickFrames = 85;    // keys 40:2 45:3 68:4
    static constexpr int kAttackFrames = 70;   // keys 33:2 34:0 35:3 37:4 38:1 39:5
    static constexpr int kDeadFrames = 140;    // no keys

    void reset(const P2HoudaiParms& parms, const P2HoudaiVec& home, float faceDir);
    void update(const P2HoudaiInput& in, P2HoudaiOutput& out);

    P2LongLegsState state() const { return mState; }
    float flickTimer() const { return mFlickTimer; }
    float burstTimer() const { return mBurstTimer; }
    int frame() const { return mFrame; }
    bool gunRotating() const { return mRotation; }
    float gunYaw() const { return mYaw; }
    float gunTilt() const { return mTilt; }
    const P2HoudaiParms& parms() const { return mParms; }
    // Clip the body pose is showing (disc clip order, = p2houdairig::Rig::Clip): landing 0, wait 1,
    // flick 2, attack 3, dead 4. Walk has no clip in the source (IK only), so the pose holds the
    // last frame of the clip that was playing (Houdai::startIKMotion does not start an animation).
    static constexpr int kPoseLanding = 0, kPoseWait = 1, kPoseFlick = 2, kPoseAttack = 3, kPoseDead = 4;
    int poseClip() const { return mPoseClip; }
    int poseFrame() const { return mPoseFrame; }
    // True while the clip clock is running, so a draw frame between two source ticks may blend toward
    // the next frame (presentation only).
    bool poseAdvancing() const;
    // Sight effect runs while the source rotation is searching (doUpdate: not yet finished).
    bool gunAiming() const { return mRotation && !mGunFinished; }
    // Gun barrel (local X) direction in the world, from the brain's yaw and tilt-from-down.
    P2HoudaiVec gunDirection() const;
    bool isStartFlick(int stuck) const;
    static bool isStartFlickFor(const P2HoudaiParms& p, int stuck, float flickTimer);
    // Source Houdai::damageCallBack (Houdai.cpp:223-236, US build) multiplier
    // for a stuck-Pikmin hit in `state`: the US check is only isStickTo, and
    // only Land scales (0.25x). Stay therefore takes full damage (and the
    // EB_TakingDamage flag wakes it into Land). Dead takes nothing.
    static float damageRateFor(P2LongLegsState state);

private:
    void enter(P2LongLegsState next, const P2HoudaiInput& in, P2HoudaiOutput& out);
    void requestFlick(P2HoudaiOutput& out, float chance, float knock, float damage, const char* cause);
    void walkTargetRule(const P2HoudaiInput& in);
    void startStride(const P2HoudaiVec& pos, float face);
    void gunUpdate(const P2HoudaiInput& in);
    P2HoudaiVec gunOrigin(const P2HoudaiInput& in) const;
    void emit(const P2HoudaiInput& in, P2HoudaiOutput& out);

    P2HoudaiParms mParms;
    P2LongLegsState mState = P2LongLegsState::Stay;
    P2LongLegsState mNext = P2LongLegsState::Stay;
    bool mHasNext = false;
    P2HoudaiVec mHome;
    int mFrame = 0;          // animation frame of the current clip
    int mKey = -1;           // key event reached by the last animation advance
    bool mStopped = false;   // stopMotion
    bool mFinish = false;    // finishMotion requested
    float mStateTimer = 0.0f;
    float mStateDuration = 0.0f;
    float mFlickTimer = 0.0f;   // EnemyBase::mFlickTimer (hit counter)
    float mBurstTimer = 0.0f;   // mShotGunBurstTimer
    float mSearchTimer = 0.0f;  // mShotGunSearchTimer
    int mShotState = 0;         // mShotGunState
    bool mRotation = false, mLockOn = false, mGunFinished = false;
    float mYaw = 0.0f, mTilt = 0.0f; // world yaw and tilt-from-down of the gun
    P2HoudaiVec mGunAim;             // mShotGunTargetPosition
    // IK stride
    P2HoudaiVec mTarget;             // mTargetPosition
    bool mIkInMotion = false, mIkActive = false;
    float mStrideT = 0.0f;
    P2HoudaiVec mStrideFrom, mStrideTo;
    float mFaceFrom = 0.0f, mFaceTo = 0.0f;
    float mFace = 0.0f;
    int mPoseClip = 0;
    int mPoseFrame = 0;
};
