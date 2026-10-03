#pragma once

// Kabuto 75 (Armored Cannon Beetle Larva) travelling Stone fleet (#884).
//
// Engine-free emission rule + projectile fleet for the campaign Kabuto FSM
// (pc_p2_kabuto_fsm.cpp). The per-stone lifecycle policy is the existing
// P2CannonStone (pc_p2_cannon_stone.h); this header only adds what the
// campaign needs on top of it:
//   * KEYEVENT_2 emission timing for the attack clip,
//   * the source birth point (mouth XZ, body Y + 25),
//   * a fixed pool of stones owned independently of their shooters (a Stone
//     outlives the Kabuto that fired it), with 30 Hz ticking, host trace
//     adaptation, sphere contacts against a host target snapshot, a per-stone
//     strike ledger, dead-hold, release and flight metrics.
// Host dependencies (map trace, target enumeration, receivers, logs, draw) are
// injected; nothing here touches the P1 engine.
//
// Source (projectPiki/pikmin2, read-only checkout native/pikmin2-research):
//   KabutoState.cpp:347-372   StateAttack::exec: health gate first, then
//                             KEYEVENT_2 -> createStoneAttack.
//   Kabuto.cpp:268-290        createStoneAttack: Rock manager births
//                             EnemyID_Stone at (mouth.tx, 25 + mPosition.y,
//                             mouth.tz) facing mFaceDir; mIsHoming only for
//                             Rkabuto (95), so Kabuto 75's Stone never homes.
//   Rock.cpp:204-238/244-249  collisionCallback / wallCallback.
//   Rock.cpp:298-304          ignoreAtari: source enemy ignored for 1 s.
//   RockState.cpp:229-241     Move: timer, Dead on health <= 0 or timer > 15.
//   enemyBase.cpp:1878-1893   ground simulation keeps current Y velocity and
//                             applies gravity.
//   enemyBase.cpp:2080-2089   map sphere radius = fp01 (Stone disc 25).
// Retail data (experimental/pikmin2_cannon_projectile_assets.py):
//   EXPECTED_EVENTS Kabuto 'attack' [[50, 2]] (KEYEVENT_2 at frame 50),
//   DISC_PARMS 'Stone' general fp00 99999, fp01 25, fp06 250, fp08 0.03,
//   fp12 150, fp24 10, fp28 3.0; proper fp01 100.
//   docs/PIKMIN2_CANNON_PROJECTILE_ASSETS.md:164 Rock/Stone enemycoll: root
//   r40 @ joint 6 with one child r27 @ joint 6, both offset 0 (see
//   kContactRadiusFull for why the r27 leaf is the creature contact).

#include "pc_p2_cannon_stone.h"

#include <cmath>
#include <cstdint>
#include <vector>

namespace p2kabutostone {

constexpr int kAttackKey2Frame = 50;       // Kabuto attack clip KEYEVENT_2 (retail enemyanimmgr)
constexpr float kAnimFps = 30.0f;          // enemyAnimatorBase.cpp:4,11
// The animator raises a key event on the first advance where the integer
// timer passes the key frame: `mCurAnimKey->getFrame() < (int)mTimer`
// (sysGCU/sysShape.cpp:142), after `mTimer += speed` from 0 at startAnim
// (sysShape.cpp:53,139). startMotion pins mNormalizedTime to 1
// (enemyBase.cpp:2346-2350), so the timer advances mSpeed (30) x dt, one frame
// per 1/30 s (enemyBase.cpp:1685). The pose is then set to `(int)mTimer`
// (sysShape.cpp:187) and the model is calc'd in the same doAnimation
// (enemyBase.cpp:1705-1729). So KEYEVENT_2 at frame 50 is seen by
// StateAttack::exec once 51 animation frames have elapsed, with the joints
// posed at frame 51.
constexpr int kAttackKey2TriggerFrame = kAttackKey2Frame + 1;
constexpr float kBirthYOffset = 25.0f;     // Kabuto.cpp:276 (over the Kabuto's own Y)
constexpr float kMapRadius = 25.0f;        // Stone fp01, map sphere (enemyBase.cpp:2080-2089)
// Creature contact sphere (collisionCallback, Rock.cpp:204-238). Rock/Stone
// enemycoll.txt (retail enemyParms.szs) is a root r40 @ joint 6 with a single
// child r27 @ joint 6, both offset (0,0,0). P2 reports a creature collision
// only for a prim pair: isPrim() is `getChild() == nullptr || tube`
// (include/CollInfo.h:82), and CollTree::checkCollisionRec
// (plugProjectKandoU/collinfo.cpp:291-320) descends below a non-prim root
// before reporting. The r40 root is therefore only a bounding sphere; the
// contact is the concentric r27 leaf. CollPart::setScale scales every part
// (collinfo.cpp:1549-1558), called with the Stone's scale (Rock.cpp:346).
constexpr float kBoundRadiusFull = 40.0f;   // enemycoll root (broadphase only)
constexpr float kContactRadiusFull = 27.0f; // enemycoll r27 leaf
// Contact centre height: the leaf sits on joint 6 (rock_body), placed by
// CollPart::makeMatrixTo (collinfo.cpp:832-841) from the model matrix
// SRT(mScale, rot, mPosition) (enemyBase.cpp:1724,1745), so it is
// mPosition + (0, rockBodyY * scale, 0). StateMove plays run.bca
// (RockState.cpp:215); rock_body is (0, 25.0, 0) at run frame 0 and its Y
// bobs over [23.283, 27.576] (mean 25.666) across the 40 frames with X/Z
// always 0 (retail Rock enemy.bmd sha256 9ccbbc1a..., run.bca sha256
// ee786d76..., extracted read-only by
// output/claude-orch/p2-884/kabuto-r2/rock_body_run.py). The host uses the
// frame-0 value; the +/-2.3 unit bob is not modelled.
constexpr float kContactCentreYFull = 25.0f;
// Source "mouth" joint (index 3 of the babykabuto enemy.bmd) model-space
// translation at attack.bca frame 51, the pose the joint world matrix holds
// when createStoneAttack reads it (Kabuto.cpp:274-276). Extracted from the
// retail bank (enemy.bmd sha256 e63561e2..., attack.bca sha256 744d34a6...)
// by output/claude-orch/p2-884/kabuto_mouth_joint.py with the same J3D
// evaluation the pose banks use (experimental/pikmin2_rigid.joint_matrices).
// Neighbouring frames: 49 -> (0.002, 39.1, 40.2), 50 -> (-0.009, 38.7, 52.9),
// 52 -> (-0.039, 33.8, 65.7): the mouth lunges forward through the event.
// Model space: +z facing, +x left-to-right (R_y(h) maps +x to (cos h, 0,
// -sin h)); Kabuto mScaleModifier is 1 (enemyBase.cpp:893, never overridden).
constexpr int kMouthPoseFrame = kAttackKey2TriggerFrame;
constexpr float kMouthLocalX = -0.025f;
constexpr float kMouthLocalZ = 62.898f;
// Host stand-in for the Rock dead.bca length (unverified); matches the
// arena host's hold (pc_p2_projectiles.cpp kDeadHoldSeconds).
constexpr float kDeadHoldSeconds = 0.5f;
// Host capacity; RockMgr sizes its array per stage (RockMgr.cpp:101-115),
// retail per-stage count unverified. Exhaustion is tolerated (Kabuto.cpp:283).
constexpr int kFleetCapacity = 16;
// Retail P2 gravity (user/Kando/aiConstants.txt `gravity 560.0`,
// docs/PIKMIN2_ENGINE_DISC_PARMS.md:21), read by the Stone's ground
// simulation as _aiConstants->mGravity (enemyBase.cpp:1878-1893). The host
// passes this to Fleet::tick instead of the P1 AICONST gravity.
constexpr float kStoneGravity = 560.0f;

inline P2CannonStoneConfig stoneConfig()
{
    P2CannonStoneConfig c;
    c.variant = P2CannonStoneVariant::Stone;
    c.moveSpeed = 250.0f;        // fp06
    c.searchRumbleSpeed = 100.0f; // proper fp01 (homing only; unused for 75)
    c.turnSpeed = 0.03f;         // fp08
    c.maxTurnAngle = 3.0f;       // fp28
    c.attackDamage = 10.0f;      // fp24 (InteractPress)
    c.sightRadius = 150.0f;      // fp12 (homing only; unused for 75)
    c.collisionRadius = kMapRadius;
    c.health = 99999.0f;         // fp00
    return c;
}

// Attack-state seconds at which StateAttack::exec sees KEYEVENT_2: 51
// animation frames at 30 fps = 1.7 s (see kAttackKey2TriggerFrame).
inline float key2Seconds() { return static_cast<float>(kAttackKey2TriggerFrame) / kAnimFps; }

// Float tolerance for the accumulated stateTime (51 x float(1/30) can sum to
// just under 1.7); 1e-4 s is 0.003 animation frames.
constexpr float kKey2Epsilon = 1.0e-4f;

// True exactly on the host frame whose accumulated attack stateTime first
// reaches the KEYEVENT_2 time.
inline bool key2Crossed(float prev, float now)
{
    const float k = key2Seconds() - kKey2Epsilon;
    return prev < k && now >= k;
}

// The staged attack clip must contain frame 50 or the event can never play:
// with total frames <= 50 the key test (sysShape.cpp:142) never sees
// (int)mTimer > 50 before the timer is clamped to total - 1
// (sysShape.cpp:173-175) and the clip completes.
inline bool clipHasKey2(int durationFrames) { return durationFrames > kAttackKey2Frame; }

// StateAttack::exec order (KabutoState.cpp:350-358): a Kabuto with health <= 0
// transits to Dead before the event is looked at, so it never fires.
inline bool attackMayFire(float health, bool fireDone, float prev, float now)
{
    return health > 0.0f && !fireDone && key2Crossed(prev, now);
}

// createStoneAttack birth point (Kabuto.cpp:274-277): the mouth joint's world
// XZ, Y = the Kabuto's own Y + 25 (not the mouth Y). `localX/localZ` are the
// joint's model-space XZ; the world rotation is R_y(heading) about the feet.
inline P2CannonStoneVec3 birthPosition(const P2CannonStoneVec3& kabutoPos, float heading,
                                       float localX, float localZ)
{
    const float s = std::sin(heading), c = std::cos(heading);
    return { kabutoPos.x + c * localX + s * localZ, kabutoPos.y + kBirthYOffset,
             kabutoPos.z - s * localX + c * localZ };
}

// The source mouth at the KEYEVENT_2 pose.
inline P2CannonStoneVec3 mouthBirthPosition(const P2CannonStoneVec3& kabutoPos, float heading)
{
    return birthPosition(kabutoPos, heading, kMouthLocalX, kMouthLocalZ);
}

struct ContactSphere {
    P2CannonStoneVec3 centre;
    float radius = 0.0f;
};

// The Stone's creature contact sphere at base point `base` (mPosition) and
// scale `scale`: the r27 leaf on rock_body (see kContactRadiusFull).
inline ContactSphere contactSphere(const P2CannonStoneVec3& base, float scale)
{
    ContactSphere c;
    c.centre = { base.x, base.y + kContactCentreYFull * scale, base.z };
    c.radius = kContactRadiusFull * scale;
    return c;
}

// Host target snapshot entry (one per candidate creature per source tick).
struct Target {
    std::uint64_t token = 0;
    P2CannonStoneVec3 centre;
    float radius = 0.0f;
    P2CannonStoneContactKind kind = P2CannonStoneContactKind::NaviPiki;
    bool onFloor = false;
    bool alive = false;
    bool homingSearchable = false;
    P2CannonStoneVec3 position;
};

enum class DeadReason { Wall, Contact, Timeout, Invalid };

inline const char* deadReasonName(DeadReason r)
{
    switch (r) {
    case DeadReason::Wall: return "wall";
    case DeadReason::Contact: return "contact";
    case DeadReason::Timeout: return "timeout";
    default: return "invalid";
    }
}

struct Strike {
    int slot = -1;
    std::uint32_t stone = 0;
    std::uint64_t owner = 0; // live shooter token, 0 once forgotten
    std::uint64_t target = 0;
    P2CannonStoneContactKind targetKind = P2CannonStoneContactKind::NaviPiki;
    P2CannonStoneStrikeKind kind = P2CannonStoneStrikeKind::None;
    float damage = 0.0f;
    float flight = 0.0f;
    float travel = 0.0f;
};

struct DeadEvent {
    int slot = -1;
    std::uint32_t stone = 0;
    std::uint64_t owner = 0;
    DeadReason reason = DeadReason::Invalid;
    float flight = 0.0f;
    float travel = 0.0f;
    float maxLateral = 0.0f;
    float closestNaviPiki = 0.0f;
    int hits = 0;
    P2CannonStoneVec3 pos;
};

struct Released {
    int slot = -1;
    std::uint32_t stone = 0;
};

// Host map trace in the P2 base-point convention: `base` is mPosition, the
// velocity already carries the gravity-updated Y. Returns false when no trace
// was performed.
typedef bool (*TraceFn)(void* ctx, const P2CannonStoneVec3& base,
                        const P2CannonStoneVec3& velocity, float dt, float radius,
                        P2CannonStoneTraceResult& out);

class Fleet {
public:
    static constexpr int capacity() { return kFleetCapacity; }

    // Scene teardown / re-entry: drop every stone. The id counter is NOT reset
    // so stone ids stay unique for the whole process.
    void reset()
    {
        for (Slot& s : mSlots) {
            s.clear();
        }
    }

    // createStoneAttack. Kabuto 75: homing is always false. Returns the slot,
    // or -1 on exhaustion/invalid input with no state change.
    int fire(std::uint64_t owner, const P2CannonStoneVec3& birth, float faceDir,
             std::uint32_t& id, bool homing=false, float deathDuration=kDeadHoldSeconds)
    {
        for (int i = 0; i < kFleetCapacity; ++i) {
            Slot& s = mSlots[i];
            if (s.used) {
                continue;
            }
            const std::uint32_t next = mNextId + 1u;
            s.stone.reset(stoneConfig());
            if (!s.stone.birth(birth, faceDir, homing, owner, selfToken(next))) {
                s.stone.reset(stoneConfig());
                return -1;
            }
            s.clearMetrics();
            s.used = true;
            s.id = next;
            s.owner = owner;
            s.deathDuration=deathDuration;
            s.birth = birth;
            s.dirX = std::sin(s.stone.faceDir());
            s.dirZ = std::cos(s.stone.faceDir());
            mNextId = next;
            id = next;
            return i;
        }
        return -1;
    }

    // Shooter destroyed: its stones keep flying; later strikes carry owner 0.
    int forgetOwner(std::uint64_t owner)
    {
        if (!owner) {
            return 0;
        }
        int n = 0;
        for (Slot& s : mSlots) {
            if (s.used && s.owner == owner) {
                s.owner = 0;
                s.stone.forgetSource();
                ++n;
            }
        }
        return n;
    }

    // One 30 Hz source tick over every used slot.
    void tick(float gravity, TraceFn trace, void* traceCtx, const Target* targets, int targetCount,
              Strike* strikes, int strikeCap, int& strikeCount, DeadEvent* deads, int deadCap,
              int& deadCount, Released* released, int releasedCap, int& releasedCount,
              std::uint64_t activeNavi=0)
    {
        strikeCount = deadCount = releasedCount = 0;
        const float dt = P2CannonStone::kSourceDelta;
        for (int i = 0; i < kFleetCapacity; ++i) {
            Slot& s = mSlots[i];
            if (!s.used) {
                continue;
            }
            const P2CannonStonePhase phase = s.stone.phase();
            if (phase == P2CannonStonePhase::Killed || phase == P2CannonStonePhase::Inactive) {
                if (releasedCount < releasedCap) {
                    released[releasedCount++] = Released{ i, s.id };
                }
                s.clear();
                continue;
            }
            if (phase == P2CannonStonePhase::Dead) {
                // Dead disables atari (RockState.cpp:275-281): no contacts.
                s.deadHold += dt;
                if (s.deadHold >= s.deathDuration) {
                    s.stone.finishDeath();
                }
                continue;
            }

            // ROCK_Move.
            TraceAdapter adapter{ trace, traceCtx, gravity, &s.vy, false };
            P2CannonStoneTarget target;
            if(s.stone.homing()){
                float best=stoneConfig().sightRadius*stoneConfig().sightRadius;
                for(int n=0;n<targetCount;++n){const auto& q=targets[n];
                    if(!q.homingSearchable||!q.alive)continue;
                    if(activeNavi&&q.token==activeNavi){target.hasTarget=true;target.position=q.position;break;}
                    const float dx=q.position.x-s.stone.position().x,dz=q.position.z-s.stone.position().z;
                    const float d=dx*dx+dz*dz;if(d<best){best=d;target.hasTarget=true;target.position=q.position;}
                }
            }
            s.stone.update(dt, target, &TraceAdapter::call, &adapter);
            updateMetrics(s);
            if (!s.stone.isAlive()) {
                DeadEvent e;
                e.slot = i;
                e.stone = s.id;
                e.owner = s.owner;
                e.reason = adapter.wall                      ? DeadReason::Wall
                    : s.stone.hasHealthZeroed()                ? DeadReason::Contact
                    : s.stone.timer() > P2CannonStone::kMoveTimeoutSeconds ? DeadReason::Timeout
                                                                       : DeadReason::Invalid;
                e.flight = s.stone.timer();
                e.travel = s.travel;
                e.maxLateral = s.maxLateral;
                e.closestNaviPiki = s.closest;
                e.hits = s.hits;
                e.pos = s.stone.position();
                if (deadCount < deadCap) {
                    deads[deadCount++] = e;
                }
                continue;
            }

            // Contacts (collisionCallback, Rock.cpp:204-238) while still Move.
            const ContactSphere sphere = contactSphere(s.stone.position(), s.stone.scale());
            const float r = sphere.radius;
            const P2CannonStoneVec3& c = sphere.centre;
            for (int t = 0; t < targetCount; ++t) {
                const Target& tg = targets[t];
                if (!tg.alive) {
                    continue;
                }
                const float dx = tg.centre.x - c.x, dy = tg.centre.y - c.y, dz = tg.centre.z - c.z;
                const float d = std::sqrt(dx * dx + dy * dy + dz * dz);
                const float gap = d - r - tg.radius;
                if (tg.kind == P2CannonStoneContactKind::NaviPiki && gap < s.closest) {
                    s.closest = gap;
                }
                if (gap > 0.0f || s.struck(tg.token)) {
                    continue;
                }
                if (strikeCount >= strikeCap) {
                    // Host strike buffer full this tick: leave the contact
                    // unresolved (no policy call, no ledger entry, no hit
                    // count) so it is resolved on a later tick instead of
                    // being recorded as struck without a dispatched strike.
                    ++mStrikesDeferred;
                    continue;
                }
                const P2CannonStoneContactResult res =
                    s.stone.contact(tg.kind, tg.onFloor, false, tg.token);
                if (res.ignored) {
                    // Source grace (Rock.cpp:298-304): not a strike, not
                    // recorded, so the contact is eligible once grace ends.
                    ++mGraceIgnored;
                    continue;
                }
                if (!res.strikeEmitted) {
                    continue; // e.g. airborne Navi/Piki: no press, stone rolls on
                }
                s.ledger.push_back(tg.token);
                ++s.hits;
                Strike k;
                k.slot = i;
                k.stone = s.id;
                k.owner = s.owner;
                k.target = tg.token;
                k.targetKind = tg.kind;
                k.kind = res.strike.kind;
                k.damage = res.strike.damage;
                k.flight = s.stone.timer();
                k.travel = s.travel;
                strikes[strikeCount++] = k;
            }
        }
    }

    int active() const
    {
        int n = 0;
        for (const Slot& s : mSlots) {
            n += s.used ? 1 : 0;
        }
        return n;
    }
    bool used(int slot) const { return valid(slot) && mSlots[slot].used; }
    const P2CannonStone& stone(int slot) const { return mSlots[valid(slot) ? slot : 0].stone; }
    std::uint32_t id(int slot) const { return valid(slot) ? mSlots[slot].id : 0u; }
    std::uint64_t owner(int slot) const { return valid(slot) ? mSlots[slot].owner : 0u; }
    float travel(int slot) const { return valid(slot) ? mSlots[slot].travel : 0.0f; }
    float maxLateral(int slot) const { return valid(slot) ? mSlots[slot].maxLateral : 0.0f; }
    int hits(int slot) const { return valid(slot) ? mSlots[slot].hits : 0; }
    // Contacts suppressed by the source-enemy grace (diagnostic counter).
    std::uint64_t graceIgnored() const { return mGraceIgnored; }
    // Contacts left for a later tick because the host strike buffer was full.
    std::uint64_t strikesDeferred() const { return mStrikesDeferred; }
    float deadSeconds(int slot)const{return slot>=0&&slot<kFleetCapacity?mSlots[slot].deadHold:0.0f;}
    int ownedBy(std::uint64_t owner) const
    {
        int n = 0;
        for (const Slot& s : mSlots) {
            n += (s.used && owner && s.owner == owner) ? 1 : 0;
        }
        return n;
    }

private:
    struct Slot {
        bool used = false;
        P2CannonStone stone;
        std::uint32_t id = 0;
        std::uint64_t owner = 0;
        P2CannonStoneVec3 birth;
        float dirX = 0.0f, dirZ = 1.0f;
        float vy = 0.0f;
        float deadHold = 0.0f;
        float deathDuration=kDeadHoldSeconds;
        float travel = 0.0f;
        float maxLateral = 0.0f;
        float closest = 1.0e30f;
        int hits = 0;
        std::vector<std::uint64_t> ledger;

        void clearMetrics()
        {
            vy = 0.0f;
            deadHold = 0.0f;
            travel = 0.0f;
            maxLateral = 0.0f;
            closest = 1.0e30f;
            hits = 0;
            ledger.clear();
        }
        void clear()
        {
            used = false;
            stone.reset(stoneConfig());
            id = 0;
            owner = 0;
            clearMetrics();
        }
        bool struck(std::uint64_t token) const
        {
            for (std::uint64_t t : ledger) {
                if (t == token) {
                    return true;
                }
            }
            return false;
        }
    };

    // Adapts the policy's (position, targetVelocity) trace call to the host:
    // horizontal velocity follows the target, Y keeps the current velocity and
    // takes gravity (enemyBase.cpp:1878-1893).
    struct TraceAdapter {
        TraceFn host;
        void* ctx;
        float gravity;
        float* vy;
        bool wall;
        static bool call(void* context, const P2CannonStoneVec3& base,
                         const P2CannonStoneVec3& targetVelocity, float dt, float radius,
                         P2CannonStoneTraceResult& out)
        {
            TraceAdapter& a = *static_cast<TraceAdapter*>(context);
            if (!a.host) {
                return false;
            }
            const P2CannonStoneVec3 vel{ targetVelocity.x, *a.vy - a.gravity * dt, targetVelocity.z };
            if (!a.host(a.ctx, base, vel, dt, radius, out)) {
                return false;
            }
            *a.vy = out.velocity.y;
            a.wall = a.wall || out.wall;
            return true;
        }
    };

    static std::uint64_t selfToken(std::uint32_t id)
    {
        // Distinct from any creature address token (top bit set).
        return (std::uint64_t(1) << 63) | id;
    }
    static bool valid(int slot) { return slot >= 0 && slot < kFleetCapacity; }

    static void updateMetrics(Slot& s)
    {
        const P2CannonStoneVec3& p = s.stone.position();
        const float dx = p.x - s.birth.x, dz = p.z - s.birth.z;
        s.travel = std::sqrt(dx * dx + dz * dz);
        const float lateral = std::fabs(dx * s.dirZ - dz * s.dirX);
        if (lateral > s.maxLateral) {
            s.maxLateral = lateral;
        }
    }

    Slot mSlots[kFleetCapacity];
    std::uint32_t mNextId = 0;
    std::uint64_t mGraceIgnored = 0;
    std::uint64_t mStrikesDeferred = 0;
};

// ---- Campaign seam (called verbatim by pc_p2_kabuto_fsm.cpp) ----

// Accumulates the attack stateTime exactly as the campaign FSM does (prev is
// captured before `stateTime += dt`). Returns prev.
inline float advanceStateTime(float& stateTime, float dt)
{
    const float prev = stateTime;
    stateTime += dt;
    return prev;
}

enum class AttackAction { None, Die, Fired, PoolFull };

struct AttackStep {
    AttackAction action = AttackAction::None;
    int slot = -1;
    std::uint32_t id = 0;
    P2CannonStoneVec3 birth;
};

// One KB_ATTACK tick up to (not including) the clip-end transition, in
// StateAttack::exec order (KabutoState.cpp:347-358):
//   1. health <= 0 -> Die (nothing is fired, the caller transits to Dead);
//   2. on the KEYEVENT_2 crossing, exactly once per attack state, birth one
//      non-homing Stone at the source mouth (createStoneAttack) into the
//      shooter-independent fleet. A full fleet is tolerated (PoolFull), as a
//      failed Rock manager birth is (Kabuto.cpp:283).
// `fireDone` is the per-state latch the FSM resets on every transition.
inline AttackStep attackStep(Fleet& fleet, std::uint64_t owner, float health, bool& fireDone,
                             float prevStateTime, float stateTime,
                             const P2CannonStoneVec3& kabutoPos, float heading)
{
    AttackStep r;
    if (health <= 0.0f) {
        r.action = AttackAction::Die;
        return r;
    }
    if (!attackMayFire(health, fireDone, prevStateTime, stateTime)) {
        return r;
    }
    fireDone = true;
    r.birth = mouthBirthPosition(kabutoPos, heading);
    r.slot = fleet.fire(owner, r.birth, heading, r.id);
    r.action = r.slot >= 0 ? AttackAction::Fired : AttackAction::PoolFull;
    return r;
}

// Host frames -> 30 Hz source ticks for the fleet (same debt rule as
// pc_p2_projectiles_update): at most kMaxStoneTicksPerFrame per host frame,
// dropping the backlog when a frame is longer than that.
constexpr int kMaxStoneTicksPerFrame = 4;
inline int stoneTicksFor(double& debt, float dt)
{
    if (!(dt > 0.0f)) {
        return 0;
    }
    debt += dt;
    int ticks = static_cast<int>(debt / P2CannonStone::kSourceDelta);
    if (ticks > kMaxStoneTicksPerFrame) {
        ticks = kMaxStoneTicksPerFrame;
        debt = 0.0;
    } else {
        debt -= ticks * static_cast<double>(P2CannonStone::kSourceDelta);
    }
    return ticks;
}

} // namespace p2kabutostone
