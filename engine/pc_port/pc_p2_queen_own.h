#pragma once
// Engine-free port of the Pikmin 2 Empress Bulblax (Queen, enemy 30) and its
// Bulborb Larva (Baby, enemy 31) behaviour for the campaign OWN binding
// (#256). Source of truth (read-only public decomp, pikmin2-research):
//   include/Game/Entities/Queen.h              StateID / AnimID / proper parms
//   src/plugProjectNishimuraU/Queen.cpp        onInit, damageCallBack,
//       ignoreAtari, rollingAttack, flickPikmin, isRollingAttackLeft,
//       createBabyChappy, updateCreateBaby, isCreateBaby, isHitCounterUp
//   src/plugProjectNishimuraU/QueenState.cpp   the 7 FSM states
//       (StateRolling::cleanup from asm/QueenState.s: resets mFlickTimer,
//       mPrevHitNum and mIsRolling)
//   src/plugProjectNishimuraU/Baby.cpp/BabyState.cpp  larva FSM
//   src/plugProjectYamashitaU/enemyAction.cpp  EnemyFunc::isStartFlick
//   src/plugProjectYamashitaU/enemyBase.cpp    addDamage (mFlickTimer += 1)
//   src/sysGCU/sysShape.cpp                    SysShape::Animator::animate
//
// The FSM owns state, the animation clock, the timers and the target
// velocity. The host (pc_p2_queen_teki.cpp) supplies one snapshot per 30 Hz
// source update (engine health, the number of Pikmin hits delivered through
// the damage seam, the real stuck-Pikmin count, the live larva count) and
// executes the returned commands (flick, rolling press, larva birth, kill).
// No engine type is referenced, so every decision is unit-testable.
//
// Adaptations (each forced by the P1 host or missing data):
//  * mStuckPikminCount -> P1 Pikmin whose getStickObject() is the host.
//  * damageCallBack -> the BTeki::interact seam (Pikmin only; x0.1 Sleep,
//    x0.2 Flick; captains ignored); each accepted Pikmin hit is one
//    addDamage(dmg, 1.0) i.e. mFlickTimer += 1.
//  * flickPikmin's stuck CollPart ids (nose/head/bod1/bod5) do not exist on
//    the P1 host; the host classifies each stuck Pikmin by its position along
//    the body axis instead (see pc_p2_queen_teki.cpp flickStuck).
//  * randWeightFloat uses a per-actor LCG seeded from the generator token.
//  * Velocity: mTargetVelocity is applied directly (no accel blend); the P1
//    host integrates it against its own map collision.
//  * Effects, sounds, BGM, camera vibration/rumble are logged, not played.
//  * HoH crash rocks (cave l_02 only) are never created in P1 (no cave).
#include <cmath>
#include <cstdint>
#include <istream>
#include <sstream>
#include <string>
#include <vector>

namespace p2queenown {

constexpr float kPi = 3.14159265358979323846f;
constexpr float kHalfPi = kPi * 0.5f;
constexpr float kSourceDelta = 1.0f / 30.0f;
constexpr float kBlockWindow = 0.5f;    // port: no-progress window (s)
constexpr float kBlockFraction = 0.25f; // port: blocked below this fraction of commanded travel

// Queen.h:26-34.
enum State : int { Null = -1, Dead = 0, Sleep = 1, Wait = 2, Damage = 3, Flick = 4, Rolling = 5, Born = 6 };
inline const char* stateName(int s) {
    switch (s) {
    case Dead: return "Dead";
    case Sleep: return "Sleep";
    case Wait: return "Wait";
    case Damage: return "Damage";
    case Flick: return "Flick";
    case Rolling: return "Rolling";
    case Born: return "Born";
    }
    return "Null";
}
// Queen.h:199-209 (registry order == AnimID).
enum Anim : int {
    AnimDead = 0, AnimSleep = 1, AnimWait = 2, AnimDamage = 3, AnimFlick = 4,
    AnimRollingL = 5, AnimRollingR = 6, AnimBorn = 7, AnimCarry = 8, AnimCount = 9,
};
inline const char* animName(int a) {
    static const char* names[AnimCount] = {"dead", "sleep", "wait1", "damage", "flick",
                                           "rolling_l", "rolling_r", "born", "carry"};
    return a >= 0 && a < AnimCount ? names[a] : "wait1";
}
// Baby.h state/anim ids (BabyState.cpp FSM::init order; Baby.h AnimID).
enum BabyState : int { BabyDead = 0, BabyPress = 1, BabyBorn = 2, BabyMove = 3, BabyAttack = 4 };
enum BabyAnim : int { BabyAnimDead = 0, BabyAnimDeadPress = 1, BabyAnimMove = 2, BabyAnimAttack = 3,
                      BabyAnimAttackFail = 4, BabyAnimBorn = 5, BabyAnimCount = 6 };
inline const char* babyAnimName(int a) {
    static const char* names[BabyAnimCount] = {"dead", "deadpress", "move", "attack", "attackfail", "born"};
    return a >= 0 && a < BabyAnimCount ? names[a] : "move";
}
inline const char* babyStateName(int s) {
    switch (s) {
    case BabyDead: return "Dead";
    case BabyPress: return "Press";
    case BabyBorn: return "Born";
    case BabyMove: return "Move";
    case BabyAttack: return "Attack";
    }
    return "Null";
}

// SysShape/KeyEvent.h.
enum KeyType : int { KeyLoopStart = 0, KeyLoopEnd = 1, Key2 = 2, Key3 = 3, KeyEnd = 1000 };

struct KeyEvent { int frame = 0; int type = 0; };
struct Clip {
    std::string name;
    int frames = 0;
    std::vector<KeyEvent> events;
    std::vector<int> poses; // staged pose frames (draw only)
    bool staged = false;
};

// Disc parameters (queen/enemyparm.txt general + QueenParms proper; the root
// extractor validates each against DISC_PARMS and stages them as `parm` rows).
struct Params {
    float health = 5000.0f;          // general fp00
    float moveSpeed = 125.0f;        // general fp06
    float territoryRadius = 200.0f;  // general fp09
    float homeRadius = 25.0f;        // general fp10
    float searchDistance = 50.0f;    // general fp14 (larva launch speed, createBabyChappy)
    float shakeKnockback = 300.0f;   // general fp17
    float shakeDamage = 1.0f;        // general fp18
    float attackRadius = 150.0f;     // general fp22 (rollingAttack forward)
    float attackHitAngle = 25.0f;    // general fp23 (rollingAttack lateral, units)
    float attackDamage = 10.0f;      // general fp24 (InteractPress damage)
    int shakeOffBlowA = 30, shakeOffSticking1 = 5, shakeOffBlowB = 35, shakeOffSticking2 = 10;
    int shakeOffBlowC = 45, shakeOffSticking3 = 15, shakeOffBlowD = 50; // general ip01..ip07
    float rollingTime = 3.5f;        // proper fp01
    float birthInterval = 2.0f;      // proper fp02
    float hobHealth = 3300.0f;       // proper fp11
    int maxBirths = 50;              // proper ip01
    int minBirths = 25;              // proper ip02
    // Baby (baby/enemyparm.txt general)
    float babyHealth = 5.0f;         // fp00
    float babyMoveSpeed = 40.0f;     // fp06
    float babySightRadius = 800.0f;  // fp12
    float babyViewAngle = 180.0f;    // fp13 (degrees)
    float babyTurnSpeed = 0.1f;      // fp08
    float babyMaxTurnAngle = 10.0f;  // fp28 (degrees)
    float babyMaxAttackRange = 30.0f; // fp20
    float babyMaxAttackAngle = 45.0f; // fp21 (degrees)
    float babyAttackRadius = 30.0f;  // fp22 not staged by the #235 audit: = fp20 (approximation)
    float babyAttackHitAngle = 45.0f; // fp23 not staged: = fp21 (approximation, degrees)
    float babyAttackDamage = 2.0f;   // fp24
    // Carcass draw fallback staged by the root (pikmin2_queen_stage): the
    // baked carry poses collapse to a point, so the carcass draws this dead pose.
    int carcassCarryDegenerate = 0;
    int carcassDeadPose = -1;
    bool retail = false;             // true once staged parm rows were read
};

struct Bank {
    Clip clip[AnimCount];
    Clip baby[BabyAnimCount];
};

// Disc clip registry (queen/enemyanimmgr.txt; the root extractor asserts the
// same rows via pikmin2_bulblax_assets.EXPECTED_EVENTS). Frame counts are the
// bca totals recorded in pikmin2_bulblax_behavior.QUEEN_CLIPS.
inline Bank defaultBank() {
    Bank b;
    auto set = [](Clip& c, const char* n, int frames, std::initializer_list<KeyEvent> ev) {
        c.name = n;
        c.frames = frames;
        c.events.assign(ev.begin(), ev.end());
    };
    set(b.clip[AnimDead], "dead", 140, {{60, 2}, {73, 2}, {86, 2}, {99, 2}});
    set(b.clip[AnimSleep], "sleep", 210, {{59, 0}, {118, 1}, {120, 2}});
    set(b.clip[AnimWait], "wait1", 30, {{0, 0}, {29, 1}});
    set(b.clip[AnimDamage], "damage", 50, {{10, 0}, {29, 1}});
    set(b.clip[AnimFlick], "flick", 60, {{40, 2}});
    set(b.clip[AnimRollingL], "rolling_l", 110, {{20, 0}, {67, 2}, {69, 1}});
    set(b.clip[AnimRollingR], "rolling_r", 110, {{20, 0}, {67, 2}, {69, 1}});
    set(b.clip[AnimBorn], "born", 28, {{24, 2}});
    set(b.clip[AnimCarry], "carry", 40, {{10, 0}, {29, 1}});
    // Baby (baby/enemyanimmgr.txt, pikmin2_bulblax_behavior.BABY_CLIPS).
    set(b.baby[BabyAnimDead], "dead", 100, {});
    set(b.baby[BabyAnimDeadPress], "deadpress", 80, {});
    set(b.baby[BabyAnimMove], "move", 12, {{0, 0}, {11, 1}});
    set(b.baby[BabyAnimAttack], "attack", 70, {{10, 2}, {30, 3}});
    set(b.baby[BabyAnimAttackFail], "attackfail", 20, {});
    set(b.baby[BabyAnimBorn], "born", 35, {{7, 0}, {8, 1}});
    return b;
}

// p2-queen-bank.txt grammar (whitespace separated, '#' comments to end of
// line), written by the root stage (experimental/pikmin2_queen_stage.py):
//   P2_QUEEN_BANK_1
//   parm <name> <value>                               (optional, repeated)
//   clip <queen|baby> <name> <frames> <nEvents> {<frame> <type>}* <nPoses> {<frame>}*
//   end
// Unknown clip names, out-of-range frames, non-increasing pose frames or a
// missing `end` fail closed (the caller keeps the built-in bank).
// Dense pose bank bound (#972): pikmin2_animation.DEFAULT_POSE_LIMIT, the same
// per-clip cap the other P2 pose banks use. Was 16 (the staged bank was 12).
constexpr int kMaxPosesPerClip = 24;
inline bool parseBank(std::istream& in, Bank& bank, Params& params, std::string& error) {
    std::stringstream clean;
    std::string line;
    while (std::getline(in, line)) {
        const auto hash = line.find('#');
        if (hash != std::string::npos) line.erase(hash);
        clean << line << '\n';
    }
    std::string magic, tok;
    if (!(clean >> magic) || magic != "P2_QUEEN_BANK_1") { error = "magic"; return false; }
    bool ended = false;
    int parms = 0;
    while (clean >> tok) {
        if (tok == "end") { ended = true; break; }
        if (tok == "parm") {
            std::string name;
            float v;
            if (!(clean >> name >> v) || !std::isfinite(v)) { error = "parm"; return false; }
            struct F { const char* n; float* p; };
            struct I { const char* n; int* p; };
            const F fs[] = {{"health", &params.health}, {"move_speed", &params.moveSpeed},
                            {"territory_radius", &params.territoryRadius}, {"home_radius", &params.homeRadius},
                            {"search_distance", &params.searchDistance}, {"shake_knockback", &params.shakeKnockback},
                            {"shake_damage", &params.shakeDamage}, {"attack_radius", &params.attackRadius},
                            {"attack_hit_angle", &params.attackHitAngle}, {"attack_damage", &params.attackDamage},
                            {"rolling_time", &params.rollingTime}, {"birth_interval", &params.birthInterval},
                            {"hob_health", &params.hobHealth}, {"baby_health", &params.babyHealth},
                            {"baby_move_speed", &params.babyMoveSpeed}, {"baby_sight_radius", &params.babySightRadius},
                            {"baby_view_angle", &params.babyViewAngle}, {"baby_turn_speed", &params.babyTurnSpeed},
                            {"baby_max_turn_angle", &params.babyMaxTurnAngle},
                            {"baby_max_attack_range", &params.babyMaxAttackRange},
                            {"baby_max_attack_angle", &params.babyMaxAttackAngle},
                            {"baby_attack_radius", &params.babyAttackRadius},
                            {"baby_attack_hit_angle", &params.babyAttackHitAngle},
                            {"baby_attack_damage", &params.babyAttackDamage}};
            const I is[] = {{"shake_off_blow_a", &params.shakeOffBlowA}, {"shake_off_sticking_1", &params.shakeOffSticking1},
                            {"shake_off_blow_b", &params.shakeOffBlowB}, {"shake_off_sticking_2", &params.shakeOffSticking2},
                            {"shake_off_blow_c", &params.shakeOffBlowC}, {"shake_off_sticking_3", &params.shakeOffSticking3},
                            {"shake_off_blow_d", &params.shakeOffBlowD}, {"max_births", &params.maxBirths},
                            {"min_births", &params.minBirths},
                            {"carcass_carry_degenerate", &params.carcassCarryDegenerate},
                            {"carcass_dead_pose", &params.carcassDeadPose}};
            bool known = false;
            for (const auto& f : fs) if (name == f.n) { *f.p = v; known = true; }
            for (const auto& i : is) if (name == i.n) { *i.p = int(v); known = true; }
            if (!known) { error = "parm_name:" + name; return false; }
            ++parms;
            continue;
        }
        if (tok != "clip") { error = "token:" + tok; return false; }
        std::string who, name;
        int frames, nEvents;
        if (!(clean >> who >> name >> frames >> nEvents) || frames < 1 || frames > 10000 || nEvents < 0 || nEvents > 16) {
            error = "clip_header";
            return false;
        }
        Clip* target = nullptr;
        if (who == "queen") {
            for (int a = 0; a < AnimCount; ++a) if (name == animName(a)) target = &bank.clip[a];
        } else if (who == "baby") {
            for (int a = 0; a < BabyAnimCount; ++a) if (name == babyAnimName(a)) target = &bank.baby[a];
        }
        if (!target) { error = "clip_name:" + who + "/" + name; return false; }
        Clip c;
        c.name = name;
        c.frames = frames;
        for (int e = 0; e < nEvents; ++e) {
            KeyEvent k;
            if (!(clean >> k.frame >> k.type) || k.frame < 0 || k.frame > frames) { error = "event:" + name; return false; }
            c.events.push_back(k);
        }
        int nPoses;
        if (!(clean >> nPoses) || nPoses < 0 || nPoses > kMaxPosesPerClip) { error = "poses:" + name; return false; }
        for (int p = 0; p < nPoses; ++p) {
            int f;
            if (!(clean >> f) || f < 0 || f >= frames || (p && f <= c.poses.back())) { error = "pose:" + name; return false; }
            c.poses.push_back(f);
        }
        c.staged = true;
        *target = c;
    }
    if (!ended) { error = "end"; return false; }
    params.retail = parms > 0;
    return true;
}

// SysShape::Animator + EnemyAnimatorBase stop/finish flags + the single
// latched key event of EnemyBase::onKeyEvent (same semantics as the Groink
// port's p2groinkfsm::Animator, sysShape.cpp:133-188).
class Animator {
public:
    void start(const Clip* clip, int anim) {
        mClip = clip;
        mAnim = anim;
        mTimer = 0.0f;
        mKey = clip ? lowest(0.0f) : 0;
        mFinish = mCompleted = false;
    }
    void finish() { mFinish = true; }
    bool isFinishing() const { return mFinish; }
    void animate(float dt) {
        mPlaying = false;
        if (!mClip) return;
        mTimer += 30.0f * dt;
        bool loopEndFound = false;
        const auto& events = mClip->events;
        while (!loopEndFound && mKey < events.size() && events[mKey].frame < int(mTimer)) {
            trigger(events[mKey].type);
            if (events[mKey].type == KeyLoopEnd && !mFinish) {
                int start = -1;
                for (std::size_t j = mKey; j-- > 0;)
                    if (events[j].type == KeyLoopStart) { start = events[j].frame; break; }
                mTimer = start >= 0 ? float(start) : 0.0f;
                loopEndFound = true;
                break;
            }
            ++mKey;
        }
        if (loopEndFound) mKey = lowest(mTimer);
        if (mTimer >= float(mClip->frames)) {
            mTimer = float(mClip->frames) - 1.0f;
            if (!mCompleted) { mCompleted = true; trigger(KeyEnd); }
        }
    }
    bool is(int type) const { return mPlaying && mType == type; }
    bool playing() const { return mPlaying; }
    int anim() const { return mAnim; }
    float frame() const { return mTimer; }
private:
    void trigger(int type) { mType = type; mPlaying = true; }
    std::size_t lowest(float minimum) const {
        std::size_t best = mClip->events.size();
        float bestFrame = 1e30f;
        for (std::size_t i = 0; i < mClip->events.size(); ++i) {
            const int f = mClip->events[i].frame;
            if (f >= int(minimum) && float(f) < bestFrame) { bestFrame = float(f); best = i; }
        }
        return best;
    }
    const Clip* mClip = nullptr;
    int mAnim = -1;
    float mTimer = 0.0f;
    std::size_t mKey = 0;
    bool mFinish = false, mCompleted = false, mPlaying = false;
    int mType = KeyLoopStart;
};

struct Vec2 { float x = 0.0f, z = 0.0f; };

// EnemyFunc::isStartFlick(enemy, false) (enemyAction.cpp:1209-1244).
inline bool isStartFlick(float flickTimer, int stuck, const Params& p) {
    const float v = flickTimer >= 0.0f ? flickTimer + 0.5f : flickTimer - 0.5f;
    const int flickInt = int(static_cast<std::uint8_t>(int(v)));
    if (stuck < p.shakeOffSticking1) return flickInt > p.shakeOffBlowA;
    if (stuck < p.shakeOffSticking2) return flickInt > p.shakeOffBlowB;
    if (stuck < p.shakeOffSticking3) return flickInt > p.shakeOffBlowC;
    return flickInt > p.shakeOffBlowD;
}

// Obj::damageCallBack coefficient for a Pikmin hit on a part (Queen.cpp).
inline float damageFactor(int state) {
    if (state == Sleep) return 0.1f;
    if (state == Flick) return 0.2f;
    return 1.0f;
}

struct TickInput {
    float health = 0.0f;   // engine BTeki::mHealth
    int hits = 0;          // Pikmin hits accepted by the damage seam since last tick
    int stuck = 0;         // live Pikmin stuck to the host
    int larvae = 0;        // live larvae (Baby::Mgr count)
    Vec2 pos;              // host position
    bool captain = false;  // an active captain exists (isRollingAttackLeft easy roll)
    Vec2 captainPos;
};
struct TickOutput {
    bool valid = false;
    std::vector<int> entered;       // states entered this tick, in order
    bool flickFace = false;         // StateFlick KEYEVENT_2: flickPikmin(faceDir)
    bool flickBackward = false;     // StateRolling (rolling): flickPikmin(FLICK_BACKWARD_ANGLE)
    bool rollingAttack = false;     // StateRolling (rolling): rollingAttack()
    bool birth = false;             // StateBorn KEYEVENT_2: createBabyChappy()
    bool crash = false;             // Rolling key 2 past territory-50 while rolling
    bool rollStart = false;         // Rolling loop-start: mIsRolling = true
    // PORT CONSTRAINT (no P2 counterpart): the P1 host map collision can hold a
    // rolling Queen against geometry the P2 arena never had. Key 2 with a
    // no-progress window either turns the roll like a territory-edge crash, or,
    // once rollingTime has elapsed, ends it to Wait. Guarantees termination.
    bool blockedTurn = false;       // blocked before rollingTime: turned like a crash
    bool blockedEnd = false;        // blocked after rollingTime: roll ended to Wait
    bool deadKey = false;           // Dead KEYEVENT_2 (vibration/rumble)
    bool wakeUp = false;            // Sleep KEYEVENT_2
    bool kill = false;              // Dead KEYEVENT_END: kill()
    bool constrained = true;        // hardConstraintOn (position held)
    Vec2 velocity;                  // mTargetVelocity
    float rollDot = 0.0f;
};

class Queen {
public:
    void init(const Params& p, const Bank& bank, bool canCreateLarva, bool easyRoll, Vec2 home, float faceDir,
              std::uint32_t seed) {
        mParams = p;
        mBank = &bank;
        mCanCreateLarva = canCreateLarva;
        mDoEasyRoll = easyRoll;
        mHome = home;
        mFaceDir = faceDir;
        mRng = seed ? seed : 1u;
        mNextState = Null;
        mIsRolling = false;
        mWaitTimer = 0.0f;
        resetRollProgress();
        mIsRoomForLarva = false;
        mBirthTimer = 0.0f;
        mPrevHitNum = 0.0f;
        mFlickTimer = 0.0f;
        mState = Null;
        TickOutput scratch;
        transit(mCanCreateLarva ? Wait : Sleep, false, scratch);
    }
    int state() const { return mState; }
    const Animator& animator() const { return mAnim; }
    float flickTimer() const { return mFlickTimer; }
    float birthTimer() const { return mBirthTimer; }
    bool rolling() const { return mIsRolling; }
    bool room() const { return mIsRoomForLarva; }
    float faceDir() const { return mFaceDir; }
    const Vec2& home() const { return mHome; }
    const Params& params() const { return mParams; }
    bool canCreateLarva() const { return mCanCreateLarva; }

    // One 30 Hz source update: Obj::doUpdate (updateCreateBaby, FSM exec)
    // then doAnimationCullingOff (animate).
    TickOutput tick(const TickInput& in) {
        TickOutput o;
        o.valid = true;
        mStuck = in.stuck;
        mHealth = in.health;
        // addDamage(dmg, 1.0): EB_FlickEnabled is on for the Queen.
        mFlickTimer += float(in.hits);
        // updateCreateBaby (Queen.cpp:8028A9A8).
        if (mCanCreateLarva) {
            mBirthTimer += kSourceDelta;
            if (in.larvae >= mParams.maxBirths) mIsRoomForLarva = false;
            else if (in.larvae <= mParams.minBirths) mIsRoomForLarva = true;
        }
        exec(in, o);
        mAnim.animate(kSourceDelta);
        o.velocity = mVelocity;
        o.constrained = mConstrained;
        return o;
    }

private:
    bool isCreateBaby() const { return mCanCreateLarva && mIsRoomForLarva && mBirthTimer > mParams.birthInterval; }
    bool isHitCounterUp() const { return mFlickTimer > mPrevHitNum; }
    bool startFlick() const { return isStartFlick(mFlickTimer, mStuck, mParams); }
    float randWeight() {
        mRng = mRng * 1664525u + 1013904223u;
        return float(mRng >> 8) / 16777216.0f;
    }
    void start(int anim) { mAnim.start(&mBank->clip[anim], anim); }
    Vec2 rollDir() const {
        const float theta = (mAnim.anim() == AnimRollingL ? kHalfPi : -kHalfPi) + mFaceDir;
        return {std::sin(theta), std::cos(theta)};
    }
    void cleanup(int s) {
        switch (s) {
        case Sleep: case Wait: case Damage: case Flick: mConstrained = false; break;
        case Born: mConstrained = false; mBirthTimer = 0.0f; break;
        case Rolling: mFlickTimer = 0.0f; mPrevHitNum = 0.0f; mIsRolling = false; break;
        default: break;
        }
    }
    void resetRollProgress() {
        mHavePrev = false;
        mRollBlocked = false;
        mRollProgress = mRollExpected = 0.0f;
    }
    // Port-only no-progress detector: compares the host's actual displacement
    // along last tick's commanded velocity over a kBlockWindow window.
    void trackRollProgress(const Vec2& pos) {
        const float speed = std::sqrt(mVelocity.x * mVelocity.x + mVelocity.z * mVelocity.z);
        if (mHavePrev && speed > 0.0f) {
            const float progress = ((pos.x - mPrevPos.x) * mVelocity.x + (pos.z - mPrevPos.z) * mVelocity.z) / speed;
            mRollProgress += progress;
            mRollExpected += speed * kSourceDelta;
            if (mRollExpected >= speed * kBlockWindow) {
                mRollBlocked = mRollProgress < kBlockFraction * mRollExpected;
                mRollProgress = mRollExpected = 0.0f;
            }
        } else {
            mRollProgress = mRollExpected = 0.0f;
        }
        mPrevPos = pos;
        mHavePrev = true;
    }
    void transit(int next, bool left, TickOutput& o) {
        if (next == Null) next = mState; // defensive: restart current state
        resetRollProgress();
        if (mState != Null) cleanup(mState);
        mState = next;
        o.entered.push_back(next);
        mNextState = Null;
        mVelocity = {};
        switch (next) {
        case Dead: mConstrained = false; start(AnimDead); break;
        case Sleep:
            mWaitTimer = 0.0f; mPrevHitNum = mFlickTimer; mConstrained = true; start(AnimSleep); break;
        case Wait:
            mWaitTimer = 0.0f; mPrevHitNum = mFlickTimer; mConstrained = true; start(AnimWait); break;
        case Damage: mWaitTimer = 0.0f; mConstrained = true; start(AnimDamage); break;
        case Flick: mWaitTimer = 0.0f; mConstrained = true; start(AnimFlick); break;
        case Rolling: mIsRolling = false; mConstrained = false; start(left ? AnimRollingL : AnimRollingR); break;
        case Born: mWaitTimer = 0.0f; mConstrained = true; start(AnimBorn); break;
        }
    }
    bool isRollingAttackLeft(const TickInput& in) {
        if (mDoEasyRoll) {
            mDoEasyRoll = false;
            if (in.captain) {
                const float a = kHalfPi + mFaceDir;
                const float dx = in.captainPos.x - in.pos.x, dz = in.captainPos.z - in.pos.z;
                if (std::sin(a) * dx + std::cos(a) * dz > 0.0f) return false;
            }
            return true;
        }
        return randWeight() < 0.5f;
    }
    void exec(const TickInput& in, TickOutput& o) {
        const bool dead = mHealth <= 0.0f;
        switch (mState) {
        case Sleep:
            if (dead || isHitCounterUp() || isCreateBaby()) mAnim.finish();
            if (mAnim.isFinishing()) {
                if (dead) mNextState = Dead;
                else if (startFlick()) mNextState = Flick;
                else if (mStuck != 0) mNextState = Damage;
                else mNextState = Wait;
            }
            if (mAnim.is(Key2)) o.wakeUp = true;
            else if (mAnim.is(KeyEnd)) transit(mNextState, false, o);
            break;
        case Wait:
            if (!isCreateBaby() && mWaitTimer > 30.0f) { mNextState = Sleep; mAnim.finish(); }
            if (isHitCounterUp()) { mNextState = Damage; mAnim.finish(); }
            if (isCreateBaby()) { mNextState = Born; mAnim.finish(); }
            if (startFlick()) { mNextState = Flick; mAnim.finish(); }
            if (dead) { mNextState = Dead; mAnim.finish(); }
            mWaitTimer += kSourceDelta;
            if (mAnim.is(KeyEnd)) transit(mNextState, false, o);
            break;
        case Damage:
            if (isCreateBaby()) { mNextState = Born; mAnim.finish(); }
            if (mStuck == 0) { mNextState = Wait; mAnim.finish(); }
            if (startFlick()) { mNextState = Flick; mAnim.finish(); }
            if (dead) { mNextState = Dead; mAnim.finish(); }
            if (mAnim.is(KeyEnd)) transit(mNextState, false, o);
            break;
        case Flick:
            if (mAnim.is(Key2)) o.flickFace = true;
            else if (mAnim.is(KeyEnd)) {
                if (dead) transit(Dead, false, o);
                else transit(Rolling, isRollingAttackLeft(in), o);
            }
            break;
        case Rolling: {
            if (mIsRolling) {
                trackRollProgress(in.pos);
                const Vec2 dir = rollDir();
                const float sx = in.pos.x - mHome.x, sz = in.pos.z - mHome.z;
                const float dot = sx * dir.x + sz * dir.z;
                o.rollDot = dot;
                if (dot > mParams.territoryRadius) {
                    mVelocity = {};
                } else {
                    const float r = 10.0f + mParams.territoryRadius;
                    float nx = dir.x * r + (mHome.x - in.pos.x), nz = dir.z * r + (mHome.z - in.pos.z);
                    const float len = std::sqrt(nx * nx + nz * nz);
                    if (len > 0.0f) { nx /= len; nz /= len; }
                    mVelocity = {nx * mParams.moveSpeed, nz * mParams.moveSpeed};
                }
                o.flickBackward = true;
                o.rollingAttack = true;
                mWaitTimer += kSourceDelta;
            } else {
                mVelocity = {};
                resetRollProgress();
            }
            if (dead) { mNextState = Dead; mIsRolling = false; mVelocity = {}; mAnim.finish(); }
            if (mAnim.is(Key2)) {
                const Vec2 dir = rollDir();
                const float dot = (in.pos.x - mHome.x) * dir.x + (in.pos.z - mHome.z) * dir.z;
                o.rollDot = dot;
                const float territory = mParams.territoryRadius - 50.0f;
                const float homeRad = -(50.0f + mParams.homeRadius);
                if (dot > territory) {
                    if (mIsRolling) o.crash = true;
                    mIsRolling = false;
                    mNextState = Rolling;
                    mAnim.finish();
                } else if (mWaitTimer > mParams.rollingTime && dot > homeRad && dot < 50.0f) {
                    mIsRolling = false;
                    mNextState = Wait;
                    mAnim.finish();
                } else if (mIsRolling && mRollBlocked) {
                    // Port constraint, see TickOutput::blockedTurn.
                    mIsRolling = false;
                    mAnim.finish();
                    if (mWaitTimer > mParams.rollingTime) { mNextState = Wait; o.blockedEnd = true; }
                    else { mNextState = Rolling; o.blockedTurn = true; }
                }
            } else if (mAnim.is(KeyLoopStart)) {
                if (!mIsRolling) { mIsRolling = true; o.rollStart = true; }
            } else if (mAnim.is(KeyEnd)) {
                // anim 6 (rolling_r) -> next pass left, else right.
                transit(mNextState, mAnim.anim() == AnimRollingR, o);
            }
            break;
        }
        case Born:
            if (mAnim.is(Key2)) o.birth = true;
            else if (mAnim.is(KeyEnd)) transit(dead ? Dead : Wait, false, o);
            break;
        case Dead:
            if (mAnim.is(Key2)) o.deadKey = true;
            else if (mAnim.is(KeyEnd)) o.kill = true;
            break;
        default: break;
        }
    }

    Params mParams;
    const Bank* mBank = nullptr;
    Animator mAnim;
    int mState = Null, mNextState = Null;
    bool mCanCreateLarva = true, mDoEasyRoll = false, mIsRolling = false, mIsRoomForLarva = false;
    bool mConstrained = true;
    float mWaitTimer = 0.0f, mBirthTimer = 0.0f, mPrevHitNum = 0.0f, mFlickTimer = 0.0f;
    float mHealth = 0.0f, mFaceDir = 0.0f;
    int mStuck = 0;
    Vec2 mHome, mVelocity, mPrevPos;
    bool mHavePrev = false, mRollBlocked = false;
    float mRollProgress = 0.0f, mRollExpected = 0.0f;
    std::uint32_t mRng = 1u;
};

// ---------------------------------------------------------------------------
// Baby (Bulborb Larva, 31). BabyState.cpp: Born -> Move <-> Attack; Dead and
// Press end in kill() (no carcass: EB_LeaveCarcass disabled, Baby.cpp onInit).
struct BabyTarget {
    bool valid = false;
    bool navi = false;
    Vec2 pos;
    float dist = 0.0f;
};
struct BabyInput {
    float health = 0.0f;
    bool landed = true;     // mFloorTriangle
    Vec2 pos;
    BabyTarget target;      // EnemyFunc::getNearestPikminOrNavi (host resolves)
};
struct BabyOutput {
    std::vector<int> entered;
    bool attackKey = false; // StateAttack KEYEVENT_2: attackNavi + eatPikmin (host resolves the mouth)
    bool swallowKey = false; // StateAttack KEYEVENT_3: swallowPikmin (kills what the mouth holds)
    bool kill = false;
    Vec2 velocity;
    float faceDir = 0.0f;
};
// Stickable body parts (queen/enemycoll.txt: seven 'st__' spheres on the skeleton,
// Queen.cpp Obj::flickPikmin switches on the stuck part's id). World-axis centres
// (forward = +Z, height above the actor origin) evaluated from the bind-pose
// joints of enemy.bmd with the collision file's joint offsets (local +X is the
// body axis): nose = head + 30, head, bod1 = neck5 - 25, bod2 = neck3 - 10,
// bod3 = body1, bod4 = body3, bod5 = body5 - 45 (the offset is along the joint's
// forward axis, so it lands inside the tail). The wait pose is the bind pose.
enum Part : int { PartNose = 0, PartHead, PartBod1, PartBod2, PartBod3, PartBod4, PartBod5, PartCount };
struct PartSphere { float z, y, radius; };
inline const PartSphere& partSphere(int p) {
    static const PartSphere spheres[PartCount] = {
        {237.5f, 90.1f, 10.0f}, {207.5f, 89.6f, 25.0f}, {154.6f, 87.0f, 60.0f}, {88.1f, 87.0f, 80.0f},
        {0.0f, 87.0f, 90.0f},   {-92.0f, 87.0f, 85.0f}, {-155.7f, 87.0f, 75.0f}};
    return spheres[p];
}
// The P1 host cannot say which part a Pikmin latched on, so the part is the
// sphere whose surface is nearest the Pikmin (smallest centre distance minus
// radius; a point inside several spheres takes the deepest). along/lateral/height
// are relative to the actor origin and facing.
inline int nearestPart(float along, float lateral, float height) {
    int best = PartBod3;
    float bestGap = 1e30f;
    for (int p = 0; p < PartCount; ++p) {
        const PartSphere& s = partSphere(p);
        const float dz = along - s.z, dy = height - s.y;
        const float gap = std::sqrt(dz * dz + lateral * lateral + dy * dy) - s.radius;
        if (gap < bestGap) { bestGap = gap; best = p; }
    }
    return best;
}
// Part a Pikmin latched on, from where it came from. The P1 host latches every
// Pikmin at the one point at its centre (all Pikmin read along~0, lateral~0 in
// the evidence), so the position at flick time carries no part information.
// The bearing of the Pikmin's last approach position (actor frame, taken before
// it stuck) does: P2 Pikmin attack the body part facing them, so the part is
// the sphere whose footprint circle the ray from the actor origin along that
// bearing leaves last (height ignored; Pikmin reach over the sphere height).
inline int exitPart(float along, float lateral) {
    const float len = std::sqrt(along * along + lateral * lateral);
    if (len < 1e-3f) return PartBod3;
    const float da = along / len; // ray direction (along, lateral)
    int best = PartBod3;
    float bestT = -1e30f;
    for (int p = 0; p < PartCount; ++p) {
        const PartSphere& s = partSphere(p);
        const float proj = da * s.z; // d . c, the centre lies on the lateral = 0 axis
        const float disc = proj * proj - s.z * s.z + s.radius * s.radius;
        if (disc < 0.0f) continue;
        const float t = proj + std::sqrt(disc);
        if (t > bestT) { bestT = t; best = p; }
    }
    return best;
}
// Queen::flickPikmin branches: nose/head/bod1 -> angle, bod5 -> PI + angle,
// everything else -> no knockback, no damage, FLICK_BACKWARD_ANGLE.
enum FlickKind : int { FlickFront = 0, FlickRear, FlickNone };
inline int flickKind(int part) {
    if (part == PartNose || part == PartHead || part == PartBod1) return FlickFront;
    if (part == PartBod5) return FlickRear;
    return FlickNone;
}
inline const char* partName(int p) {
    static const char* names[PartCount] = {"nose", "head", "bod1", "bod2", "bod3", "bod4", "bod5"};
    return p >= 0 && p < PartCount ? names[p] : "none";
}
// View-frustum cull sphere, centred on the actor origin. The P1 vehicle's root
// collision sphere (what BTeki::drawDefault culls with) is far smaller than the
// drawn P2 body, so she was dropped while partly on screen. Radii are the
// largest distance from the actor origin to any corner of the staged pose-bank
// bounds (Queen 24-pose bank: 385; Baby: 36), plus a small margin.
constexpr float kQueenCullRadius = 400.0f;
constexpr float kBabyCullRadius = 40.0f;
inline float cullRadius(bool larva) { return larva ? kBabyCullRadius : kQueenCullRadius; }
// Baby mouth slot (Baby::initMouthSlots: one slot on the "kamu" joint, radius
// 20). The staged larva rest/attack poses span z = -13.6..16.5, so the joint is
// approximated at the head tip 15 units ahead of the root along the facing; the
// joint itself is not evaluated on the P1 vehicle. EnemyFunc::eatPikmin takes a
// Pikmin whose position is within the slot radius of the slot (3D distance; the
// staged head sits near the ground, so the slot height is the root height).
constexpr float kBabyMouthRadius = 20.0f;
constexpr float kBabyMouthForward = 15.0f;
inline Vec2 babyMouthPoint(Vec2 pos, float faceDir) {
    return {pos.x + std::sin(faceDir) * kBabyMouthForward, pos.z + std::cos(faceDir) * kBabyMouthForward};
}
inline bool babyMouthReaches(Vec2 pos, float faceDir, Vec2 prey, float dy) {
    const Vec2 m = babyMouthPoint(pos, faceDir);
    const float dx = prey.x - m.x, dz = prey.z - m.z;
    return dx * dx + dz * dz + dy * dy < kBabyMouthRadius * kBabyMouthRadius;
}
inline float angDist(float target, float cur) {
    float d = target - cur;
    while (d > kPi) d -= 2.0f * kPi;
    while (d < -kPi) d += 2.0f * kPi;
    return d;
}
class Baby {
public:
    void init(const Params& p, const Bank& bank, float faceDir, Vec2 launch) {
        mParams = p;
        mBank = &bank;
        mFaceDir = faceDir;
        mVelocity = launch;
        mState = -1;
        BabyOutput o;
        transit(BabyBorn, o);
    }
    int state() const { return mState; }
    const Animator& animator() const { return mAnim; }
    float faceDir() const { return mFaceDir; }
    // StateAttack KEYEVENT_2: getSlotPikiNum() == 0 -> startMotion(AttackFail).
    // The clip has no key events, so it ends at KEYEVENT_END -> StateMove and
    // KEYEVENT_3 (swallow) never fires. Host calls this after eating nothing.
    void attackFailed() { if (mState == BabyAttack) start(BabyAnimAttackFail); }
    // Baby::pressCallBack: any press while past Born (state id > 2).
    bool press(BabyOutput& o) {
        if (mState > BabyBorn) { transit(BabyPress, o); return true; }
        return false;
    }
    BabyOutput tick(const BabyInput& in) {
        BabyOutput o;
        const bool dead = in.health <= 0.0f;
        switch (mState) {
        case BabyBorn:
            if (in.landed) { mVelocity.x *= 0.95f; mVelocity.z *= 0.95f; mAnim.finish(); }
            if (mAnim.is(KeyEnd)) transit(dead ? BabyDead : BabyMove, o);
            break;
        case BabyMove:
            if (dead) { transit(BabyDead, o); break; }
            if (in.target.valid) {
                const float want = std::atan2(in.target.pos.x - in.pos.x, in.target.pos.z - in.pos.z);
                // EnemyBase::turnToTarget: turn by min(turnSpeed * diff, maxTurnAngle).
                const float diff = angDist(want, mFaceDir);
                float step = mParams.babyTurnSpeed * diff;
                const float lim = mParams.babyMaxTurnAngle * kPi / 180.0f;
                if (step > lim) step = lim;
                if (step < -lim) step = -lim;
                mFaceDir = std::atan2(std::sin(mFaceDir + step), std::cos(mFaceDir + step));
                const float angle = angDist(want, mFaceDir);
                const float maxAtk = mParams.babyMaxAttackAngle * kPi / 180.0f;
                const float speed = std::fabs(angle) <= maxAtk ? mParams.babyMoveSpeed : 0.25f * mParams.babyMoveSpeed;
                mVelocity = {std::sin(mFaceDir) * speed, std::cos(mFaceDir) * speed};
                if (in.target.dist < mParams.babyMaxAttackRange && std::fabs(angle) <= maxAtk) {
                    transit(BabyAttack, o);
                    break;
                }
            } else {
                mVelocity = {}; // moveNoTarget: idle wander omitted (documented)
            }
            if (mAnim.is(KeyEnd)) transit(BabyMove, o);
            break;
        case BabyAttack:
            if (mAnim.is(Key2)) o.attackKey = true;
            else if (mAnim.is(Key3)) o.swallowKey = true;
            else if (mAnim.is(KeyEnd)) transit(dead ? BabyDead : BabyMove, o);
            break;
        case BabyDead:
        case BabyPress:
            if (mAnim.is(KeyEnd)) o.kill = true;
            break;
        }
        mAnim.animate(kSourceDelta);
        o.velocity = mVelocity;
        o.faceDir = mFaceDir;
        return o;
    }
private:
    void transit(int s, BabyOutput& o) {
        mState = s;
        o.entered.push_back(s);
        switch (s) {
        case BabyBorn: start(BabyAnimBorn); break;
        case BabyMove: start(BabyAnimMove); break;
        case BabyAttack: mVelocity = {}; start(BabyAnimAttack); break;
        case BabyDead: mVelocity = {}; start(BabyAnimDead); break;
        case BabyPress: mVelocity = {}; start(BabyAnimDeadPress); break;
        }
    }
    void start(int a) { mAnim.start(&mBank->baby[a], a); }
    Params mParams;
    const Bank* mBank = nullptr;
    Animator mAnim;
    int mState = -1;
    float mFaceDir = 0.0f;
    Vec2 mVelocity;
};

} // namespace p2queenown
