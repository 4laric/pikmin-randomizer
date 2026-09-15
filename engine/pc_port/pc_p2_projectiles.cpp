// Additive projectile host seam (#413/#425, parent #169).
//
// Wires the isolated Stone (#406), Egg (#410), Cannon-Beetle fire FSM (#424) and
// falling-Rock (#411) policies into the shared game target with live hosts: a P1
// static-map terrain trace, P2ProjectileHostAdapter homing-target selection over
// the enumerated Navi/Pikmin, an automatic Kabuto attack cycle that fires the
// Stone from a configured mouth joint, and contact/strike logging. It is
// registered from the existing batch-2 setup/reset/forget hooks plus the
// hard-lane update seam, and it is opt-in (`p2-projectiles.txt`); absent config
// is a no-op so ordinary P1 play and unconfigured rooms are untouched.
//
// No shared semantics are owned or changed: engine target health is never
// mutated (strikes go to a private host-owned proxy receiver, see
// pc_p2_projectile_receiver.*), drops are reported rather than birthed, and no
// save/reward/captain/actor lifetime state is touched. See pc_p2_projectiles.h
// for the terrain center/base convention.
#include "pc_p2_projectiles.h"
#include "pc_p2_cannon_stone.h"
#include "pc_p2_attachments.h"
#include "pc_p2_egg_hazard.h"
#include "pc_p2_kabuto_cannon.h"
#include "pc_p2_kabuto_events.h"
#include "pc_p2_kabuto_muzzle.h"
#include "pc_p2_projectile_host.h"
#include "pc_p2_projectile_receiver.h"
#include "pc_p2_projectile_engine_receiver.h"
#include "pc_p2_rock_hazard.h"
#include "pc_p2_rock_host.h"
#include "pc_p2_groink.h"
#include "pc_p2_groink_hit.h"
#include "pc_bbft.h"
#include "Creature.h"
#include "Generator.h"
#include "ItemMgr.h"
#include "MapMgr.h"
#include "ObjType.h"
#include "Pellet.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "MoviePlayer.h"
#include "gameflow.h"
#include "system.h"
#include "teki.h"
#include <cctype>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <memory>
#include <set>
#include <string>

namespace {
constexpr float kPi = 3.14159265358979323846f;
constexpr float kSourceDelta = 1.0f / 30.0f;
constexpr int kMaxTicksPerFrame = 4;
constexpr float kOnFloorTolerance = 40.0f; // host approximation, documented
constexpr float kTargetPad = 12.0f;        // host proximity pad for contact
constexpr float kEggContactRadius = 25.0f; // host proximity pad for Egg contact
constexpr double kDeadHoldSeconds = 0.5;   // host stand-in for the dead anim
constexpr float kRockContactPad = 12.0f;   // host proximity pad for Rock contact
constexpr double kRockDeadHoldSeconds = 0.5; // host stand-in for the dead anim
constexpr int kMaxTargetCandidates = 256;  // homing snapshot capacity
// Defaults for the automatic Kabuto attack cycle when a `kabuto` row omits its
// timing fields (all counts are 30 Hz source ticks).
constexpr int kKabutoWaitTicks = 30;   // Wait motion hold before END
constexpr int kKabutoTurnTicks = 15;   // Turn motion hold before END
constexpr int kKabutoAttackTicks = 20; // Attack motion hold through END
constexpr int kKabutoKey2Tick = 8;     // KEYEVENT_2 (fire) frame in Attack

bool finite(float value) { return std::isfinite(value); }

bool bounded(const P2CannonStoneVec3& value)
{
    return finite(value.x) && finite(value.y) && finite(value.z)
        && std::fabs(value.x) <= 100000.0f && std::fabs(value.y) <= 100000.0f
        && std::fabs(value.z) <= 100000.0f;
}

bool iequals(const char* a, const char* b)
{
    if (!a || !b) {
        return false;
    }
    for (; *a && *b; ++a, ++b) {
        if (std::tolower(static_cast<unsigned char>(*a))
            != std::tolower(static_cast<unsigned char>(*b))) {
            return false;
        }
    }
    return *a == '\0' && *b == '\0';
}

// Binds the Stone trace primitive to the P1 static map. center/base conversion
// is owned here: P1 traceMove adds the radius before collision and subtracts it
// afterward, so the policy's center is lowered by the radius for the trace and
// the raw result is raised back. The trace proxy is the shared lane-20
// p2rockhost::TraceProxy (pc_p2_rock_host.h), not a local fork.
class ProjectileMapBinding {
public:
    void reset(MapMgr* map) { mMap = map; mProxy.clear(); mCalls = mFloors = mWalls = 0; }

    static bool trace(void* context, const P2CannonStoneVec3& center,
                      const P2CannonStoneVec3& velocity, float delta, float radius,
                      P2CannonStoneTraceResult& result)
    {
        if (!context || !bounded(center) || !bounded(velocity) || !finite(delta)
            || std::fabs(delta - kSourceDelta) > 0.000001f
            || !finite(radius) || radius <= 0.0f) {
            return false;
        }
        ProjectileMapBinding& self = *static_cast<ProjectileMapBinding*>(context);
        if (!self.mMap || !self.mMap->mMapModel) {
            return false;
        }
        self.mProxy.clear();
        const Vector3f base(center.x, center.y - radius, center.z);
        // ignoreDynColl=true: static-map-only testing, explicitly labeled.
        MoveTrace movement(base, Vector3f(velocity.x, velocity.y, velocity.z), radius, true);
        self.mMap->traceMove(&self.mProxy, movement, delta);
        ++self.mCalls;
        result.position = { movement.mPosition.x, movement.mPosition.y + radius, movement.mPosition.z };
        result.velocity = { movement.mVelocity.x, movement.mVelocity.y, movement.mVelocity.z };
        result.wall = self.mProxy.wall;
        if (!bounded(result.position) || !bounded(result.velocity)) {
            return false;
        }
        self.mFloors += (self.mProxy.mGroundTriangle != nullptr);
        self.mWalls += result.wall;
        return true;
    }

    std::uint64_t calls() const { return mCalls; }
    std::uint64_t floors() const { return mFloors; }
    std::uint64_t walls() const { return mWalls; }

private:
    MapMgr* mMap = nullptr;
    p2rockhost::TraceProxy mProxy;
    std::uint64_t mCalls = 0, mFloors = 0, mWalls = 0;
};

// Deterministic scripted RNG for the Egg policy (the host owns the source).
// The shared lane-20 p2rockhost::ScriptRng / rngFloat / rngInt are used instead
// of a local fork.

std::uint64_t tokenOf(const Creature* creature)
{
    return static_cast<std::uint64_t>(reinterpret_cast<std::uintptr_t>(creature));
}

[[noreturn]] void fail(const char* what)
{
    std::fprintf(stderr, "P2_PROJECTILES %s\n", what);
    std::abort();
}

struct Host {
    ProjectileMapBinding* binding = nullptr;
    p2rockhost::RockMapBinding* rockBinding = nullptr;

    bool haveStoneCfg = false;
    P2CannonStoneConfig stoneCfg;
    P2CannonStoneVec3 stonePos;
    float stoneFaceDeg = 0.0f;
    bool stoneHoming = false;
    std::uint64_t stoneSource = 0;

    bool stoneActive = false;
    P2CannonStone stone;
    std::uint64_t stoneSelf = 0x504A5354ULL;
    double stoneDeadTimer = 0.0;
    std::set<std::uint64_t> stoneContacts;

    bool haveEggCfg = false;
    P2EggConfig eggCfg;
    P2EggVec3 eggPos;
    bool eggDropGroup = false;
    float eggDamage = 0.0f;
    int eggDamageTick = 0;

    bool eggActive = false;
    P2Egg egg;
    int eggTick = 0;
    bool eggDamageApplied = false;

    // Kabuto/Rkabuto fire FSM (#424). When a `kabuto` row is configured the
    // Stone is born from the FSM's FireStone action, not at setup.
    bool haveKabutoCfg = false;
    P2KabutoCannonConfig kabutoCfg;
    P2KabutoSpecies kabutoSpecies = P2KabutoSpecies::Kabuto;
    P2CannonStoneVec3 kabutoMouthJoint; // world mouth joint (before the +25 birth offset)
    float kabutoFaceDeg = 0.0f;
    int kabutoWaitTicks = kKabutoWaitTicks;
    int kabutoTurnTicks = kKabutoTurnTicks;
    int kabutoAttackTicks = kKabutoAttackTicks;
    int kabutoKey2Tick = kKabutoKey2Tick;
    P2KabutoCannon kabuto;
    int kabutoTicks = 0;
    std::uint64_t kabutoSelf = 0x504B4254ULL; // "PKBT"
    int kabutoFires = 0;

    // Optional attachment-bank moving muzzle (#169 muzzle slice). When a
    // `kabuto_rig <bankPath> <x> <y> <z> <faceDeg>` row is present the Stone is
    // born from the sampled `kuti` joint in the actor's world transform instead
    // of the static `kabutoMouthJoint`; absent -> legacy static mouth point.
    bool haveKabutoRig = false;
    std::string kabutoRigPath;
    p2attach::Vec kabutoRigOrigin{};
    float kabutoRigFaceDeg = 0.0f;
    std::shared_ptr<const p2attach::Bank> kabutoBank;
    p2attach::Instance kabutoAttachment;
    p2attach::Token kabutoAttachmentToken = 0;
    P2KabutoMuzzle kabutoMuzzle;
    std::uint64_t kabutoRigTick = 0;

    // Optional live Kabuto proxy actor (#424): `kabuto_actor <generator>`. When
    // present the muzzle owner follows that Teki's world transform and facing
    // instead of the configured rig origin, i.e. the mouth moves with the actor.
    bool haveKabutoActor = false;
    unsigned kabutoActorGenerator = 0;
    BTeki* kabutoActor = nullptr;

    // Optional P2_ANIM_CLOCK_1 sidecar (#431) driving the attack motion's
    // KEYEVENT_2/END from the shared sampled clock instead of the synthetic tick.
    bool haveKabutoClock = false;
    std::string kabutoClockPath;
    p2sampled::Clip kabutoAttackClip;
    P2KabutoEventAdapter kabutoEvents;
    bool kabutoClockStarted = false;

    // Falling-Rock hazard (#411), instantiated once as a host-driven actor.
    bool haveRockCfg = false;
    P2RockHazardConfig rockCfg;
    P2RockHazardInit rockInit;
    P2RockHazard rock;
    P2RockHazardPhase rockPrev = P2RockHazardPhase::Inactive;
    bool rockPending = false;
    double rockDeadTimer = 0.0;
    std::set<std::uint64_t> rockContacts;

    // Private proxy receivers (#169 lane 20): strikes are applied here, never to
    // an engine Creature. Populated from `receiver <token> <maxHealth>` rows.
    P2ProjectileReceiverRegistry receivers;

    // Opt-in real engine receiver mutation ("actual receiver mutation", #169
    // lane 20 remaining work). When set via `engine_receiver 1`, each emitted
    // Stone/Rock strike is additionally routed into the live creature through
    // its own stimulate(InteractAttack/InteractPress) path; the proxy is left
    // intact so both signals are recorded. Default 0 = proxy only.
    bool engineReceiver = false;
    // Tracks whether an `engine_receiver` row was seen, so `engine_receiver 0`
    // followed by `engine_receiver 1` is still rejected as a duplicate.
    bool sawEngineReceiverRow = false;
    // Emits P2_PROJECTILE_SKIP_SELF at most once per Stone flight.
    bool stoneSkippedSelf = false;

    // Groink consumer proof (#169 lane 20): exercises lane-21's Groink classifier
    // (pc_p2_groink_hit.h -> p2_groink_classify_hit) without forking lane-21's
    // modules, then applies the classified Bomb through THIS lane's real engine
    // receiver (stimulate on the captain Navi). The sweep is the muzzle-origin ->
    // live-captain segment (the host supplies it because the Groink policy owns no
    // actor).
    bool haveGroinkCfg = false;
    P2GroinkVec3 groinkOrigin{};
    float groinkDamage = 0.0f;
    bool groinkApplied = false;

    // Two-Teki injected placement: when `teki_pin 1` is set, every other live Teki
    // (the victim) is re-anchored to the bound firer each step so the Stone's
    // birth-frame contact deterministically reaches it. Clearly labelled injected
    // (the room's two Dwarf Bulborbs otherwise settle ~70 units apart).
    bool pinVictim = false;
    bool sawTekiPinRow = false;

    p2rockhost::ScriptRng rng;
    double debt = 0.0;
};
Host gHost;

void parseConfig(const char* path)
{
    std::ifstream in(path);
    if (!in) {
        fail("config vanished after probe");
    }
    std::string word;
    if (!(in >> word) || word != "P2_PROJECTILES_1") {
        fail("invalid config header");
    }
    while (in >> word) {
        if (word == "seed") {
            unsigned long long seed = 0;
            if (!(in >> seed) || seed > 0xffffffffULL) {
                fail("invalid seed row");
            }
            gHost.rng.state = static_cast<std::uint32_t>(seed != 0ULL ? seed : 1ULL);
        } else if (word == "stone") {
            if (gHost.haveStoneCfg) {
                fail("duplicate stone row");
            }
            P2CannonStoneConfig config;
            float homing = 0.0f, faceDeg = 0.0f;
            unsigned long long source = 0;
            if (!(in >> gHost.stonePos.x >> gHost.stonePos.y >> gHost.stonePos.z
                    >> faceDeg >> homing >> config.moveSpeed >> config.searchRumbleSpeed
                    >> config.turnSpeed >> config.maxTurnAngle >> config.attackDamage
                    >> config.sightRadius >> config.collisionRadius >> config.health >> source)
                || source > 0xffffffffULL || (homing != 0.0f && homing != 1.0f)
                || !bounded(gHost.stonePos) || !finite(faceDeg)) {
                fail("invalid stone row");
            }
            config.variant = P2CannonStoneVariant::Stone;
            gHost.stoneCfg = config;
            gHost.stoneFaceDeg = faceDeg;
            gHost.stoneHoming = (homing == 1.0f);
            gHost.stoneSource = source;
            gHost.haveStoneCfg = true;
        } else if (word == "kabuto") {
            if (gHost.haveKabutoCfg) {
                fail("duplicate kabuto row");
            }
            std::string species;
            int waitTicks = kKabutoWaitTicks, turnTicks = kKabutoTurnTicks;
            int attackTicks = kKabutoAttackTicks, key2Tick = kKabutoKey2Tick;
            if (!(in >> species >> gHost.kabutoMouthJoint.x >> gHost.kabutoMouthJoint.y
                    >> gHost.kabutoMouthJoint.z >> gHost.kabutoFaceDeg
                    >> gHost.kabutoCfg.maxAttackAngle >> gHost.kabutoCfg.health)
                || !(in >> waitTicks >> turnTicks >> attackTicks >> key2Tick)) {
                fail("invalid kabuto row");
            }
            if (species == "Kabuto") {
                gHost.kabutoSpecies = P2KabutoSpecies::Kabuto;
            } else if (species == "Rkabuto") {
                gHost.kabutoSpecies = P2KabutoSpecies::Rkabuto;
            } else if (species == "Fkabuto") {
                gHost.kabutoSpecies = P2KabutoSpecies::Fkabuto;
            } else {
                fail("invalid kabuto species");
            }
            if (!bounded(gHost.kabutoMouthJoint) || !finite(gHost.kabutoFaceDeg)
                || !finite(gHost.kabutoCfg.maxAttackAngle) || gHost.kabutoCfg.maxAttackAngle < 0.0f
                || !finite(gHost.kabutoCfg.health) || gHost.kabutoCfg.health <= 0.0f
                || waitTicks < 0 || turnTicks < 0 || key2Tick < 0 || attackTicks <= key2Tick) {
                fail("invalid kabuto row");
            }
            gHost.kabutoWaitTicks = waitTicks;
            gHost.kabutoTurnTicks = turnTicks;
            gHost.kabutoAttackTicks = attackTicks;
            gHost.kabutoKey2Tick = key2Tick;
            gHost.haveKabutoCfg = true;
        } else if (word == "kabuto_rig") {
            // Opt-in moving muzzle: `kabuto_rig <bankPath> <x> <y> <z> <faceDeg>`.
            // Requires a kabuto row (checked below); the bank is loaded and the
            // species clip/joint resolved in setup.
            if (gHost.haveKabutoRig) {
                fail("duplicate kabuto_rig row");
            }
            if (!(in >> gHost.kabutoRigPath >> gHost.kabutoRigOrigin.x >> gHost.kabutoRigOrigin.y
                    >> gHost.kabutoRigOrigin.z >> gHost.kabutoRigFaceDeg)) {
                fail("invalid kabuto_rig row");
            }
            if (gHost.kabutoRigPath.empty()
                || !finite(gHost.kabutoRigOrigin.x) || !finite(gHost.kabutoRigOrigin.y)
                || !finite(gHost.kabutoRigOrigin.z) || !finite(gHost.kabutoRigFaceDeg)
                || std::fabs(gHost.kabutoRigOrigin.x) > 100000.0f
                || std::fabs(gHost.kabutoRigOrigin.y) > 100000.0f
                || std::fabs(gHost.kabutoRigOrigin.z) > 100000.0f) {
                fail("invalid kabuto_rig row");
            }
            gHost.haveKabutoRig = true;
        } else if (word == "kabuto_clock") {
            // Opt-in authoritative fire events: `kabuto_clock <animClockPath>`.
            // The attack clip is resolved from a P2_ANIM_CLOCK_1 sidecar in setup.
            if (gHost.haveKabutoClock) {
                fail("duplicate kabuto_clock row");
            }
            if (!(in >> gHost.kabutoClockPath) || gHost.kabutoClockPath.empty()) {
                fail("invalid kabuto_clock row");
            }
            gHost.haveKabutoClock = true;
        } else if (word == "kabuto_actor") {
            // Opt-in live actor: `kabuto_actor <generator>`. The host binds the
            // Teki with that generator in setup and follows its transform.
            if (gHost.haveKabutoActor) {
                fail("duplicate kabuto_actor row");
            }
            unsigned long long generator = 0;
            if (!(in >> generator) || generator == 0 || generator > 0xffffffffULL) {
                fail("invalid kabuto_actor row");
            }
            gHost.kabutoActorGenerator = static_cast<unsigned>(generator);
            gHost.haveKabutoActor = true;
        } else if (word == "rock") {
            if (gHost.haveRockCfg) {
                fail("duplicate rock row");
            }
            float dropGroupNone = 1.0f, timedAppear = 0.0f;
            unsigned long long source = 0, self = 0;
            if (!(in >> gHost.rockInit.position.x >> gHost.rockInit.position.y
                    >> gHost.rockInit.position.z >> dropGroupNone >> timedAppear
                    >> gHost.rockInit.initialTimer >> gHost.rockCfg.fallSpeed
                    >> gHost.rockCfg.fallOffset >> gHost.rockCfg.scaleUpRate
                    >> gHost.rockCfg.sightRadius >> gHost.rockCfg.attackDamage
                    >> gHost.rockCfg.collisionRadius >> gHost.rockCfg.health >> source >> self)) {
                fail("invalid rock row");
            }
            if ((dropGroupNone != 0.0f && dropGroupNone != 1.0f)
                || (timedAppear != 0.0f && timedAppear != 1.0f)
                || !finite(gHost.rockInit.position.x) || !finite(gHost.rockInit.position.y)
                || !finite(gHost.rockInit.position.z) || !(gHost.rockInit.initialTimer >= 0.0f)
                || !finite(gHost.rockCfg.fallSpeed) || gHost.rockCfg.fallSpeed < 0.0f
                || !finite(gHost.rockCfg.fallOffset) || gHost.rockCfg.fallOffset < 0.0f
                || !finite(gHost.rockCfg.scaleUpRate) || gHost.rockCfg.scaleUpRate <= 0.0f
                || !finite(gHost.rockCfg.sightRadius) || gHost.rockCfg.sightRadius < 0.0f
                || !finite(gHost.rockCfg.attackDamage) || gHost.rockCfg.attackDamage < 0.0f
                || !finite(gHost.rockCfg.collisionRadius) || gHost.rockCfg.collisionRadius <= 0.0f
                || !finite(gHost.rockCfg.health) || gHost.rockCfg.health <= 0.0f
                || source > 0xffffffffULL || self > 0xffffffffULL) {
                fail("invalid rock row");
            }
            gHost.rockInit.dropGroupNone = (dropGroupNone == 1.0f);
            gHost.rockInit.timedAppear = (timedAppear == 1.0f);
            gHost.rockInit.sourceToken = source;
            gHost.rockInit.selfToken = self;
            gHost.haveRockCfg = true;
        } else if (word == "egg") {
            if (gHost.haveEggCfg) {
                fail("duplicate egg row");
            }
            P2EggConfig config;
            float dropGroup = 0.0f, checkSprays = 1.0f;
            if (!(in >> gHost.eggPos.x >> gHost.eggPos.y >> gHost.eggPos.z >> dropGroup
                    >> config.singleNectarChance >> config.doubleNectarChance
                    >> config.mititesChance >> config.spicyChance >> config.bitterChance
                    >> config.forcedDropType >> config.health >> checkSprays
                    >> gHost.eggDamage >> gHost.eggDamageTick)
                || (dropGroup != 0.0f && dropGroup != 1.0f)
                || (checkSprays != 0.0f && checkSprays != 1.0f)
                || !finite(gHost.eggPos.x) || !finite(gHost.eggPos.y)
                || !finite(gHost.eggPos.z) || !(gHost.eggDamage >= 0.0f)
                || gHost.eggDamageTick < 0) {
                fail("invalid egg row");
            }
            config.checkHasSpray = (checkSprays == 1.0f);
            gHost.eggCfg = config;
            gHost.eggDropGroup = (dropGroup == 1.0f);
            gHost.haveEggCfg = true;
        } else if (word == "receiver") {
            // Proxy receiver row: `receiver <token> <maxHealth>` or the
            // `receiver any <maxHealth>` wildcard sink. The wildcard exists
            // because engine creature tokens are runtime pointers an arena
            // config cannot name; multiple exact rows are allowed.
            std::string selector;
            if (!(in >> selector)) {
                fail("invalid receiver row");
            }
            const bool any = (selector == "any");
            std::uint64_t token = 0;
            if (!any) {
                char* end = nullptr;
                token = std::strtoull(selector.c_str(), &end, 10);
                if (end == selector.c_str() || *end != '\0' || token == 0) {
                    fail("invalid receiver row");
                }
            }
            float maxHealth = 0.0f;
            if (!(in >> maxHealth) || !finite(maxHealth) || maxHealth <= 0.0f
                || (any ? !gHost.receivers.addAny(maxHealth)
                        : !gHost.receivers.add(token, maxHealth))) {
                fail("invalid receiver row");
            }
        } else if (word == "engine_receiver") {
            // Opt-in real engine receiver mutation: `engine_receiver <0|1>`.
            if (gHost.sawEngineReceiverRow) {
                fail("duplicate engine_receiver row");
            }
            gHost.sawEngineReceiverRow = true;
            float enabled = 0.0f;
            if (!(in >> enabled) || (enabled != 0.0f && enabled != 1.0f)) {
                fail("invalid engine_receiver row");
            }
            gHost.engineReceiver = (enabled == 1.0f);
        } else if (word == "groink") {
            // Opt-in second-consumer proof: drive lane-21's Groink Bomb -> this
            // lane's receiver bridge. `groink <mx> <my> <mz> <damage>`.
            if (gHost.haveGroinkCfg) {
                fail("duplicate groink row");
            }
            float d = 0.0f;
            if (!(in >> gHost.groinkOrigin.x >> gHost.groinkOrigin.y >> gHost.groinkOrigin.z >> d)
                || !finite(gHost.groinkOrigin.x) || !finite(gHost.groinkOrigin.y)
                || !finite(gHost.groinkOrigin.z) || !finite(d) || d < 0.0f) {
                fail("invalid groink row");
            }
            gHost.groinkDamage = d;
            gHost.haveGroinkCfg = true;
        } else if (word == "teki_pin") {
            // Opt-in injected victim placement: `teki_pin <0|1>` (default 0).
            if (gHost.sawTekiPinRow) {
                fail("duplicate teki_pin row");
            }
            gHost.sawTekiPinRow = true;
            float v = 0.0f;
            if (!(in >> v) || (v != 0.0f && v != 1.0f)) {
                fail("invalid teki_pin row");
            }
            gHost.pinVictim = (v == 1.0f);
        } else {
            fail("invalid config token");
        }
    }
    if (gHost.haveKabutoCfg && !gHost.haveStoneCfg) {
        fail("kabuto requires a stone row");
    }
    if (gHost.haveKabutoRig && !gHost.haveKabutoCfg) {
        fail("kabuto_rig requires a kabuto row");
    }
    if (gHost.haveKabutoClock && !gHost.haveKabutoCfg) {
        fail("kabuto_clock requires a kabuto row");
    }
    if (gHost.haveKabutoActor && (!gHost.haveKabutoCfg || !gHost.haveKabutoRig)) {
        fail("kabuto_actor requires a kabuto row and a kabuto_rig row");
    }
    if (gHost.pinVictim && !gHost.haveKabutoActor) {
        fail("teki_pin requires a kabuto_actor row");
    }
    if (!gHost.haveStoneCfg && !gHost.haveEggCfg && !gHost.haveRockCfg && !gHost.haveGroinkCfg) {
        fail("config has no rows");
    }
}

bool onFloor(const Creature& creature)
{
    if (!mapMgr) {
        return false;
    }
    const Vector3f& position = creature.mSRT.t;
    if (!finite(position.x) || !finite(position.z)) {
        return false;
    }
    const float ground = mapMgr->getMinY(position.x, position.z, true);
    return finite(ground) && std::fabs(position.y - ground) <= kOnFloorTolerance;
}

// Snapshot the enumerated Navi/Pikmin and let the committed host adapter apply
// the source selection (active Navi first, else nearest live candidate within
// sightRadius by 2D x/z distance; Rock.cpp:370-386). This replaces the seam's
// former inline snapshot with P2ProjectileHostAdapter::selectTarget.
P2CannonStoneTarget selectHostTarget(const P2CannonStoneVec3& from, float sightRadius)
{
    P2ProjectileHostCandidate candidates[kMaxTargetCandidates];
    P2ProjectileHostCandidateSnapshot snapshot;
    int count = 0;

    auto consider = [&](Creature* creature) {
        if (!creature || count >= kMaxTargetCandidates) {
            return;
        }
        P2ProjectileHostCandidate& candidate = candidates[count++];
        candidate.position = { creature->mSRT.t.x, creature->mSRT.t.y, creature->mSRT.t.z };
        candidate.token = tokenOf(creature);
        candidate.alive = creature->isAlive();
    };

    // Source order: the active Navi first, then the nearest Pikmin/Navi.
    Navi* navi = naviMgr ? naviMgr->getNavi() : nullptr;
    if (navi && navi->isAlive()) {
        snapshot.hasActiveNavi = true;
        snapshot.activeNaviPosition = { navi->mSRT.t.x, navi->mSRT.t.y, navi->mSRT.t.z };
        snapshot.activeNaviToken = tokenOf(navi);
    }
    // getNearestPikminOrNavi enumerates the Navi+Pikmin population; the adapter
    // applies the 2D x/z sight filter and tie order.
    consider(navi);
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) { consider(static_cast<Piki*>(*it)); }
    }
    snapshot.candidates = candidates;
    snapshot.candidateCount = count;
    return P2ProjectileHostAdapter::selectTarget(from, snapshot, sightRadius);
}

const char* kabutoPhaseName(P2KabutoPhase phase)
{
    switch (phase) {
    case P2KabutoPhase::Inactive: return "Inactive";
    case P2KabutoPhase::Wait: return "Wait";
    case P2KabutoPhase::Turn: return "Turn";
    case P2KabutoPhase::Attack: return "Attack";
    case P2KabutoPhase::FixAttack: return "FixAttack";
    case P2KabutoPhase::Flick: return "Flick";
    case P2KabutoPhase::FixWait: return "FixWait";
    case P2KabutoPhase::FixTurn: return "FixTurn";
    case P2KabutoPhase::FixHide: return "FixHide";
    case P2KabutoPhase::FixStay: return "FixStay";
    case P2KabutoPhase::FixAppear: return "FixAppear";
    case P2KabutoPhase::Dead: return "Dead";
    case P2KabutoPhase::Killed: return "Killed";
    }
    return "?";
}

const char* kabutoActionName(P2KabutoAction action)
{
    switch (action) {
    case P2KabutoAction::None: return "None";
    case P2KabutoAction::FireStone: return "FireStone";
    case P2KabutoAction::ToWait: return "ToWait";
    case P2KabutoAction::ToTurn: return "ToTurn";
    case P2KabutoAction::ToAttack: return "ToAttack";
    case P2KabutoAction::ToFlick: return "ToFlick";
    case P2KabutoAction::ToDead: return "ToDead";
    case P2KabutoAction::ToFixAttack: return "ToFixAttack";
    case P2KabutoAction::ToFixWait: return "ToFixWait";
    case P2KabutoAction::ToFixTurn: return "ToFixTurn";
    case P2KabutoAction::ToFixHide: return "ToFixHide";
    case P2KabutoAction::ToFixStay: return "ToFixStay";
    case P2KabutoAction::ToFixAppear: return "ToFixAppear";
    }
    return "?";
}

const char* kabutoSpeciesName(P2KabutoSpecies species)
{
    switch (species) {
    case P2KabutoSpecies::Kabuto: return "Kabuto";
    case P2KabutoSpecies::Rkabuto: return "Rkabuto";
    case P2KabutoSpecies::Fkabuto: return "Fkabuto";
    }
    return "?";
}

const char* rockPhaseName(P2RockHazardPhase phase)
{
    switch (phase) {
    case P2RockHazardPhase::Inactive: return "Inactive";
    case P2RockHazardPhase::Wait: return "Wait";
    case P2RockHazardPhase::Appear: return "Appear";
    case P2RockHazardPhase::DropWait: return "DropWait";
    case P2RockHazardPhase::Fall: return "Fall";
    case P2RockHazardPhase::Dead: return "Dead";
    case P2RockHazardPhase::Killed: return "Killed";
    }
    return "?";
}

const char* rockContactKindName(P2RockHazardContactKind kind)
{
    switch (kind) {
    case P2RockHazardContactKind::NaviPiki: return "NaviPiki";
    case P2RockHazardContactKind::Teki: return "Teki";
    case P2RockHazardContactKind::Other: return "Other";
    }
    return "?";
}

void logStoneStrike(const P2CannonStoneContactResult& result)
{
    const char* kind = result.strike.kind == P2CannonStoneStrikeKind::Press ? "Press" : "Attack";
    std::printf("P2_PROJECTILE_STRIKE kind=%s damage=%.1f target=%llu attributed=%llu source=%d health_zeroed=%d\n",
                kind, result.strike.damage,
                static_cast<unsigned long long>(result.strike.targetToken),
                static_cast<unsigned long long>(result.strike.attributedToken),
                int(result.strike.attributedToSource), int(result.healthZeroed));
}

// Proxy-receiver markers. `damage` is the amount actually applied (clamped by
// the receiver), and DEAD is emitted exactly once through the hit's died flag.
void logReceiverStrike(const P2ProjectileReceiverHit& hit)
{
    if (!hit.known || !hit.applied) {
        return;
    }
    std::printf("P2_PROJECTILE_RECEIVER_HIT token=%llu kind=%s damage=%.1f health=%.1f "
                "attributed=%llu\n",
                static_cast<unsigned long long>(hit.targetToken),
                p2ProjectileReceiverStrikeKindName(hit.kind), hit.appliedDamage, hit.health,
                static_cast<unsigned long long>(hit.attributedToken));
    if (hit.died) {
        std::printf("P2_PROJECTILE_RECEIVER_DEAD token=%llu\n",
                    static_cast<unsigned long long>(hit.targetToken));
    }
}

// Real engine receiver mutation (#169 "actual receiver mutation"). Applies the
// already-classified strike to a live engine creature through its own
// stimulate(InteractAttack/InteractPress) path and records the observed outcome.
// `source` is the host-resolved source enemy: null for Teki (source attributes
// Teki damage to the Stone, which has no live Creature here), the bound Kabuto
// actor for a grounded Navi/Pikmin.
void applyAndLogEngineStrike(Creature* target, Creature* source, bool attack,
                             bool targetIsTeki, float damage)
{
    if (!gHost.engineReceiver || !target) {
        return;
    }
    const P2ProjectileEngineHit hit = p2_projectile_apply_engine_strike(
        target, source, attack, targetIsTeki, damage);
    std::printf("P2_PROJECTILE_ENGINE_STRIKE target=%llu kind=%s damage=%.1f applied=%d "
                "rejected=%d health=%.1f->%.1f stored=%.1f->%.1f source=%llu\n",
                static_cast<unsigned long long>(tokenOf(target)),
                attack ? "Attack" : "Press", damage, int(hit.applied), int(hit.rejected),
                hit.healthBefore, hit.healthAfter,
                hit.storedDamageBefore, hit.storedDamageAfter,
                static_cast<unsigned long long>(tokenOf(source)));
    if (hit.attempted && !hit.applied) {
        std::printf("P2_PROJECTILE_ENGINE_NOP target=%llu rejected=%d\n",
                    static_cast<unsigned long long>(tokenOf(target)), int(hit.rejected));
    }
}

void detectStoneContacts()
{
    if (!gHost.stoneActive || !gHost.stone.isAlive()) {
        return;
    }
    const P2CannonStoneVec3 position = gHost.stone.position();
    const float radius = gHost.stoneCfg.collisionRadius + kTargetPad;
    const float radiusSq = radius * radius;
    auto consider = [&](Creature* creature, P2CannonStoneContactKind kind) {
        if (!creature || !creature->isAlive()) {
            return;
        }
        const Vector3f& p = creature->mSRT.t;
        const float dx = p.x - position.x, dy = p.y - position.y, dz = p.z - position.z;
        if (dx * dx + dy * dy + dz * dz > radiusSq) {
            return;
        }
        // Never let a Stone damage its own firing Kabuto: the bound actor is
        // skipped even beyond the 1 s source-grace (a forward-fired Stone should
        // not wrap back onto its firer). Emitted at most once per flight, only
        // when the firer is actually inside the contact radius.
        if (creature == gHost.kabutoActor) {
            if (!gHost.stoneSkippedSelf) {
                std::printf("P2_PROJECTILE_SKIP_SELF target=%llu\n",
                            static_cast<unsigned long long>(tokenOf(creature)));
                gHost.stoneSkippedSelf = true;
            }
            return;
        }
        const std::uint64_t token = tokenOf(creature);
        if (!gHost.stoneContacts.insert(token).second) {
            return;
        }
        const P2CannonStoneContactResult result =
            gHost.stone.contact(kind, onFloor(*creature), false, token);
        if (result.ignored) {
            std::printf("P2_PROJECTILE_CONTACT_IGNORED target=%llu\n",
                        static_cast<unsigned long long>(token));
            return;
        }
        if (result.strikeEmitted) {
            logStoneStrike(result);
            logReceiverStrike(gHost.receivers.applyStrike(result));
            const bool attack = result.strike.kind == P2CannonStoneStrikeKind::Attack;
            const bool targetIsTeki = kind == P2CannonStoneContactKind::Teki;
            // Source attribution: InteractPress uses mSourceEnemy (the firing
            // Kabuto) when present; InteractAttack is attributed to the Stone
            // itself (no live Creature in this host -> null source).
            Creature* source = (kind == P2CannonStoneContactKind::NaviPiki) ? gHost.kabutoActor
                                                                            : nullptr;
            applyAndLogEngineStrike(creature, source, attack, targetIsTeki, result.strike.damage);
        }
        if (result.healthZeroed) {
            std::printf("P2_PROJECTILE_STONE_CONTACT target=%llu kind=%d health_zeroed=1\n",
                        static_cast<unsigned long long>(token), int(kind));
        }
    };
    consider(naviMgr ? naviMgr->getNavi() : nullptr, P2CannonStoneContactKind::NaviPiki);
    if (pikiMgr) {
        Iterator pikiIt(pikiMgr);
        CI_LOOP(pikiIt) { consider(static_cast<Piki*>(*pikiIt), P2CannonStoneContactKind::NaviPiki); }
    }
    if (tekiMgr) {
        Iterator tekiIt(tekiMgr);
        CI_LOOP(tekiIt) { consider(static_cast<Teki*>(*tekiIt), P2CannonStoneContactKind::Teki); }
    }
}

void tickStone()
{
    P2CannonStone& stone = gHost.stone;
    if (!stone.isAlive()) {
        if (stone.phase() == P2CannonStonePhase::Dead) {
            gHost.stoneDeadTimer += kSourceDelta;
            if (gHost.stoneDeadTimer >= kDeadHoldSeconds && stone.finishDeath()) {
                const char* reason = stone.hasHealthZeroed() ? "health"
                    : (stone.timer() > P2CannonStone::kMoveTimeoutSeconds ? "timeout" : "wall");
                std::printf("P2_PROJECTILE_STONE_DESTROY reason=%s traces=%llu floors=%llu walls=%llu\n",
                            reason, static_cast<unsigned long long>(gHost.binding->calls()),
                            static_cast<unsigned long long>(gHost.binding->floors()),
                            static_cast<unsigned long long>(gHost.binding->walls()));
                gHost.stoneActive = false;
                gHost.stoneContacts.clear();
            }
        }
        return;
    }

    P2CannonStoneTarget target;
    if (stone.homing()) {
        target = selectHostTarget(stone.position(), gHost.stoneCfg.sightRadius);
    }
    stone.update(kSourceDelta, target, ProjectileMapBinding::trace, gHost.binding);
    if (!stone.isAlive()) {
        std::printf("P2_PROJECTILE_STONE_DEAD x=%.1f y=%.1f z=%.1f timer=%.2f health=%.1f\n",
                    stone.position().x, stone.position().y, stone.position().z,
                    stone.timer(), stone.health());
    }
    detectStoneContacts();
}

void logKabutoAction(P2KabutoAction action)
{
    std::printf("P2_PROJECTILE_KABUTO_ACTION phase=%s action=%s tick=%d\n",
                kabutoPhaseName(gHost.kabuto.phase()), kabutoActionName(action),
                gHost.kabutoTicks);
}

// Actor world transform for the attachment-bank muzzle: translate to the live
// bound actor when one is configured, else the rig origin, and rotate about Y by
// the facing.
p2attach::Affine kabutoActorWorld(float faceRad)
{
    p2attach::Affine owner;
    const float c = std::cos(faceRad), s = std::sin(faceRad);
    owner.m[0][0] = c;
    owner.m[0][2] = s;
    owner.m[2][0] = -s;
    owner.m[2][2] = c;
    if (gHost.haveKabutoActor && gHost.kabutoActor) {
        const Vector3f& p = gHost.kabutoActor->mSRT.t;
        owner.m[0][3] = p.x;
        owner.m[1][3] = p.y;
        owner.m[2][3] = p.z;
    } else {
        owner.m[0][3] = gHost.kabutoRigOrigin.x;
        owner.m[1][3] = gHost.kabutoRigOrigin.y;
        owner.m[2][3] = gHost.kabutoRigOrigin.z;
    }
    return owner;
}

// Birth the Stone from a consumed FireStone: sample the rig muzzle when
// configured, else the static mouth joint, then birth the Stone. Shared by the
// synthetic KEYEVENT_2 path and the sampled-clock Key2 path.
void fireKabutoStone(P2KabutoCannon& cannon)
{
    P2KabutoStoneBirth birth;
    // A live bound actor supplies its own facing (radians); otherwise the row.
    const float faceRad = (gHost.haveKabutoActor && gHost.kabutoActor)
        ? gHost.kabutoActor->getDirection()
        : gHost.kabutoFaceDeg * kPi / 180.0f;
    P2CannonStoneVec3 mouthJoint = gHost.kabutoMouthJoint;
    bool took = false;
    if (gHost.haveKabutoRig) {
        // Attachment-bank moving muzzle: sample the `kuti` joint at the source
        // fire frame in the actor's world transform.
        took = gHost.kabutoMuzzle.takeBirth(
            cannon, gHost.kabutoAttachment, gHost.kabutoAttachmentToken,
            kabutoActorWorld(faceRad), ++gHost.kabutoRigTick, faceRad, birth);
        if (took) {
            // takeBirth applied the source +25 y offset; recover the joint.
            mouthJoint = { birth.mouthPosition.x, birth.mouthPosition.y - 25.0f,
                           birth.mouthPosition.z };
        }
    } else {
        took = cannon.takeBirth(gHost.kabutoMouthJoint, faceRad, birth);
    }
    if (!took) {
        fail("kabuto takeBirth failed");
    }
    gHost.stone.reset(gHost.stoneCfg);
    // Source token for the source-grace (shouldIgnoreAtari, CannonStone:289):
    // when a real Kabuto actor is bound, use its live token so the Stone ignores
    // the firing Teki for the first second instead of never matching the synthetic
    // kabutoSelf token (which otherwise lets the Stone hit its own firer from the
    // birth-frame contact).
    const std::uint64_t sourceToken = (gHost.haveKabutoActor && gHost.kabutoActor)
        ? tokenOf(gHost.kabutoActor)
        : gHost.kabutoSelf;
    if (!gHost.stone.birth(birth.mouthPosition, birth.faceDir, birth.homing,
                           sourceToken, gHost.stoneSelf)) {
        fail("kabuto stone birth failed");
    }
    gHost.stoneActive = true;
    gHost.stoneDeadTimer = 0.0;
    gHost.stoneSkippedSelf = false;
    ++gHost.kabutoFires;
    std::printf("P2_PROJECTILE_KABUTO_FIRE species=%s homing=%d rig=%d mouth=(%.1f,%.1f,%.1f) "
                "birth=(%.1f,%.1f,%.1f) face_deg=%.1f source=%llu fire=%d\n",
                kabutoSpeciesName(cannon.species()), int(birth.homing),
                int(gHost.haveKabutoRig), mouthJoint.x, mouthJoint.y,
                mouthJoint.z, birth.mouthPosition.x,
                birth.mouthPosition.y, birth.mouthPosition.z, gHost.kabutoFaceDeg,
                static_cast<unsigned long long>(gHost.kabutoSelf), gHost.kabutoFires);
}

// Host-driven automatic attack cycle: Wait -> Turn -> Attack -> KEYEVENT_2 ->
// END, one source tick at a time. The cycle freezes while a Stone is in flight
// so the FSM sequence is clean and exactly one Stone is active at a time.
void tickKabuto()
{
    P2KabutoCannon& cannon = gHost.kabuto;
    if (!cannon.isAlive() || gHost.stoneActive) {
        return;
    }

    // Search for a target around the live bound actor when present, else the
    // configured mouth point.
    P2CannonStoneVec3 origin = gHost.kabutoMouthJoint;
    if (gHost.haveKabutoActor && gHost.kabutoActor) {
        const Vector3f& p = gHost.kabutoActor->mSRT.t;
        origin = { p.x, p.y, p.z };
    }
    const P2CannonStoneTarget target = selectHostTarget(origin, gHost.stoneCfg.sightRadius);
    {
        static bool logged = false;
        if (!logged) {
            logged = true;
            std::printf("P2_PROJECTILE_KABUTO_TARGET present=%d origin=(%.1f,%.1f,%.1f) sight=%.1f\n",
                        int(target.hasTarget), origin.x, origin.y, origin.z,
                        gHost.stoneCfg.sightRadius);
        }
    }

    P2KabutoHostState host;
    host.targetPresent = target.hasTarget;
    host.targetAttackable = target.hasTarget;
    host.flickRequested = false;
    host.health = gHost.kabutoCfg.health;
    host.targetAngle = 0.0f;
    if (target.hasTarget) {
        host.targetAngle = std::atan2(target.position.x - origin.x, target.position.z - origin.z);
    }

    ++gHost.kabutoTicks;
    const P2KabutoPhase phase = cannon.phase();
    P2KabutoAction action = P2KabutoAction::None;
    bool motionEnded = false;
    bool logged = false;

    if (phase != P2KabutoPhase::Attack) {
        gHost.kabutoClockStarted = false;
    }

    if (gHost.haveKabutoClock && phase == P2KabutoPhase::Attack) {
        // Authoritative fire events (#431): KEYEVENT_2 and the one-shot END come
        // from the shared sampled clock instead of the synthetic tick.
        if (!gHost.kabutoClockStarted) {
            gHost.kabutoClockStarted = gHost.kabutoEvents.begin(gHost.kabutoAttackClip, "key2");
            if (!gHost.kabutoClockStarted) {
                fail("kabuto clock begin failed");
            }
        }
        P2KabutoEvent events[4];
        int count = 0;
        if (!gHost.kabutoEvents.advance(1.0, events, 4, count)) {
            fail("kabuto clock advance failed");
        }
        for (int i = 0; i < count; ++i) {
            action = cannon.onEvent(events[i], host);
            if (action == P2KabutoAction::FireStone) {
                fireKabutoStone(cannon);
            }
            if (events[i] == P2KabutoEvent::End) {
                motionEnded = true;
            }
            if (action != P2KabutoAction::None) {
                logKabutoAction(action);
                logged = true;
            }
        }
    } else if (phase == P2KabutoPhase::Wait && gHost.kabutoTicks >= gHost.kabutoWaitTicks) {
        action = cannon.onEvent(P2KabutoEvent::End, host);
        motionEnded = true;
    } else if (phase == P2KabutoPhase::Turn && gHost.kabutoTicks >= gHost.kabutoTurnTicks) {
        action = cannon.onEvent(P2KabutoEvent::End, host);
        motionEnded = true;
    } else if (phase == P2KabutoPhase::Attack) {
        if (gHost.kabutoTicks == gHost.kabutoKey2Tick) {
            action = cannon.onEvent(P2KabutoEvent::Key2, host);
            if (action == P2KabutoAction::FireStone) {
                fireKabutoStone(cannon);
            }
        } else if (gHost.kabutoTicks >= gHost.kabutoAttackTicks) {
            action = cannon.onEvent(P2KabutoEvent::End, host);
            motionEnded = true;
        }
    }

    if (action != P2KabutoAction::None && !logged) {
        logKabutoAction(action);
    }
    if (motionEnded) {
        gHost.kabutoTicks = 0;
    }
}

bool withinEggRange(const Vector3f& p)
{
    const float dx = p.x - gHost.eggPos.x, dy = p.y - gHost.eggPos.y, dz = p.z - gHost.eggPos.z;
    return dx * dx + dy * dy + dz * dz <= kEggContactRadius * kEggContactRadius;
}

void logEggDrop(const P2EggDrop& drop)
{
    std::printf("P2_PROJECTILE_EGG_DROP type=%d items=%d fallback=%d offset_y=%.1f\n",
                int(drop.type), drop.itemCount, int(drop.mititeFallbackToNectar),
                drop.positionOffsetY);
    for (int i = 0; i < drop.itemCount && i < 2; ++i) {
        const P2EggItem& item = drop.items[i];
        std::printf("P2_PROJECTILE_EGG_ITEM index=%d kind=%d pellet_color=%d mitites=%d "
                    "vx=%.1f vy=%.1f vz=%.1f\n",
                    i, int(item.kind), item.pelletColor, item.mititeCount,
                    item.velocity.x, item.velocity.y, item.velocity.z);
    }
}

// Real child births for a broken Egg (#410, "real requested child births").
// Maps the P2EggDrop policy result onto the P1 managers that exist in this host:
//   PelletOne/Five -> pelletMgr->newNumberPellet(color, NUMPEL_*) with the
//                     source spawn velocity;
//   Nectar         -> itemMgr->birth(OBJTYPE_Water);
//   MititeGroup    -> the source createGroup-failure fallback to nectar
//                     (egg.cpp:351-360), since P1 has no Mitite manager;
//   Spicy/Bitter   -> P1 has no spray item and the policy only emits these when
//                     the family opts in with the first-spray demo flag, so the
//                     host reports them unsupported rather than inventing a drop.
void birthEggDrop(const P2EggDrop& drop)
{
    const Vector3f base(gHost.eggPos.x, gHost.eggPos.y + drop.positionOffsetY, gHost.eggPos.z);
    for (int i = 0; i < drop.itemCount && i < 2; ++i) {
        const P2EggItem& item = drop.items[i];
        P2EggSpawnKind kind = item.kind;
        bool fallback = false;
        if (kind == P2EggSpawnKind::MititeGroup && drop.mititeFallbackToNectar) {
            kind = P2EggSpawnKind::Nectar;
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
        std::printf("P2_PROJECTILE_EGG_BIRTH index=%d kind=%d real=%d fallback=%d item=%s "
                    "x=%.1f y=%.1f z=%.1f\n",
                    i, int(item.kind), int(birthed), int(fallback), born, base.x, base.y,
                    base.z);
    }
}

void tickEgg()
{
    P2Egg& egg = gHost.egg;
    ++gHost.eggTick;

    if (gHost.eggDropGroup && egg.health() > 0.0f) {
        bool touched = false;
        Navi* navi = naviMgr ? naviMgr->getNavi() : nullptr;
        if (navi && navi->isAlive() && withinEggRange(navi->mSRT.t)) {
            touched = true;
        }
        if (!touched) {
            Iterator it(pikiMgr);
            CI_LOOP(it) {
                Piki* piki = static_cast<Piki*>(*it);
                if (piki && piki->isAlive() && withinEggRange(piki->mSRT.t)) {
                    touched = true;
                    break;
                }
            }
        }
        // Non-null, non-Teki creature only (egg.cpp:178-186).
        if (touched && egg.contact(false, false)) {
            std::printf("P2_PROJECTILE_EGG_CONTACT drop_group=1 health_zeroed=1\n");
        }
    }

    if (!gHost.eggDamageApplied && gHost.eggDamage > 0.0f
        && gHost.eggTick >= gHost.eggDamageTick) {
        egg.damage(gHost.eggDamage);
        gHost.eggDamageApplied = true;
        std::printf("P2_PROJECTILE_EGG_DAMAGE amount=%.1f health=%.1f injected=1\n",
                    gHost.eggDamage, egg.health());
    }

    if (egg.health() <= 0.0f && egg.update(p2rockhost::rngFloat, &gHost.rng, p2rockhost::rngInt, &gHost.rng)) {
        logEggDrop(egg.drop());
        birthEggDrop(egg.drop());
        gHost.eggActive = false;
    }
}

void logRockTransition()
{
    const P2RockHazardPhase now = gHost.rock.phase();
    if (now == gHost.rockPrev) {
        return;
    }
    const P2RockHazardVec3 p = gHost.rock.position();
    std::printf("P2_PROJECTILE_ROCK_PHASE from=%s to=%s pos=(%.1f,%.1f,%.1f) scale=%.4f "
                "traces=%llu floors=%llu\n",
                rockPhaseName(gHost.rockPrev), rockPhaseName(now), p.x, p.y, p.z,
                gHost.rock.scale(),
                static_cast<unsigned long long>(gHost.rockBinding->calls()),
                static_cast<unsigned long long>(gHost.rockBinding->floors()));
    gHost.rockPrev = now;
}

// Host Wait detection approximation: 3D distance to the active Navi / any live
// Pikmin within mSightRadius (source runs EnemyFunc::isThereOlimar/isTherePikmin).
// The shared lane-20 p2rockhost::detectRock is used instead of a local fork.
P2RockHazardDetection rockDetection(const P2RockHazardVec3& from)
{
    return p2rockhost::detectRock(from, gHost.rockCfg.sightRadius);
}

void detectRockContacts()
{
    if (!gHost.rock.isAlive()) {
        return;
    }
    const P2RockHazardVec3 p = gHost.rock.position();
    const float radius = gHost.rockCfg.collisionRadius + kRockContactPad;
    const float radiusSq = radius * radius;
    auto consider = [&](Creature* creature, P2RockHazardContactKind kind) {
        if (!creature || !creature->isAlive()) {
            return;
        }
        const Vector3f& q = creature->mSRT.t;
        const float dx = q.x - p.x, dy = q.y - p.y, dz = q.z - p.z;
        if (dx * dx + dy * dy + dz * dz > radiusSq) {
            return;
        }
        const std::uint64_t token = tokenOf(creature);
        if (!gHost.rockContacts.insert(token).second) {
            return;
        }
        const P2RockHazardContactResult result =
            gHost.rock.contact(kind, onFloor(*creature), false, token);
        if (result.ignored) {
            std::printf("P2_PROJECTILE_ROCK_CONTACT_IGNORED kind=%s target=%llu\n",
                        rockContactKindName(kind), static_cast<unsigned long long>(token));
            return;
        }
        if (result.strikeEmitted) {
            const char* strike = result.strike.kind == P2RockHazardStrikeKind::Press ? "Press" : "Attack";
            std::printf("P2_PROJECTILE_ROCK_STRIKE kind=%s damage=%.1f target=%llu "
                        "attributed=%llu source=%d health_zeroed=%d\n",
                        strike, result.strike.damage,
                        static_cast<unsigned long long>(result.strike.targetToken),
                        static_cast<unsigned long long>(result.strike.attributedToken),
                        int(result.strike.attributedToSource), int(result.healthZeroed));
            logReceiverStrike(gHost.receivers.applyStrike(result));
            const bool attack = result.strike.kind == P2RockHazardStrikeKind::Attack;
            const bool targetIsTeki = kind == P2RockHazardContactKind::Teki;
            applyAndLogEngineStrike(creature, nullptr, attack, targetIsTeki, result.strike.damage);
        }
        if (result.healthZeroed) {
            std::printf("P2_PROJECTILE_ROCK_HEALTH_ZERO kind=%s target=%llu\n",
                        rockContactKindName(kind), static_cast<unsigned long long>(token));
        }
        if (result.selfCollisionSuppressed) {
            std::printf("P2_PROJECTILE_ROCK_SELF_SUPPRESSED target=%llu\n",
                        static_cast<unsigned long long>(token));
        }
    };
    consider(naviMgr ? naviMgr->getNavi() : nullptr, P2RockHazardContactKind::NaviPiki);
    if (pikiMgr) {
        Iterator pikiIt(pikiMgr);
        CI_LOOP(pikiIt) { consider(static_cast<Piki*>(*pikiIt), P2RockHazardContactKind::NaviPiki); }
    }
    if (tekiMgr) {
        Iterator tekiIt(tekiMgr);
        CI_LOOP(tekiIt) { consider(static_cast<Teki*>(*tekiIt), P2RockHazardContactKind::Teki); }
    }
}

void tickRock()
{
    if (!gHost.rockPending) {
        return;
    }
    P2RockHazard& rock = gHost.rock;
    if (!rock.isAlive()) {
        if (rock.phase() == P2RockHazardPhase::Dead) {
            gHost.rockDeadTimer += kSourceDelta;
            if (gHost.rockDeadTimer >= kRockDeadHoldSeconds && rock.finishDeath()) {
                std::printf("P2_PROJECTILE_ROCK_DESTROY reason=%s traces=%llu floors=%llu contacts=%llu\n",
                            rock.health() <= 0.0f ? "health" : "floor",
                            static_cast<unsigned long long>(gHost.rockBinding->calls()),
                            static_cast<unsigned long long>(gHost.rockBinding->floors()),
                            static_cast<unsigned long long>(gHost.rockContacts.size()));
                logRockTransition();
                gHost.rockPending = false;
            }
        }
        return;
    }

    const P2RockHazardDetection detection = rockDetection(rock.position());
    rock.update(kSourceDelta, detection, p2rockhost::RockMapBinding::trace, gHost.rockBinding);
    logRockTransition();
    detectRockContacts();
    logRockTransition();
}

// Second-consumer proof: exercise lane-21's Groink classifier end-to-end in the
// production room preview, without forking its modules. The configured muzzle
// origin aims at the live captain Navi; the classified Bomb strike is applied
// through THIS lane's real engine receiver (stimulate(InteractAttack) on the
// Navi), not the proxy registry, and the Navi health change is logged. Emits
// P2_PROJECTILE_GROINK_ENGINE_HIT exactly once; skipped until the captain exists.
void tickGroinkConsumer()
{
    if (!gHost.haveGroinkCfg || gHost.groinkApplied) {
        return;
    }
    Navi* navi = naviMgr ? naviMgr->getNavi() : nullptr;
    if (!navi || !navi->isAlive()) {
        return;
    }
    const Vector3f& p = navi->mSRT.t;
    P2GroinkHitCandidate candidate;
    candidate.position = { p.x, p.y, p.z };
    candidate.kind = P2GroinkCandidateKind::Captain;
    candidate.alive = true;
    candidate.owner = false;
    candidate.cellRadius = 10.0f;

    P2GroinkHitInput hit;
    hit.start = gHost.groinkOrigin;
    hit.end = { p.x, p.y, p.z };
    hit.radius = P2GroinkPolicy::kShellRadius;
    hit.terminalRadius = 65.0f;
    hit.damage = gHost.groinkDamage;
    hit.terminal = true;

    // lane-21's classifier decides the shell kind; this lane's engine receiver
    // applies the Bomb via the captain's own stimulate(InteractAttack) path.
    const P2GroinkHitCommand command = p2_groink_classify_hit(hit, candidate);
    const bool bomb = command.kind == P2GroinkHitKind::Bomb;
    const float damage = bomb ? command.damage : 0.0f;
    const P2ProjectileEngineHit result =
        p2_projectile_apply_engine_strike(navi, nullptr, bomb, false, damage);

    std::printf("P2_PROJECTILE_GROINK_ENGINE_HIT token=%llu kind=%s damage=%.1f "
                "applied=%d rejected=%d health=%.1f->%.1f\n",
                static_cast<unsigned long long>(tokenOf(navi)),
                bomb ? "Bomb" : "Wind", damage, int(result.applied),
                int(result.rejected), result.healthBefore, result.healthAfter);
    gHost.groinkApplied = true;
}

// Injected victim placement for the two-Teki proof: re-anchor every Teki other
// than the bound firer to the firer's transform each step, so the Stone's
// birth-frame contact finds the victim within collision radius regardless of the
// room's natural ~70-unit Dwarf settle separation. Labelled injected; the marker
// is emitted once at setup, not per step.
void pinVictimTeki()
{
    if (!gHost.pinVictim || !gHost.haveKabutoActor || !gHost.kabutoActor) {
        return;
    }
    const Vector3f& anchor = gHost.kabutoActor->mSRT.t;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* t = static_cast<Teki*>(*it);
        if (t && t != gHost.kabutoActor) {
            t->mSRT.t = anchor;
        }
    }
}

void step()
{
    pinVictimTeki();
    tickKabuto();
    if (gHost.stoneActive) {
        tickStone();
    }
    if (gHost.eggActive) {
        tickEgg();
    }
    tickRock();
    tickGroinkConsumer();
}
} // namespace

void pc_p2_projectiles_reset()
{
    gHost.haveStoneCfg = false;
    gHost.stoneActive = false;
    gHost.stone.reset(P2CannonStoneConfig{});
    gHost.stoneFaceDeg = 0.0f;
    gHost.stoneHoming = false;
    gHost.stoneSource = 0;
    gHost.stoneDeadTimer = 0.0;
    gHost.stoneContacts.clear();
    gHost.stoneSkippedSelf = false;
    gHost.haveEggCfg = false;
    gHost.eggActive = false;
    gHost.egg.reset(P2EggConfig{});
    gHost.eggTick = 0;
    gHost.eggDamageApplied = false;
    gHost.eggDamage = 0.0f;
    gHost.eggDamageTick = 0;
    gHost.haveKabutoCfg = false;
    gHost.kabutoCfg = P2KabutoCannonConfig{};
    gHost.kabutoSpecies = P2KabutoSpecies::Kabuto;
    gHost.kabutoMouthJoint = P2CannonStoneVec3{};
    gHost.kabutoFaceDeg = 0.0f;
    gHost.kabutoWaitTicks = kKabutoWaitTicks;
    gHost.kabutoTurnTicks = kKabutoTurnTicks;
    gHost.kabutoAttackTicks = kKabutoAttackTicks;
    gHost.kabutoKey2Tick = kKabutoKey2Tick;
    gHost.kabuto.reset(P2KabutoCannonConfig{}, P2KabutoSpecies::Kabuto);
    gHost.kabutoTicks = 0;
    gHost.kabutoFires = 0;
    gHost.haveKabutoRig = false;
    gHost.kabutoRigPath.clear();
    gHost.kabutoRigOrigin = p2attach::Vec{};
    gHost.kabutoRigFaceDeg = 0.0f;
    gHost.kabutoBank.reset();
    gHost.kabutoAttachment.reset();
    gHost.kabutoAttachmentToken = 0;
    gHost.kabutoMuzzle = P2KabutoMuzzle{};
    gHost.kabutoRigTick = 0;
    gHost.haveKabutoActor = false;
    gHost.kabutoActorGenerator = 0;
    gHost.kabutoActor = nullptr;
    gHost.haveKabutoClock = false;
    gHost.kabutoClockPath.clear();
    gHost.kabutoAttackClip = p2sampled::Clip{};
    gHost.kabutoEvents = P2KabutoEventAdapter{};
    gHost.kabutoClockStarted = false;
    gHost.haveRockCfg = false;
    gHost.rockCfg = P2RockHazardConfig{};
    gHost.rockInit = P2RockHazardInit{};
    gHost.rock.reset(P2RockHazardConfig{});
    gHost.rockPrev = P2RockHazardPhase::Inactive;
    gHost.rockPending = false;
    gHost.rockDeadTimer = 0.0;
    gHost.rockContacts.clear();
    gHost.receivers.reset();
    gHost.engineReceiver = false;
    gHost.haveGroinkCfg = false;
    gHost.groinkOrigin = P2GroinkVec3{};
    gHost.groinkDamage = 0.0f;
    gHost.groinkApplied = false;
    gHost.pinVictim = false;
    gHost.sawTekiPinRow = false;
    gHost.rng.state = 1u;
    gHost.debt = 0.0;
    if (gHost.binding) {
        gHost.binding->reset(nullptr);
    }
    if (gHost.rockBinding) {
        gHost.rockBinding->reset(nullptr);
    }
}

void pc_p2_projectiles_forget(BTeki* actor)
{
    // Clear the contact dedupe so a recycled Teki pointer can never suppress a
    // fresh contact, and drop the bound Kabuto actor reference if it is the one
    // being forgotten (otherwise a later grounded Navi/Pikmin strike would hand
    // a dangling pointer to InteractPress(owner) -> playEventSound(mOwner)).
    if (actor && actor == gHost.kabutoActor) {
        gHost.kabutoActor = nullptr;
    }
    gHost.stoneContacts.clear();
    gHost.rockContacts.clear();
}

void pc_p2_projectiles_setup()
{
    pc_p2_projectiles_reset();
    if (!pc_pikipelago_room_preview() || !mapMgr) {
        return;
    }
    std::ifstream probe("p2-projectiles.txt");
    if (!probe) {
        return; // opt-in: absent config -> P1 fallback
    }
    probe.close();

    if (!gHost.binding) {
        gHost.binding = new ProjectileMapBinding();
    }
    if (!gHost.rockBinding) {
        gHost.rockBinding = new p2rockhost::RockMapBinding();
    }
    gHost.binding->reset(mapMgr);
    gHost.rockBinding->reset(mapMgr);
    parseConfig("p2-projectiles.txt");

    if (gHost.haveKabutoCfg) {
        // FSM-driven birth (#425): the Stone is born from the Kabuto FireStone
        // action, using the configured mouth joint and species homing.
        gHost.kabuto.reset(gHost.kabutoCfg, gHost.kabutoSpecies);
        if (!gHost.kabuto.start()) {
            fail("kabuto start failed");
        }
        gHost.kabutoTicks = 0;
        gHost.kabutoFires = 0;
        if (gHost.haveKabutoRig) {
            // Load the species attachment bank and bind the moving muzzle. The
            // bank is an authored sidecar; a failed parse or unresolved species
            // clip/joint fails closed.
            std::ifstream bankIn(gHost.kabutoRigPath);
            gHost.kabutoBank = p2attach::read(bankIn);
            if (!gHost.kabutoBank) {
                fail("kabuto_rig bank parse failed");
            }
            gHost.kabutoAttachmentToken = gHost.kabutoAttachment.bind(gHost.kabutoBank);
            if (gHost.kabutoAttachmentToken == 0
                || !gHost.kabutoMuzzle.bind(*gHost.kabutoBank, gHost.kabutoSpecies)) {
                fail("kabuto_rig resolve failed");
            }
            gHost.kabutoRigTick = 0;
            std::printf("P2_PROJECTILE_KABUTO_RIG clip=%s joint=%d fire_frame=%d "
                        "origin=(%.1f,%.1f,%.1f)\n",
                        gHost.kabutoBank->clips[gHost.kabutoMuzzle.binding().clip].name.c_str(),
                        gHost.kabutoMuzzle.binding().joint,
                        gHost.kabutoMuzzle.binding().fireFrame, gHost.kabutoRigOrigin.x,
                        gHost.kabutoRigOrigin.y, gHost.kabutoRigOrigin.z);
        }
        if (gHost.haveKabutoClock) {
            // Load the P2_ANIM_CLOCK_1 sidecar and resolve the species attack clip.
            std::ifstream clockIn(gHost.kabutoClockPath);
            std::vector<p2sampled::Clip> clips;
            if (!p2sampled::parse(clockIn, clips)) {
                fail("kabuto_clock parse failed");
            }
            const char* wanted = p2_kabuto_mouth_clip(gHost.kabutoSpecies).clip;
            const p2sampled::Clip* found = nullptr;
            for (const p2sampled::Clip& clip : clips) {
                if (clip.poses.name == wanted || iequals(clip.poses.name.c_str(), wanted)) {
                    found = &clip;
                    break;
                }
            }
            if (!found) {
                fail("kabuto_clock attack clip missing");
            }
            gHost.kabutoAttackClip = *found;
            gHost.kabutoClockStarted = false;
            std::printf("P2_PROJECTILE_KABUTO_CLOCK clip=%s events=%zu first_frame=%d\n",
                        gHost.kabutoAttackClip.poses.name.c_str(),
                        gHost.kabutoAttackClip.events.size(),
                        gHost.kabutoAttackClip.events.empty()
                            ? -1
                            : gHost.kabutoAttackClip.events[0].frame);
        }
        if (gHost.haveKabutoActor) {
            // Bind the live Teki with the configured generator; the muzzle owner
            // then follows its world transform and facing.
            Iterator actors(tekiMgr);
            CI_LOOP(actors) {
                Teki* candidate = static_cast<Teki*>(*actors);
                if (candidate && candidate->mGenerator
                    && candidate->mGenerator->_70 == gHost.kabutoActorGenerator) {
                    gHost.kabutoActor = candidate;
                    break;
                }
            }
            if (!gHost.kabutoActor) {
                // Diagnostic: report every live Teki generator so a misconfigured
                // `kabuto_actor` row can be corrected from the log instead of a
                // silent/opaque abort.
                Iterator all(tekiMgr);
                CI_LOOP(all) {
                    Teki* candidate = static_cast<Teki*>(*all);
                    if (candidate) {
                        std::printf("P2_PROJECTILE_KABUTO_ACTOR_CAND type=%d gen=%u pos=(%.1f,%.1f,%.1f)\n",
                                    int(candidate->mTekiType),
                                    candidate->mGenerator ? candidate->mGenerator->_70 : 0u,
                                    candidate->mSRT.t.x, candidate->mSRT.t.y, candidate->mSRT.t.z);
                    }
                }
                fail("kabuto_actor generator not found");
            }
            const Vector3f& p = gHost.kabutoActor->mSRT.t;
            std::printf("P2_PROJECTILE_KABUTO_ACTOR generator=%u bound=1 type=%d pos=(%.1f,%.1f,%.1f)\n",
                        gHost.kabutoActorGenerator, int(gHost.kabutoActor->mTekiType),
                        p.x, p.y, p.z);
            // Two-Teki diagnostic: list every live Teki (including the victim) so
            // runtime evidence can confirm the victim's distinct token/position
            // beside the bound firer.
            {
                Iterator all(tekiMgr);
                CI_LOOP(all) {
                    Teki* t = static_cast<Teki*>(*all);
                    if (t) {
                        std::printf("P2_PROJECTILE_TEKI_ROSTER token=%llu type=%d gen=%u pos=(%.1f,%.1f,%.1f)\n",
                                    static_cast<unsigned long long>(tokenOf(t)),
                                    int(t->mTekiType),
                                    t->mGenerator ? t->mGenerator->_70 : 0u,
                                    t->mSRT.t.x, t->mSRT.t.y, t->mSRT.t.z);
                    }
                }
            }
            if (gHost.pinVictim) {
                std::printf("P2_PROJECTILE_TEKI_PIN injected=1 anchor=%llu\n",
                            static_cast<unsigned long long>(tokenOf(gHost.kabutoActor)));
            }
        }
        std::printf("P2_PROJECTILE_KABUTO_READY species=%s mouth=(%.1f,%.1f,%.1f) face_deg=%.1f "
                    "max_attack_angle=%.1f health=%.1f wait=%d turn=%d attack=%d key2=%d\n",
                    kabutoSpeciesName(gHost.kabutoSpecies), gHost.kabutoMouthJoint.x,
                    gHost.kabutoMouthJoint.y, gHost.kabutoMouthJoint.z, gHost.kabutoFaceDeg,
                    gHost.kabutoCfg.maxAttackAngle, gHost.kabutoCfg.health,
                    gHost.kabutoWaitTicks, gHost.kabutoTurnTicks, gHost.kabutoAttackTicks,
                    gHost.kabutoKey2Tick);
    } else if (gHost.haveStoneCfg) {
        // No FSM configured: keep the #413 static host birth.
        gHost.stone.reset(gHost.stoneCfg);
        const float faceRad = gHost.stoneFaceDeg * kPi / 180.0f;
        if (!gHost.stone.birth(gHost.stonePos, faceRad, gHost.stoneHoming,
                               gHost.stoneSource, gHost.stoneSelf)) {
            fail("stone birth failed");
        }
        gHost.stoneActive = true;
        gHost.stoneSkippedSelf = false;
        std::printf("P2_PROJECTILE_STONE_BORN x=%.1f y=%.1f z=%.1f face_deg=%.1f "
                    "homing=%d source=%llu radius=%.1f\n",
                    gHost.stonePos.x, gHost.stonePos.y, gHost.stonePos.z,
                    gHost.stoneFaceDeg, int(gHost.stoneHoming),
                    static_cast<unsigned long long>(gHost.stoneSource),
                    gHost.stoneCfg.collisionRadius);
    }
    if (gHost.haveRockCfg) {
        gHost.rock.reset(gHost.rockCfg);
        if (!gHost.rock.onInit(gHost.rockInit)) {
            fail("rock birth failed");
        }
        gHost.rockPending = true;
        gHost.rockPrev = P2RockHazardPhase::Inactive;
        logRockTransition();
    }
    if (gHost.haveEggCfg) {
        gHost.egg.reset(gHost.eggCfg);
        if (!gHost.egg.birth(gHost.eggDropGroup)) {
            fail("egg birth failed");
        }
        gHost.eggActive = true;
        std::printf("P2_PROJECTILE_EGG_BORN x=%.1f y=%.1f z=%.1f drop_group=%d health=%.1f\n",
                    gHost.eggPos.x, gHost.eggPos.y, gHost.eggPos.z,
                    int(gHost.eggDropGroup), gHost.eggCfg.health);
    }
    std::printf("P2_PROJECTILES_READY stone=%d egg=%d kabuto=%d rock=%d seed=%u\n",
                int(gHost.haveStoneCfg), int(gHost.haveEggCfg), int(gHost.haveKabutoCfg),
                int(gHost.haveRockCfg), gHost.rng.state);
    std::fflush(stdout);
}

void pc_p2_projectiles_update()
{
    const bool anyActive = gHost.stoneActive || gHost.eggActive || gHost.rockPending
        || (gHost.haveKabutoCfg && gHost.kabuto.isAlive())
        || (gHost.haveGroinkCfg && !gHost.groinkApplied);
    if (!gsys || !anyActive) {
        return;
    }
    const bool active = !gameflow.mPauseAll && !gameflow.mIsUIOverlayActive
        && !(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive);
    if (!active) {
        return;
    }
    gHost.debt += gsys->getFrameTime();
    int ticks = static_cast<int>(gHost.debt / kSourceDelta);
    if (ticks > kMaxTicksPerFrame) {
        ticks = kMaxTicksPerFrame;
    }
    gHost.debt -= ticks * static_cast<double>(kSourceDelta);
    for (int i = 0; i < ticks; ++i) {
        step();
    }
}
