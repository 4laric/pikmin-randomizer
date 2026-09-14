#pragma once

#include <cstdint>

// Isolated falling Rock (EnemyID 19) hazard FSM policy. Game::Rock::Obj /
// Rock::Mgr manage both the falling Rock (19) and the fired Stone (74) in one
// shared object array (RockMgr.cpp:101-115). This slice owns only the
// Rock-only states ROCK_Wait / ROCK_Appear / ROCK_DropWait / ROCK_Fall plus
// the shared ROCK_Dead / onKill teardown. The Stone's rolling ROCK_Move
// projectile path is a separate FSM group and stays in pc_p2_cannon_stone.*
// (#406); it is neither implemented nor modified here.
//
// The policy deliberately has no engine, map, creature, sound or effect
// dependency: a future host integration owns map/creature physics, Wait target
// detection, receiver stimulation, shadow/effect/sound and the animation bank.
// The host supplies movement traces, detection results and the random cull
// timer through explicit input and function-pointer contracts.
//
// Source reference: projectPiki/pikmin2 revision
// 632af93787b9c95b63f0c13be32b161375ce3a96 (US GPVE01 rev 0):
//   src/plugProjectNishimuraU/Rock.cpp (onInit/onKill collisionCallback/
//   fallRockScaleUp/wallCallback/hipdropCallBack),
//   src/plugProjectNishimuraU/RockState.cpp (Wait/Appear/DropWait/Fall/Dead),
//   include/Game/Entities/Rock.h.
// See docs/PIKMIN2_ROCK_HAZARD.md for the contract.

struct P2RockHazardVec3 {
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
};

// Phases mapped to the source Rock FSM (Rock.h:178-186). Inactive is the
// reset state. Wait/Appear/DropWait/Fall are the four Rock-only falling states
// this slice owns. Dead is the shared teardown state (RockState.cpp:261-286);
// Killed is kill(nullptr) after the Dead animation's KEYEVENT_END
// (RockState.cpp:283-285). ROCK_Move is not reachable for EnemyID_Rock
// (Rock.cpp:71-93 starts Move only for EnemyID_Stone) and is out of scope.
enum class P2RockHazardPhase { Inactive, Wait, Appear, DropWait, Fall, Dead, Killed };

// Contact classification for collisionCallback (Rock.cpp:204-238). NaviPiki is
// `other->isNavi() || other->isPiki()`; Teki is `other->isTeki()`; everything
// else is Other. Both Teki and Other force mHealth to zero (notFakePiki).
enum class P2RockHazardContactKind { NaviPiki, Teki, Other };

enum class P2RockHazardStrikeKind { None, Press, Attack };

// Last animation requested through startMotion (Rock.h:159-163).
enum class P2RockHazardMotion { None, Run, Dead };

// Host/converter parameters. The fall/scale parms are the Rock onInit
// initial-setting values (Rock.cpp:36-41): mFallSpeed = general mSearchDistance,
// mFallOffset = general mSearchHeight, mScaleUpRate = general mSearchAngle.
// They are host inputs and are never invented by the policy.
struct P2RockHazardConfig {
    float fallSpeed = 0.0f;       // Rock.cpp:38
    float fallOffset = 0.0f;      // Rock.cpp:39
    float scaleUpRate = 0.0f;     // Rock.cpp:40, mScaleUpRate per source second
    float sightRadius = 0.0f;     // general mSightRadius (Wait detection, RockState.cpp:58)
    float attackDamage = 0.0f;    // general mAttackDamage (InteractPress, Rock.cpp:218)
    float collisionRadius = 0.0f; // host fall trace sphere radius
    float health = 0.0f;          // general mHealth
};

// Host Wait-detection snapshot. The host runs EnemyFunc::isThereOlimar then
// EnemyFunc::isTherePikmin at mSightRadius (RockState.cpp:59-65); the policy
// only evaluates the result and never enumerates creatures.
struct P2RockHazardDetection {
    bool olimarInSight = false;
    bool pikminInSight = false;
};

// Host Fall trace. floorTriangle mirrors enemy->mFloorTriangle and colliding
// mirrors EB_Colliding (RockState.cpp:184-188). Return false only when no
// trace was performed (the policy then integrates the source fall velocity).
struct P2RockHazardTraceResult {
    P2RockHazardVec3 position;
    P2RockHazardVec3 velocity;
    bool floorTriangle = false;
    bool colliding = false;
};

typedef bool (*P2RockHazardTraceFn)(void* context, const P2RockHazardVec3& position,
                                    const P2RockHazardVec3& velocity, float delta,
                                    float radius, P2RockHazardTraceResult& result);

// onInit inputs (Rock.cpp:47-94). dropGroupNone is mDropGroup == EDG_None;
// timedAppear is mExistDuration != 0; initialTimer is the host-supplied
// randWeightFloat(1.5) result used only on the timed path (Rock.cpp:73-76).
// sourceToken is mSourceEnemy (0 = none), used for Press attribution and the
// 1 s atari grace; selfToken identifies this Rock for Attack/Press self
// attribution.
struct P2RockHazardInit {
    P2RockHazardVec3 position;
    bool dropGroupNone = true;
    bool timedAppear = false;
    float initialTimer = 0.0f;
    std::uint64_t sourceToken = 0;
    std::uint64_t selfToken = 0;
};

// One recorded hit. Press is InteractPress on a grounded Navi/Piki attributed
// to mSourceEnemy when set and to the Rock otherwise (Rock.cpp:210-220).
// Attack is InteractAttack with the source-fixed 250 damage (Rock.cpp:221-223).
struct P2RockHazardStrike {
    P2RockHazardStrikeKind kind = P2RockHazardStrikeKind::None;
    float damage = 0.0f;
    std::uint64_t targetToken = 0;
    std::uint64_t attributedToken = 0;
    bool attributedToSource = false;
};

struct P2RockHazardContactResult {
    bool ignored = false;                 // source-enemy atari grace (Rock.cpp:298-304)
    bool strikeEmitted = false;
    P2RockHazardStrike strike;
    bool healthZeroed = false;            // non-Navi/Piki contact forces mHealth = 0
    bool selfCollisionSuppressed = false; // Rock-vs-Rock setCollEvent suppression
};

class P2RockHazard {
public:
    static constexpr float kSourceDelta = 1.0f / 30.0f;
    static constexpr float kAppearTimerSeconds = 1.5f;    // RockState.cpp:53
    static constexpr float kInitialHiddenScale = 0.0001f; // Rock.cpp:51-55
    static constexpr float kAtariGraceSeconds = 1.0f;     // Rock.cpp:300
    static constexpr float kTekiAttackDamage = 250.0f;    // Rock.cpp:222
    static constexpr float kCullTimerRange = 1.5f;        // randWeightFloat(1.5), Rock.cpp:75

    void reset(const P2RockHazardConfig& config);

    // Falling-Rock onInit (Rock.cpp:47-94). dropGroupNone starts ROCK_Wait with
    // the 0.0001 hidden scale (Rock.cpp:51-55,78-80); otherwise ROCK_DropWait
    // (Rock.cpp:82-84). timedAppear disables EB_Cullable and seeds mTimer with
    // the host randWeightFloat(1.5) value (Rock.cpp:73-76). The shadow is
    // removed on both branches (Rock.cpp:86). Returns false on invalid input
    // or if the phase is not Inactive, leaving the state untouched.
    bool onInit(const P2RockHazardInit& init);

    // One 30 Hz source update. delta must equal kSourceDelta. Wait runs the
    // timer/detection branch (RockState.cpp:48-71), Appear runs fallRockScaleUp
    // (Rock.cpp:310-327), DropWait transits immediately (RockState.cpp:147-150)
    // and Fall applies the (0, -mFallSpeed, 0) velocity and dies on a floor
    // triangle or EB_Colliding (RockState.cpp:170-204).
    bool update(float delta, const P2RockHazardDetection& detection,
                P2RockHazardTraceFn trace = nullptr, void* traceContext = nullptr);

    // collisionCallback (Rock.cpp:204-238). The host classifies the colliding
    // creature and its grounded state. Records a strike, forces health to zero
    // for non-Navi/Piki contacts, sets EB_Colliding unless suppressed and
    // reports Rock-vs-Rock suppression. Only fires while atari is enabled.
    P2RockHazardContactResult contact(P2RockHazardContactKind kind, bool targetOnFloor,
                                      bool targetIsRock, std::uint64_t targetToken);

    // wallCallback (Rock.cpp:244-249) and hipdropCallBack (Rock.cpp:190-198)
    // transit to Dead only from ROCK_Move. The falling Rock never reaches
    // ROCK_Move, so both always return false for this FSM; they exist so a host
    // sharing the Obj callbacks can route them without branching on identity.
    bool notifyWallContact();
    bool notifyHipdrop(bool bittered);

    // StateDead::exec (RockState.cpp:275-286): once the host reports the dead
    // animation's KEYEVENT_END, request kill(nullptr). Returns true exactly
    // once on Dead -> Killed; false in any other phase.
    bool finishDeath();

    P2RockHazardPhase phase() const { return mPhase; }
    bool isAlive() const
    {
        return mPhase == P2RockHazardPhase::Wait || mPhase == P2RockHazardPhase::Appear
            || mPhase == P2RockHazardPhase::DropWait || mPhase == P2RockHazardPhase::Fall;
    }
    const P2RockHazardVec3& position() const { return mPosition; }
    const P2RockHazardVec3& velocity() const { return mVelocity; }
    const P2RockHazardVec3& targetVelocity() const { return mTargetVelocity; }
    float scale() const { return mScale; }
    float timer() const { return mTimer; }
    float health() const { return mHealth; }
    std::uint64_t sourceToken() const { return mSourceToken; }
    std::uint64_t selfToken() const { return mSelfToken; }

    // Source event flags, exposed for the host and fixtures.
    bool atari() const { return mAtari; }
    bool untargetable() const { return mUntargetable; }
    bool hardConstrained() const { return mHardConstrained; }
    bool animating() const { return mAnimating; }
    bool modelHidden() const { return mModelHidden; }
    bool cullable() const { return mCullable; }
    bool cullSound() const { return mCullSound; }
    bool shadow() const { return mShadow; }
    bool shadowForcedVisible() const { return mShadowForced; }
    bool fallEffectActive() const { return mFallEffect; }
    bool deadEffectCreated() const { return mDeadEffect; }
    bool animationCullingOff() const { return mAnimationCullingOff; }
    bool colliding() const { return mColliding; }
    P2RockHazardMotion motion() const { return mMotion; }
    bool motionStopped() const { return mMotionStopped; }

    // ignoreAtari (Rock.cpp:298-304): ignore mSourceEnemy while mTimer < 1.0.
    bool shouldIgnoreAtari(std::uint64_t targetToken) const;

private:
    void enterAppear();
    void enterFallFromAppear();
    void enterFallFromDropWait();
    void enterFall(); // shared Fall init
    void enterDead();

    P2RockHazardConfig mConfig;
    P2RockHazardPhase mPhase = P2RockHazardPhase::Inactive;
    P2RockHazardVec3 mPosition;
    P2RockHazardVec3 mVelocity;
    P2RockHazardVec3 mTargetVelocity;
    float mScale = 1.0f;
    float mTimer = 0.0f;
    float mHealth = 0.0f;
    bool mTimedAppear = false;
    std::uint64_t mSourceToken = 0;
    std::uint64_t mSelfToken = 0;
    bool mAtari = true;
    bool mUntargetable = false;
    bool mHardConstrained = false;
    bool mAnimating = true;
    bool mModelHidden = false;
    bool mCullable = true;
    bool mCullSound = true;
    bool mShadow = false;
    bool mShadowForced = false;
    bool mFallEffect = false;
    bool mDeadEffect = false;
    bool mAnimationCullingOff = false;
    bool mColliding = false;
    P2RockHazardMotion mMotion = P2RockHazardMotion::None;
    bool mMotionStopped = false;
};

// Fixed-capacity pool over the falling-Rock subset of the shared Rock manager
// array (RockMgr.cpp:101-115). The host configures the real shared limit; the
// pool models only slot supply/exhaustion/reuse. Exhaustion returns nullptr
// with no partial state, matching the source's silent tolerance of a failed
// birth.
class P2RockHazardPool {
public:
    explicit P2RockHazardPool(int capacity) : mCapacity(capacity > 0 ? capacity : 0) {}

    P2RockHazard* spawn(const P2RockHazardInit& init, const P2RockHazardConfig& config);
    P2RockHazard* spawn(const P2RockHazardVec3& position, bool dropGroupNone, bool timedAppear,
                        float initialTimer, std::uint64_t sourceToken, std::uint64_t selfToken,
                        const P2RockHazardConfig& config);

    int capacity() const { return mCapacity; }
    int activeCount() const;

private:
    static constexpr int kMaxRocks = 16;
    int mCapacity;
    P2RockHazard mRocks[kMaxRocks];
    bool mUsed[kMaxRocks] = {};
};
