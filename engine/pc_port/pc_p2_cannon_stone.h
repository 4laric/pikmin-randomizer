#pragma once

#include <cstdint>

// Isolated Armored/Decorated Cannon Beetle Larva Stone projectile policy.
// The Stone is Game::Rock::Obj with mRockType == EnemyID_Stone (74), fired by
// Kabuto (75) / Rkabuto (95) through Obj::createStoneAttack. It deliberately
// has no engine, map, creature, sound or effect dependency: a future host
// integration owns terrain movement, target enumeration, receiver stimulation
// and the firing Kabuto FSM. The host owns actual locomotion; this policy owns
// the source state machine, steering command, contact classification and
// strike/destruction events.
//
// Source reference: projectPiki/pikmin2 revision
// 632af93787b9c95b63f0c13be32b161375ce3a96 (US GPVE01 rev 0):
//   src/plugProjectNishimuraU/Rock.cpp / RockState.cpp,
//   src/plugProjectNishimuraU/Kabuto.cpp (createStoneAttack),
//   include/Game/Entities/Rock.h / Kabuto.h.
// See docs/PIKMIN2_CANNON_STONE_PROJECTILE.md for the contract.

struct P2CannonStoneVec3 {
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
};

// mRockType (Rock.h:116). This slice models the fired Stone; the falling/
// rolling Rock variant's Wait/Appear/Fall/DropWait states are a separate
// bounded slice and are NOT implemented here. The variant is still carried so
// the source Rock-vs-Rock mutual-collision branch can be classified.
enum class P2CannonStoneVariant { Stone, Rock };

// Lifecycle phases, mapped to the Rock FSM (Rock.h:178-186):
//   Move   = ROCK_Move. Stone onInit starts directly here (Rock.cpp:88-93):
//            initMoveVelocity then ROCK_Move; no Wait/Appear/Fall for Stone.
//            updateMoveVelocity + moveRockScaleUp + timer run each tick; health
//            <= 0 or timer > 15 s transits to Dead (RockState.cpp:229-241).
//   Dead   = ROCK_Dead. Target velocity zeroed and the dead motion started
//            (RockState.cpp:261-269); atari is disabled and the object is
//            constrained on the first exec (RockState.cpp:275-286).
//   Killed = kill(nullptr) after the Dead animation's KEYEVENT_END
//            (RockState.cpp:283-285). The host frees/reuses the slot.
enum class P2CannonStonePhase { Inactive, Move, Dead, Killed };

// Contact classification for collisionCallback (Rock.cpp:204-238). NaviPiki is
// `other->isNavi() || other->isPiki()`; everything else that is not a Teki is
// still non-Navi/Piki and forces health to zero.
enum class P2CannonStoneContactKind { NaviPiki, Teki, Other };

enum class P2CannonStoneStrikeKind { None, Press, Attack };

// Host-supplied parameters. Values fixed by the source are compile-time
// constants on P2CannonStone; the rest are parm/host inputs and are never
// invented by the policy.
struct P2CannonStoneConfig {
    P2CannonStoneVariant variant = P2CannonStoneVariant::Stone;
    float moveSpeed = 0.0f;         // general mMoveSpeed (Stone fp06 disc 250)
    float searchRumbleSpeed = 0.0f; // proper fp01 (disc 100); homing move speed
    float turnSpeed = 0.0f;         // general mTurnSpeed (per-update fraction)
    float maxTurnAngle = 0.0f;      // general mMaxTurnAngle (degrees)
    float attackDamage = 0.0f;      // general mAttackDamage (InteractPress)
    float sightRadius = 0.0f;       // general mSightRadius (homing search range)
    float collisionRadius = 0.0f;   // trace sphere radius (Rock 40 / child 27)
    float health = 0.0f;            // general mHealth (Stone disc 99999)
};

// Host target snapshot for the homing branch. The host picks the active Navi
// or the nearest Pikmin/Navi within mSightRadius and the 180-degree search
// angle (Rock.cpp:370-386; 180 degrees = unrestricted, see
// kHomingSearchAngleDegrees). The policy only steers. hasTarget=false mirrors
// the source's no-target fallback (targetPos = position + mTargetVelocity).
struct P2CannonStoneTarget {
    bool hasTarget = false;
    P2CannonStoneVec3 position;
};

// Called once per 30 Hz source tick while the Stone is in Move. The host
// applies the policy's target velocity with the engine creature physics and
// returns the resulting position/velocity. `wall` mirrors wallCallback
// (Rock.cpp:244-249) and interrupts Move into Dead. Return false only when no
// trace was performed (the policy then integrates target velocity itself).
struct P2CannonStoneTraceResult {
    P2CannonStoneVec3 position;
    P2CannonStoneVec3 velocity;
    bool wall = false;
};

typedef bool (*P2CannonStoneTraceFn)(void* context, const P2CannonStoneVec3& position,
                                     const P2CannonStoneVec3& targetVelocity, float delta,
                                     float radius, P2CannonStoneTraceResult& result);

// One recorded hit. Press is InteractPress on a grounded Navi/Piki, attributed
// to mSourceEnemy when set and to the Stone itself otherwise (Rock.cpp:212-219).
// Attack is InteractAttack with the source-fixed 250 damage (Rock.cpp:221-223).
struct P2CannonStoneStrike {
    P2CannonStoneStrikeKind kind = P2CannonStoneStrikeKind::None;
    float damage = 0.0f;
    std::uint64_t targetToken = 0;
    std::uint64_t attributedToken = 0;
    bool attributedToSource = false;
};

struct P2CannonStoneContactResult {
    bool ignored = false;                // source-enemy atari grace (Rock.cpp:298-304)
    bool strikeEmitted = false;
    P2CannonStoneStrike strike;
    bool healthZeroed = false;           // !isNaviOrPiki contact forces mHealth = 0
    bool selfCollisionSuppressed = false; // Rock-vs-Rock setCollEvent suppression
};

class P2CannonStone {
public:
    static constexpr float kSourceDelta = 1.0f / 30.0f;
    static constexpr float kMoveTimeoutSeconds = 15.0f;   // RockState.cpp:238
    static constexpr float kRollScaleUpPerSecond = 5.0f;  // Rock.cpp:336-337
    static constexpr float kInitialScale = 0.0001f;       // Rock.cpp:53
    static constexpr float kAtariGraceSeconds = 1.0f;     // Rock.cpp:300
    // getNearestPikminOrNavi searchAngle in degrees (Rock.cpp:376). 180 = PI
    // radians, which passes every horizontal angle (enemyAction.cpp:21,45).
    static constexpr float kHomingSearchAngleDegrees = 180.0f;
    static constexpr float kTekiAttackDamage = 250.0f;    // Rock.cpp:222
    static constexpr float kNonHomingCurrentWeight = 0.01f; // Rock.cpp:391-393
    static constexpr float kNonHomingTargetWeight = 0.99f;

    void reset(const P2CannonStoneConfig& config);

    // createStoneAttack birth (Kabuto.cpp:268-290) + Stone onInit
    // (Rock.cpp:88-93). `mouthPosition` must already include the source's
    // +25 y mouth offset (see mouthBirthPosition). faceDir is the firing
    // Kabuto's facing; homing is true only for Rkabuto. sourceToken is the
    // firing enemy (0 = none); selfToken identifies this Stone for Press
    // attribution. Returns false on invalid input or if not Inactive.
    bool birth(const P2CannonStoneVec3& mouthPosition, float faceDir, bool homing,
               std::uint64_t sourceToken, std::uint64_t selfToken);

    // One 30 Hz source update (ROCK_Move). delta must equal kSourceDelta.
    // `target` is the host's homing snapshot; it is ignored by the non-homing
    // branch. Transits Move -> Dead on wall contact, health <= 0 or the 15 s
    // timeout.
    bool update(float delta, const P2CannonStoneTarget& target,
                P2CannonStoneTraceFn trace = nullptr, void* traceContext = nullptr);

    // collisionCallback (Rock.cpp:204-238). The host classifies the colliding
    // creature and its grounded state. Records a strike, forces health to zero
    // for non-Navi/Piki contacts and reports Rock-vs-Rock suppression.
    P2CannonStoneContactResult contact(P2CannonStoneContactKind kind, bool targetOnFloor,
                                       bool targetIsRock, std::uint64_t targetToken);

    // wallCallback (Rock.cpp:244-249): Move -> Dead.
    bool notifyWallContact();

    // hipdropCallBack (Rock.cpp:190-198): Move -> Dead unless bittered.
    bool notifyHipdrop(bool bittered);

    // Dead state (RockState.cpp:275-286): once the host reports the dead
    // animation's KEYEVENT_END, request kill(nullptr). Returns true exactly
    // once on Dead -> Killed; false in any other phase.
    bool finishDeath();

    P2CannonStonePhase phase() const { return mPhase; }
    bool isAlive() const { return mPhase == P2CannonStonePhase::Move; }
    bool homing() const { return mHoming; }
    float faceDir() const { return mFaceDir; }
    float timer() const { return mTimer; }
    float scale() const { return mScale; }
    float health() const { return mHealth; }
    bool hasHealthZeroed() const { return mHealthZeroed; }
    std::uint64_t sourceToken() const { return mSourceToken; }
    std::uint64_t selfToken() const { return mSelfToken; }
    const P2CannonStoneVec3& position() const { return mPosition; }
    const P2CannonStoneVec3& velocity() const { return mVelocity; }
    const P2CannonStoneVec3& targetVelocity() const { return mTargetVelocity; }

    // True while a collision with the source enemy must be ignored
    // (ignoreAtari, Rock.cpp:298-304).
    bool shouldIgnoreAtari(std::uint64_t targetToken) const;

    // Source birth helpers, exposed for the host/fixtures:
    // worldMat mouth joint position + (0, 25, 0) (Kabuto.cpp:276).
    static P2CannonStoneVec3 mouthBirthPosition(const P2CannonStoneVec3& mouthJointWorldPos);
    // getDirection(faceDir) * moveSpeed (Rock.cpp:356-362, trig.h:182-186).
    static P2CannonStoneVec3 initialVelocity(float faceDir, float moveSpeed);

private:
    void enterDead();
    void steerTo(const P2CannonStoneVec3& targetPos);

    P2CannonStoneConfig mConfig;
    P2CannonStonePhase mPhase = P2CannonStonePhase::Inactive;
    P2CannonStoneVec3 mPosition;
    P2CannonStoneVec3 mVelocity;       // last traced/actual velocity
    P2CannonStoneVec3 mTargetVelocity; // steering command
    float mFaceDir = 0.0f;
    float mTimer = 0.0f;
    float mScale = kInitialScale;
    float mHealth = 0.0f;
    bool mHoming = false;
    bool mHealthZeroed = false;
    std::uint64_t mSourceToken = 0;
    std::uint64_t mSelfToken = 0;
};

// Fixed-capacity supply pool over the Rock manager's shared object array
// (RockMgr.cpp:101-115). The host configures the real manager limit, which is
// shared with falling Rock objects. Failed supply returns nullptr with no
// partial state, mirroring the source's silent tolerance of a failed birth
// (Kabuto.cpp:281-288).
class P2CannonStonePool {
public:
    explicit P2CannonStonePool(int capacity) : mCapacity(capacity > 0 ? capacity : 0) {}

    P2CannonStone* spawn(const P2CannonStoneVec3& mouthPosition, float faceDir, bool homing,
                         std::uint64_t sourceToken, std::uint64_t selfToken,
                         const P2CannonStoneConfig& config);

    int capacity() const { return mCapacity; }
    int activeCount() const;

private:
    static constexpr int kMaxStones = 16;
    int mCapacity;
    P2CannonStone mStones[kMaxStones];
    bool mUsed[kMaxStones] = {};
};
