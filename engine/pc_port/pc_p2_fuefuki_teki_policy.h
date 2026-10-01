#pragma once
// Engine-free campaign policy for the OWN Antenna Beetle (P2 Fuefuki, 41), #245.
//
// One p2fuefuki::Actor per seed-bound beetle. Each call to Actor::step() is one
// fixed 30 Hz source frame in the retail EnemyBase::update order:
//
//   1. doUpdate: the source FSM (pc_p2_fuefuki_fsm.h) execs with the key event
//      the previous frame's animate produced (mCurAnim->mType), the host world
//      snapshot (health, stuck attackers, intruders in mPrivateRadius, whistle
//      ring candidates, follower pings, press/hipdrop latch);
//   2. the FSM outputs become host commands: every locomotion output is applied
//      (Land teleport to a random territory point with random facing,
//      turnToTargetPos / walkToTarget at the retail fp06/fp08/fp28, Jump escape
//      velocity 1500 along the facing, zero velocity), plus flicks, Untargetable
//      hide/unhide, follower claims and releases, the kill request;
//   3. updateFootmarks (Fuefuki.cpp Obj::doUpdate) feeds the follower trail;
//   4. doAnimation: the retail player (pc_p2_retail_player.h, the verified
//      SysShape key-event semantics) advances one source frame of the current
//      clip and records the frame's last key event for the next exec.
//
// The host (pc_p2_fuefuki_teki.cpp) builds the World snapshot from P1 actors
// and applies Commands; tools/p2_fuefuki_teki_policy_test.cpp drives this with
// a mock host. Source: projectPiki/pikmin2 632af937 (read-only under
// native/pikmin2-research): Fuefuki.cpp, FuefukiState.cpp, aiTeki.cpp,
// interactPiki.cpp, enemyAction.cpp (walkToTarget), EnemyBase.h (turnToTarget).
#include "pc_p2_fuefuki_fsm.h"
#include "pc_p2_fuefuki_follow.h"
#include "pc_p2_retail_player.h"
#include <cmath>
#include <cstdint>
#include <functional>
#include <istream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

namespace p2fuefuki {

constexpr float kPi = 3.14159265358979323846f;
constexpr float kTau = 2.0f * kPi;
constexpr float kSourceDelta = 1.0f / 30.0f;
constexpr float kEscapeSpeed = 1500.0f;        // StateJump::exec hard-coded
constexpr float kTurnEndAngleDeg = 30.0f;      // StateTurn turnToTargetPos(..., 30)
constexpr float kArriveDistSq = 625.0f;        // Obj::isArriveTarget
constexpr float kFlickBackwardAngle = -1000.0f; // EnemyFunc.h FLICK_BACKWARD_ANGLE
// P1 safety guard on Obj::setTargetPosition (not in the source). The source
// picks any point in the territory ring; P2 maps are authored so every point
// there is valid ground. A P1 map is not: d4 (#245) landed on a ledge ~76 u
// above home, walked back onto it, died there, and the carcass route to the
// Onion ran into a closed waypoint. The host supplies a TargetProbe; each roll
// the probe rejects is re-rolled (up to kTargetTries source rolls, all from the
// per-token FSM RNG, so the choice stays deterministic), and if every roll is
// rejected the target falls back to home, which the placement audit proved.
constexpr int kTargetTries = 8;

// ------------------------------------------------------------------ parms
// General (EnemyParmsBase) + proper (Fuefuki::Parms::ProperParms) values the
// port consumes. Defaults are the source Parm<> defaults; `retail` is set only
// when a staged retail enemyparm.txt parsed.
struct Retail {
    float life = 100.0f;            // general fp00
    float moveSpeed = 80.0f;        // fp06
    float turnSpeed = 0.1f;         // fp08
    float maxTurnAngle = 10.0f;     // fp28 (degrees)
    float territoryRadius = 200.0f; // fp09
    float homeRadius = 15.0f;       // fp10
    float privateRadius = 70.0f;    // fp11
    float shakeChance = 1.0f;       // fp16
    float shakeKnockback = 300.0f;  // fp17
    float shakeDamage = 0.0f;       // fp18
    float shakeRange = 120.0f;      // fp19
    float attackRadius = 70.0f;     // fp22 (whistle ring base)
    float attackHitAngle = 15.0f;   // fp23 (ring effect angle speed)
    P2FuefukiFsmParms fsm;          // proper fp01..fp31
    bool retail = false;
};

inline float roundAng(float a)
{
    a = std::fmod(a, kTau);
    if (a < 0.0f) a += kTau;
    return a;
}
// Source angDist: signed shortest difference target - current in (-PI, PI].
inline float angDist(float target, float current)
{
    float d = roundAng(target) - roundAng(current);
    if (d > kPi) d -= kTau;
    if (d <= -kPi) d += kTau;
    return d;
}

// Block grammar of retail enemyparm.txt: `{tag} <kind> <value>` rows, blocks end
// at `{_eof}`, `#` comments dropped. General = the block holding fp00 and fp14;
// proper = the first later block holding fp01/fp31 without fp00.
inline bool parseEnemyParm(std::istream& in, Retail& out, std::string& error)
{
    std::vector<std::map<std::string, float>> blocks(1);
    std::string line;
    while (std::getline(in, line)) {
        const auto hash = line.find('#');
        if (hash != std::string::npos) line.resize(hash);
        std::istringstream words(line);
        std::string word;
        while (words >> word) {
            if (word == "{_eof}") {
                blocks.emplace_back();
                continue;
            }
            if (word.size() == 6 && word.front() == '{' && word.back() == '}') {
                std::string kind, value;
                if (!(words >> kind >> value)) {
                    error = "truncated parameter row " + word;
                    return false;
                }
                char* end = nullptr;
                const float v = std::strtof(value.c_str(), &end);
                if (!end || *end || !std::isfinite(v)) {
                    error = "bad parameter value " + word;
                    return false;
                }
                blocks.back()[word.substr(1, 4)] = v;
            }
        }
    }
    const std::map<std::string, float>* general = nullptr;
    const std::map<std::string, float>* proper = nullptr;
    for (const auto& b : blocks) {
        if (b.count("fp00") && b.count("fp14")) {
            if (general) {
                error = "duplicate general block";
                return false;
            }
            general = &b;
        } else if (general && !proper && !b.count("fp00") && b.count("fp01") && b.count("fp31")) {
            proper = &b;
        }
    }
    if (!general || !proper) {
        error = general ? "missing proper block" : "missing general block";
        return false;
    }
    Retail r;
    auto g = [&](const char* tag, float& dst) {
        auto it = general->find(tag);
        if (it != general->end()) dst = it->second;
    };
    auto p = [&](const char* tag, float& dst) {
        auto it = proper->find(tag);
        if (it != proper->end()) dst = it->second;
    };
    g("fp00", r.life); g("fp06", r.moveSpeed); g("fp08", r.turnSpeed); g("fp28", r.maxTurnAngle);
    g("fp09", r.territoryRadius); g("fp10", r.homeRadius); g("fp11", r.privateRadius);
    g("fp16", r.shakeChance); g("fp17", r.shakeKnockback); g("fp18", r.shakeDamage);
    g("fp19", r.shakeRange); g("fp22", r.attackRadius); g("fp23", r.attackHitAngle);
    p("fp01", r.fsm.maxGroundTime); p("fp02", r.fsm.minGroundTime); p("fp03", r.fsm.airborneTime);
    p("fp11", r.fsm.minWhistleTime); p("fp12", r.fsm.maxWhistleTimeNoSquad);
    p("fp13", r.fsm.maxWhistleTimeWithSquad); p("fp21", r.fsm.struggleTime);
    p("fp22", r.fsm.jumpTime); p("fp31", r.fsm.normalLandingChance);
    r.fsm.attackRadius = r.attackRadius;
    if (!(r.life > 0.0f) || r.moveSpeed < 0.0f || r.turnSpeed < 0.0f || r.maxTurnAngle < 0.0f
        || !(r.territoryRadius > 0.0f) || r.homeRadius < 0.0f || r.privateRadius < 0.0f
        || r.attackRadius < 0.0f || r.fsm.airborneTime < 0.0f || r.fsm.struggleTime < 0.0f) {
        error = "nonphysical parameter value";
        return false;
    }
    r.retail = true;
    out = r;
    return true;
}

// ------------------------------------------------------------------ clips
// FUEFUKIANIM_* (Fuefuki.h) == retail fuefuki/enemyanimmgr.txt row order.
enum Anim { AnimDead, AnimLanding, AnimLandFail, AnimMove, AnimPivot, AnimWait,
            AnimWhisle, AnimStruggle, AnimJump, AnimCarry, AnimCount };
inline const char* animName(int a)
{
    static const char* names[AnimCount] = {"dead", "landing", "landfail", "move", "pivot",
                                           "wait", "whisle", "struggle", "jump", "carry"};
    return a >= 0 && a < AnimCount ? names[a] : "none";
}
inline const char* stateName(P2FuefukiFsmState s)
{
    switch (s) {
    case P2FuefukiFsmState::Dead: return "dead";
    case P2FuefukiFsmState::Stay: return "stay";
    case P2FuefukiFsmState::Land: return "land";
    case P2FuefukiFsmState::Jump: return "jump";
    case P2FuefukiFsmState::Wait: return "wait";
    case P2FuefukiFsmState::Turn: return "turn";
    case P2FuefukiFsmState::Walk: return "walk";
    case P2FuefukiFsmState::Whisle: return "whisle";
    case P2FuefukiFsmState::Struggle: return "struggle";
    }
    return "none";
}
// State init -> startMotion (FuefukiState.cpp). Land picks landing/landfail by
// the fp31 roll; Stay starts Landing and stops it (frame 0, zero-scale pose).
inline int animForState(P2FuefukiFsmState s, bool landingNormal)
{
    switch (s) {
    case P2FuefukiFsmState::Dead: return AnimDead;
    case P2FuefukiFsmState::Stay: return AnimLanding;
    case P2FuefukiFsmState::Land: return landingNormal ? AnimLanding : AnimLandFail;
    case P2FuefukiFsmState::Jump: return AnimJump;
    case P2FuefukiFsmState::Wait: return AnimWait;
    case P2FuefukiFsmState::Turn: return AnimPivot;
    case P2FuefukiFsmState::Walk: return AnimMove;
    case P2FuefukiFsmState::Whisle: return AnimWhisle;
    case P2FuefukiFsmState::Struggle: return AnimStruggle;
    }
    return AnimWait;
}

// Retail motion table (P2_RETAIL_EVENTS_1 from pikmin2_fuefuki_motion.py) keyed
// by FUEFUKIANIM slot. All 10 clips are required.
struct Motions {
    p2retail::Motion clip[AnimCount];
    bool loaded = false;
};
inline bool loadMotions(std::istream& in, Motions& out, std::string& error)
{
    Motions m;
    p2retail::Table table;
    try {
        table = p2retail::read(in);
    } catch (const std::exception& e) {
        error = e.what();
        return false;
    }
    int found = 0;
    for (const auto& motion : table.motions) {
        for (int a = 0; a < AnimCount; ++a) {
            if (motion.name == std::string(animName(a)) + ".bca") {
                m.clip[a] = motion;
                ++found;
            }
        }
    }
    if (found != AnimCount) {
        error = "motion table lacks a FUEFUKIANIM clip";
        return false;
    }
    m.loaded = true;
    out = m;
    return true;
}

// ------------------------------------------------------------------ world
struct PikiView {
    std::uint32_t id = 0;
    float x = 0.0f, y = 0.0f, z = 0.0f;
    bool alive = false;
    bool pikmin = true;        // Piki::isPikmin (not a Bulbmin)
    bool callable = false;     // current state callable() (P1: Normal, not stuck/buried)
    bool stuckToMouth = false;
    bool stuckToSelf = false;  // attacker stuck on this beetle
    bool followingOther = false; // ACT_Teki owned by another beetle
};
struct NaviView {
    std::uint32_t id = 0;
    float x = 0.0f, z = 0.0f;
    bool alive = false;
};
struct World {
    float x = 0.0f, y = 0.0f, z = 0.0f; // host position (after last integration)
    float health = 1.0f;
    bool pressed = false;               // press/hipdrop latched since last step
    bool bittered = false;
    bool water = false;
    std::vector<PikiView> pikis;
    std::vector<NaviView> navis;
};

struct Commands {
    bool valid = false;
    // Locomotion (host integrates velocity with its own map collision).
    float faceDir = 0.0f;
    float vx = 0.0f, vz = 0.0f;
    bool teleport = false;
    float tx = 0.0f, tz = 0.0f;         // host resolves ground height
    int targetTries = 0;                // guarded rolls spent on this target
    bool targetFallback = false;        // every roll rejected -> home
    // Visibility / targetability (EB_Untargetable mirror).
    bool untargetable = false;
    bool untargetableChanged = false;
    bool drawHidden = false;            // Stay (landing frame 0 is zero-scale)
    // Whistle theft.
    float whistleRadius = 0.0f;
    std::vector<std::uint32_t> claimed, releasedSuspend, releasedPanic, pinged;
    // Flicks (EnemyFunc::flickStickPikmin / flickNearbyPikmin / flickNearbyNavi).
    std::vector<std::uint32_t> flickStick, flickPiki, flickNavi;
    float flickKnockback = 0.0f, flickDamage = 0.0f, flickStickAngle = 0.0f, flickNearbyAngle = 0.0f;
    // Animation / lifecycle.
    int anim = AnimWait;
    float animFrame = 0.0f;
    bool transited = false;
    P2FuefukiFsmState from = P2FuefukiFsmState::Land, to = P2FuefukiFsmState::Land;
    bool pressAccepted = false;
    bool kill = false;
    int stuck = 0;
    bool intruder = false;
};

// ------------------------------------------------------------------ press
// Source Obj::pressCallBack / hipdropCallBack (Fuefuki.cpp:163-185): with a
// presser, mCanStruggle and no EB_Bittered the beetle transits to Struggle and
// the callback returns false, so PikiFlyingState::collisionCallback goes on to
// latch the Pikmin; otherwise it returns true and the descending Pikmin does
// NOT latch (pressCheck). A dead or already struggling beetle never accepts
// (the flying callback only presses living enemies; Struggle clears the flag).
inline bool pressAccepted(const P2FuefukiFsm& fsm, bool presser, bool bittered)
{
    const P2FuefukiFsmState st = fsm.getState();
#ifdef P2_FUEFUKI_MUTANT_PRESS_ALWAYS
    (void)bittered;
    return presser && st != P2FuefukiFsmState::Dead;
#else
    return presser && fsm.getCanStruggle() && !bittered && st != P2FuefukiFsmState::Dead
           && st != P2FuefukiFsmState::Struggle;
#endif
}

// ------------------------------------------------------------------ actor
class Actor {
public:
    // Host reachability probe for Land/Walk targets (see kTargetTries). Set it
    // before bind(): the onInit Land teleport already asks it. Unset = source
    // behaviour (every roll accepted).
    using TargetProbe = std::function<bool(float x, float z)>;
    void setTargetProbe(TargetProbe probe) { probe_ = std::move(probe); }
    int lastTargetTries() const { return lastTries_; }
    bool lastTargetFallback() const { return lastFallback_; }
    int rejectedTargets() const { return rejected_; }
    int fallbackTargets() const { return fallbacks_; }

    // `epoch` must be unique and nonzero per actor within `table` (the host uses
    // a monotonically increasing bind counter); `token` is the seed slot uid.
    bool bind(const Retail& retail, const Motions& motions, P2FuefukiOwnershipTable& table,
              std::uint64_t epoch, std::uint32_t token, float x, float y, float z, float faceDir)
    {
        if (bound_ || !motions.loaded) return false;
        retail_ = retail;
        motions_ = motions;
        token_ = token;
        fsm_ = P2FuefukiFsm(retail.fsm);
#ifdef P2_FUEFUKI_MUTANT_TOKEN_UNUSED
        fsm_.seed(0x9E3779B9u);
#else
        fsm_.seed(token * 2654435761u + 0x9E3779B9u);
#endif
        P2FuefukiFollowParms fp;
        follow_.setParms(fp);
        homeX_ = x; homeY_ = y; homeZ_ = z;
        x_ = x; z_ = z;
        faceDir_ = roundAng(faceDir);
        const P2FuefukiFsmOut out = fsm_.spawn(table, epoch);
        if (!out.accepted) return false;
        bound_ = true;
        // onInit -> FUEFUKI_Land: StateLand::init effects.
        Commands spawnCmd;
        applyTransition(out, P2FuefukiFsmState::Stay, spawnCmd);
        spawnCmd.valid = true;
        spawnCmd.faceDir = faceDir_;
        spawnCmd.transited = true;
        spawnCmd.from = P2FuefukiFsmState::Stay;
        spawnCmd.to = out.state;
        pendingSpawn_ = spawnCmd;
        return true;
    }

    bool bound() const { return bound_; }
    std::uint32_t token() const { return token_; }
    P2FuefukiFsm& fsm() { return fsm_; }
    const P2FuefukiFsm& fsm() const { return fsm_; }
    P2FuefukiFollowController& follow() { return follow_; }
    const Retail& retail() const { return retail_; }
    int anim() const { return anim_; }
    float animFrame() const { return player_.frame(); }
    bool playing() const { return playing_; }
    bool untargetable() const { return untargetable_; }
    float faceDir() const { return faceDir_; }
    float targetX() const { return targetX_; }
    float targetZ() const { return targetZ_; }
    float homeX() const { return homeX_; }
    float homeZ() const { return homeZ_; }
    bool holds(std::uint32_t pikmin) const { return follow_.holds(pikmin); }

    // Spawn-time commands (Land entry: teleport, clip) the host applies once.
    Commands takeSpawnCommands()
    {
        Commands c = pendingSpawn_;
        pendingSpawn_ = Commands{};
        return c;
    }

    // One fixed 30 Hz source frame.
    Commands step(const World& w)
    {
        Commands c;
        if (!bound_) return c;
        c.valid = true;
        x_ = w.x;
        z_ = w.z;
        const P2FuefukiFsmState before = fsm_.getState();

        P2FuefukiFsmInput in;
        in.delta = kSourceDelta;
        in.health = w.health;
        in.animPlaying = playing_;
        in.keyEvent = pendingKey_;
        pendingKey_ = 0;
        in.motionFinished = finishing_;
        in.pressed = w.pressed;
        in.bittered = w.bittered;
        in.water = w.water;
        int stuck = 0;
        for (const PikiView& p : w.pikis)
            if (p.alive && p.stuckToSelf) ++stuck;
        in.stuckPikmin = stuck;
        c.stuck = stuck;

        // Turn/Walk locomotion runs inside exec, before the transition checks.
        velX_ = velZ_ = 0.0f;
        if (before == P2FuefukiFsmState::Turn) {
            const float ang = turnToTarget();
            in.turnComplete = std::fabs(ang) <= kTurnEndAngleDeg * kPi / 180.0f;
        } else if (before == P2FuefukiFsmState::Walk) {
            if (!finishing_) {
                // EnemyFunc::walkToTarget: turnToTarget then setTargetSpeed.
                turnToTarget();
                velX_ = retail_.moveSpeed * std::sin(faceDir_);
                velZ_ = retail_.moveSpeed * std::cos(faceDir_);
                const float dx = x_ - targetX_, dz = z_ - targetZ_;
                in.arriveTarget = dx * dx + dz * dz < kArriveDistSq;
            }
        }
        // Whistle ring candidates (Obj::updateWhisle): modifier grows before the
        // scan, so this frame's ring is min(1, modifier + delta) * fp22.
        if (before == P2FuefukiFsmState::Whisle) {
            float mod = fsm_.squad().getRadiusModifier() + kSourceDelta;
            if (mod > 1.0f) mod = 1.0f;
            const float radius = mod * retail_.attackRadius;
            const float r2 = radius * radius;
            for (const PikiView& p : w.pikis) {
                if (!p.alive || !p.pikmin || p.stuckToMouth || holds(p.id)) continue;
                const float dx = p.x - x_, dz = p.z - z_;
#ifdef P2_FUEFUKI_MUTANT_RING_IGNORED
                (void)r2;
                if (dx * dx + dz * dz < 1e12f) {
#else
                if (dx * dx + dz * dz < r2) {
#endif
                    P2FuefukiCandidate cand;
                    cand.id = p.id;
                    cand.living = p.alive;
                    cand.callable = p.callable;
                    cand.stuckToMouth = p.stuckToMouth;
                    cand.alreadyTeki = p.followingOther;
                    in.candidates.push_back(cand);
                }
            }
        }
        // isJumpAway runs after updateWhisle inside the same exec, so a Pikmin
        // the ring admits this frame is already isMyPikmin(this), not an intruder.
        {
            std::vector<std::uint32_t> admitting;
            for (const P2FuefukiCandidate& cand : in.candidates)
                if (cand.living && cand.callable && !cand.stuckToMouth && !cand.alreadyTeki) admitting.push_back(cand.id);
            in.intruder = intruder(w, admitting);
            c.intruder = in.intruder;
        }
        // ActTeki::exec pings (InteractFuefukiTimerReset) from live followers.
        for (int i = 0; i < follow_.followerCount(); ++i) in.followerPings.push_back(follow_.followerAt(i));

        const P2FuefukiFsmOut out = fsm_.tick(in);
        if (!out.accepted) {
            c.valid = false;
            return c;
        }
        c.pinged = out.pinged;
        c.whistleRadius = out.whistleRadius;
        c.claimed = out.claimed;
        for (std::uint32_t id : out.claimed) follow_.claim(id);
        if (out.requestFinishMotion) {
            finishing_ = true;
            player_.finishMotion(true);
        }
        if (out.zeroVelocity) velX_ = velZ_ = 0.0f;
        if (out.escapeVelocity) {
            velX_ = kEscapeSpeed * std::sin(faceDir_);
            velZ_ = kEscapeSpeed * std::cos(faceDir_);
        }
        if (out.flickStuck || out.flickNavi || out.flickPikmin) flick(w, out, c);
        if (out.transited) {
            c.transited = true;
            c.from = before;
            c.to = out.state;
            // Walk / Land cleanup: setTargetPosition(false).
            if (before == P2FuefukiFsmState::Walk || before == P2FuefukiFsmState::Land)
                setTargetPosition(false);
            applyTransition(out, before, c);
            c.pressAccepted = out.state == P2FuefukiFsmState::Struggle && w.pressed;
        } else {
            applyEvents(out, c);
        }
        for (std::uint32_t id : out.releasedSuspend) {
            follow_.release(id);
            c.releasedSuspend.push_back(id);
        }
        for (std::uint32_t id : out.releasedPanic) {
            follow_.release(id);
#ifndef P2_FUEFUKI_MUTANT_NO_PANIC
            c.releasedPanic.push_back(id);
#endif
        }
        c.kill = out.kill;

        // updateFootmarks after exec (Obj::doUpdate).
        follow_.beetleTick(x_, z_, kSourceDelta);

        // doAnimation: one retail frame (anim speed 30 frames/s at 30 Hz).
        if (playing_) {
            int key = 0;
            player_.advance(1.0f, [&](const p2retail::Event& e) {
                if (e.type == 2 || e.type == 3) key = e.type;
                else if (e.type == 1000) key = 4;
            });
            pendingKey_ = key;
        }
        c.faceDir = faceDir_;
        c.vx = velX_;
        c.vz = velZ_;
        c.anim = anim_;
        c.animFrame = player_.frame();
        c.untargetable = untargetable_;
        c.drawHidden = fsm_.getState() == P2FuefukiFsmState::Stay;
        return c;
    }

    // Owner teardown outside the FSM (host forget): commit the owner-death
    // release so no follower survives the actor.
    std::vector<std::uint32_t> ownerDeath()
    {
        std::vector<std::uint32_t> released;
        if (!bound_) return released;
        const P2FuefukiFsmOut out = fsm_.enterOwnerDeath();
        for (std::uint32_t id : out.releasedPanic) {
            follow_.release(id);
            released.push_back(id);
        }
        return released;
    }

    // Drop a follower that died / was removed without an FSM release.
    void forgetFollower(std::uint32_t id)
    {
        follow_.release(id);
    }

private:
    bool intruder(const World& w, const std::vector<std::uint32_t>& admitting) const
    {
        const float r2 = retail_.privateRadius * retail_.privateRadius;
        for (const NaviView& n : w.navis) {
            if (!n.alive) continue;
            const float dx = n.x - x_, dz = n.z - z_;
            if (dx * dx + dz * dz < r2) return true;
        }
        for (const PikiView& p : w.pikis) {
            if (!p.alive || !p.pikmin || p.stuckToMouth || holds(p.id)) continue;
            bool admitted = false;
            for (std::uint32_t id : admitting) admitted = admitted || id == p.id;
            if (admitted) continue;
            const float dx = p.x - x_, dz = p.z - z_;
            if (dx * dx + dz * dz < r2) return true;
        }
        return false;
    }

    // EnemyBase::turnToTargetPos(target, fp08, fp28): returns the pre-turn
    // angle distance.
    float turnToTarget()
    {
        const float want = std::atan2(targetX_ - x_, targetZ_ - z_);
        const float dist = angDist(want, faceDir_);
        const float limit = retail_.maxTurnAngle * kPi / 180.0f;
        float turn = dist * retail_.turnSpeed;
        if (turn > limit) turn = limit;
        if (turn < -limit) turn = -limit;
        faceDir_ = roundAng(faceDir_ + turn);
        return dist;
    }

    // Obj::setTargetPosition (not a cave: P1 has no caves).
    // With a host probe, rejected rolls are re-rolled and the last resort is
    // home (P1 safety guard, see kTargetTries).
    void setTargetPosition(bool landing)
    {
        lastTries_ = 0;
        lastFallback_ = false;
        for (int attempt = 0; attempt < kTargetTries; ++attempt) {
            const float range = retail_.territoryRadius - retail_.homeRadius;
            const float dist = retail_.homeRadius + fsm_.randWeight(range > 0.0f ? range : 0.0f);
            float angle;
            if (landing) {
                angle = fsm_.randWeight(kTau);
            } else {
                angle = std::atan2(x_ - homeX_, z_ - homeZ_) + fsm_.randWeight(kPi) + 0.5f * kPi;
            }
            targetX_ = dist * std::sin(angle) + homeX_;
            targetZ_ = dist * std::cos(angle) + homeZ_;
            ++lastTries_;
#ifdef P2_FUEFUKI_MUTANT_NO_TARGET_GUARD
            return;
#endif
            if (!probe_ || probe_(targetX_, targetZ_)) return;
            ++rejected_;
        }
        lastFallback_ = true;
        ++fallbacks_;
        targetX_ = homeX_;
        targetZ_ = homeZ_;
    }

    void startAnim(int a, bool play)
    {
        anim_ = a;
        finishing_ = false;
        playing_ = play && player_.start(motions_.clip[a]);
        if (!play) player_.start(motions_.clip[a]); // stopMotion: hold frame 0
        pendingKey_ = 0;
    }

    void setUntargetable(bool on, Commands& c)
    {
        if (untargetable_ == on) return;
        untargetable_ = on;
        c.untargetableChanged = true;
    }

    void applyEvents(const P2FuefukiFsmOut& out, Commands& c)
    {
#ifndef P2_FUEFUKI_MUTANT_NO_HIDE
        if (out.eventSet & P2FUEFUKI_EB_Untargetable) setUntargetable(true, c);
#endif
        if (out.eventClear & P2FUEFUKI_EB_Untargetable) setUntargetable(false, c);
    }

    void applyTransition(const P2FuefukiFsmOut& out, P2FuefukiFsmState before, Commands& c)
    {
        (void)before;
        applyEvents(out, c);
        const P2FuefukiFsmState to = out.state;
        if (to == P2FuefukiFsmState::Land) {
            // StateLand::init: setTargetPosition(true), onSetPosition(target),
            // mFaceDir = randWeightFloat(TAU), fp31 landing roll.
            setTargetPosition(true);
            c.teleport = true;
            c.tx = targetX_;
            c.tz = targetZ_;
            c.targetTries = lastTries_;
            c.targetFallback = lastFallback_;
            x_ = targetX_;
            z_ = targetZ_;
            faceDir_ = roundAng(fsm_.randWeight(kTau));
            const bool normal = fsm_.rand01() < retail_.fsm.normalLandingChance;
            startAnim(animForState(to, normal), true);
        } else if (to == P2FuefukiFsmState::Stay) {
            startAnim(AnimLanding, false); // startMotion(Landing) + stopMotion()
        } else {
            startAnim(animForState(to, true), true);
        }
        c.anim = anim_;
    }

    void flick(const World& w, const P2FuefukiFsmOut& out, Commands& c)
    {
        c.flickKnockback = retail_.shakeKnockback;
        c.flickDamage = retail_.shakeDamage;
        c.flickStickAngle = roundAng(kFlickBackwardAngle + kPi);
        c.flickNearbyAngle = kFlickBackwardAngle + kPi;
        const float r2 = retail_.shakeRange * retail_.shakeRange;
        if (out.flickStuck)
            for (const PikiView& p : w.pikis)
                if (p.alive && p.stuckToSelf && !p.stuckToMouth && retail_.shakeChance > fsm_.rand01())
                    c.flickStick.push_back(p.id);
        if (out.flickPikmin)
            for (const PikiView& p : w.pikis) {
                if (!p.alive || p.stuckToSelf) continue;
                const float dx = p.x - x_, dz = p.z - z_;
                if (dx * dx + dz * dz < r2) c.flickPiki.push_back(p.id);
            }
        if (out.flickNavi)
            for (const NaviView& n : w.navis) {
                if (!n.alive) continue;
                const float dx = n.x - x_, dz = n.z - z_;
                if (dx * dx + dz * dz < r2) c.flickNavi.push_back(n.id);
            }
    }

    Retail retail_;
    Motions motions_;
    P2FuefukiFsm fsm_;
    P2FuefukiFollowController follow_;
    p2retail::Player player_;
    Commands pendingSpawn_;
    std::uint32_t token_ = 0;
    bool bound_ = false;
    bool playing_ = false;
    bool finishing_ = false;
    bool untargetable_ = false;
    int anim_ = AnimLanding;
    int pendingKey_ = 0;
    float x_ = 0.0f, z_ = 0.0f;
    float homeX_ = 0.0f, homeY_ = 0.0f, homeZ_ = 0.0f;
    float targetX_ = 0.0f, targetZ_ = 0.0f;
    float faceDir_ = 0.0f;
    float velX_ = 0.0f, velZ_ = 0.0f;
    TargetProbe probe_;
    int lastTries_ = 0;
    bool lastFallback_ = false;
    int rejected_ = 0;
    int fallbacks_ = 0;
};

} // namespace p2fuefuki
