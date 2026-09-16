// Family-owned Long Legs native path (#312, parent #173).
//
// Registers the arena's P1 placement vehicles by generator ID from
// `p2-long-legs-actors.txt` (P2_LONG_LEGS_ACTORS_1), draws the installed static
// bind shape (`longlegs_<species>_bind_00.mod`), and advances the lane-owned
// source policy `pc_p2_long_legs_fsm` for each registered actor.
//
// The port has no IKSystemMgr, animation-event reader, foot collision or shell
// pool, so the policy is ticked from the draw path (which the engine calls every
// frame for on-camera registered actors) and the animation key edges are
// synthesized from the source animation key frames in the audit (30 fps). The
// policy only emits intents: foot crush, shake, shell request and death bursts
// are logged/observed, not applied. IK stability, real foot-press collision,
// Man-at-Legs shell objects and damage receivers remain lane work (#173/#186).
//
// Slice 2: the Houdai host now exposes a source damageable window and consumes
// lane 20's shared fired-projectile primitive (`pc_p2_cannon_stone.h`, the Stone
// policy/pool, #169) to fly a Man-at-Legs shell and route the source
// HoudaiShotGun damage (`InteractBomb` shellDamage 10) into a real Pikmin. The
// Stone's rolling/homing flight is a documented approximation of the source
// THdamaShell; the in-flight pool mirrors the source pool of 10.
#include "pc_p2_long_legs.h"
#include "pc_p2_long_legs_fsm.h"
#include "pc_p2_cannon_stone.h"
#include "pc_p2_animation.h"
#include "pc_bbft.h"
#include "teki.h"
#include "Pellet.h"
#include "Interactions.h"
#include "Generator.h"
#include "Shape.h"
#include "Texture.h"
#include "Graphics.h"
#include "Camera.h"
#include "gameflow.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <map>
#include <set>
#include <string>
#include <vector>

namespace {
struct SpeciesDef {
    const char* name;
    const char* mod;
};
const SpeciesDef SPECIES[] = {
    {"Houdai", "longlegs_Houdai_bind_00.mod"},
    {"BigFoot", "longlegs_BigFoot_bind_00.mod"},
};
constexpr size_t MeshBytes = 4 * 1024 * 1024;    // per species
constexpr size_t TotalBytes = 16 * 1024 * 1024;  // per setup
constexpr float AccumulateRadius = 60.0f;        // Pikmin "accumulating" census

struct ActorState {
    std::string species;
    unsigned generator = 0;
    P2LongLegsFsmParms parms;
    P2LongLegsFsm fsm;
    float animSeconds = 0.0f;   // time in the current state (source-key edges)
    bool key2Fired = false;
    float lastHealth = 0.0f;        // host damage edge for the Houdai shot cooldown
    float lastPositiveHealth = 0.0f; // last still-positive health, for death provenance
    P2LongLegsState lastState = P2LongLegsState::Stay;
    bool stateLogged = false;
    bool damageable = false;        // source damage window (Wait/Flick/Walk/Shot)
    bool bitterImmune = true;       // Stay/Land immunity
    float shotLoopAccum = 0.0f;     // Man-at-Legs attack-loop shell cadence
    Vector3f homePos;               // spawn position (source mHomePosition)
    Vector3f walkTarget;            // source mTargetPosition for the current Walk
    Vector3f walkStart;             // position at Walk entry (displacement measure)
    float walkDistance = 0.0f;      // accumulated body translation this Walk
    float walkSeconds = 0.0f;       // time spent in the current Walk
    bool hasWalkTarget = false;
    float lastMoveRatio = 1.0f;     // measured translation ratio fed to crushGate
    bool homeRecorded = false;
};

std::map<BTeki*, ActorState> actors;      // actor -> species + policy state
// Naturally dead Long Legs proxy corpses, keyed on the corpse Pellet* the engine
// created (PelletView::mPellet). A number-pellet stand-in corpse has no
// PelletView, so the receipt must key on the Pellet* (mirrors lane 31 Waterwraith).
std::map<Pellet*, unsigned> corpses;      // corpse pellet -> generator
std::map<std::string, Shape*> shapes;     // species -> bind shape
size_t bytesTotal = 0;
bool logged[2] = {false, false};

// Drop a registered corpse that died/vanished before it was delivered. The
// registry is keyed on the corpse Pellet*, and MonoObjectMgr recycles slots, so
// without this a future unrelated pellet at the same address could be credited as
// a Long Legs corpse. Mirrors lane 31's Waterwraith sweepCorpses()
// (pc_p2_waterwraith_register.cpp:48-58).
//
// Called from pc_p2_long_legs_corpse_count() (the fixture's observation point),
// NOT from the per-frame tick: an unconditional tick sweep dereferences the
// engine-owned corpse Pellet* every frame and stalled the stage-2 FSM in the
// merged wave (naviMgr went null). reset() clears the whole registry and
// forget() erases the forgotten actor's corpse, so the live tick does not need
// to sweep. A corpse that dies undelivered is still dropped the next time the
// registry is observed (or cleared), which is the slot-reuse protection.
void sweepCorpses() {
    for (auto it = corpses.begin(); it != corpses.end();) {
        if (!it->first->isAlive()) {
            std::printf("P2_LONG_LEGS_CORPSE_DROPPED generator=%u\n", it->second);
            std::fflush(stdout);
            it = corpses.erase(it);
        } else {
            ++it;
        }
    }
}

// Man-at-Legs shell pool (source pool of 10, HoudaiShotGun.cpp:1050) hosted on
// lane 20's shared fired-projectile policy. Consume-only: no forked projectile.
// Each shell remembers its firing actor (sourceToken) so a forget/death can kill
// only that actor's shells and two live Houdai never step each other's shells.
struct HoudaiShell {
    P2CannonStone* stone = nullptr;
    std::uint64_t sourceToken = 0;
};
P2CannonStonePool shellPool(10);
std::vector<HoudaiShell> shells;           // active shells, keyed by sourceToken
std::uint64_t shellSelfToken = 1;

[[noreturn]] void fail(const char* what) {
    std::fprintf(stderr, "P2_LONG_LEGS %s\n", what);
    std::abort();
}

const SpeciesDef* findSpecies(const std::string& name) {
    for (const SpeciesDef& species : SPECIES)
        if (name == species.name) return &species;
    return nullptr;
}

P2LongLegsSpecies speciesEnum(const std::string& name) {
    if (name == "BigFoot") return P2LongLegsSpecies::BigFoot;
    return P2LongLegsSpecies::Houdai;
}

// Source animation key frames (docs/PIKMIN2_LONG_LEGS_AUDIT.md) converted to
// seconds at 30 fps. Landing runs to the last landing key; Flick to the last
// flick key. Used only to synthesize the missing key edges in this fixture.
float landingSeconds(P2LongLegsSpecies species) {
    // Source Land (frames): Damagumo/Houdai 150, BigFoot 18.
    return species == P2LongLegsSpecies::BigFoot ? 18.0f / 30.0f : 150.0f / 30.0f;
}
float flickSeconds(P2LongLegsSpecies species) {
    // Source Flick (frames): Damagumo/Houdai 68, BigFoot 35.
    return species == P2LongLegsSpecies::BigFoot ? 35.0f / 30.0f : 68.0f / 30.0f;
}
float shotSeconds(P2LongLegsSpecies species) {
    // Houdai attack clip is 39 frames (Houdai.h); the gunless species never shoot.
    return species == P2LongLegsSpecies::Houdai ? 39.0f / 30.0f : 0.0f;
}
constexpr float kShellLoopPeriod = 5.0f / 30.0f; // one shell per attack loop (<-> frame 35)
constexpr float kShellHitRadius = 30.0f;         // shell radius 10 + contact margin over the +25 mouth y

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

// Source Houdai::getTargetPosition default (Houdai.cpp:313-349, via
// setTargetPattern: nearest navi or piki), consumed by StateWalk::init
// (HoudaiState.cpp:340-350, startIKMotion + getTargetPosition). The port has no
// IKSystemMgr, so the chosen target drives body translation at the source
// species speed instead of an IK motion; the target rule itself is source.
// A live target is taken as-is (source takes the Pikmin position); a missing
// target falls back to the source random territory-ring point around home
// (homeRadius + rand*(territory-homeRadius)).
Vector3f pickWalkTarget(const Vector3f& pos, const Vector3f& home,
                        const P2LongLegsFsmParms& parms)
{
    Creature* prey = nearestTarget(pos, parms.territoryRadius);
    if (prey) {
        Vector3f target = prey->getPosition();
        const float dx = target.x - home.x, dz = target.z - home.z;
        const float dist = std::sqrt(dx * dx + dz * dz);
        if (dist > parms.territoryRadius && dist > 1.0e-6f) {
            target.x = home.x + dx / dist * parms.territoryRadius;
            target.z = home.z + dz / dist * parms.territoryRadius;
        }
        return target;
    }
    const float range = parms.territoryRadius - parms.homeRadius;
    const float leg = parms.homeRadius + (range > 0.0f && gsys ? gsys->getRand(range) : 0.0f);
    const float ang = gsys ? gsys->getRand(6.2831853f) : 0.0f;
    return Vector3f(home.x + leg * std::sin(ang), home.y, home.z + leg * std::cos(ang));
}

int countPikiWithin(const Vector3f& pos, float radius) {
    int count = 0;
    if (!pikiMgr) return 0;
    const float rSq = radius * radius;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive()) continue;
        const Vector3f q = p->getPosition();
        const float dx = q.x - pos.x, dz = q.z - pos.z;
        if (dx * dx + dz * dz <= rSq) ++count;
    }
    return count;
}

// Man-at-Legs shell (consume lane 20 `P2CannonStone`; no forked projectile).
// Fired on the Shot loop boundary and stepped each tick; on contact with a live
// Pikmin the source HoudaiShotGun receiver (InteractBomb shellDamage) is applied.
// Documented approximations: the flight is the Stone's flat homing plan (no
// source gravity arc), contact is a flat 20-unit sphere (`kShellHitRadius`) keyed
// on the shell's elevated mouth y, and `nearestTarget` may select the Navi, which
// a shell can home on but never damages (InteractBomb is only routed to Pikmin).
void fireHoudaiShell(BTeki* actor, const Vector3f& pos) {
    Creature* target = nearestTarget(pos, 200.0f); // source shot search range
    if (!target) return;
    const Vector3f tp = target->getPosition();
    const float faceDir = std::atan2(tp.x - pos.x, tp.z - pos.z);
    P2CannonStoneConfig cfg;
    cfg.variant = P2CannonStoneVariant::Stone;
    cfg.moveSpeed = 600.0f;          // source shell speed (HoudaiShotGun.cpp:1193)
    cfg.searchRumbleSpeed = 600.0f;
    cfg.turnSpeed = 0.1f;            // homing steering fraction (approximation)
    cfg.maxTurnAngle = 180.0f;       // unrestricted homing sweep
    cfg.attackDamage = 10.0f;        // source Navi/Piki shell damage (HoudaiShotGun.cpp:227)
    cfg.sightRadius = 0.0f;
    cfg.collisionRadius = 10.0f;     // source shell trace radius
    cfg.health = 1.0f;
    P2CannonStoneVec3 mouth{ pos.x, pos.y + 25.0f, pos.z }; // source mouth offset
    P2CannonStone* s = shellPool.spawn(mouth, faceDir, true,
                                       (std::uint64_t)(std::uintptr_t)actor,
                                       shellSelfToken++, cfg);
    if (s) shells.push_back(HoudaiShell{s, (std::uint64_t)(std::uintptr_t)actor});
}

// Kill and drop every in-flight shell owned by `actor`, freeing its pool slots.
// Called on the host death path and on forget so a dead/forgotten Houdai never
// leaks shells (and a re-entered one regains the full 10-slot pool).
void killShellsOf(BTeki* actor) {
    const std::uint64_t token = (std::uint64_t)(std::uintptr_t)actor;
    for (HoudaiShell& shell : shells) {
        if (shell.sourceToken != token || !shell.stone) continue;
        shell.stone->notifyWallContact();
        shell.stone->finishDeath();
    }
    shells.erase(std::remove_if(shells.begin(), shells.end(),
                                [token](const HoudaiShell& s) { return s.sourceToken == token; }),
                 shells.end());
}

int countShellsOf(BTeki* actor) {
    const std::uint64_t token = (std::uint64_t)(std::uintptr_t)actor;
    int count = 0;
    for (const HoudaiShell& shell : shells)
        if (shell.sourceToken == token && shell.stone && shell.stone->isAlive()) ++count;
    return count;
}

void stepHoudaiShells(BTeki* actor, const std::string& species, unsigned generator) {
    if (shells.empty() || !pikiMgr) return;
    const std::uint64_t token = (std::uint64_t)(std::uintptr_t)actor;
    int hitTotal = 0;
    for (size_t i = 0; i < shells.size();) {
        HoudaiShell& shell = shells[i];
        if (shell.sourceToken != token) { ++i; continue; }  // only step this actor's shells
        P2CannonStone* s = shell.stone;
        if (!s || !s->isAlive()) { shells.erase(shells.begin() + i); continue; }
        const P2CannonStoneVec3 sp = s->position();
        P2CannonStoneTarget tgt;
        Creature* c = nearestTarget(Vector3f(sp.x, sp.y, sp.z), 400.0f);
        if (c) {
            const Vector3f tp = c->getPosition();
            tgt.hasTarget = true;
            tgt.position = P2CannonStoneVec3{ tp.x, tp.y, tp.z };
        }
        s->update(P2CannonStone::kSourceDelta, tgt, nullptr, nullptr);
        if (s->isAlive()) {
            const P2CannonStoneVec3 now = s->position();
            Iterator it(pikiMgr);
            CI_LOOP(it) {
                Piki* p = static_cast<Piki*>(*it);
                if (!p || !p->isAlive()) continue;
                const Vector3f q = p->getPosition();
                const float dx = q.x - now.x, dy = q.y - now.y, dz = q.z - now.z;
                if (dx * dx + dy * dy + dz * dz > kShellHitRadius * kShellHitRadius) continue;
                const P2CannonStoneContactResult res = s->contact(
                    P2CannonStoneContactKind::NaviPiki, true, false,
                    (std::uint64_t)(std::uintptr_t)p);
                if (res.strikeEmitted && res.strike.damage > 0.0f) {
                    p->stimulate(InteractBomb(actor, res.strike.damage, nullptr));
                    ++hitTotal;
                }
                s->notifyWallContact(); // terminate the shell on impact
                s->finishDeath();       // free the pool slot
                break;
            }
        }
        if (!s->isAlive()) shells.erase(shells.begin() + i);
        else ++i;
    }
    if (hitTotal > 0) {
        std::printf("P2_LONG_LEGS_SHELL_HIT species=%s generator=%u pikmin=%d\n",
                    species.c_str(), generator, hitTotal);
        std::fflush(stdout);
    }
}

// Port substitution: the P1 engine has no InteractPress callback, so the
// landing key-2 "all four feet" press is applied as a single InteractFlick
// (knockback + source press damage) to grounded Pikmin within the foot radius.
// The source foot sphere radius is not in the audit; 60 units is the documented
// port value and applies only on the landing-key-2 event.
void applyFootCrush(BTeki* actor, const Vector3f& pos, const std::string& species,
                    unsigned generator, float damage, float radius) {
    if (!pikiMgr || damage <= 0.0f) return;
    int hit = 0;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive()) continue;
        const Vector3f q = p->getPosition();
        const float dx = q.x - pos.x, dz = q.z - pos.z;
        if (dx * dx + dz * dz >= radius * radius) continue;
        const float angle = std::atan2(q.x - pos.x, q.z - pos.z);
        p->stimulate(InteractFlick(actor, 100.0f, damage, angle));
        ++hit;
    }
    if (hit > 0) {
        std::printf("P2_LONG_LEGS_CRUSH species=%s generator=%u pikmin=%d\n",
                    species.c_str(), generator, hit);
        std::fflush(stdout);
    }
}

bool parseActors(const std::string& path, std::map<unsigned, std::string>& out) {
    std::ifstream in(path);
    if (!in) return false;  // absent config -> P1 fallback
    std::string header, species, word;
    int count = 0;
    if (!(in >> header >> count) || header.size() < 11
            || header.compare(0, 3, "P2_") != 0
            || header.compare(header.size() - 9, 9, "_ACTORS_1") != 0
            || count < 1 || count > 100) fail("invalid actor config");
    for (int i = 0; i < count; ++i) {
        unsigned long long generator = 0;
        if (!(in >> generator >> species) || generator > 0xffffffffULL
                || !findSpecies(species)
                || !out.emplace(unsigned(generator), species).second) fail("invalid actor row");
    }
    if (in >> word) fail("trailing actor config data");
    return true;
}

Shape* loadBind(const SpeciesDef& species) {
    std::vector<unsigned char> data;
    {
        std::ifstream file(std::string("assets/dataDir/courses/pikmin2room/") + species.mod,
                           std::ios::binary | std::ios::ate);
        if (!file) fail("missing bind mesh");
        const auto size = file.tellg();
        if (size <= 0 || size_t(size) > MeshBytes) fail("bind mesh exceeds per-species budget");
        bytesTotal += size_t(size);
        if (bytesTotal > TotalBytes) fail("bind mesh exceeds total budget");
        file.seekg(0);
        data.assign(size_t(size), 0);
        if (!file.read(reinterpret_cast<char*>(data.data()), size)) fail("unreadable bind mesh");
    }
    std::vector<unsigned char> resources;
    if (!p2animation::resources(data, resources)) fail("invalid bind resources");
    Shape* shape = gameflow.loadShape(
        (std::string("courses/pikmin2room/") + species.mod).c_str(), true);
    if (!shape) fail("bind mesh load failed");
    for (int i = 0; i < shape->mTexAttrCount; ++i)
        if (shape->mTexAttrList[i].mTexture) shape->mTexAttrList[i].mTexture->attach();
    return shape;
}
}

void pc_p2_long_legs_reset() {
    for (HoudaiShell& shell : shells) {
        if (shell.stone) { shell.stone->notifyWallContact(); shell.stone->finishDeath(); }
    }
    actors.clear();
    corpses.clear();
    shapes.clear();
    shells.clear();
    bytesTotal = 0;
    logged[0] = logged[1] = false;
}

void pc_p2_long_legs_forget(BTeki* actor) {
    killShellsOf(actor);
    actors.erase(actor);
    // The actor's corpse registration is keyed on its Pellet*, so a plain
    // actors.erase leaves it behind; clear it with the actor (review fix 3b).
    if (actor && actor->mPellet) corpses.erase(actor->mPellet);
}

void pc_p2_long_legs_setup() {
    pc_p2_long_legs_reset();
    if (!pc_pikipelago_room_preview() || !tekiMgr) return;
    std::map<unsigned, std::string> wanted;
    if (!parseActors("p2-long-legs-actors.txt", wanted)) return;

    std::set<unsigned> found;
    std::set<std::string> speciesUsed;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* teki = static_cast<Teki*>(*it);
        if (!teki || !teki->mGenerator) continue;
        const unsigned generator = teki->mGenerator->_70;
        auto match = wanted.find(generator);
        if (match == wanted.end()) continue;
        if (teki->mTekiType != TEKI_Chappy) fail("native type mismatch");
        if (!found.insert(generator).second) fail("duplicate generator in scene");
        ActorState& state = actors[teki];
        state.species = match->second;
        state.generator = generator;
        state.parms = p2LongLegsParmsFor(speciesEnum(match->second));
        state.fsm.reset(state.parms);
        state.homePos = teki->getPosition(); // source mHomePosition: spawn point
        state.homeRecorded = true;
        state.lastHealth = teki->mHealth;
        state.lastPositiveHealth = teki->mHealth;
        speciesUsed.insert(match->second);
    }
    if (found.size() != wanted.size()) fail("arena actor not present in scene");
    for (const std::string& species : speciesUsed) {
        if (shapes.count(species)) continue;
        const SpeciesDef* def = findSpecies(species);
        if (!def) fail("unknown species in actor config");
        shapes[species] = loadBind(*def);
    }
    for (const auto& entry : actors)
        std::printf("P2_LONG_LEGS_BIND generator=%u species=%s pose=bind visual_only=0 "
                    "native_fsm=implemented\n",
                    entry.second.generator,
                    entry.second.species.c_str());
    std::printf("P2_LONG_LEGS_BANK total_mod_bytes=%zu species=%zu pose_bank=0\n",
                bytesTotal, shapes.size());
}

// Per-frame source-FSM tick. Called from BTeki::update() (tekibteki.cpp) so the
// schedule runs for every registered actor regardless of camera visibility; the
// previous draw-tick only advanced on-camera actors.
void pc_p2_long_legs_update(BTeki* actor) {
    auto entry = actors.find(actor);
    if (entry == actors.end()) return;
    ActorState& state = entry->second;
    // Once the proxy dies, capture the corpse Pellet* the engine created
    // (PelletView::mPellet) so the ordinary Pod receipt can resolve a view-less
    // stand-in corpse (mirrors lane 31). Runs each tick until the corpse is
    // delivered (the receipt consumes it one-shot) or swept as dead, and is also
    // cleared by forget (per-actor) and reset (whole registry).
    if (!actor->isAlive() && actor->mPellet && !corpses.count(actor->mPellet)) {
        corpses[actor->mPellet] = state.generator;
        std::printf("P2_LONG_LEGS_CORPSE_REGISTER generator=%u species=%s\n",
                    state.generator, state.species.c_str());
        std::fflush(stdout);
    }
    if (state.fsm.state() == P2LongLegsState::Dead) return;

    const float dt = gsys ? gsys->getFrameTime() : 0.0f;
    if (!(dt > 0.0f && dt < 0.5f)) return;

    const Vector3f pos = actor->getPosition();
    const P2LongLegsSpecies species = speciesEnum(state.species);

    // Engine death of the placement vehicle is the host kill signal. One
    // terminal tick lets the policy emit its source death output: the held
    // treasure drop, or the no-treasure child burst. The dropped treasure and
    // children are lane 06/14/15/20 objects, so the intents are logged, not
    // spawned here. No further ticks run once the policy is Dead.
    if (!actor->isAlive()) {
        killShellsOf(actor);  // free the actor's in-flight shells on death
        P2LongLegsFsmInput kill;
        kill.health = actor->mHealth;
        kill.killed = true;
        P2LongLegsFsmOutput dead;
        state.fsm.update(kill, dead);
        // prior_health distinguishes a naturally-fought death (small, drained
        // to zero by incremental combat damage) from a fixture-injected large
        // jump to zero. Reported from the last still-positive health, since the
        // engine death tick already sees health == 0.
        std::printf("P2_LONG_LEGS_DEAD species=%s generator=%u health=0 prior_health=%.2f\n",
                    state.species.c_str(), state.generator, state.lastPositiveHealth);
        if (dead.dropTreasure)
            std::printf("P2_LONG_LEGS_DROP species=%s generator=%u\n",
                        state.species.c_str(), state.generator);
        if (dead.birthChildren > 0)
            std::printf("P2_LONG_LEGS_BIRTH species=%s generator=%u count=%d\n",
                        state.species.c_str(), state.generator, dead.birthChildren);
        std::printf("P2_LONG_LEGS_STATE species=%s generator=%u state=%s\n",
                    state.species.c_str(), state.generator,
                    P2LongLegsFsm::stateName(state.fsm.state()));
        std::fflush(stdout);
        return;
    }

    const float land = landingSeconds(species);
    const float flick = flickSeconds(species);
    const float shot = shotSeconds(species);
    const P2LongLegsState before = state.fsm.state();

    P2LongLegsFsmInput in;
    in.health = actor->mHealth;
    // Measured body-translation ratio from the previous tick drives the source
    // crush gate (IKSystemMgr::isCollisionCheck: a foot presses only while
    // descending/planting with a move ratio above 1). Without leg state the
    // planting edge is never synthesized, so Walk crush stays closed; the ratio
    // is still observed for the movement evidence.
    in.ikMoveRatio = state.lastMoveRatio;
    // A health decrease this tick is the source damage edge; it postpones the
    // Houdai gun by resetting the shot cooldown (Houdai.cpp).
    if (actor->mHealth > 0.0f && actor->mHealth < state.lastHealth) {
        // Natural combat observability: an incremental, still-positive health
        // decrease is live Pikmin attack damage, distinguishable from a single
        // fixture-injected jump to zero (which shows up only in P2_LONG_LEGS_DEAD).
        std::printf("P2_LONG_LEGS_DAMAGE species=%s generator=%u health=%.2f prior=%.2f\n",
                    state.species.c_str(), state.generator, actor->mHealth, state.lastHealth);
        std::fflush(stdout);
    }
    in.damageTaken = actor->mHealth < state.lastHealth;
    state.lastHealth = actor->mHealth;
    if (actor->mHealth > 0.0f) state.lastPositiveHealth = actor->mHealth;
    in.roll = gsys->getRand(1.0f);
    in.wakeTargetNearby = nearestTarget(pos, state.parms.privateRadius) != nullptr;
    in.pikminAccumulating = countPikiWithin(pos, AccumulateRadius) > 0;
    in.landingKey2 = before == P2LongLegsState::Land && !state.key2Fired
        && state.animSeconds >= land * 0.5f;
    in.flickKey2 = before == P2LongLegsState::Flick && !state.key2Fired
        && state.animSeconds >= flick * 0.5f;
    in.animEnd = (before == P2LongLegsState::Land && state.animSeconds >= land)
        || (before == P2LongLegsState::Flick && state.animSeconds >= flick)
        || (before == P2LongLegsState::Shot && shot > 0.0f && state.animSeconds >= shot);
    // Man-at-Legs attack loop: one shell every ~5 source frames while the burst
    // is on, bounded by the lane-20 in-flight pool occupancy.
    if (before == P2LongLegsState::Shot) {
        state.shotLoopAccum += dt;
        in.shotLoop = state.shotLoopAccum >= kShellLoopPeriod;
        if (in.shotLoop) state.shotLoopAccum = 0.0f;
    } else {
        state.shotLoopAccum = 0.0f;
    }
    in.shellsInFlight = countShellsOf(actor);
    if (in.landingKey2 || in.flickKey2) state.key2Fired = true;

    P2LongLegsFsmOutput out;
    state.fsm.update(in, out);
    const P2LongLegsState after = state.fsm.state();
    // Source StateWalk (HoudaiState.cpp:340-375, BigFoot/Damagumo equivalents):
    // startIKMotion toward getTargetPosition for mStateDuration, with no walk
    // animation (family-wide). The port has no IKSystemMgr and no leg joints, so
    // the source target rule + species speed drive BODY translation here while
    // the legs stay bind-pose (documented approximation). Translation runs only
    // in FSM Walk; every other state leaves the actor where it stands.
    if (after == P2LongLegsState::Walk && before != P2LongLegsState::Walk) {
        if (!state.homeRecorded) { state.homePos = pos; state.homeRecorded = true; }
        state.walkTarget = pickWalkTarget(pos, state.homePos, state.parms);
        state.walkStart = pos;
        state.walkDistance = 0.0f;
        state.walkSeconds = 0.0f;
        state.hasWalkTarget = true;
        std::printf("P2_LONG_LEGS_WALK species=%s generator=%u from=%.1f,%.1f to=%.1f,%.1f speed=%.1f\n",
                    state.species.c_str(), state.generator, pos.x, pos.z,
                    state.walkTarget.x, state.walkTarget.z, state.parms.speed);
        std::fflush(stdout);
    }
    if (after == P2LongLegsState::Walk && state.hasWalkTarget) {
        const float dx = state.walkTarget.x - pos.x, dz = state.walkTarget.z - pos.z;
        const float dist = std::sqrt(dx * dx + dz * dz);
        const float maxStep = state.parms.speed * dt;
        const float step = dist < maxStep ? dist : maxStep;
        state.lastMoveRatio = maxStep > 1.0e-6f ? step / maxStep : 1.0f;
        state.walkSeconds += dt;
        if (step > 1.0e-6f && dist > 1.0e-6f) {
            const Vector3f next(pos.x + dx / dist * step, pos.y, pos.z + dz / dist * step);
            actor->resetPosition(next);
            // Registered actors are TEKI_Chappy placement vehicles (setup fails
            // otherwise), so the Teki facing control is available.
            static_cast<Teki*>(actor)->setDirection(std::atan2(dx, dz));
            state.walkDistance += step;
        }
    } else {
        state.lastMoveRatio = 1.0f;
        if (before == P2LongLegsState::Walk && state.hasWalkTarget) {
            std::printf("P2_LONG_LEGS_WALK_END species=%s generator=%u distance=%.1f seconds=%.2f\n",
                        state.species.c_str(), state.generator,
                        state.walkDistance, state.walkSeconds);
            std::fflush(stdout);
            state.hasWalkTarget = false;
        }
    }
    if (state.fsm.state() != before) {
        state.animSeconds = 0.0f;
        state.key2Fired = false;
        state.lastState = state.fsm.state();
    } else {
        state.animSeconds += dt;
    }
    state.damageable = out.damageable;
    state.bitterImmune = out.bitterImmune;
    if (out.footCrush) {
        std::printf("P2_LONG_LEGS_FOOT species=%s generator=%u\n", state.species.c_str(),
                    state.generator);
        std::fflush(stdout);
        applyFootCrush(actor, pos, state.species, state.generator,
                       state.parms.pressDamage, 60.0f);
    }
    if (out.fireShell) {
        std::printf("P2_LONG_LEGS_SHELL species=%s generator=%u\n", state.species.c_str(),
                    state.generator);
        std::fflush(stdout);
        if (state.species == "Houdai") fireHoudaiShell(actor, pos);
    }
    if (state.species == "Houdai") stepHoudaiShells(actor, state.species, state.generator);
    if (!state.stateLogged || out.entered) {
        state.stateLogged = true;
        std::printf("P2_LONG_LEGS_STATE species=%s generator=%u state=%s\n",
                    state.species.c_str(), state.generator,
                    P2LongLegsFsm::stateName(state.fsm.state()));
        std::fflush(stdout);
    }
}

bool pc_p2_long_legs_draw(BTeki* actor, Graphics& gfx, const Matrix4f& matrix, bool corpse) {
    auto entry = actors.find(actor);
    if (entry == actors.end() || !gfx.mCamera) return false;
    ActorState& state = entry->second;
    auto shapeIt = shapes.find(state.species);
    if (shapeIt == shapes.end() || !shapeIt->second) return false;
    Shape* shape = shapeIt->second;

    if (!logged[corpse ? 1 : 0]) {
        std::printf("P2_LONG_LEGS_DRAW corpse=%d species=%s pose=bind\n",
                    int(corpse), state.species.c_str());
        logged[corpse ? 1 : 0] = true;
    }
    shape->updateAnim(gfx, matrix, nullptr, actor);
    shape->drawshape(gfx, *gfx.mCamera, nullptr);
    return true;
}

// Fixture observability (#397): behavior-neutral read-only accessors so the
// lifecycle fixture can prove pc_p2_long_legs_forget() clears a registration.
unsigned long pc_p2_long_legs_count() {
    return (unsigned long)actors.size();
}

bool pc_p2_long_legs_registered(BTeki* actor) {
    return actors.count(actor) != 0;
}

bool pc_p2_long_legs_damageable(const BTeki* actor) {
    auto entry = actors.find(const_cast<BTeki*>(actor));
    if (entry == actors.end()) return false;
    return entry->second.damageable;
}

bool pc_p2_long_legs_receiver_rejects(Teki* teki, const InteractAttack* /*attack*/) {
    // Source damageCallBack + EB_BitterImmune: a registered Long Legs rejects
    // every attack while it is still bitter-immune (Stay or Land). Once damageable
    // (Wait/Flick/Walk/Shot) the P1 proxy accepts ordinary Pikmin attack damage.
    // Unregistered actors are never rejected, keeping the shared hook a no-op.
    if (!actors.count(teki)) return false;
    return !actors[teki].damageable;
}

bool pc_p2_long_legs_receipt(Pellet* pellet, unsigned& generator) {
    // Ordinary corpse receipt (mirrors lane 31's pc_p2_waterwraith_receipt and
    // kurage/otakara). Primary key is the corpse Pellet* captured at death, which
    // resolves even a view-less stand-in corpse; the PelletView backlink is a
    // fallback for a live-binding corpse. Returns false for any unowned pellet.
    // One-shot: the resolved registration is consumed so MonoObjectMgr slot reuse
    // cannot re-credit a future unrelated pellet at the same address (lane 31).
    if (!pellet) return false;
    auto corpse = corpses.find(pellet);
    if (corpse != corpses.end()) {
        generator = corpse->second;
        corpses.erase(corpse);
        return true;
    }
    PelletView* view = pellet->mPelletView;
    if (!view) return false;
    auto it = actors.find(static_cast<BTeki*>(view));
    if (it == actors.end()) return false;
    generator = it->second.generator;
    return true;
}

bool pc_p2_long_legs_shot(const BTeki* actor) {
    auto it = actors.find(const_cast<BTeki*>(actor));
    return it != actors.end() && it->second.fsm.state() == P2LongLegsState::Shot;
}

void pc_p2_long_legs_update_all() {
    // Sweeping is done from the guarded per-actor tick (pc_p2_long_legs_update),
    // not here: an unconditional per-frame sweep stalled the stage-2 FSM.
    if (actors.empty()) return;
    for (const auto& entry : actors) pc_p2_long_legs_update(entry.first);
}

unsigned long pc_p2_long_legs_corpse_count() {
    // Fixture observability (review fix 3b): sweeps dead/undelivered corpses and
    // reports the surviving registrations, so a non-one-shot receipt is visible.
    sweepCorpses();
    return static_cast<unsigned long>(corpses.size());
}
