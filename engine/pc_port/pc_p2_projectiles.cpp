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
#include "pc_p2_egg_hazard.h"
#include "pc_p2_kabuto_cannon.h"
#include "pc_p2_projectile_host.h"
#include "pc_p2_projectile_receiver.h"
#include "pc_p2_rock_hazard.h"
#include "pc_bbft.h"
#include "Creature.h"
#include "MapMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "MoviePlayer.h"
#include "gameflow.h"
#include "system.h"
#include "teki.h"
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
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

// P1 trace proxy. It is never registered with an actor manager; its collision
// fields are used only for the static-map probe (same pattern as
// P2BombSaraiTraceProxy, #244).
class ProjectileTraceProxy : public Creature {
public:
    ProjectileTraceProxy() : Creature(nullptr) { clear(); }
    void clear()
    {
        wall = false;
        mGroundTriangle = nullptr;
        mCollisionOccurred = 0;
        mHasCollChangedVelocity = 0;
        mCurrCollisionModel = nullptr;
        mCollPlatform = nullptr;
        mCollNormal = nullptr;
        mPikiPlatformTriangle = nullptr;
    }
    void refresh(Graphics&) override {}
    void wallCallback(immut Plane&, DynCollObject*) override { wall = true; }
    bool wall = false;
protected:
    void doKill() override {}
};

// Binds the Stone trace primitive to the P1 static map. center/base conversion
// is owned here: P1 traceMove adds the radius before collision and subtracts it
// afterward, so the policy's center is lowered by the radius for the trace and
// the raw result is raised back.
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
    ProjectileTraceProxy mProxy;
    std::uint64_t mCalls = 0, mFloors = 0, mWalls = 0;
};

// Binds the falling-Rock trace primitive to the P1 static map. The Rock policy
// stores its position as the sphere center, so the same center/base conversion
// as ProjectileMapBinding is applied. `colliding` is host-owned (P1 has no
// EB_Colliding); floor contact is reported through mGroundTriangle.
class RockMapBinding {
public:
    void reset(MapMgr* map) { mMap = map; mProxy.clear(); mCalls = mFloors = 0; }

    static bool trace(void* context, const P2RockHazardVec3& center,
                      const P2RockHazardVec3& velocity, float delta, float radius,
                      P2RockHazardTraceResult& result)
    {
        if (!context || !finite(center.x) || !finite(center.y) || !finite(center.z)
            || !finite(velocity.x) || !finite(velocity.y) || !finite(velocity.z)
            || !finite(delta) || std::fabs(delta - kSourceDelta) > 0.000001f
            || !finite(radius) || radius <= 0.0f) {
            return false;
        }
        RockMapBinding& self = *static_cast<RockMapBinding*>(context);
        if (!self.mMap || !self.mMap->mMapModel) {
            return false;
        }
        self.mProxy.clear();
        const Vector3f base(center.x, center.y - radius, center.z);
        MoveTrace movement(base, Vector3f(velocity.x, velocity.y, velocity.z), radius, true);
        self.mMap->traceMove(&self.mProxy, movement, delta);
        ++self.mCalls;
        result.position = { movement.mPosition.x, movement.mPosition.y + radius, movement.mPosition.z };
        result.velocity = { movement.mVelocity.x, movement.mVelocity.y, movement.mVelocity.z };
        result.floorTriangle = self.mProxy.mGroundTriangle != nullptr;
        result.colliding = false;
        if (!finite(result.position.x) || !finite(result.position.y) || !finite(result.position.z)
            || !finite(result.velocity.x) || !finite(result.velocity.y) || !finite(result.velocity.z)) {
            return false;
        }
        self.mFloors += result.floorTriangle;
        return true;
    }

    std::uint64_t calls() const { return mCalls; }
    std::uint64_t floors() const { return mFloors; }

private:
    MapMgr* mMap = nullptr;
    ProjectileTraceProxy mProxy;
    std::uint64_t mCalls = 0, mFloors = 0;
};

// Deterministic scripted RNG for the Egg policy (the host owns the source).
struct ScriptRng {
    std::uint32_t state = 1u;
    float next()
    {
        state = state * 1664525u + 1013904223u;
        return static_cast<float>((state >> 8) & 0xffffffu) / 16777216.0f;
    }
    int nextInt(int count)
    {
        if (count <= 0) {
            return 0;
        }
        int value = static_cast<int>(next() * static_cast<float>(count));
        if (value >= count) {
            value = count - 1;
        }
        return value;
    }
};

float rngFloat(void* context) { return static_cast<ScriptRng*>(context)->next(); }
int rngInt(void* context, int count) { return static_cast<ScriptRng*>(context)->nextInt(count); }

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
    RockMapBinding* rockBinding = nullptr;

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

    ScriptRng rng;
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
        } else {
            fail("invalid config token");
        }
    }
    if (gHost.haveKabutoCfg && !gHost.haveStoneCfg) {
        fail("kabuto requires a stone row");
    }
    if (!gHost.haveStoneCfg && !gHost.haveEggCfg && !gHost.haveRockCfg) {
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

// Host-driven automatic attack cycle: Wait -> Turn -> Attack -> KEYEVENT_2 ->
// END, one source tick at a time. The cycle freezes while a Stone is in flight
// so the FSM sequence is clean and exactly one Stone is active at a time.
void tickKabuto()
{
    P2KabutoCannon& cannon = gHost.kabuto;
    if (!cannon.isAlive() || gHost.stoneActive) {
        return;
    }

    const P2CannonStoneVec3 origin = gHost.kabutoMouthJoint;
    const P2CannonStoneTarget target = selectHostTarget(origin, gHost.stoneCfg.sightRadius);

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

    if (phase == P2KabutoPhase::Wait && gHost.kabutoTicks >= gHost.kabutoWaitTicks) {
        action = cannon.onEvent(P2KabutoEvent::End, host);
        motionEnded = true;
    } else if (phase == P2KabutoPhase::Turn && gHost.kabutoTicks >= gHost.kabutoTurnTicks) {
        action = cannon.onEvent(P2KabutoEvent::End, host);
        motionEnded = true;
    } else if (phase == P2KabutoPhase::Attack) {
        if (gHost.kabutoTicks == gHost.kabutoKey2Tick) {
            action = cannon.onEvent(P2KabutoEvent::Key2, host);
            if (action == P2KabutoAction::FireStone) {
                P2KabutoStoneBirth birth;
                const float faceRad = gHost.kabutoFaceDeg * kPi / 180.0f;
                if (!cannon.takeBirth(gHost.kabutoMouthJoint, faceRad, birth)) {
                    fail("kabuto takeBirth failed");
                }
                gHost.stone.reset(gHost.stoneCfg);
                if (!gHost.stone.birth(birth.mouthPosition, birth.faceDir, birth.homing,
                                       gHost.kabutoSelf, gHost.stoneSelf)) {
                    fail("kabuto stone birth failed");
                }
                gHost.stoneActive = true;
                gHost.stoneDeadTimer = 0.0;
                ++gHost.kabutoFires;
                std::printf("P2_PROJECTILE_KABUTO_FIRE species=%s homing=%d mouth=(%.1f,%.1f,%.1f) "
                            "birth=(%.1f,%.1f,%.1f) face_deg=%.1f source=%llu fire=%d\n",
                            kabutoSpeciesName(cannon.species()), int(birth.homing),
                            gHost.kabutoMouthJoint.x, gHost.kabutoMouthJoint.y,
                            gHost.kabutoMouthJoint.z, birth.mouthPosition.x,
                            birth.mouthPosition.y, birth.mouthPosition.z, gHost.kabutoFaceDeg,
                            static_cast<unsigned long long>(gHost.kabutoSelf), gHost.kabutoFires);
            }
        } else if (gHost.kabutoTicks >= gHost.kabutoAttackTicks) {
            action = cannon.onEvent(P2KabutoEvent::End, host);
            motionEnded = true;
        }
    }

    if (action != P2KabutoAction::None) {
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

    if (egg.health() <= 0.0f && egg.update(rngFloat, &gHost.rng, rngInt, &gHost.rng)) {
        logEggDrop(egg.drop());
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
P2RockHazardDetection rockDetection(const P2RockHazardVec3& from)
{
    P2RockHazardDetection detection;
    const float sightSq = gHost.rockCfg.sightRadius * gHost.rockCfg.sightRadius;
    auto inRange = [&](const Creature* creature) {
        const Vector3f& p = creature->mSRT.t;
        const float dx = p.x - from.x, dy = p.y - from.y, dz = p.z - from.z;
        return dx * dx + dy * dy + dz * dz <= sightSq;
    };
    Navi* navi = naviMgr ? naviMgr->getNavi() : nullptr;
    if (navi && navi->isAlive() && inRange(navi)) {
        detection.olimarInSight = true;
    }
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* piki = static_cast<Piki*>(*it);
            if (piki && piki->isAlive() && inRange(piki)) {
                detection.pikminInSight = true;
                break;
            }
        }
    }
    return detection;
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
    rock.update(kSourceDelta, detection, RockMapBinding::trace, gHost.rockBinding);
    logRockTransition();
    detectRockContacts();
    logRockTransition();
}

void step()
{
    tickKabuto();
    if (gHost.stoneActive) {
        tickStone();
    }
    if (gHost.eggActive) {
        tickEgg();
    }
    tickRock();
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
    gHost.haveRockCfg = false;
    gHost.rockCfg = P2RockHazardConfig{};
    gHost.rockInit = P2RockHazardInit{};
    gHost.rock.reset(P2RockHazardConfig{});
    gHost.rockPrev = P2RockHazardPhase::Inactive;
    gHost.rockPending = false;
    gHost.rockDeadTimer = 0.0;
    gHost.rockContacts.clear();
    gHost.receivers.reset();
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
    // This host holds no engine-actor references. Clear the contact dedupe so a
    // recycled Teki pointer can never suppress a fresh contact.
    (void)actor;
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
        gHost.rockBinding = new RockMapBinding();
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
        || (gHost.haveKabutoCfg && gHost.kabuto.isAlive());
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
