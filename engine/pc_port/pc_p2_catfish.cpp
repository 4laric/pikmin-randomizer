// Catfish (Water Dumple, EnemyID 26) source behavior on the P1 TEKI_Namazu
// placement vehicle. Catfish has no dedicated state file: Catfish.cpp forwards
// onInit/birth to the shared KochappyBase FSM (KochappyBase.cpp and
// kochappyState.cpp). This port implements that inherited source FSM:
//   Wait 0 -> Turn 2 -> Walk 3 -> Attack 4 -> Flick 5,
//   TurnToHome 6 -> GoHome 7, Dead 1.
// Attack is driven by the source animation key events: the bite event runs
// attackNavi + eatPikmin (or the Eat motion) and the later event runs
// swallowPikmin. Source revision 632af93787b9c95b63f0c13be32b161375ce3a96;
// retail parms from experimental/pikmin2_aquatic_assets.py (GPVE01 rev 0).
//
// Port adaptations (recorded, not retail-faithful):
//   * The P2 two-slot mouth (kamu1/kamu2, Catfish.cpp:83) is not representable
//     on the P1 host. The P2 swallow is resolved as an explicit capture inside
//     the source attack sweep radius at the banked attack bite animation event
//     (attack frame 17, event 2), then exactly one InteractKill at the banked
//     swallow event (attack frame 75, event 3). Exactly-once per bite; mirrors
//     the Armor port.
//   * Catfish ships no waitact1 clip (the KochappyBase Turn motion), so the Turn
//     state reuses wait1. The Eat motion (waitact2) is not entered because the
//     bite and swallow both live in the single attack clip.
//   * Target detection accepts the nearest Navi or Pikmin; the source view angle
//     is treated as a full hemisphere because the Catfish general block does not
//     override it. Turn rate, flick radius and shake values are P1-host values.
// Every hook is a no-op for unregistered actors; no other lane's module is
// modified.
#include "pc_p2_catfish.h"
#include "teki.h"
#include "Interactions.h"
#include "Piki.h"
#include "PikiMgr.h"
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
    CATFISH_INVALID = -1,
    CATFISH_WAIT = 0,
    CATFISH_DEAD = 1,
    CATFISH_TURN = 2,
    CATFISH_WALK = 3,
    CATFISH_ATTACK = 4,
    CATFISH_FLICK = 5,
    CATFISH_TURNTOHOME = 6,
    CATFISH_GOHOME = 7,
};

const char* stateName(State s) {
    switch (s) {
    case CATFISH_WAIT: return "wait";
    case CATFISH_DEAD: return "dead";
    case CATFISH_TURN: return "turn";
    case CATFISH_WALK: return "walk";
    case CATFISH_ATTACK: return "attack";
    case CATFISH_FLICK: return "flick";
    case CATFISH_TURNTOHOME: return "turntohome";
    case CATFISH_GOHOME: return "gohome";
    default: return "null";
    }
}

// Source enemyparm.txt values (aquatic manifest general + KochappyBase proper).
constexpr float LIFE = 200.0f;          // general fp00
constexpr float MOVE_SPEED = 60.0f;     // general fp06
constexpr float TERRITORY = 280.0f;     // general fp09
constexpr float HOME_RADIUS = 80.0f;    // general fp10
constexpr float SIGHT = 200.0f;         // general fp12
constexpr float ATTACK_RANGE = 50.0f;   // general fp20/fp22 attack hit
constexpr float ATTACK_ANGLE = 0.785398f; // port adaptation ~45 deg
constexpr float ABSENT_MINDED = 2.0f;   // proper fp01
constexpr float TURN_RATE = 2.5f;       // port adaptation
constexpr float FLICK_RADIUS = 25.0f;   // port adaptation
constexpr float SHAKE_RANGE = 100.0f;   // port adaptation
constexpr float SHAKE_KNOCKBACK = 120.0f; // port adaptation
constexpr float PI_F = 3.14159265f;

struct Clip {
    std::string name;
    float duration = 1.0f;
    bool loop = false;
    std::vector<std::pair<int, int>> events; // source frame -> event code
};

struct Catfish {
    State state = CATFISH_WAIT;
    float stateTime = 0.0f;
    float heading = 0.0f;
    Vector3f home;
    Vector3f wanderTarget;
    bool wanderValid = false;
    Piki* captured = nullptr;
    std::set<int> firedEvents;
    std::string clip = "wait1";
    float phase = 0.0f;
    unsigned rng = 1;
    bool deadLogged = false;
    float logTimer = 0.0f;
};

std::map<PelletView*, Catfish> actors;
std::map<std::string, Clip> clips;
bool ready = false;

float wrapPi(float a) {
    while (a > PI_F) a -= 2.0f * PI_F;
    while (a < -PI_F) a += 2.0f * PI_F;
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
unsigned nextRand(Catfish& s) {
    s.rng = s.rng * 1664525u + 1013904223u;
    return s.rng >> 8;
}
float rand01(Catfish& s) { return float(nextRand(s) & 0xffff) / 65535.0f; }

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
Piki* nearestPiki(const Vector3f& pos, float radius) {
    Piki* best = nullptr;
    float bestSq = radius * radius;
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
bool shouldFlick(BTeki* a) {
    return nearestPiki(a->getPosition(), FLICK_RADIUS) != nullptr;
}
void doFlick(BTeki* a) {
    if (!pikiMgr) return;
    const Vector3f pos = a->getPosition();
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (p && p->isAlive() && distXZ(p->getPosition(), pos) < SHAKE_RANGE) {
            p->stimulate(InteractFlick(a, SHAKE_KNOCKBACK, 0.0f, a->getDirection()));
        }
    }
}
void stop(BTeki* a) {
    a->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
    a->mVelocity.x = 0.0f;
    a->mVelocity.z = 0.0f;
}
void setRandTarget(Catfish& s, const Vector3f& pos) {
    const float radius = 0.5f * (TERRITORY - HOME_RADIUS) * rand01(s) + HOME_RADIUS;
    const float angle = 2.0f * PI_F * rand01(s);
    s.wanderTarget.x = radius * std::sin(angle) + s.home.x;
    s.wanderTarget.y = s.home.y;
    s.wanderTarget.z = radius * std::cos(angle) + s.home.z;
    s.wanderValid = true;
    (void)pos;
}
// Rotate toward a point; returns the residual angle to the target after the turn.
float turnTo(BTeki* a, Catfish& s, const Vector3f& target, float dt) {
    const Vector3f pos = a->getPosition();
    const float desired = std::atan2(target.x - pos.x, target.z - pos.z);
    const float maxTurn = TURN_RATE * dt;
    float diff = wrapPi(desired - s.heading);
    if (diff > maxTurn) diff = maxTurn;
    if (diff < -maxTurn) diff = -maxTurn;
    s.heading = wrapPi(s.heading + diff);
    a->setDirection(s.heading);
    return wrapPi(desired - s.heading);
}
void walkTo(BTeki* a, Catfish& s, const Vector3f& target, float dt) {
    turnTo(a, s, target, dt);
    const Vector3f drive(std::sin(s.heading) * MOVE_SPEED, 0.0f,
                         std::cos(s.heading) * MOVE_SPEED);
    a->inputDrive(drive);
    a->mVelocity.set(drive);
}
float targetAngle(const Catfish& s, const Vector3f& pos, const Vector3f& target) {
    return std::fabs(wrapPi(std::atan2(target.x - pos.x, target.z - pos.z) - s.heading));
}
void setPhase(Catfish& s) {
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
void transition(Catfish& s, State state, const char* clip, unsigned generator) {
    s.state = state;
    s.stateTime = 0.0f;
    s.firedEvents.clear();
    s.captured = nullptr;
    if (clip) s.clip = clip;
    std::printf("P2_CATFISH_STATE generator=%u state=%s\n", generator, stateName(state));
    std::fflush(stdout);
}

// Source StateAttack events: event 2 = bite (attackNavi + eatPikmin), event 3 =
// swallowPikmin. Resolved as capture then one kill for the P1 host.
void fireAttackEvents(BTeki* actor, Catfish& s, unsigned generator) {
    auto it = clips.find("attack");
    if (it == clips.end()) return;
    const Vector3f pos = actor->getPosition();
    for (const auto& event : it->second.events) {
        if (s.firedEvents.count(event.first)) continue;
        if (s.stateTime < event.first / 30.0f) continue;
        s.firedEvents.insert(event.first);
        if (event.second == 2) {
            Piki* piki = nearestPiki(pos, ATTACK_RANGE);
            if (piki) {
                s.captured = piki;
                std::printf("P2_CATFISH_BITE generator=%u frame=%d pikmin=1\n",
                            generator, event.first);
                std::fflush(stdout);
            }
        } else if (event.second == 3) {
            if (s.captured && s.captured->isAlive()) {
                s.captured->stimulate(InteractKill(actor, 0));
                std::printf("P2_CATFISH_EAT generator=%u pikmin=1\n", generator);
                std::fflush(stdout);
            }
            s.captured = nullptr;
        }
    }
}
void fireFlickEvents(BTeki* actor, Catfish& s, unsigned generator) {
    auto it = clips.find("flick");
    if (it == clips.end()) return;
    for (const auto& event : it->second.events) {
        if (s.firedEvents.count(event.first)) continue;
        if (s.stateTime < event.first / 30.0f) continue;
        s.firedEvents.insert(event.first);
        if (event.second == 2) {
            doFlick(actor);
            std::printf("P2_CATFISH_FLICK generator=%u frame=%d\n",
                        generator, event.first);
            std::fflush(stdout);
        }
    }
}
bool attackable(const Catfish& s, const Vector3f& pos, Creature* target) {
    if (!target) return false;
    const Vector3f tp = target->getPosition();
    return distXZ(tp, pos) < ATTACK_RANGE && targetAngle(s, pos, tp) < ATTACK_ANGLE;
}
}

void pc_p2_catfish_reset() {
    actors.clear();
    clips.clear();
    ready = false;
}

void pc_p2_catfish_forget(BTeki* actor) {
    actors.erase(static_cast<PelletView*>(actor));
}

float pc_p2_catfish_param_f(const BTeki* actor, int idx, float fallback) {
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

bool pc_p2_catfish_clip(const BTeki* actor, const char*& name, float& phase) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    name = it->second.clip.c_str();
    phase = it->second.phase;
    return true;
}

void pc_p2_catfish_setup() {
    pc_p2_catfish_reset();
    if (!tekiMgr) return;

    // Clip durations and source key-event frames from the validated aquatic bank.
    std::ifstream bank("p2-aquatic-bank.txt");
    if (bank) {
        std::string token;
        if (bank >> token && token == "P2_AQUATIC_BANK_1") {
            while (bank >> token) {
                if (token == "species") {
                    std::string species, id;
                    bank >> species >> id;
                } else if (token == "clip") {
                    std::string species, name, frames, events, marker, poses, status;
                    bank >> species >> name >> frames >> events >> marker >> poses >> status;
                    if (species == "Catfish") {
                        Clip clip;
                        clip.name = name;
                        const double sourceFrames = std::atof(frames.c_str());
                        clip.duration = sourceFrames > 0.0 ? float(sourceFrames) / 30.0f : 1.0f;
                        clip.loop = (name == "wait1" || name == "move1");
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

    std::ifstream in("p2-aquatic-actors.txt");
    if (!in) return;
    std::string header;
    int count = 0;
    if (!(in >> header >> count) || header != "P2_AQUATIC_ACTORS_1" || count < 1) return;
    std::map<unsigned, std::string> wanted;
    for (int i = 0; i < count; ++i) {
        unsigned long long generator = 0;
        std::string species;
        if (!(in >> generator >> species)) return;
        if (species == "Catfish") wanted[unsigned(generator)] = species;
    }
    if (wanted.empty()) return;

    std::set<unsigned> found;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* actor = static_cast<Teki*>(*it);
        if (!actor || !actor->mGenerator) continue;
        auto match = wanted.find(actor->mGenerator->_70);
        if (match == wanted.end()) continue;
        if (actor->mTekiType != TEKI_Namazu) {
            std::printf("P2_CATFISH_ERROR native_type generator=%u\n", actor->mGenerator->_70);
            std::fflush(stdout);
            std::abort();
        }
        Catfish& s = actors[static_cast<PelletView*>(actor)];
        s.home = actor->getPosition();
        s.heading = actor->getDirection();
        s.wanderTarget = s.home;
        s.rng = (actor->mGenerator->_70 * 2654435761u) | 1u;
        actor->mHealth = LIFE;
        s.state = CATFISH_WAIT;
        s.clip = "wait1";
        std::printf("P2_CATFISH_BIND generator=%u source_id=26 visual_only=0\n",
                    actor->mGenerator->_70);
        const Vector3f pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=Catfish native_family=Namazu generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented attack=animation_event water=absent\n",
                    actor->mGenerator->_70, pos.x, pos.y, pos.z, actor->mHealth, LIFE);
        std::fflush(stdout);
        found.insert(actor->mGenerator->_70);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_CATFISH_ERROR missing_actor wanted=%zu found=%zu\n", wanted.size(), found.size());
        std::fflush(stdout);
        std::abort();
    }
    ready = true;
}

void pc_p2_catfish_update(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Catfish& s = it->second;
    const float dt = gsys->getFrameTime();
    if (dt <= 0.0f || dt > 0.5f) return;
    const Vector3f pos = actor->getPosition();
    const unsigned generator = actor->mGenerator ? actor->mGenerator->_70 : 0u;

    if (actor->mHealth <= 0.0f && s.state != CATFISH_DEAD) {
        if (!s.deadLogged) {
            std::printf("P2_CATFISH_DEAD generator=%u source_id=26 health=0\n", generator);
            std::fflush(stdout);
            s.deadLogged = true;
        }
        transition(s, CATFISH_DEAD, "dead", generator);
    }

    s.stateTime += dt;
    switch (s.state) {
    case CATFISH_WAIT: {
        stop(actor);
        if (shouldFlick(actor)) { transition(s, CATFISH_FLICK, "flick", generator); break; }
        Creature* target = nearestTarget(pos);
        if (target) {
            const Vector3f tp = target->getPosition();
            if (attackable(s, pos, target)) transition(s, CATFISH_ATTACK, "attack", generator);
            else if (targetAngle(s, pos, tp) < 0.1f) transition(s, CATFISH_WALK, "move1", generator);
            else transition(s, CATFISH_TURN, "wait1", generator);
        } else if (s.stateTime > ABSENT_MINDED) {
            setRandTarget(s, pos);
            transition(s, CATFISH_WALK, "move1", generator);
        }
        break;
    }
    case CATFISH_TURN: {
        stop(actor);
        if (shouldFlick(actor)) { transition(s, CATFISH_FLICK, "flick", generator); break; }
        Creature* target = nearestTarget(pos);
        if (!target) {
            if (s.stateTime > ABSENT_MINDED) transition(s, CATFISH_TURNTOHOME, "wait1", generator);
            break;
        }
        const Vector3f tp = target->getPosition();
        if (attackable(s, pos, target)) { transition(s, CATFISH_ATTACK, "attack", generator); break; }
        turnTo(actor, s, tp, dt);
        if (targetAngle(s, pos, tp) < 0.1f) transition(s, CATFISH_WALK, "move1", generator);
        break;
    }
    case CATFISH_WALK: {
        Creature* target = nearestTarget(pos);
        if (target) {
            const Vector3f tp = target->getPosition();
            if (attackable(s, pos, target)) { transition(s, CATFISH_ATTACK, "attack", generator); break; }
            walkTo(actor, s, tp, dt);
        } else {
            if (!s.wanderValid || distXZ(s.wanderTarget, pos) < 20.0f) setRandTarget(s, pos);
            walkTo(actor, s, s.wanderTarget, dt);
        }
        if (distXZ(pos, s.home) > TERRITORY) {
            transition(s, CATFISH_TURNTOHOME, "wait1", generator);
        } else if (shouldFlick(actor)) {
            transition(s, CATFISH_FLICK, "flick", generator);
        }
        break;
    }
    case CATFISH_ATTACK: {
        stop(actor);
        fireAttackEvents(actor, s, generator);
        if (s.stateTime >= clipDuration("attack")) {
            s.captured = nullptr;
            Creature* target = nearestTarget(pos);
            if (target && attackable(s, pos, target)) {
                transition(s, CATFISH_ATTACK, "attack", generator);
            } else if (target) {
                transition(s, CATFISH_TURN, "wait1", generator);
            } else {
                transition(s, CATFISH_TURNTOHOME, "wait1", generator);
            }
        }
        break;
    }
    case CATFISH_FLICK: {
        stop(actor);
        fireFlickEvents(actor, s, generator);
        if (s.stateTime >= clipDuration("flick")) {
            Creature* target = nearestTarget(pos);
            transition(s, target ? CATFISH_TURN : CATFISH_WAIT, "wait1", generator);
        }
        break;
    }
    case CATFISH_TURNTOHOME: {
        stop(actor);
        if (distXZ(pos, s.home) < HOME_RADIUS) {
            transition(s, CATFISH_WAIT, "wait1", generator);
            break;
        }
        Creature* target = nearestTarget(pos);
        if (target && attackable(s, pos, target)) {
            transition(s, CATFISH_ATTACK, "attack", generator);
            break;
        }
        turnTo(actor, s, s.home, dt);
        if (targetAngle(s, pos, s.home) < 0.1f) transition(s, CATFISH_GOHOME, "move1", generator);
        break;
    }
    case CATFISH_GOHOME: {
        if (distXZ(pos, s.home) < HOME_RADIUS) {
            transition(s, CATFISH_WAIT, "wait1", generator);
            break;
        }
        walkTo(actor, s, s.home, dt);
        break;
    }
    case CATFISH_DEAD:
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
        const Vector3f now = actor->getPosition();
        std::printf("P2_CATFISH_POS generator=%u state=%s clip=%s phase=%.2f "
                    "x=%.2f y=%.2f z=%.2f\n",
                    generator, stateName(s.state), s.clip.c_str(), s.phase,
                    now.x, now.y, now.z);
        std::fflush(stdout);
    }
}
