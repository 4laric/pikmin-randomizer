#include "pc_p2_kurage_arena.h"

#include "Camera.h"
#include "Collision.h"
#include "Creature.h"
#include "Graphics.h"
#include "MapMgr.h"
#include "Navi.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Shape.h"
#include "gameflow.h"
#include "system.h"
#include "pc_p2_captain_policy.h"
#include "pc_p2_kurage_fsm.h"
#include "pc_p2_onikurage_mouth.h"
#include "pc_p2_sampled_clock.h"
#include "pc_p2_kurage_receiver.h"
#include "pc_p2_retail_player.h"
#include "pc_p2_kurage_visual.h"

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

namespace {
class LesserHost final : public Creature {
public:
    LesserHost() : Creature(nullptr) { }
    void refresh(Graphics&) override { }
    void doKill() override { }
};
struct Host {
    Shape* shape = nullptr;
    Shape* attackShape = nullptr;
    LesserHost owner;
    CollPart mouth{};
    Vector3f position;
    float height = 90.0f;
    float radius = 35.0f;
    Vector3f mouthJointTranslation;
    bool sourceJointAvailable = false;
    float phase = 0.0f;
    bool ready = false;
    bool alive = false;
    // The event clock is supplied by Kurage attack.bca.  The converted MOD is
    // deliberately a static attack pose; it does not provide skeletal BCA/BTK
    // playback.
    p2retail::Player attackPlayer;
    bool attackPlaying = false;
    bool sucking = false;
    // Test-only frame injection retained for focused unit/fixture seams.  It
    // never drives the live host update path.
    bool attackFrameSeam = false;
    float attackFrame = 0.0f;
    // Opt-in source flight-lifecycle authority (pc_p2_kurage_fsm.h).
    p2kurage::Fsm fsm;
    bool fsmEnabled = false;
    int fsmTicks = 0;
    int lastFsmState = -1;
    float fsmAltitude = 0.0f;
    float fsmHealth = 100.0f;
    bool ownerHasHealth = true;
    bool ownerBittered = false;
    int autoAdmissions = 0;
    p2kurage::KeyEvent pendingKey = p2kurage::KeyEvent::None;
    bool fsmMotionFinished = false;
    // Bounded animation-END fallback for states with no imported clip.
    int fsmMotionTimer = 0;
    // Real source animation clock (lane 08 #431 contract) for non-Attack states.
    p2sampled::Clock stateClock;
    bool stateClockActive = false;
    std::uint64_t clockCycle = 0;
    bool killed = false;
    // Host walkToTarget: Move patrols, Chase pursues the searched target.
    Vector3f spawnPos;
    Vector3f patrolTarget;
    bool hasPatrol = false;
    unsigned patrolState = 0x12345678u;
    float lastDistToGoal = 1e9f;
    // Greater (OniKurage, id 72) selection and the labelled captain-held seam.
    p2kurage::Variant variant = p2kurage::Variant::Lesser;
    bool captainHeld = false;
    bool captainSettled = true;
    float fallVelocity = 0.0f;
    // Lane-12 consumer path (Greater captain capture).
    P2CaptainPolicy* captainPolicy = nullptr;
    int captainTarget = -1;
    Navi* captainNavi = nullptr;
    p2onikurage::MouthSlots captainSlots;
    std::uint64_t captorEpoch = 0;
    bool captainCaptured = false;
};
Host sHost;
// Retail Lesser Kurage suckPikmin() queries collision part ID 'suck'; hire1 is
// a BMD visual joint, not the source suction collision location.
constexpr char kSourceSuctionPart[] = "suck";
constexpr char kVisualHireJoint[] = "hire1";
constexpr int kSourceSuctionJoint = 4;
constexpr float kSourceSuctionRadius = 15.0f;
// Bounded host approximation of Kurage::mAttackRadius for getSearchedTarget/
// isSuck; the source ProperParms value is asset-supplied and not yet imported.
constexpr float kSourceAttackRadius = 35.0f;
constexpr int kMaxAutoAdmissions = 10; // Kurage.h ip11 maxSuckPiki
constexpr float kFsmLiveHealth = 100.0f;
// Bounded host animation-END period (0.5 s at 60 Hz) used only while the
// converted MOD cannot supply a real motion-end event (#431 owns that bridge).
constexpr int kFsmMotionFrames = 30;
// p2retail::Player timers are animation frames. Kurage attack.bca is a 30 fps
// clip, so a real-time host advances the clock by delta * 30.
constexpr float kAttackFramesPerSecond = 30.0f;
// Bounded OniKurage StateDrop gravity (the source falls under creature physics;
// the host owns the integration until that seam exists).
constexpr float kDropGravity = 300.0f;
// Bounded host walkToTarget speed and patrol radius (source target is a random
// patrol point; the host owns the walk).
constexpr float kPatrolSpeed = 60.0f;
constexpr float kPatrolRadius = 150.0f;

// Source Kurage animation clips: durations from the ANF1 header (low 16 bits of
// the third uint32) and events from enemyanimmgr.txt.  KeyEvents are carried as
// the source event type ("2"/"3"/"1"); the attack clip stays on the retail
// Player that also owns the suction window.
p2sampled::Clip makeStateClip(const char* name, int duration, double loopBegin, double loopEnd,
                              std::initializer_list<std::pair<int, const char*>> events)
{
    p2sampled::Clip clip;
    clip.poses.name = name;
    clip.poses.count = 1;
    clip.poses.duration = duration;
    clip.loopBegin = loopBegin;
    clip.loopEnd = loopEnd;
    for (const auto& e : events) clip.events.push_back(p2sampled::Event{e.first, e.second});
    return clip;
}
const p2sampled::Clip* stateClip(int state)
{
    static const p2sampled::Clip clips[] = {
        makeStateClip("dead1.bca", 96, 0.0, -1.0, { { 33, "2" }, { 93, "3" } }), // 0 Dead
        makeStateClip("wait.bca", 35, 0.0, 34.0, {}),                            // 1 Wait
        makeStateClip("move1.bca", 60, 0.0, 59.0, {}),                           // 2 Move
        makeStateClip("move1.bca", 60, 0.0, 59.0, {}),                           // 3 Chase
        makeStateClip("", 0, 0.0, -1.0, {}),                                     // 4 Attack (Player)
        makeStateClip("type1.bca", 75, 0.0, -1.0, { { 32, "2" } }),              // 5 Fall
        makeStateClip("type2.bca", 20, 0.0, 19.0, {}),                           // 6 Land
        makeStateClip("wait.bca", 35, 0.0, 34.0, {}),                            // 7 Ground
        makeStateClip("type2.bca", 20, 0.0, 19.0, {}),                           // 8 TakeOff
        makeStateClip("flick1.bca", 60, 0.0, -1.0, { { 16, "2" } }),             // 9 FlyFlick
        makeStateClip("flick2.bca", 60, 0.0, -1.0, { { 20, "2" }, { 30, "3" } }),// 10 GroundFlick
    };
    if (state < 0 || state > 10) return nullptr;
    return clips[state].poses.name.empty() ? nullptr : &clips[state];
}

// Retail Kurage/attack.bca SHA-256 302660c6ba9c86fee11cc6aca98bd514e201a80d8530be3a5cce867a9dc74a4e.
// ANF1 is big-endian: loop attribute 2, duration 0x0078 (120), 12 joints.
// enemyanimmgr.txt supplies the source event table below.
const p2retail::Motion kAttackMotion{
    "attack.bca", "302660c6ba9c86fee11cc6aca98bd514e201a80d8530be3a5cce867a9dc74a4e",
    120, 2, {{37, 2}, {60, 0}, {67, 1}}
};

bool attackPoseActive()
{
    return sHost.attackFrameSeam
        ? sHost.attackFrame >= 37.0f && sHost.attackFrame < 67.0f
        : sHost.sucking;
}
bool suckingActive()
{
    return sHost.attackFrameSeam
        ? sHost.attackFrame >= 37.0f && sHost.attackFrame < 67.0f
        : sHost.sucking;
}

bool finite(float value) { return std::isfinite(value); }
bool valid(Vector3f value)
{
    return finite(value.x) && finite(value.y) && finite(value.z)
        && std::fabs(value.x) < 100000.0f && std::fabs(value.y) < 100000.0f
        && std::fabs(value.z) < 100000.0f;
}

void updateHostCollision()
{
    sHost.owner.mSRT.t = sHost.position;
    sHost.owner.mSRT.s.set(1.0f, 1.0f, 1.0f);
    sHost.owner.mSRT.r.set(0.0f, 0.0f, 0.0f);
    sHost.mouth.mPartType = PART_BoundSphere;
    sHost.mouth.mRadius = kSourceSuctionRadius;
    // enemycoll.txt binds suck to JNT1 index 4 with a zero offset.  The
    // converted preview MOD currently omits that JNT1 hierarchy, so the
    // bounded host uses the source offset from its origin until a collision-
    // tree world-matrix bridge can supply that joint's animated position.
    sHost.mouth.mCentre.set(sHost.position.x + sHost.mouthJointTranslation.x,
        sHost.position.y + sHost.mouthJointTranslation.y,
        sHost.position.z + sHost.mouthJointTranslation.z);
    sHost.mouth.mJointMatrix.makeIdentity();
}

// Bounded host approximation of Kurage::getSearchedTarget(altitude): return the
// first live Pikmin inside the source vertical suction window and attack
// radius whose sticker is not this owner.  View-angle rejection and per-family
// sight radius belong to the one-consumer receiver, not this scan.
Piki* findSuctionTarget()
{
    if (!pikiMgr || !sHost.ready) return nullptr;
    ObjectMgr* manager = static_cast<ObjectMgr*>(pikiMgr);
    const float radiusSqr = kSourceAttackRadius * kSourceAttackRadius;
    for (int it = manager->getFirst(); !manager->isDone(it); it = manager->getNext(it)) {
        Piki* piki = static_cast<Piki*>(manager->getCreature(it));
        if (!piki || !piki->isAlive() || piki->getStickObject() == &sHost.owner || !piki->mayIstick()) continue;
        if (!p2kurage::inSuctionWindow(sHost.position.y, 0.0f, piki->mSRT.t.y)) continue;
        const float dx = piki->mSRT.t.x - sHost.position.x;
        const float dz = piki->mSRT.t.z - sHost.position.z;
        if (dx * dx + dz * dz >= radiusSqr) continue;
        return piki;
    }
    return nullptr;
}

// Deterministic patrol point within kPatrolRadius of the spawn, for StateMove.
void pickPatrol()
{
    sHost.patrolState = sHost.patrolState * 1664525u + 1013904223u;
    const float u = float((sHost.patrolState >> 8) & 0xFFFFu) / 65535.0f;
    sHost.patrolState = sHost.patrolState * 1664525u + 1013904223u;
    const float v = float((sHost.patrolState >> 8) & 0xFFFFu) / 65535.0f;
    const float angle = u * 6.2831853f;
    const float dist = 40.0f + v * kPatrolRadius;
    sHost.patrolTarget.set(sHost.spawnPos.x + std::cos(angle) * dist, 0.0f,
        sHost.spawnPos.z + std::sin(angle) * dist);
}
}

void pc_p2_kurage_arena_reset()
{
    // Detach while the concrete host and its CollPart still exist.
    pc_p2_kurage_receiver_owner_invalidated(&sHost.owner);
    sHost.shape = nullptr; sHost.ready = sHost.alive = false; sHost.phase = 0.0f;
    sHost.attackPlayer.cancel(); sHost.attackPlaying = sHost.sucking = false;
    sHost.attackFrameSeam = false; sHost.attackFrame = 0.0f;
    sHost.fsmEnabled = false; sHost.fsmTicks = 0; sHost.lastFsmState = -1; sHost.fsmAltitude = 0.0f;
    sHost.fsmHealth = kFsmLiveHealth; sHost.ownerHasHealth = true; sHost.ownerBittered = false;
    sHost.autoAdmissions = 0; sHost.pendingKey = p2kurage::KeyEvent::None; sHost.fsmMotionFinished = false; sHost.fsmMotionTimer = 0;
    sHost.stateClock.cancel(); sHost.stateClockActive = false; sHost.clockCycle = 0; sHost.killed = false;
    sHost.hasPatrol = false; sHost.patrolState = 0x12345678u; sHost.lastDistToGoal = 1e9f;
    sHost.variant = p2kurage::Variant::Lesser; sHost.captainHeld = false; sHost.captainSettled = true; sHost.fallVelocity = 0.0f;
    sHost.captainPolicy = nullptr; sHost.captainTarget = -1; sHost.captainNavi = nullptr;
    sHost.captainSlots.reset(); sHost.captorEpoch = 0; sHost.captainCaptured = false;
}

bool pc_p2_kurage_arena_setup(const char* profilePath)
{
    pc_p2_kurage_arena_reset();
    if (!profilePath || !*profilePath) return false;
    std::ifstream profile(profilePath);
    std::string header;
    if (!(profile >> header) || header != "P2_KURAGE_ARENA_1") return false;
    Host parsed;
    std::string key;
    if (!(profile >> key >> parsed.position.x >> parsed.position.y >> parsed.position.z)
        || key != "position" || !valid(parsed.position)) return false;
    if (!(profile >> key >> parsed.height >> parsed.radius)
        || key != "params" || !finite(parsed.height) || !finite(parsed.radius)
        || parsed.height <= 0.0f || parsed.height > 1000.0f || parsed.radius < 0.0f
        || parsed.radius > 1000.0f) return false;
    if (profile >> key) return false;
    if (!pc_p2_kurage_visual_setup()) return false;
    parsed.shape = pc_p2_kurage_visual_wait_shape();
    parsed.attackShape = pc_p2_kurage_visual_attack_shape();
    if (!parsed.shape || !parsed.attackShape) return false;
    parsed.sourceJointAvailable = parsed.shape->mJointCount > kSourceSuctionJoint;
    if (parsed.sourceJointAvailable)
        parsed.mouthJointTranslation = parsed.shape->mJointList[kSourceSuctionJoint].mTranslation;
    else
        parsed.mouthJointTranslation.set(0.0f, 0.0f, 0.0f);
    parsed.ready = parsed.alive = true;
    sHost.shape = parsed.shape; sHost.attackShape = parsed.attackShape; sHost.position = parsed.position; sHost.height = parsed.height;
    sHost.radius = parsed.radius; sHost.mouthJointTranslation = parsed.mouthJointTranslation;
    sHost.sourceJointAvailable = parsed.sourceJointAvailable;
    sHost.spawnPos = sHost.position;
    sHost.phase = 0.0f; sHost.ready = sHost.alive = true;
    sHost.fsmEnabled = false; sHost.fsmTicks = 0; sHost.lastFsmState = -1; sHost.fsmAltitude = 0.0f;
    sHost.fsmHealth = kFsmLiveHealth; sHost.ownerHasHealth = true; sHost.ownerBittered = false;
    sHost.autoAdmissions = 0; sHost.pendingKey = p2kurage::KeyEvent::None; sHost.fsmMotionFinished = false; sHost.fsmMotionTimer = 0;
    sHost.stateClock.cancel(); sHost.stateClockActive = false; sHost.clockCycle = 0; sHost.killed = false;
    sHost.hasPatrol = false; sHost.patrolState = 0x12345678u; sHost.lastDistToGoal = 1e9f;
    sHost.variant = p2kurage::Variant::Lesser; sHost.captainHeld = false; sHost.captainSettled = true; sHost.fallVelocity = 0.0f;
    sHost.captainPolicy = nullptr; sHost.captainTarget = -1; sHost.captainNavi = nullptr;
    sHost.captainSlots.reset(); sHost.captorEpoch = 0; sHost.captainCaptured = false;
    sHost.fsm = p2kurage::Fsm(); sHost.fsm.spawn();
    sHost.owner.mStickListHead = nullptr;
    updateHostCollision();
    std::printf("P2_KURAGE_ARENA_READY species=Kurage id=57 visual=converted_wait source_part=%s joint=%d radius=%.1f offset=0,0,0 joint_translation=%s visual_joint=%s host_receiver=bounded\n", kSourceSuctionPart, kSourceSuctionJoint, kSourceSuctionRadius, sHost.sourceJointAvailable ? "wait_pose" : "unavailable_origin", kVisualHireJoint);
    return true;
}

bool pc_p2_kurage_arena_update(float delta, bool ownerAlive)
{
    if (!sHost.ready || !sHost.alive || !finite(delta) || delta < 0.0f || delta > 1.0f) return false;
    if (!ownerAlive) {
        // This private host is the lifecycle authority for its bounded receiver.
        // Release while the concrete owner and mouth still exist; callers must
        // not substitute this for P2's full Kurage health/bitter/FSM path.
        if (sHost.captainCaptured && sHost.captainPolicy) {
            sHost.captainPolicy->releaseCaptured(sHost.captainTarget, sHost.captorEpoch);
            sHost.captainSlots.onDeath();
            sHost.captainCaptured = false;
        }
        pc_p2_kurage_receiver_update(0.0f, false, true, false);
        return false;
    }
    if (sHost.fsmEnabled) {
        // Source Kurage StateWait/Move/Chase/Attack vertical authority.  The
        // bounded host supplies real map height/position and the real attack.bca
        // event clock; target facts come from a live Pikmin scan, not a
        // fabricated target.
        const float mapY = mapMgr ? mapMgr->getMinY(sHost.position.x, sHost.position.z, false) : 0.0f;
        p2kurage::In in;
        in.deltaTime = delta;
        in.health = sHost.fsmHealth;
        // Mouth-travel Pikmin are not body-stuck; only stomach-attached ones
        // count toward the source fall/flick threshold.
        in.stuckPikminCount = pc_p2_kurage_receiver_stomach_count();
        in.isFlying = true;
        in.mapY = mapY;
        in.positionY = sHost.position.y;
        in.distToTargetXZ = sHost.lastDistToGoal;
        const bool captainRoute = sHost.variant == p2kurage::Variant::Greater
            && sHost.captainPolicy && sHost.captainTarget >= 0 && sHost.captainNavi;
        const bool captainInRange = captainRoute && !sHost.captainCaptured
            && sHost.captainNavi->isAlive()
            && p2kurage::naviSearchAdmit(true, false, sHost.captainNavi->mSRT.t.y, sHost.position.y, 0.0f,
                (sHost.captainNavi->mSRT.t.x - sHost.position.x) * (sHost.captainNavi->mSRT.t.x - sHost.position.x)
                + (sHost.captainNavi->mSRT.t.z - sHost.position.z) * (sHost.captainNavi->mSRT.t.z - sHost.position.z),
                kSourceAttackRadius);
        in.targetFound = findSuctionTarget() != nullptr || pc_p2_kurage_receiver_count() > 0 || captainInRange;
        in.suckTarget = in.targetFound;
        in.suckAny = in.targetFound;
        in.naviSucked = captainRoute ? sHost.captainCaptured : sHost.captainHeld;
        in.naviSuckFinished = captainRoute ? sHost.captainSlots.isFinishNaviSuck() : sHost.captainSettled;
        in.velocityY = -sHost.fallVelocity;
        in.motionFrame = sHost.attackPlaying ? sHost.attackPlayer.frame() : 0.0f;
        // Real source animation clock (lane 08 #431 contract) for the current
        // non-Attack state: durations/events transcribed from the source BCA
        // headers and enemyanimmgr.txt.
        bool clockMotionEnd = false;
        p2kurage::KeyEvent clockKey = p2kurage::KeyEvent::None;
        if (sHost.stateClockActive) {
            const p2sampled::Batch batch = sHost.stateClock.advance(delta * kAttackFramesPerSecond);
            for (const p2sampled::Occurrence& occ : batch.events) {
                if (occ.key == "2") clockKey = p2kurage::KeyEvent::Key2;
                else if (occ.key == "3") clockKey = p2kurage::KeyEvent::Key3;
                else if (occ.key == "1") clockKey = p2kurage::KeyEvent::Key1;
            }
            if (sHost.stateClock.finished() || sHost.stateClock.cycle() != sHost.clockCycle) clockMotionEnd = true;
            sHost.clockCycle = sHost.stateClock.cycle();
        }
        // Bounded animation-END fallback for states with no imported clip.
        bool motionEnd = false;
        if (!sHost.attackPlaying && !sHost.stateClockActive
            && ++sHost.fsmMotionTimer >= kFsmMotionFrames) {
            sHost.fsmMotionTimer = 0;
            motionEnd = true;
        }
        in.motionFinished = sHost.fsmMotionFinished || motionEnd || clockMotionEnd;
        in.keyEvent = clockKey != p2kurage::KeyEvent::None ? clockKey : sHost.pendingKey;
        sHost.pendingKey = p2kurage::KeyEvent::None;
        sHost.fsmMotionFinished = false;

        const p2kurage::Out out = sHost.fsm.tick(in);
        if (out.state == p2kurage::State::Drop && sHost.variant == p2kurage::Variant::Greater) {
            // Source StateDrop::exec is a pure fall (no setHeightVelocity); the
            // host integrates gravity until dropShouldFinish or the bounded
            // motion-END lands the body.
            sHost.fallVelocity += kDropGravity * delta;
            sHost.position.y -= sHost.fallVelocity * delta;
        } else {
            sHost.fallVelocity = 0.0f;
            sHost.position.y += out.heightVelocity * delta;
        }
        // Host walkToTarget: Move patrols, Chase pursues the searched target.
        // distToTargetXZ (next tick) drives the source Move arrival.
        {
            Vector3f goal;
            bool haveGoal = false;
            if (out.state == p2kurage::State::Move) {
                if (!sHost.hasPatrol) { pickPatrol(); sHost.hasPatrol = true; }
                goal = sHost.patrolTarget;
                haveGoal = true;
            } else if (out.state == p2kurage::State::Chase) {
                Piki* chase = findSuctionTarget();
                if (chase) { goal = chase->mSRT.t; haveGoal = true; }
                else if (sHost.captainNavi && sHost.captainNavi->isAlive()) { goal = sHost.captainNavi->mSRT.t; haveGoal = true; }
            } else {
                sHost.hasPatrol = false;
            }
            if (haveGoal) {
                const float dx = goal.x - sHost.position.x;
                const float dz = goal.z - sHost.position.z;
                const float dist = std::sqrt(dx * dx + dz * dz);
                sHost.lastDistToGoal = dist;
                if (dist > 1.0f && finite(delta)) {
                    float step = kPatrolSpeed * delta;
                    if (step > dist) step = dist;
                    sHost.position.x += dx / dist * step;
                    sHost.position.z += dz / dist * step;
                }
            } else {
                sHost.lastDistToGoal = 1e9f;
            }
        }
        sHost.fsmAltitude = out.altitude;
        if ((int)out.state != sHost.lastFsmState) {
            sHost.lastFsmState = (int)out.state;
            const p2sampled::Clip* clip = stateClip((int)out.state);
            if (clip && out.state != p2kurage::State::Attack) {
                sHost.stateClock.start(*clip);
                sHost.stateClockActive = true;
                sHost.clockCycle = 0;
            } else {
                sHost.stateClock.cancel();
                sHost.stateClockActive = false;
            }
            std::printf("P2_KURAGE_FSM state=%d motion=%d altitude=%.3f vy=%.3f ticks=%d\n",
                (int)out.state, (int)out.motion, out.altitude, out.heightVelocity, sHost.fsmTicks);
        }
        // Entering the source Attack state starts the retail attack.bca clock.
        if (out.state == p2kurage::State::Attack && out.motionChanged && !sHost.attackPlaying) {
            if (pc_p2_kurage_arena_begin_attack()) { sHost.autoAdmissions = 0; sHost.fsmMotionTimer = 0; sHost.fallVelocity = 0.0f; }
        }
        // The clock supplies KeyEvent 2/1 and the open suction interval.  The
        // retail Player advances in animation frames, not seconds.
        if (sHost.attackPlaying) pc_p2_kurage_arena_tick_attack(delta * kAttackFramesPerSecond);
        if (!valid(sHost.position)) { sHost.alive = false; return false; }
        updateHostCollision();
        // Source Attack suction: the ordinary Attack state autonomously admits
        // eligible Pikmin while its window is open.
        if ((out.isSucking || sHost.sucking)
            && pc_p2_kurage_receiver_scan_admit(0.0f, kSourceAttackRadius, kMaxAutoAdmissions, true) > 0)
            ++sHost.autoAdmissions;
        if (captainRoute) {
            // OniKurage::suckNavi during the source Attack suction window.
            if (!sHost.captainCaptured && out.state == p2kurage::State::Attack
                && (out.isSucking || sHost.sucking) && sHost.captainNavi->isAlive()) {
                const Vector3f naviPos = sHost.captainNavi->mSRT.t;
                const float dx = naviPos.x - sHost.position.x;
                const float dz = naviPos.z - sHost.position.z;
                const bool eligible = p2kurage::naviSearchAdmit(true, false, naviPos.y,
                    sHost.position.y, 0.0f, dx * dx + dz * dz, kSourceAttackRadius);
                if (eligible && sHost.captainSlots.capture(sHost.captainTarget, true)) {
                    if (++sHost.captorEpoch == 0) sHost.captorEpoch = 1;
                    if (sHost.captainPolicy->capture(sHost.captainTarget, sHost.captorEpoch)) {
                        sHost.captainCaptured = true;
                        std::printf("P2_KURAGE_CAPTAIN_CAPTURED captain=%d epoch=%llu\n",
                            sHost.captainTarget, (unsigned long long)sHost.captorEpoch);
                    } else {
                        sHost.captainSlots.onDeath(); // policy refused (last control)
                    }
                }
            }
            if (sHost.captainCaptured) {
                for (int slot = 0; slot < p2onikurage::kMouthSlotCount; ++slot)
                    sHost.captainSlots.advanceDefaultOffset(slot);
                // Bounded attach: pin the held captain to the mouth-slot offset.
                // The source keeps it held through Drop/Land/Ground and releases
                // it at the GroundFlick flickNearby (KEY3), not at Drop exit.
                const p2onikurage::Slot& held = sHost.captainSlots.slots()[0];
                Vector3f target = sHost.mouth.mCentre;
                target.x += held.offset.x;
                target.y += held.offset.y;
                target.z += held.offset.z;
                if (valid(target)) sHost.captainNavi->resetPosition(target);
            }
        }
        if (out.flickStick) {
            // KurageState flickStickPikmin: eject Pikmin the Kurage holds.
            const int released = pc_p2_kurage_receiver_count();
            pc_p2_kurage_receiver_release_all();
            std::printf("P2_KURAGE_FLICK_STICK released=%d\n", released);
        }
        if (out.flickNearby) {
            // KurageState GroundFlick KEY3: flickNearbyNavi releases the held
            // captain (InteractFlick + InteractBomb) away from the body, and
            // flickNearbyPikmin clears nearby Pikmin.
            std::printf("P2_KURAGE_FLICK_NEARBY\n");
            if (sHost.captainCaptured && sHost.captainPolicy && sHost.captainNavi) {
                const float dx = sHost.captainNavi->mSRT.t.x - sHost.position.x;
                const float dz = sHost.captainNavi->mSRT.t.z - sHost.position.z;
                const float len = std::sqrt(dx * dx + dz * dz);
                if (len > 1e-6f && valid(sHost.captainNavi->mSRT.t)) {
                    Vector3f flung = sHost.captainNavi->mSRT.t;
                    flung.x += dx / len * p2onikurage::kFlickSeparation;
                    flung.z += dz / len * p2onikurage::kFlickSeparation;
                    if (valid(flung)) sHost.captainNavi->resetPosition(flung);
                }
                sHost.captainPolicy->releaseCaptured(sHost.captainTarget, sHost.captorEpoch);
                std::printf("P2_KURAGE_CAPTAIN_RELEASED captain=%d state=%d\n",
                    sHost.captainTarget, (int)out.state);
                sHost.captainSlots.onDeath();
                sHost.captainCaptured = false;
            }
        }
        if (out.downEffect) std::printf("P2_KURAGE_DOWN_EFFECT\n");
        if (out.flickEffect) std::printf("P2_KURAGE_FLICK_EFFECT\n");
        if (out.deathProcedure) std::printf("P2_KURAGE_DEATH_PROCEDURE\n");
        if (out.bodyBomb) std::printf("P2_KURAGE_BODY_BOMB\n");
        if (out.kill && !sHost.killed) {
            // KurageState Dead END: natural death releases owned Pikmin and any
            // held captain, then the host leaves the field.
            sHost.killed = true;
            if (sHost.captainCaptured && sHost.captainPolicy) {
                sHost.captainPolicy->releaseCaptured(sHost.captainTarget, sHost.captorEpoch);
                sHost.captainSlots.onDeath();
                sHost.captainCaptured = false;
            }
            pc_p2_kurage_receiver_release_all();
            sHost.alive = false;
            std::printf("P2_KURAGE_KILL\n");
            std::fflush(stdout);
        }
        sHost.fsmTicks++;
        pc_p2_kurage_receiver_update(delta, true, sHost.ownerHasHealth, sHost.ownerBittered);
        return true;
    }
    sHost.phase += delta * 0.8f;
    if (!finite(sHost.phase)) { sHost.alive = false; return false; }
    sHost.position.y += std::sin(sHost.phase) * sHost.height * delta;
    if (!valid(sHost.position)) { sHost.alive = false; return false; }
    updateHostCollision();
    // Ordering contract: the Piki frame observes the previous receiver
    // velocity; this host tick refreshes the moving `suck` target and drives
    // the following frame.  Piki::doAI suppresses ordinary action writes for
    // receiver-owned Piki.  Health/bitter are intentionally unavailable on
    // this bounded host and remain the source-adapter defaults here.
    pc_p2_kurage_receiver_update(delta, true, true, false);
    return true;
}

bool pc_p2_kurage_arena_begin_attack()
{
    if (!sHost.ready || !sHost.alive || !sHost.attackPlayer.start(kAttackMotion)) return false;
    sHost.attackFrameSeam = false;
    sHost.attackFrame = 0.0f;
    sHost.attackPlaying = true;
    sHost.sucking = false;
    return true;
}

bool pc_p2_kurage_arena_tick_attack(float delta)
{
    if (!sHost.ready || !sHost.alive || !sHost.attackPlaying) return false;
    const auto result = sHost.attackPlayer.advance(delta, [](const p2retail::Event& event) {
        if (event.type == 2) {
            sHost.sucking = true;
            sHost.pendingKey = p2kurage::KeyEvent::Key2; // Kurage KEYEVENT_2 suck start
        } else if (event.type == 1 || event.type == 1000) {
            // Kurage StateAttack leaves its sucking interval on type 1.  This
            // bounded static-pose host closes there instead of re-looping 60..67.
            sHost.sucking = false;
            sHost.attackPlaying = false;
            sHost.attackPlayer.cancel();
            sHost.pendingKey = p2kurage::KeyEvent::Key1; // Kurage KEYEVENT_1 suck end
            sHost.fsmMotionFinished = true;
        }
    });
    if (result == p2retail::Update::Ok && sHost.attackPlayer.completed()) sHost.fsmMotionFinished = true;
    return result == p2retail::Update::Ok || result == p2retail::Update::Replaced;
}

Creature* pc_p2_kurage_arena_owner()
{
    return sHost.ready && sHost.alive ? &sHost.owner : nullptr;
}

CollPart* pc_p2_kurage_arena_mouth()
{
    return sHost.ready && sHost.alive ? &sHost.mouth : nullptr;
}

int pc_p2_kurage_arena_scan_admit(float verticalOffset, float attackRadius, int maxAdmissions, bool admitEligible)
{
    // Retail attack.bca events: 37=KEYEVENT_2 starts suck, 67=type1 ends it.
    if (!sHost.ready || !sHost.alive || !suckingActive()) return 0;
    return pc_p2_kurage_receiver_scan_admit(verticalOffset, attackRadius, maxAdmissions, admitEligible);
}
void pc_p2_kurage_arena_set_attack_frame(float frame)
{
    sHost.attackFrameSeam = true;
    sHost.attackFrame = finite(frame) && frame >= 0.0f ? frame : 0.0f;
}
bool pc_p2_kurage_arena_attack_pose_active()
{
    return sHost.ready && attackPoseActive();
}

void pc_p2_kurage_arena_fsm_enable(bool enable)
{
    if (sHost.ready && sHost.alive) sHost.fsmEnabled = enable;
}
bool pc_p2_kurage_arena_fsm_enabled()
{
    return sHost.ready && sHost.alive && sHost.fsmEnabled;
}
int pc_p2_kurage_arena_fsm_state()
{
    return sHost.ready ? (int)sHost.fsm.state() : -1;
}
float pc_p2_kurage_arena_fsm_altitude()
{
    return sHost.fsmAltitude;
}
void pc_p2_kurage_arena_set_owner_facts(bool hasHealth, bool bittered)
{
    sHost.ownerHasHealth = hasHealth;
    sHost.ownerBittered = bittered;
    sHost.fsmHealth = hasHealth ? kFsmLiveHealth : 0.0f;
}
int pc_p2_kurage_arena_auto_admissions()
{
    return sHost.autoAdmissions;
}

void pc_p2_kurage_arena_set_greater(bool greater)
{
    if (!sHost.ready || !sHost.alive) return;
    sHost.variant = greater ? p2kurage::Variant::Greater : p2kurage::Variant::Lesser;
    sHost.fsm = p2kurage::Fsm(p2kurage::Parms(), sHost.variant);
    sHost.fsm.spawn();
    sHost.lastFsmState = -1;
    sHost.fallVelocity = 0.0f;
    std::printf("P2_KURAGE_ARENA_VARIANT variant=%s id=%d\n", greater ? "Greater" : "Lesser", greater ? 72 : 57);
}
int pc_p2_kurage_arena_fsm_variant()
{
    return sHost.variant == p2kurage::Variant::Greater ? 72 : 57;
}
void pc_p2_kurage_arena_set_captain_held(bool held)
{
    sHost.captainHeld = held;
    sHost.captainSettled = true;
}
void pc_p2_kurage_arena_set_captain_target(P2CaptainPolicy* policy, int captain, Navi* navi)
{
    sHost.captainPolicy = policy;
    sHost.captainTarget = captain;
    sHost.captainNavi = navi;
    sHost.captainSlots.reset();
    sHost.captainCaptured = false;
}
int pc_p2_kurage_arena_captain_occupied()
{
    return sHost.captainSlots.occupiedCount();
}
bool pc_p2_kurage_arena_captain_captured()
{
    return sHost.captainCaptured;
}
bool pc_p2_kurage_arena_killed()
{
    return sHost.killed;
}

void pc_p2_kurage_arena_draw(Graphics& gfx)
{
    if (!sHost.ready || !sHost.alive || !sHost.shape || !gfx.mCamera) return;
    gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx, gfx.mCamera->mFov,
        gfx.mCamera->mAspectRatio, gfx.mCamera->mNear, gfx.mCamera->mFar, 1.f);
    gfx.useMaterial(nullptr);
    gfx.setDepth(true);
    Matrix4f world;
    world.makeIdentity();
    world.mMtx[0][3] = sHost.position.x;
    world.mMtx[1][3] = sHost.position.y;
    world.mMtx[2][3] = sHost.position.z;
    Matrix4f matrix;
    gfx.mCamera->mLookAtMtx.multiplyTo(world, matrix);
    Shape* shape = nullptr;
    if (sHost.fsmEnabled) {
        const char* base = pc_p2_kurage_visual_motion_for_state(sHost.lastFsmState);
        const bool greater = sHost.variant == p2kurage::Variant::Greater;
        shape = pc_p2_kurage_visual_shape_variant(base, greater);
        static const char* lastBase = nullptr;
        static int lastVariant = -1;
        if (base && (base != lastBase || int(greater) != lastVariant)) {
            lastBase = base;
            lastVariant = int(greater);
            std::printf("P2_KURAGE_POSE motion=%s variant=%s available=%d\n", base,
                greater ? "Greater" : "Lesser", int(shape != nullptr));
            std::fflush(stdout);
        }
    }
    if (!shape) shape = attackPoseActive() ? sHost.attackShape : sHost.shape;
    shape->updateAnim(gfx, matrix, nullptr, nullptr);
    shape->drawshape(gfx, *gfx.mCamera, nullptr);
    static bool logged = false;
    if (!logged) { std::printf("P2_KURAGE_DRAW position=%.2f,%.2f,%.2f\n", sHost.position.x, sHost.position.y, sHost.position.z); logged = true; }
}
