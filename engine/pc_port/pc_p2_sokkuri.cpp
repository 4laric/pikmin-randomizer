// Family-owned ground-invertebrate source behavior for the batch-2 Chappy
// placement vehicle: Skitter Leaf (Sokkuri, EnemyID 79). Implements the source
// SokkuriState.cpp FSM (Stay/Appear/Disappear/Wait/MoveGround/MoveWater/Flick/
// Dead/Press) on the P1 host, driven from p2-ground-actors.txt / p2-ground-bank.txt
// written by the batch-2 arena. Source revision
// 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms from
// experimental/pikmin2_ground_inverts_assets.py (GPVE01 rev 0).
//
// Port adaptations (recorded, not retail-faithful):
//   * View-angle detection is treated as a full hemisphere (fp13 is not present
//     in the Sokkuri general block); sight radius is the source fp12=150.
//   * Turn rate is a fixed adaptation (~pi rad/s); source uses fp turn class.
//   * Flick latch radius 25 and shake range/knockback are P1-host approximations.
//   * Water (MoveWater) is implemented but no staged arena supplies a water box.
// No other lane's module is modified; every hook is a no-op for unregistered
// actors.
#include "pc_p2_sokkuri.h"
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
    SOKKURI_INVALID = -1,
    SOKKURI_DEAD = 0,
    SOKKURI_PRESS = 1,
    SOKKURI_STAY = 2,
    SOKKURI_APPEAR = 3,
    SOKKURI_DISAPPEAR = 4,
    SOKKURI_WAIT = 5,
    SOKKURI_MOVE_GROUND = 6,
    SOKKURI_MOVE_WATER = 7,
    SOKKURI_FLICK = 8,
};

const char* stateName(State s) {
    switch (s) {
    case SOKKURI_DEAD: return "dead";
    case SOKKURI_PRESS: return "press";
    case SOKKURI_STAY: return "stay";
    case SOKKURI_APPEAR: return "appear";
    case SOKKURI_DISAPPEAR: return "disappear";
    case SOKKURI_WAIT: return "wait";
    case SOKKURI_MOVE_GROUND: return "moveground";
    case SOKKURI_MOVE_WATER: return "movewater";
    case SOKKURI_FLICK: return "flick";
    default: return "null";
    }
}

// Source values (ground_inverts manifest general/proper blocks).
constexpr float LIFE = 120.0f;
constexpr float MOVE_SPEED = 120.0f;
constexpr float SIGHT = 150.0f;
constexpr float HOME_RADIUS = 150.0f;
constexpr float TERRITORY = 200.0f;
constexpr float MAX_TRAVEL = 1.0f;   // fp01
constexpr float MIN_WAIT = 1.75f;    // fp13
constexpr float MAX_WAIT = 3.25f;    // fp12
constexpr float WAIT_PROB = 0.4f;    // fp11
constexpr float UNDERWATER_SPEED = 25.0f; // fp21
constexpr float TURN_RATE = 3.14159265f;  // port adaptation
constexpr float FLICK_RADIUS = 25.0f;     // port adaptation
constexpr float SHAKE_RANGE = 100.0f;     // port adaptation
constexpr float SHAKE_KNOCKBACK = 120.0f; // port adaptation

struct Clip {
    std::string name;
    float duration = 1.0f;
    bool loop = false;
    std::vector<std::pair<int, int>> events; // source frame -> event code
};

struct Sokkuri {
    State state = SOKKURI_STAY;
    State nextState = SOKKURI_INVALID;
    float stateTime = 0.0f;
    float timer = 0.0f;
    float moveVelocity = MOVE_SPEED;
    float heading = 0.0f;
    Vector3f targetPosition;
    Vector3f home;
    unsigned rng = 1;
    std::set<int> firedEvents;
    std::string clip = "appear1";
    float phase = 0.0f;
    bool hidden = true;
    bool deadLogged = false;
    float logTimer = 0.0f;
};

std::map<PelletView*, Sokkuri> actors;
std::map<std::string, Clip> clips;
bool ready = false;
bool loggedHidden = false;

unsigned nextRand(Sokkuri& s) {
    s.rng = s.rng * 1664525u + 1013904223u;
    return s.rng >> 8;
}
float rand01(Sokkuri& s) { return float(nextRand(s) & 0xffff) / 65535.0f; }
float randRange(Sokkuri& s, float lo, float hi) { return lo + (hi - lo) * rand01(s); }

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
bool isAppear(const Vector3f& pos) { return nearestTarget(pos) != nullptr; }
bool isDisappear(const Vector3f& pos, const Vector3f& home) {
    return distXZ(pos, home) < HOME_RADIUS && nearestTarget(pos) == nullptr;
}

bool shouldFlick(BTeki* a) {
    if (!pikiMgr) return false;
    const Vector3f pos = a->getPosition();
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (p && p->isAlive() && distXZ(p->getPosition(), pos) < FLICK_RADIUS) return true;
    }
    return false;
}
void doFlick(BTeki* a) {
    if (!pikiMgr) return;
    const Vector3f pos = a->getPosition();
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (p && p->isAlive() && distXZ(p->getPosition(), pos) < SHAKE_RANGE) {
            p->stimulate(InteractFlick(a, SHAKE_KNOCKBACK, 0.0f, 0.0f));
        }
    }
}

void enter(Sokkuri& s, State state, const char* clip, float timer = 0.0f) {
    s.state = state;
    s.stateTime = 0.0f;
    s.timer = timer;
    s.nextState = SOKKURI_INVALID;
    s.firedEvents.clear();
    if (clip) s.clip = clip;
}

void setNextMoveInfo(Sokkuri& s, const Vector3f& pos) {
    s.timer = randRange(s, 0.0f, MAX_TRAVEL); // source randWeightFloat(max-min)+0
    const float deg = randRange(s, 45.0f, 90.0f); // fp04..fp03
    float angle = deg * 3.14159265f / 180.0f * 3.14159265f;
    angle = rand01(s) < 0.5f ? angle + s.heading : angle - s.heading;
    s.targetPosition.x = 1000.0f * std::sin(angle) + pos.x;
    s.targetPosition.y = pos.y;
    s.targetPosition.z = 1000.0f * std::cos(angle) + pos.z;
}

void updateMove(BTeki* a, Sokkuri& s, float dt, bool water) {
    const Vector3f pos = a->getPosition();
    if (distXZ(pos, s.home) > TERRITORY) s.targetPosition = s.home;
    const float speedTarget = water ? UNDERWATER_SPEED : MOVE_SPEED;
    const float rate = (water ? 10.0f : 25.0f) * dt;
    s.moveVelocity += (speedTarget - s.moveVelocity) * (rate > 1.0f ? 1.0f : rate);
    const float desired = std::atan2(s.targetPosition.x - pos.x, s.targetPosition.z - pos.z);
    const float maxTurn = TURN_RATE * dt;
    float diff = wrapPi(desired - s.heading);
    if (diff > maxTurn) diff = maxTurn;
    if (diff < -maxTurn) diff = -maxTurn;
    s.heading = wrapPi(s.heading + diff);
    a->setDirection(s.heading);
    const Vector3f drive(std::sin(s.heading) * s.moveVelocity, 0.0f,
                         std::cos(s.heading) * s.moveVelocity);
    a->inputDrive(drive);
    a->mVelocity.set(drive);
}

void fireEvents(BTeki* a, Sokkuri& s) {
    auto it = clips.find(s.clip);
    if (it == clips.end()) return;
    for (const auto& event : it->second.events) {
        if (s.firedEvents.count(event.first)) continue;
        if (s.stateTime < event.first / 30.0f) continue;
        s.firedEvents.insert(event.first);
        if (s.state == SOKKURI_FLICK && event.second == 3) {
            doFlick(a);
            std::printf("P2_SOKKURI_FLICK generator=%u source_id=79 frame=%d\n",
                        a->mGenerator ? a->mGenerator->_70 : 0u, event.first);
        } else if (s.state == SOKKURI_DEAD && event.second == 2) {
            std::printf("P2_SOKKURI_DEAD_EFFECT generator=%u source_id=79\n",
                        a->mGenerator ? a->mGenerator->_70 : 0u);
        } else if (s.state == SOKKURI_PRESS && event.second == 2) {
            std::printf("P2_SOKKURI_PRESS_EFFECT generator=%u source_id=79\n",
                        a->mGenerator ? a->mGenerator->_70 : 0u);
        } else if (s.state == SOKKURI_DISAPPEAR && event.second == 2) {
            std::printf("P2_SOKKURI_HIDE_EFFECT generator=%u source_id=79\n",
                        a->mGenerator ? a->mGenerator->_70 : 0u);
        }
    }
}

void setPhase(Sokkuri& s) {
    if (s.state == SOKKURI_STAY) { s.phase = 0.0f; return; }
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
}

void pc_p2_sokkuri_reset() {
    actors.clear();
    clips.clear();
    ready = false;
    loggedHidden = false;
}

void pc_p2_sokkuri_forget(BTeki* actor) {
    actors.erase(static_cast<PelletView*>(actor));
}

// Fixture observability (#165/#407 lifecycle gates): read-only registration
// count / membership. Never mutates state and is safe for any actor pointer.
unsigned long pc_p2_sokkuri_count() {
    return (unsigned long)actors.size();
}

bool pc_p2_sokkuri_registered(BTeki* actor) {
    return actors.count(static_cast<PelletView*>(actor)) != 0;
}

float pc_p2_sokkuri_param_f(const BTeki* actor, int idx, float fallback) {
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

bool pc_p2_sokkuri_pressed(BTeki* teki, Creature*) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(teki));
    if (it == actors.end()) return false;
    Sokkuri& s = it->second;
    if (s.state == SOKKURI_DEAD || s.state == SOKKURI_PRESS) return true;
    teki->mHealth = 0.0f;
    enter(s, SOKKURI_PRESS, "pdead1");
    std::printf("P2_SOKKURI_PRESS generator=%u source_id=79\n",
                teki->mGenerator ? teki->mGenerator->_70 : 0u);
    std::fflush(stdout);
    return true;
}

bool pc_p2_sokkuri_clip(const BTeki* actor, const char*& name, float& phase) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    name = it->second.clip.c_str();
    phase = it->second.phase;
    return true;
}

void pc_p2_sokkuri_setup() {
    pc_p2_sokkuri_reset();
    if (!tekiMgr) return;

    // Clip durations and event frames from the validated ground-invertebrate bank.
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
                    if (species == "Sokkuri") {
                        Clip clip;
                        clip.name = name;
                        clip.duration = frames > 0 ? float(frames) / 30.0f : 1.0f;
                        clip.loop = (name == "run1" || name == "wrun1" || name == "wait1");
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
        if (species == "Sokkuri") wanted[unsigned(generator)] = species;
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
            std::printf("P2_SOKKURI_ERROR native_type generator=%u\n", actor->mGenerator->_70);
            std::abort();
        }
        Sokkuri& s = actors[static_cast<PelletView*>(actor)];
        s.rng = (actor->mGenerator->_70 * 2654435761u) | 1u;
        s.home = actor->getPosition();
        s.heading = actor->getDirection();
        s.targetPosition = s.home;
        actor->mHealth = LIFE;
        enter(s, SOKKURI_STAY, "appear1");
        std::printf("P2_SOKKURI_BIND generator=%u source_id=79 visual_only=0\n",
                    actor->mGenerator->_70);
        const Vector3f pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=Sokkuri native_family=Chappy generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented disguise=native\n",
                    actor->mGenerator->_70, pos.x, pos.y, pos.z, actor->mHealth, LIFE);
        found.insert(actor->mGenerator->_70);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_SOKKURI_ERROR missing_actor wanted=%zu found=%zu\n", wanted.size(), found.size());
        std::abort();
    }
    ready = true;
}

void pc_p2_sokkuri_update(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Sokkuri& s = it->second;
    const float dt = gsys->getFrameTime();
    if (dt <= 0.0f || dt > 0.5f) return;
    const Vector3f pos = actor->getPosition();

    if (actor->mHealth <= 0.0f && s.state != SOKKURI_DEAD && s.state != SOKKURI_PRESS) {
        if (!s.deadLogged) {
            std::printf("P2_SOKKURI_DEAD generator=%u source_id=79 health=0\n",
                        actor->mGenerator ? actor->mGenerator->_70 : 0u);
            std::fflush(stdout);
            s.deadLogged = true;
        }
        enter(s, SOKKURI_DEAD, "dead1");
    }

    s.stateTime += dt;
    switch (s.state) {
    case SOKKURI_STAY:
        s.hidden = true;
        s.clip = "appear1";
        if (!loggedHidden) {
            loggedHidden = true;
            std::printf("P2_SOKKURI_DISGUISE generator=%u hidden=1\n",
                        actor->mGenerator ? actor->mGenerator->_70 : 0u);
        }
        if (isAppear(pos)) {
            std::printf("P2_SOKKURI_DISGUISE generator=%u hidden=0\n",
                        actor->mGenerator ? actor->mGenerator->_70 : 0u);
            std::printf("P2_SOKKURI_STATE generator=%u state=appear\n",
                        actor->mGenerator ? actor->mGenerator->_70 : 0u);
            enter(s, SOKKURI_APPEAR, "appear1");
        }
        break;
    case SOKKURI_APPEAR:
        s.hidden = false;
        if (shouldFlick(actor)) {
            std::printf("P2_SOKKURI_STATE generator=%u state=flick\n",
                        actor->mGenerator ? actor->mGenerator->_70 : 0u);
            enter(s, SOKKURI_FLICK, "flick1");
        } else if (s.stateTime >= clipDuration("appear1")) {
            setNextMoveInfo(s, pos);
            std::printf("P2_SOKKURI_STATE generator=%u state=moveground\n",
                        actor->mGenerator ? actor->mGenerator->_70 : 0u);
            enter(s, SOKKURI_MOVE_GROUND, "run1", randRange(s, 0.0f, MAX_TRAVEL));
        }
        break;
    case SOKKURI_DISAPPEAR:
        if (s.stateTime >= clipDuration("hide1")) {
            std::printf("P2_SOKKURI_STATE generator=%u state=stay\n",
                        actor->mGenerator ? actor->mGenerator->_70 : 0u);
            enter(s, SOKKURI_STAY, "appear1");
        }
        break;
    case SOKKURI_WAIT:
        if (shouldFlick(actor)) {
            std::printf("P2_SOKKURI_STATE generator=%u state=flick\n",
                        actor->mGenerator ? actor->mGenerator->_70 : 0u);
            enter(s, SOKKURI_FLICK, "flick1");
            break;
        }
        s.timer += dt;
        if (s.timer > MAX_WAIT) {
            s.nextState = isDisappear(pos, s.home) ? SOKKURI_DISAPPEAR : SOKKURI_MOVE_GROUND;
        }
        if (s.stateTime >= clipDuration("wait1")) {
            const State next = s.nextState == SOKKURI_INVALID ? SOKKURI_MOVE_GROUND : s.nextState;
            if (next == SOKKURI_DISAPPEAR) {
                std::printf("P2_SOKKURI_STATE generator=%u state=disappear\n",
                            actor->mGenerator ? actor->mGenerator->_70 : 0u);
                enter(s, SOKKURI_DISAPPEAR, "hide1");
            } else {
                setNextMoveInfo(s, pos);
                std::printf("P2_SOKKURI_STATE generator=%u state=moveground\n",
                            actor->mGenerator ? actor->mGenerator->_70 : 0u);
                enter(s, SOKKURI_MOVE_GROUND, "run1", randRange(s, 0.0f, MAX_TRAVEL));
            }
        }
        break;
    case SOKKURI_MOVE_GROUND:
    case SOKKURI_MOVE_WATER: {
        const bool water = s.state == SOKKURI_MOVE_WATER;
        updateMove(actor, s, dt, water);
        s.timer += dt;
        if (shouldFlick(actor)) {
            std::printf("P2_SOKKURI_STATE generator=%u state=flick\n",
                        actor->mGenerator ? actor->mGenerator->_70 : 0u);
            enter(s, SOKKURI_FLICK, "flick1");
            break;
        }
        if (s.timer > MAX_TRAVEL) {
            if (isDisappear(pos, s.home)) {
                std::printf("P2_SOKKURI_STATE generator=%u state=disappear\n",
                            actor->mGenerator ? actor->mGenerator->_70 : 0u);
                enter(s, SOKKURI_DISAPPEAR, "hide1");
            } else if (rand01(s) < WAIT_PROB) {
                std::printf("P2_SOKKURI_STATE generator=%u state=wait\n",
                            actor->mGenerator ? actor->mGenerator->_70 : 0u);
                enter(s, SOKKURI_WAIT, "wait1", randRange(s, 0.0f, MAX_WAIT - MIN_WAIT));
            } else {
                setNextMoveInfo(s, pos);
                enter(s, s.state, water ? "wrun1" : "run1", randRange(s, 0.0f, MAX_TRAVEL));
            }
        }
        break;
    }
    case SOKKURI_FLICK:
        actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
        actor->mVelocity.x = 0.0f;
        actor->mVelocity.z = 0.0f;
        if (s.stateTime >= clipDuration("flick1")) {
            const bool water = false; // staged arena has no water box
            setNextMoveInfo(s, pos);
            std::printf("P2_SOKKURI_STATE generator=%u state=moveground\n",
                        actor->mGenerator ? actor->mGenerator->_70 : 0u);
            enter(s, SOKKURI_MOVE_GROUND, water ? "wrun1" : "run1", randRange(s, 0.0f, MAX_TRAVEL));
        }
        break;
    case SOKKURI_DEAD:
        actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
        actor->mVelocity.x = 0.0f;
        actor->mVelocity.z = 0.0f;
        // Host death handoff: the P1 strategy reacts to mHealth<=0 inside
        // BTeki::doAI(), calls die() there and then dieSoon()->becomePellet() in
        // the same doAI() pass. Calling BTeki::die() from this update-phase hook
        // would set mDeadState before the next doAI() and permanently block
        // dieSoon(), leaving a dead-but-present actor with no corpse. The module
        // therefore only drives the source dead clip and lets the host complete
        // teardown/corpse. (The SOKKURI_PRESS crush path is unchanged.)
        break;
    case SOKKURI_PRESS:
        if (s.stateTime >= clipDuration("pdead1")) actor->die();
        break;
    default:
        break;
    }
    setPhase(s);
    fireEvents(actor, s);
    s.logTimer += dt;
    if (s.logTimer >= 1.0f) {
        s.logTimer = 0.0f;
        std::printf("P2_SOKKURI_POS generator=%u state=%s clip=%s phase=%.2f x=%.2f z=%.2f\n",
                    actor->mGenerator ? actor->mGenerator->_70 : 0u, stateName(s.state),
                    s.clip.c_str(), s.phase, pos.x, pos.z);
        std::fflush(stdout);
    }
}
