#pragma once
// Engine-free port of the Pikmin 2 Breadbug behaviour (PanModoki, source 38).
// Source of truth (read-only public decomp, projectPiki/pikmin2):
//   include/Game/Entities/PanModokiBase.h   StateID / AnimID / proper Parms
//   include/Game/Entities/PanModoki.h       canTarget (weightLimit > min)
//   src/plugProjectMorimuraU/panModoki.cpp  damageCallBack (bitter only),
//       pressCallBack, bounceCallback, walkFunc, findNextRoutePoint,
//       isReachToGoal, isCarryToGoal, findNearestPellet, isTargetable,
//       canBack, carryTarget, setCarryDir, endCarry, suckFinish, checkSucked
//   src/plugProjectMorimuraU/panModokiState.cpp  the 11 FSM states
//   src/plugProjectKandoU/pelletCarry.cpp   PelletCarry pull/pullable/giveup
//   src/plugProjectYamashitaU/enemyAction.cpp  EnemyFunc::walkToTarget
//   include/Game/EnemyParmsBase.h           general parameter tags/defaults
//
// The FSM owns health, face direction, target velocity, the animation clock,
// the wander/carry waypoint bookkeeping and the cargo contest (a PelletCarry
// replica). The host supplies one snapshot per 30 Hz source update (position,
// pellets, the cargo it is stuck to, press/bounce/suck-finish events, damage
// from bombs) and executes the returned commands (stick, release, pull, move
// pellet home, consume cargo, kill). No engine type is referenced, so every
// decision is unit-testable.
//
// Damage model (the point of this port): ordinary Pikmin attacks do NOTHING
// (damageCallBack applies damage only while bittered, and the port has no
// bitter spray). Health drops only through
//   * press  (pressCallBack: a thrown Pikmin landing while falling, in
//             Walk/Wait/Stick/Back/Pulled -> Damage, fp06 press damage),
//   * suck   (the cargo is sucked into the Onion while held -> Sucked ->
//             bounceCallback on landing -> Damage, fp04 container damage),
//   * bombs  (EnemyBase::bombCallBack -> addDamage, host `externalDamage`).
// Hide refills health to fp00 and consumes the cargo (endCarry).
//
// Adaptations kept (each forced by the P1 host or missing data):
//  * P2 mRouteMgr waypoints -> the P1 'test' carry-route graph; nearest edge
//    queries use the nearest open waypoint; the async testPathfinder is the
//    host's synchronous path (`Route::path`, P1 makePositionRoute).
//  * The retail slope push (mFloorNormal in walkFunc/carryTarget) is not
//    reproduced; map collision and gravity stay with the P1 host.
//  * State transitions that happen mid-exec end that exec (the retail code
//    keeps running the old state's tail; only the waypoint bookkeeping of
//    Walk -> Stick is kept, see Walk).
//  * PelletCarry ordering: the host's Pikmin carriers pull first each update,
//    then the Breadbug (retail pull order depends on manager update order).
//  * The nest (PanHouse 83) is only the home point; no nest actor is spawned.
//    Treasure hoarding (mHeldTreasures) is not ported: every cargo is killed
//    at Hide END (P1 has no treasures, only pellets and corpses).
//  * randInt uses a per-actor LCG (generator seed).
#include <cstddef>
#include <cstdint>
#include <istream>
#include <string>
#include <vector>

namespace p2breadbugfsm {

constexpr float kPi = 3.14159265358979323846f;
constexpr float kTau = 6.28318530717958647692f;
constexpr float kSourceDelta = 1.0f / 30.0f;
constexpr float kDefaultAnimSpeed = 30.0f;  // EnemyAnimatorBase::defaultAnimSpeed
constexpr float kCarrySizeDiff = 20.0f;     // PanModokiBase::Obj() mCarrySizeDiff (small Breadbug)
constexpr float kGiantCarrySizeDiff = 40.0f; // OoPanModoki::Obj() mCarrySizeDiff (panModoki.cpp:1709)
constexpr float kWaypointSlack = 100.0f;    // walkFunc slack box (panModoki.cpp:926)
constexpr float kGiantWaypointSlack = 150.0f; // OoPanModoki (panModoki.cpp:927-929)
constexpr int kMaxHeldTreasures = 15;       // PANMODOKI_MaxHeldTreasures
constexpr int kBackStuckRelease = 8;       // #898 port watchdog: 8 x 60 ticks (16 s) wedged in Back -> release

struct Vec3 { float x = 0.0f, y = 0.0f, z = 0.0f; };

// PanModokiBase.h:29-43 (ordinals are the source StateID values).
enum class State : int {
    Null = -1, Dead = 0, Walk = 1, Back = 2, Pulled = 3, Appear = 4, Hide = 5,
    Damage = 6, Wait = 7, Stick = 8, Sucked = 9, CarryEnd = 10,
};
const char* stateName(State state);

// PanModokiBase.h:242-253 == retail panmodoki/enemyanimmgr.txt row order.
enum Anim : int {
    AnimDead = 0, AnimWalk = 1, AnimBack = 2, AnimPulled = 3, AnimAppear = 4,
    AnimHide = 5, AnimDamage = 6, AnimCarry = 7, AnimWait = 8, AnimCount = 9,
};
const char* animDefaultName(int anim);

// SysShape/KeyEvent.h.
enum KeyType : int { KeyLoopStart = 0, KeyLoopEnd = 1, Key2 = 2, Key3 = 3, KeyEnd = 1000 };

// General (EnemyParmsBase) + proper (PanModokiBase::Parms::ProperParms)
// blocks. Initialisers are the SOURCE DEFAULTS; parseEnemyParm overwrites
// them with the retail panmodoki/enemyparm.txt values.
struct Params {
    float accel = 0.1f;            // s003 CreatureProps accel
    float health = 100.0f;         // general fp00
    float moveSpeed = 80.0f;       // general fp06
    float turnSpeed = 0.1f;        // general fp08 (rate per update)
    float maxTurnAngle = 10.0f;    // general fp28 (degrees per update)
    float homeRadius = 15.0f;      // general fp10
    float searchDistance = 200.0f; // general fp14
    float searchAngle = 120.0f;    // general fp15 (degrees)
    // proper
    float nestScale = 1.0f;        // proper fp00
    float walkAnimSpeed = 1.0f;    // proper fp16
    float fastTurnSpeed = 0.1f;    // proper fp02
    float maxFastTurnAngle = 1.0f; // proper fp05 (degrees)
    float carrySpeed = 10.0f;      // proper fp03
    float suckDamage = 10.0f;      // proper fp04 (container damage)
    float pressDamage = 10.0f;     // proper fp06
    float waitTime = 20.0f;        // proper fp14 (updates)
    float hideTime = 50.0f;        // proper fp15 (updates)
    int maxCarryWeight = 5;        // proper ip01 (canTarget weight limit)
    bool retail = false;           // true once a retail enemyparm.txt was parsed
    // Variant (#958): false = PanModoki 38, true = OoPanModoki 40 (Giant
    // Breadbug). Set with applyVariant() BEFORE parseEnemyParm/init.
    bool giant = false;
    float carrySizeDiff = 20.0f;   // mCarrySizeDiff (stick radius, reach-to-goal)
    float waypointSlack = 100.0f;  // walkFunc slack box before the speed timer
};
// PanModoki vs OoPanModoki constants (canTarget, mCarrySizeDiff, walkFunc
// slack). parseEnemyParm keeps these fields.
void applyVariant(Params& params, bool giant);
// Retail `panmodoki/enemyparm.txt`: blocks ended by {_eof}; `{tag} <kind>
// <value>` rows; '#' comments. The CreatureProps block (s003), the general
// block (fp00 + fp27) and the proper block (the later block with fp16 and
// ip01 and no fp27) are told apart by content. Fails closed on a malformed
// file, a missing general block or a nonphysical value.
bool parseEnemyParm(std::istream& in, Params& out, std::string& error);

struct KeyEvent { int frame = 0; int type = 0; };
struct Clip {
    std::string name;
    int frames = 0;
    std::vector<KeyEvent> events;
    std::vector<int> poses;   // staged pose frames (draw only)
    bool staged = false;
};
struct Bank { Clip clip[AnimCount]; };
// Retail GPVE01 clip table (panmodoki/enemyanimmgr.txt + bca durations,
// recorded by the root extractor): used when no p2-breadbug-bank.txt is staged.
Bank defaultBank();
// p2-breadbug-bank.txt:
//   P2_BREADBUG_BANK_1 <clipCount>
//   clip <animId 0..8> <name> <frames> <eventCount> (<frame> <type>)* <poseCount> <poseFrame>*
//   END
bool parseBank(std::istream& in, Bank& bank, std::string& error);

// SysShape::Animator + EnemyAnimatorBase stop/finish + the single latched
// key event (same model as the Groink port, pc_p2_groink_fsm.cpp).
class Animator {
public:
    void start(const Clip* clip, int anim);
    void finish() { mFinish = true; }
    bool isFinishing() const { return mFinish; }
    void setSpeed(float speed) { mSpeed = speed; }
    float speed() const { return mSpeed; }
    void setFrame(float frame);  // EnemyBase::setMotionFrame
    void animate(float dt);
    bool is(int type) const { return mPlaying && mType == type; }
    int anim() const { return mAnim; }
    float frame() const { return mTimer; }
    int firstKeyFrame() const;   // EnemyBase::getFirstKeyFrame (first event frame)
private:
    void trigger(int type) { mType = type; mPlaying = true; }
    std::size_t lowest(float minimum) const;
    const Clip* mClip = nullptr;
    int mAnim = -1;
    float mTimer = 0.0f;
    float mSpeed = kDefaultAnimSpeed;
    std::size_t mKey = 0;
    bool mFinish = false, mCompleted = false;
    bool mPlaying = false;
    int mType = KeyLoopStart;
};

// PelletCarry (pelletCarry.cpp): shared tug-of-war state of ONE pellet.
enum CarryState : int { PcsIdle = 0xFFFF, PcsCarry = 0, PcsBreadbug = 2 };
struct PelletCarry {
    int state = PcsIdle;
    float strength = 0.0f;
    Vec3 velocity;
    float timer = 0.0f;
    void reset() { *this = PelletCarry(); }
    bool pull(int who, const Vec3& vel, float amount);
    bool pullable(int who, float amount) const;
    void giveup(int who);
};

// One pellet seen by the host (P1 pelletMgr). `id` is opaque, never 0.
struct PelletInfo {
    std::uint64_t id = 0;
    Vec3 pos;
    float bottomY = 0.0f;        // pos.y - 0.5 * cylinder height (findNearestPellet)
    float radius = 0.0f;         // config/stick radius (isReachToGoal, StateStick)
    int carryMin = 1, carryMax = 1;
    float pikiStrength = 0.0f;   // total carry strength of Piki stuck to it
    bool alive = true;
    bool pickable = true;        // not in the Onion goal, not a UFO part, not a captain
    bool captured = false;       // mCaptureMatrix (held in a mouth)
    bool otherTekiStuck = false; // another enemy is stuck to it
    bool carcass = false;        // an enemy corpse
    bool inGoal = false;         // PELSTATE_Goal (being sucked)
    bool slotFree = true;        // isSlotFree(9999)
    Vec3 velocity;
};

struct WayPointInfo {
    int index = -1;
    Vec3 pos;
    bool open = true;
    int links[8] = {-1, -1, -1, -1, -1, -1, -1, -1};
    int linkCount = 0;
};
class Route {
public:
    virtual ~Route() {}
    virtual int nearest(const Vec3& pos) const = 0;               // -1 when none
    virtual bool get(int index, WayPointInfo& out) const = 0;
    // Synchronous testPathfinder: waypoint indices from `from` to `to` inclusive.
    virtual bool path(int from, int to, std::vector<int>& out) const = 0;
    // #898 fix: the carry-route edge nearest `pos` (both ends). The source
    // pathfinder starts from the nearest EDGE (panModoki.cpp findNextRoutePoint
    // "nearest edge -> nearest open waypoint"); the nearest waypoint alone
    // can sit behind a wall. Default: no edge query (nearest waypoint only).
    virtual bool nearestEdge(const Vec3&, int& a, int& b) const { (void)a; (void)b; return false; }
};

struct TickInput {
    Vec3 position;
    float externalDamage = 0.0f; // bombs / other addDamage since last update
    int presses = 0;             // thrown Pikmin landed on it while falling
    bool bounced = false;        // bounceCallback (landed on the map)
    bool suckFinished = false;   // InteractSuckFinish for the held cargo
    std::uint64_t held = 0;      // pellet the host reports it is stuck to (0 = none)
    const PelletInfo* pellets = nullptr;
    std::size_t count = 0;
    const Route* route = nullptr;
};

enum class DamageKind : int { None = 0, Press = 1, Suck = 2, External = 3 };

struct TickOutput {
    bool valid = false;
    float faceDir = 0.0f;
    Vec3 velocity;               // mCurrentVelocity (x/z) for an unstuck Breadbug
    std::vector<State> entered;
    // Commands for the host.
    std::uint64_t stickTo = 0;   // StateStick: startStick(target) + startPick
    bool release = false;        // endStick + giveup
    bool releaseReverse = false; // releaseCarryTarget from Back: negate pellet x/z velocity
    bool backStuckSkip = false;  // #898: Back made no progress; skipped to the next route node
    bool backStuckRelease = false; // #898: Back wedged too long; cargo released (Wait)
    bool stopCargo = false;      // Back init: pellet velocity 0
    bool pulled = false;         // PelletCarry::pull succeeded this update
    Vec3 pullVelocity;           //  ... with this pellet velocity
    float pullStrength = 0.0f;
    bool holdCargo = false;      // CarryEnd/Hide: the cargo stays in the mouth
    Vec3 homeNudge;              // CarryEnd forceMovePosition delta (applied to Breadbug+cargo)
    bool consumeCargo = false;   // Hide END -> endCarry (kill stuck Pikmin, kill cargo)
    bool killRequest = false;    // Dead KEYEVENT_END -> kill()
    bool hidden = false;         // underground after Hide END until Appear
    bool pressRejected = false;  // a press arrived in a state pressCallBack ignores
    // Damage applied this update (for markers).
    DamageKind damageKind = DamageKind::None;
    float hpBefore = 0.0f, hpAfter = 0.0f;
    bool refilled = false;       // Hide END health = fp00
    // Contest snapshot while holding cargo.
    bool contest = false;
    float contestPiki = 0.0f, contestSelf = 0.0f;
    bool canBack = false;
};

class Fsm {
public:
    // Obj::onInit (panModoki.cpp:81-121): starts in Appear at `home`.
    void init(const Params& params, const Bank& bank, const Vec3& home, float faceDir,
              std::uint32_t seed, const Route* route);
    TickOutput tick(const TickInput& in);

    State state() const { return mState; }
    float health() const { return mHealth; }
    float faceDir() const { return mFaceDir; }
    const Vec3& home() const { return mHome; }
    std::uint64_t target() const { return mTarget; }
    const Animator& animator() const { return mAnim; }
    const Params& params() const { return mParams; }
    float carryStrength() const { return mCarryStrength; }
    const PelletCarry& contest() const { return mCarry; }
    const Vec3& nextWayPoint() const { return mNextWp; }
    bool pathfinding() const { return mPathfinding; }  // #898 haul diagnostics
    std::size_t pathLength() const { return mPath.size(); }
    // damageCallBack (panModoki.cpp:450-456): an ordinary attack is refused
    // unless bittered. The port never bitters, so this is always false and
    // no health changes; the host logs OWN_ATTACK_IGNORED.
    bool damageCallBack(float damage) const { (void)damage; return false; }

private:
    void transit(State next);
    void execState();
    const PelletInfo* find(std::uint64_t id) const;
    const PelletInfo* cargo() const { return find(mTarget); }
    float angDistTo(const Vec3& t) const;
    float turnToTarget(const Vec3& target, float speed, float maxDeg);
    void walkToTarget(const Vec3& target, float speed, float turn, float maxDeg);
    void setTargetSpeed(float speed);
    bool pressCallBack();
    void walkFunc();
    void findNextRoutePoint(bool stuck);
    bool isReachToGoal(float radius);
    bool isCarryToGoal();
    bool canBack() const;
    bool isCarryHomeDirect() const;
    bool isTargetable(const PelletInfo& p) const;
    bool canTarget(int pelMinWeight) const;
    const PelletInfo* findNearestPellet() const;
    void releaseCarryTarget();
    void checkNearHomeGraphIndex();
    void carryTarget(float scale);
    void setCarryDir(bool direct);
    void changeCarryDir(bool direct);
    void setPathFinder();
    void addDamage(float damage, DamageKind kind);
    void endStickCargo();
    int randInt(int count);

    Params mParams;
    Bank mBank;
    State mState = State::Null;
    State mNext = State::Null;
    Animator mAnim;
    float mHealth = 0.0f;
    float mFaceDir = 0.0f, mCarryDir = 0.0f;
    float mAlsoRotationOffset = 0.0f;
    Vec3 mHome, mPos, mNextWp, mPrevCheck, mTargetVel, mCurrentVel, mStartPos;
    std::uint64_t mTarget = 0;   // mTargetCreature (the cargo pellet)
    bool mStuck = false;         // isStickTo(cargo)
    float mCarryStrength = 0.0f;
    PelletCarry mCarry;          // PelletCarry of the held cargo
    std::uint64_t mCarryPellet = 0;
    int mWp1 = -1, mWp2 = -1, mWp3 = -1;
    std::vector<int> mPath;      // pathfinder nodes (mPathNode list)
    bool mPathfinding = false;
    bool mCanReactToPress = false;
    bool mNoInterrupt = false;   // checkSucked EB_NoInterrupt
    bool mConstrained = false;   // hardConstraintOn
    bool mHidden = false;
    int mFindNextRouteCounter = 0;
    int mMoveToWpTimer = 0, mMoveSpeedTimer = 0;
    int mStateTimer = 0;         // StateWait/Hide/Stick timers
    int mBackTimer = 0, mBackStuck = 0;  // #898 Back progress watchdog
    Vec3 mBackCheck;
    std::uint32_t mRng = 1;
    // current tick
    const TickInput* mIn = nullptr;
    TickOutput* mOut = nullptr;
};

// #898 fix: PanModokiBase::isLivingThing() (PanModokiBase.h:93) is true only
// while bittered. Pikmin/captain target selection skips a non-living teki, so
// an unbittered live Breadbug is never an attack target. The port has no
// bitter spray (always unbittered), but the rule keeps the source shape.
inline bool isLivingThing(bool bittered, bool alive) { return bittered && alive; }

// #898 fix: randomizer policy for the CarryEnd/Hide cargo consume. Retail
// endCarry destroys whatever the Breadbug dragged home. In the port a teki
// CARCASS is never destroyed: it is released at the nest, stays carriable, and
// the Breadbug that spared it never picks it again. Reasons: (1) a carcass may
// owe a randomizer delivery check (onion:p2:<source> on its own generator
// token), which a Breadbug must never forfeit; (2) the only teardown the
// port's corpse pipeline (PelletView, P2 forget hooks, receipt bookkeeping)
// has been validated through is the Onion suck, not InteractKill. Plain
// pellets are eaten as in retail (the P1 Collec putting recipe). The Pikmin
// still hanging on are killed either way (retail endCarry).
enum class ConsumeOutcome { Destroy, SpareCarcass };
inline ConsumeOutcome consumeOutcome(bool carcass) {
    return carcass ? ConsumeOutcome::SpareCarcass : ConsumeOutcome::Destroy;
}

float roundAng(float angle);
float angDist(float first, float second);

} // namespace p2breadbugfsm
