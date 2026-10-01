#pragma once

// Engine-free, source-faithful Careening Dirigibug (BombSarai, EnemyID 58)
// OWN state machine for the campaign port (#244).
//
// Source (projectPiki/pikmin2 632af93787b9c95b63f0c13be32b161375ce3a96):
//   src/plugProjectNishimuraU/BombSarai.cpp       Obj helpers
//   src/plugProjectNishimuraU/BombSaraiState.cpp  13-state FSM
//   include/Game/Entities/BombSarai.h             parms, AnimID order
//   src/plugProjectYamashitaU/enemyAction.cpp     walkToTarget / getNearest*
//   src/plugProjectYamashitaU/enemyBase.cpp       collisionMapAndPlat:
//       !EB_Untargetable -> doSimulationGround, else doSimulationFlying.
//
// The machine owns: state + timers, the ProperAnimator clock (retail clip
// frame counts and enemyanimmgr key events from the staged bank, the same
// SysShape::Animator semantics as pc_p2_groink_fsm), hover vertical control
// (setHeightVelocity / addPitchRatio), getNextStateOnHeight (flick chance
// lerp fp31 -> fp32 by clamp(stuck-1, 0, 4) / 4), getAttackablePikmin,
// setRandTarget, walkToTarget/turnToTarget and the doSimulation velocity
// blend. The host owns the P1 vehicle (position integration, map collision,
// gravity while not Untargetable), the stuck-Pikmin census, the bomb payload,
// the flick receivers and the death funnel.
//
// Untargetable (EB_Untargetable) is reported as `flying`: the host maps it to
// P1 CF_IsFlying, which is exactly what makes free Pikmin ignore the carrier
// (piki.cpp graspSituation / aiAttack findTarget skip isFlying()) while thrown
// Pikmin can still latch on, the P2 engagement rule for this species.

#include <cstdint>
#include <istream>
#include <string>
#include <vector>

namespace p2bsown {

constexpr float kPi = 3.14159265358979323846f;
constexpr float kTau = 2.0f * kPi;
constexpr float kSourceDelta = 1.0f / 30.0f;

enum class State : int {
    Null = -1,
    Dead = 0, Damage = 1, Wait = 2, BombWait = 3, Move = 4, BombMove = 5,
    Supply = 6, Release = 7, Fall = 8, TakeOff1 = 9, TakeOff2 = 10,
    Flick = 11, BombFlick = 12
};
const char* stateName(State state);

// BombSarai.h:161-177 AnimID order == retail bombsarai/enemyanimmgr.txt rows.
enum Anim : int {
    AnimDead = 0, AnimFall = 1, AnimFlick = 2, AnimBombFlick = 3, AnimStruggle = 4,
    AnimRelease = 5, AnimRun = 6, AnimBombRun = 7, AnimSupply = 8, AnimTakeOff1 = 9,
    AnimTakeOff2 = 10, AnimCarry = 11, AnimWait = 12, AnimBombWait = 13, AnimCount = 14
};
const char* animDefaultName(int anim);

// SysShape/KeyEvent.h: loop markers and numbered events; END is synthetic.
enum KeyType : int {
    KeyLoopStart = 0, KeyLoopEnd = 1, Key2 = 2, Key3 = 3, Key4 = 4, Key5 = 5,
    Key6 = 6, Key7 = 7, Key8 = 8, KeyEnd = 1000
};

// Retail values (bombsarai/enemyparm.txt, US GPVE01 rev 0) are the defaults so
// a missing staged file still runs the retail machine; parseEnemyParm replaces
// them from the verbatim staged file.
struct Params {
    // CreatureProps
    float accel = 0.1f;            // s003
    // EnemyParmsBase general
    float health = 1500.0f;        // fp00
    float regenRate = 0.0f;        // fp31 (general)
    float moveSpeed = 60.0f;       // fp06
    float turnSpeed = 0.1f;        // fp08
    float maxTurnAngle = 2.0f;     // fp28 (degrees)
    float territoryRadius = 200.0f; // fp09
    float homeRadius = 100.0f;     // fp10
    float sightRadius = 200.0f;    // fp12
    float viewAngle = 180.0f;      // fp13
    float shakeChance = 1.0f;      // fp16
    float shakeKnockback = 80.0f;  // fp17
    float shakeDamage = 1.0f;      // fp18
    float maxAttackRange = 100.0f; // fp20
    float maxAttackAngle = 45.0f;  // fp21
    float attackRadius = 50.0f;    // fp22
    float attackDamage = 10.0f;    // fp24
    // BombSarai proper (BombSarai.h:121-146)
    float flightHeight = 70.0f;    // fp01 (header 90, disc 70)
    float transitHeight = 50.0f;   // fp03
    float pitchRate = 2.5f;        // fp10
    float pitchAmp = 20.0f;        // fp11
    float freeRise = 1.5f;         // fp21
    float ladenRise = 1.0f;        // fp22
    float freeFlick = 0.2f;        // fp31 (header 0.1, disc 0.2)
    float ladenFlick = 0.8f;       // fp32 (header 0.7, disc 0.8)
    float struggleTime = 0.8f;     // fp40 (header 3.0, disc 0.8)
    bool retail = false;           // parsed from a staged file
};
// Verbatim enemyparm.txt: `{tag} <kind> <value>` rows, `{_eof}` block ends,
// '#' comments. The creature block holds s003, the general block fp00+fp14,
// the proper block (first later block) fp01+fp40. Fails closed.
bool parseEnemyParm(std::istream& in, Params& out, std::string& error);

// Bomb payload parms (bomb/enemyparm.txt): general fp00 fuse life, fp22
// blast radius, fp24 Navi/Pikmin damage; proper fp01 Teki damage, fp02 blast
// half-height, ip02 induction limit.
struct BombParams {
    float fuseHealth = 4.5f;
    float blastRadius = 90.0f;
    float naviPikiDamage = 10.0f;
    float tekiDamage = 500.0f;
    float blastHalfHeight = 50.0f;
    int inductionLimit = 15;
    bool retail = false;
};
bool parseBombParm(std::istream& in, BombParams& out, std::string& error);

struct Vec3 {
    float x = 0.0f, y = 0.0f, z = 0.0f;
};
struct KeyEvent { int frame = 0; int type = 0; };
struct Pose { int frame = 0; int file = 0; Vec3 kamu; };
struct Clip {
    std::string name;
    int frames = 0;                // retail bca frame count
    std::vector<KeyEvent> events;  // enemyanimmgr.txt rows, list order
    std::vector<Pose> poses;       // staged pose frames (draw + kamu_jnt1)
    bool staged = false;
};
struct BombClip {
    std::string name;
    int frames = 0;
    std::vector<int> poseFrames;
    std::vector<int> poseFiles;
};
struct Bank {
    Clip clip[AnimCount];
    BombClip bombClip[2];          // [0] hit_start, [1] hit_loop
    int bombClipCount = 0;
    bool staged = false;
};
// Fallback: retail enemyanimmgr key events and retail bca frame counts
// (recorded from the GPVE01 extraction), no poses.
Bank defaultBank();
// Grammar (whitespace separated):
//   P2_BOMBSARAI_OWN_BANK_1 <clipCount>
//   clip <animId 0..13> <name> <frames> <eventCount> (<frame> <type>)*
//        <poseCount> (<poseFrame> <fileIndex> <kx> <ky> <kz>)*
//   bomb <name> <frames> <poseCount> (<poseFrame> <fileIndex>)*    (0..2 rows)
//   END
bool parseBank(std::istream& in, Bank& bank, std::string& error);

// SysShape::Animator + EnemyAnimatorBase finish flag + the single latched key
// event (identical semantics to p2groinkfsm::Animator).
class Animator {
public:
    void start(const Clip* clip, int anim);
    void finish() { mFinish = true; }
    bool isFinishing() const { return mFinish; }
    void animate(float dt);
    bool is(int type) const { return mPlaying && mType == type; }
    int anim() const { return mAnim; }
    float frame() const { return mTimer; }
private:
    std::size_t lowest(float minimum) const;
    void trigger(int type) { mType = type; mPlaying = true; }
    const Clip* mClip = nullptr;
    int mAnim = -1;
    float mTimer = 0.0f;
    std::size_t mKey = 0;
    bool mFinish = false, mCompleted = false, mPlaying = false;
    int mType = KeyLoopStart;
};

struct Candidate {
    std::uint64_t id = 0;
    Vec3 pos;
    bool navi = false;
    bool pikmin = false;
    bool alive = false;
    bool searchable = false;  // Piki::isSearchable (alive, above ground, not in a mouth)
    bool stuckToSelf = false; // Stickers(this)
    bool stuckToMouth = false;
};

struct TickInput {
    Vec3 position;
    float groundY = 0.0f;       // mapMgr->getMinY(mPosition)
    float health = 0.0f;
    int stuckPikmin = 0;        // mStuckPikminCount
    int stuckPurple = 0;        // getStickPikminColorNum(this, Purple)
    bool carrying = false;      // mHeldBomb != nullptr
    bool bitterQueued = false;  // EB_BitterQueued (no P1 spray: always false)
    bool inCave = false;        // gameSystem->mIsInCave
    const Candidate* candidates = nullptr;
    std::size_t count = 0;
};

struct TickOutput {
    bool valid = false;
    std::vector<State> entered;
    Vec3 velocity;              // mCurrentVelocity after doSimulation*
    bool flying = false;        // EB_Untargetable after this tick
    float faceDir = 0.0f;
    float height = 0.0f;        // last setHeightVelocity return (-1 when not sampled)
    bool supply = false;        // StateSupply::init supplyBomb()
    bool throwBomb = false;     // throwBomb(vel)
    Vec3 throwVelocity;
    int throwKind = 0;          // 0 Release, 1 Fall
    bool flick = false;         // Flick/BombFlick KEYEVENT_2
    std::vector<std::uint64_t> flickStick;
    float flickKnockback = 0.0f, flickDamage = 0.0f, flickAngle = 0.0f;
    bool killRequest = false;   // StateDead KEYEVENT_END -> kill()
    bool flickRolled = false;   // getNextStateOnHeight rolled the flick chance
    float flickChance = 0.0f;
    float flickRoll = 0.0f;
    int balloon = -1;           // createBalloonEffect index this tick
    bool down = false;          // createDownEffect this tick
};

class Fsm {
public:
    void init(const Params& params, const Bank& bank, const Vec3& position, float faceDir,
              std::uint32_t seed);
    TickOutput tick(const TickInput& in);

    State state() const { return mState; }
    const Animator& animator() const { return mAnim; }
    const Params& params() const { return mParams; }
    const Vec3& home() const { return mHome; }
    const Vec3& target() const { return mTargetPos; }
    float pitchRatio() const { return mPitchRatio; }
    float stateTimer() const { return mStateTimer; }
    float carryTimer() const { return mBombCarryTimer; }
    bool flying() const { return mUntargetable; }

    // getNextStateOnHeight flick chance (BombSarai.cpp:326-330), exposed for tests.
    static float flickChance(const Params& p, int stuck);

private:
    float randFloat();
    float angDistTo(const Vec3& t) const;
    void turnToTarget(const Vec3& t, float factor, float maxDeg);
    void walkToTarget(const Vec3& t);
    float setHeightVelocity(bool fast);
    void setRandTarget();
    const Candidate* attackablePikmin() const;
    bool targetAttackable(const Candidate& c) const;
    State nextStateOnHeight();
    void transit(State next);
    void doFlick();
    void execState();

    Params mParams;
    Bank mBank;
    Animator mAnim;
    State mState = State::Null;
    State mNext = State::Null;
    Vec3 mPos, mHome, mTargetPos;
    Vec3 mTargetVel, mCurrentVel;
    float mFaceDir = 0.0f;
    float mStateTimer = 0.0f;
    float mBombCarryTimer = 0.0f;
    float mPitchRatio = 0.0f;
    float mFlickTimer = 0.0f;
    bool mUntargetable = false;
    float mLastHeight = -1.0f;
    std::uint32_t mRng = 1;
    const TickInput* mIn = nullptr;
    TickOutput* mOut = nullptr;
};

// Nearest staged pose (by frame) of the current clip; nullptr when unstaged.
const Pose* nearestPose(const Clip& clip, float frame);

} // namespace p2bsown
