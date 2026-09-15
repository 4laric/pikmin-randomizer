// Family-owned lane-22 elemental-dweevil source behavior for the batch-2 Chappy
// placement vehicle: Fiery Dweevil (FireOtakara, EnemyID 59) and its shared-base
// elemental siblings WaterOtakara (60), GasOtakara (61), ElecOtakara (62).
// Implements the shared OtakaraBase normal FSM subset (Wait/Move/Turn/Flick/Dead,
// OtakaraBase.h:22-39 / OtakaraBaseState.cpp:14-34,71-136) on the P1 host, driven
// from p2-dweevil-actors.txt / p2-dweevil-bank.txt written by the dweevil arena.
// Source revision 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms from
// docs/PIKMIN2_DWEEVIL_ASSETS.md (GPVE01 rev 0).
//
// Port adaptations (recorded, not retail-faithful):
//   * The shared Otakara Flick charge/discharge is resolved on the P1 host as a
//     bounded Flick clip: event type 2 (source `attack1` frame 12) flicks stuck
//     Pikmin, event type 3 (source `attack1` frame 35) discharges the species
//     element through the engine receivers. Fire/Bubble use the P1 InteractFire/
//     InteractBubble receivers; Gas/Denki use the lane-10 InteractGas/InteractDenki
//     receivers (see docs/PIKMIN2_RECEIVER_PATHS.md). Immunity is the receiver's
//     own lane-11 capability matrix (Red/Bulbmin fire, Blue/Bulbmin bubble,
//     White/Bulbmin gas, Yellow/Bulbmin electric).
//   * The item-carry (5..10) and Bomb-carry (11..13) states are source-backed N/A:
//     no treasure or Bomb payload is staged. BombOtakara (93) is bound for identity
//     only: it delegates its element to the lane-20 Bomb payload (no discharge).
//   * Wander/wake navigation is a P1-host adaptation of OtakaraBase Move/Turn.
//   * View angle is a full circle (hit angle fp23=0 on the disc).
// No other lane's module is modified; every hook is a no-op for unregistered actors.
#include "pc_p2_otakara.h"
#include "pc_p2_dweevil_policy.h"
#include "pc_p2_species.h"
#include "pc_p2_hazard_emitter.h"
#include "teki.h"
#include "Interactions.h"
#include "Piki.h"
#include "PikiState.h"
#include "PikiMgr.h"
#include "Pellet.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Generator.h"
#include "gameflow.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <set>
#include <string>
#include <vector>

namespace {
enum State {
    OTA_INVALID = -1,
    OTA_DEAD = 0,
    OTA_FLICK = 1,
    OTA_WAIT = 2,
    OTA_MOVE = 3,
    OTA_TURN = 4,
};

const char* stateName(State s) {
    switch (s) {
    case OTA_DEAD: return "dead";
    case OTA_FLICK: return "flick";
    case OTA_WAIT: return "wait";
    case OTA_MOVE: return "move";
    case OTA_TURN: return "turn";
    default: return "null";
    }
}

// Source per-species general block (docs/PIKMIN2_DWEEVIL_ASSETS.md section 4).
inline float speciesLife(int species) {
    return species == p2dweevil::GasId ? 350.0f : 150.0f; // fp00
}
inline float speciesMoveSpeed(int species) {
    return species == p2dweevil::GasId ? 100.0f : 80.0f; // fp06
}
inline float speciesAttack(int species) {
    switch (species) { // fp24
    case p2dweevil::FireId: return 10.0f;
    case p2dweevil::ElecId: return 10.0f;
    default: return 0.0f; // Water/Gas/Bomb route through the elemental effect
    }
}
inline const char* colorName(unsigned color) {
    switch (color) {
    case Blue: return "blue";
    case Red: return "red";
    case Yellow: return "yellow";
    default: return "other";
    }
}

constexpr float SIGHT = 200.0f;       // fp12
constexpr float TERRITORY = 200.0f;   // fp09 home territory
constexpr float HIT_RANGE = 60.0f;    // fp22 attack hit range (disc)
constexpr float FLICK_RADIUS = 60.0f; // trigger the Flick discharge
constexpr float TURN_RATE = 2.0f;     // port adaptation
constexpr float WAIT_MIN = 1.0f;      // port adaptation
constexpr float WAIT_MAX = 2.0f;      // port adaptation

struct Clip {
    std::string name;
    float duration = 1.0f;
    bool loop = false;
    std::vector<std::pair<int, int>> events; // source frame -> event type
};

struct Otakara {
    State state = OTA_WAIT;
    float stateTime = 0.0f;
    float timer = 0.0f;
    float heading = 0.0f;
    Vector3f home;
    Vector3f target;
    int species = p2dweevil::FireId;
    p2dweevil::Stimulus stimulus = p2dweevil::StimFire;
    float life = 150.0f;
    float attack = 10.0f;
    unsigned rng = 1;
    std::set<int> firedEvents;
    std::string clip = "wait1";
    float phase = 0.0f;
    float prevHealth = 0.0f;
    bool deadLogged = false;
    float logTimer = 0.0f;
    std::string lastInteraction = "unknown";
    std::string lastAttacker = "none";
    unsigned generator = 0;
    bool deathSeamLogged = false;
};

std::map<PelletView*, Otakara> actors;
std::map<std::string, Clip> clips;
bool ready = false;

unsigned nextRand(Otakara& s) {
    s.rng = s.rng * 1664525u + 1013904223u;
    return s.rng >> 8;
}
float rand01(Otakara& s) { return float(nextRand(s) & 0xffff) / 65535.0f; }
float randRange(Otakara& s, float lo, float hi) { return lo + (hi - lo) * rand01(s); }
unsigned genOf(const BTeki* actor) { return actor && actor->mGenerator ? actor->mGenerator->_70 : 0u; }

float wrapPi(float a) {
    while (a > 3.14159265f) a -= 6.28318531f;
    while (a < -3.14159265f) a += 6.28318531f;
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

Piki* nearestPiki(const Vector3f& pos, float radius) {
    Piki* best = nullptr;
    float bestSq = radius * radius;
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive()) continue;
            const float d = distXZ(p->getPosition(), pos);
            if (d * d < bestSq) { bestSq = d * d; best = p; }
        }
    }
    return best;
}
Creature* nearestTarget(const Vector3f& pos) {
    Creature* best = nullptr;
    float bestSq = SIGHT * SIGHT;
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

// The receiver decides immunity; this mirrors the receiver's own lane-11 matrix
// so the emitter can log the immune/rejected case distinctly and never deliver an
// interaction the receiver would swallow.
bool dweevilAccepts(const Piki* p, p2dweevil::Stimulus stim) {
    if (!p || !p->isAlive()) return false;
    const int species = pc_p2_species(p);
    switch (stim) {
    case p2dweevil::StimFire: return !p2_species_immune(species, P2HazardFire);
    case p2dweevil::StimBubble: return !p2_species_immune(species, P2HazardWater);
    case p2dweevil::StimGas: return p2_emitter_accepts(species, P2HazardGas, p->gasInvicible());
    case p2dweevil::StimDenki: return p2_emitter_accepts(species, P2HazardElectric, p->gasInvicible());
    default: return false;
    }
}

void doDischarge(BTeki* a, Otakara& s) {
    if (!pikiMgr) return;
    if (s.stimulus == p2dweevil::StimNone) {
        // BombOtakara (93) delegates its element to the carried Bomb payload
        // (lane-20 shared blast contract); there is no self-contained discharge.
        std::printf("P2_OTAKARA_DISCHARGE_NONE generator=%u source_id=%d payload_delegated=1\n",
                    genOf(a), s.species);
        std::fflush(stdout);
        return;
    }
    const Vector3f pos = a->getPosition();
    const unsigned generator = genOf(a);
    int applied = 0, immune = 0;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive()) continue;
        if (distXZ(p->getPosition(), pos) >= HIT_RANGE) continue;
        const int species = pc_p2_species(p);
        if (!dweevilAccepts(p, s.stimulus)) {
            ++immune;
            std::printf("P2_OTAKARA_DISCHARGE_IMMUNE generator=%u source_id=%d pikmin=%d colour=%s "
                        "stimulus=%s\n",
                        generator, s.species, species, colorName(p->mColor),
                        p2dweevil::stimulusName(s.stimulus));
            continue;
        }
        bool accepted = false;
        switch (s.stimulus) {
        case p2dweevil::StimFire:
            accepted = p->stimulate(InteractFire(a, s.attack));
            break;
        case p2dweevil::StimBubble:
            accepted = p->stimulate(InteractBubble(a, s.attack));
            break;
        case p2dweevil::StimGas:
            accepted = p->stimulate(InteractGas(a, s.attack));
            break;
        case p2dweevil::StimDenki: {
            Vector3f dir(p->getPosition().x - pos.x, 0.0f, p->getPosition().z - pos.z);
            accepted = p->stimulate(InteractDenki(a, s.attack, &dir));
            break;
        }
        default:
            break;
        }
        ++applied;
        std::printf("P2_OTAKARA_DISCHARGE_HIT generator=%u source_id=%d pikmin=%d colour=%s "
                    "stimulus=%s accepted=%d target_state=%d(%s)\n",
                    generator, s.species, species, colorName(p->mColor),
                    p2dweevil::stimulusName(s.stimulus), int(accepted), p->getState(),
                    p->getState() == PIKISTATE_DenkiDying ? "DenkiDying"
                    : p->getState() == PIKISTATE_Fired ? "Fired"
                    : p->getState() == PIKISTATE_Panic ? "Panic" : "other");
        std::fflush(stdout);
    }
    std::printf("P2_OTAKARA_DISCHARGE generator=%u source_id=%d stimulus=%s applied=%d immune=%d\n",
                generator, s.species, p2dweevil::stimulusName(s.stimulus), applied, immune);
    std::fflush(stdout);
}

void doFlick(BTeki* a) {
    if (!pikiMgr) return;
    const Vector3f pos = a->getPosition();
    int flicked = 0;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (p && p->isAlive() && distXZ(p->getPosition(), pos) < HIT_RANGE) {
            if (p->stimulate(InteractFlick(a, 120.0f, 0.0f, a->getDirection()))) ++flicked;
        }
    }
    if (flicked) std::printf("P2_OTAKARA_FLICK generator=%u flicked=%d\n", genOf(a), flicked);
}

void enter(Otakara& s, State state, const char* clip, float timer = 0.0f) {
    s.state = state;
    s.stateTime = 0.0f;
    s.timer = timer;
    s.firedEvents.clear();
    if (clip) s.clip = clip;
}

void fireEvents(BTeki* a, Otakara& s) {
    auto it = clips.find(s.clip);
    if (it == clips.end()) return;
    for (const auto& event : it->second.events) {
        if (s.firedEvents.count(event.first)) continue;
        if (s.stateTime < event.first / 30.0f) continue;
        s.firedEvents.insert(event.first);
        if (s.state == OTA_FLICK && event.second == 2) {
            doFlick(a);
        } else if (s.state == OTA_FLICK && event.second == 3) {
            doDischarge(a, s);
        }
    }
}

void setPhase(Otakara& s) {
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
} // namespace

void pc_p2_otakara_reset() {
    actors.clear();
    clips.clear();
    ready = false;
}

void pc_p2_otakara_forget(BTeki* actor) {
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    const unsigned generator = it->second.generator;
    actors.erase(it);
    // lane-07 seam (pc_p2_forget_teki in BTeki::doKill / slot reuse): report the
    // registration actually dropping (count after the erase). This marker is
    // computed from the live map; the fixture's P2_OTAKARA_SEAM_OBSERVED is the
    // authoritative zero-registration probe.
    const unsigned long after = (unsigned long)actors.size();
    std::printf("P2_OTAKARA_FORGET generator=%u registered=1 count=%lu\n", generator, after);
    std::fflush(stdout);
}

void pc_p2_otakara_died(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end() || it->second.deathSeamLogged) return;
    it->second.deathSeamLogged = true;
    // Host death seam (BTeki::die, mDeadState transition), distinct from the
    // module's P2_OTAKARA_MODULE_DEAD observation on mHealth<=0.
    std::printf("P2_OTAKARA_DEAD generator=%u source_id=%d mDeadState=1\n",
                it->second.generator, it->second.species);
    std::fflush(stdout);
}

bool pc_p2_otakara_receipt(PelletView* view, unsigned& generator) {
    if (!view || !ready) return false;
    auto it = actors.find(view);
    if (it == actors.end()) return false;
    generator = it->second.generator;
    return true;
}

void pc_p2_otakara_attack(BTeki* actor, Creature* owner, const char* interaction) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Otakara& s = it->second;
    s.lastInteraction = interaction && *interaction ? interaction : "InteractAttack";
    if (owner && owner->isPiki()) {
        s.lastAttacker = colorName(static_cast<Piki*>(owner)->mColor);
    } else if (owner) {
        s.lastAttacker = "creature";
    } else {
        s.lastAttacker = "none";
    }
}

unsigned long pc_p2_otakara_count() { return (unsigned long)actors.size(); }
bool pc_p2_otakara_registered(BTeki* actor) {
    return actors.count(static_cast<PelletView*>(actor)) != 0;
}

float pc_p2_otakara_param_f(const BTeki* actor, int idx, float fallback) {
    if (!ready || !actors.count(static_cast<PelletView*>(const_cast<BTeki*>(actor)))) return fallback;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (idx == TPF_Life) return it->second.life;
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

bool pc_p2_otakara_clip(const BTeki* actor, const char*& name, float& phase) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    name = it->second.clip.c_str();
    phase = it->second.phase;
    return true;
}

static int speciesFromName(const std::string& name) {
    if (name == "FireOtakara") return p2dweevil::FireId;
    if (name == "WaterOtakara") return p2dweevil::WaterId;
    if (name == "GasOtakara") return p2dweevil::GasId;
    if (name == "ElecOtakara") return p2dweevil::ElecId;
    if (name == "BombOtakara") return p2dweevil::BombId;
    return -1; // unknown species left to the other paths
}

void pc_p2_otakara_setup() {
    pc_p2_otakara_reset();
    if (!tekiMgr) return;

    // Shared OtakaraBase clip bank (one bank aliased across the dweevil species).
    std::ifstream bank("p2-dweevil-bank.txt");
    if (bank) {
        std::string token;
        if (bank >> token && token == "P2_DWEEVIL_BANK_1") {
            while (bank >> token) {
                if (token == "species") {
                    std::string species, id;
                    bank >> species >> id;
                } else if (token == "clip") {
                    std::string species, name, events, marker, status;
                    long long frames = 0;
                    int poses = 0;
                    bank >> species >> name >> frames >> events >> marker >> poses >> status;
                    if (clips.count(name) == 0) {
                        Clip clip;
                        clip.name = name;
                        clip.duration = frames > 0 ? float(frames) / 30.0f : 1.0f;
                        clip.loop = (name == "wait1" || name == "move1" || name == "pivot1"
                                     || name == "wait2" || name == "move2" || name == "pivot2"
                                     || name == "carry");
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

    std::ifstream in("p2-dweevil-actors.txt");
    if (!in) return;
    std::string header;
    int count = 0;
    if (!(in >> header >> count) || header != "P2_DWEEVIL_ACTORS_1" || count < 1) return;
    std::map<unsigned, int> wanted;
    for (int i = 0; i < count; ++i) {
        unsigned long long generator = 0;
        std::string species;
        if (!(in >> generator >> species)) return;
        const int sid = speciesFromName(species);
        if (sid >= 0) wanted[unsigned(generator)] = sid;
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
            std::printf("P2_OTAKARA_ERROR native_type generator=%u\n", actor->mGenerator->_70);
            std::abort();
        }
        Otakara& s = actors[static_cast<PelletView*>(actor)];
        s = Otakara();
        s.species = match->second;
        s.stimulus = p2dweevil::stimulusFor(s.species);
        s.life = speciesLife(s.species);
        s.attack = speciesAttack(s.species);
        s.generator = actor->mGenerator->_70;
        s.rng = (actor->mGenerator->_70 * 2654435761u) | 1u;
        s.home = actor->getPosition();
        s.target = s.home;
        s.heading = actor->getDirection();
        actor->mHealth = s.life;
        s.prevHealth = s.life;
        enter(s, OTA_WAIT, "wait1");
        std::printf("P2_OTAKARA_BIND generator=%u source_id=%d stimulus=%s visual_only=0\n",
                    actor->mGenerator->_70, s.species, p2dweevil::stimulusName(s.stimulus));
        const Vector3f pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=%s native_family=Chappy generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented attack=elemental_discharge\n",
                    p2dweevil::speciesName(s.species), actor->mGenerator->_70, pos.x, pos.y,
                    pos.z, actor->mHealth, s.life);
        found.insert(actor->mGenerator->_70);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_OTAKARA_ERROR missing_actor wanted=%zu found=%zu\n", wanted.size(), found.size());
        std::abort();
    }
    ready = true;
}

void pc_p2_otakara_update(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Otakara& s = it->second;
    const float dt = gsys->getFrameTime();
    if (dt <= 0.0f || dt > 0.5f) return;
    const Vector3f pos = actor->getPosition();
    const unsigned generator = genOf(actor);

    // Damage receipt observation (queue-then-apply, docs/PIKMIN2_RECEIVER_PATHS.md):
    // the host TAI applies mStoredDamage inside makeDamaged; this logs the drop
    // independent of the injected fixture trigger, so natural pre-injection combat
    // is observable as a positive delta.
    if (s.prevHealth - actor->mHealth > 0.5f) {
        std::printf("P2_OTAKARA_HIT generator=%u source_id=%d health=%.1f->%.1f delta=%.1f "
                    "interaction=%s attacker=%s\n",
                    generator, s.species, s.prevHealth, actor->mHealth,
                    s.prevHealth - actor->mHealth, s.lastInteraction.c_str(), s.lastAttacker.c_str());
        std::fflush(stdout);
        // Attribution is per drop: clear it so a later non-Attack drop is not mislabelled.
        s.lastInteraction = "unknown";
        s.lastAttacker = "none";
    }
    s.prevHealth = actor->mHealth;

    if (actor->mHealth <= 0.0f && s.state != OTA_DEAD) {
        if (!s.deadLogged) {
            std::printf("P2_OTAKARA_MODULE_DEAD generator=%u source_id=%d health=0\n", generator, s.species);
            std::fflush(stdout);
            s.deadLogged = true;
        }
        enter(s, OTA_DEAD, "dead");
    }

    s.stateTime += dt;
    switch (s.state) {
    case OTA_WAIT: {
        actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
        actor->mVelocity.x = 0.0f;
        actor->mVelocity.z = 0.0f;
        s.clip = "wait1";
        if (nearestPiki(pos, FLICK_RADIUS)) {
            std::printf("P2_OTAKARA_STATE generator=%u state=flick\n", generator);
            enter(s, OTA_FLICK, "attack1");
            break;
        }
        s.timer += dt;
        if (nearestTarget(pos) && s.timer > WAIT_MIN) {
            std::printf("P2_OTAKARA_STATE generator=%u state=move\n", generator);
            enter(s, OTA_MOVE, "move1", randRange(s, 0.5f, 1.5f));
        } else if (s.timer > WAIT_MAX) {
            std::printf("P2_OTAKARA_STATE generator=%u state=turn\n", generator);
            enter(s, OTA_TURN, "pivot1", randRange(s, 0.5f, 1.0f));
        }
        break;
    }
    case OTA_MOVE: {
        Creature* target = nearestTarget(pos);
        if (nearestPiki(pos, FLICK_RADIUS)) {
            actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
            std::printf("P2_OTAKARA_STATE generator=%u state=flick\n", generator);
            enter(s, OTA_FLICK, "attack1");
            break;
        }
        if (distXZ(pos, s.home) > TERRITORY) s.target = s.home;
        else if (target) s.target = target->getPosition();
        const float desired = std::atan2(s.target.x - pos.x, s.target.z - pos.z);
        const float maxTurn = TURN_RATE * dt;
        float diff = wrapPi(desired - s.heading);
        if (diff > maxTurn) diff = maxTurn;
        if (diff < -maxTurn) diff = -maxTurn;
        s.heading = wrapPi(s.heading + diff);
        actor->setDirection(s.heading);
        const Vector3f drive(std::sin(s.heading) * speciesMoveSpeed(s.species), 0.0f,
                             std::cos(s.heading) * speciesMoveSpeed(s.species));
        actor->inputDrive(drive);
        actor->mVelocity.set(drive);
        s.timer -= dt;
        if (s.timer <= 0.0f) {
            std::printf("P2_OTAKARA_STATE generator=%u state=wait\n", generator);
            enter(s, OTA_WAIT, "wait1");
        }
        break;
    }
    case OTA_TURN:
        actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
        actor->mVelocity.x = 0.0f;
        actor->mVelocity.z = 0.0f;
        if (nearestPiki(pos, FLICK_RADIUS)) {
            std::printf("P2_OTAKARA_STATE generator=%u state=flick\n", generator);
            enter(s, OTA_FLICK, "attack1");
        } else if (s.stateTime >= clipDuration("pivot1")) {
            s.heading = wrapPi(s.heading + randRange(s, -3.14159265f, 3.14159265f));
            actor->setDirection(s.heading);
            std::printf("P2_OTAKARA_STATE generator=%u state=wait\n", generator);
            enter(s, OTA_WAIT, "wait1");
        }
        break;
    case OTA_FLICK:
        actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
        actor->mVelocity.x = 0.0f;
        actor->mVelocity.z = 0.0f;
        if (s.stateTime >= clipDuration("attack1")) {
            std::printf("P2_OTAKARA_STATE generator=%u state=wait\n", generator);
            enter(s, OTA_WAIT, "wait1");
        }
        break;
    case OTA_DEAD:
        actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
        actor->mVelocity.x = 0.0f;
        actor->mVelocity.z = 0.0f;
        // Host death handoff: the P1 strategy reacts to mHealth<=0 inside
        // BTeki::doAI(), calls die() and then dieSoon()->becomePellet() in the
        // same pass. The module only drives the source dead clip and lets the
        // host complete teardown/corpse (same contract as pc_p2_sokkuri/armor).
        break;
    default:
        break;
    }
    setPhase(s);
    fireEvents(actor, s);
    s.logTimer += dt;
    if (s.logTimer >= 1.0f) {
        s.logTimer = 0.0f;
        std::printf("P2_OTAKARA_POS generator=%u state=%s clip=%s phase=%.2f x=%.2f z=%.2f\n",
                    generator, stateName(s.state), s.clip.c_str(), s.phase, pos.x, pos.z);
        std::fflush(stdout);
    }
}
