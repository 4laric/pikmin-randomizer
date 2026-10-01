// Campaign OWN Jellyfloat host (wave 3 flyers, #960): drives the source Kurage
// FSM (pc_p2_kurage_fsm.h, KurageState.cpp) on a bound P1 host actor.
//
// The bound BTeki is the vehicle: it carries health, the Pikmin stickers, the
// collision the Pikmin hit and the engine corpse. Its P1 strategy is suppressed
// (pc_p2_kurage_teki_suppress_ai) and this host owns movement, facing, flying,
// the suction of Pikmin, the flick and death, per the retail source:
//
//  * EB_Untargetable == EnemyBase::isFlying() is mirrored onto CF_IsFlying
//    (pc_p2_flyer.h): ground Pikmin cannot chase a hovering body, thrown Pikmin
//    latch onto its retail collision spheres (pc_p2_flyer_coll.h), and once
//    enough weight drags it into Fall -> Land -> Ground the whole squad fights
//    it (KurageState.cpp: Land/Ground/GroundFlick clear EB_Untargetable).
//  * Fixed 30 Hz source tick (P2GroinkSourceClock), deterministic LCG seeded
//    from the generator token: no wall clock in sim state.
#pragma once

#include "pc_p2_flyer.h"
#include "pc_p2_flyer_coll.h"
#include "pc_p2_groink_clock.h"
#include "pc_p2_kurage_fsm.h"
#include "pc_p2_kurage_fx.h"
#include "pc_p2_kurage_own.h"
#include "pc_p2_onikurage_mouth.h"
#include "pc_p2_retail_player.h"

class BTeki;
class CollPart;
class Navi;
class Piki;
class Shape;
class Vector3f;

class P2KurageOwn {
public:
    // Binds the FSM to the actor. `restShape` (optional) supplies the vertex
    // centroid used as the body joint offset.
    bool init(BTeki* actor, unsigned generator, unsigned source, CollPart* mouth, Shape* restShape);
    bool active() const { return mActive; }
    bool escaped() const { return mEscaped; }
    // One real frame. Returns true once the host teardown (pcEscapeNow) ran; the
    // caller must not touch the actor's binding again that frame.
    bool tick(BTeki* actor, float dt);
    // Detach from a dying/forgotten actor (restores the vehicle collision).
    void detach(BTeki* actor);
    p2kurage::Motion motion() const { return mMotion; }
    // #972: clip + source frame of the pose drawn this frame. The source clip
    // steps at 30 Hz; the fraction of the next tick already elapsed is added so
    // the pose bank is sampled at the real frame rate.
    const char* drawClip() const;
    float drawFrame() const;
    p2kurage::State state() const { return mState; }
    bool untargetable() const { return mUntargetable; }
    float life() const { return p2kurageown::general(mVariant).life; }
    bool captainHeld() const { return mCaptain != nullptr; }
    bool greater() const { return mVariant == p2kurage::Variant::Greater; }
    p2kurage::Variant variant() const { return mVariant; }

private:
    void sourceTick(BTeki* actor);
    void applyOutput(BTeki* actor, const p2kurage::Out& out);
    float rand01();
    struct Target {
        bool found = false;
        float x = 0.0f, y = 0.0f, z = 0.0f;
    };
    Target search(BTeki* actor, float altitude, bool& suckTarget, bool& suckAny) const;
    int countStuck(BTeki* actor, bool& purple) const;
    void suckPikmin(BTeki* actor, float mapY);
    void flickStuck(BTeki* actor, float chance, float knockback, float damage);
    void flickNearby(BTeki* actor, float radius, float knockback, float damage);
    void startMotion(p2kurage::Motion m);
    // OniKurage captain mouth (suckNavi / updateCollPartOffset / flickStickNavi).
    void suckNavi(BTeki* actor, float mapY);
    void updateCaptain(BTeki* actor, const p2kurage::Out& out);
    void placeMouthJoint(BTeki* actor);
    void logCaptainHold(BTeki* actor) const;
    Vector3f stomachAnchor(BTeki* actor) const;
    void releaseCaptain(BTeki* actor, const char* why, bool drop);

    bool mActive = false;
    bool mEscaped = false;
    unsigned mGenerator = 0;
    unsigned mSource = 57;
    p2kurage::Variant mVariant = p2kurage::Variant::Lesser;
    CollPart* mMouth = nullptr;

    p2kurage::Fsm mFsm;
    p2kurage::Out mLast;
    P2GroinkSourceClock mClock;
    p2retail::Player mPlayer;
    p2kurage::Motion mMotion = p2kurage::Motion::None;
    p2kurage::State mState = p2kurage::State::Wait;
    p2kurage::KeyEvent mPendingKey = p2kurage::KeyEvent::None;
    bool mPendingEnd = false;

    P2FlyerColl mColl;
    p2flyer::Vec3 mBody;

    float mYaw = 0.0f;
    bool mUntargetable = true;
    float mAltitude = 0.0f;
    float mVelX = 0.0f, mVelZ = 0.0f, mVelY = 0.0f;
    float mHomeX = 0.0f, mHomeZ = 0.0f;
    float mTargetX = 0.0f, mTargetZ = 0.0f;
    bool mHasTarget = false;
    float mDistGoal = 1.0e9f;
    unsigned mRng = 1u;
    int mSucked = 0;
    bool mSuckFull = false;
    p2kuragefx::State mFx;
    int mWinRolled = 0;   // log: in-range Pikmin that won the fp12 roll this suction window
    int mWinAdmitted = 0; // log: of those, taken into the suction

    // OniKurage captain mouth: one captain through the shared demon captain bridge.
    p2onikurage::MouthSlots mSlots;
    Navi* mCaptain = nullptr;
    int mCaptainSlot = 0;
    std::uint64_t mOwnerToken = 0;
    int mCaptures = 0;

    float mLastHealth = 0.0f;
    int mTicks = 0;
    float mLogTimer = 0.0f;
    int mStuckPrev = 0;
    bool mDeadLogged = false;
    bool mLandLogged = false;
};
