// ADDITIVE-SCOPE GUARD (#678): standalone contract builds define
// P2_DAMAGUMO_BINDING_STANDALONE to compile only the engine-free
// profile/mesh/slot binding below. Production builds (macro undefined)
// compile the original file content that follows, byte-identical.
#ifndef P2_DAMAGUMO_BINDING_STANDALONE
// Family-owned snagret-family source behavior for the batch-3 Chappy placement
// vehicle: Segmented Crawbster (DangoMushi, EnemyID 94). Implements the source
// DangoMushiState.cpp segmented roller FSM: Stay -> Appear (fly) -> Wait ->
// Move -> Attack (ball roll) -> Turn (crash) -> Recover -> Flick (attack_2) ->
// Wait, plus Dead. Source revision
// 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms from
// experimental/pikmin2_snagret_assets.py (GPVE01 revision 0, DangoMushi
// DISC_PARMS). The source states, animation IDs and key-event streams are the
// audited disc values (DangoMushi.h:23-35, DangoMushi.h:210-222,
// EXPECTED_EVENTS['DangoMushi']).
//
// DangoMushi is a standalone `EnemyBase`/`EnemyBlendAnimatorBase` boss, not a
// snagret and not a `ChappyBase`; it shares this batch-3 host only as a
// placement vehicle (expected native type TEKI_Chappy) so the source FSM can
// run on the P1 engine.
//
// Port adaptations (recorded, not retail-faithful):
//   * The roll contact (source Obj::collisionCallback InteractPress while
//     mIsRolling) has no P1 collision-callback path here. It is resolved as a
//     single InteractFlick knockback+damage on the first Pikmin/Navi inside the
//     source fp22=100 hit radius after the roll starts, once per roll, instead
//     of every frame; the source InteractPress crush is not representable.
//   * The source only enters StateTurn from Obj::wallCallback (roll speed > 100
//     and >30 deg into a wall normal). The P1 host exposes no wall normal, so a
//     roll enters Turn when it leaves the source fp09=150 territory or after
//     the bounded roll timeout; the crash effects are approximated. The Turn
//     LOOP_START..key-3 vulnerability window (DangoMushiState.cpp:530) is now
//     applied: pc_p2_dangomushi_invulnerable rejects attack/bomb damage outside
//     the stickable window, exposed through the shared tekiinteraction hooks.
//   * The Flick arm sweep (Obj::flickHandCollision) is resolved as one
//     InteractFlick per Flick state at the attack_2 KEYEVENT_2 arm-swing frame
//     (26), not per frame; the source Navi wither and Purple-crab rules are not
//     representable.
//   * The P2 ModelHidden state flag and the dangomushi.brk material loop
//     (DangoMushi.cpp:106-134) are P2-only and are not reproduced. The falling
//     Rock/Egg child spawner (DangoMushi.cpp:649-776) is realized by hosting the
//     lane-20 P2RockHazard / P2Egg policies (see the DANGO_TURN rain below).
//   * Walk uses the source fp08=0.05 turn rate clamped to fp28=5 deg; the roll
//     uses proper fp02=0.03 / fp03=3 deg and fp01=200. Target search is a full
//     hemisphere (the source fp13 view-angle gate is not applied). When the
//     installed p2-snagret-bank.txt is absent the audited retail event frames
//     are used with 1 s fallback clip durations.
// No other lane's module is modified; every hook is a no-op for unregistered
// actors.
#include "pc_p2_dangomushi.h"
#include "pc_p2_dangomushi_hazard.h"
#include "pc_p2_egg_hazard.h"
#include "pc_p2_rock_hazard.h"
#include "pc_p2_rock_host.h"
#include "teki.h"
#include "Interactions.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Generator.h"
#include "gameflow.h"
#include "GameStat.h"
#include "Creature.h"
#include "MapMgr.h"
#include "ItemMgr.h"
#include "Pellet.h"
#include "ObjType.h"
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <set>
#include <string>
#include <vector>

namespace {
enum State {
    DANGO_DEAD = 0,
    DANGO_STAY = 1,
    DANGO_APPEAR = 2,
    DANGO_WAIT = 3,
    DANGO_MOVE = 4,
    DANGO_ATTACK = 5,
    DANGO_TURN = 6,
    DANGO_RECOVER = 7,
    DANGO_FLICK = 8,
};

const char* stateName(State s) {
    switch (s) {
    case DANGO_DEAD: return "dead";
    case DANGO_STAY: return "stay";
    case DANGO_APPEAR: return "appear";
    case DANGO_WAIT: return "wait";
    case DANGO_MOVE: return "move";
    case DANGO_ATTACK: return "attack";
    case DANGO_TURN: return "turn";
    case DANGO_RECOVER: return "recover";
    case DANGO_FLICK: return "flick";
    default: return "null";
    }
}

// Source enemyparm.txt retail values (snagret manifest, DangoMushi general).
constexpr float LIFE = 3000.0f;              // fp00
constexpr float MOVE_SPEED = 50.0f;          // fp06
constexpr float TERRITORY = 150.0f;          // fp09 territory radius
constexpr float HOME_RADIUS = 100.0f;        // fp10 home radius
constexpr float PRIVATE_RADIUS = 150.0f;     // fp11 Stay wake distance
constexpr float SIGHT = 500.0f;              // fp12 sight radius
constexpr float ATTACK_RANGE = 300.0f;       // fp20 max attack range
constexpr float ATTACK_ANGLE = 0.261799f;    // fp21 15 deg
constexpr float ATTACK_DAMAGE = 10.0f;       // fp24 attack power
constexpr float SHAKE_KNOCKBACK = 200.0f;    // fp17 shake knockback
constexpr float CONTACT_RADIUS = 100.0f;     // fp22 attack hit radius (roll body)
constexpr float WALK_TURN_RATE = 0.05f;      // fp08 rotation speed rate
constexpr float WALK_MAX_TURN = 0.0872665f;  // fp28 5 deg
// Source proper-parm retail values (DangoMushi proper block).
constexpr float ROLL_SPEED = 200.0f;         // fp01 rolling movement speed
constexpr float ROLL_TURN_ACCEL = 0.03f;     // fp02 rolling rotation speed rate
constexpr float ROLL_TURN_SPEED = 0.0523599f; // fp03 rolling max turn 3 deg
constexpr float FLIP_TIME = 7.5f;            // fp10 (disc omits it; header default)
// Source state timers (DangoMushiState.cpp).
constexpr float WAIT_TIME = 3.0f;            // StateWait::exec 3.0f
constexpr float MOVE_TIMEOUT = 10.0f;        // StateMove::exec 10.0f
constexpr float ATTACK_TIMEOUT = 15.0f;      // StateAttack::exec 15.0f
constexpr float MOVE_ARRIVE = 25.0f;         // sqrt(625) Obj::isReachedTarget
// Port arm-sweep radius: the source hand_R contact test needs the P2 model
// joints; a flat radius is the documented port value.
constexpr float FLICK_RADIUS = 150.0f;
// Audited retail event frames (EXPECTED_EVENTS['DangoMushi']); used when the
// installed bank is absent.
constexpr int FALLBACK_ROLL_START = 23;      // attack 23:4 KEYEVENT_4
constexpr int FALLBACK_FLICK_START = 26;     // attack_2 26:2 KEYEVENT_2
// Lane-25 real rain host slots (source reserves 30 Rocks / 10 Eggs per
// Crawbster; 16 host slots with reuse of dead rocks is the documented host
// limit, matching the lane-20 P2RockHazardPool capacity).
constexpr int kRainRockSlots = 16;

struct Clip {
    std::string name;
    float duration = 1.0f;
    bool loop = false;
    std::vector<std::pair<int, int>> events;
};

struct Dango {
    State state = DANGO_STAY;
    float stateTime = 0.0f;
    float heading = 0.0f;
    Vector3f home;
    Vector3f moveTarget;
    bool rolling = false;
    bool rollHit = false;
    bool armSwinging = false;
    std::set<int> firedEvents;
    std::string clip = "fly";
    float phase = 0.0f;
    bool deadLogged = false;
    float logTimer = 0.0f;
    // Lane-25 hazard policy (#376): Turn vulnerability window + Rock/Egg rain.
    P2DangoMushiHazardPolicy hazard;
    bool turnJustEntered = false;
    bool hazardWindowLogged = false;
    int hazardRocks = 0;
    // Applied vulnerability state: true only inside the Turn stickable window.
    // Outside it pc_p2_dangomushi_invulnerable rejects attack/bomb damage.
    bool stickable = false;
    bool attackRejectedLogged = false;
    // Lane-25 real rain host (#174/#376): the hazard policy's Rock/Egg decisions
    // realized as falling Rock hazards (lane-20 P2RockHazard) and a real Egg
    // (lane-20 P2Egg) whose break births real P1 pellets/nectar. The policies are
    // consumed unchanged; this state only hosts them.
    P2RockHazard rainRock[kRainRockSlots];
    bool rainRockUsed[kRainRockSlots] = {};
    float rainRockDeadTimer[kRainRockSlots] = {};
    float rainRockMaxLife[kRainRockSlots] = {};
    float rainRockAge[kRainRockSlots] = {};
    bool rainRockLifetimeExpired[kRainRockSlots] = {};
    P2RockHazardPhase rainRockPrev[kRainRockSlots] = {};
    std::set<std::uint64_t> rainContacts[kRainRockSlots];
    std::uint64_t rainRockSelf = 1;
    P2Egg rainEgg;
    bool rainEggActive = false;
    P2EggVec3 rainEggPos;
    p2rockhost::ScriptRng rainRng;
    double rainDebt = 0.0;
};

std::map<PelletView*, Dango> actors;
std::map<std::string, Clip> clips;
int rollStartFrame = FALLBACK_ROLL_START;
int flickStartFrame = FALLBACK_FLICK_START;
bool ready = false;

float wrapPi(float a) {
    while (a > PI) a -= TAU;
    while (a < -PI) a += TAU;
    return a;
}
float distXZ(const Vector3f& a, const Vector3f& b) {
    const float dx = a.x - b.x, dz = a.z - b.z;
    return std::sqrt(dx * dx + dz * dz);
}
float clipDuration(const std::string& name) {
    auto it = clips.find(name);
    return it == clips.end() ? 1.0f : it->second.duration;
}
bool clipLoops(const std::string& name) {
    auto it = clips.find(name);
    return it != clips.end() && it->second.loop;
}
int eventFrame(const char* name, int type) {
    auto it = clips.find(name);
    if (it != clips.end()) {
        for (const auto& event : it->second.events)
            if (event.second == type) return event.first;
    }
    return -1;
}

Creature* nearestTarget(const Vector3f& pos, float radius) {
    Creature* best = nullptr;
    float bestSq = radius * radius;
    if (naviMgr) {
        Navi* n = naviMgr->getNavi();
        if (n && n->isAlive()) {
            const Vector3f p = n->getPosition();
            const float dx = p.x - pos.x, dz = p.z - pos.z;
            const float d = dx * dx + dz * dz;
            if (d < bestSq) { bestSq = d; best = n; }
        }
    }
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive()) continue;
            const Vector3f q = p->getPosition();
            const float dx = q.x - pos.x, dz = q.z - pos.z;
            const float d = dx * dx + dz * dz;
            if (d < bestSq) { bestSq = d; best = p; }
        }
    }
    return best;
}

void stop(BTeki* a) {
    a->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
    a->mVelocity.x = 0.0f;
    a->mVelocity.z = 0.0f;
}

// Source Obj::turnByAngle: clamp(angleDist * turnSpeed, maxTurnAngle).
void turnAndMove(BTeki* a, Dango& s, const Vector3f& target,
                 float speed, float turnSpeed, float maxTurn) {
    const Vector3f pos = a->getPosition();
    const float desired = std::atan2(target.x - pos.x, target.z - pos.z);
    float delta = wrapPi(desired - s.heading) * turnSpeed;
    if (delta > maxTurn) delta = maxTurn;
    if (delta < -maxTurn) delta = -maxTurn;
    s.heading = wrapPi(s.heading + delta);
    a->setDirection(s.heading);
    const Vector3f drive(std::sin(s.heading) * speed, 0.0f,
                         std::cos(s.heading) * speed);
    a->inputDrive(drive);
    a->mVelocity.x = drive.x;
    a->mVelocity.z = drive.z;
}

// Source Obj::setRandTarget: a random point between the home and territory radii
// on the far side of the crab from home.
void setRandTarget(Dango& s) {
    const float outside = TERRITORY > HOME_RADIUS ? TERRITORY - HOME_RADIUS : 0.0f;
    const float radius = gsys->getRand(outside) + HOME_RADIUS;
    const float theta = gsys->getRand(TAU);
    s.moveTarget = Vector3f(s.home.x + radius * std::sin(theta), s.home.y,
                            s.home.z + radius * std::cos(theta));
}

bool canAttack(const Vector3f& pos, const Dango& s, Creature* target) {
    // Port adaptation: the source attackable check also gates on a narrow
    // fp21=15 deg cone, but the P1 host has no wall-route roll and wandering
    // rarely aligns the cone. Activation uses the source fp20=300 range only;
    // the roll then steers toward the target via rollingMove.
    (void)s;
    const Vector3f t = target->getPosition();
    return distXZ(t, pos) <= ATTACK_RANGE;
}

void enter(Dango& s, State state, const char* clip) {
    s.state = state;
    s.stateTime = 0.0f;
    s.turnJustEntered = state == DANGO_TURN;
    s.firedEvents.clear();
    s.rolling = false;
    s.rollHit = false;
    s.armSwinging = false;
    // Leave the body invulnerable on every transition; the Turn window reopens
    // it while stickable. attackRejectedLogged is per-window, not per-state.
    s.stickable = false;
    if (clip) s.clip = clip;
}
void setState(BTeki* a, Dango& s, State state, const char* clip) {
    enter(s, state, clip);
    const unsigned generator = a->mGenerator ? a->mGenerator->_70 : 0u;
    std::printf("P2_DANGOMUSHI_STATE generator=%u state=%s\n", generator, stateName(state));
    std::fflush(stdout);
}

// Source Obj::rollingMove: steer toward the active Navi (else the nearest
// Pikmin/Navi) at the proper rolling speed.
void rollingMove(BTeki* a, Dango& s, const Vector3f& pos) {
    Creature* target = nullptr;
    if (naviMgr) {
        Navi* n = naviMgr->getNavi();
        if (n && n->isAlive()) target = n;
    }
    if (!target) target = nearestTarget(pos, SIGHT);
    if (target) {
        turnAndMove(a, s, target->getPosition(), ROLL_SPEED,
                    ROLL_TURN_ACCEL, ROLL_TURN_SPEED);
    } else {
        turnAndMove(a, s, Vector3f(pos.x + std::sin(s.heading) * 100.0f, pos.y,
                                   pos.z + std::cos(s.heading) * 100.0f),
                    ROLL_SPEED, ROLL_TURN_ACCEL, ROLL_TURN_SPEED);
    }
}

// Resolve the single roll contact: the first Pikmin/Navi inside fp22 after the
// roll starts, at most once per roll.
void rollContact(BTeki* a, Dango& s, const Vector3f& pos, unsigned generator) {
    if (s.rollHit) return;
    Creature* target = nearestTarget(pos, CONTACT_RADIUS);
    if (!target) return;
    s.rollHit = true;
    const Vector3f q = target->getPosition();
    const float angle = std::atan2(q.x - pos.x, q.z - pos.z);
    target->stimulate(InteractFlick(a, SHAKE_KNOCKBACK, ATTACK_DAMAGE, angle));
    std::printf("P2_DANGOMUSHI_HIT generator=%u pikmin=1\n", generator);
    std::fflush(stdout);
}

// Resolve the single attack_2 arm sweep at the source KEYEVENT_2 frame.
void flickSweep(BTeki* a, const Vector3f& pos, unsigned generator) {
    if (!pikiMgr) return;
    int hit = 0;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive()) continue;
        const Vector3f q = p->getPosition();
        if (distXZ(q, pos) >= FLICK_RADIUS) continue;
        const float angle = std::atan2(q.x - pos.x, q.z - pos.z);
        p->stimulate(InteractFlick(a, SHAKE_KNOCKBACK, 0.0f, angle));
        ++hit;
    }
    if (hit > 0) {
        std::printf("P2_DANGOMUSHI_FLICK generator=%u pikmin=%d\n", generator, hit);
        std::fflush(stdout);
    }
}

void setPhase(Dango& s) {
    const float duration = clipDuration(s.clip);
    const float len = duration > 0.0f ? duration : 1.0f;
    if (clipLoops(s.clip)) {
        s.phase = s.stateTime / len;
        s.phase -= std::floor(s.phase);
    } else {
        s.phase = s.stateTime / len;
        if (s.phase > 1.0f) s.phase = 1.0f;
    }
}

// ---------------------------------------------------------------------------
// Lane-25 real rain host (#174/#376): consume the lane-20 Rock/Egg policies and
// realize the Crawbster's hazard decisions as real children. The policies are
// not forked: P2RockHazard falls under the source velocity and emits real
// InteractPress/InteractAttack; P2Egg breaks into real P1 pellets/nectar. Rock
// fall/scale values are the documented fixture host parms already used by
// tools/p2_rock_hazard_test.cpp (mSearchDistance/Height/Angle stand-ins); they
// are host inputs, never source constants. Egg drop chances are the disc proper
// parms fp01-fp05 (0.5/0.35/0.05/0.05/0.05) with general fp00=50.
// ---------------------------------------------------------------------------
constexpr float kRainDelta = P2RockHazard::kSourceDelta;
constexpr float kRainOnFloorTolerance = 40.0f;
constexpr float kRainContactPad = 12.0f;
constexpr float kRainEggContactRadius = 25.0f;
constexpr float kRainSpawnHeight = 300.0f;

P2RockHazardConfig rainRockConfig() {
    P2RockHazardConfig config;
    config.fallSpeed = 500.0f;      // fixture host parm (mSearchDistance)
    config.fallOffset = 100.0f;     // fixture host parm (mSearchHeight)
    config.scaleUpRate = 5.0f;      // fixture host parm (mSearchAngle)
    config.sightRadius = 350.0f;    // general mSightRadius fixture
    config.attackDamage = 10.0f;    // general mAttackDamage fixture
    config.collisionRadius = 40.0f; // host fall trace radius
    config.health = 100.0f;         // general mHealth fixture
    return config;
}

P2EggConfig rainEggConfig() {
    P2EggConfig config;
    config.singleNectarChance = 0.5f;  // disc fp01
    config.doubleNectarChance = 0.35f; // disc fp02
    config.mititesChance = 0.05f;      // disc fp03
    config.spicyChance = 0.05f;        // disc fp04
    config.bitterChance = 0.05f;       // disc fp05
    config.forcedDropType = 0;
    config.checkHasSpray = true;
    config.health = 50.0f;             // general fp00
    return config;
}

// Static-map sphere trace for the rain Rocks: reuse the shared lane-20 Rock host
// binding (p2rockhost::RockMapBinding / detectRock / ScriptRng) rather than a
// local fork of pc_p2_projectiles.cpp's RockMapBinding / rockDetection / rng.
p2rockhost::RockMapBinding gRainBinding;

bool rainOnFloor(const Creature& creature) {
    if (!mapMgr) return false;
    const Vector3f& position = creature.mSRT.t;
    if (!std::isfinite(position.x) || !std::isfinite(position.z)) return false;
    const float ground = mapMgr->getMinY(position.x, position.z, true);
    return std::isfinite(ground) && std::fabs(position.y - ground) <= kRainOnFloorTolerance;
}

std::uint64_t rainToken(const Creature* creature) {
    return static_cast<std::uint64_t>(reinterpret_cast<std::uintptr_t>(creature));
}

void spawnRainRocks(Dango& s, BTeki* actor, const Vector3f& center, float angle,
                    int count, float lifetime, unsigned generator) {
    const P2RockHazardConfig config = rainRockConfig();
    int spawned = 0;
    for (int i = 0; i < count; ++i) {
        int slot = -1;
        for (int k = 0; k < kRainRockSlots; ++k) {
            if (!s.rainRockUsed[k]
                || s.rainRock[k].phase() == P2RockHazardPhase::Killed) {
                slot = k;
                break;
            }
        }
        if (slot < 0) break; // slot exhaustion: silent, matches the source birth
        float ox = 0.0f, oz = 0.0f;
        P2DangoMushiHazardPolicy::rockOffset(i, count, angle, &ox, &oz);
        P2RockHazardInit init;
        init.position = { center.x + ox, center.y + kRainSpawnHeight, center.z + oz };
        init.dropGroupNone = false; // DropWait -> immediate Fall
        init.timedAppear = false;
        init.initialTimer = 0.0f;
        init.sourceToken = actor
            ? static_cast<std::uint64_t>(reinterpret_cast<std::uintptr_t>(actor)) : 0;
        init.selfToken = s.rainRockSelf++;
        s.rainRock[slot].reset(config);
        if (!s.rainRock[slot].onInit(init)) continue;
        s.rainRockUsed[slot] = true;
        s.rainRockDeadTimer[slot] = 0.0f;
        s.rainRockMaxLife[slot] = lifetime;
        s.rainRockAge[slot] = 0.0f;
        s.rainRockLifetimeExpired[slot] = false;
        s.rainRockPrev[slot] = s.rainRock[slot].phase();
        s.rainContacts[slot].clear();
        ++spawned;
    }
    std::printf("P2_DANGOMUSHI_ROCK_BIRTH generator=%u requested=%d real=%d lifetime=%.1f\n",
                generator, count, spawned, lifetime);
    std::fflush(stdout);
}

void spawnRainEgg(Dango& s, const Vector3f& home, unsigned generator) {
    // Only one Egg can be live per Crawbster; a second request while the first
    // has not broken must not reset() it (that would discard its pending drop).
    if (s.rainEggActive) return;
    s.rainEgg.reset(rainEggConfig());
    s.rainEggPos = { home.x, home.y, home.z };
    if (!s.rainEgg.birth(true)) { // drop-group: a Navi/Piki touch breaks it
        std::printf("P2_DANGOMUSHI_EGG_BIRTH generator=%u real=0\n", generator);
        std::fflush(stdout);
        return;
    }
    s.rainEggActive = true;
    std::printf("P2_DANGOMUSHI_EGG_BIRTH generator=%u real=1 x=%.1f y=%.1f z=%.1f health=%.1f\n",
                generator, home.x, home.y, home.z, rainEggConfig().health);
    std::fflush(stdout);
}

void applyRainRockContact(Dango& s, int slot, P2RockHazardContactKind kind,
                          Creature* target, BTeki* owner, unsigned generator) {
    const std::uint64_t token = rainToken(target);
    const P2RockHazardContactResult result =
        s.rainRock[slot].contact(kind, rainOnFloor(*target), false, token);
    // Do not dedupe a contact ignored by the source 1 s atari grace, or it would
    // be skipped forever for this rock once the grace expires.
    if (result.ignored) return;
    if (!s.rainContacts[slot].insert(token).second) return;
    if (result.strikeEmitted) {
        if (result.strike.kind == P2RockHazardStrikeKind::Press) {
            target->stimulate(InteractPress(owner, result.strike.damage));
        } else {
            target->stimulate(InteractAttack(owner, nullptr, result.strike.damage, false));
        }
        std::printf("P2_DANGOMUSHI_ROCK_STRIKE generator=%u kind=%s damage=%.1f target=%llu\n",
                    generator,
                    result.strike.kind == P2RockHazardStrikeKind::Press ? "Press" : "Attack",
                    result.strike.damage, static_cast<unsigned long long>(token));
        std::fflush(stdout);
    }
}

void birthRainEggDrop(Dango& s, unsigned generator) {
    const P2EggDrop& drop = s.rainEgg.drop();
    const Vector3f base(s.rainEggPos.x, s.rainEggPos.y + drop.positionOffsetY, s.rainEggPos.z);
    for (int i = 0; i < drop.itemCount && i < 2; ++i) {
        const P2EggItem& item = drop.items[i];
        P2EggSpawnKind kind = item.kind;
        bool fallback = false;
        if (kind == P2EggSpawnKind::MititeGroup && drop.mititeFallbackToNectar) {
            kind = P2EggSpawnKind::Nectar; // P1 has no Mitite manager
            fallback = true;
        }
        bool birthed = false;
        const char* born = "none";
        if (kind == P2EggSpawnKind::PelletOne || kind == P2EggSpawnKind::PelletFive) {
            if (pelletMgr) {
                Pellet* pellet = pelletMgr->newNumberPellet(
                    item.pelletColor,
                    kind == P2EggSpawnKind::PelletFive ? NUMPEL_FivePellet : NUMPEL_OnePellet);
                if (pellet) {
                    pellet->init(base);
                    pellet->mVelocity.set(item.velocity.x, item.velocity.y, item.velocity.z);
                    pellet->startAI(0);
                    birthed = true;
                    born = "pellet";
                }
            }
        } else if (kind == P2EggSpawnKind::Nectar) {
            if (itemMgr) {
                Creature* nectar = itemMgr->birth(OBJTYPE_Water);
                if (nectar) {
                    nectar->init(base);
                    nectar->startAI(0);
                    birthed = true;
                    born = "nectar";
                }
            }
        } else {
            born = "unsupported";
        }
        std::printf("P2_DANGOMUSHI_EGG_ITEM generator=%u index=%d kind=%d real=%d fallback=%d "
                    "item=%s\n", generator, i, int(item.kind), int(birthed), int(fallback), born);
    }
    std::fflush(stdout);
}

void tickRain(Dango& s, BTeki* actor, const Vector3f& pos, float dt) {
    s.rainDebt += dt;
    int ticks = static_cast<int>(s.rainDebt / kRainDelta);
    if (ticks > 6) ticks = 6;
    s.rainDebt -= ticks * static_cast<double>(kRainDelta);
    if (ticks <= 0) return;
    const unsigned generator = actor->mGenerator ? actor->mGenerator->_70 : 0u;
    const P2RockHazardConfig config = rainRockConfig();
    const float radiusSq = (config.collisionRadius + kRainContactPad)
        * (config.collisionRadius + kRainContactPad);

    for (int tick = 0; tick < ticks; ++tick) {
        for (int k = 0; k < kRainRockSlots; ++k) {
            if (!s.rainRockUsed[k]) continue;
            P2RockHazard& rock = s.rainRock[k];
            if (rock.phase() == P2RockHazardPhase::Killed) {
                s.rainRockUsed[k] = false;
                s.rainContacts[k].clear();
                continue;
            }
            if (!rock.isAlive()) {
                if (rock.phase() == P2RockHazardPhase::Dead) {
                    s.rainRockDeadTimer[k] += kRainDelta;
                    if (s.rainRockDeadTimer[k] >= 0.5f && rock.finishDeath()) {
                        std::printf("P2_DANGOMUSHI_ROCK_DESTROY generator=%u slot=%d "
                                    "reason=%s\n", generator, k,
                                    s.rainRockLifetimeExpired[k] ? "lifetime"
                                        : (rock.health() <= 0.0f ? "health" : "floor"));
                        std::fflush(stdout);
                    }
                }
                continue;
            }
            // Source birthArg.mExistenceLength 30 s: a rock that never traces a
            // floor still dies and releases its pool slot after its lifetime.
            s.rainRockAge[k] += kRainDelta;
            if (s.rainRockMaxLife[k] > 0.0f && s.rainRockAge[k] >= s.rainRockMaxLife[k]) {
                rock.forceDeath();
                s.rainRockLifetimeExpired[k] = true;
                if (rock.phase() != s.rainRockPrev[k]) {
                    std::printf("P2_DANGOMUSHI_ROCK_PHASE generator=%u slot=%d phase=%d\n",
                                generator, k, int(rock.phase()));
                    std::fflush(stdout);
                    s.rainRockPrev[k] = rock.phase();
                }
                continue;
            }
            const P2RockHazardVec3 before = rock.position();
            rock.update(kRainDelta, p2rockhost::detectRock(before, config.sightRadius),
                        p2rockhost::RockMapBinding::trace, &gRainBinding);
            if (rock.phase() != s.rainRockPrev[k]) {
                std::printf("P2_DANGOMUSHI_ROCK_PHASE generator=%u slot=%d phase=%d\n",
                            generator, k, int(rock.phase()));
                std::fflush(stdout);
                s.rainRockPrev[k] = rock.phase();
            }
            const P2RockHazardVec3 rp = rock.position();
            auto consider = [&](Creature* creature, P2RockHazardContactKind kind) {
                if (!creature || !creature->isAlive()) return;
                const Vector3f& q = creature->mSRT.t;
                const float dx = q.x - rp.x, dy = q.y - rp.y, dz = q.z - rp.z;
                if (dx * dx + dy * dy + dz * dz > radiusSq) return;
                applyRainRockContact(s, k, kind, creature, actor, generator);
            };
            consider(naviMgr ? naviMgr->getNavi() : nullptr, P2RockHazardContactKind::NaviPiki);
            if (pikiMgr) {
                Iterator pikiIt(pikiMgr);
                CI_LOOP(pikiIt) {
                    consider(static_cast<Piki*>(*pikiIt), P2RockHazardContactKind::NaviPiki);
                }
            }
            if (tekiMgr) {
                Iterator tekiIt(tekiMgr);
                CI_LOOP(tekiIt) {
                    consider(static_cast<Teki*>(*tekiIt), P2RockHazardContactKind::Teki);
                }
            }
        }

        if (s.rainEggActive) {
            bool touched = false;
            auto near = [&](const Creature* creature) {
                const Vector3f& p = creature->mSRT.t;
                const float dx = p.x - s.rainEggPos.x, dy = p.y - s.rainEggPos.y;
                const float dz = p.z - s.rainEggPos.z;
                return dx * dx + dy * dy + dz * dz
                    <= kRainEggContactRadius * kRainEggContactRadius;
            };
            Navi* navi = naviMgr ? naviMgr->getNavi() : nullptr;
            if (navi && navi->isAlive() && near(navi)) touched = true;
            if (!touched && pikiMgr) {
                Iterator it(pikiMgr);
                CI_LOOP(it) {
                    Piki* piki = static_cast<Piki*>(*it);
                    if (piki && piki->isAlive() && near(piki)) { touched = true; break; }
                }
            }
            if (touched && s.rainEgg.contact(false, false)) {
                std::printf("P2_DANGOMUSHI_EGG_CONTACT generator=%u health=0\n", generator);
                std::fflush(stdout);
            }
            if (s.rainEgg.health() <= 0.0f
                && s.rainEgg.update(p2rockhost::rngFloat, &s.rainRng, p2rockhost::rngInt, &s.rainRng)) {
                birthRainEggDrop(s, generator);
                s.rainEggActive = false;
            }
        }
    }
}
}

void pc_p2_dangomushi_reset() {
    actors.clear();
    clips.clear();
    rollStartFrame = FALLBACK_ROLL_START;
    flickStartFrame = FALLBACK_FLICK_START;
    ready = false;
}
void pc_p2_dangomushi_forget(BTeki* actor) { actors.erase(static_cast<PelletView*>(actor)); }

float pc_p2_dangomushi_param_f(const BTeki* actor, int idx, float fallback) {
    if (!ready || !actors.count(static_cast<PelletView*>(const_cast<BTeki*>(actor)))) return fallback;
    if (idx == TPF_Life) return LIFE;
    if (idx == TPF_LifeRecoverRate) return 0.0f;
    switch (idx) {
    case TPF_VisibleRange:
    case TPF_VisibleAngle:
    case TPF_AttackableRange:
    case TPF_AttackableAngle:
    case TPF_AttackRange:
    case TPF_AttackHitRange:
    case TPF_AttackPower:
    case TPF_DangerTerritoryRange:
    case TPF_SafetyTerritoryRange:
        return 0.0f;
    default:
        return fallback;
    }
}

bool pc_p2_dangomushi_clip(const BTeki* actor, const char*& name, float& phase) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    name = it->second.clip.c_str();
    phase = it->second.phase;
    return true;
}

bool pc_p2_dangomushi_invulnerable(const BTeki* actor) {
    if (!ready || !actor) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    Dango& s = it->second;
    const unsigned generator = actor->mGenerator ? actor->mGenerator->_70 : 0u;
    if (!P2DangoMushiHazardPolicy::attackRejected(s.stickable)) {
        // Inside the Turn stickable window: EB_Invulnerable is clear and the
        // attack is admitted (return false so the normal damage path runs).
        std::printf("P2_DANGOMUSHI_DAMAGE_ACCEPTED generator=%u stickable=1 state=%s\n",
                    generator, stateName(s.state));
        std::fflush(stdout);
        return false;
    }
    // Outside the window the source body is invulnerable. Report the first
    // rejection per window so the fixture can observe an applied (not merely
    // decided) window without spamming every attack frame.
    if (!s.attackRejectedLogged) {
        s.attackRejectedLogged = true;
        std::printf("P2_DANGOMUSHI_DAMAGE_REJECTED generator=%u stickable=0 invulnerable=1 "
                    "state=%s\n", generator, stateName(s.state));
        std::fflush(stdout);
    }
    return true;
}

void pc_p2_dangomushi_setup() {
    pc_p2_dangomushi_reset();
    gRainBinding.reset(mapMgr);
    if (!tekiMgr) return;

    std::ifstream bank("p2-snagret-bank.txt");
    if (bank) {
        std::string token;
        if (bank >> token && token == "P2_SNAGRET_BANK_1") {
            while (bank >> token) {
                if (token == "species") {
                    std::string species, identity;
                    bank >> species >> identity;
                    // Snagret install writes the numeric enemy id; tolerate the
                    // `clips <count>` row as well.
                    if (identity == "clips") {
                        int clipCount = 0;
                        bank >> clipCount;
                    }
                } else if (token == "clip") {
                    std::string species, name, events, marker, status, value;
                    long long frames = 0;
                    int poses = 0;
                    if (!(bank >> species >> name >> frames >> events >> marker >> poses)) break;
                    if (!(bank >> value)) break;
                    if (value != "status") status = value;
                    else if (!(bank >> status)) break;
                    if (species == "DangoMushi") {
                        Clip clip;
                        clip.name = name;
                        clip.duration = frames > 0 ? float(frames) / 30.0f : 1.0f;
                        clip.loop = (name == "fly" || name == "wait" || name == "move");
                        if (events != "-") {
                            size_t start = 0;
                            while (start < events.size()) {
                                const size_t comma = events.find(',', start);
                                const std::string pair = events.substr(start, comma - start);
                                const size_t colon = pair.find(':');
                                if (colon != std::string::npos) {
                                    clip.events.emplace_back(std::atoi(pair.substr(0, colon).c_str()),
                                                             std::atoi(pair.substr(colon + 1).c_str()));
                                }
                                if (comma == std::string::npos) break;
                                start = comma + 1;
                            }
                        }
                        clips[name] = clip;
                    }
                } else {
                    break;
                }
            }
        }
    }
    const int roll = eventFrame("attack", 4);
    const int flick = eventFrame("attack_2", 2);
    if (roll >= 0) rollStartFrame = roll;
    if (flick >= 0) flickStartFrame = flick;

    std::ifstream in("p2-snagret-actors.txt");
    if (!in) return;
    std::string header;
    int count = 0;
    if (!(in >> header >> count) || header != "P2_SNAGRET_ACTORS_1" || count < 1) return;
    std::map<unsigned, std::string> wanted;
    for (int i = 0; i < count; ++i) {
        unsigned long long generator = 0;
        std::string species;
        if (!(in >> generator >> species)) return;
        if (species == "DangoMushi") wanted[unsigned(generator)] = species;
    }
    if (wanted.empty()) return;

    std::set<unsigned> found;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* actor = static_cast<Teki*>(*it);
        if (!actor || !actor->mGenerator) continue;
        auto match = wanted.find(actor->mGenerator->_70);
        if (match == wanted.end()) continue;
        if (actor->mTekiType != TEKI_Chappy) {
            std::printf("P2_DANGOMUSHI_ERROR native_type generator=%u\n", actor->mGenerator->_70);
            std::abort();
        }
        Dango& s = actors[static_cast<PelletView*>(actor)];
        s.hazard.reset(P2DangoMushiHazardParms{});
        s.home = actor->getPosition();
        s.heading = actor->getDirection();
        s.moveTarget = s.home;
        actor->mHealth = LIFE;
        enter(s, DANGO_STAY, "fly");
        std::printf("P2_DANGOMUSHI_BIND generator=%u source_id=94 visual_only=0\n",
                    actor->mGenerator->_70);
        const Vector3f pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=DangoMushi native_family=Chappy generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented attack=interactflick_roll\n",
                    actor->mGenerator->_70, pos.x, pos.y, pos.z, actor->mHealth, LIFE);
        std::printf("P2_DANGOMUSHI_STATE generator=%u state=stay\n", actor->mGenerator->_70);
        std::fflush(stdout);
        found.insert(actor->mGenerator->_70);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_DANGOMUSHI_ERROR missing_actor wanted=%zu found=%zu\n",
                    wanted.size(), found.size());
        std::abort();
    }
    ready = true;
}

void pc_p2_dangomushi_update(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Dango& s = it->second;
    const float dt = gsys->getFrameTime();
    if (dt <= 0.0f || dt > 0.5f) return;
    const Vector3f pos = actor->getPosition();
    const unsigned generator = actor->mGenerator ? actor->mGenerator->_70 : 0u;

    if (actor->mHealth <= 0.0f && s.state != DANGO_DEAD) {
        if (!s.deadLogged) {
            std::printf("P2_DANGOMUSHI_DEAD generator=%u source_id=94 health=0\n", generator);
            std::fflush(stdout);
            s.deadLogged = true;
        }
        setState(actor, s, DANGO_DEAD, "dead");
    }

    s.stateTime += dt;
    switch (s.state) {
    case DANGO_STAY:
        stop(actor);
        // Source StateStay: wake when a target enters the source private radius.
        if (nearestTarget(pos, PRIVATE_RADIUS)) {
            setState(actor, s, DANGO_APPEAR, "fly");
        }
        break;
    case DANGO_APPEAR:
        stop(actor);
        if (s.stateTime >= clipDuration("fly")) {
            Creature* target = nearestTarget(pos, SIGHT);
            if (target) {
                setRandTarget(s);
                setState(actor, s, DANGO_MOVE, "move");
            } else {
                setState(actor, s, DANGO_WAIT, "wait");
            }
        }
        break;
    case DANGO_WAIT: {
        stop(actor);
        Creature* target = nearestTarget(pos, SIGHT);
        if (target) {
            if (canAttack(pos, s, target)) {
                setState(actor, s, DANGO_ATTACK, "attack");
            } else {
                setRandTarget(s);
                setState(actor, s, DANGO_MOVE, "move");
            }
        } else if (s.stateTime > WAIT_TIME) {
            setRandTarget(s);
            setState(actor, s, DANGO_MOVE, "move");
        }
        break;
    }
    case DANGO_MOVE: {
        Creature* target = nearestTarget(pos, SIGHT);
        if (target) {
            if (canAttack(pos, s, target)) {
                setState(actor, s, DANGO_ATTACK, "attack");
                break;
            }
            turnAndMove(actor, s, target->getPosition(), MOVE_SPEED,
                        WALK_TURN_RATE, WALK_MAX_TURN);
        } else if (distXZ(pos, s.moveTarget) < MOVE_ARRIVE || s.stateTime > MOVE_TIMEOUT) {
            setState(actor, s, DANGO_WAIT, "wait");
        } else {
            turnAndMove(actor, s, s.moveTarget, MOVE_SPEED, WALK_TURN_RATE, WALK_MAX_TURN);
        }
        break;
    }
    case DANGO_ATTACK: {
        const float frame = s.stateTime * 30.0f;
        if (!s.rolling && frame >= float(rollStartFrame)) {
            s.rolling = true;
            s.rollHit = false;
            std::printf("P2_DANGOMUSHI_ROLL generator=%u frame=%.1f\n",
                        generator, float(rollStartFrame));
            std::fflush(stdout);
        }
        if (s.rolling) {
            rollingMove(actor, s, pos);
            rollContact(actor, s, pos, generator);
            if (distXZ(pos, s.home) > TERRITORY) {
                setState(actor, s, DANGO_TURN, "turn");
            } else if (s.stateTime > ATTACK_TIMEOUT) {
                setState(actor, s, DANGO_WAIT, "wait");
            }
        } else {
            stop(actor);
        }
        break;
    }
    case DANGO_TURN: {
        stop(actor);
        // Lane-25 hazard policy: the source stickable window and the Rock/Egg
        // rain decisions. The window is applied through the shared
        // tekiinteraction damage gate (pc_p2_dangomushi_invulnerable): attack/
        // bomb/press damage is admitted only while stickable.
        const float share = GameStat::allPikis > 0
            ? float(GameStat::formationPikis) / float(GameStat::allPikis) : 0.0f;
        P2DangoMushiHazardInput hz;
        hz.turnEntered = s.turnJustEntered;
        hz.turnFrame = s.stateTime * 30.0f;
        hz.activeCaptainGroupShare = share;
        hz.eggRoll = gsys->getRand(1.0f);
        P2DangoMushiHazardOutput hzo;
        s.hazard.update(hz, hzo);
        // Apply the window: damage is only admitted while stickable.
        if (hzo.stickable && !s.stickable) {
            s.attackRejectedLogged = false;
        }
        s.stickable = hzo.stickable;
        if (hzo.rocksToSpawn > 0) {
            s.hazardRocks += hzo.rocksToSpawn;
            std::printf("P2_DANGOMUSHI_HAZARD generator=%u rocks=%d lifetime=%.1f egg=%d\n",
                        generator, hzo.rocksToSpawn, hzo.rockLifetime,
                        int(hzo.eggRequested));
            std::fflush(stdout);
            // Realize the decision as real falling Rocks around the active
            // captain (the source rain centre). No-op when the slot pool is full.
            Vector3f rainCentre = pos;
            if (naviMgr) {
                Navi* active = naviMgr->getNavi();
                if (active && active->isAlive()) rainCentre = active->getPosition();
            }
            spawnRainRocks(s, actor, rainCentre, s.heading, hzo.rocksToSpawn,
                           hzo.rockLifetime, generator);
        }
        if (hzo.eggRequested) {
            // One real Egg at the Crawbster's home; its break births real items.
            // Source probability is the captain's formation share of all Pikmin
            // (DangoMushi.cpp:732-748), so with a squad attacking out of formation
            // (share ~0) it is rare in the attack fixture; run 9093da5e observed one birth.
            spawnRainEgg(s, s.home, generator);
        }
        if (hzo.stickable != s.hazardWindowLogged) {
            s.hazardWindowLogged = hzo.stickable;
            std::printf("P2_DANGOMUSHI_TURN_WINDOW generator=%u frame=%.1f stickable=%d "
                        "invulnerable=%d\n", generator, s.stateTime * 30.0f,
                        int(hzo.stickable), int(hzo.invulnerable));
            std::fflush(stdout);
        }
        s.turnJustEntered = false;
        if (s.stateTime >= FLIP_TIME || s.stateTime >= clipDuration("turn")) {
            P2DangoMushiHazardInput exitInput;
            exitInput.turnExited = true;
            P2DangoMushiHazardOutput exitOutput;
            s.hazard.update(exitInput, exitOutput);
            s.stickable = exitOutput.stickable; // false: body is invulnerable again
            setState(actor, s, DANGO_RECOVER, "recover");
        }
        break;
    }
    case DANGO_RECOVER:
        stop(actor);
        if (s.stateTime >= clipDuration("recover")) {
            // Source StateRecover::exec KEYEVENT_END flips the facing direction.
            s.heading = wrapPi(s.heading + PI);
            actor->setDirection(s.heading);
            setState(actor, s, DANGO_FLICK, "attack_2");
        }
        break;
    case DANGO_FLICK: {
        stop(actor);
        const float frame = s.stateTime * 30.0f;
        if (!s.armSwinging && frame >= float(flickStartFrame)) {
            s.armSwinging = true;
            flickSweep(actor, pos, generator);
        }
        if (s.stateTime >= clipDuration("attack_2")) {
            setState(actor, s, DANGO_WAIT, "wait");
        }
        break;
    }
    case DANGO_DEAD:
        stop(actor);
        if (s.stateTime >= clipDuration("dead")) actor->die();
        break;
    default:
        break;
    }
    setPhase(s);
    s.logTimer += dt;
    if (s.logTimer >= 1.0f) {
        s.logTimer = 0.0f;
        std::printf("P2_DANGOMUSHI_POS generator=%u state=%s clip=%s phase=%.2f x=%.2f z=%.2f\n",
                    generator, stateName(s.state), s.clip.c_str(), s.phase, pos.x, pos.z);
        std::fflush(stdout);
    }
    // Step any live Rock/Egg children the hazard decisions created.
    tickRain(s, actor, pos, dt);
}

#else
// pc_p2_dangomushi.cpp -- DangoMushi profile/mesh/slot binding, slot 312004 (#678).
//
// Binds the #670-derived Damagumo/Demon profile+mesh for arena slot 312004
// under the #638 staging contract (installer accepts Damagumo ONLY from an
// explicit demon-lane 56 profile/mesh, hash-gated, never aliased).
//
// Source facts (verified #670 record; read-only refs, nothing reimplemented):
//   profile f9ec5030..., mesh 8fc0ac7f..., slot-312004 61019a39...,
//   15 joints, 4 textures, BCA rows landing/wait/flick/dead.
// Full artifact hashes are caller-supplied here: the emitted #670 artifact
// files are not present on disk in this workspace, so this TU takes expected
// hashes as explicit parameters and gates on exact match (fail-closed). The
// recorded prefixes above are cross-checks, not substitutes.
//
// Engine-free core (stdlib only): compiles standalone for contract review and
// links into the guarded fixture. Not wired into CMakeLists.txt by this lane
// (shared registration stays serialized); never linked into production here.

#include <cstdint>
#include <cstdio>
#include <cstring>

namespace p2_dangomushi {

constexpr int kSlotId = 312004;
constexpr int kEnemyId = 56;
constexpr int kJointCount = 15;
constexpr int kTextureCount = 4;
constexpr const char* kRecordedProfilePrefix = "f9ec5030";
constexpr const char* kRecordedMeshPrefix = "8fc0ac7f";
constexpr const char* kRecordedSlotPrefix = "61019a39";
constexpr const char* kProfileName = "damagumo-family.json";
constexpr const char* kMeshPath = "Demon/enemy.bmd";
constexpr const char* kSlotName = "damagumo-slot-312004.json";
constexpr const char* kRequiredClips[] = {"landing", "wait", "flick", "dead"};
constexpr int kRequiredClipCount =
    static_cast<int>(sizeof(kRequiredClips) / sizeof(kRequiredClips[0]));

namespace {

bool is_hex64(const char* value) {
    if (!value) {
        return false;
    }
    if (std::strlen(value) != 64) {
        return false;
    }
    for (const char* p = value; *p; ++p) {
        const char c = *p;
        const bool hex = (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') ||
                         (c >= 'A' && c <= 'F');
        if (!hex) {
            return false;
        }
    }
    return true;
}

bool starts_with(const char* value, const char* prefix) {
    if (!value || !prefix) {
        return false;
    }
    return std::strncmp(value, prefix, std::strlen(prefix)) == 0;
}

bool has_clip(const char** clips, int count, const char* want) {
    if (!clips || !want) {
        return false;
    }
    for (int i = 0; i < count; ++i) {
        if (clips[i] && std::strcmp(clips[i], want) == 0) {
            return true;
        }
    }
    return false;
}

}  // namespace

struct ExpectedHashes {
    char profile[65];
    char mesh[65];
    char slot[65];
};

struct SlotBinding {
    int slot;
    int enemy;
    const char* profile_name;
    const char* mesh_path;
    const char* slot_name;
    bool hash_gated;
};

// Fail-closed structural check against the verified #670 record. Returns
// null on success or a static reason string.
const char* check_structure(int joints, int textures, const char** clips,
                            int clip_count) {
    if (joints != kJointCount) {
        return "joint count mismatch";
    }
    if (textures != kTextureCount) {
        return "texture count mismatch";
    }
    for (int i = 0; i < kRequiredClipCount; ++i) {
        if (!has_clip(clips, clip_count, kRequiredClips[i])) {
            return "required clip absent";
        }
    }
    return nullptr;
}

// Exact-match hash gate over caller-supplied expected hashes. All three must
// be well-formed 64-hex and equal the observed values; recorded #670 prefixes
// are cross-checked but never substitute for the full comparison.
const char* check_hashes(const char* profile_sha, const char* mesh_sha,
                         const char* slot_sha, const ExpectedHashes* exp) {
    if (!exp) {
        return "missing expected hashes";
    }
    if (!is_hex64(exp->profile) || !is_hex64(exp->mesh) || !is_hex64(exp->slot)) {
        return "malformed expected hash";
    }
    if (!profile_sha || std::strcmp(profile_sha, exp->profile) != 0) {
        return "profile hash mismatch";
    }
    if (!mesh_sha || std::strcmp(mesh_sha, exp->mesh) != 0) {
        return "mesh hash mismatch";
    }
    if (!slot_sha || std::strcmp(slot_sha, exp->slot) != 0) {
        return "slot hash mismatch";
    }
    if (!starts_with(exp->profile, kRecordedProfilePrefix) ||
        !starts_with(exp->mesh, kRecordedMeshPrefix) ||
        !starts_with(exp->slot, kRecordedSlotPrefix)) {
        return "expected hash outside recorded #670 prefix";
    }
    return nullptr;
}

// Slot binding record consumed by the #638 staging contract: demon-lane 56
// profile+mesh bound to arena actor slot 312004, hash-gated, never aliased.
SlotBinding bind_slot(const ExpectedHashes* exp) {
    SlotBinding out;
    out.slot = kSlotId;
    out.enemy = kEnemyId;
    out.profile_name = kProfileName;
    out.mesh_path = kMeshPath;
    out.slot_name = kSlotName;
    out.hash_gated = (exp != nullptr);
    return out;
}

}  // namespace p2_dangomushi

#endif  // P2_DAMAGUMO_BINDING_STANDALONE
