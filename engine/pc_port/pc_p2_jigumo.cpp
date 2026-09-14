// Jigumo / Hermit Crawmad (EnemyID 63, aquatic family #167) source behavior on
// the P1 TEKI_Chappy (3) placement vehicle, generator 374003. Jigumo owns a
// PanHouse child (Jigumo.cpp:73) and runs its own fourteen-state FSM
// (jigumoState.cpp:16). This port implements the bounded source slice:
//   Appear 1 -> Wait 0 -> Search 10 -> SAttack 11 / Attack 4 -> Miss 5 ->
//   Return 6 -> Carry 7 -> Eat 9 -> Hide 2, plus Flick 8 and Dead 3.
// Attack/S Attack are driven by the source animation key events: the bite
// event resolves an explicit capture and the later swallow event resolves
// exactly one InteractKill. Source revision
// 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms from
// experimental/pikmin2_aquatic_assets.py (GPVE01 rev 0).
//
// Port adaptations (recorded, not retail-faithful):
//   * No PanHouse/nest actor exists on the P1 host. The source birth creates a
//     PanHouse and links it through mHouse; here the nest is the Jigumo's home
//     point. Appear/Hide are animation-only (the source nest constraint and
//     revisionAnimPos nest-follow motion are not representable), so the host
//     stays at home while hidden and only the animation plays.
//   * The source mouth slot (JIGUMO_MOUTH_JOINT 0, MouthSlots) and the
//     Eat/S Attack swallowPikmin mouth matrix are not representable on the P1
//     host. The bite is resolved as an explicit capture inside the source
//     attack radius at the banked bite event frame, then exactly one
//     InteractKill at the banked swallow event frame; mirrors the Catfish and
//     Armor ports. Exactly-once per bite.
//   * The source view/search angle is a full hemisphere (the Jigumo general
//     block does not override the angle), so target selection ignores facing.
//     Turn rate, flick radius and shake values are P1-host values.
//   * The source damageCallBack part rule (only Carry/Return, head-vs-body) and
//     waterBox effects are not representable; damage is accepted while alive.
// Every hook is a no-op for unregistered actors; no other lane's module is
// modified.
#include "pc_p2_jigumo.h"
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
    JIGUMO_INVALID = -1,
    JIGUMO_WAIT = 0,
    JIGUMO_APPEAR = 1,
    JIGUMO_HIDE = 2,
    JIGUMO_DEAD = 3,
    JIGUMO_ATTACK = 4,
    JIGUMO_MISS = 5,
    JIGUMO_RETURN = 6,
    JIGUMO_CARRY = 7,
    JIGUMO_FLICK = 8,
    JIGUMO_EAT = 9,
    JIGUMO_SEARCH = 10,
    JIGUMO_SATTACK = 11,
    JIGUMO_SMISS = 12,
};

const char* stateName(State s) {
    switch (s) {
    case JIGUMO_WAIT: return "wait";
    case JIGUMO_APPEAR: return "appear";
    case JIGUMO_HIDE: return "hide";
    case JIGUMO_DEAD: return "dead";
    case JIGUMO_ATTACK: return "attack";
    case JIGUMO_MISS: return "miss";
    case JIGUMO_RETURN: return "return";
    case JIGUMO_CARRY: return "carry";
    case JIGUMO_FLICK: return "flick";
    case JIGUMO_EAT: return "eat";
    case JIGUMO_SEARCH: return "search";
    case JIGUMO_SATTACK: return "sattack";
    case JIGUMO_SMISS: return "smiss";
    default: return "null";
    }
}

// Source enemyparm.txt values (aquatic manifest general + Jigumo proper).
constexpr float LIFE = 500.0f;              // general fp00
constexpr float MOVE_SPEED = 300.0f;        // general fp06
constexpr float TERRITORY = 400.0f;         // general fp09
constexpr float HOME_RADIUS = 25.0f;        // general fp10
constexpr float SIGHT = 400.0f;             // general fp12
constexpr float ATTACK_RANGE = 200.0f;      // general fp20
constexpr float ATTACK_ANGLE = 3.14159265f; // port adaptation (hemisphere)
constexpr float CARRY_SPEED = 75.0f;        // proper fp01
constexpr float RETURN_SPEED = 30.0f;       // proper fp02
constexpr float HIDING_FRAMES = 30.0f;      // proper ip01
constexpr float SATTACK_ACTIVE_FRAME = 13.0f; // Jigumo.h:133
constexpr float TURN_RATE = 2.5f;           // port adaptation
constexpr float FLICK_RADIUS = 25.0f;       // port adaptation
constexpr float SHAKE_RANGE = 100.0f;       // port adaptation
constexpr float SHAKE_KNOCKBACK = 120.0f;   // port adaptation
constexpr float ARRIVE_DIST = 20.0f;
constexpr float PI_F = 3.14159265f;

struct Clip {
    std::string name;
    float duration = 1.0f;
    std::vector<std::pair<int, int>> events; // source frame -> event code
};

struct Jigumo {
    State state = JIGUMO_APPEAR;
    float stateTime = 0.0f;
    float heading = 0.0f;
    Vector3f home;
    Vector3f goal;
    bool appearArmed = false;
    bool attackActive = false;
    Piki* captured = nullptr;
    State nextState = JIGUMO_INVALID;
    const char* nextClip = nullptr;
    std::set<int> firedEvents;
    std::string clip = "appear1";
    float phase = 0.0f;
    bool deadLogged = false;
    float logTimer = 0.0f;
};

std::map<PelletView*, Jigumo> actors;
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
float turnTo(BTeki* a, Jigumo& s, const Vector3f& target, float dt) {
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
void walkTo(BTeki* a, Jigumo& s, const Vector3f& target, float speed, float dt) {
    turnTo(a, s, target, dt);
    const Vector3f drive(std::sin(s.heading) * speed, 0.0f, std::cos(s.heading) * speed);
    a->inputDrive(drive);
    a->mVelocity.set(drive);
}
void setPhase(Jigumo& s) {
    const float duration = clipDuration(s.clip);
    const float len = duration > 0.0f ? duration : 1.0f;
    s.phase = s.stateTime / len;
    if (s.phase > 1.0f) s.phase = 1.0f;
}
void transition(BTeki* actor, Jigumo& s, State state, const char* clip,
                unsigned generator, bool keepCaptured = false) {
    (void)actor;
    s.state = state;
    s.stateTime = 0.0f;
    s.firedEvents.clear();
    s.attackActive = false;
    if (!keepCaptured) s.captured = nullptr;
    if (clip) s.clip = clip;
    std::printf("P2_JIGUMO_STATE generator=%u state=%s\n", generator, stateName(state));
    std::fflush(stdout);
}
// Fires the first not-yet-fired event with the given code once its banked source
// frame is reached; returns true and the source frame when it fires.
bool dueEvent(Jigumo& s, const char* clipName, int code, int& frameOut) {
    auto it = clips.find(clipName);
    if (it == clips.end()) return false;
    for (const auto& event : it->second.events) {
        if (event.second != code) continue;
        if (s.firedEvents.count(event.first)) continue;
        if (s.stateTime < event.first / 30.0f) continue;
        s.firedEvents.insert(event.first);
        frameOut = event.first;
        return true;
    }
    return false;
}
void emitBite(unsigned generator, int frame) {
    std::printf("P2_JIGUMO_BITE generator=%u frame=%d pikmin=1\n", generator, frame);
    std::fflush(stdout);
}
void emitEat(unsigned generator) {
    std::printf("P2_JIGUMO_EAT generator=%u pikmin=1\n", generator);
    std::fflush(stdout);
}
bool resolveKill(BTeki* actor, Jigumo& s, unsigned generator) {
    if (s.captured && s.captured->isAlive()) {
        s.captured->stimulate(InteractKill(actor, 0));
        emitEat(generator);
        s.captured = nullptr;
        return true;
    }
    s.captured = nullptr;
    return false;
}
}

void pc_p2_jigumo_reset() {
    actors.clear();
    clips.clear();
    ready = false;
}

void pc_p2_jigumo_forget(BTeki* actor) {
    actors.erase(static_cast<PelletView*>(actor));
}

float pc_p2_jigumo_param_f(const BTeki* actor, int idx, float fallback) {
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

bool pc_p2_jigumo_clip(const BTeki* actor, const char*& name, float& phase) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    name = it->second.clip.c_str();
    phase = it->second.phase;
    return true;
}

void pc_p2_jigumo_setup() {
    pc_p2_jigumo_reset();
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
                    if (species == "Jigumo") {
                        Clip clip;
                        clip.name = name;
                        const double sourceFrames = std::atof(frames.c_str());
                        clip.duration = sourceFrames > 0.0 ? float(sourceFrames) / 30.0f : 1.0f;
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
        if (species == "Jigumo") wanted[unsigned(generator)] = species;
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
            std::printf("P2_JIGUMO_ERROR native_type generator=%u\n", actor->mGenerator->_70);
            std::fflush(stdout);
            std::abort();
        }
        Jigumo& s = actors[static_cast<PelletView*>(actor)];
        s.home = actor->getPosition();
        s.goal = s.home;
        s.heading = actor->getDirection();
        s.state = JIGUMO_APPEAR;
        s.clip = "appear1";
        s.appearArmed = false;
        actor->mHealth = LIFE;
        std::printf("P2_JIGUMO_BIND generator=%u source_id=63 visual_only=0\n",
                    actor->mGenerator->_70);
        const Vector3f pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=Jigumo native_family=Chappy generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented attack=animation_event nest=2\n",
                    actor->mGenerator->_70, pos.x, pos.y, pos.z, actor->mHealth, LIFE);
        std::printf("P2_JIGUMO_STATE generator=%u state=appear\n", actor->mGenerator->_70);
        std::fflush(stdout);
        found.insert(actor->mGenerator->_70);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_JIGUMO_ERROR missing_actor wanted=%zu found=%zu\n", wanted.size(), found.size());
        std::fflush(stdout);
        std::abort();
    }
    ready = true;
}

void pc_p2_jigumo_update(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Jigumo& s = it->second;
    const float dt = gsys->getFrameTime();
    if (dt <= 0.0f || dt > 0.5f) return;
    const Vector3f pos = actor->getPosition();
    const unsigned generator = actor->mGenerator ? actor->mGenerator->_70 : 0u;
    int frame = 0;

    if (actor->mHealth <= 0.0f && s.state != JIGUMO_DEAD) {
        if (!s.deadLogged) {
            std::printf("P2_JIGUMO_DEAD generator=%u source_id=63 health=0\n", generator);
            std::fflush(stdout);
            s.deadLogged = true;
        }
        transition(actor, s, JIGUMO_DEAD, "dead1", generator);
    }

    s.stateTime += dt;
    switch (s.state) {
    case JIGUMO_APPEAR: {
        stop(actor);
        if (!s.appearArmed) {
            // Source StateAppear holds the nest-hidden pose for mHidingTime,
            // then emerges only while a target is inside the territory.
            if (s.stateTime >= HIDING_FRAMES / 30.0f && nearestTarget(pos, TERRITORY)) {
                s.appearArmed = true;
                s.stateTime = 0.0f;
                s.clip = "appear1";
                std::printf("P2_JIGUMO_STATE generator=%u state=appear\n", generator);
                std::fflush(stdout);
            }
            break;
        }
        if (s.stateTime >= clipDuration("appear1")) {
            transition(actor, s, JIGUMO_WAIT, "wait1", generator);
        }
        break;
    }
    case JIGUMO_WAIT: {
        stop(actor);
        Creature* target = nearestTarget(pos, SIGHT);
        if (target) {
            s.goal = target->getPosition();
            transition(actor, s, JIGUMO_SEARCH, "turn1", generator);
            break;
        }
        if (s.stateTime >= clipDuration("wait1")) {
            transition(actor, s, JIGUMO_HIDE, "hide1", generator);
        }
        break;
    }
    case JIGUMO_SEARCH: {
        stop(actor);
        Creature* target = nearestTarget(pos, SIGHT);
        if (!target) {
            transition(actor, s, JIGUMO_WAIT, "wait1", generator);
            break;
        }
        s.goal = target->getPosition();
        const float residual = turnTo(actor, s, s.goal, dt);
        if (std::fabs(residual) < 0.02f || s.stateTime >= clipDuration("turn1")) {
            if (distXZ(pos, s.goal) < ATTACK_RANGE) {
                transition(actor, s, JIGUMO_SATTACK, "sattack1", generator);
            } else {
                transition(actor, s, JIGUMO_ATTACK, "attack1", generator);
            }
        }
        break;
    }
    case JIGUMO_ATTACK: {
        Creature* target = nearestTarget(pos, SIGHT);
        if (target) s.goal = target->getPosition();
        // Source StateAttack enables the bite at animation key event 2 (frame 26)
        // and only then calls walkFunc for the lunge.
        if (s.stateTime < 26.0f / 30.0f) {
            stop(actor);
            if (target) turnTo(actor, s, target->getPosition(), dt);
        } else {
            if (dueEvent(s, "attack1", 2, frame) && !s.captured) {
                Piki* piki = nearestPiki(pos, ATTACK_RANGE);
                if (piki) {
                    s.captured = piki;
                    emitBite(generator, frame);
                }
            }
            if (s.captured || distXZ(pos, s.goal) > ARRIVE_DIST) {
                walkTo(actor, s, s.goal, MOVE_SPEED, dt);
            } else {
                stop(actor);
            }
        }
        if (s.stateTime >= clipDuration("attack1")) {
            if (s.captured) {
                transition(actor, s, JIGUMO_CARRY, "backrun1", generator, true);
            } else {
                transition(actor, s, JIGUMO_MISS, "to_runaway1", generator);
            }
        }
        break;
    }
    case JIGUMO_MISS:
        stop(actor);
        if (s.stateTime >= clipDuration("to_runaway1")) {
            transition(actor, s, JIGUMO_RETURN, "runaway1", generator);
        }
        break;
    case JIGUMO_RETURN: {
        if (shouldFlick(actor)) {
            s.nextState = JIGUMO_HIDE;
            s.nextClip = "hide1";
            transition(actor, s, JIGUMO_FLICK, "flick1", generator);
            break;
        }
        if (distXZ(pos, s.home) < ARRIVE_DIST) {
            transition(actor, s, JIGUMO_HIDE, "hide1", generator);
            break;
        }
        walkTo(actor, s, s.home, RETURN_SPEED, dt);
        break;
    }
    case JIGUMO_CARRY: {
        if (shouldFlick(actor)) {
            s.nextState = JIGUMO_EAT;
            s.nextClip = "dive1";
            transition(actor, s, JIGUMO_FLICK, "flick1", generator, true);
            break;
        }
        if (distXZ(pos, s.home) < ARRIVE_DIST) {
            transition(actor, s, JIGUMO_EAT, "dive1", generator, true);
            break;
        }
        walkTo(actor, s, s.home, CARRY_SPEED, dt);
        break;
    }
    case JIGUMO_EAT: {
        stop(actor);
        // Source dive1 key event 8 (frame 80) swallows the carried Pikmin.
        if (dueEvent(s, "dive1", 8, frame)) {
            resolveKill(actor, s, generator);
        }
        if (s.stateTime >= clipDuration("dive1")) {
            transition(actor, s, JIGUMO_HIDE, "hide1", generator);
        }
        break;
    }
    case JIGUMO_FLICK: {
        stop(actor);
        if (dueEvent(s, "flick1", 2, frame)) {
            doFlick(actor);
            std::printf("P2_JIGUMO_FLICK generator=%u frame=%d\n", generator, frame);
            std::fflush(stdout);
        }
        if (s.stateTime >= clipDuration("flick1")) {
            const State next = s.nextState == JIGUMO_INVALID ? JIGUMO_RETURN : s.nextState;
            const char* clip = s.nextClip ? s.nextClip : "runaway1";
            s.nextState = JIGUMO_INVALID;
            s.nextClip = nullptr;
            transition(actor, s, next, clip, generator, true);
        }
        break;
    }
    case JIGUMO_SATTACK: {
        Creature* target = nearestTarget(pos, SIGHT);
        stop(actor);
        if (target) turnTo(actor, s, target->getPosition(), dt);
        // Source StateSAttack activates at mSAttackActiveFrame (13) and runs
        // eatPikmin continuously until the key event 3 miss check (frame 26).
        if (!s.attackActive && s.stateTime * 30.0f >= SATTACK_ACTIVE_FRAME) {
            s.attackActive = true;
            if (!s.captured) {
                Piki* piki = nearestPiki(pos, ATTACK_RANGE);
                if (piki) {
                    s.captured = piki;
                    emitBite(generator, int(SATTACK_ACTIVE_FRAME));
                }
            }
        }
        if (dueEvent(s, "sattack1", 3, frame)) {
            s.attackActive = false;
            if (!s.captured) {
                transition(actor, s, JIGUMO_SMISS, "smiss1", generator);
                break;
            }
        }
        // Source sattack1 key event 10 (frame 115) swallows a caught Pikmin.
        if (dueEvent(s, "sattack1", 10, frame)) {
            resolveKill(actor, s, generator);
        }
        if (s.stateTime >= clipDuration("sattack1")) {
            transition(actor, s, JIGUMO_SEARCH, "turn1", generator);
        }
        break;
    }
    case JIGUMO_SMISS:
        stop(actor);
        if (s.stateTime >= clipDuration("smiss1")) {
            transition(actor, s, JIGUMO_SEARCH, "turn1", generator);
        }
        break;
    case JIGUMO_HIDE:
        stop(actor);
        if (s.stateTime >= clipDuration("hide1")) {
            transition(actor, s, JIGUMO_APPEAR, "appear1", generator);
        }
        break;
    case JIGUMO_DEAD:
        stop(actor);
        if (s.stateTime >= clipDuration("dead1")) actor->die();
        break;
    default:
        break;
    }
    setPhase(s);
    s.logTimer += dt;
    if (s.logTimer >= 1.0f) {
        s.logTimer = 0.0f;
        const Vector3f now = actor->getPosition();
        std::printf("P2_JIGUMO_POS generator=%u state=%s clip=%s phase=%.2f "
                    "x=%.2f y=%.2f z=%.2f\n",
                    generator, stateName(s.state), s.clip.c_str(), s.phase,
                    now.x, now.y, now.z);
        std::fflush(stdout);
    }
}
