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
#include "pc_p2_long_legs.h"
#include "pc_p2_long_legs_fsm.h"
#include "pc_p2_animation.h"
#include "pc_bbft.h"
#include "teki.h"
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
    float lastHealth = 0.0f;    // host damage edge for the Houdai shot cooldown
    P2LongLegsState lastState = P2LongLegsState::Stay;
    bool stateLogged = false;
};

std::map<BTeki*, ActorState> actors;      // actor -> species + policy state
std::map<std::string, Shape*> shapes;     // species -> bind shape
size_t bytesTotal = 0;
bool logged[2] = {false, false};

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
    return species == P2LongLegsSpecies::BigFoot ? 18.0f / 30.0f : 150.0f / 30.0f;
}
float flickSeconds(P2LongLegsSpecies species) {
    return species == P2LongLegsSpecies::BigFoot ? 35.0f / 30.0f : 68.0f / 30.0f;
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
    actors.clear();
    shapes.clear();
    bytesTotal = 0;
    logged[0] = logged[1] = false;
}

void pc_p2_long_legs_forget(BTeki* actor) {
    actors.erase(actor);
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
        state.lastHealth = teki->mHealth;
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
        P2LongLegsFsmInput kill;
        kill.health = actor->mHealth;
        kill.killed = true;
        P2LongLegsFsmOutput dead;
        state.fsm.update(kill, dead);
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
    const P2LongLegsState before = state.fsm.state();

    P2LongLegsFsmInput in;
    in.health = actor->mHealth;
    // A health decrease this tick is the source damage edge; it postpones the
    // Houdai gun by resetting the shot cooldown (Houdai.cpp).
    in.damageTaken = actor->mHealth < state.lastHealth;
    state.lastHealth = actor->mHealth;
    in.roll = gsys->getRand(1.0f);
    in.wakeTargetNearby = nearestTarget(pos, state.parms.privateRadius) != nullptr;
    in.pikminAccumulating = countPikiWithin(pos, AccumulateRadius) > 0;
    in.landingKey2 = before == P2LongLegsState::Land && !state.key2Fired
        && state.animSeconds >= land * 0.5f;
    in.flickKey2 = before == P2LongLegsState::Flick && !state.key2Fired
        && state.animSeconds >= flick * 0.5f;
    in.animEnd = (before == P2LongLegsState::Land && state.animSeconds >= land)
        || (before == P2LongLegsState::Flick && state.animSeconds >= flick);
    if (in.landingKey2 || in.flickKey2) state.key2Fired = true;

    P2LongLegsFsmOutput out;
    state.fsm.update(in, out);
    if (state.fsm.state() != before) {
        state.animSeconds = 0.0f;
        state.key2Fired = false;
        state.lastState = state.fsm.state();
    } else {
        state.animSeconds += dt;
    }
    if (out.footCrush) {
        std::printf("P2_LONG_LEGS_FOOT species=%s generator=%u\n", state.species.c_str(),
                    state.generator);
        std::fflush(stdout);
        applyFootCrush(actor, pos, state.species, state.generator,
                       state.parms.pressDamage, 60.0f);
    }
    if (out.fireShell)
        std::printf("P2_LONG_LEGS_SHELL species=%s generator=%u\n", state.species.c_str(),
                    state.generator);
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
