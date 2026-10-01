#pragma once

// Engine-free Raging Long Legs (BigFoot, P2 source id 69) brain (#1018).
//
// Source: native/pikmin2-research src/plugProjectNishimuraU/BigFoot.cpp and
// BigFootState.cpp, IKSystemMgr.cpp (legs, via pc_p2_long_legs_ik) and
// src/plugProjectYamashitaU/enemyAction.cpp (EnemyFunc::isStartFlick). One
// update() is one 30 Hz source tick (sys->mDeltaTime = 1/30), in the order of
// Obj::doUpdate (BigFoot.cpp:108-113): state exec, then updateIKSystem (the
// body position IS the IK centre), then the animation advance that produces
// the key event the next exec reads.
//
// The brain owns the state machine, every clip clock (disc lengths and key
// frames from bigfoot/enemyanimmgr.txt), the flick hit counter, the walk timer
// and target rule, the source IK legs and the posed skeleton (clip body from
// pc_p2_bigfoot_tables.h, legs from the IK) that the host uses for the retail
// collision tree, the foot press and the draw. The host (pc_p2_long_legs.cpp)
// senses the world, applies requested effects and never decides a transition.
//
// Retail disc parameters: bigfoot/enemyparm.txt in enemy/parm/enemyParms.szs
// (US GPVE01 rev 0).

#include "pc_p2_long_legs_fsm.h"
#include "pc_p2_long_legs_ik.h"

struct P2BigFootParms {
    // EnemyParmsBase (general)
    float maxHealth = 10000.0f;      // fp00
    float moveSpeed = 70.0f;         // fp06 -> IKSystemParms::mMoveSpeed
    float maxTurnDeg = 42.0f;        // fp28 -> IKSystemParms::mMaxTurnAngle
    float territoryRadius = 310.0f;  // fp09
    float homeRadius = 75.0f;        // fp10
    float privateRadius = 70.0f;     // fp11 (StateStay wake)
    float sightRadius = 400.0f;      // fp12
    float viewAngleDeg = 180.0f;     // fp13
    float shakeKnockback = 400.0f;   // fp17
    float shakeDamage = 0.0f;        // fp18
    float shakeChance = 1.0f;        // fp16
    float attackDamage = 10.0f;      // fp24 (InteractPress of a descending foot)
    int shakeOffBlowA = 70, shakeOffSticking1 = 50; // ip01, ip02
    int shakeOffBlowB = 80, shakeOffSticking2 = 60; // ip03, ip04
    int shakeOffBlowC = 90, shakeOffSticking3 = 70; // ip05, ip06
    int shakeOffBlowD = 100;                        // ip07
    // ProperParms (BigFoot.h:185-205, disc values)
    float baseCoefficient = 1.4f, raiseSlowdown = -0.1f, downwardAccel = 2.0f;           // fp01..fp03
    float minDecel = -0.7f, maxDecel = 10.0f, legSwing = 80.0f;                          // fp04..fp06
    float eBaseCoefficient = 4.0f, eRaiseSlowdown = -0.3f, eDownwardAccel = 2.0f;        // fp11..fp13
    float eMinDecel = -1.7f, eMaxDecel = 10.0f, eLegSwing = 110.0f;                      // fp14..fp16
    float movementOffset = 50.0f;    // fp17 enraged stomp step
    float normalTravelTime = 10.0f;  // fp20
    float postShakeTravelTime = 5.0f; // fp21
    // Model scale (P2 enemy scale 1: the collision tree radii are in these units).
    float scale = 1.0f;
};

struct P2BigFootInput {
    float health = 0.0f;
    bool wake = false;           // captain or Pikmin inside mPrivateRadius (StateStay::exec)
    int hits = 0;                // accepted damage events this tick (addDamage flickSpeed 1.0 each)
    int stuck = 0;               // mStuckPikminCount
    bool walkPikiFound = false;  // nearest non-stuck Pikmin in the view cone and sight radius
    p2ik::V3 walkPiki;
    float roll[4] = {0.0f, 0.0f, 0.0f, 0.0f}; // host uniform [0,1)
    p2ik::GroundFn ground = nullptr;          // mapMgr->getMinY
    void* groundCtx = nullptr;
};

struct P2BigFootOutput {
    P2LongLegsState state = P2LongLegsState::Stay;
    P2LongLegsState from = P2LongLegsState::Stay;
    bool entered = false;
    float chosenSeconds = 0.0f;   // mFlickWalkTimeMax on Walk entry
    bool flickStuck = false;      // StateFlick key 2: EnemyFunc::flickStickPikmin
    float flickChance = 0.0f, flickKnockback = 0.0f, flickDamage = 0.0f;
    bool landKey2 = false;        // StateLand key 2: immunity off, ground effects on all feet
    bool deadKey2 = false;        // StateDead key 2: throwupItem + createItemAndEnemy
    bool deadEnd = false;         // StateDead END: kill
    bool hidden = false;          // Stay: EB_ModelHidden
    bool bitterImmune = true;     // Stay, Land before key 2
    bool enraged = false;
    int lifted = 0, planted = 0;  // IK leg edges this tick (JointGroundCallBack)
};

class P2BigFootFsm {
public:
    static constexpr float kDelta = 1.0f / 30.0f;
    static constexpr int kKeyEnd = 100;
    enum Clip { ClipDead = 0, ClipLanding = 1, ClipWait = 2, ClipFlick = 3 };
    static constexpr int kJoints = 15;
    // Source leg order (BigFoot::setupIKSystem, BigFoot.cpp:393-399):
    // rhand, lhand, rfoot, lfoot; three joints each.
    static const int kLegJoint[p2ik::kLegCount][3];
    // IKSystemMgr::isCollisionCheck (IKSystemMgr.cpp:263-281): the foot sphere of each leg.
    static const char* const kFootNode[p2ik::kLegCount];

    void reset(const P2BigFootParms& parms, const p2ik::V3& home, float faceDir);
    void update(const P2BigFootInput& in, P2BigFootOutput& out);

    P2LongLegsState state() const { return mState; }
    const P2BigFootParms& parms() const { return mParms; }
    float flickTimer() const { return mFlickTimer; }
    float walkTimeMax() const { return mFlickWalkTimeMax; }
    float stateTimer() const { return mStateTimer; }
    bool enraged() const { return mEnraged; }
    int clip() const { return mClip; }
    int frame() const { return mFrame; }
    p2ik::V3 position() const { return mPos; }   // mPosition (IK centre)
    p2ik::V3 trace() const { return mIk.traceCentre(); } // draw translation
    float face() const { return mFace; }
    p2ik::V3 target() const { return mTarget; }
    const p2ik::Mgr& ik() const { return mIk; }
    bool ikActive() const { return mIk.active(); }
    const p2ik::Parms& ikParms() const { return mIkParms; }

    static bool isStartFlickFor(const P2BigFootParms& p, int stuck, float flickTimer);
    bool isStartFlick(int stuck) const { return isStartFlickFor(mParms, stuck, mFlickTimer); }
    // IKSystemMgr::isCollisionCheck for leg `leg`: lifting/descending (state 1/2)
    // with a move ratio above 1.
    bool footPressing(int leg) const;

    // Body matrix: T(trace) * RotY(face) * S(scale) (Obj::doAnimationIKSystem).
    p2ik::M34 bodyMatrix() const;
    // Current world matrix of every joint: clip body, IK legs once programmed.
    const p2ik::M34* jointsWorld() const { return mJoints; }
    // World centre of retail collision node `node` (pc_p2_bigfoot_tables.h kColl).
    p2ik::V3 collCentre(int node) const;
    // Model-space matrix of every joint (inverse body * world) for the skin draw.
    void jointsModel(p2ik::M34 out[kJoints]) const;
    // Model-space joint matrices of `clip` at source frame `frame` (tables, lerped).
    static void clipJoints(int clip, float frame, p2ik::M34 out[kJoints]);
    static int clipFrames(int clip);
    static int keyAt(int clip, int frame);

private:
    void transit(P2LongLegsState next, const P2BigFootInput& in, P2BigFootOutput& out);
    void cleanup(P2LongLegsState s);
    void startMotion(int clip);
    void setIKParameter();
    void resetFlickWalkTimeMax(float roll);
    void setFlickWalkTimeMax(float roll);
    void getTargetPosition(const P2BigFootInput& in);
    void pose();

    P2BigFootParms mParms;
    p2ik::Parms mIkParms;
    p2ik::Mgr mIk;
    P2LongLegsState mState = P2LongLegsState::Stay;
    P2LongLegsState mNext = P2LongLegsState::Stay;
    bool mHasNext = false;
    p2ik::V3 mHome, mPos, mTarget;
    float mFace = 0.0f;
    int mClip = ClipLanding;
    int mFrame = 0;
    int mKey = -1;
    bool mStopped = false;
    bool mFinish = false;
    bool mEnded = false;
    float mStateTimer = 0.0f;
    float mFlickTimer = 0.0f;
    float mFlickWalkTimeMax = 0.0f;
    bool mEnraged = false;
    bool mBitterImmune = true;
    float mRoll[4] = {0.0f, 0.0f, 0.0f, 0.0f};
    p2ik::GroundFn mGround = nullptr;
    void* mGroundCtx = nullptr;
    p2ik::M34 mJoints[kJoints];
};
