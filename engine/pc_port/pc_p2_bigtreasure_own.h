#pragma once
// Engine-free source-order port of the Pikmin 2 Titan Dweevil (BigTreasure,
// enemy ID 73) for the campaign actor (#246). Source of truth (read-only
// public decomp, research revision 632af93787b9c95b63f0c13be32b161375ce3a96):
//   include/Game/Entities/BigTreasure.h        StateID / AnimID / Parms
//   src/plugProjectNishimuraU/BigTreasure.cpp  onInit, damageCallBack,
//       isAttackLimitTime, getTargetPosition, setTreasureAttack, the
//       per-weapon anim/time-max helpers, treasure capture/drop
//   src/plugProjectNishimuraU/BigTreasureState.cpp  the 12 FSM states
//   src/plugProjectNishimuraU/IKSystemMgr.cpp / IKSystemBase.cpp  leg gait
//   src/plugProjectYamashitaU/enemyAction.cpp  isStartFlick, flickStickPikmin
//   src/plugProjectYamashitaU/enemyBase.cpp    addDamage (flick timer)
//
// The core owns the FSM, the key-event animator, the leg gait (position and
// face direction), the weapon ownership (P2BigTreasureOwnership), the attack
// pacer and the element runtime. The host supplies one snapshot per 30 Hz
// source update (position, body health, counted Pikmin hits, candidate
// creatures, a map trace) and executes the returned commands (velocity/face,
// flicks, receiver hits, drops, kill request). No engine type is referenced.
//
// Adaptations (each forced by the P1 host or by missing data; see also the
// teki glue in pc_p2_bigtreasure_teki.cpp):
//  * Damage parts (#246 fix stage): the Titan carries its OWN collision tree,
//    built by the teki glue from the retail bigtreasure/enemycoll.txt (root
//    r250, tam1/tam2 body spheres, the four r25 weapon spheres elec/fire/gasi/
//    mizu on the otakara_* joints, four leg tube chains). A P1 InteractAttack
//    carries the CollPart the Pikmin is stuck to (nullptr for a ground swing);
//    the glue classifies it as a weapon part, another Titan part or none, and
//    damageCallBack routes it exactly as the source does: a weapon part hits
//    that weapon; no part (or a non-Piki source) does nothing; any other part
//    damages the body only once every weapon is gone. setupBigTreasureCollision
//    is mirrored: tam1/tam2 are '_t__' (not stickable) while armed and 'st__'
//    after the last drop; a dropped weapon's part becomes '_t__' radius 0.
//    Leg tube positions follow the gait feet (no leg IK joint solve).
//  * Blend animation: startBlendAnimation starts the new clip immediately;
//    KEYEVENT_END_BLEND is not produced (the 30-frame visual blend is not
//    reproduced). The one-frame event latch of EnemyBase::onKeyEvent is kept.
//  * Wait2_2 (anim 29, Walk) is wait2.bca without events (the second
//    registry row carries none); it is played from the same motion with its
//    events stripped.
//  * Boot-up demo: no movie system, so startBigTreasureBootUpDemo() is false
//    (Stay goes to Land on the tick after a target enters the private
//    radius, the source's no-demo branch). Zukan mode is not modelled.
//  * Gait: IKSystemBase foot motion is the source Lagrange curve in XZ; a foot
//    lands once moveRatio passes 2 (flat-ground equivalent of
//    onGroundPosition). Heights, leg IK joint solving and the trace-centre
//    spring are left to the P1 host (it integrates the returned velocity with
//    its own map collision and gravity).
//  * randWeightFloat / randFloat use a per-actor LCG (generator seed);
//    atan2/sin/cos replace JMAAtan2Radian and the dolsin/dolcos tables.
//  * Material colour, BGM, effects, shadows, stone/bitter/earthquake hooks
//    are not ported (no P1 source). EB_Bittered is always false in P1.
#include "pc_p2_bigtreasure.h"
#include "pc_p2_bigtreasure_elements.h"
#include "pc_p2_bigtreasure_receiver.h"
#include "pc_p2_motion_events.h"
#include "pc_p2_retail_player.h"
#include <cstddef>
#include <cstdint>
#include <istream>
#include <string>
#include <vector>

namespace p2btown {

constexpr float kPi = 3.14159265358979323846f;
constexpr float kTau = 6.28318530717958647692f;
constexpr float kSourceDelta = 1.0f / 30.0f;

using Vec3 = P2BigTreasureVec3;

// BigTreasure.h:57-72 (ordinals are the source StateID values).
enum class State : int {
    Null = -1, Dead = 0, Stay = 1, Land = 2, Wait = 3, ItemWait = 4, Flick = 5,
    PreAttack = 6, Attack = 7, PutItem = 8, DropItem = 9, Walk = 10, ItemWalk = 11,
};
const char* stateName(State state);

// BigTreasure.h:469-512 (enemyanimmgr.txt registry row order).
enum Anim : int {
    AnimAppear = 0, AnimAppear2 = 1, AnimWait1 = 2,
    AnimPreAttackF = 3, AnimAttackF = 4, AnimAttackEndF = 5,
    AnimPreAttackFR = 6, AnimAttackFR = 7, AnimAttackEndFR = 8,
    AnimPreAttackFL = 9, AnimAttackFL = 10, AnimAttackEndFL = 11,
    AnimPreAttackFB = 12, AnimAttackFB = 13, AnimAttackEndFB = 14,
    AnimPreAttackW = 15, AnimAttackW = 16, AnimAttackEndW = 17,
    AnimPreAttackG = 18, AnimAttackG = 19, AnimAttackEndG = 20,
    AnimPreAttackE = 21, AnimAttackE = 22, AnimAttackEndE = 23,
    AnimDropItem = 24, AnimWait2 = 25, AnimFlick = 26, AnimDead = 27,
    AnimMove1 = 28, AnimWait2_2 = 29, AnimCount = 30,
};
// Registry clip name (lowercase, no .bca) for an AnimID; nullptr if invalid.
const char* animClipName(int anim);

// SysShape/KeyEvent.h.
enum KeyType : int {
    KeyLoopStart = 0, KeyLoopEnd = 1, Key2 = 2, Key3 = 3, Key4 = 4, Key5 = 5, Key6 = 6,
    Key7 = 7, Key8 = 8, Key9 = 9, Key10 = 10, Key11 = 11, Key100 = 100, KeyEnd = 1000,
};

// EnemyParmsBase general block + BigTreasure proper block. Initialisers are
// the RETAIL US GPVE01 values of bigtreasure/enemyparm.txt (the disc facts
// recorded in docs/PIKMIN2_ENGINE_DISC_PARMS.md); parseEnemyParm overwrites
// them from the staged file.
struct Params {
    // general
    float health = 5000.0f;         // fp00
    float moveSpeed = 100.0f;       // fp06
    float maxTurnAngle = 60.0f;     // fp28 (degrees)
    float territoryRadius = 250.0f; // fp09
    float homeRadius = 75.0f;       // fp10
    float privateRadius = 100.0f;   // fp11
    float sightRadius = 300.0f;     // fp12
    float viewAngle = 180.0f;       // fp13 (degrees)
    float shakeChance = 1.0f;       // fp16
    float shakeKnockback = 100.0f;  // fp17
    float shakeDamage = 0.0f;       // fp18
    float attackDamage = 10.0f;     // fp24
    int shakeOffBlowA = 6, shakeOffSticking1 = 5, shakeOffBlowB = 12, shakeOffSticking2 = 10;
    int shakeOffBlowC = 17, shakeOffSticking3 = 20, shakeOffBlowD = 22; // ip01..ip07
    // proper (BigTreasure.h:305-323)
    float baseFactor = 3.0f;          // fp01 -> IK mBottomJointMoveSpeed
    float raiseDecelFactor = -0.2f;   // fp02 -> mRaiseSlowdownFactor
    float downwardDecelFactor = 0.5f; // fp03 -> mDownwardAccelFactor
    float minReducedAccel = -2.0f;    // fp04 -> mMinDecelFactor
    float maxDecelAccel = 10.0f;      // fp05 -> mMaxDecelFactor
    float legSwing = 120.0f;          // fp06 -> mHeightOffset
    float elecWait = 2.5f;            // fp10
    float fireWait1 = 2.8f;           // fp11
    float fireWait2 = 2.5f;           // fp31
    float gasWait = 2.5f;             // fp12
    float waterWait = 2.5f;           // fp13
    float elecAttackMax = 5.0f;       // fp20
    float fireAttackMax = 5.0f;       // fp21
    float gasAttackMax = 5.0f;        // fp22
    float waterAttackMax = 5.0f;      // fp23
    bool retail = false;              // true once a staged enemyparm.txt was parsed
};
// Retail `bigtreasure/enemyparm.txt`: blocks ended by {_eof}; `{tag} <kind>
// <value>` rows; '#' comments. Blocks are told apart by content (general has
// fp00; proper has fe00/fw00 or fp01+fp20 without fp00; Creature::Property
// has s000), never by position. Fails closed on malformed input or a
// nonphysical value.
bool parseEnemyParm(std::istream& in, Params& out, std::string& error);

// ---------------------------------------------------------------------------
// Staged bank: per-clip pose frames plus the otakara_* joint matrices at each
// staged pose (so captured weapons ride the animated joints), and the leg
// layout used by IKSystemMgr::startProgramedIK.
enum Joint : int {
    JointElec = 0, JointFire = 1, JointGas = 2, JointWater = 3, JointLoozy = 4, JointKosi = 5,
    // Attack emit joints (BigTreasureAttack.cpp: update*EmitPosition reads the
    // *_eff world matrix; fire emits along its column 0).
    JointElecEff = 6, JointFireEff = 7, JointGasEff = 8, JointWaterEff = 9, JointCount = 10
};
const char* jointName(int joint);

struct Mat34 { float m[3][4] = {{1, 0, 0, 0}, {0, 1, 0, 0}, {0, 0, 1, 0}}; };
struct PoseJoints { int frame = 0; Mat34 joint[JointCount]; bool have[JointCount] = {}; };
struct ClipBank {
    std::string name;
    int frames = 0;
    std::vector<PoseJoints> poses; // staged frames, ascending
};
struct LegLayout {
    // IKSystemMgr::startProgramedIK: mIKDistanceOffset = |owner - leg0 foot|;
    // mLegHeight[i] = atan2(foot_i - owner) - faceDir. Leg order is the
    // setupJoint order: 0 rhand, 1 lhand, 2 rfoot, 3 lfoot.
    float distance = 150.0f;
    float angle[4] = {-0.785398f, 0.785398f, -2.356194f, 2.356194f};
    bool staged = false;
};
struct Bank {
    ClipBank clip[AnimCount];
    Mat34 bind[JointCount]; // bind-pose fallback
    LegLayout legs;
    bool staged = false;
};
Bank defaultBank();
// p2-bigtreasure-bank.txt grammar (see the .cpp). Fails closed.
bool parseBank(std::istream& in, Bank& bank, std::string& error);

// ---------------------------------------------------------------------------
// IKSystemMgr + 4 x IKSystemBase gait (IKSystemMgr.cpp:99-488,
// IKSystemBase.cpp:88-320). XZ only; see the header note.
struct GaitParams {
    float moveSpeed = 100.0f;       // mMoveSpeed (general fp06)
    float minimumMoveSpeed = 0.0f;  // mMinimumMoveSpeed (default)
    float viewAngle = 30.0f;        // mEnragedAngle default (getViewAngle)
    float maxTurnAngle = 60.0f;     // general fp28
    float bottomSpeed = 3.0f;       // proper fp01
    float raiseSlow = -0.2f;        // proper fp02
    float downAccel = 0.5f;         // proper fp03
    float minDecel = -2.0f;         // proper fp04
    float maxDecel = 10.0f;         // proper fp05
    float moveInterpolation = 0.75f; // mMoveInterpolationRate default
};

class Gait {
public:
    void init(const GaitParams& params, const LegLayout& legs, const Vec3& position, float faceDir);
    void startProgramedIK(const Vec3& ownerPos, float faceDir);
    void startIKMotion();
    void finishIKMotion() { mInMotion = false; }
    void forceFinishIKMotion() { mInMotion = false; mOnGround = true; }
    bool isFinishIKMotion() const;
    bool active() const { return mActive; }
    bool inMotion() const { return mInMotion; }
    // IKSystemMgr::doUpdate: legs, controller, face dir, centre. `target` is
    // mTargetPosition (setIKSystemTargetPosition). Returns the leg index that
    // landed this update (or -1) for diagnostics.
    int update(const Vec3& ownerPos, float ownerFace, const Vec3& target, float dt);
    const Vec3& centre() const { return mCentre; }
    // IKSystemMgr::mTraceCentrePosition: a damped spring (calcTraceCentre-
    // Position) that follows the foot-average centre. The source draws the
    // body there (BigTreasure doAnimationIKSystem) while mPosition, and so
    // collision and gameplay, is the raw centre, which sways with each step.
    const Vec3& traceCentre() const { return mTrace; }
    float faceDir() const { return mFaceDir; }
    int legState(int leg) const { return mLegState[leg]; }
    float moveRatio(int leg) const { return mLeg[leg].ratio; }
    const Vec3& foot(int leg) const { return mLeg[leg].pos; }
    int steps() const { return mSteps; }

private:
    struct Leg {
        Vec3 pos, top, middle, bottom;
        float ratio = 0.0f, timer = 0.0f;
        bool grounded = true;
    };
    void startMove(int leg);
    void setNextCentrePosition(const Vec3& ownerPos, float ownerFace, const Vec3& target);
    GaitParams mParams;
    Leg mLeg[4];
    float mLegAngle[4] = {};
    float mDistance = 0.0f;
    Vec3 mLegTarget[4];
    int mLegState[4] = {0, 0, 0, 0};
    bool mActive = false, mInMotion = false, mOnGround = false;
    Vec3 mCentre;
    Vec3 mTrace, mTraceVel;
    float mFaceDir = 0.0f;
    int mSteps = 0;
};

// ---------------------------------------------------------------------------
// Key-event animator over the retail P2_RETAIL_EVENTS_1 table (the vendored
// p2retail::Player: positive-timer SysShape semantics, loops, finishMotion),
// with EnemyBase::onKeyEvent's one-frame latch (doAnimationCullingOff clears
// mIsPlaying, animate latches the last event).
class Animator {
public:
    bool load(const p2retail::Table& table, std::string& error);
    bool loaded() const { return mLoaded; }
    bool start(int anim);                  // EnemyBase::startMotion(id)
    void stop() { mStopped = true; }       // stopMotion
    void resume() { mStopped = false; }    // startMotion()
    void finish() { mPlayer.finishMotion(true); } // finishMotion
    void animate();                        // one source update
    bool is(int type) const { return mPlaying && mType == type; }
    bool playing() const { return mPlaying; }
    int latched() const { return mType; }
    int anim() const { return mAnim; }
    float frame() const { return mPlayer.frame(); }
    int frames() const { return mAnim >= 0 ? mMotion[mAnim].duration : 0; }

private:
    p2retail::Motion mMotion[AnimCount];
    bool mHave[AnimCount] = {};
    p2retail::Player mPlayer;
    int mAnim = -1;
    bool mStopped = false, mPlaying = false, mLoaded = false;
    int mType = KeyLoopStart;
};

// ---------------------------------------------------------------------------
// Host snapshot and commands.
struct Candidate {
    std::uint64_t id = 0;
    Vec3 pos;
    bool alive = true;
    bool navi = false;
    bool pikmin = false;
    bool stuckToSelf = false;   // Piki stuck on the Titan
    bool stuckElsewhere = false; // isStickTo() && mSticker != Titan
    bool blue = false;          // Blue Pikmin (never a water shot target)
    bool buried = false;        // not searchable (Piki::isSearchable)
    int stuckPart = -2;         // HitPart of the Titan CollPart it is stuck to
};
// Titan collision part carried by a hit (BigTreasure::damageCallBack's
// `collpart`): one of the four weapon parts (P2BigTreasureWeapon order:
// elec, fire, gasi, mizu), another Titan part, or none (a P1 ground swing
// passes no CollPart).
enum HitPart : int { PartNone = -2, PartOther = -1 };
// One counted P1 InteractAttack on the Titan.
struct Hit {
    int part = PartNone;
    float damage = 0.0f;
    bool fromPiki = true;
};

// Retail enemycoll.txt node (CollTree text format): child count, radius,
// {id}, {code}, offset, joint index, attribute, then `{ children }`.
struct CollNode {
    std::string id, code;
    float radius = 0.0f;
    Vec3 offset;
    int joint = 0;
    int attribute = 0;
    int parent = -1; // index into the flat pre-order list, -1 for the root
};
// Parses the retail tree into pre-order nodes. Fails closed on malformed input.
bool parseCollTree(std::istream& in, std::vector<CollNode>& out, std::string& error);
// Weapon index (P2BigTreasureWeapon) of a weapon part id ("elec", "fire",
// "gasi", "mizu"), else -1. setupTreasure collTags order.
int weaponForPartId(const std::string& id);
struct TickInput {
    Vec3 position;
    float health = 0.0f;       // body health (host mHealth) BEFORE this tick's body damage
    float groundY = 0.0f;
    const Candidate* candidates = nullptr;
    std::size_t count = 0;
    const Hit* hits = nullptr;
    std::size_t hitCount = 0;
    P2BigTreasureElementHost element; // map trace for elec/water
};
struct ElementHit {
    std::uint64_t id = 0;
    bool navi = false;
    // BigTreasureAttack.cpp: a captain that refuses the element stimulus is
    // flicked (randWeightFloat(1) < *_NAVI_FLICK_CHANCE) or gets a 0-damage
    // InteractAttack. The roll is drawn from the actor RNG up front.
    bool naviFlick = false;
    P2BigTreasureReceiverHit hit;
};
struct Drop {
    int weapon = -1;        // P2BigTreasureWeapon, -1 Louie
    Vec3 position;          // joint world position at the drop
    Vec3 velocity;          // (0,100,0) weapons / (0,150,0) Louie
};
struct Transition { State from = State::Null; State to = State::Null; };
struct TickOutput {
    bool valid = false;
    std::vector<Transition> entered;
    // movement (IK centre and face direction)
    float faceDir = 0.0f;
    Vec3 velocity;           // xz per second for the host to integrate
    bool ikActive = false;
    int legLanded = -1;
    // damage
    float bodyDamage = 0.0f; // host subtracts from mHealth
    int weaponHits[P2BTWEAPON_Count] = {};
    float weaponDamage[P2BTWEAPON_Count] = {};
    int bodyHits = 0;        // accepted body hits (unarmed)
    int ignoredHits = 0;     // body hits while armed (source: ignored)
    int deadHits = 0;        // hits after deathProcedure (setAlive(false)): ignored
    bool pinchSmoke[P2BTWEAPON_Count] = {};
    // flicks: stuck Pikmin to flick (flickStickPikmin), and stuck Pikmin on a
    // part whose weapon dropped (flickStickCollPartPikmin, knockback 10, 0 dmg)
    std::vector<std::uint64_t> flick;
    float flickKnockback = 0.0f, flickDamage = 0.0f, flickAngle = 0.0f;
    const char* flickReason = nullptr;
    std::vector<std::uint64_t> partFlick;
    float partFlickAngle = 0.0f;
    // attacks
    int attackStarted = -1;  // weapon started this tick (startAttack KEYEVENT_2)
    int fireVariant = -1;    // 0 F, 1 FR, 2 FL, 3 FB (fire only)
    bool attackFinished = false;
    int attackNodes = 0;
    int attackEmits = 0;
    std::vector<ElementHit> elementHits;
    int pickedWeapon = -1;   // setTreasureAttack result this tick (PreAttack init)
    // weapons / death
    std::vector<Drop> drops;
    bool throwupItem = false;
    bool louieReleased = false;
    bool killRequest = false;
    bool attackLimit = false; // isAttackLimitTime() result, when evaluated
};

class Fsm {
public:
    // `seed` feeds the per-actor LCG.
    void init(const Params& params, const Bank& bank, const Animator& animator, const Vec3& position,
              float faceDir, std::uint32_t seed);
    TickOutput tick(const TickInput& in);

    State state() const { return mState; }
    const Animator& animator() const { return mAnim; }
    const Gait& gait() const { return mGait; }
    const P2BigTreasureOwnership& ownership() const { return mOwn; }
    const Params& params() const { return mParams; }
    int attackIndex() const { return mAttackIndex; }
    // TEST-ONLY seam (evidence runs, PIKMIN_P2_TEST_BIGTREASURE_WEAPONS): cycle the attack
    // weapon through `order` (skipping detached weapons) instead of the health-weighted pick.
    // The pick still consumes its random number, so a run stays reproducible.
    void setForcedWeaponOrder(const int* order, int count) {
        mForcedCount = count < 0 ? 0 : (count > 8 ? 8 : count);
        for (int i = 0; i < mForcedCount; ++i) mForced[i] = order[i];
        mForcedAt = 0;
    }
    float stateTimer() const { return mStateTimer; }
    float flickTimer() const { return mFlickTimer; }
    float attackLimitTimer() const { return mAttackLimitTimer; }
    const Vec3& targetPosition() const { return mTarget; }
    const Vec3& home() const { return mHome; }
    // World position of a joint at the current pose (weapons ride the
    // animated otakara_* joints).
    Vec3 jointWorld(int joint) const;
    // Current pose matrix for a joint in model space (nearest staged pose).
    const Mat34& jointModel(int joint) const;
    // World position of a point given in a joint's local frame.
    Vec3 jointPoint(int joint, const Vec3& local) const;
    // World centre of a retail collision node at the current pose/gait, for
    // the glue's CollParts: joint-0 (kosi) nodes use their offset in the kosi
    // frame, weapon parts ride their otakara_* joint, leg chain nodes
    // (lft/lht/rft/rht 2..5) lie on the hip-to-gait-foot polyline.
    Vec3 collCentre(const CollNode& node) const;
    const P2BigTreasureElementRuntime& elements() const { return mElements; }

    // Test seams.
    float randWeightFloat(float range);

private:
    // Per-joint interpolated pose matrix (jointModel): distinct storage per joint so
    // callers may hold several joints at once.
    mutable Mat34 mJointCache[JointCount];
    void transit(State next, TickOutput& out);
    void cleanup(State state, TickOutput& out);
    void initState(State state, TickOutput& out);
    void exec(TickOutput& out);
    bool isCaptured() const { return mOwn.hasAnyWeapon(); }
    bool isCaptured(int weapon) const { return weapon >= 0 && weapon < P2BTWEAPON_Count && mOwn.isWeaponAttached(weapon); }
    bool isStartFlick() const;
    bool isAttackLimitTime(TickOutput& out);
    void resetAttackLimitTimer() { mAttackLimitTimer = randWeightFloat(2.0f); }
    void getTargetPosition();
    void setTreasureAttack(TickOutput& out);
    int preAttackAnim() const;
    int attackAnim() const;
    int putItemAnim() const;
    int fireAttackAnim();
    float preAttackTimeMax() const;
    float attackTimeMax() const;
    void flickStick(TickOutput& out, const char* reason);
    void startBlend(int anim) { mAnim.start(anim); }
    void applyHits(TickOutput& out);
    void updateAttack(TickOutput& out);
    P2BigTreasureElementAim buildAim(int weapon);
    Vec3 jointAxisWorld(int joint, int column) const;
    bool poseHasJoint(int joint) const;
    void updateTreasure(TickOutput& out);
    float roundAngle(float a) const;
    float angDist(const Vec3& to) const;

    Params mParams;
    Bank mBank;
    Animator mAnim;
    Gait mGait;
    P2BigTreasureOwnership mOwn;
    P2BigTreasureElementRuntime mElements;
    State mState = State::Stay;
    State mNext = State::Null;
    float mStateTimer = 0.0f;
    float mFlickTimer = 0.0f;
    float mAttackLimitTimer = 0.0f;
    int mAttackIndex = -1;
    int mForced[8] = {};
    int mForcedCount = 0;
    int mForcedAt = 0;
    int mFireVariant = 0;
    bool mLouie = true;
    Vec3 mPos, mHome, mTarget;
    float mFaceDir = 0.0f;
    float mHealth = 0.0f;
    std::uint32_t mRng = 1;
    const TickInput* mIn = nullptr;
    int mStuck = 0;
};

} // namespace p2btown
