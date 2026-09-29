#pragma once
// Engine-free port of the Pikmin 2 Gatling Groink behaviour (MiniHoudai 78,
// NormMiniHoudai roaming; FixMiniHoudai 97 is the same FSM with no
// locomotion). Source of truth (read-only public decomp):
//   include/Game/Entities/MiniHoudai.h            StateID / AnimID / Parms
//   src/plugProjectNishimuraU/MiniHoudai.cpp      onInit, doUpdate, caution,
//       waypoints, isAttackableTarget, getSearchedTarget, damageCallBack
//   src/plugProjectNishimuraU/MiniHoudaiState.cpp the 11 FSM states
//   src/plugProjectNishimuraU/MiniHoudaiShotGun.cpp gun rotation + shells
//   src/plugProjectYamashitaU/enemyAction.cpp     EnemyFunc search/flick
//   src/plugProjectYamashitaU/enemyBase.cpp       motion flags, addDamage,
//       doSimulationGround, EnemyBase::onInit
//   src/sysGCU/sysShape.cpp                       SysShape::Animator::animate
//   include/Game/EnemyBase.h / EnemyParmsBase.h   turn helpers, defaults
//
// The FSM owns face direction, target velocity, the animation clock, the gun
// rotation and the 6-node shell pool. The host supplies one snapshot per
// 30 Hz source update (position, drained health, hit count, stuck Pikmin,
// candidate creatures, a route graph and a map trace) and executes the
// returned commands (face/velocity, flicks, shell hits, kill request). No
// engine type is referenced, so every decision is unit-testable.
//
// Adaptations kept (each is forced by the P1 host or by missing data):
//  * CellIterator queries -> the host snapshot (captains in naviMgr index
//    order, Piki in pikiMgr order, enemies), filtered by the source spheres.
//  * P2 mRouteMgr waypoints -> the P1 'test' carry-route graph; nearest is
//    RouteMgr::findNearestWayPoint (open points) instead of WPSearchArg.
//  * EB_Colliding is not reported by the host (caution resets on damage and
//    stuck Pikmin only). addDamage calls = P1 InteractAttack count; the
//    source partless damage/4 (damageCallBack) is not reproduced.
//  * doSimulationGround blends x/z only; y, gravity and map collision stay
//    with the P1 host, which integrates the returned velocity.
//  * Clip timing: attack1 is retail; the other seven clips have retail key
//    events but placeholder frame counts, and the kuti muzzle is a
//    placeholder, until the run stages p2-groink-bank.txt.
//  * randFloat/randInt/randWeightFloat use a per-actor LCG (generator seed);
//    atan2/sin/cos replace the JMAAtan2Radian and dolsin/dolcos tables.
//  * Stone/earthquake/bitter/movie hooks and all effects/sounds are not
//    ported (no P1 source); Dead KEYEVENT_2 is surfaced as `deadBomb`.
//  * A transit to MINIHOUDAI_NULL (only reachable with a looping clip that
//    lacks LOOP_END) restarts the current state instead of indexing -1.
#include "pc_p2_groink.h"
#include "pc_p2_groink_attack.h"
#include "pc_p2_groink_hit.h"
#include "pc_p2_groink_volley.h"
#include <cstddef>
#include <cstdint>
#include <istream>
#include <string>
#include <vector>

namespace p2groinkfsm {

constexpr float kPi = 3.14159265358979323846f;
constexpr float kTau = 6.28318530717958647692f;
constexpr float kQuarterPi = kPi / 4.0f;
constexpr float kSourceDelta = 1.0f / 30.0f;

// MiniHoudai.h:25-39 (ordinals are the source StateID values).
enum class State : int {
    Null = -1, Dead = 0, Rebirth = 1, Lost = 2, Attack = 3, Flick = 4, Turn = 5,
    TurnHome = 6, TurnPath = 7, Walk = 8, WalkHome = 9, WalkPath = 10,
};
const char* stateName(State state);

// MiniHoudai.h:181-191. The anim registry row order is the AnimID.
enum Anim : int {
    AnimWalk = 0, AnimSearch = 1, AnimTurn = 2, AnimAttack = 3, AnimFlick = 4,
    AnimDead = 5, AnimCarry = 6, AnimRebirth = 7, AnimCount = 8,
};
const char* animDefaultName(int anim);

// SysShape/KeyEvent.h:7-22.
enum KeyType : int {
    KeyLoopStart = 0, KeyLoopEnd = 1, Key2 = 2, Key3 = 3, Key4 = 4, Key5 = 5, KeyEnd = 1000,
};

// EnemyParmsBase general block + CreatureProps accel + MiniHoudai proper
// block. Initialisers are the SOURCE DEFAULTS (EnemyParmsBase.h:20,55-101;
// MiniHoudai.h:157-160). parseEnemyParm overwrites them with the retail
// enemyparm.txt values when the run stages that file.
struct Params {
    float accel = 0.1f;            // s003 CreatureProps accel
    float health = 100.0f;         // fp00
    float moveSpeed = 80.0f;       // fp06
    float turnSpeed = 0.1f;        // fp08 (rate per source update)
    float maxTurnAngle = 10.0f;    // fp28 (degrees per source update)
    float territoryRadius = 200.0f; // fp09
    float homeRadius = 15.0f;      // fp10
    float privateRadius = 70.0f;   // fp11
    float sightRadius = 200.0f;    // fp12
    float fov = 50.0f;             // fp25 (vertical view height)
    float viewAngle = 90.0f;       // fp13 (degrees)
    float searchDistance = 200.0f; // fp14
    float shakeChance = 1.0f;      // fp16
    float shakeKnockback = 300.0f; // fp17
    float shakeDamage = 0.0f;      // fp18
    float shakeRange = 120.0f;     // fp19
    float maxAttackAngle = 15.0f;  // fp21 (degrees)
    float attackRadius = 70.0f;    // fp22 (shell sweep radius)
    float attackHitAngle = 15.0f;  // fp23 (shell splash radius, source quirk)
    float attackDamage = 10.0f;    // fp24
    float alertDuration = 15.0f;   // fp29
    int shakeOffBlowA = 3, shakeOffSticking1 = 3, shakeOffBlowB = 8, shakeOffSticking2 = 5;
    int shakeOffBlowC = 15, shakeOffSticking3 = 10, shakeOffBlowD = 30; // ip01..ip07
    float healthGaugeTimer = 30.0f; // proper fp11 (death -> gauge)
    float respawnRate = 10.0f;      // proper fp12 (gauge -> revival)
    bool retail = false;            // true once a retail enemyparm.txt was parsed
};
// Retail `minihoudai/enemyparm.txt` (or `fminihoudai/`) text: blocks ended by
// {_eof}; `{tag} <kind> <value>` rows; '#' comments. The CreatureProps block
// (s003), the general block (has fp00 and fp14) and the proper block (fp11/fp12
// without fp00) are told apart by content, never by position. Fails closed on
// a malformed file, a missing general block or a nonphysical value.
bool parseEnemyParm(std::istream& in, Params& out, std::string& error);

struct KeyEvent { int frame = 0; int type = 0; };
struct Clip {
    std::string name;
    int frames = 0;                 // bca total frame count
    std::vector<KeyEvent> events;   // enemyanimmgr.txt rows, list order
    std::vector<int> poses;         // staged pose frames (draw only)
    bool staged = false;            // false: built-in fallback timing
};
struct Bank {
    Clip clip[AnimCount];
    // `kuti` joint basis in model space (columns), before the runtime vertical
    // aim callback (MiniHoudaiShotGun.cpp:581-624) and the owner transform.
    P2GroinkMuzzle muzzle;
    bool muzzleStaged = false;
};
// Fallback bank used when the run stages no p2-groink-bank.txt. attack1 is
// the retail GPVE01 contract recorded in engine/tools/P2_GROINK_ATTACK.md
// (44 frames; events (11,2) (22,3) (25,4) (32,5)); the other clips carry the
// retail key events but PLACEHOLDER frame counts, and the muzzle is a
// placeholder. The root stages the real bank as p2-groink-bank.txt.
Bank defaultBank();
// p2-groink-bank.txt (see the .cpp for the grammar). Clips are keyed by
// AnimID; a missing clip keeps its fallback. Fails closed on malformed rows.
bool parseBank(std::istream& in, Bank& bank, std::string& error);

// SysShape::Animator (sysShape.cpp:45-62,133-188) + the EnemyAnimatorBase
// stop flag (enemyBase.cpp:2325-2369,3132-3189) + EnemyBase::onKeyEvent's
// single latched event (enemyBase.cpp:2375-2381).
class Animator {
public:
    void start(const Clip* clip, int anim);   // EnemyBase::startMotion(id)
    void resume() { mStopped = false; }       // EnemyBase::startMotion()
    void stop() { mStopped = true; }          // EnemyBase::stopMotion()
    void finish() { mFinish = true; }         // EnemyBase::finishMotion()
    bool isStopped() const { return mStopped; }
    bool isFinishing() const { return mFinish; }
    void setSpeed(float speed) { mSpeed = speed; }
    float speed() const { return mSpeed; }
    // One source update: doAnimationCullingOff clears the latch, then
    // animate(mSpeed * dt) (0 while stopped).
    void animate(float dt);
    bool playing() const { return mPlaying; }
    int latched() const { return mType; }
    bool is(int type) const { return mPlaying && mType == type; }
    int anim() const { return mAnim; }
    float frame() const { return mTimer; }
    int frames() const { return mClip ? mClip->frames : 0; }
private:
    void trigger(int type) { mType = type; mPlaying = true; }
    std::size_t lowest(float minimum) const;
    const Clip* mClip = nullptr;
    int mAnim = -1;
    float mTimer = 0.0f;
    float mSpeed = 30.0f;
    std::size_t mKey = 0;
    bool mFinish = false, mCompleted = false, mStopped = false;
    bool mPlaying = false;
    int mType = KeyLoopStart;
};

// Opaque creature snapshot. Order is the host's manager order: every captain
// (naviMgr index order), then every Piki (pikiMgr order), then other enemies.
struct Candidate {
    std::uint64_t id = 0;
    P2GroinkVec3 pos;
    bool alive = true;
    bool navi = false;
    bool pikmin = false;
    bool teki = false;
    bool owner = false;       // the Groink itself (never hit by its shells)
    bool searchable = true;   // Piki::isSearchable
    bool stuckToSelf = false; // Piki::mSticker == this Groink
    bool stuckToMouth = false;
    float cellRadius = 0.0f;  // enemies only (shell terminal splash)
};

struct WayPointInfo {
    int index = -1;
    P2GroinkVec3 pos;
    float radius = 0.0f;
    bool open = true;
    int links[8] = {-1, -1, -1, -1, -1, -1, -1, -1};
    int linkCount = 0;
};
class Route {
public:
    virtual ~Route() {}
    virtual int nearest(const P2GroinkVec3& pos) const = 0;  // -1 when none
    virtual bool get(int index, WayPointInfo& out) const = 0;
};

struct TickInput {
    P2GroinkVec3 position;
    float health = 0.0f;       // after the host drained stored damage
    int damageHits = 0;        // addDamage calls since the last update
    bool colliding = false;    // EB_Colliding (host may leave false)
    int stuckPikmin = 0;       // mStuckPikminCount
    const Candidate* candidates = nullptr;
    std::size_t count = 0;
    const Route* route = nullptr;
    P2GroinkTraceFn trace = nullptr;
    void* traceContext = nullptr;
};

struct HitCommand {
    std::uint64_t id = 0;
    std::size_t slot = 0;
    bool primary = false;
    P2GroinkHitCommand hit;
};

struct TickOutput {
    bool valid = false;
    float faceDir = 0.0f;
    P2GroinkVec3 velocity;     // mCurrentVelocity after doSimulationGround (x/z)
    std::vector<State> entered; // states entered this update, in order
    // Flick/Rebirth KEYEVENT_2 (EnemyFunc::flick*). Angles are the literal
    // source arguments (FLICK_BACKWARD_ANGLE + PI, stick list also roundAng).
    bool flick = false;
    float flickKnockback = 0.0f, flickDamage = 0.0f;
    float flickStickAngle = 0.0f, flickNearbyAngle = 0.0f;
    std::vector<std::uint64_t> flickStick, flickPiki, flickNavi;
    // Attack KEYEVENT_4: shells actually emitted (0..3, pool of 6).
    int volley = 0;
    float volleySpeed = 0.0f, volleyAngle = 0.0f;
    P2GroinkVec3 volleyTarget;
    // emitShotGun ran (its TChibiShoot fires even when the pool is full,
    // MiniHoudaiShotGun.cpp:1385) and the kuti basis passed to emit (#892).
    bool shotFired = false;
    P2GroinkMuzzle volleyMuzzle;
    std::vector<HitCommand> hits;
    int terminals = 0;
    bool deadBomb = false;     // Dead KEYEVENT_2 (effects/sound only)
    P2GroinkMuzzle deadMuzzle; // kuti basis at deadBomb (createDeadBombEmitEffect, #892)
    bool killRequest = false;  // Dead KEYEVENT_END -> kill(nullptr)
    bool lockedOn = false;     // gun lock edge this update
};

class Fsm {
public:
    // Obj::onInit (MiniHoudai.cpp:36-56). `fixed` selects FixMiniHoudai
    // (EnemyID_FminiHoudai: zero locomotion, MiniHoudaiState.cpp:803-808).
    void init(const Params& params, const Bank& bank, bool fixed,
              const P2GroinkVec3& position, float faceDir, std::uint32_t seed,
              const Route* route);
    // One 30 Hz source update, source order: addDamage bookkeeping,
    // updateCaution, updateTargetDistance, FSM exec, doUpdateShotGun,
    // doUpdateCommonShotGun (shells + hits), doSimulationGround, animate.
    TickOutput tick(const TickInput& in);
    // doUpdateCarcass revival (MiniHoudai.cpp:313-316) enters Rebirth.
    void startRebirth(const TickInput& in);
    // Obj::onKill -> forceFinishShotGun (MiniHoudai.cpp:62-67).
    void forceFinishShotGun();

    State state() const { return mState; }
    float faceDir() const { return mFaceDir; }
    const P2GroinkVec3& home() const { return mHome; }
    const P2GroinkVec3& walkTarget() const { return mWalkTarget; }
    int nearestWayPoint() const { return mNearestWp; }
    float cautionTimer() const { return mCaution; }
    float flickTimer() const { return mFlickTimer; }
    float attackWait() const { return mAttackWait; }
    // Id of the last getSearchedTarget() result (0 = none), for logs/tests.
    std::uint64_t lastSearched() const { return mLastSearched; }
    const Animator& animator() const { return mAnim; }
    const P2GroinkGunRotation& gun() const { return mGun; }
    const P2GroinkVolley& shells() const { return mShells; }
    const Params& params() const { return mParams; }
    bool fixed() const { return mFixed; }
    // World kuti basis for the current pose (rotated while the gun rotates).
    P2GroinkMuzzle worldMuzzle(const P2GroinkVec3& position) const;

private:
    // helpers bound to the current tick
    void transit(State next);
    void execState();
    float angDistTo(const P2GroinkVec3& target) const;
    float turnToTarget(const P2GroinkVec3& target, float speed, float maxDeg);
    bool turnToTargetPos(const P2GroinkVec3& target, float speed, float maxDeg, float endDeg);
    bool isTargetOutOfRange(const Candidate& target, float angle) const;
    float viewAngle() const;
    const Candidate* searchedTarget();
    bool attackableTarget();
    bool isStartFlick(bool reset);
    void setNearestWayPoint();
    void setLinkWayPoint();
    void updateTargetDistance();
    void updateHomePosition();
    void setTargetSpeed(float speed);
    void walkVelocity();
    float homeDistSq() const;
    void stateEndDecision(bool attackEnd); // shared Attack/Flick END ladder
    void doFlick();
    float randFloat();
    int randInt(int count);

    Params mParams;
    Bank mBank;
    bool mFixed = false;
    State mState = State::Null;
    State mNext = State::Null;
    Animator mAnim;
    P2GroinkGunRotation mGun;
    P2GroinkVolley mShells;
    float mFaceDir = 0.0f;
    P2GroinkVec3 mHome, mWalkTarget, mTargetPos;
    P2GroinkVec3 mTargetVel, mCurrentVel;
    float mCaution = 128.0f;   // mHealthGaugeTimer while alive
    float mAttackWait = 0.0f;
    float mUpdateTimer = 0.0f;
    float mFlickTimer = 0.0f;
    int mNearestWp = -1, mOldNearestWp = -1;
    std::uint32_t mRng = 1;
    bool mTakingDamage = false;
    std::uint64_t mLastSearched = 0;
    // current tick
    const TickInput* mIn = nullptr;
    TickOutput* mOut = nullptr;
    P2GroinkVec3 mPos;
};

// roundAng / angDist (sysMath.cpp) as used by getAngDist.
float roundAng(float angle);
float angDist(float first, float second);

} // namespace p2groinkfsm
