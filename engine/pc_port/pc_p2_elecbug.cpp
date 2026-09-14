// Family-owned ground-invertebrate source behavior for the batch-2 Chappy
// placement vehicle: Anode Beetle (ElecBug, EnemyID 28). Implements the source
// ElecBugState.cpp cycle (Wait/Turn/Move wander -> Charge -> Discharge -> Return)
// plus the source two-beetle Charge/ChildCharge partner link and the Reverse flip
// from ElecBug.cpp::pressCallBack / StateReverse. Source revision
// 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms from
// experimental/pikmin2_ground_inverts_assets.py (GPVE01 rev 0).
//
// Source contract implemented:
//   * StateCharge::exec searches once, 2.0s into Charge, for a live unlinked
//     beetle in Wait/Turn/Move within 300 units and links reciprocally via
//     startChargeState/startChildChargeState (generator Charge, child ChildCharge).
//   * Charge lasts 3.0s then Discharge; ChildCharge lasts 1.0s then ChildDischarge.
//     On discharge the generator sweeps the electrical receiver across the pair.
//   * Partner links break on partner death, press/Reverse (finishPartnerAndEffect),
//     discharge completion and partner loss.
//
// Port adaptations (recorded, not retail-faithful):
//   * Partner selection is nearest-first (the source picks uniformly at random
//     among candidates within 300 units).
//   * Between-beetle Denki geometry is resolved as a single nearest shockable
//     Pikmin within the discharge radius of either linked beetle, shocked once
//     per discharge. The emitter now delivers the real lane-10 `InteractDenki`
//     receiver (not InteractKill), so the source Yellow/Bulbmin exclusion is
//     enforced by the lane-11 species capability matrix exactly as the receiver
//     does; a non-immune target transits PIKISTATE_DenkiDying.
//   * Charge and ChildCharge durations are port values (source hard-codes
//     mStateTimer > 3.0 / > 1.0; Return ends on animation end).
//   * View angle is a full hemisphere.
// No other lane's module is modified; every hook is a no-op for unregistered actors.
#include "pc_p2_elecbug.h"
#include "pc_p2_species.h"
#include "pc_p2_hazard_emitter.h"
#include "teki.h"
#include "Interactions.h"
#include "Piki.h"
#include "PikiState.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "GlobalGameOptions.h"
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
    ELEC_INVALID = -1,
    ELEC_DEAD = 0,
    ELEC_WAIT = 1,
    ELEC_TURN = 2,
    ELEC_MOVE = 3,
    ELEC_CHARGE = 4,
    ELEC_DISCHARGE = 5,
    ELEC_CHILDCHARGE = 6,
    ELEC_CHILDISCHARGE = 7,
    ELEC_REVERSE = 8,
    ELEC_RETURN = 9,
};

const char* stateName(State s) {
    switch (s) {
    case ELEC_DEAD: return "dead";
    case ELEC_WAIT: return "wait";
    case ELEC_TURN: return "turn";
    case ELEC_MOVE: return "move";
    case ELEC_CHARGE: return "charge";
    case ELEC_DISCHARGE: return "discharge";
    case ELEC_CHILDCHARGE: return "childcharge";
    case ELEC_CHILDISCHARGE: return "childdischarge";
    case ELEC_REVERSE: return "reverse";
    case ELEC_RETURN: return "return";
    default: return "null";
    }
}

// Source enemyparm.txt values (ground_inverts manifest general/proper).
constexpr float LIFE = 500.0f;
constexpr float MOVE_SPEED = 30.0f;
constexpr float SIGHT = 200.0f;
constexpr float TERRITORY = 200.0f;
constexpr float HOME_RADIUS = 100.0f;
constexpr float FLIP_TIME = 5.0f;         // fp01
constexpr float WAIT_TIME = 1.5f;         // fp02
constexpr float DISCHARGE_TIME = 3.0f;    // fp11
constexpr float CHARGE_TIME = 3.0f;       // source StateCharge mStateTimer > 3.0
constexpr float CHILD_CHARGE_TIME = 1.0f; // source StateChildCharge mStateTimer > 1.0
constexpr float CHARGE_SEARCH_DELAY = 2.0f; // source mStateTimer > 2.0
constexpr float PAIR_RADIUS = 300.0f;     // source bugPos.distance(otherPos) < 300
constexpr float RETURN_TIME = 0.5f;       // port value
constexpr float WANDER_TIME = 1.5f;       // port value
constexpr float ELEC_RADIUS = 70.0f;      // source sweep radius fp20/22 = 70
constexpr float TURN_RATE = 2.0f;

struct Clip {
    std::string name;
    float duration = 1.0f;
    bool loop = false;
};

struct ElecBug {
    State state = ELEC_WAIT;
    float stateTime = 0.0f;
    float heading = 0.0f;
    Vector3f home;
    BTeki* self = nullptr;
    BTeki* partner = nullptr;
    bool hasSearched = false;
    bool shockedThisDischarge = false;
    bool immuneLogged = false;
    bool flipped = false;
    bool deadLogged = false;
    float lastHealth = LIFE;
    std::string clip = "wait";
    float phase = 0.0f;
    float logTimer = 0.0f;
};

std::map<PelletView*, ElecBug> actors;
std::map<std::string, Clip> clips;
bool ready = false;

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
unsigned genOf(const BTeki* actor) { return actor && actor->mGenerator ? actor->mGenerator->_70 : 0u; }
ElecBug* lookup(BTeki* actor) {
    auto it = actors.find(static_cast<PelletView*>(actor));
    return it == actors.end() ? nullptr : &it->second;
}
bool targetInSight(const Vector3f& pos) {
    if (naviMgr) {
        Navi* n = naviMgr->getNavi();
        if (n && n->isAlive() && distXZ(n->getPosition(), pos) < SIGHT) return true;
    }
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (p && p->isAlive() && distXZ(p->getPosition(), pos) < SIGHT) return true;
        }
    }
    return false;
}
// A Pikmin is shockable exactly when the lane-10 electric receiver would accept
// it: the lane-11 capability matrix rejects electric-immune species (Yellow,
// Bulbmin) and everything else transits PIKISTATE_DenkiDying. Deriving the
// emitter's target from the receiver's own decision keeps the two in lockstep.
bool elecShockable(const Piki* p) {
    if (!p || !p->isAlive()) return false;
    return p2_emitter_accepts(pc_p2_species(p), P2HazardElectric, p->gasInvicible());
}
Piki* nearestShockable(const Vector3f& pos, float radius) {
    Piki* best = nullptr;
    float bestSq = radius * radius;
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!elecShockable(p)) continue;
            const float d = distXZ(p->getPosition(), pos);
            if (d < radius && d * d < bestSq) { bestSq = d * d; best = p; }
        }
    }
    return best;
}
// The source StateDischarge::checkInteract sweeps the Denki line between the two
// linked beetles. The emitter resolves the nearest shockable Pikmin to either
// end of the pair and delivers the real lane-10 InteractDenki receiver.
Piki* nearestShockablePair(const Vector3f& pos, const BTeki* partner, float radius) {
    Piki* best = nearestShockable(pos, radius);
    if (!best && partner) best = nearestShockable(partner->getPosition(), radius);
    return best;
}
const char* colorName(unsigned color) {
    switch (color) {
    case Blue: return "blue";
    case Red: return "red";
    case Yellow: return "yellow";
    default: return "other";
    }
}
// Source InteractDenki::actPiki excludes Yellow/Bulbmin from the discharge. The
// receiver and the emitter both consult the lane-11 matrix, so this probe
// reports every immune species inside the sweep that was deliberately rejected,
// emitting one immunity marker per species. Returns true when any was in range.
bool logElecImmuneInRange(unsigned generator, const Vector3f& pos, float radius) {
    if (!pikiMgr) return false;
    bool sawYellow = false, sawBulbmin = false;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive()) continue;
        const int species = pc_p2_species(p);
        if (!p2_species_immune(species, P2HazardElectric)) continue;
        if (distXZ(p->getPosition(), pos) >= radius) continue;
        if (species == P2SpeciesBulbmin) sawBulbmin = true;
        else if (species == P2SpeciesYellow) sawYellow = true;
    }
    if (sawYellow) {
        std::printf("P2_ELECBUG_IMMUNE generator=%u source_id=28 pikmin=yellow species=2\n",
                    generator);
    }
    if (sawBulbmin) {
        std::printf("P2_ELECBUG_IMMUNE generator=%u source_id=28 pikmin=bulbmin species=5\n",
                    generator);
    }
    std::fflush(stdout);
    return sawYellow || sawBulbmin;
}
void enter(ElecBug& s, State state, const char* clip) {
    s.state = state;
    s.stateTime = 0.0f;
    if (clip) s.clip = clip;
}
void wander(BTeki* a, ElecBug& s) {
    a->setDirection(s.heading);
    const Vector3f drive(std::sin(s.heading) * MOVE_SPEED, 0.0f, std::cos(s.heading) * MOVE_SPEED);
    a->inputDrive(drive);
    a->mVelocity.set(drive);
}
void stop(BTeki* a) {
    a->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
    a->mVelocity.x = 0.0f;
    a->mVelocity.z = 0.0f;
}
void setPhase(ElecBug& s) {
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
// Source Obj::resetPartnerPtr / finishPartnerAndEffect null both sides. Log the
// unlink for each beetle that actually carried the pointer.
void breakLink(BTeki* actor, ElecBug& s) {
    BTeki* partner = s.partner;
    if (!partner) return;
    ElecBug* other = lookup(partner);
    s.partner = nullptr;
    if (other) other->partner = nullptr;
    std::printf("P2_ELECBUG_UNLINK generator=%u\n", genOf(actor));
    if (other) std::printf("P2_ELECBUG_UNLINK generator=%u\n", genOf(partner));
    std::fflush(stdout);
}
// Source StateCharge::exec picks among other beetles within 300 units that are in
// a pre-charge state. A beetle already in Charge but still unlinked is also a
// valid candidate here so two beetles that acquire sight on the same frame still
// form a pair (the source staggers via its random inactive timer).
BTeki* nearestPartner(BTeki* actor, float radius) {
    const Vector3f pos = actor->getPosition();
    BTeki* best = nullptr;
    float bestSq = radius * radius;
    for (auto& entry : actors) {
        ElecBug& other = entry.second;
        if (!other.self || other.self == actor) continue;
        if (other.partner || other.state == ELEC_DEAD) continue;
        if (other.self->mHealth <= 0.0f) continue;
        if (other.state != ELEC_WAIT && other.state != ELEC_TURN
                && other.state != ELEC_MOVE && other.state != ELEC_CHARGE) continue;
        const float d = distXZ(pos, other.self->getPosition());
        if (d < radius && d * d < bestSq) { bestSq = d * d; best = other.self; }
    }
    return best;
}
// Source startChargeState/startChildChargeState reciprocal assignment.
void linkPair(BTeki* actor, ElecBug& s, BTeki* partner, ElecBug& child) {
    s.partner = partner;
    child.partner = actor;
    s.hasSearched = true;
    child.hasSearched = true;
    child.shockedThisDischarge = false;
    child.immuneLogged = false;
    child.flipped = false;
    enter(child, ELEC_CHILDCHARGE, "charge");
    std::printf("P2_ELECBUG_LINK generator=%u partner=%u\n", genOf(actor), genOf(partner));
    std::printf("P2_ELECBUG_STATE generator=%u state=childcharge\n", genOf(partner));
    std::fflush(stdout);
}
// Source StateCharge::exec faces the pair outward: target = bugPos + (bugPos - partnerPos).
void turnTowardsPair(BTeki* a, ElecBug& s) {
    if (!s.partner) return;
    const Vector3f bugPos = a->getPosition();
    const Vector3f partnerPos = s.partner->getPosition();
    const float dx = bugPos.x - partnerPos.x;
    const float dz = bugPos.z - partnerPos.z;
    if (dx * dx + dz * dz < 1e-6f) return;
    s.heading = std::atan2(dx, dz);
    a->setDirection(s.heading);
}
}

void pc_p2_elecbug_reset() {
    actors.clear();
    clips.clear();
    ready = false;
}
void pc_p2_elecbug_forget(BTeki* actor) {
    ElecBug* s = lookup(actor);
    if (s && s->partner) breakLink(actor, *s);
    actors.erase(static_cast<PelletView*>(actor));
}

float pc_p2_elecbug_param_f(const BTeki* actor, int idx, float fallback) {
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

bool pc_p2_elecbug_attacked(Teki* teki) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(teki));
    if (it == actors.end()) return false;
    if (it->second.state == ELEC_DEAD) return false;
    if (!it->second.flipped) {
        // Source ElecBug::init enables invulnerability; any attack is swallowed.
        std::printf("P2_ELECBUG_ATTACK_BLOCKED generator=%u source_id=28 invulnerable=1\n",
                    genOf(teki));
        std::fflush(stdout);
        return true;
    }
    // Source StateReverse::init disables invulnerability: the attack lands.
    std::printf("P2_ELECBUG_ATTACK_ACCEPTED generator=%u source_id=28 state=reverse health=%.1f\n",
                genOf(teki), teki->mHealth);
    std::fflush(stdout);
    return false;
}

bool pc_p2_elecbug_pressed(BTeki* teki, Creature* presser) {
    if (!ready) return false;
    ElecBug* s = lookup(teki);
    if (!s) return false;
    if (s->state == ELEC_DEAD || s->state == ELEC_REVERSE) return true;
    // Source ElecBug::pressCallBack: an actively discharging beetle sends Denki
    // to the pressing Pikmin (InteractDenki still excludes Yellow/Bulbmin).
    if (s->state == ELEC_DISCHARGE || s->state == ELEC_CHILDISCHARGE) {
        Piki* piki = (presser && presser->isPiki()) ? static_cast<Piki*>(presser) : nullptr;
        if (piki && piki->isAlive()) {
            const int species = pc_p2_species(piki);
            if (p2_species_immune(species, P2HazardElectric)) {
                std::printf("P2_ELECBUG_PRESS_IMMUNE generator=%u source_id=28 pikmin=%s species=%d\n",
                            genOf(teki), species == P2SpeciesBulbmin ? "bulbmin" : "yellow", species);
            } else {
                Vector3f dir(piki->getPosition().x - teki->getPosition().x, 0.0f,
                             piki->getPosition().z - teki->getPosition().z);
                const bool accepted = piki->stimulate(InteractDenki(teki, 1.0f, &dir));
                std::printf("P2_ELECBUG_PRESS_DENKI generator=%u source_id=28 pikmin=1 target=%d accepted=%d "
                            "target_state=%d(%s)\n",
                            genOf(teki), species, int(accepted), piki->getState(),
                            piki->getState() == PIKISTATE_DenkiDying ? "DenkiDying" : "other");
                std::printf("P2_ELECBUG_PRESS_SHOCK generator=%u source_id=28 pikmin=1 color=%s\n",
                            genOf(teki), colorName(piki->mColor));
            }
            std::fflush(stdout);
        }
    }
    if (s->partner) breakLink(teki, *s); // source StateReverse::init finishPartnerAndEffect
    s->flipped = true;
    enter(*s, ELEC_REVERSE, "recover");
    std::printf("P2_ELECBUG_FLIP generator=%u source_id=28\n", genOf(teki));
    std::printf("P2_ELECBUG_STATE generator=%u state=reverse\n", genOf(teki));
    std::fflush(stdout);
    return true;
}

bool pc_p2_elecbug_clip(const BTeki* actor, const char*& name, float& phase) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    name = it->second.clip.c_str();
    phase = it->second.phase;
    return true;
}

// Read-only state probe for the private runtime fixture. It lets an injected
// main schedule the press/discharge gates at the exact source state; it never
// mutates behavior and returns nullptr for unregistered actors.
const char* pc_p2_elecbug_state_name(const BTeki* actor) {
    if (!ready) return nullptr;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return nullptr;
    return stateName(it->second.state);
}

void pc_p2_elecbug_setup() {
    pc_p2_elecbug_reset();
    if (!tekiMgr) return;

    std::ifstream bank("p2-ground-bank.txt");
    if (bank) {
        std::string token;
        if (bank >> token && token == "P2_GROUND_BANK_1") {
            while (bank >> token) {
                if (token == "species") {
                    std::string species, id;
                    bank >> species >> id;
                } else if (token == "clip") {
                    std::string species, name, events, marker, status;
                    long long frames = 0;
                    int poses = 0;
                    bank >> species >> name >> frames >> events >> marker >> poses >> status;
                    if (species == "ElecBug") {
                        Clip clip;
                        clip.name = name;
                        clip.duration = frames > 0 ? float(frames) / 30.0f : 1.0f;
                        clip.loop = (name == "move" || name == "wait");
                        clips[name] = clip;
                    }
                } else {
                    break;
                }
            }
        }
    }

    std::ifstream in("p2-ground-actors.txt");
    if (!in) return;
    std::string header;
    int count = 0;
    if (!(in >> header >> count) || header != "P2_GROUND_ACTORS_1" || count < 1) return;
    std::map<unsigned, std::string> wanted;
    for (int i = 0; i < count; ++i) {
        unsigned long long generator = 0;
        std::string species;
        if (!(in >> generator >> species)) return;
        if (species == "ElecBug") wanted[unsigned(generator)] = species;
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
            std::printf("P2_ELECBUG_ERROR native_type generator=%u\n", actor->mGenerator->_70);
            std::abort();
        }
        ElecBug& s = actors[static_cast<PelletView*>(actor)];
        s.self = actor;
        s.home = actor->getPosition();
        s.heading = actor->getDirection();
        actor->mHealth = LIFE;
        enter(s, ELEC_WAIT, "wait");
        std::printf("P2_ELECBUG_BIND generator=%u source_id=28 visual_only=0\n",
                    actor->mGenerator->_70);
        const Vector3f pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=ElecBug native_family=Chappy generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented attack=discharge_receiver\n",
                    actor->mGenerator->_70, pos.x, pos.y, pos.z, actor->mHealth, LIFE);
        found.insert(actor->mGenerator->_70);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_ELECBUG_ERROR missing_actor wanted=%zu found=%zu\n", wanted.size(), found.size());
        std::abort();
    }
    ready = true;
}

void pc_p2_elecbug_update(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    ElecBug& s = it->second;
    const float dt = gsys->getFrameTime();
    if (dt <= 0.0f || dt > 0.5f) return;
    const Vector3f pos = actor->getPosition();
    const unsigned generator = genOf(actor);

    // Reversed beetles accept InteractAttack damage; every non-lethal drop is the
    // runtime proof that invulnerability is disabled while flipped.
    if (actor->mHealth < s.lastHealth && actor->mHealth > 0.0f) {
        std::printf("P2_ELECBUG_HIT generator=%u source_id=28 health=%.1f\n",
                    generator, actor->mHealth);
        std::fflush(stdout);
    }
    s.lastHealth = actor->mHealth;

    if (actor->mHealth <= 0.0f && s.state != ELEC_DEAD) {
        if (s.partner) breakLink(actor, s);
        if (!s.deadLogged) {
            std::printf("P2_ELECBUG_DEAD generator=%u source_id=28 health=0\n", generator);
            std::fflush(stdout);
            s.deadLogged = true;
        }
        enter(s, ELEC_DEAD, "dead");
    }

    // Partner loss (removed from the arena, dead, or health-0) breaks the link.
    if (s.state != ELEC_DEAD && s.partner) {
        ElecBug* other = lookup(s.partner);
        if (!other || !other->self || other->state == ELEC_DEAD || other->self->mHealth <= 0.0f) {
            breakLink(actor, s);
        }
    }

    s.stateTime += dt;
    switch (s.state) {
    case ELEC_WAIT:
        stop(actor);
        if (targetInSight(pos)) {
            std::printf("P2_ELECBUG_STATE generator=%u state=charge\n", generator);
            s.hasSearched = false;
            enter(s, ELEC_CHARGE, "charge");
        } else if (s.stateTime > WAIT_TIME) {
            std::printf("P2_ELECBUG_STATE generator=%u state=move\n", generator);
            enter(s, ELEC_MOVE, "move");
        }
        break;
    case ELEC_TURN:
        stop(actor);
        if (s.stateTime > RETURN_TIME) {
            std::printf("P2_ELECBUG_STATE generator=%u state=move\n", generator);
            enter(s, ELEC_MOVE, "move");
        }
        break;
    case ELEC_MOVE:
        if (targetInSight(pos)) {
            std::printf("P2_ELECBUG_STATE generator=%u state=charge\n", generator);
            s.hasSearched = false;
            enter(s, ELEC_CHARGE, "charge");
            break;
        }
        s.heading = wrapPi(s.heading + 0.4f * dt);
        wander(actor, s);
        if (s.stateTime > WANDER_TIME) {
            std::printf("P2_ELECBUG_STATE generator=%u state=wait\n", generator);
            enter(s, ELEC_WAIT, "wait");
        }
        break;
    case ELEC_CHARGE: {
        stop(actor);
        if (!s.hasSearched && s.stateTime >= CHARGE_SEARCH_DELAY) {
            s.hasSearched = true;
            BTeki* partner = nearestPartner(actor, PAIR_RADIUS);
            ElecBug* child = partner ? lookup(partner) : nullptr;
            if (child) linkPair(actor, s, partner, *child);
        }
        if (s.partner) turnTowardsPair(actor, s);
        if (s.stateTime >= CHARGE_TIME) {
            if (s.partner) {
                s.shockedThisDischarge = false;
                s.immuneLogged = false;
                std::printf("P2_ELECBUG_STATE generator=%u state=discharge\n", generator);
                std::printf("P2_ELECBUG_DISCHARGE generator=%u source_id=28 duration=%.3f state=charge\n",
                            generator, DISCHARGE_TIME);
                std::fflush(stdout);
                enter(s, ELEC_DISCHARGE, "discharge");
            } else {
                std::printf("P2_ELECBUG_STATE generator=%u state=return\n", generator);
                enter(s, ELEC_RETURN, "recover");
            }
        }
        break;
    }
    case ELEC_CHILDCHARGE: {
        stop(actor);
        if (s.partner) turnTowardsPair(actor, s);
        if (s.stateTime >= CHILD_CHARGE_TIME) {
            if (s.partner) {
                s.shockedThisDischarge = false;
                s.immuneLogged = false;
                std::printf("P2_ELECBUG_STATE generator=%u state=childdischarge\n", generator);
                std::printf("P2_ELECBUG_DISCHARGE generator=%u source_id=28 duration=%.3f state=child\n",
                            generator, DISCHARGE_TIME);
                std::fflush(stdout);
                enter(s, ELEC_CHILDISCHARGE, "discharge");
            } else {
                std::printf("P2_ELECBUG_STATE generator=%u state=return\n", generator);
                enter(s, ELEC_RETURN, "recover");
            }
        }
        break;
    }
    case ELEC_DISCHARGE: {
        stop(actor);
        if (!s.partner) {
            std::printf("P2_ELECBUG_STATE generator=%u state=return\n", generator);
            enter(s, ELEC_RETURN, "recover");
            break;
        }
        if (!s.shockedThisDischarge) {
            Piki* piki = nearestShockablePair(pos, s.partner, ELEC_RADIUS);
            if (piki) {
                s.shockedThisDischarge = true;
                const Vector3f target = piki->getPosition();
                Vector3f dir(target.x - pos.x, 0.0f, target.z - pos.z);
                const bool accepted = piki->stimulate(InteractDenki(actor, 1.0f, &dir));
                const int targetState = piki->getState();
                std::printf("P2_ELECBUG_DENKI generator=%u source_id=28 emitter=sweep target=%d "
                            "accepted=%d target_state=%d(%s)\n",
                            generator, pc_p2_species(piki), int(accepted), targetState,
                            targetState == PIKISTATE_DenkiDying ? "DenkiDying" : "other");
                std::printf("P2_ELECBUG_SHOCK generator=%u pikmin=1 color=%s\n", generator,
                            colorName(piki->mColor));
                std::fflush(stdout);
            }
        }
        // Emit one immunity marker per immune species inside the sweep that the
        // source Yellow/Bulbmin gate deliberately rejected.
        if (!s.immuneLogged) {
            bool found = logElecImmuneInRange(generator, pos, ELEC_RADIUS);
            if (!found && s.partner) {
                found = logElecImmuneInRange(generator, s.partner->getPosition(), ELEC_RADIUS);
            }
            if (found) s.immuneLogged = true;
        }
        if (s.stateTime >= DISCHARGE_TIME) {
            breakLink(actor, s);
            std::printf("P2_ELECBUG_STATE generator=%u state=return\n", generator);
            enter(s, ELEC_RETURN, "recover");
        }
        break;
    }
    case ELEC_CHILDISCHARGE: {
        stop(actor);
        if (!s.partner) {
            std::printf("P2_ELECBUG_STATE generator=%u state=wait\n", generator);
            enter(s, ELEC_WAIT, "wait");
            break;
        }
        if (s.stateTime >= DISCHARGE_TIME) {
            breakLink(actor, s);
            std::printf("P2_ELECBUG_STATE generator=%u state=wait\n", generator);
            enter(s, ELEC_WAIT, "wait");
        }
        break;
    }
    case ELEC_RETURN:
        stop(actor);
        if (s.stateTime >= RETURN_TIME) {
            std::printf("P2_ELECBUG_STATE generator=%u state=wait\n", generator);
            enter(s, ELEC_WAIT, "wait");
        }
        break;
    case ELEC_REVERSE:
        stop(actor);
        if (s.stateTime >= FLIP_TIME) {
            s.flipped = false;
            std::printf("P2_ELECBUG_RECOVER generator=%u source_id=28\n", generator);
            std::fflush(stdout);
            enter(s, ELEC_RETURN, "recover");
        }
        break;
    case ELEC_DEAD:
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
        std::printf("P2_ELECBUG_POS generator=%u state=%s clip=%s phase=%.2f x=%.2f z=%.2f\n",
                    generator, stateName(s.state), s.clip.c_str(), s.phase, pos.x, pos.z);
        std::fflush(stdout);
    }
}
