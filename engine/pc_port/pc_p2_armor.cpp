// Family-owned ground-invertebrate source behavior for the batch-2 Chappy
// placement vehicle: Cloaking Burrow-nit (Armor, EnemyID 15). Implements the
// source ArmorState.cpp combat FSM: Stay (buried) -> Appear -> Move/GoHome ->
// Attack2 -> Eat/Fail -> Dead, plus Flick. Bridge states (Attack1, MoveSide/
// Centre/Top) are source-backed N/A because the arena has no ItemBridge.
// Source revision 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms from
// experimental/pikmin2_ground_inverts_assets.py (GPVE01 rev 0).
//
// Port adaptations (recorded, not retail-faithful):
//   * The P2 mouth-slot swallow is resolved on the P1 host as an explicit
//     capture within the source attack sweep radius at the attack2 motion-frame
//     window (17<frame<27), then a single InteractKill at the source eat event.
//     Exactly-once per bite.
//   * The source `damageCallBack` part-id rule (`dmg1`/bittered) is not
//     representable on the P1 host; damage is accepted while surfaced.
//   * View angle is a full hemisphere (fp13 absent from the Armor general block);
//     turn rate and flick radius are documented port adaptations.
// No other lane's module is modified; every hook is a no-op for unregistered actors.
#include "pc_p2_armor.h"
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
    ARMOR_INVALID = -1,
    ARMOR_DEAD = 0,
    ARMOR_STAY = 1,
    ARMOR_APPEAR = 2,
    ARMOR_DIVE = 3,
    ARMOR_MOVE = 4,
    ARMOR_GOHOME = 8,
    ARMOR_ATTACK2 = 10,
    ARMOR_EAT = 11,
    ARMOR_FLICK = 12,
    ARMOR_FAIL = 13,
};

const char* stateName(State s) {
    switch (s) {
    case ARMOR_DEAD: return "dead";
    case ARMOR_STAY: return "stay";
    case ARMOR_APPEAR: return "appear";
    case ARMOR_DIVE: return "dive";
    case ARMOR_MOVE: return "move";
    case ARMOR_GOHOME: return "gohome";
    case ARMOR_ATTACK2: return "attack2";
    case ARMOR_EAT: return "eat";
    case ARMOR_FLICK: return "flick";
    case ARMOR_FAIL: return "fail";
    default: return "null";
    }
}

// Source enemyparm.txt values (ground_inverts manifest general).
constexpr float LIFE = 300.0f;
constexpr float MOVE_SPEED = 50.0f;
constexpr float SIGHT = 200.0f;
constexpr float TERRITORY = 400.0f;
constexpr float HOME_RADIUS = 30.0f;
constexpr float ATTACK_RANGE = 75.0f;
constexpr float ATTACK_ANGLE = 0.785398f; // fp attack hit angle ~45 deg
constexpr float TURN_RATE = 2.0f;         // port adaptation
constexpr float FLICK_RADIUS = 25.0f;     // port adaptation
constexpr float SHAKE_RANGE = 100.0f;
constexpr float SHAKE_KNOCKBACK = 120.0f;

struct Clip {
    std::string name;
    float duration = 1.0f;
    bool loop = false;
    std::vector<std::pair<int, int>> events;
};

struct Armor {
    State state = ARMOR_STAY;
    float stateTime = 0.0f;
    float heading = 0.0f;
    Vector3f home;
    Piki* captured = nullptr;
    std::set<int> firedEvents;
    std::string clip = "appear";
    float phase = 0.0f;
    bool biteLogged = false;
    bool deadLogged = false;
    float logTimer = 0.0f;
};

std::map<PelletView*, Armor> actors;
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
    const Vector3f pos = a->getPosition();
    return nearestPiki(pos, FLICK_RADIUS) != nullptr;
}
void doFlick(BTeki* a, Armor& s) {
    if (!pikiMgr) return;
    const Vector3f pos = a->getPosition();
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (p && p->isAlive() && distXZ(p->getPosition(), pos) < SHAKE_RANGE) {
            p->stimulate(InteractFlick(a, SHAKE_KNOCKBACK, 0.0f, a->getDirection()));
        }
    }
    (void)s;
}
void enter(Armor& s, State state, const char* clip) {
    s.state = state;
    s.stateTime = 0.0f;
    s.firedEvents.clear();
    s.biteLogged = false;
    if (clip) s.clip = clip;
}
void walkTo(BTeki* a, Armor& s, const Vector3f& target, float dt) {
    const Vector3f pos = a->getPosition();
    const float desired = std::atan2(target.x - pos.x, target.z - pos.z);
    const float maxTurn = TURN_RATE * dt;
    float diff = wrapPi(desired - s.heading);
    if (diff > maxTurn) diff = maxTurn;
    if (diff < -maxTurn) diff = -maxTurn;
    s.heading = wrapPi(s.heading + diff);
    a->setDirection(s.heading);
    const Vector3f drive(std::sin(s.heading) * MOVE_SPEED, 0.0f,
                         std::cos(s.heading) * MOVE_SPEED);
    a->inputDrive(drive);
    a->mVelocity.set(drive);
}
void stop(BTeki* a) {
    a->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
    a->mVelocity.x = 0.0f;
    a->mVelocity.z = 0.0f;
}
float motionFrame(const Armor& s) { return s.stateTime * 30.0f; }

void setPhase(Armor& s) {
    if (s.state == ARMOR_STAY) { s.phase = 0.0f; return; }
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

void pc_p2_armor_reset() {
    actors.clear();
    clips.clear();
    ready = false;
}
void pc_p2_armor_forget_piki(Piki* piki) {
    for (auto& entry : actors) if (entry.second.captured == piki) entry.second.captured = nullptr;
}

void pc_p2_armor_forget(BTeki* actor) { actors.erase(static_cast<PelletView*>(actor)); }

float pc_p2_armor_param_f(const BTeki* actor, int idx, float fallback) {
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

bool pc_p2_armor_clip(const BTeki* actor, const char*& name, float& phase) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    name = it->second.clip.c_str();
    phase = it->second.phase;
    return true;
}

void pc_p2_armor_setup() {
    pc_p2_armor_reset();
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
                    if (species == "Armor") {
                        Clip clip;
                        clip.name = name;
                        clip.duration = frames > 0 ? float(frames) / 30.0f : 1.0f;
                        clip.loop = (name == "move");
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
        if (species == "Armor") wanted[unsigned(generator)] = species;
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
            std::printf("P2_ARMOR_ERROR native_type generator=%u\n", actor->mGenerator->_70);
            std::abort();
        }
        Armor& s = actors[static_cast<PelletView*>(actor)];
        s.home = actor->getPosition();
        s.heading = actor->getDirection();
        actor->mHealth = LIFE;
        enter(s, ARMOR_STAY, "appear");
        std::printf("P2_ARMOR_BIND generator=%u source_id=15 visual_only=0\n", actor->mGenerator->_70);
        const Vector3f pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=Armor native_family=Chappy generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented attack=animation_event\n",
                    actor->mGenerator->_70, pos.x, pos.y, pos.z, actor->mHealth, LIFE);
        found.insert(actor->mGenerator->_70);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_ARMOR_ERROR missing_actor wanted=%zu found=%zu\n", wanted.size(), found.size());
        std::abort();
    }
    ready = true;
}

void pc_p2_armor_update(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Armor& s = it->second;
    const float dt = gsys->getFrameTime();
    if (dt <= 0.0f || dt > 0.5f) return;
    const Vector3f pos = actor->getPosition();
    const unsigned generator = actor->mGenerator ? actor->mGenerator->_70 : 0u;

    if (actor->mHealth <= 0.0f && s.state != ARMOR_DEAD) {
        if (!s.deadLogged) {
            std::printf("P2_ARMOR_DEAD generator=%u source_id=15 health=0\n", generator);
            std::fflush(stdout);
            s.deadLogged = true;
        }
        enter(s, ARMOR_DEAD, "dead");
    }

    s.stateTime += dt;
    switch (s.state) {
    case ARMOR_STAY:
        stop(actor);
        s.clip = "appear";
        if (nearestTarget(pos)) {
            std::printf("P2_ARMOR_STATE generator=%u state=appear\n", generator);
            enter(s, ARMOR_APPEAR, "appear");
        }
        break;
    case ARMOR_APPEAR:
        stop(actor);
        if (s.stateTime >= clipDuration("appear")) {
            std::printf("P2_ARMOR_STATE generator=%u state=move\n", generator);
            enter(s, ARMOR_MOVE, "move");
        }
        break;
    case ARMOR_MOVE:
    case ARMOR_GOHOME: {
        Creature* target = nearestTarget(pos);
        if (s.state == ARMOR_MOVE && target) {
            const float angle = std::fabs(wrapPi(std::atan2(target->getPosition().x - pos.x,
                                                           target->getPosition().z - pos.z) - s.heading));
            if (distXZ(target->getPosition(), pos) < ATTACK_RANGE && angle < ATTACK_ANGLE) {
                std::printf("P2_ARMOR_STATE generator=%u state=attack2\n", generator);
                enter(s, ARMOR_ATTACK2, "attack2");
                break;
            }
            walkTo(actor, s, target->getPosition(), dt);
        } else if (s.state == ARMOR_GOHOME || !target) {
            walkTo(actor, s, s.home, dt);
        }
        if (distXZ(pos, s.home) > TERRITORY && s.state != ARMOR_GOHOME) {
            std::printf("P2_ARMOR_STATE generator=%u state=gohome\n", generator);
            enter(s, ARMOR_GOHOME, "move");
            break;
        }
        if (s.state == ARMOR_GOHOME && distXZ(pos, s.home) < HOME_RADIUS) {
            std::printf("P2_ARMOR_STATE generator=%u state=dive\n", generator);
            enter(s, ARMOR_DIVE, "dive");
            break;
        }
        if (shouldFlick(actor)) {
            std::printf("P2_ARMOR_STATE generator=%u state=flick\n", generator);
            enter(s, ARMOR_FLICK, "flick");
        }
        break;
    }
    case ARMOR_ATTACK2: {
        stop(actor);
        const float frame = motionFrame(s);
        if (frame > 17.0f && frame < 27.0f && !s.captured) {
            Piki* piki = nearestPiki(pos, ATTACK_RANGE);
            if (piki) {
                s.captured = piki;
                std::printf("P2_ARMOR_BITE generator=%u frame=%.1f pikmin=1\n", generator, frame);
                std::fflush(stdout);
            }
        }
        if (s.stateTime >= clipDuration("attack2")) {
            if (s.captured && s.captured->isAlive()) {
                std::printf("P2_ARMOR_STATE generator=%u state=eat\n", generator);
                enter(s, ARMOR_EAT, "eat");
            } else {
                std::printf("P2_ARMOR_STATE generator=%u state=fail\n", generator);
                enter(s, ARMOR_FAIL, "attack_fail");
            }
        }
        break;
    }
    case ARMOR_EAT: {
        stop(actor);
        auto clip = clips.find("eat");
        if (clip != clips.end()) {
            for (const auto& event : clip->second.events) {
                if (event.second == 2 && !s.firedEvents.count(event.first)
                        && s.stateTime >= event.first / 30.0f) {
                    s.firedEvents.insert(event.first);
                    if (s.captured && s.captured->isAlive()) {
                        s.captured->stimulate(InteractKill(actor, 0));
                        std::printf("P2_ARMOR_EAT generator=%u pikmin=1\n", generator);
                        std::fflush(stdout);
                    }
                    s.captured = nullptr;
                }
            }
        }
        if (s.stateTime >= clipDuration("eat")) {
            s.captured = nullptr;
            std::printf("P2_ARMOR_STATE generator=%u state=move\n", generator);
            enter(s, ARMOR_MOVE, "move");
        }
        break;
    }
    case ARMOR_FLICK: {
        stop(actor);
        auto clip = clips.find("flick");
        const int flickFrame = (clip != clips.end() && !clip->second.events.empty())
                                   ? clip->second.events.front().first : 14;
        if (!s.firedEvents.count(flickFrame) && s.stateTime >= flickFrame / 30.0f) {
            s.firedEvents.insert(flickFrame);
            doFlick(actor, s);
            std::printf("P2_ARMOR_FLICK generator=%u frame=%d\n", generator, flickFrame);
            std::fflush(stdout);
        }
        if (s.stateTime >= clipDuration("flick")) {
            std::printf("P2_ARMOR_STATE generator=%u state=move\n", generator);
            enter(s, ARMOR_MOVE, "move");
        }
        break;
    }
    case ARMOR_FAIL:
        stop(actor);
        if (s.stateTime >= clipDuration("attack_fail")) {
            std::printf("P2_ARMOR_STATE generator=%u state=move\n", generator);
            enter(s, ARMOR_MOVE, "move");
        }
        break;
    case ARMOR_DIVE:
        stop(actor);
        if (s.stateTime >= clipDuration("dive")) {
            std::printf("P2_ARMOR_STATE generator=%u state=stay\n", generator);
            enter(s, ARMOR_STAY, "appear");
        }
        break;
    case ARMOR_DEAD:
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
        std::printf("P2_ARMOR_POS generator=%u state=%s clip=%s phase=%.2f x=%.2f z=%.2f\n",
                    generator, stateName(s.state), s.clip.c_str(), s.phase, pos.x, pos.z);
        std::fflush(stdout);
    }
}
